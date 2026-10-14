/**
 * VoiceMode — Nova Sonic voice interface for Connected Care.
 * Simple approach: collect complete turns, then add to history.
 * No charts unless explicitly requested. No duplicate text.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import Box from '@cloudscape-design/components/box';
import Button from '@cloudscape-design/components/button';
import SpaceBetween from '@cloudscape-design/components/space-between';
import StatusIndicator from '@cloudscape-design/components/status-indicator';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import { io, Socket } from 'socket.io-client';

type VoiceState = 'idle' | 'connecting' | 'listening' | 'thinking' | 'speaking';

interface VoiceEntry {
  role: 'user' | 'agent' | 'system';
  text: string;
}

const NOVA_SONIC_URL = import.meta.env.VITE_NOVA_SONIC_URL || 'http://localhost:3001';

interface VoiceModeProps {
  agentId: string;
  agentLabel: string;
}

export default function VoiceMode({ agentLabel }: VoiceModeProps) {
  const [state, setState] = useState<VoiceState>('idle');
  const [history, setHistory] = useState<VoiceEntry[]>([]);
  const [liveText, setLiveText] = useState('');
  const [liveRole, setLiveRole] = useState<'user' | 'agent'>('user');
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<Socket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const playbackQueueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const isStreamingRef = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Buffers — only committed to history on turn boundaries
  const userBufferRef = useRef('');
  const agentBufferRef = useRef('');
  const lastCommittedRoleRef = useRef<'user' | 'agent' | ''>('');
  const agentCommittedThisTurnRef = useRef(false); // Prevents duplicate agent commits

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [history, liveText]);

  useEffect(() => () => { stopStreaming(); }, []);

  // --- Audio playback ---
  const playAudioChunk = useCallback((base64Audio: string) => {
    if (!playbackContextRef.current) {
      playbackContextRef.current = new AudioContext({ sampleRate: 24000 });
    }
    const ctx = playbackContextRef.current;
    if (ctx.state === 'suspended') ctx.resume();
    const bin = atob(base64Audio);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const dv = new DataView(bytes.buffer);
    const n = bytes.length / 2;
    const f32 = new Float32Array(n);
    for (let i = 0; i < n; i++) f32[i] = dv.getInt16(i * 2, true) / 32768.0;
    const buf = ctx.createBuffer(1, f32.length, 24000);
    buf.getChannelData(0).set(f32);
    playbackQueueRef.current.push(buf);
    if (!isPlayingRef.current) playNext();
  }, []);

  const playNext = useCallback(() => {
    if (playbackQueueRef.current.length === 0) { isPlayingRef.current = false; return; }
    isPlayingRef.current = true;
    const buf = playbackQueueRef.current.shift()!;
    const src = playbackContextRef.current!.createBufferSource();
    src.buffer = buf;
    src.connect(playbackContextRef.current!.destination);
    src.onended = () => playNext();
    src.start();
  }, []);

  // --- Commit helpers ---
  const commitUser = useCallback(() => {
    const text = userBufferRef.current.trim();
    if (text && lastCommittedRoleRef.current !== 'user') {
      setHistory(prev => [...prev, { role: 'user', text }]);
      lastCommittedRoleRef.current = 'user';
      agentCommittedThisTurnRef.current = false; // New user turn — allow next agent commit
    }
    userBufferRef.current = '';
    setLiveText('');
  }, []);

  const commitAgent = useCallback(() => {
    const text = agentBufferRef.current.trim();
    if (text) {
      // Deduplicate: only add if the last agent entry doesn't have the same text
      setHistory(prev => {
        const lastAgent = [...prev].reverse().find(e => e.role === 'agent');
        if (lastAgent && lastAgent.text === text) return prev; // Skip duplicate
        return [...prev, { role: 'agent', text }];
      });
      lastCommittedRoleRef.current = 'agent';
    }
    agentBufferRef.current = '';
    setLiveText('');
  }, []);

  // --- Start streaming ---
  const startStreaming = useCallback(async () => {
    setError(null);
    setState('connecting');
    setLiveText('');
    userBufferRef.current = '';
    agentBufferRef.current = '';
    lastCommittedRoleRef.current = '';
    agentCommittedThisTurnRef.current = false;

    try {
      const socket = io(NOVA_SONIC_URL, { transports: ['polling', 'websocket'] });
      socketRef.current = socket;

      socket.on('connect', () => console.log('Nova Sonic connected'));

      // TEXT OUTPUT — accumulate into buffers, show live
      socket.on('textOutput', (data: any) => {
        const text = data?.content || '';
        const role = data?.role;
        if (role === 'USER') {
          userBufferRef.current += text;
          setLiveText(userBufferRef.current);
          setLiveRole('user');
        } else if (role === 'ASSISTANT') {
          agentBufferRef.current += text;
          setLiveText(agentBufferRef.current);
          setLiveRole('agent');
        }
      });

      // AUDIO — play it
      socket.on('audioOutput', (data: any) => {
        if (data?.content) {
          setState('speaking');
          playAudioChunk(data.content);
        }
      });

      // CONTENT START — signals a new content block
      socket.on('contentStart', (data: any) => {
        if (data?.type === 'TEXT' && data?.role === 'USER') {
          // Commit any pending agent response before new user turn
          if (agentBufferRef.current.trim()) commitAgent();
          userBufferRef.current = '';
          setLiveText('');
          setLiveRole('user');
        }
        if (data?.type === 'TEXT' && data?.role === 'ASSISTANT') {
          // Commit user text, but DON'T commit or reset agent buffer
          // — accumulate all assistant text blocks into one bubble
          if (userBufferRef.current.trim()) commitUser();
          setLiveRole('agent');
          setState('speaking');
        }
      });

      // CONTENT END — signals end of a content block
      socket.on('contentEnd', (data: any) => {
        if (data?.type === 'TEXT' && data?.role === 'USER') {
          commitUser();
        }
        // Don't commit agent text on TEXT contentEnd — wait for AUDIO end
        // This prevents broken bubbles from multiple text blocks
        if (data?.type === 'AUDIO') {
          // Audio done = agent turn complete. Commit the full agent response.
          if (agentBufferRef.current.trim()) commitAgent();
          setTimeout(() => {
            if (isStreamingRef.current) setState('listening');
          }, 500);
        }
      });

      // TOOL USE — show system message
      socket.on('toolUse', () => {
        setState('thinking');
        // Commit any pending user text first
        if (userBufferRef.current.trim()) commitUser();
        setHistory(prev => [...prev, { role: 'system', text: 'Querying clinical data...' }]);
      });

      socket.on('error', (data: any) => {
        console.error('Nova Sonic error:', data);
        setError(typeof data === 'string' ? data : data?.message || 'Voice error');
      });

      socket.on('audioReady', () => {
        setState('listening');
        isStreamingRef.current = true;
      });

      socket.on('sessionClosed', () => {
        setState('idle');
        isStreamingRef.current = false;
      });

      // Initialize
      socket.emit('initializeConnection', (resp: any) => {
        if (!resp?.success) { setError('Failed to connect'); setState('idle'); return; }
        setupAudioCapture(socket);
        socket.emit('promptStart');
        socket.emit('systemPrompt');
        socket.emit('audioStart');
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
      setState('idle');
    }
  }, [playAudioChunk, commitUser, commitAgent]);

  const setupAudioCapture = async (socket: Socket) => {
    const ctx = new AudioContext({ sampleRate: 16000 });
    audioContextRef.current = ctx;
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
    mediaStreamRef.current = stream;
    const source = ctx.createMediaStreamSource(stream);
    const processor = ctx.createScriptProcessor(2048, 1, 1);
    processor.onaudioprocess = (e) => {
      if (!isStreamingRef.current) return;
      const f32 = e.inputBuffer.getChannelData(0);
      const i16 = new Int16Array(f32.length);
      for (let i = 0; i < f32.length; i++) i16[i] = Math.max(-32768, Math.min(32767, Math.round(f32[i] * 32768)));
      socket.emit('audioInput', btoa(String.fromCharCode(...new Uint8Array(i16.buffer))));
    };
    source.connect(processor);
    processor.connect(ctx.destination);
  };

  const stopStreaming = useCallback(() => {
    isStreamingRef.current = false;
    mediaStreamRef.current?.getTracks().forEach(t => t.stop());
    mediaStreamRef.current = null;
    audioContextRef.current?.close();
    audioContextRef.current = null;
    socketRef.current?.emit('stopAudio');
    socketRef.current?.disconnect();
    socketRef.current = null;
    playbackQueueRef.current = [];
    isPlayingRef.current = false;
    // Commit any pending text
    if (userBufferRef.current.trim()) commitUser();
    if (agentBufferRef.current.trim()) commitAgent();
    setState('idle');
  }, [commitUser, commitAgent]);

  // --- Render ---
  const stateConfig: Record<VoiceState, { color: string; label: string; icon: string }> = {
    idle: { color: '#6b7280', label: 'Tap to start', icon: '🎤' },
    connecting: { color: '#f59e0b', label: 'Connecting...', icon: '⏳' },
    listening: { color: '#ef4444', label: 'Listening...', icon: '🔴' },
    thinking: { color: '#8b5cf6', label: 'Querying data...', icon: '🧠' },
    speaking: { color: '#10b981', label: 'Speaking...', icon: '🔊' },
  };
  const cfg = stateConfig[state];

  return (
    <Container fitHeight disableContentPaddings
      header={<Header variant="h2" description="Powered by Amazon Nova Sonic">{agentLabel} — Voice Mode</Header>}
    >
      <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 280px)' }}>
        {/* History */}
        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
          <SpaceBetween size="s">
            {history.length === 0 && state === 'idle' && (
              <Box textAlign="center" padding="xxl" color="text-body-secondary">
                Tap the microphone to start a voice conversation with Ana.
              </Box>
            )}
            {history.map((entry, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: entry.role === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '85%', padding: '10px 16px', borderRadius: 14,
                  background: entry.role === 'user'
                    ? '#0972d3'
                    : entry.role === 'system' ? '#f0f0f0' : '#37475a',
                  color: entry.role === 'system' ? '#687078' : '#fff',
                  fontSize: entry.role === 'system' ? '0.8em' : '0.93em',
                  fontStyle: entry.role === 'system' ? 'italic' : 'normal',
                  lineHeight: 1.5,
                }}>
                  {entry.text}
                </div>
              </div>
            ))}
            {/* Live text indicator */}
            {liveText && (
              <div style={{ display: 'flex', justifyContent: liveRole === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '85%', padding: '10px 16px', borderRadius: 14,
                  background: liveRole === 'user' ? '#0972d3' : '#37475a',
                  color: '#fff', fontSize: '0.93em', lineHeight: 1.5, opacity: 0.6,
                }}>
                  {liveText}{liveRole === 'user' ? '...' : ''}
                </div>
              </div>
            )}
          </SpaceBetween>
        </div>

        {/* Error */}
        {error && <div style={{ padding: '8px 20px' }}><StatusIndicator type="error">{error}</StatusIndicator></div>}

        {/* Controls */}
        <div style={{
          padding: '16px', borderTop: '1px solid #d5dbdb',
          display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 16,
        }}>
          <button
            onClick={state === 'idle' ? startStreaming : stopStreaming}
            aria-label={state === 'idle' ? 'Start voice' : 'Stop voice'}
            style={{
              width: 68, height: 68, borderRadius: '50%',
              border: `3px solid ${cfg.color}`,
              background: state === 'idle' ? 'transparent' : `${cfg.color}15`,
              cursor: 'pointer', fontSize: '1.8em',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              animation: state === 'listening' ? 'pulse-mic 1.5s ease-in-out infinite' : 'none',
            }}
          >
            {cfg.icon}
          </button>
          <div style={{ textAlign: 'center' }}>
            <Box variant="small" color="text-body-secondary">{cfg.label}</Box>
            {state !== 'idle' && <Button variant="link" onClick={stopStreaming}>End</Button>}
          </div>
        </div>
      </div>
      <style>{`@keyframes pulse-mic { 0%,100% { transform: scale(1); } 50% { transform: scale(1.08); } }`}</style>
    </Container>
  );
}
