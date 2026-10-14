/**
 * Workflows Page — Interactive showcase of all platform workflows.
 * Each workflow is a clickable card that shows what the system can do.
 * "Try it" sends the user to the orchestrator chat with a pre-filled prompt.
 */

import { useState } from 'react';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Box from '@cloudscape-design/components/box';
import Button from '@cloudscape-design/components/button';
import ColumnLayout from '@cloudscape-design/components/column-layout';
import Icon from '@cloudscape-design/components/icon';
import Badge from '@cloudscape-design/components/badge';
import { signedFetch } from './auth';

interface Workflow {
  id: string;
  name: string;
  icon: string;
  type: 'cross-module' | 'single-agent';
  persona: 'clinical' | 'medtech';
  agents: string[];
  trigger: string;
  description: string;
  clinicalValue: string;
  sla: string;
  steps: number;
  examplePrompts: string[];
  simulateScenario?: string;
  simulateDetails?: string;
}

const AGENT_COLORS: Record<string, string> = {
  'Patient Monitoring': '#10b981',
  'Device Management': '#3b82f6',
  'Patient Engagement': '#f59e0b',
  'Inventory Management': '#ec4899',
  'Field Service': '#06b6d4',
  'Account Intelligence': '#f97316',
  'Orchestrator': '#8b5cf6',
};

const WORKFLOWS: Workflow[] = [
  {
    id: 'WF-01',
    name: 'Fall Detection & Investigation',
    icon: '🚨',
    type: 'cross-module',
    persona: 'clinical',
    agents: ['Patient Monitoring', 'Device Management', 'Patient Engagement'],
    trigger: 'fall.detected',
    description: 'Confirms a fall event, correlates device diagnostics, analyzes contributing clinical factors, and initiates automated care response.',
    clinicalValue: 'Identifies medication-related falls that would otherwise be missed. Reduces time-to-response.',
    sla: '30s target',
    steps: 5,
    simulateScenario: 'fall_risk',
    simulateDetails: 'Patient P-10001 (ICU-412): Restlessness score → 8.5 (threshold: 6.0), Bed exit alarm → triggered, Bed position → upright, Rails → none. Combined with Furosemide + Metoprolol (orthostatic risk).',
    examplePrompts: [
      'Investigate a fall in ICU-412 for patient P-10001',
      'Patient P-10002 fell in Room 308. What caused it?',
      'Run a fall investigation for Margaret Chen',
    ],
  },
  {
    id: 'WF-02',
    name: 'Medication-Vitals Correlation',
    icon: '💊',
    type: 'cross-module',
    persona: 'clinical',
    agents: ['Patient Monitoring', 'Patient Engagement', 'Device Management'],
    trigger: 'vital_sign.anomaly',
    description: 'Investigates whether an unexpected vital sign change was caused by a medication change or device malfunction.',
    clinicalValue: 'Prevents adverse drug events by catching medication-related vital sign changes early.',
    sla: '45s target',
    steps: 5,
    examplePrompts: [
      'Patient P-10001 has an unexpected BP drop. Is it medication-related?',
      'Correlate the vital sign anomaly for James Rodriguez with his recent meds',
      'Check if the heart rate spike for P-10003 is a drug side effect or device issue',
    ],
  },
  {
    id: 'WF-03',
    name: 'Patient Deterioration Cascade',
    icon: '⚡',
    type: 'cross-module',
    persona: 'clinical',
    agents: ['Patient Monitoring', 'Device Management', 'Patient Engagement'],
    trigger: 'vital_sign.early_warning',
    description: 'Validates deterioration is real (not a device issue), gathers full clinical context, and activates rapid response with pre-assembled information.',
    clinicalValue: 'Care team arrives already informed. Eliminates 5-10 minutes typically spent gathering context during rapid response.',
    sla: '20s target',
    steps: 4,
    simulateScenario: 'deterioration',
    simulateDetails: 'Patient P-10001 (ICU-412): Heart rate → 118 bpm, Systolic BP → 82 mmHg, SpO2 → 87%, Respiratory rate → 28/min, Temperature → 101.8°F. Early Warning Score exceeds critical threshold.',
    examplePrompts: [
      'Patient P-10001 is deteriorating. Activate the cascade.',
      'Margaret Chen\'s vitals are trending down. Run the deterioration protocol.',
      'Early warning triggered for P-10002. Assess and activate rapid response.',
    ],
  },
  {
    id: 'WF-04',
    name: 'Device Failure Patient Impact',
    icon: '🔧',
    type: 'cross-module',
    persona: 'clinical',
    agents: ['Device Management', 'Patient Monitoring', 'Patient Engagement'],
    trigger: 'device.failure',
    description: 'Assesses which patients are affected by a device failure, evaluates clinical risk, locates replacements, and notifies care teams.',
    clinicalValue: 'Transforms device failures from an IT problem into a clinical safety response with patient-specific risk assessments.',
    sla: '45s target',
    steps: 5,
    examplePrompts: [
      'Device D-4001 has failed. What\'s the patient impact?',
      'Ventilator in ICU-412 went offline. Assess affected patients.',
      'Run a device failure impact assessment for D-3002',
    ],
  },
  {
    id: 'WF-05',
    name: 'Post-Discharge Monitoring',
    icon: '🏠',
    type: 'cross-module',
    persona: 'clinical',
    agents: ['Patient Engagement', 'Device Management', 'Patient Monitoring'],
    trigger: 'patient.discharged',
    description: 'Retrieves discharge plan, provisions home monitoring devices, activates personalized protocols, and onboards the patient.',
    clinicalValue: 'Ensures continuous monitoring starts immediately at discharge. Reduces readmission rates during the most vulnerable period.',
    sla: '5m target',
    steps: 4,
    examplePrompts: [
      'Discharge patient P-10004 and set up remote monitoring',
      'Robert Kim is being discharged. Activate home monitoring.',
      'Set up post-discharge monitoring for P-10005 with wearable devices',
    ],
  },
  {
    id: 'WF-06',
    name: 'Vital Sign Early Warning',
    icon: '📈',
    type: 'single-agent',
    persona: 'clinical',
    agents: ['Patient Monitoring'],
    trigger: 'vital_sign.reading_received',
    description: 'Detects subtle vital sign trends that individually look normal but collectively indicate a patient heading toward a critical event.',
    clinicalValue: 'Catches slowly declining patients 30-60 minutes before traditional threshold alerts would fire.',
    sla: '5s target',
    steps: 3,
    examplePrompts: [
      'Show me the vital sign trends for patient P-10001',
      'Is P-10002 showing any deterioration patterns?',
      'Analyze the 4-hour vital sign trajectory for Margaret Chen',
    ],
  },
  {
    id: 'WF-07',
    name: 'Predictive Maintenance',
    icon: '🔮',
    type: 'single-agent',
    persona: 'clinical',
    agents: ['Device Management'],
    trigger: 'device.telemetry_batch',
    description: 'Predicts which devices are likely to fail in the coming 7/14/30 days. Prioritizes maintenance by patient dependency.',
    clinicalValue: 'Shifts from reactive "fix when broken" to proactive "fix before it breaks." Reduces unplanned device downtime.',
    sla: '5m target',
    steps: 4,
    examplePrompts: [
      'Which devices are at risk of failing this week?',
      'Show me the predictive maintenance schedule',
      'Run a fleet health assessment and flag at-risk devices',
    ],
  },
  {
    id: 'WF-08',
    name: 'Appointment No-Show Prediction',
    icon: '📅',
    type: 'single-agent',
    persona: 'clinical',
    agents: ['Patient Engagement'],
    trigger: 'appointment.scheduled',
    description: 'Evaluates upcoming appointments for no-show risk and triggers proactive outreach for high-risk patients.',
    clinicalValue: 'Reduces no-show rates by identifying at-risk patients early and intervening with personalized outreach.',
    sla: '2m target',
    steps: 4,
    examplePrompts: [
      'Which patients are at risk of missing their appointments?',
      'Assess no-show risk for P-10003\'s upcoming appointment',
      'Check appointment adherence patterns for all patients',
    ],
  },
  {
    id: 'WF-09',
    name: 'Bed Exit Fall Risk Assessment',
    icon: '🛏️',
    type: 'cross-module',
    persona: 'clinical',
    agents: ['Device Management', 'Patient Monitoring', 'Patient Engagement'],
    trigger: 'bed.exit_detected',
    description: 'When a smart bed detects a patient getting up, correlates vitals, medications, and time of day to assess fall risk in real time.',
    clinicalValue: 'Shifts from "patient fell, investigate why" to "patient is getting up and is at high risk." Catches medication-related orthostatic risk before the fall happens.',
    sla: '10s target',
    steps: 5,
    examplePrompts: [
      'What is the current fall risk for patient P-10001?',
      'Show me bed exit events for ICU-412 in the last 24 hours',
      'Assess fall risk for Margaret Chen based on her meds and vitals',
    ],
  },
  {
    id: 'WF-10',
    name: 'Pressure Injury Prevention',
    icon: '🩹',
    type: 'cross-module',
    persona: 'clinical',
    agents: ['Device Management', 'Patient Monitoring', 'Patient Engagement'],
    trigger: 'bed.repositioning_overdue',
    description: 'Monitors smart bed pressure sensors to detect when patients have not been repositioned. Escalates based on Braden score, pressure zones, and comorbidities.',
    clinicalValue: 'Pressure injuries are CMS "never events" costing $9-11B annually. Automated tracking replaces paper-based turning schedules with intelligent, risk-aware alerts.',
    sla: '30s target',
    steps: 4,
    simulateScenario: 'pressure_injury',
    simulateDetails: 'Patient P-10001 (ICU-412) Smart Bed D-7001: Sacral pressure → 52 mmHg (threshold: 40), Hours since reposition → 4.1 (threshold: 2.0), Braden score → 12 (HIGH risk).',
    examplePrompts: [
      'When was patient P-10001 last repositioned?',
      'Show me pressure injury risk for all patients',
      'Which patients need repositioning right now?',
    ],
  },
  {
    id: 'WF-12',
    name: 'Alert Triage & Fatigue Management',
    icon: '🔕',
    type: 'cross-module',
    persona: 'clinical',
    agents: ['Patient Monitoring', 'Patient Engagement'],
    trigger: 'alert.generated',
    description: 'Intercepts every alert before it reaches a nurse. Suppresses device noise and repeat thresholds, bundles related alerts, and escalates critical findings. Reduces alert volume by 60-80%.',
    clinicalValue: 'Nurses receive 150-400 alerts per shift, 95% non-actionable. This system ensures every alert that reaches a nurse is worth their attention. CRITICAL alerts are never suppressed.',
    sla: '2s for critical, 10m for bundled',
    steps: 5,
    examplePrompts: [
      'Evaluate this alert: patient P-10001, vital threshold, medium severity, heart rate 112',
      'How many alerts were suppressed in the last hour?',
      'Show me the triage breakdown for tonight\'s shift',
    ],
  },
  {
    id: 'WF-13',
    name: 'Nurse Workload Query',
    icon: '👩‍⚕️',
    type: 'cross-module',
    persona: 'clinical',
    agents: ['Patient Engagement', 'Patient Monitoring'],
    trigger: 'user.query',
    description: 'Nurses and charge nurses can query their alert load, view suppressed alerts, check team workload distribution, and request alert redistribution.',
    clinicalValue: 'Gives charge nurses real-time visibility into team workload. Identifies overloaded nurses before burnout affects patient care.',
    sla: '5s target',
    steps: 2,
    examplePrompts: [
      'What is the alert load for Maria Santos?',
      'Show me suppressed alerts for the last hour',
      'How is the nursing team workload distributed tonight?',
    ],
  },
  {
    id: 'WF-06',
    name: 'Critical Shortage Patient Impact',
    icon: '📦',
    type: 'cross-module',
    persona: 'clinical',
    agents: ['Inventory Management', 'Patient Monitoring', 'Device Management', 'Patient Engagement'],
    trigger: 'inventory.stockout_risk',
    description: 'Identifies critical supply shortages, correlates with admitted patients, assesses clinical impact, checks for substitutes, and notifies care teams.',
    clinicalValue: 'Prevents supply-driven care disruptions by connecting inventory data to patient needs before a stockout occurs.',
    sla: '30s target',
    steps: 5,
    examplePrompts: [
      'Check for critical supply shortages in the ICU and assess patient impact',
      'Heparin is running low on ICU. Who is affected?',
      'Run a shortage impact assessment for all floors',
    ],
  },
  {
    id: 'WF-07',
    name: 'Admission Supply Readiness',
    icon: '🏥',
    type: 'cross-module',
    persona: 'clinical',
    agents: ['Patient Monitoring', 'Inventory Management', 'Device Management'],
    trigger: 'patient.admitted',
    description: 'Verifies that all required supplies, medications, and device consumables are available on the floor before or during a new patient admission.',
    clinicalValue: 'Eliminates day-of scrambles by proactively checking supply readiness before a patient arrives on the floor.',
    sla: '25s target',
    steps: 4,
    examplePrompts: [
      'Check if Floor2 is ready for patient P-10003 admission',
      'Is the ICU stocked for a new ventilator patient?',
      'Run admission readiness check for P-10001 on ICU',
    ],
  },
  {
    id: 'WF-08',
    name: 'Floor Situational Awareness',
    icon: '📋',
    type: 'cross-module',
    persona: 'clinical',
    agents: ['Patient Monitoring', 'Device Management', 'Inventory Management', 'Patient Engagement'],
    trigger: 'floor.briefing',
    description: 'Generates a comprehensive floor status briefing combining patient acuity, device health, supply levels, and staffing for charge nurse shift handoffs.',
    clinicalValue: 'Replaces manual shift-start rounds with a synthesized, prioritized action list covering patients, devices, supplies, and staffing.',
    sla: '40s target',
    steps: 4,
    examplePrompts: [
      'Give me a full situational briefing for the ICU',
      'Floor 3 shift handoff — what do I need to know?',
      'Generate a floor status report for Floor 1',
    ],
  },
  {
    id: 'WF-09',
    name: 'Proactive Service Dispatch',
    icon: '🔧',
    type: 'cross-module',
    persona: 'medtech',
    agents: ['Field Service', 'Inventory Management', 'Account Intelligence'],
    trigger: 'field_service.dispatch_needed',
    description: 'Scans the installed base for devices predicted to need service, checks parts availability, and creates an optimized FSE dispatch plan across hospital sites.',
    clinicalValue: 'Shifts field service from reactive to predictive. Reduces unplanned downtime and groups site visits for efficiency.',
    sla: '35s target',
    steps: 5,
    examplePrompts: [
      'Which devices across our hospitals need service in the next 14 days?',
      'Plan proactive service dispatches for the next month',
      'Create an FSE dispatch plan for all critical devices',
    ],
  },
  {
    id: 'WF-10',
    name: 'Post-Market Surveillance',
    icon: '📊',
    type: 'cross-module',
    persona: 'medtech',
    agents: ['Field Service', 'Account Intelligence'],
    trigger: 'field_service.surveillance',
    description: 'Aggregates fleet-wide performance data for a device model, compares firmware versions, detects emerging quality signals, and generates a surveillance summary.',
    clinicalValue: 'Automates FDA post-market surveillance requirements. Detects firmware-related quality issues before they become field safety actions.',
    sla: '30s target',
    steps: 4,
    examplePrompts: [
      'How are our BD Alaris 8015 pumps performing across all hospitals?',
      'Compare firmware performance for Hamilton C6 ventilators',
      'Generate a post-market surveillance report for Philips IntelliVue MX800',
    ],
  },
  {
    id: 'WF-11',
    name: 'Account Health Review',
    icon: '💼',
    type: 'cross-module',
    persona: 'medtech',
    agents: ['Account Intelligence', 'Field Service'],
    trigger: 'account.review',
    description: 'Calculates health scores for all hospital accounts, identifies at-risk customers, reviews service history, and generates a prioritized action plan for the commercial team.',
    clinicalValue: 'Gives sales and customer success teams early warning on churn risk. Quantifies account health with data, not gut feel.',
    sla: '25s target',
    steps: 4,
    examplePrompts: [
      'Show me account health scores for all our hospital customers',
      'Which accounts are at risk of not renewing their contracts?',
      'Generate an account review for Riverside Community Hospital',
    ],
  },
  {
    id: 'WF-16',
    name: 'Regulatory Recall Response',
    icon: '🚨',
    type: 'cross-module',
    persona: 'medtech',
    agents: ['Field Service', 'Inventory Management', 'Account Intelligence'],
    trigger: 'device.recall',
    description: 'When a safety recall is issued, instantly identifies every affected device across all hospitals, assesses risk severity, checks replacement parts, and generates a prioritized FSE dispatch plan.',
    clinicalValue: 'Reduces recall response from days to minutes. Traces every affected device across the installed base with one query.',
    sla: '40s target',
    steps: 5,
    examplePrompts: [
      'Firmware 9.19.1 on BD Alaris 8015 has a safety recall. Show me every affected device and create a response plan.',
      'A recall was issued for Hamilton C6 ventilators on firmware 2.8.0. What is the impact across our hospitals?',
      'How many devices are affected by the BD Alaris firmware recall and which hospitals need immediate attention?',
    ],
  },
  {
    id: 'WF-17',
    name: 'Contract Renewal Package',
    icon: '📄',
    type: 'cross-module',
    persona: 'medtech',
    agents: ['Account Intelligence', 'Field Service'],
    trigger: 'account.renewal',
    description: 'Auto-generates a data-driven contract renewal package — fleet health summary, service value delivered, firmware upgrade benefits, and a risk assessment of non-renewal.',
    clinicalValue: 'Turns renewal conversations from gut feel to data. Shows the customer exactly what value they received and what they would lose.',
    sla: '35s target',
    steps: 4,
    examplePrompts: [
      'Generate a contract renewal package for Riverside Community Hospital',
      'Riverside\'s contract expires in 60 days. Build me a renewal case with fleet health and service value.',
      'What would Lakewood Surgical Center lose if they don\'t renew their service contract?',
    ],
  },
  {
    id: 'WF-18',
    name: 'Competitive Intelligence',
    icon: '🔍',
    type: 'cross-module',
    persona: 'medtech',
    agents: ['Field Service', 'Account Intelligence'],
    trigger: 'account.competitive_threat',
    description: 'Detects early signals that hospitals may be evaluating competitors — declining utilization, deferred updates, service friction — and generates a competitive response strategy per account.',
    clinicalValue: 'Catches churn signals before they become lost deals. Turns device telemetry into competitive intelligence.',
    sla: '30s target',
    steps: 4,
    examplePrompts: [
      'Which accounts are showing signs of evaluating competitor devices?',
      'Are any of our hospital customers at risk of switching to a competitor?',
      'Run a competitive intelligence assessment across all accounts and recommend actions.',
    ],
  },
];

const AgentPill = ({ name }: { name: string }) => {
  const color = AGENT_COLORS[name] || '#6b7280';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 10px', borderRadius: 12, fontSize: '0.78em', fontWeight: 500,
      background: `${color}15`, color, border: `1px solid ${color}30`,
      whiteSpace: 'nowrap',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
      {name}
    </span>
  );
};

interface WorkflowsPageProps {
  onTryWorkflow: (prompt: string) => void;
  persona?: 'hospital' | 'medtech' | null;
}

export default function WorkflowsPage({ onTryWorkflow, persona }: WorkflowsPageProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const showClinical = !persona || persona === 'hospital';
  const showMedtech = !persona || persona === 'medtech';
  const clinicalCross = showClinical ? WORKFLOWS.filter(w => w.persona === 'clinical' && w.type === 'cross-module') : [];
  const clinicalSingle = showClinical ? WORKFLOWS.filter(w => w.persona === 'clinical' && w.type === 'single-agent') : [];
  const medtech = showMedtech ? WORKFLOWS.filter(w => w.persona === 'medtech') : [];
  const totalShown = clinicalCross.length + clinicalSingle.length + medtech.length;

  return (
    <div style={{ overflowY: 'auto', height: 'calc(100vh - 200px)', padding: '0 4px' }}>
      <SpaceBetween size="l">

        {/* Hero */}
        <Container header={<Header variant="h2" description="Click any workflow to see details, then try it with a single click.">Platform Workflows</Header>}>
          <ColumnLayout columns={4}>
            <div style={{ textAlign: 'center' }}>
              <Box variant="h1" color="text-status-info">{totalShown}</Box>
              <Box variant="small">Workflows</Box>
            </div>
            <div style={{ textAlign: 'center' }}>
              <Box variant="h1" color="text-status-warning">{clinicalCross.length + clinicalSingle.length}</Box>
              <Box variant="small">Clinical (Hospital)</Box>
            </div>
            <div style={{ textAlign: 'center' }}>
              <Box variant="h1" color="text-status-success">{medtech.length}</Box>
              <Box variant="small">MedTech (Manufacturer)</Box>
            </div>
            <div style={{ textAlign: 'center' }}>
              <Box variant="h1">7</Box>
              <Box variant="small">AI Agents</Box>
            </div>
          </ColumnLayout>
        </Container>

        {/* Clinical Cross-Module Workflows */}
        {clinicalCross.length > 0 && (
        <Container header={
          <Header variant="h2" description="Hospital-side workflows that coordinate across clinical agents for patient care.">
            <Icon name="share" /> Clinical Workflows — Cross-Module
          </Header>
        }>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 16 }}>
            {clinicalCross.map(wf => (
              <WorkflowCard
                key={wf.id}
                workflow={wf}
                isExpanded={expandedId === wf.id}
                onToggle={() => setExpandedId(expandedId === wf.id ? null : wf.id)}
                onTry={onTryWorkflow}
              />
            ))}
          </div>
        </Container>
        )}

        {/* Clinical Single-Agent Workflows */}
        {clinicalSingle.length > 0 && (
        <Container header={
          <Header variant="h2" description="Specialized workflows that operate within a single clinical agent.">
            <Icon name="status-positive" /> Clinical Workflows — Single-Agent
          </Header>
        }>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 16 }}>
            {clinicalSingle.map(wf => (
              <WorkflowCard
                key={wf.id}
                workflow={wf}
                isExpanded={expandedId === wf.id}
                onToggle={() => setExpandedId(expandedId === wf.id ? null : wf.id)}
                onTry={onTryWorkflow}
              />
            ))}
          </div>
        </Container>
        )}

        {/* MedTech Workflows */}
        {medtech.length > 0 && (
        <Container header={
          <Header variant="h2" description="Manufacturer-side workflows for field service, quality surveillance, and account management across hospital customers.">
            <Icon name="multiscreen" /> MedTech Workflows — Device Manufacturer
          </Header>
        }>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: 16 }}>
            {medtech.map(wf => (
              <WorkflowCard
                key={wf.id}
                workflow={wf}
                isExpanded={expandedId === wf.id}
                onToggle={() => setExpandedId(expandedId === wf.id ? null : wf.id)}
                onTry={onTryWorkflow}
              />
            ))}
          </div>
        </Container>
        )}

      </SpaceBetween>
    </div>
  );
}

function WorkflowCard({
  workflow: wf,
  isExpanded,
  onToggle,
  onTry,
}: {
  workflow: Workflow;
  isExpanded: boolean;
  onToggle: () => void;
  onTry: (prompt: string) => void;
}) {
  const borderColor = wf.persona === 'medtech' ? '#06b6d4' : wf.type === 'cross-module' ? '#8b5cf6' : '#10b981';
  const [simulating, setSimulating] = useState(false);
  const [simulated, setSimulated] = useState(false);

  return (
    <div
      onClick={onToggle}
      role="button"
      tabIndex={0}
      aria-expanded={isExpanded}
      aria-label={`${wf.name} workflow`}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(); } }}
      style={{
        border: `1px solid ${isExpanded ? borderColor : 'var(--color-border-divider-default, #d5dbdb)'}`,
        borderRadius: 12,
        padding: 20,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        background: isExpanded ? `${borderColor}06` : 'var(--color-background-container-content, #fff)',
        boxShadow: isExpanded ? `0 0 0 1px ${borderColor}40` : 'none',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Top accent line */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 3,
        background: `linear-gradient(90deg, ${wf.agents.map(a => AGENT_COLORS[a] || '#6b7280').join(', ')})`,
      }} />

      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: '1.6em' }}>{wf.icon}</span>
          <div>
            <div style={{ fontWeight: 600, fontSize: '1.05em' }}>{wf.name}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}>
              <span style={{ fontSize: '0.75em', color: 'var(--color-text-body-secondary, #687078)', fontFamily: 'monospace' }}>{wf.id}</span>
              <Badge color={wf.type === 'cross-module' ? 'blue' : 'green'}>
                {wf.type === 'cross-module' ? 'Cross-Module' : 'Single-Agent'}
              </Badge>
            </div>
          </div>
        </div>
        <div style={{ textAlign: 'right', fontSize: '0.8em', color: 'var(--color-text-body-secondary, #687078)' }}>
          <div>{wf.steps} steps</div>
          <div>{wf.sla}</div>
        </div>
      </div>

      {/* Agent pills */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
        {wf.agents.map(a => <AgentPill key={a} name={a} />)}
      </div>

      {/* Description */}
      <Box variant="small" color="text-body-secondary">{wf.description}</Box>

      {/* Expanded content */}
      {isExpanded && (
        <div style={{ marginTop: 16, borderTop: '1px solid var(--color-border-divider-default, #d5dbdb)', paddingTop: 14 }}>
          {/* Trigger */}
          <div style={{ marginBottom: 12 }}>
            <Box variant="small"><strong>Trigger event:</strong>{' '}
              <code style={{
                background: 'var(--color-background-badge-icon, #f2f3f3)',
                padding: '2px 8px', borderRadius: 4, fontSize: '0.9em',
              }}>{wf.trigger}</code>
            </Box>
          </div>

          {/* Clinical value */}
          <div style={{
            padding: '10px 14px', borderRadius: 8, marginBottom: 14,
            background: 'linear-gradient(135deg, #10b98110, #3b82f610)',
            border: '1px solid #10b98125',
          }}>
            <Box variant="small">
              <span style={{ marginRight: 6 }}>💡</span>
              <strong>Clinical value:</strong> {wf.clinicalValue}
            </Box>
          </div>

          {/* Try it prompts */}
          <div>
            <Box variant="small"><strong>Try it — click a prompt:</strong></Box>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
              {wf.examplePrompts.map((prompt, i) => (
                <Button
                  key={i}
                  variant="inline-link"
                  onClick={e => { e.stopPropagation(); onTry(prompt); }}
                  ariaLabel={`Try prompt: ${prompt}`}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ color: borderColor }}>▶</span>
                    <span style={{ fontStyle: 'italic', fontSize: '0.92em' }}>"{prompt}"</span>
                  </span>
                </Button>
              ))}
            </div>
          </div>

          {/* Simulate button for telemetry-driven trigger */}
          {wf.simulateScenario && (
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid var(--color-border-divider-default, #d5dbdb)` }}>
              <Button
                variant="normal"
                loading={simulating}
                onClick={async (e) => {
                  e.stopPropagation();
                  setSimulating(true);
                  try {
                    await signedFetch('', {
                      method: 'POST',
                      body: JSON.stringify({ simulate_scenario: wf.simulateScenario }),
                    });
                    setSimulated(true);
                    setTimeout(() => setSimulated(false), 5000);
                  } catch { /* ignore */ }
                  setSimulating(false);
                }}
                ariaLabel={`Simulate ${wf.name} trigger`}
              >
                {simulated ? 'Telemetry Injected — Watch the Bell' : 'Inject Abnormal Telemetry'}
              </Button>
              {simulated && (
                <div style={{ marginTop: 6, padding: '8px 12px', borderRadius: 6, background: '#10b98110', border: '1px solid #10b98130', fontSize: '0.8em' }}>
                  <div style={{ color: '#10b981', fontWeight: 600, marginBottom: 4 }}>Abnormal telemetry injected</div>
                  <div style={{ color: 'var(--color-text-body-secondary, #687078)', lineHeight: 1.4 }}>{wf.simulateDetails}</div>
                  <div style={{ color: '#10b981', marginTop: 6, fontStyle: 'italic' }}>The threshold evaluator will detect this within 10 seconds. Watch the notification bell.</div>
                </div>
              )}
              {!simulated && (
                <Box variant="small" color="text-body-secondary" margin={{ top: 'xxs' }}>
                  Writes abnormal data to trigger this workflow automatically. Watch the notification bell.
                </Box>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
