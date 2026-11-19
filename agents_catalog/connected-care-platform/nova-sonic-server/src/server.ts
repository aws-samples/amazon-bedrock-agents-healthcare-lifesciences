/**
 * Nova Sonic WebSocket Server for Connected Care.
 * Bridges browser audio ↔ Bedrock Nova Sonic bidirectional stream.
 */

import express from "express";
import http from "http";
import path from "path";
import { fileURLToPath } from "url";
import { Server } from "socket.io";
import { defaultProvider } from "@aws-sdk/credential-provider-node";
import { NovaSonicClient, StreamSession } from "./client.js";
import { Buffer } from "node:buffer";
import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: "*", methods: ["GET", "POST"] },
});

const PROXY_FUNCTION_NAME = process.env.PROXY_FUNCTION_NAME || "connected-care-agentcore-proxy";
const lambdaClient = new LambdaClient({ region: process.env.AWS_REGION || "us-east-1" });

const bedrockClient = new NovaSonicClient({
  requestHandlerConfig: { maxConcurrentStreams: 10 },
  clientConfig: {
    region: process.env.AWS_REGION || "us-east-1",
    credentials: defaultProvider(),
  },
});

const socketSessions = new Map<string, StreamSession>();
const sessionStates = new Map<string, string>();

// Serve test page
app.use(express.static(path.join(__dirname, "../public")));

app.get("/health", (_req, res) => {
  res.json({ status: "ok", activeSessions: bedrockClient.getActiveSessions().length });
});

io.on("connection", (socket) => {
  console.log(`Client connected: ${socket.id}`);
  sessionStates.set(socket.id, "closed");

  socket.on("initializeConnection", async (callback) => {
    try {
      const state = sessionStates.get(socket.id);
      if (state === "active") { callback?.({ success: true }); return; }

      console.log(`Creating session for ${socket.id}`);
      sessionStates.set(socket.id, "initializing");

      const session = bedrockClient.createStreamSession(socket.id);

      // Wire up event handlers
      session.onEvent("textOutput", (data) => {
        console.log("Text:", data?.content || data);
        socket.emit("textOutput", data);
      });
      session.onEvent("audioOutput", (data) => {
        socket.emit("audioOutput", data);
      });
      session.onEvent("contentStart", (data) => {
        socket.emit("contentStart", data);
      });
      session.onEvent("contentEnd", (data) => {
        socket.emit("contentEnd", data);
      });
      session.onEvent("completionStart", (data) => {
        socket.emit("completionStart", data);
      });
      session.onEvent("error", (data) => {
        console.error("Session error:", data);
        socket.emit("error", data);
      });
      session.onEvent("toolUse", (data) => {
        console.log("Tool use requested:", data?.toolName, data);
        socket.emit("toolUse", data);
      });
      session.onEvent("toolEnd", async (data) => {
        console.log(`Tool end — raw data:`, JSON.stringify(data, null, 2));
        try {
          // Parse the tool input — toolUseContent has a 'content' field that's a JSON string
          let toolInput: any = {};
          const rawContent = data.toolUseContent?.content;
          if (rawContent) {
            try {
              toolInput = typeof rawContent === "string" ? JSON.parse(rawContent) : rawContent;
            } catch {
              toolInput = { query: String(rawContent) };
            }
          }

          const agentId = toolInput.agent || "patient-monitoring";
          const query = toolInput.query || "list all patients";

          console.log(`Calling agent: ${agentId}, query: ${query}`);

          // Call the existing proxy Lambda
          const payload = {
            requestContext: { http: { method: "POST" } },
            body: JSON.stringify({
              agent: agentId,
              prompt: query,
              session_id: `nova-sonic-${socket.id}`,
              sync: true,
              voice_mode: true,
            }),
          };

          const lambdaResponse = await lambdaClient.send(new InvokeCommand({
            FunctionName: PROXY_FUNCTION_NAME,
            InvocationType: "RequestResponse",
            Payload: Buffer.from(JSON.stringify(payload)),
          }));

          const responseBody = JSON.parse(new TextDecoder().decode(lambdaResponse.Payload));
          const body = JSON.parse(responseBody.body || "{}");
          const agentResponse = body.response || body.error || "No data available";

          // Clean the response — remove markdown that could break JSON serialization
          const cleanResponse = agentResponse
            .replace(/\|/g, ' ')
            .replace(/\*\*/g, '')
            .replace(/\*/g, '')
            .replace(/#{1,4}\s*/g, '')
            .replace(/```[\s\S]*?```/g, '')
            .replace(/`/g, '')
            .replace(/---/g, '')
            .substring(0, 1500);

          console.log(`Agent response (${cleanResponse.length} chars): ${cleanResponse.substring(0, 100)}...`);

          // Send raw agent response to frontend for chart rendering
          socket.emit('agentData', {
            agent: agentId,
            query: query,
            rawResponse: agentResponse,  // Full response with vitals data for charts
          });

          // Send tool result back to Nova Sonic
          bedrockClient.sendToolResult(socket.id, data.toolUseId, cleanResponse);
        } catch (error) {
          console.error("Tool execution error:", error);
          bedrockClient.sendToolResult(socket.id, data.toolUseId, "Sorry, I couldn't retrieve that clinical data right now. Please try again.");
        }
      });
      session.onEvent("streamComplete", () => {
        socket.emit("streamComplete");
        sessionStates.set(socket.id, "closed");
      });

      socketSessions.set(socket.id, session);
      bedrockClient.initiateBidirectionalStreaming(socket.id);
      sessionStates.set(socket.id, "active");

      callback?.({ success: true });
    } catch (error) {
      console.error("Init error:", error);
      sessionStates.set(socket.id, "closed");
      callback?.({ success: false, error: String(error) });
    }
  });

  socket.on("promptStart", async () => {
    const session = socketSessions.get(socket.id);
    if (!session) return;
    await session.setupSessionAndPromptStart();
  });

  socket.on("systemPrompt", async (data) => {
    const session = socketSessions.get(socket.id);
    if (!session) return;
    await session.setupSystemPrompt(typeof data === "string" ? data : undefined);
  });

  socket.on("audioStart", async () => {
    const session = socketSessions.get(socket.id);
    if (!session) return;
    await session.setupStartAudio();
    socket.emit("audioReady");
  });

  socket.on("audioInput", async (audioData) => {
    const session = socketSessions.get(socket.id);
    if (!session || sessionStates.get(socket.id) !== "active") return;
    const buffer = typeof audioData === "string"
      ? Buffer.from(audioData, "base64")
      : Buffer.from(audioData);
    await session.streamAudio(buffer);
  });

  socket.on("stopAudio", async () => {
    const session = socketSessions.get(socket.id);
    if (!session) return;
    try {
      sessionStates.set(socket.id, "closed");
      await session.endAudioContent();
      await session.endPrompt();
      await session.close();
      socketSessions.delete(socket.id);
      socket.emit("sessionClosed");
    } catch (e) {
      console.error("Stop error:", e);
      bedrockClient.forceCloseSession(socket.id);
      socketSessions.delete(socket.id);
    }
  });

  socket.on("disconnect", async () => {
    console.log(`Client disconnected: ${socket.id}`);
    const session = socketSessions.get(socket.id);
    if (session && bedrockClient.isSessionActive(socket.id)) {
      try {
        await Promise.race([
          (async () => { await session.endAudioContent(); await session.endPrompt(); await session.close(); })(),
          new Promise((_, rej) => setTimeout(() => rej("timeout"), 3000)),
        ]);
      } catch {
        bedrockClient.forceCloseSession(socket.id);
      }
    }
    socketSessions.delete(socket.id);
    sessionStates.delete(socket.id);
  });
});

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`Nova Sonic server running on http://localhost:${PORT}`);
  console.log(`Open http://localhost:${PORT} to test voice interaction`);
});

process.on("SIGINT", async () => {
  console.log("Shutting down...");
  for (const sid of bedrockClient.getActiveSessions()) {
    try { await bedrockClient.closeSession(sid); } catch { bedrockClient.forceCloseSession(sid); }
  }
  process.exit(0);
});
