import { NextRequest } from 'next/server';
import {
  BedrockAgentRuntimeClient,
  InvokeInlineAgentCommand
} from '@aws-sdk/client-bedrock-agent-runtime';
import {
  BedrockAgentClient,
  ListAgentAliasesCommand,
  GetAgentAliasCommand
} from '@aws-sdk/client-bedrock-agent';
import { a, p } from 'framer-motion/client';

import dotenv from "dotenv";
dotenv.config();

const REGION: string = process.env.AWS_REGION


const runtimeClient = new BedrockAgentRuntimeClient({ region: REGION });
const controlClient = new BedrockAgentClient({ region: REGION });

export async function getAgentAliasArnByName(agentId) {
  try {
    const listCommand = new ListAgentAliasesCommand({ agentId });
    const listResponse = await controlClient.send(listCommand);
    const latestAlias = listResponse.agentAliasSummaries?.sort(
      (a, b) => new Date(b.updatedAt) - new Date(a.updatedAt)
    )[0];
    if (!latestAlias) return null;

    const getCommand = new GetAgentAliasCommand({
      agentId,
      agentAliasId: latestAlias.agentAliasId
    });
    const getResponse = await controlClient.send(getCommand);
    return getResponse.agentAlias?.agentAliasArn;
  } catch (error) {
    console.error('Error getting alias ARN:', error);
    throw error;
  }
}

export async function invokeInlineAgentHelper(requestParams) {
  try {
    const command = new InvokeInlineAgentCommand(requestParams);
    const response = await runtimeClient.send(command);
    return response;
  } catch (error) {
    console.error('Error invoking inline agent:', error);
    throw error;
  }
}

function extractAndRemoveImageUrls(text: string): [string[], string] {
  const imageUrlRegex = /(https:\/\/[^\s"']+\.(?:png|jpg|jpeg|webp)[^\s"']*)/gi;
  const imageUrls = [...text.matchAll(imageUrlRegex)].map(match => match[1]);
  const cleanedText = text.replace(imageUrlRegex, '').trim();
  return [imageUrls, cleanedText];
}


function chunkTextSafely(text: string, size: number = 3000): string[] {
  const chunks = [];
  for (let i = 0; i < text.length; i += size) {
    let chunk = text.slice(i, i + size).trim();
    if (i > 0) chunk = '... ' + chunk;            
    if (i + size < text.length) chunk += ' ...';  
    chunks.push(chunk);
  }
  return chunks;
}


export async function POST(req: NextRequest) {
  const encoder = new TextEncoder();
  const { message, agents, agent_instruction, requestId } = await req.json();
  const sessionId = requestId || `session-${Date.now()}`;

  const log = (msg: string, ...args: any[]) => {
    console.log(`[${sessionId}] ${msg}`, ...args);
  };

  log('Received chat request', { message, agent_instruction, agentCount: agents.length });

  try {
    const foundationModel = 'us.anthropic.claude-3-5-sonnet-20241022-v2:0';

    log('Resolving agent aliases...');
    const collaboratorConfigurations = await Promise.all(
      agents.map(async (agent) => {
        const agentAliasArn = await getAgentAliasArnByName(agent.id || agent.name);
        log(`Resolved agent "${agent.name}" to ARN`, agentAliasArn);
        return {
          collaboratorName: agent.name,
          collaboratorInstruction: agent_instruction,
          agentAliasArn,
          relayConversationHistory: 'TO_COLLABORATOR'
        };
      })
    );

    const requestParams = {
      foundationModel,
      instruction: agent_instruction,
      sessionId,
      endSession: false,
      enableTrace: true,
      agentCollaboration: 'SUPERVISOR_ROUTER',
      inputText: message,
      collaboratorConfigurations,
      inlineSessionState: {
        promptSessionAttributes: {
          today: new Date().toISOString().split('T')[0],
        },
      },
    };

    log('Invoking agent collaboration', requestParams);
    const result = await invokeInlineAgentHelper(requestParams);
    log('Agent invocation started');

    const stream = new ReadableStream({
      async start(controller) {
        let finalMessage = '';
        let imageUrls: string[] = [];
        let step = 1;
        let inputTokens = 0;
        let outputTokens = 0;

        try {
          for await (const event of result.completion) {
  
            const agentId = event.trace?.agentId || 'unknown-agent';
  
            if (event.chunk?.bytes) {
              const text = new TextDecoder('utf-8').decode(event.chunk.bytes);
              finalMessage += text;
              log('Received chunk', { text });
  
              controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'chunk', data: text })}\n\n`));
            }
  
            if (event.trace?.trace?.orchestrationTrace) {
              const trace = event.trace.trace.orchestrationTrace;
              log('Processing orchestration trace', trace);
  
              const toolInput = trace.invocationInput?.actionGroupInvocationInput;
              if (toolInput) {
                log('Tool input received', toolInput);
  
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({
                  type: 'tool',
                  step,
                  agent: agentId,
                  function: toolInput.function || '',
                  apiPath: toolInput.apiPath || '',
                  executionType: toolInput.executionType || '',
                  parameters: toolInput.parameters || []
                })}\n\n`));
  
                // if(toolInput.executionType === 'RETURN_CONTROL') {
                //   if(toolInput.function === 'showImage'){
                //     imageUrl = toolInput.parameters[0].value;
                //     break;
                //   }
                // } else {
                //   controller.enqueue(encoder.encode(`data: ${JSON.stringify({
                //     type: 'tool',
                //     step,
                //     agent: agentId,
                //     function: toolInput.function || '',
                //     apiPath: toolInput.apiPath || '',
                //     executionType: toolInput.executionType || '',
                //     parameters: toolInput.parameters || []
                //   })}\n\n`));
                // }
                step++;
              }
  
              if (trace.rationale?.text) {
                log('Rationale received', trace.rationale.text);
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({
                  type: 'rationale',
                  step,
                  agent: "Model",
                  text: trace.rationale.text
                })}\n\n`));
                step++;
              }
  
              const agentColab = trace.invocationInput?.agentCollaboratorInvocationInput;
              if (agentColab) {
                log(`Agent collaborator input from "${agentColab.agentCollaboratorName}"`, agentColab.input.text);
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({
                  type: 'agent-collaborator',
                  step,
                  agent: agentColab.agentCollaboratorName,
                  text: agentColab.input.text
                })}\n\n`));
                step++;
              }
  
              const obsTool = trace.observation?.actionGroupInvocationOutput?.text;
              if (obsTool) {
                log(`Tool observation from "${agentId}"`, obsTool);
  
                const [extractedUrls, cleanedText] = extractAndRemoveImageUrls(obsTool);
                if (extractedUrls.length > 0) {
                  imageUrls.push(...extractedUrls); // ✅ flattening
                  log('Image URLs captured from observation text', extractedUrls);
                }

                const obs_chunks = chunkTextSafely(cleanedText, 4000);
                for (const obs_chunk of obs_chunks) {
                  controller.enqueue(encoder.encode(`data: ${JSON.stringify({
                    type: 'observation',
                    step,
                    agent: agentId,
                    text: obs_chunk
                  })}\n\n`));
                }
                step++;
              }

              const kbOutput = trace.observation?.knowledgeBaseLookupOutput;
              if (kbOutput?.retrievedReferences?.length) {
                log('Knowledge Base lookup retrieved references', kbOutput.retrievedReferences);
              
                for (const reference of kbOutput.retrievedReferences) {
                  console.log('Reference Object:', JSON.stringify(reference, null, 2));
              
                  const metadata = reference.metadata || {};
                  const sourceUri = metadata['x-amz-bedrock-kb-source-uri'] || '';
                  const contentText = reference.content?.text || '';
              
                  if (contentText) {
                    const combinedText = `${contentText}\n\nReference: ${sourceUri}`;
                    controller.enqueue(encoder.encode(`data: ${JSON.stringify({
                      type: 'knowledge-base',  
                      step,
                      agent: agentId,
                      text: combinedText
                    })}\n\n`));
                  }
                }
                step++;
                
              }                            
              const finalResp = trace.observation?.finalResponse;
              if (finalResp?.text) {
                log(`Final response from "${agentId}"`, finalResp.text);
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({
                  type: 'observation',
                  step,
                  agent: agentId,
                  text: finalResp.text
                })}\n\n`));
                step++;
              }
  
              const usage = trace.modelInvocationOutput?.metadata?.usage;
              if (usage) {
                inputTokens += usage.inputTokens || 0;
                outputTokens += usage.outputTokens || 0;
                log('Model usage stats', usage);
              }
  
              const attachment = finalResp?.attachments?.[0];
              if (attachment?.url) {
                imageUrls.push(attachment.url);
                log('Image URL captured from response', attachment.url);
              }
            }
          }
  
        } catch (streamError) {
          log('Error during streaming', streamError);
          
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({
            type: 'error',
            step,
            agent: 'Model',
            text: streamError + ' ' + requestId || 'An error occurred during streaming.',
          })}\n\n`));

          finalMessage = "Sorry ! I am having trouble processing your request. Please try again later.";

        }finally{

          const endPayload = {
            type: 'end',
            finalMessage,
            images: imageUrls,
            requestId: sessionId
          };
          log('Streaming final message and closing connection', endPayload);
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(endPayload)}\n\n`));
          controller.close();
        }
      }
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'Transfer-Encoding': 'chunked'
      }
    });
  } catch (err) {
    log('Error during processing', err);
    return new Response('Internal Server Error', { status: 500 });
  }
}


