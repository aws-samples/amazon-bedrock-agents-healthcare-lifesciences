"use client";

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';

interface Message {
  sender: string;
  text: string;
  timestamp: string;
  trace?: string;
}

interface Agent {
  name: string;
  image?: string;
  icon?: string;
  agentCollaboration: 'SUPERVISOR' | 'DISABLED';
  collaborators?: string[];
}

export default function ChatPage() {
  const [selectedAgents, setSelectedAgents] = useState<Agent[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [instruction, setInstruction] = useState('You are a medical research assistant AI specializing in cancer biomarker analysis and discovery. Coordinate sub-agents to fulfill user questions.');
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatRequestIdRef = useRef(`req-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`);
  const isSupervisorChat = selectedAgents.some(agent => 
    agent.agentCollaboration === 'SUPERVISOR' || agent.agentCollaboration === 'SUPERVISOR_ROUTER'
  );
  const [alwaysCollapseTraces, setAlwaysCollapseTraces] = useState(false);

  const formatTime = (timestamp) => new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const sendMessage = async () => {
    if (!input.trim()) return;
    const timestamp = new Date().toISOString();
    const userMessage = { sender: 'You', text: input, timestamp };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsProcessing(true);

    // Insert placeholder trace message immediately
    const chat_request_id = chatRequestIdRef.current;
    setMessages((prev) => [
      ...prev,
      {
        sender: 'AI Agent',
        text: '',
        trace: [{ type: 'placeholder', text: 'Trace loading for chat id : ' + chat_request_id }],
        expandTrace: true
      }
    ]);

    
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message: input, 
        agents: selectedAgents, 
        agent_instruction: instruction,
        requestId : chat_request_id
      })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let finalText = '';
    let stepCount = 0;

    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });

      let boundary = buffer.indexOf('\n\n');
      while (boundary !== -1) {
        const fullChunk = buffer.slice(0, boundary).trim();
        buffer = buffer.slice(boundary + 2);

        if (fullChunk.startsWith('data: ')) {
          try {
            const parsed = JSON.parse(fullChunk.slice(6));
  
            if (parsed.type === 'chunk') {
              finalText += parsed.data;
              setMessages((prev) => {
                const lastMsg = prev[prev.length - 1];
                if (!lastMsg || lastMsg.sender !== 'AI Agent') {
                  return [...prev, { sender: 'AI Agent', text: parsed.data, trace: [{ type: 'placeholder', text: 'Trace loading...' }], expandTrace: true }];
                }
                const updated = [...prev];
                updated[updated.length - 1].text += parsed.data;
                return updated;
              });
            }
  
            else if (['rationale', 'tool', 'observation', 'agent-collaborator', 'knowledge-base', 'error'].includes(parsed.type)) {
              const step = parsed.step !== undefined ? parsed.step : stepCount + 1;
              stepCount = step;
              const agent = parsed.agent || parsed.data?.agent || 'unknown-agent';
              const traceStep = { ...parsed, step, agent };
              setMessages((prev) => {
                const updated = [...prev];
                const lastMsg = updated[updated.length - 1];
                if (!lastMsg || lastMsg.sender !== 'AI Agent') {
                updated.push({ sender: 'AI Agent', text: '', trace: [traceStep], expandTrace: true });
              } else {
                const existing = lastMsg.trace || [];
                const alreadyExists = existing.some(t =>
                  t.step === traceStep.step &&
                  t.type === traceStep.type &&
                  t.text === traceStep.text
                );
                if (!alreadyExists) {
                  lastMsg.trace = [...existing.filter(t => t.type !== 'placeholder'), traceStep];
  lastMsg.trace.push(existing.find(t => t.type === 'placeholder'));
                  }
                  lastMsg.expandTrace = true;
                }
                return updated;
              });
            }
            else if (parsed.type === 'end') {
              setMessages((prev) => {
                const updated = [...prev];
                const lastMsg = updated[updated.length - 1];
                if (lastMsg && lastMsg.sender === 'AI Agent') {
                lastMsg.text = parsed.finalMessage || finalText;
                lastMsg.timestamp = new Date().toISOString();
                lastMsg.images = parsed.images || (parsed.image ? [parsed.image] : []);
                lastMsg.trace = (lastMsg.trace || []).filter(t => t.type !== 'placeholder');
                  lastMsg.expandTrace = true;
                }
                return updated;
              });
              setIsProcessing(false);
            }
  
          } catch (e) {
            console.error('Error parsing SSE:', e);
            console.error(fullChunk);
          }
        }
        
        boundary = buffer.indexOf('\n\n');

      }  
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const stored = localStorage.getItem('selectedAgents');
    if (stored) setSelectedAgents(JSON.parse(stored));
    const storedInstruction = localStorage.getItem('agent_instruction');
    if (storedInstruction) setInstruction(storedInstruction);
    const storedMessages = localStorage.getItem('chatMessages');
    if (storedMessages) setMessages(JSON.parse(storedMessages));
  }, []);

  // useEffect(() => {
  //   const storedChatId = localStorage.getItem('chat_request_id');
  //   if (storedChatId) {
  //     setChatRequestId(storedChatId);
  //   } else {
  //     const newId = `req-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
  //     setChatRequestId(newId);
  //     localStorage.setItem('chat_request_id', newId);
  //   }
  // }, [messages]);

  return (
    <div className="min-h-screen flex flex-col bg-gray-100">
      <header className="bg-white shadow p-4 text-center text-2xl font-bold">
        <Image src="/images/aws-logo.svg" alt="AWS Logo" width={150} height={50} className="mx-auto mb-2" />
        Chat with Selected Agents
      </header>

      <div className="flex flex-1 p-4 gap-4 relative">
        <aside className="w-64 bg-white p-4 rounded shadow flex flex-col justify-between">
          <div>
          <h3 className="text-lg font-semibold mb-4">Selected Agents</h3>
          {selectedAgents.map((agent, idx) => (
          <div key={idx} className="mb-4">
            <div className="flex items-center mb-1">
              <Image
                src={agent.image || agent.icon}
                alt="Agent Icon"
                width={40}
                height={40}
                className="rounded-full mr-2"
              />
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{agent.name}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border shadow-sm 
                      ${
                      isSupervisorChat
                        ? 'bg-purple-100 text-purple-800 border-purple-300'
                        : 'bg-gray-100 text-gray-700 border-gray-300'
                    }`}
                  >
                    {isSupervisorChat ? 'Supervisor' : 'Individual'}
                  </span>

                </div>
              </div>
            </div>

    {/* Collaborators */}
    {isSupervisorChat &&
      Array.isArray(agent.collaborators) &&
      agent.collaborators.length > 0 && (
        <div className="ml-10 mt-2 space-y-2 border-l pl-4 border-blue-300">
          {agent.collaborators.map((name, cIdx) => (
            <div key={cIdx} className="flex items-center gap-2">
              <span className="text-blue-600 text-sm">👥</span>
              <span className="text-sm text-gray-700">{name}</span>
            </div>
          ))}
        </div>
    )}
  </div>
))}


          </div>
          <div className="mt-4">
            <button
              onClick={() => {
                setMessages([]);
                localStorage.removeItem('chatMessages');
                chatRequestIdRef.current = `req-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
              }}              
              className="w-full text-center bg-red-500 hover:bg-red-600 text-white py-2 px-4 rounded-lg shadow-md font-semibold transition duration-200 mb-3"
            >
              🗑️ Clear Chat
            </button>
            <a
            href="/"
            onClick={() => {
              localStorage.removeItem('chatMessages');
            }}
            className="block text-center bg-gradient-to-r from-blue-500 to-blue-700 hover:from-blue-600 hover:to-blue-800 text-white py-2 px-4 rounded-lg shadow-lg font-semibold tracking-wide transition-all duration-300 ease-in-out w-full"
          >
            ← Back to Catalog
          </a>

          </div>
        </aside>

        <main className="flex flex-1 flex-col bg-white rounded shadow">
        <div className="p-2 border-b text-right text-xs text-gray-500">
          <details open>
            <summary className="cursor-pointer underline inline-block">Edit Agent Instructions</summary>
            <textarea
              className={`w-full border rounded p-2 mt-2 ${isSupervisorChat ? 'bg-gray-100 cursor-not-allowed' : 'border-gray-300'}`}
              placeholder="Enter shared instruction for agent collaboration..."
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              rows={3}
              disabled={isSupervisorChat}
            />
            {isSupervisorChat && (
              <p className="text-red-500 text-xs mt-1">🔒 Instruction is locked while using a Supervisor agent.</p>
            )}
          </details>
        </div>
        <div className="p-2 border-b flex items-center justify-end gap-3 bg-gray-50">
        <label className="flex items-center cursor-pointer">
          <div className="relative">
            <input
              type="checkbox"
              checked={alwaysCollapseTraces}
              onChange={(e) => setAlwaysCollapseTraces(e.target.checked)}
              className="sr-only"
            />
            <div className="w-11 h-6 bg-gray-300 rounded-full shadow-inner"></div>
            <div
              className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transform transition-transform ${alwaysCollapseTraces ? 'translate-x-5' : ''}`}
            ></div>
          </div>
          <span className="ml-3 text-sm font-semibold text-gray-700">
            {alwaysCollapseTraces ? 'Collapsed Traces' : 'Expanded Traces'}
          </span>
        </label>
      </div>
          <div className="flex-1 p-4 overflow-y-auto" id="chat-messages">
            {messages.map((msg, index) => (
              <div key={index} className="mb-4">
                {msg.trace && (
                  <details open={!alwaysCollapseTraces && msg.expandTrace} className="mt-3 border rounded-md bg-gray-50 p-3">
                    <summary className="cursor-pointer font-semibold text-blue-700">🧵 Trace Steps</summary>
                    <div className="mt-3 space-y-3">
                    {msg.trace.map((step, stepIdx) => (
                    <details key={stepIdx} open className="border rounded-lg bg-white shadow-sm p-3">
                      <summary className="cursor-pointer font-semibold text-blue-700 mb-1 text-sm">
                        ▶️ Step {step.step}
                      </summary>
                      <div className="mt-2 text-sm">
                        {step.type === 'rationale' && (
                          <div className="break-all whitespace-pre-wrap">
                            <span className="font-semibold">💡 Rationale:</span>{' '}
                            <span className="block">{step.text}</span>
                          </div>
                        )}
                        {step.type === 'agent-collaborator' && (
                          <div><span className="font-semibold">👤➡️👤 Agent - {step.agent}:</span> {step.text}</div>
                        )}
                        {step.type === 'tool' && (
                          <div>
                            <div><span className="font-semibold">🧰 Tool:</span> {step.function || step.apiPath || 'Unknown'}</div>
                            <div><span className="font-semibold">Execution:</span> {step.executionType}</div>
                          </div>
                        )}
                        {step.type === 'observation' && (
                        <div className="max-w-full break-all whitespace-pre-wrap">
                          <span className="font-semibold">📝 Observation:</span>
                          <span className="block">{step.text}</span>
                        </div>
                        )}
                        {step.type === 'knowledge-base' && (
                          <div className="max-w-full break-all whitespace-pre-wrap mt-4 p-3 border rounded-md bg-gray-50">
                            <span className="font-semibold">📚 Knowledge Base Result:</span>
                            <span className="block">{step.text}</span>
                          </div>
                        )}
                        {step.type === 'placeholder' && (
                          <div className="italic text-gray-400">⏳ {step.text}</div>
                        )}
                        {step.type === 'error' && (() => {
                          console.error('Agent execution error:', step.message || step.text);
                          return (
                            <div className="block font-medium">
                              Something went wrong during agent execution.
                            </div>
                          );
                        })()}
                      </div>
                    </details>
                  ))}

                    </div>
                  </details>
                )}
                {msg.text && (
                  <p className="mt-3 break-all whitespace-pre-wrap">
                    <strong>{msg.sender}:</strong> {msg.text}
                    <span className="ml-2 text-xs text-gray-400">{formatTime(msg.timestamp)}</span>
                  </p>
                )}
                {msg.images && msg.images.length > 0 && (
                <div className="mt-2 space-y-2">
                  {msg.images.map((url, idx) => (
                    <Image
                      key={idx}
                      src={url}
                      alt={`Generated Visual ${idx + 1}`}
                      width={800}
                      height={600}
                      className="rounded shadow border"
                      unoptimized
                    />
                  ))}
                </div>
              )}
              </div>
            ))}
            {isProcessing && (
              <div className="mb-4 animate-pulse text-blue-600 italic">Waiting for response...</div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="border-t border-gray-200 p-3 flex">
            <input
              type="text"
              className="flex-1 border border-gray-300 rounded px-3 py-2"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            />
            <button
              className="ml-3 bg-blue-600 text-white px-4 py-2 rounded"
              onClick={sendMessage}
            >
              Send
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}