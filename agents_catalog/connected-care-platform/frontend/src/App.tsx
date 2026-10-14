import { useState, useRef, useEffect, useCallback } from 'react';
import '@cloudscape-design/global-styles/index.css';
import { applyMode, Mode } from '@cloudscape-design/global-styles';

import AppLayout from '@cloudscape-design/components/app-layout';
import SideNavigation from '@cloudscape-design/components/side-navigation';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Box from '@cloudscape-design/components/box';
import PromptInput from '@cloudscape-design/components/prompt-input';
import Spinner from '@cloudscape-design/components/spinner';
import StatusIndicator from '@cloudscape-design/components/status-indicator';
import Toggle from '@cloudscape-design/components/toggle';
import Button from '@cloudscape-design/components/button';
import ChatBubble from '@cloudscape-design/chat-components/chat-bubble';
import Avatar from '@cloudscape-design/chat-components/avatar';

import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import VitalsChart from './VitalsChart';
import MedTechChart, { extractMedTechChartData, MedTechChartData } from './MedTechCharts';
import ArchitecturePage from './ArchitecturePage';
import WorkflowsPage from './WorkflowsPage';
import NotificationBell from './NotificationBell';
import VoiceMode from './VoiceMode';
import LoginPage from './LoginPage';
import PatientMemoryPanel from './PatientMemoryPanel';
import DeviceDigitalTwin from './DeviceDigitalTwin';
import { getCurrentUser, signOut, signedFetch, fetchUserAttributes } from './auth';

// API calls use SigV4-signed requests via auth.ts — no proxy URL needed

interface ToolCall {
  tool: string;
  input: string;
}

interface TraceEvent {
  agent: string;
  status: 'in_progress' | 'completed' | 'failed';
  duration_ms?: number;
  response_preview?: string;
  error?: string;
  tool_calls?: ToolCall[];
}

interface MemoryContext {
  used: boolean;
  short_term: number;
  long_term: string[];
}

interface Message {
  role: 'user' | 'agent';
  content: string;
  vitalsData?: Record<string, number | string>[];
  medtechChart?: MedTechChartData;
  traces?: TraceEvent[];
  memory?: MemoryContext;
  timestamp: string;
}

type AgentId = 'orchestrator' | 'patient-monitoring' | 'device-management' | 'patient-engagement' | 'inventory-management' | 'field-service' | 'account-intelligence';
type PageId = AgentId | 'architecture' | 'workflows';
type Persona = 'hospital' | 'medtech' | null;

interface AgentConfig {
  id: AgentId;
  label: string;
  welcomeMessage: string;
  placeholder: string;
  persona: 'hospital' | 'medtech' | 'both';
}

const AGENTS: AgentConfig[] = [
  {
    id: 'orchestrator',
    label: 'Orchestrator Agent',
    welcomeMessage: '',
    placeholder: 'Ask cross-module questions that span multiple agents...',
    persona: 'both',
  },
  {
    id: 'patient-monitoring',
    label: 'Patient Monitoring',
    welcomeMessage: "Hello! I'm the Patient Monitoring Agent. I can help you monitor patient vitals, analyze trends, and assess deterioration risk. Try asking me \"List all patients\" or \"Show me vitals for patient P-10001\".",
    placeholder: 'Ask about patient vitals, trends, or deterioration risk...',
    persona: 'hospital',
  },
  {
    id: 'device-management',
    label: 'Device Management',
    welcomeMessage: "Hello! I'm the Device Management Agent. I can help you monitor device fleet health, diagnose issues, predict failures, and manage device-patient assignments. Try \"List all devices\" or \"Show me the fleet summary\".",
    placeholder: 'Ask about device status, fleet health, or maintenance...',
    persona: 'hospital',
  },
  {
    id: 'patient-engagement',
    label: 'Patient Engagement',
    welcomeMessage: "Hello! I'm the Patient Engagement Agent. I can help you manage patient communications, track medications, schedule appointments, assess no-show risk, and coordinate care.",
    placeholder: 'Ask about medications, appointments, care coordination...',
    persona: 'hospital',
  },
  {
    id: 'inventory-management',
    label: 'Inventory Management',
    welcomeMessage: "Hello! I'm the Inventory Management Agent. I can help you track floor-level supply inventory, assess stockout risks, identify patient care impacts from shortages, and manage reorder requests. Try \"Check stockout risk for ICU\" or \"What patients are affected by low Heparin stock?\"",
    placeholder: 'Ask about supply levels, stockout risks, reorders...',
    persona: 'hospital',
  },
  {
    id: 'field-service',
    label: 'Field Service',
    welcomeMessage: "Hello! I'm the Field Service Intelligence Agent. I help you manage your installed base across hospital customers, predict which devices need service, plan FSE dispatches, and compare firmware performance. Try \"Show me the installed base\" or \"Which devices need service in the next 14 days?\"",
    placeholder: 'Ask about installed base, service needs, firmware...',
    persona: 'medtech',
  },
  {
    id: 'account-intelligence',
    label: 'Account Intelligence',
    welcomeMessage: "Hello! I'm the Account Intelligence Agent. I help you assess hospital account health, predict contract renewal risks, and identify revenue opportunities. Try \"Show me account health scores\" or \"Which accounts are at risk of not renewing?\"",
    placeholder: 'Ask about account health, renewals, customer risk...',
    persona: 'medtech',
  },
];

function extractVitalsData(text: string): Record<string, number | string>[] | undefined {
  if (!text) return undefined;
  const vitalKeywords = ['heart rate', 'blood pressure', 'temperature', 'spo2', 'respiratory', 'glucose'];
  if (!vitalKeywords.some(kw => text.toLowerCase().includes(kw))) return undefined;
  const dp: Record<string, number | string> = { timestamp: new Date().toISOString() };
  let found = false;
  const patterns: [RegExp, string][] = [
    [/heart\s*rate[:\s]*(\d+\.?\d*)/i, 'heart_rate'],
    [/(?:bp\s*)?systolic[:\s]*(\d+\.?\d*)/i, 'blood_pressure_systolic'],
    [/(?:bp\s*)?diastolic[:\s]*(\d+\.?\d*)/i, 'blood_pressure_diastolic'],
    [/temperature[:\s]*(\d+\.?\d*)/i, 'temperature'],
    [/spo2[:\s]*(\d+\.?\d*)/i, 'spo2'],
    [/respiratory\s*rate[:\s]*(\d+\.?\d*)/i, 'respiratory_rate'],
    [/(?:blood\s*)?glucose[:\s]*(\d+\.?\d*)/i, 'blood_glucose'],
  ];
  for (const [p, k] of patterns) { if (dp[k]) continue; const m = text.match(p); if (m) { dp[k] = parseFloat(m[1]); found = true; } }
  return found ? [dp] : undefined;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [userEmail, setUserEmail] = useState<string>('');
  const [persona, setPersona] = useState<Persona>(null);
  const [activePage, setActivePage] = useState<PageId>('orchestrator');
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);
  const [voiceMode, setVoiceMode] = useState(false);
  const [activePatientId, setActivePatientId] = useState<string | null>(null);
  const [digitalTwinDeviceId, setDigitalTwinDeviceId] = useState<string | null>(null);
  const chatHistoriesRef = useRef<Record<string, Message[]>>(
    (() => { try { const s = sessionStorage.getItem('cc-chat-histories'); return s ? JSON.parse(s) : {}; } catch { return {}; } })()
  );
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('cc-dark-mode');
    const isDark = saved ? saved === 'true' : false;
    applyMode(isDark ? Mode.Dark : Mode.Light);
    return isDark;
  });

  // Check if user is already signed in on mount
  useEffect(() => {
    getCurrentUser()
      .then(async (user) => {
        setIsAuthenticated(true);
        try {
          const attrs = await fetchUserAttributes();
          if (attrs.email) {
            setUserEmail(attrs.email);
          }
        } catch {
          // Fallback: try to get email from the username if it looks like an email
          try {
            const username = user?.username || user?.userId || '';
            if (username.includes('@')) setUserEmail(username);
          } catch { /* ignore */ }
        }
      })
      .catch(() => setIsAuthenticated(false));
  }, []);

  const toggleDarkMode = (checked: boolean) => {
    setDarkMode(checked);
    applyMode(checked ? Mode.Dark : Mode.Light);
    localStorage.setItem('cc-dark-mode', String(checked));
  };

  const handleSignOut = async () => {
    await signOut();
    setIsAuthenticated(false);
  };

  // Loading state while checking auth
  if (isAuthenticated === null) {
    return (
      <Box padding="xxxl" textAlign="center">
        <Spinner size="large" />
      </Box>
    );
  }

  // Not authenticated — show login
  if (!isAuthenticated) {
    return <LoginPage onAuthenticated={() => setIsAuthenticated(true)} />;
  }

  // No persona selected — show persona picker
  if (!persona) {
    const isDark = document.body.classList.contains('awsui-dark');
    return (
      <Box padding="xxxl">
        <div style={{ maxWidth: 700, margin: '60px auto' }}>
          <SpaceBetween size="xl">
            <Box textAlign="center">
              <Box variant="h1" fontSize="heading-xl">Connected Care Platform</Box>
              <Box variant="p" color="text-body-secondary" margin={{ top: 's' }}>Select your role to get started</Box>
            </Box>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
              <div
                onClick={() => setPersona('hospital')}
                role="button" tabIndex={0}
                onKeyDown={e => { if (e.key === 'Enter') setPersona('hospital'); }}
                style={{
                  padding: 32, borderRadius: 16, cursor: 'pointer',
                  border: `2px solid ${isDark ? '#43A047' : '#C8E6C9'}`,
                  background: isDark ? '#0f1b2a' : '#ffffff',
                  transition: 'all 0.2s ease',
                  textAlign: 'center',
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = '#43A047'; (e.currentTarget as HTMLDivElement).style.boxShadow = '0 4px 20px rgba(67,160,71,0.15)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = isDark ? '#43A047' : '#C8E6C9'; (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'; }}
              >
                <div style={{ fontSize: '2.5em', marginBottom: 12 }}>🏥</div>
                <Box variant="h2">Hospital Staff</Box>
                <Box variant="p" color="text-body-secondary" margin={{ top: 'xs' }} fontSize="body-s">
                  Patient monitoring, device management, care coordination, inventory tracking, and clinical workflows.
                </Box>
                <div style={{ marginTop: 16, display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'center' }}>
                  {['Patient Monitoring', 'Device Management', 'Patient Engagement', 'Inventory'].map(a => (
                    <span key={a} style={{ fontSize: '0.72em', padding: '2px 8px', borderRadius: 10, background: '#C8E6C920', color: '#43A047', border: '1px solid #43A04730' }}>{a}</span>
                  ))}
                </div>
              </div>
              <div
                onClick={() => setPersona('medtech')}
                role="button" tabIndex={0}
                onKeyDown={e => { if (e.key === 'Enter') setPersona('medtech'); }}
                style={{
                  padding: 32, borderRadius: 16, cursor: 'pointer',
                  border: `2px solid ${isDark ? '#0288D1' : '#B3E5FC'}`,
                  background: isDark ? '#0f1b2a' : '#ffffff',
                  transition: 'all 0.2s ease',
                  textAlign: 'center',
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = '#0288D1'; (e.currentTarget as HTMLDivElement).style.boxShadow = '0 4px 20px rgba(2,136,209,0.15)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = isDark ? '#0288D1' : '#B3E5FC'; (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'; }}
              >
                <div style={{ fontSize: '2.5em', marginBottom: 12 }}>🔧</div>
                <Box variant="h2">MedTech Operations</Box>
                <Box variant="p" color="text-body-secondary" margin={{ top: 'xs' }} fontSize="body-s">
                  Installed base management, field service dispatch, account health, contract renewals, and post-market surveillance.
                </Box>
                <div style={{ marginTop: 16, display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'center' }}>
                  {['Field Service', 'Account Intelligence'].map(a => (
                    <span key={a} style={{ fontSize: '0.72em', padding: '2px 8px', borderRadius: 10, background: '#B3E5FC20', color: '#0288D1', border: '1px solid #0288D130' }}>{a}</span>
                  ))}
                </div>
              </div>
            </div>
            <Box textAlign="center">
              <Button variant="link" onClick={handleSignOut}>Sign out</Button>
            </Box>
          </SpaceBetween>
        </div>
      </Box>
    );
  }

  const handleTryWorkflow = (prompt: string) => {
    setPendingPrompt(prompt);
    setActivePage('orchestrator');
  };

  const renderContent = () => {
    if (digitalTwinDeviceId) {
      return <DeviceDigitalTwin deviceId={digitalTwinDeviceId} onBack={() => setDigitalTwinDeviceId(null)} />;
    }
    if (activePage === 'architecture') return <ArchitecturePage />;
    if (activePage === 'workflows') return <WorkflowsPage onTryWorkflow={handleTryWorkflow} persona={persona} />;
    const agent = AGENTS.find(a => a.id === activePage);
    if (!agent) return null;
    if (voiceMode) return <VoiceMode agentId={agent.id} agentLabel={agent.label} />;
    return (
      <div style={{ display: 'flex', height: '100%', gap: 0 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <AgentChat key={agent.id} agent={agent} persona={persona} userEmail={userEmail} chatHistories={chatHistoriesRef} pendingPrompt={activePage === 'orchestrator' ? pendingPrompt : null} onPromptConsumed={() => setPendingPrompt(null)} onPatientDetected={setActivePatientId} onDeviceTwinOpen={setDigitalTwinDeviceId} />
        </div>
        {activePatientId && (
          <div style={{ width: 320, flexShrink: 0 }}>
            <PatientMemoryPanel patientId={activePatientId} userEmail={userEmail} />
          </div>
        )}
      </div>
    );
  };

  return (
    <AppLayout
      toolsHide
      navigation={
        <SideNavigation
          header={{ text: persona === 'hospital' ? 'Hospital Staff' : 'MedTech Operations', href: '#' }}
          activeHref={`#/${activePage}`}
          onFollow={e => { e.preventDefault(); setActivePage(e.detail.href.replace('#/', '') as PageId); }}
          items={[
            { type: 'link', text: 'Orchestrator Agent', href: '#/orchestrator' },
            { type: 'divider' },
            ...(persona === 'hospital' ? [
              { type: 'section' as const, text: 'Domain Agents', items: [
                { type: 'link' as const, text: 'Patient Monitoring', href: '#/patient-monitoring' },
                { type: 'link' as const, text: 'Device Management', href: '#/device-management' },
                { type: 'link' as const, text: 'Patient Engagement', href: '#/patient-engagement' },
                { type: 'link' as const, text: 'Inventory Management', href: '#/inventory-management' },
              ]},
            ] : [
              { type: 'section' as const, text: 'MedTech Agents', items: [
                { type: 'link' as const, text: 'Field Service', href: '#/field-service' },
                { type: 'link' as const, text: 'Account Intelligence', href: '#/account-intelligence' },
              ]},
            ]),
            { type: 'divider' },
            { type: 'link', text: 'Workflows', href: '#/workflows' },
            { type: 'link', text: 'Architecture', href: '#/architecture' },
          ]}
        />
      }
      content={
        <Box padding="l">
          <SpaceBetween size="s">
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, alignItems: 'center' }}>
              <NotificationBell onInvestigate={handleTryWorkflow} />
              <Toggle onChange={({ detail }) => setVoiceMode(detail.checked)} checked={voiceMode}>Voice mode</Toggle>
              <Toggle onChange={({ detail }) => toggleDarkMode(detail.checked)} checked={darkMode}>Dark mode</Toggle>
              <Button variant="link" onClick={() => { setPersona(null); setActivePage('orchestrator'); }}>Switch role</Button>
              {userEmail && <span style={{ fontSize: '0.75em', color: '#6b7280' }}>{userEmail}</span>}
              <Button variant="link" onClick={handleSignOut}>Sign out</Button>
            </div>
            <div style={{ height: 'calc(100vh - 120px)' }}>{renderContent()}</div>
          </SpaceBetween>
        </Box>
      }
    />
  );
}

const ORCHESTRATOR_WELCOME: Record<string, string> = {
  hospital: "I'm the Orchestrator Agent. I coordinate cross-module workflows across clinical agents. Try asking me:\n\n- \"Device D-4001 has failed. What's the patient impact?\"\n- \"Patient P-10001 is deteriorating. Activate the cascade.\"\n- \"Investigate a fall in ICU-412 for patient P-10001\"\n- \"Give me a full situational briefing for the ICU\"",
  medtech: "I'm the Orchestrator Agent. I coordinate cross-module workflows across MedTech agents. Try asking me:\n\n- \"Plan proactive service dispatches for all sites over the next 14 days\"\n- \"Generate a post-market surveillance report for BD Alaris 8015\"\n- \"Run an account health review across all customers\"\n- \"Which devices need service and do the sites have the parts in stock?\"",
};

function AgentChat({ agent, persona, userEmail, chatHistories, pendingPrompt, onPromptConsumed, onPatientDetected, onDeviceTwinOpen }: { agent: AgentConfig; persona: Persona; userEmail: string; chatHistories: React.MutableRefObject<Record<string, Message[]>>; pendingPrompt?: string | null; onPromptConsumed?: () => void; onPatientDetected?: (id: string | null) => void; onDeviceTwinOpen?: (id: string) => void }) {
  const welcomeMsg = agent.id === 'orchestrator' ? (ORCHESTRATOR_WELCOME[persona || 'hospital'] || ORCHESTRATOR_WELCOME.hospital) : agent.welcomeMessage;
  const savedMessages = chatHistories.current[agent.id];
  const [messages, setMessages] = useState<Message[]>(savedMessages || [{
    role: 'agent', content: welcomeMsg, timestamp: new Date().toISOString(),
  }]);

  // Persist messages back to the shared ref and sessionStorage whenever they change
  useEffect(() => {
    chatHistories.current[agent.id] = messages;
    try { sessionStorage.setItem('cc-chat-histories', JSON.stringify(chatHistories.current)); } catch { /* ignore */ }
  }, [messages, agent.id, chatHistories]);
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [liveTraces, setLiveTraces] = useState<TraceEvent[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const sessionRef = useRef(`cc-${agent.id}-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  const pollingRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, liveTraces]);

  // Cleanup polling on unmount
  useEffect(() => () => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    if (abortRef.current) abortRef.current.abort();
  }, []);

  // Pick up pending prompt from Workflows page
  useEffect(() => {
    if (pendingPrompt && !isLoading) {
      setPrompt(pendingPrompt);
      onPromptConsumed?.();
    }
  }, [pendingPrompt, isLoading, onPromptConsumed]);

  // Elapsed time counter for orchestrator loading state
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const elapsedRef = useRef<number | null>(null);

  useEffect(() => {
    if (isLoading) {
      setElapsedSeconds(0);
      elapsedRef.current = window.setInterval(() => setElapsedSeconds(s => s + 1), 1000);
    } else {
      if (elapsedRef.current) { clearInterval(elapsedRef.current); elapsedRef.current = null; }
    }
    return () => { if (elapsedRef.current) clearInterval(elapsedRef.current); };
  }, [isLoading]);

  const pollForResult = useCallback((requestId: string) => {
    const poll = async () => {
      try {
        const res = await signedFetch(`?request_id=${requestId}`);
        const data = await res.json();

        // Update live traces
        if (data.traces) setLiveTraces(data.traces);

        // Check if completed
        if (data.completed && data.result) {
          if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
          const orchChart = extractMedTechChartData(data.result.response || '', 'orchestrator');
          setMessages(prev => [...prev, {
            role: 'agent',
            content: data.result.response || 'No response',
            traces: data.traces,
            medtechChart: orchChart,
            timestamp: new Date().toISOString(),
          }]);
          setLiveTraces([]);
          setIsLoading(false);
        }
      } catch { /* ignore poll errors */ }
    };
    pollingRef.current = window.setInterval(poll, 2000);
    poll(); // immediate first poll
  }, []);

  const handleJoinCareTeam = async (patientId: string) => {
    try {
      await signedFetch('', {
        method: 'POST',
        body: JSON.stringify({ care_team_action: 'join', patient_id: patientId, actor_email: userEmail }),
      });
      setMessages(prev => [...prev, {
        role: 'agent',
        content: `Identity verified. Thank you for confirming your credentials — you have been added to the care team for patient ${patientId}. You can now access their clinical data, vitals, and memory timeline.`,
        timestamp: new Date().toISOString(),
      }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'agent',
        content: `Verification failed: ${e instanceof Error ? e.message : 'Unknown error'}. Please contact the charge nurse for access.`,
        timestamp: new Date().toISOString(),
      }]);
    }
  };

  const handleCancel = () => {
    if (abortRef.current) { abortRef.current.abort(); abortRef.current = null; }
    if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
    setMessages(prev => [...prev, { role: 'agent', content: 'Request cancelled.', timestamp: new Date().toISOString() }]);
    setLiveTraces([]);
    setIsLoading(false);
  };

  const onSend = async ({ detail: { value } }: { detail: { value: string } }) => {
    const text = value.trim();
    if (!text || isLoading) return;

    setMessages(prev => [...prev, { role: 'user', content: text, timestamp: new Date().toISOString() }]);
    setPrompt('');
    setIsLoading(true);
    setLiveTraces([]);

    // Detect patient ID from user message
    const patientMatch = text.match(/P-\d{5}/i);
    if (patientMatch && onPatientDetected) {
      onPatientDetected(patientMatch[0].toUpperCase());
    }

    // Create abort controller for this request
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await signedFetch('', {
        method: 'POST',
        body: JSON.stringify({ agent: agent.id, prompt: text, session_id: sessionRef.current, actor_email: userEmail }),
        signal: controller.signal,
      });

      const data = await response.json();

      if (data.request_id) {
        // Async mode (orchestrator) — start polling
        pollForResult(data.request_id);
      } else {
        // Sync mode (domain agents) — response is immediate
        const vitalsData = agent.id === 'patient-monitoring' ? extractVitalsData(data.response || '') : undefined;
        const medtechChart = extractMedTechChartData(data.response || '', agent.id);
        setMessages(prev => [...prev, {
          role: 'agent',
          content: data.response || data.error || 'No response received',
          vitalsData,
          medtechChart,
          memory: data.memory || undefined,
          timestamp: new Date().toISOString(),
        }]);
        setIsLoading(false);
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return; // handled by handleCancel
      setMessages(prev => [...prev, {
        role: 'agent',
        content: `Connection error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      }]);
      setIsLoading(false);
    }
  };

  const AGENT_LABELS: Record<string, string> = {
    'patient-monitoring': 'Patient Monitoring',
    'device-management': 'Device Management',
    'patient-engagement': 'Patient Engagement',
    'inventory-management': 'Inventory Management',
    'field-service': 'Field Service',
    'account-intelligence': 'Account Intelligence',
    'orchestrator': 'Orchestrator',
  };

  const AGENT_COLORS: Record<string, string> = {
    'patient-monitoring': '#10b981',
    'device-management': '#3b82f6',
    'patient-engagement': '#f59e0b',
    'inventory-management': '#ec4899',
    'field-service': '#06b6d4',
    'account-intelligence': '#f97316',
    'orchestrator': '#8b5cf6',
  };

  const renderToolCalls = (toolCalls: ToolCall[] | undefined, agentKey: string, large?: boolean) => {
    if (!toolCalls || toolCalls.length === 0) return null;
    const color = AGENT_COLORS[agentKey] || '#6b7280';
    const fontSize = large ? '0.95em' : '0.82em';
    return (
      <div style={{ marginTop: 6, marginLeft: 24, paddingLeft: 10, borderLeft: `2px solid ${color}40` }}>
        {toolCalls.map((tc, i) => (
          <div key={i} style={{ padding: '4px 0', fontSize }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ color, fontWeight: 600, fontSize: '1.1em' }}>⚡</span>
              <code style={{
                background: `${color}15`,
                color,
                padding: '2px 8px',
                borderRadius: 4,
                fontFamily: 'monospace',
                fontWeight: 500,
              }}>{tc.tool}</code>
            </div>
            {tc.input && (
              <div style={{
                marginLeft: 28, marginTop: 3,
                color: 'var(--color-text-body-secondary, #687078)',
                fontStyle: 'italic',
                lineHeight: 1.4,
                fontSize: '0.9em',
              }}>
                "{tc.input}"
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <Container fitHeight disableContentPaddings
      header={<Header variant="h2">{agent.label}</Header>}
      footer={
        <Box padding={{ horizontal: 'l', bottom: 's' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <div style={{ flex: 1 }}>
              <PromptInput onChange={({ detail }) => setPrompt(detail.value)} onAction={onSend} value={prompt}
                actionButtonAriaLabel={isLoading ? 'Sending...' : 'Send message'} actionButtonIconName="send"
                ariaLabel="Chat input" placeholder={agent.placeholder} disabled={isLoading} />
            </div>
            {isLoading && (
              <Button variant="normal" onClick={handleCancel} ariaLabel="Cancel request">
                Cancel
              </Button>
            )}
          </div>
        </Box>
      }
    >
      <div ref={scrollRef} style={{ overflowY: 'auto', height: 'calc(100vh - 280px)', padding: '16px 20px' }}>
        <SpaceBetween size="m">
          {messages.map((msg, i) => (
            <ChatBubble key={i} type={msg.role === 'user' ? 'outgoing' : 'incoming'} ariaLabel={msg.role === 'user' ? 'You' : agent.label}
              avatar={<Avatar ariaLabel={msg.role === 'user' ? 'You' : agent.label} color={msg.role === 'user' ? 'default' : 'gen-ai'} iconName={msg.role === 'user' ? 'user-profile' : 'gen-ai'} />}>
              {msg.traces && msg.traces.length > 0 && (
                <div style={{ marginBottom: 12, padding: '8px 12px', background: 'var(--color-background-container-content, #f8f9fa)', borderRadius: 8 }}>
                  <Box variant="small" color="text-body-secondary">Workflow completed — {msg.traces.filter(t => t.status === 'completed').length} agents invoked</Box>
                  <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 6 }}>
                    {msg.traces.filter(t => t.status !== 'in_progress').map((t, j) => {
                      const color = AGENT_COLORS[t.agent] || '#6b7280';
                      return (
                        <div key={j} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.9em' }}>
                          <div style={{ width: 8, height: 8, borderRadius: '50%', background: t.status === 'completed' ? color : '#ef4444' }} />
                          <span style={{ fontWeight: 500 }}>{AGENT_LABELS[t.agent] || t.agent}</span>
                          <span style={{ fontFamily: 'monospace', color: 'var(--color-text-body-secondary, #687078)' }}>
                            {t.duration_ms ? `${(t.duration_ms / 1000).toFixed(1)}s` : 'failed'}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {msg.memory && (msg.memory.short_term > 0 || (msg.memory.long_term && msg.memory.long_term.length > 0)) && (
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '3px 10px', marginBottom: 8, borderRadius: 12,
                  background: 'linear-gradient(135deg, #8b5cf620, #6366f120)',
                  border: '1px solid #8b5cf630',
                  fontSize: '0.8em', color: '#8b5cf6',
                }}>
                  <span style={{ fontSize: '1.1em' }}>🧠</span>
                  <span style={{ fontWeight: 500 }}>Memory used</span>
                  {msg.memory.short_term > 0 && (
                    <span style={{ color: '#6b7280' }}>
                      — {msg.memory.short_term} prior message{msg.memory.short_term > 1 ? 's' : ''} recalled
                    </span>
                  )}
                  {msg.memory.long_term && msg.memory.long_term.length > 0 && (
                    <span style={{ color: '#6b7280' }}>
                      — {msg.memory.long_term.join(', ')}
                    </span>
                  )}
                </div>
              )}
              {msg.role === 'agent' && msg.content && (
                msg.content.toLowerCase().includes('agentcore memory') ||
                msg.content.toLowerCase().includes('long-term memory') ||
                msg.content.toLowerCase().includes('memory record')
              ) && (
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '3px 10px', marginBottom: 8, marginLeft: 6, borderRadius: 12,
                  background: 'linear-gradient(135deg, #06b6d420, #0891b220)',
                  border: '1px solid #06b6d430',
                  fontSize: '0.8em', color: '#06b6d4',
                }}>
                  <span style={{ fontWeight: 500 }}>AgentCore Long-Term Memory</span>
                  <span style={{ color: '#6b7280' }}>— patient insights retrieved</span>
                </div>
              )}
              {msg.role === 'agent' && msg.content && (msg.content.includes('not on the care team') || msg.content.includes('Access denied') || msg.content.includes('care_team_action')) && (() => {
                const pidMatch = msg.content.match(/P-\d{5}/);
                const pid = pidMatch ? pidMatch[0] : '';
                return pid ? (
                  <div style={{
                    padding: '12px 16px', marginBottom: 10, borderRadius: 8,
                    background: 'linear-gradient(135deg, #fef2f210, #fee2e210)',
                    border: '1px solid #fca5a540',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: '0.85em', color: '#ef4444', fontWeight: 500 }}>
                        PHI Access Restricted — Identity verification required
                      </span>
                      <Button variant="primary" onClick={() => handleJoinCareTeam(pid)}>
                        Verify &amp; Join Care Team
                      </Button>
                    </div>
                  </div>
                ) : null;
              })()}
              <Markdown remarkPlugins={[remarkGfm]} components={{
                // Make device IDs (D-XXXX) clickable to open digital twin
                p: ({ children, ...props }) => {
                  if (!onDeviceTwinOpen || !children) return <p {...props}>{children}</p>;
                  const processChild = (child: React.ReactNode): React.ReactNode => {
                    if (typeof child !== 'string') return child;
                    const parts = child.split(/(D-\d{4})/g);
                    if (parts.length === 1) return child;
                    return parts.map((part, idx) =>
                      /^D-\d{4}$/.test(part) ? (
                        <span key={idx} onClick={(e) => { e.stopPropagation(); onDeviceTwinOpen(part); }}
                          style={{ color: '#06b6d4', cursor: 'pointer', textDecoration: 'underline', textDecorationStyle: 'dotted', fontWeight: 500 }}
                          role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter') onDeviceTwinOpen(part); }}
                          title={`Open Digital Twin for ${part}`}>{part}</span>
                      ) : part
                    );
                  };
                  const processed = Array.isArray(children) ? children.map(processChild) : processChild(children);
                  return <p {...props}>{processed}</p>;
                },
                td: ({ children, ...props }) => {
                  if (!onDeviceTwinOpen || !children) return <td {...props}>{children}</td>;
                  const processChild = (child: React.ReactNode): React.ReactNode => {
                    if (typeof child !== 'string') return child;
                    const parts = child.split(/(D-\d{4})/g);
                    if (parts.length === 1) return child;
                    return parts.map((part, idx) =>
                      /^D-\d{4}$/.test(part) ? (
                        <span key={idx} onClick={(e) => { e.stopPropagation(); onDeviceTwinOpen(part); }}
                          style={{ color: '#06b6d4', cursor: 'pointer', textDecoration: 'underline', textDecorationStyle: 'dotted', fontWeight: 500 }}
                          role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter') onDeviceTwinOpen(part); }}
                          title={`Open Digital Twin for ${part}`}>{part}</span>
                      ) : part
                    );
                  };
                  const processed = Array.isArray(children) ? children.map(processChild) : processChild(children);
                  return <td {...props}>{processed}</td>;
                },
                li: ({ children, ...props }) => {
                  if (!onDeviceTwinOpen || !children) return <li {...props}>{children}</li>;
                  const processChild = (child: React.ReactNode): React.ReactNode => {
                    if (typeof child !== 'string') return child;
                    const parts = child.split(/(D-\d{4})/g);
                    if (parts.length === 1) return child;
                    return parts.map((part, idx) =>
                      /^D-\d{4}$/.test(part) ? (
                        <span key={idx} onClick={(e) => { e.stopPropagation(); onDeviceTwinOpen(part); }}
                          style={{ color: '#06b6d4', cursor: 'pointer', textDecoration: 'underline', textDecorationStyle: 'dotted', fontWeight: 500 }}
                          role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter') onDeviceTwinOpen(part); }}
                          title={`Open Digital Twin for ${part}`}>{part}</span>
                      ) : part
                    );
                  };
                  const processed = Array.isArray(children) ? children.map(processChild) : processChild(children);
                  return <li {...props}>{processed}</li>;
                },
              }}>{msg.content}</Markdown>
              {msg.vitalsData && msg.vitalsData.length > 0 && <VitalsChart data={msg.vitalsData} />}
              {msg.medtechChart && <MedTechChart chartData={msg.medtechChart} />}
            </ChatBubble>
          ))}
          {/* Live trace during orchestrator execution — FOCAL POINT */}
          {isLoading && liveTraces.length > 0 && (
            <ChatBubble type="incoming" ariaLabel="Executing workflow" avatar={<Avatar ariaLabel={agent.label} color="gen-ai" iconName="gen-ai" />}>
              <div style={{ padding: '4px 0' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                  <Spinner size="normal" />
                  <span style={{ fontSize: '1.1em', fontWeight: 600 }}>
                    Orchestrating workflow — {elapsedSeconds}s
                  </span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {liveTraces.map((t, j) => {
                    const color = AGENT_COLORS[t.agent] || '#6b7280';
                    const isActive = t.status === 'in_progress';
                    return (
                      <div key={j} style={{
                        padding: '12px 16px',
                        borderRadius: 8,
                        border: `1px solid ${isActive ? color + '60' : 'var(--color-border-divider-default, #d5dbdb)'}`,
                        background: isActive ? `${color}08` : 'transparent',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <div style={{
                              width: 10, height: 10, borderRadius: '50%',
                              background: t.status === 'completed' ? '#10b981' : t.status === 'failed' ? '#ef4444' : color,
                              boxShadow: isActive ? `0 0 8px ${color}80` : 'none',
                              animation: isActive ? 'pulse 1.5s ease-in-out infinite' : 'none',
                            }} />
                            <span style={{ fontSize: '1em', fontWeight: 600 }}>
                              {AGENT_LABELS[t.agent] || t.agent}
                            </span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            {t.status === 'in_progress' && <StatusIndicator type="in-progress">Running</StatusIndicator>}
                            {t.status === 'completed' && <StatusIndicator type="success">{t.duration_ms ? `${(t.duration_ms / 1000).toFixed(1)}s` : 'Done'}</StatusIndicator>}
                            {t.status === 'failed' && <StatusIndicator type="error">Failed</StatusIndicator>}
                          </div>
                        </div>
                        {renderToolCalls(t.tool_calls, t.agent, true)}
                      </div>
                    );
                  })}
                </div>
              </div>
              <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }`}</style>
            </ChatBubble>
          )}
          {isLoading && liveTraces.length === 0 && (
            <ChatBubble type="incoming" ariaLabel="Agent is thinking" avatar={<Avatar ariaLabel={agent.label} color="gen-ai" iconName="gen-ai" />}>
              <SpaceBetween size="xs" direction="horizontal" alignItems="center">
                <Spinner size="normal" />
                <Box variant="p">Working on your request... ({elapsedSeconds}s)</Box>
              </SpaceBetween>
            </ChatBubble>
          )}
        </SpaceBetween>
      </div>
    </Container>
  );
}

export default App;
