/**
 * WorkflowTrace — Animated execution trace visualization for orchestrator workflows.
 *
 * Displays a vertical timeline of workflow steps as they execute in real-time.
 * Each step shows: agent name, description, status (with animation), duration.
 */

import { useEffect, useState } from 'react';
import Box from '@cloudscape-design/components/box';
import StatusIndicator from '@cloudscape-design/components/status-indicator';
import ExpandableSection from '@cloudscape-design/components/expandable-section';

export interface TraceStep {
  step: number;
  totalSteps: number;
  agent: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  prompt?: string;
  response?: string;
  durationMs?: number;
}

export interface WorkflowTraceData {
  workflowId: string;
  workflowName: string;
  totalSteps: number;
  status: 'started' | 'completed' | 'failed';
  steps: TraceStep[];
  totalDurationMs?: number;
}

interface WorkflowTraceProps {
  trace: WorkflowTraceData;
}

const AGENT_COLORS: Record<string, string> = {
  'Patient Monitoring': '#0972d3',
  'Device Management': '#037f0c',
  'Patient Engagement': '#5f6b7a',
  'Inventory Management': '#ec4899',
  'Field Service': '#06b6d4',
  'Account Intelligence': '#f97316',
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export default function WorkflowTrace({ trace }: WorkflowTraceProps) {
  return (
    <div className="workflow-trace">
      <Box variant="h4" margin={{ bottom: 's' }}>
        {trace.workflowId}: {trace.workflowName}
      </Box>

      <div className="trace-timeline">
        {trace.steps.map((step, idx) => (
          <TraceStepCard key={step.step} step={step} isLast={idx === trace.steps.length - 1} />
        ))}
      </div>

      {trace.status === 'completed' && trace.totalDurationMs && (
        <div className="trace-summary">
          <Box variant="h4" margin={{ top: 'm', bottom: 'xs' }}>Execution Summary</Box>
          <table className="trace-summary-table">
            <thead>
              <tr>
                <th>Step</th>
                <th>Agent</th>
                <th>Status</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {trace.steps.map(s => (
                <tr key={s.step}>
                  <td>{s.step}</td>
                  <td>{s.agent}</td>
                  <td>{s.status === 'completed' ? 'COMPLETED' : 'FAILED'}</td>
                  <td>{s.durationMs ? formatDuration(s.durationMs) : '-'}</td>
                </tr>
              ))}
              <tr className="trace-total-row">
                <td colSpan={3}>Total</td>
                <td>{formatDuration(trace.totalDurationMs)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function TraceStepCard({ step, isLast }: { step: TraceStep; isLast: boolean }) {
  const [animate, setAnimate] = useState(false);
  const agentColor = AGENT_COLORS[step.agent] || '#5f6b7a';

  useEffect(() => {
    if (step.status === 'in_progress') {
      setAnimate(true);
    } else {
      // Brief highlight when completing
      setAnimate(true);
      const timer = setTimeout(() => setAnimate(false), 600);
      return () => clearTimeout(timer);
    }
  }, [step.status]);

  return (
    <div className={`trace-step ${step.status} ${animate && step.status === 'completed' ? 'just-completed' : ''}`}>
      {/* Timeline connector */}
      <div className="trace-connector">
        <div className={`trace-dot ${step.status}`} style={{ borderColor: agentColor }} />
        {!isLast && <div className="trace-line" />}
      </div>

      {/* Step content */}
      <div className="trace-content">
        <div className="trace-header">
          <span className="trace-step-num">Step {step.step}</span>
          <span className="trace-agent" style={{ color: agentColor }}>{step.agent}</span>
          <span className="trace-status">
            {step.status === 'pending' && <StatusIndicator type="pending">PENDING</StatusIndicator>}
            {step.status === 'in_progress' && <StatusIndicator type="in-progress">IN PROGRESS</StatusIndicator>}
            {step.status === 'completed' && <StatusIndicator type="success">COMPLETED</StatusIndicator>}
            {step.status === 'failed' && <StatusIndicator type="error">FAILED</StatusIndicator>}
          </span>
          {step.durationMs !== undefined && step.status !== 'pending' && step.status !== 'in_progress' && (
            <span className="trace-duration">{formatDuration(step.durationMs)}</span>
          )}
        </div>

        <div className="trace-description">{step.description}</div>

        {(step.prompt || step.response) && step.status !== 'pending' && (
          <ExpandableSection headerText="Details" variant="footer">
            {step.prompt && (
              <Box margin={{ bottom: 'xs' }}>
                <Box variant="awsui-key-label">Prompt sent</Box>
                <Box variant="code">{step.prompt}</Box>
              </Box>
            )}
            {step.response && (
              <Box>
                <Box variant="awsui-key-label">Agent response</Box>
                <Box variant="code">{step.response}</Box>
              </Box>
            )}
          </ExpandableSection>
        )}
      </div>
    </div>
  );
}
