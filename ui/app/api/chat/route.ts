import { NextResponse } from 'next/server';
import { 
  BedrockAgentRuntimeClient, 
  InvokeInlineAgentCommand 
} from "@aws-sdk/client-bedrock-agent-runtime";
import { 
  BedrockAgentClient, 
  ListAgentAliasesCommand,
  GetAgentAliasCommand
} from "@aws-sdk/client-bedrock-agent";

import dotenv from "dotenv";
dotenv.config();

const REGION: string = process.env.AWS_REGION


const runtimeClient = new BedrockAgentRuntimeClient({ region: REGION });
const controlClient = new BedrockAgentClient({ region: REGION });

export async function getAgentAliasArnByName(agentId: any) {
  try {
    const listCommand = new ListAgentAliasesCommand({ agentId });
    const listResponse = await controlClient.send(listCommand);
    const latestAlias = listResponse.agentAliasSummaries?.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))[0];
    if (!latestAlias) {
      console.warn(`No aliases found for agentId: ${agentId}`);
      return null;
    }

    const getCommand = new GetAgentAliasCommand({
      agentId,
      agentAliasId: latestAlias.agentAliasId
    });
    const getResponse = await controlClient.send(getCommand);
    return getResponse.agentAlias?.agentAliasArn;
  } catch (error) {
    console.error(`Error fetching alias ARN for agent ${agentId}:`, error);
    return null;
  }
}

export async function invokeInlineAgentHelper(requestParams, traceLevel = "core") {
  try {
    const input = {
      ...requestParams
    };

    const command = new InvokeInlineAgentCommand(input);
    const response = await runtimeClient.send(command);

    return response;
  } catch (error) {
    console.error("Error invoking inline agent:", error);
    throw error;
  }
}

export async function POST(req) {
  try {
    const { message, agents, agent_instruction } = await req.json();

    console.log("Agents:", agents);
    console.log("Instruction:", agent_instruction);

    const foundationModel = "us.anthropic.claude-3-5-sonnet-20241022-v2:0";
    const sessionId = `session-${Date.now()}`;

    const collaboratorConfigurations = await Promise.all(
      agents.map(async (agent) => {
        const agentAliasArn = await getAgentAliasArnByName(agent.id || agent.name);
        return {
          collaboratorName: agent.name,
          collaboratorInstruction: agent_instruction,
          agentAliasArn,
          relayConversationHistory: "TO_COLLABORATOR"
        };
      })
    );

    const requestParams = {
      foundationModel,
      instruction: agent_instruction,
      sessionId,
      endSession: false,
      enableTrace: true,
      agentCollaboration: "SUPERVISOR_ROUTER",
      inputText: message,
      collaboratorConfigurations
    };

    const result = await invokeInlineAgentHelper(requestParams);

    const agentNames = agents.map((a) => a.name).join(', ');
    let reply = "";
    let trace = "";

    for await (const event of result.completion) {
      if (event.chunk?.bytes) {
        reply += Buffer.from(event.chunk.bytes).toString("utf-8");
      }
      if (event.trace?.trace?.orchestrationTrace) {
        trace += JSON.stringify(event.trace.trace.orchestrationTrace, null, 2);
      }
    }

    console.log("*************************");
    console.log(reply);

    return new Response(JSON.stringify({ reply, trace }), {
      headers: {
        "Content-Type": "application/json"
      },
      status: 200
    });
  } catch (err) {
    console.error("POST /invoke-inline-agent error:", err);
    return NextResponse.json({ error: "Failed to complete the chat message." }, { status: 500 });
  }
}
