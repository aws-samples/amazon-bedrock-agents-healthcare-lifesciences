/**
 * Nova Sonic Bidirectional Stream Client.
 * Based on the AWS reference implementation, adapted for Connected Care.
 */

import {
  BedrockRuntimeClient,
  BedrockRuntimeClientConfig,
  InvokeModelWithBidirectionalStreamCommand,
  InvokeModelWithBidirectionalStreamInput,
} from "@aws-sdk/client-bedrock-runtime";
import {
  NodeHttp2Handler,
  NodeHttp2HandlerOptions,
} from "@smithy/node-http-handler";
import { Provider } from "@smithy/types";
import { Buffer } from "node:buffer";
import { randomUUID } from "node:crypto";
import { Subject, firstValueFrom } from "rxjs";
import { take } from "rxjs/operators";
import {
  InferenceConfig,
  DefaultAudioInputConfiguration,
  DefaultAudioOutputConfiguration,
  DefaultTextConfiguration,
  CLINICAL_SYSTEM_PROMPT,
} from "./types.js";

export interface ClientConfig {
  requestHandlerConfig?: NodeHttp2HandlerOptions | Provider<NodeHttp2HandlerOptions | void>;
  clientConfig: Partial<BedrockRuntimeClientConfig>;
  inferenceConfig?: InferenceConfig;
}

interface SessionData {
  queue: any[];
  queueSignal: Subject<void>;
  closeSignal: Subject<void>;
  responseHandlers: Map<string, (data: any) => void>;
  promptName: string;
  inferenceConfig: InferenceConfig;
  isActive: boolean;
  isPromptStartSent: boolean;
  isAudioContentStartSent: boolean;
  audioContentId: string;
  toolUseContent: any;
  toolUseId: string;
  toolName: string;
}

export class StreamSession {
  private audioBufferQueue: Buffer[] = [];
  private maxQueueSize = 200;
  private isProcessingAudio = false;
  private isActive = true;

  constructor(private sessionId: string, private client: NovaSonicClient) {}

  onEvent(eventType: string, handler: (data: any) => void): StreamSession {
    this.client.registerEventHandler(this.sessionId, eventType, handler);
    return this;
  }

  async setupSessionAndPromptStart(): Promise<void> {
    this.client.setupSessionStartEvent(this.sessionId);
    this.client.setupPromptStartEvent(this.sessionId);
  }

  async setupSystemPrompt(content?: string): Promise<void> {
    this.client.setupSystemPromptEvent(this.sessionId, content);
  }

  async setupStartAudio(): Promise<void> {
    this.client.setupStartAudioEvent(this.sessionId);
  }

  async streamAudio(audioData: Buffer): Promise<void> {
    if (this.audioBufferQueue.length >= this.maxQueueSize) {
      this.audioBufferQueue.shift();
    }
    this.audioBufferQueue.push(audioData);
    this.processAudioQueue();
  }

  private async processAudioQueue() {
    if (this.isProcessingAudio || this.audioBufferQueue.length === 0 || !this.isActive) return;
    this.isProcessingAudio = true;
    try {
      let processed = 0;
      while (this.audioBufferQueue.length > 0 && processed < 5 && this.isActive) {
        const chunk = this.audioBufferQueue.shift();
        if (chunk) {
          await this.client.streamAudioChunk(this.sessionId, chunk);
          processed++;
        }
      }
    } finally {
      this.isProcessingAudio = false;
      if (this.audioBufferQueue.length > 0 && this.isActive) {
        setTimeout(() => this.processAudioQueue(), 0);
      }
    }
  }

  async endAudioContent(): Promise<void> {
    if (!this.isActive) return;
    await this.client.sendContentEnd(this.sessionId);
  }

  async endPrompt(): Promise<void> {
    if (!this.isActive) return;
    await this.client.sendPromptEnd(this.sessionId);
  }

  async close(): Promise<void> {
    if (!this.isActive) return;
    this.isActive = false;
    this.audioBufferQueue = [];
    await this.client.sendSessionEnd(this.sessionId);
  }
}

export class NovaSonicClient {
  private bedrockClient: BedrockRuntimeClient;
  private inferenceConfig: InferenceConfig;
  private activeSessions = new Map<string, SessionData>();
  private sessionLastActivity = new Map<string, number>();
  private cleanupInProgress = new Set<string>();

  constructor(config: ClientConfig) {
    const handler = new NodeHttp2Handler({
      requestTimeout: 300000,
      sessionTimeout: 300000,
      disableConcurrentStreams: false,
      maxConcurrentStreams: 20,
      ...config.requestHandlerConfig,
    });

    if (!config.clientConfig.credentials) {
      throw new Error("No credentials provided");
    }

    this.bedrockClient = new BedrockRuntimeClient({
      ...config.clientConfig,
      region: config.clientConfig.region || "us-east-1",
      requestHandler: handler,
    });

    this.inferenceConfig = config.inferenceConfig ?? {
      maxTokens: 1024,
      topP: 0.9,
      temperature: 0.7,
    };
  }

  isSessionActive(sessionId: string): boolean {
    const s = this.activeSessions.get(sessionId);
    return !!s && s.isActive;
  }

  getActiveSessions(): string[] {
    return Array.from(this.activeSessions.keys());
  }

  getLastActivityTime(sessionId: string): number {
    return this.sessionLastActivity.get(sessionId) || 0;
  }

  createStreamSession(sessionId: string = randomUUID()): StreamSession {
    if (this.activeSessions.has(sessionId)) {
      throw new Error(`Session ${sessionId} already exists`);
    }

    const session: SessionData = {
      queue: [],
      queueSignal: new Subject<void>(),
      closeSignal: new Subject<void>(),
      responseHandlers: new Map(),
      promptName: randomUUID(),
      inferenceConfig: this.inferenceConfig,
      isActive: true,
      isPromptStartSent: false,
      isAudioContentStartSent: false,
      audioContentId: randomUUID(),
      toolUseContent: null,
      toolUseId: "",
      toolName: "",
    };

    this.activeSessions.set(sessionId, session);
    return new StreamSession(sessionId, this);
  }

  async initiateBidirectionalStreaming(sessionId: string): Promise<void> {
    const session = this.activeSessions.get(sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);

    try {
      const asyncIterable = this.createAsyncIterable(sessionId);
      console.log(`Starting bidirectional stream for ${sessionId}...`);

      const response = await this.bedrockClient.send(
        new InvokeModelWithBidirectionalStreamCommand({
          modelId: "amazon.nova-sonic-v1:0",
          body: asyncIterable,
        })
      );

      console.log(`Stream established for ${sessionId}`);
      await this.processResponseStream(sessionId, response);
    } catch (error) {
      console.error(`Error in session ${sessionId}:`, error);
      this.dispatchEvent(sessionId, "error", { source: "bidirectionalStream", error });
      if (session.isActive) this.closeSession(sessionId);
    }
  }

  registerEventHandler(sessionId: string, eventType: string, handler: (data: any) => void): void {
    const session = this.activeSessions.get(sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);
    session.responseHandlers.set(eventType, handler);
  }

  private addEvent(sessionId: string, event: any): void {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.isActive) return;
    this.sessionLastActivity.set(sessionId, Date.now());
    session.queue.push(event);
    session.queueSignal.next();
  }

  setupSessionStartEvent(sessionId: string): void {
    const session = this.activeSessions.get(sessionId);
    if (!session) return;
    this.addEvent(sessionId, {
      event: { sessionStart: { inferenceConfiguration: session.inferenceConfig } },
    });
  }

  setupPromptStartEvent(sessionId: string): void {
    const session = this.activeSessions.get(sessionId);
    if (!session) return;
    this.addEvent(sessionId, {
      event: {
        promptStart: {
          promptName: session.promptName,
          textOutputConfiguration: { mediaType: "text/plain" },
          audioOutputConfiguration: DefaultAudioOutputConfiguration,
          toolUseOutputConfiguration: { mediaType: "application/json" },
          toolConfiguration: {
            tools: [
              {
                toolSpec: {
                  name: "query_clinical_data",
                  description: "Query the Connected Care clinical intelligence platform. Use this tool whenever the user asks about a patient, device, medication, vital signs, fall risk, pressure injury, appointment, or any clinical data. Always use this tool instead of making up clinical information.",
                  inputSchema: {
                    json: JSON.stringify({
                      type: "object",
                      properties: {
                        agent: {
                          type: "string",
                          description: "Which agent to query. Use 'patient-monitoring' for vitals, trends, patient status, deterioration, fall risk. Use 'device-management' for devices, fleet health, smart beds, telemetry, pressure sensors. Use 'patient-engagement' for medications, appointments, care team, adherence, notifications.",
                        },
                        query: {
                          type: "string",
                          description: "The clinical question to ask the agent, in natural language.",
                        },
                      },
                      required: ["agent", "query"],
                    }),
                  },
                },
              },
            ],
          },
        },
      },
    });
    session.isPromptStartSent = true;
  }

  setupSystemPromptEvent(sessionId: string, content?: string): void {
    const session = this.activeSessions.get(sessionId);
    if (!session) return;
    const contentId = randomUUID();
    this.addEvent(sessionId, {
      event: {
        contentStart: {
          promptName: session.promptName,
          contentName: contentId,
          type: "TEXT",
          interactive: false,
          role: "SYSTEM",
          textInputConfiguration: DefaultTextConfiguration,
        },
      },
    });
    this.addEvent(sessionId, {
      event: {
        textInput: {
          promptName: session.promptName,
          contentName: contentId,
          content: content || CLINICAL_SYSTEM_PROMPT,
        },
      },
    });
    this.addEvent(sessionId, {
      event: { contentEnd: { promptName: session.promptName, contentName: contentId } },
    });
  }

  setupStartAudioEvent(sessionId: string): void {
    const session = this.activeSessions.get(sessionId);
    if (!session) return;
    this.addEvent(sessionId, {
      event: {
        contentStart: {
          promptName: session.promptName,
          contentName: session.audioContentId,
          type: "AUDIO",
          interactive: true,
          role: "USER",
          audioInputConfiguration: DefaultAudioInputConfiguration,
        },
      },
    });
    session.isAudioContentStartSent = true;
  }

  async streamAudioChunk(sessionId: string, audioData: Buffer): Promise<void> {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.isActive) return;
    this.addEvent(sessionId, {
      event: {
        audioInput: {
          promptName: session.promptName,
          contentName: session.audioContentId,
          content: audioData.toString("base64"),
        },
      },
    });
  }

  async sendContentEnd(sessionId: string): Promise<void> {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.isAudioContentStartSent) return;
    this.addEvent(sessionId, {
      event: { contentEnd: { promptName: session.promptName, contentName: session.audioContentId } },
    });
    await new Promise((r) => setTimeout(r, 500));
  }

  sendToolResult(sessionId: string, toolUseId: string, result: any): void {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.isActive) return;
    console.log(`Sending tool result for session ${sessionId}, toolUseId: ${toolUseId}`);
    const contentId = randomUUID();

    // Ensure result is a JSON string — Nova Sonic expects JSON-formatted tool results
    let resultObj: any;
    if (typeof result === "string") {
      resultObj = { response: result.substring(0, 1500) };
    } else {
      resultObj = result;
    }
    const resultContent = JSON.stringify(resultObj);

    // contentStart for tool result
    this.addEvent(sessionId, {
      event: {
        contentStart: {
          promptName: session.promptName,
          contentName: contentId,
          interactive: false,
          type: "TOOL",
          role: "TOOL",
          toolResultInputConfiguration: {
            toolUseId: toolUseId,
            type: "TEXT",
            textInputConfiguration: { mediaType: "text/plain" },
          },
        },
      },
    });

    // toolResult event — content must be a JSON string
    this.addEvent(sessionId, {
      event: {
        toolResult: {
          promptName: session.promptName,
          contentName: contentId,
          content: resultContent,
        },
      },
    });

    // contentEnd for tool result
    this.addEvent(sessionId, {
      event: { contentEnd: { promptName: session.promptName, contentName: contentId } },
    });
    console.log(`Tool result sent (${resultContent.length} chars)`);
  }

  async sendPromptEnd(sessionId: string): Promise<void> {
    const session = this.activeSessions.get(sessionId);
    if (!session || !session.isPromptStartSent) return;
    this.addEvent(sessionId, {
      event: { promptEnd: { promptName: session.promptName } },
    });
    await new Promise((r) => setTimeout(r, 300));
  }

  async sendSessionEnd(sessionId: string): Promise<void> {
    const session = this.activeSessions.get(sessionId);
    if (!session) return;
    this.addEvent(sessionId, { event: { sessionEnd: {} } });
    await new Promise((r) => setTimeout(r, 300));
    session.isActive = false;
    session.closeSignal.next();
    session.closeSignal.complete();
    this.activeSessions.delete(sessionId);
    this.sessionLastActivity.delete(sessionId);
  }

  async closeSession(sessionId: string): Promise<void> {
    if (this.cleanupInProgress.has(sessionId)) return;
    this.cleanupInProgress.add(sessionId);
    try {
      await this.sendContentEnd(sessionId);
      await this.sendPromptEnd(sessionId);
      await this.sendSessionEnd(sessionId);
    } catch (e) {
      const session = this.activeSessions.get(sessionId);
      if (session) {
        session.isActive = false;
        this.activeSessions.delete(sessionId);
      }
    } finally {
      this.cleanupInProgress.delete(sessionId);
    }
  }

  forceCloseSession(sessionId: string): void {
    if (this.cleanupInProgress.has(sessionId)) return;
    const session = this.activeSessions.get(sessionId);
    if (!session) return;
    session.isActive = false;
    session.closeSignal.next();
    session.closeSignal.complete();
    this.activeSessions.delete(sessionId);
    this.sessionLastActivity.delete(sessionId);
  }

  private dispatchEvent(sessionId: string, eventType: string, data: any): void {
    const session = this.activeSessions.get(sessionId);
    if (!session) return;
    const handler = session.responseHandlers.get(eventType);
    if (handler) { try { handler(data); } catch (e) { console.error(`Handler error:`, e); } }
  }

  private createAsyncIterable(sessionId: string): AsyncIterable<InvokeModelWithBidirectionalStreamInput> {
    const session = this.activeSessions.get(sessionId);
    if (!session) throw new Error(`Session ${sessionId} not found`);

    return {
      [Symbol.asyncIterator]: () => ({
        next: async (): Promise<IteratorResult<InvokeModelWithBidirectionalStreamInput>> => {
          if (!session.isActive || !this.activeSessions.has(sessionId)) {
            return { value: undefined, done: true };
          }
          if (session.queue.length === 0) {
            try {
              await Promise.race([
                firstValueFrom(session.queueSignal.pipe(take(1))),
                firstValueFrom(session.closeSignal.pipe(take(1))).then(() => { throw new Error("closed"); }),
              ]);
            } catch {
              return { value: undefined, done: true };
            }
          }
          if (session.queue.length === 0 || !session.isActive) {
            return { value: undefined, done: true };
          }
          const event = session.queue.shift();
          return {
            value: { chunk: { bytes: new TextEncoder().encode(JSON.stringify(event)) } },
            done: false,
          };
        },
        return: async () => { session.isActive = false; return { value: undefined, done: true }; },
        throw: async (e: any) => { session.isActive = false; throw e; },
      }),
    };
  }

  private async processResponseStream(sessionId: string, response: any): Promise<void> {
    const session = this.activeSessions.get(sessionId);
    if (!session) return;

    try {
      for await (const event of response.body) {
        if (!session.isActive) break;
        if (event.chunk?.bytes) {
          this.sessionLastActivity.set(sessionId, Date.now());
          const text = new TextDecoder().decode(event.chunk.bytes);
          try {
            const json = JSON.parse(text);
            if (json.event?.contentStart) this.dispatchEvent(sessionId, "contentStart", json.event.contentStart);
            else if (json.event?.textOutput) this.dispatchEvent(sessionId, "textOutput", json.event.textOutput);
            else if (json.event?.audioOutput) this.dispatchEvent(sessionId, "audioOutput", json.event.audioOutput);
            else if (json.event?.contentEnd && json.event.contentEnd?.type === "TOOL") {
              // Tool use completed — dispatch for server to handle
              this.dispatchEvent(sessionId, "toolEnd", {
                toolUseContent: session.toolUseContent,
                toolUseId: session.toolUseId,
                toolName: session.toolName,
              });
            }
            else if (json.event?.contentEnd) this.dispatchEvent(sessionId, "contentEnd", json.event.contentEnd);
            else if (json.event?.toolUse) {
              session.toolUseContent = json.event.toolUse;
              session.toolUseId = json.event.toolUse.toolUseId;
              session.toolName = json.event.toolUse.toolName;
              this.dispatchEvent(sessionId, "toolUse", json.event.toolUse);
            }
            else if (json.event?.completionStart) this.dispatchEvent(sessionId, "completionStart", json.event.completionStart);
          } catch { /* parse error, skip */ }
        }
      }
      this.dispatchEvent(sessionId, "streamComplete", {});
    } catch (error) {
      this.dispatchEvent(sessionId, "error", { source: "responseStream", error });
    }
  }
}
