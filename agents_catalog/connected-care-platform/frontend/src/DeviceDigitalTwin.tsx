/**
 * DeviceDigitalTwin — Full-page device lifecycle view with predictive maintenance,
 * peer comparison, patient assignments, firmware journey, and auto-refresh.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import SpaceBetween from '@cloudscape-design/components/space-between';
import ColumnLayout from '@cloudscape-design/components/column-layout';
import Box from '@cloudscape-design/components/box';
import Button from '@cloudscape-design/components/button';
import Spinner from '@cloudscape-design/components/spinner';
import StatusIndicator from '@cloudscape-design/components/status-indicator';
import Badge from '@cloudscape-design/components/badge';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { signedFetch } from './auth';

interface TelemetryPoint {
  timestamp: string;
  battery_level: number;
  error_count: number;
  sensor_accuracy: number;
  calibration_drift: number;
}

interface ServiceVisit {
  visit_id: string;
  date: string;
  type: string;
  engineer: string;
  parts_used: string[];
  outcome: string;
  notes: string;
  duration_hours: number;
}

interface PeerDevice {
  device_id: string;
  site_name: string;
  location: string;
  firmware_version: string;
  risk_profile: string;
  error_count: number;
  sensor_accuracy: number;
  calibration_drift: number;
  battery_level: number;
}

interface Prediction {
  days_until_service: number | null;
  urgency: string;
  issues: string[];
}

interface TwinData {
  device_id: string;
  model: string;
  device_type: string;
  serial_number: string;
  location: string;
  floor: string;
  status: string;
  risk_profile: string;
  firmware_version: string;
  latest_firmware: string;
  firmware_current: boolean;
  installation_date: string;
  last_maintenance_date: string;
  notes: string;
  site: { site_id: string; site_name: string; city: string; state: string };
  telemetry: Record<string, number>;
  telemetry_history: TelemetryPoint[];
  service_history: ServiceVisit[];
  patient_assignment: { patient_id: string; assigned_date: string } | null;
  peer_devices: PeerDevice[];
  prediction: Prediction;
}

interface Props {
  deviceId: string;
  onBack: () => void;
}

const RISK_COLORS: Record<string, string> = { critical: '#ef4444', moderate: '#f59e0b', healthy: '#10b981' };
const URGENCY_COLORS: Record<string, string> = { CRITICAL: '#ef4444', HIGH: '#f59e0b', MODERATE: '#3b82f6', LOW: '#10b981' };
const STATUS_TYPE: Record<string, 'success' | 'warning' | 'error' | 'info'> = { active: 'success', maintenance: 'warning', offline: 'error', decommissioned: 'info', completed: 'success', partial: 'warning', scheduled: 'info' };

// Sparkline
const Sparkline: React.FC<{ data: TelemetryPoint[]; dataKey: string; label: string; unit: string; color: string; invertThreshold?: boolean }> = ({ data, dataKey, label, unit, color, invertThreshold }) => {
  const isDark = document.body.classList.contains('awsui-dark');
  const gridColor = isDark ? '#334155' : '#e2e8f0';
  const tickColor = isDark ? '#94a3b8' : '#64748b';
  const cardBg = isDark ? '#0f1b2a' : '#ffffff';
  const cardBorder = isDark ? '#414d5c' : '#d5dbdb';

  const values = data.map(d => (d as unknown as Record<string, number>)[dataKey]).filter(v => !isNaN(v));
  const latest = values[values.length - 1];
  const trend = values.length >= 2 ? values[values.length - 1] - values[0] : 0;
  const trendLabel = trend > 0 ? `+${trend.toFixed(1)}` : trend.toFixed(1);
  const isWorsening = invertThreshold ? trend < 0 : trend > 0;

  return (
    <div style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 10, padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ fontSize: '0.78em', color: tickColor }}>{label}</span>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
          <span style={{ fontSize: '1.2em', fontWeight: 700, color }}>{latest?.toFixed(dataKey === 'calibration_drift' ? 1 : 0)}</span>
          <span style={{ fontSize: '0.7em', color: tickColor }}>{unit}</span>
        </div>
      </div>
      <div style={{ fontSize: '0.7em', color: isWorsening ? '#ef4444' : '#10b981', marginBottom: 4 }}>{trendLabel} {unit} trend</div>
      <ResponsiveContainer width="100%" height={60}>
        <AreaChart data={data} margin={{ top: 2, right: 2, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id={`grad-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="timestamp" hide />
          <YAxis hide />
          <Tooltip contentStyle={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 6, fontSize: '0.75em' }} />
          <Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} fill={`url(#grad-${dataKey})`} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

const DeviceDigitalTwin: React.FC<Props> = ({ deviceId, onBack }) => {
  const [twin, setTwin] = useState<TwinData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const refreshRef = useRef<number | null>(null);

  const fetchTwin = useCallback(async () => {
    try {
      const res = await signedFetch(`?device_twin=${deviceId}`);
      const data = await res.json();
      if (data.error) setError(data.error);
      else { setTwin(data); setError(''); }
      setLastRefresh(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => {
    setLoading(true);
    fetchTwin();
    // Auto-refresh every 30 seconds
    refreshRef.current = window.setInterval(fetchTwin, 30000);
    return () => { if (refreshRef.current) clearInterval(refreshRef.current); };
  }, [fetchTwin]);

  if (loading && !twin) return <Box textAlign="center" padding="xxxl"><Spinner size="large" /> Loading digital twin...</Box>;
  if (error && !twin) return <Box textAlign="center" padding="xxxl"><StatusIndicator type="error">{error}</StatusIndicator></Box>;
  if (!twin) return null;

  const isDark = document.body.classList.contains('awsui-dark');
  const riskColor = RISK_COLORS[twin.risk_profile] || '#6b7280';
  const textSecondary = isDark ? '#94a3b8' : '#687078';
  const cardBg = isDark ? '#192534' : '#ffffff';
  const cardBorder = isDark ? '#414d5c' : '#d5dbdb';

  return (
    <div style={{ overflowY: 'auto', height: 'calc(100vh - 120px)', padding: '0 4px' }}>
      <SpaceBetween size="l">
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Button iconName="arrow-left" variant="icon" onClick={onBack} ariaLabel="Back to chat" />
            <Header variant="h1">Device Digital Twin — {twin.device_id}</Header>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: '0.75em', color: textSecondary }}>
              Last updated: {lastRefresh.toLocaleTimeString()}
            </span>
            <Button iconName="refresh" variant="icon" onClick={fetchTwin} ariaLabel="Refresh" />
          </div>
        </div>

        {/* Predictive Failure Countdown + Identity */}
        <ColumnLayout columns={2}>
          {/* Identity Card */}
          <Container header={<Header variant="h2">{twin.model} <Badge color={twin.status === 'active' ? 'green' : 'red'}>{twin.status.toUpperCase()}</Badge></Header>}>
            <ColumnLayout columns={2}>
              <div><Box variant="small" color="text-body-secondary">Device ID</Box><Box variant="p"><code>{twin.device_id}</code></Box></div>
              <div><Box variant="small" color="text-body-secondary">Serial</Box><Box variant="p">{twin.serial_number}</Box></div>
              <div><Box variant="small" color="text-body-secondary">Type</Box><Box variant="p">{twin.device_type?.replace(/_/g, ' ')}</Box></div>
              <div><Box variant="small" color="text-body-secondary">Location</Box><Box variant="p">{twin.site.site_name} — {twin.location}</Box></div>
              <div><Box variant="small" color="text-body-secondary">Installed</Box><Box variant="p">{twin.installation_date}</Box></div>
              <div><Box variant="small" color="text-body-secondary">Last Maintenance</Box><Box variant="p">{twin.last_maintenance_date}</Box></div>
              <div>
                <Box variant="small" color="text-body-secondary">Firmware</Box>
                <Box variant="p">
                  {twin.firmware_version}
                  {!twin.firmware_current && <span style={{ marginLeft: 8, fontSize: '0.8em', color: '#f59e0b' }}>Update: {twin.latest_firmware}</span>}
                </Box>
              </div>
              <div>
                <Box variant="small" color="text-body-secondary">Risk Profile</Box>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '2px 10px', borderRadius: 6, background: `${riskColor}15`, color: riskColor, fontWeight: 600, fontSize: '0.9em' }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: riskColor }} />
                  {twin.risk_profile?.toUpperCase()}
                </div>
              </div>
            </ColumnLayout>
            {twin.patient_assignment && (
              <Box margin={{ top: 's' }} variant="small">
                Currently assigned to patient <code>{twin.patient_assignment.patient_id}</code> since {twin.patient_assignment.assigned_date}
              </Box>
            )}
            {twin.notes && <Box variant="small" color="text-body-secondary" margin={{ top: 'xs' }}>{twin.notes}</Box>}
          </Container>

          {/* Predictive Maintenance */}
          <Container header={<Header variant="h2">Predictive Maintenance</Header>}>
            {twin.prediction.days_until_service !== null ? (
              <div style={{ textAlign: 'center', padding: '16px 0' }}>
                <div style={{ fontSize: '3.5em', fontWeight: 800, color: URGENCY_COLORS[twin.prediction.urgency] || '#6b7280', lineHeight: 1 }}>
                  {twin.prediction.days_until_service}
                </div>
                <div style={{ fontSize: '1em', color: textSecondary, marginTop: 4 }}>days until service needed</div>
                <div style={{
                  display: 'inline-block', marginTop: 8, padding: '4px 16px', borderRadius: 20,
                  background: `${URGENCY_COLORS[twin.prediction.urgency]}15`,
                  color: URGENCY_COLORS[twin.prediction.urgency],
                  fontWeight: 600, fontSize: '0.85em',
                }}>
                  {twin.prediction.urgency}
                </div>
                <div style={{ marginTop: 16, textAlign: 'left' }}>
                  {twin.prediction.issues.map((issue, i) => (
                    <div key={i} style={{ fontSize: '0.82em', padding: '4px 0', color: textSecondary, borderBottom: `1px solid ${cardBorder}` }}>
                      {issue}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '24px 0' }}>
                <div style={{ fontSize: '1.5em', color: '#10b981', fontWeight: 700 }}>All Clear</div>
                <div style={{ fontSize: '0.85em', color: textSecondary, marginTop: 4 }}>No service predicted in the near term</div>
              </div>
            )}
          </Container>
        </ColumnLayout>

        {/* Telemetry Sparklines */}
        <Container header={<Header variant="h2">Telemetry Trends <span style={{ fontSize: '0.6em', color: textSecondary, fontWeight: 400 }}>auto-refreshes every 30s</span></Header>}>
          {twin.telemetry_history.length > 0 ? (
            <ColumnLayout columns={4}>
              <Sparkline data={twin.telemetry_history} dataKey="battery_level" label="Battery Level" unit="%" color="#3b82f6" invertThreshold />
              <Sparkline data={twin.telemetry_history} dataKey="error_count" label="Error Count" unit="errors" color="#ef4444" />
              <Sparkline data={twin.telemetry_history} dataKey="sensor_accuracy" label="Sensor Accuracy" unit="%" color="#10b981" invertThreshold />
              <Sparkline data={twin.telemetry_history} dataKey="calibration_drift" label="Calibration Drift" unit="%" color="#f59e0b" />
            </ColumnLayout>
          ) : (
            <Box variant="small" color="text-body-secondary">No telemetry history available.</Box>
          )}
          {twin.telemetry && Object.keys(twin.telemetry).length > 0 && (
            <div style={{ marginTop: 16 }}>
              <Box variant="small" color="text-body-secondary" margin={{ bottom: 'xs' }}>Current Readings</Box>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {Object.entries(twin.telemetry).map(([key, val]) => {
                  if (typeof val !== 'number') return null;
                  return (
                    <div key={key} style={{ padding: '4px 12px', borderRadius: 6, fontSize: '0.8em', background: isDark ? '#192534' : '#f8f9fa', border: `1px solid ${cardBorder}` }}>
                      <span style={{ color: textSecondary }}>{key.replace(/_/g, ' ')}: </span>
                      <span style={{ fontWeight: 600 }}>{val.toFixed(1)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </Container>

        {/* Peer Comparison */}
        {twin.peer_devices.length > 0 && (
          <Container header={<Header variant="h2">Fleet Peers — {twin.model} ({twin.peer_devices.length + 1} total)</Header>}>
            <div style={{ marginBottom: 12 }}>
              <Box variant="small" color="text-body-secondary">Error count comparison across all {twin.model} devices</Box>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart
                data={[
                  { name: `${twin.device_id} (this)`, errors: twin.telemetry.error_count || 0, isCurrent: true },
                  ...twin.peer_devices.map(p => ({ name: p.device_id, errors: p.error_count, isCurrent: false })),
                ]}
                margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#334155' : '#e2e8f0'} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: textSecondary }} />
                <YAxis tick={{ fontSize: 10, fill: textSecondary }} />
                <Tooltip contentStyle={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 6, fontSize: '0.8em' }} />
                <Bar dataKey="errors" name="Error Count" radius={[4, 4, 0, 0]}>
                  {[
                    { errors: twin.telemetry.error_count || 0, isCurrent: true },
                    ...twin.peer_devices.map(p => ({ errors: p.error_count, isCurrent: false })),
                  ].map((entry, i) => (
                    <Cell key={i} fill={entry.isCurrent ? '#8b5cf6' : entry.errors > 50 ? '#ef4444' : entry.errors > 20 ? '#f59e0b' : '#10b981'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            {/* Peer table */}
            <div style={{ marginTop: 12, overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82em' }}>
                <thead>
                  <tr style={{ borderBottom: `2px solid ${cardBorder}` }}>
                    {['Device', 'Site', 'Location', 'Firmware', 'Errors', 'Accuracy', 'Drift', 'Battery', 'Risk'].map(h => (
                      <th key={h} style={{ padding: '6px 10px', textAlign: 'left', color: textSecondary, fontWeight: 600 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {/* Current device row */}
                  <tr style={{ background: isDark ? '#1e293b' : '#f0f4ff', borderBottom: `1px solid ${cardBorder}` }}>
                    <td style={{ padding: '6px 10px', fontWeight: 600 }}>{twin.device_id} (this)</td>
                    <td style={{ padding: '6px 10px' }}>{twin.site.site_name}</td>
                    <td style={{ padding: '6px 10px' }}>{twin.location}</td>
                    <td style={{ padding: '6px 10px' }}><code>{twin.firmware_version}</code></td>
                    <td style={{ padding: '6px 10px', color: (twin.telemetry.error_count || 0) > 50 ? '#ef4444' : undefined }}>{twin.telemetry.error_count?.toFixed(0) || 0}</td>
                    <td style={{ padding: '6px 10px' }}>{twin.telemetry.sensor_accuracy?.toFixed(1) || '-'}%</td>
                    <td style={{ padding: '6px 10px' }}>{twin.telemetry.calibration_drift?.toFixed(1) || '-'}%</td>
                    <td style={{ padding: '6px 10px' }}>{twin.telemetry.battery_level?.toFixed(0) || '-'}%</td>
                    <td style={{ padding: '6px 10px' }}><span style={{ color: RISK_COLORS[twin.risk_profile] }}>{twin.risk_profile?.toUpperCase()}</span></td>
                  </tr>
                  {twin.peer_devices.map((p, i) => (
                    <tr key={i} style={{ borderBottom: `1px solid ${cardBorder}` }}>
                      <td style={{ padding: '6px 10px' }}>{p.device_id}</td>
                      <td style={{ padding: '6px 10px' }}>{p.site_name}</td>
                      <td style={{ padding: '6px 10px' }}>{p.location}</td>
                      <td style={{ padding: '6px 10px' }}><code>{p.firmware_version}</code></td>
                      <td style={{ padding: '6px 10px', color: p.error_count > 50 ? '#ef4444' : undefined }}>{p.error_count}</td>
                      <td style={{ padding: '6px 10px' }}>{p.sensor_accuracy.toFixed(1)}%</td>
                      <td style={{ padding: '6px 10px' }}>{p.calibration_drift.toFixed(1)}%</td>
                      <td style={{ padding: '6px 10px' }}>{p.battery_level.toFixed(0)}%</td>
                      <td style={{ padding: '6px 10px' }}><span style={{ color: RISK_COLORS[p.risk_profile] }}>{p.risk_profile?.toUpperCase()}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Container>
        )}

        {/* Firmware Journey */}
        <Container header={<Header variant="h2">Firmware Journey</Header>}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 0, overflowX: 'auto', padding: '12px 0' }}>
            {/* Build firmware journey from service history + current */}
            {(() => {
              const fwSteps: { version: string; date: string; isCurrent: boolean }[] = [];
              // Extract firmware updates from service notes
              const fwPattern = /firmware.*?(\d+\.\d+\.\d+)/i;
              for (const visit of [...twin.service_history].reverse()) {
                const match = visit.notes?.match(fwPattern);
                if (match) {
                  fwSteps.push({ version: match[1], date: visit.date, isCurrent: false });
                }
              }
              // Add installation firmware (estimate from installation date)
              if (fwSteps.length === 0) {
                fwSteps.push({ version: twin.firmware_version, date: twin.installation_date, isCurrent: true });
              } else {
                // Add current if different from last step
                const lastStep = fwSteps[fwSteps.length - 1];
                if (lastStep.version !== twin.firmware_version) {
                  fwSteps.push({ version: twin.firmware_version, date: 'Current', isCurrent: true });
                } else {
                  lastStep.isCurrent = true;
                }
              }

              return fwSteps.map((step, i) => (
                <React.Fragment key={i}>
                  <div style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 120,
                    padding: '8px 16px', borderRadius: 10,
                    background: step.isCurrent ? `${riskColor}10` : 'transparent',
                    border: step.isCurrent ? `2px solid ${riskColor}` : `1px solid ${cardBorder}`,
                  }}>
                    <code style={{ fontSize: '1em', fontWeight: 700, color: step.isCurrent ? riskColor : textSecondary }}>
                      v{step.version}
                    </code>
                    <span style={{ fontSize: '0.7em', color: textSecondary, marginTop: 2 }}>{step.date}</span>
                    {step.isCurrent && (
                      <span style={{ fontSize: '0.65em', color: riskColor, fontWeight: 600, marginTop: 2 }}>CURRENT</span>
                    )}
                  </div>
                  {i < fwSteps.length - 1 && (
                    <div style={{ width: 40, height: 2, background: isDark ? '#475569' : '#cbd5e1', flexShrink: 0 }} />
                  )}
                </React.Fragment>
              ));
            })()}
            {/* Show target firmware if not current */}
            {!twin.firmware_current && (
              <>
                <div style={{ width: 40, height: 2, background: '#f59e0b', flexShrink: 0, borderStyle: 'dashed' }} />
                <div style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 120,
                  padding: '8px 16px', borderRadius: 10,
                  border: '2px dashed #f59e0b', background: '#f59e0b08',
                }}>
                  <code style={{ fontSize: '1em', fontWeight: 700, color: '#f59e0b' }}>v{twin.latest_firmware}</code>
                  <span style={{ fontSize: '0.7em', color: '#f59e0b', marginTop: 2 }}>TARGET</span>
                </div>
              </>
            )}
          </div>
        </Container>

        {/* Service History */}
        <Container header={<Header variant="h2">Service History ({twin.service_history.length} visits)</Header>}>
          {twin.service_history.length > 0 ? (
            <div style={{ position: 'relative', paddingLeft: 24 }}>
              <div style={{ position: 'absolute', left: 9, top: 8, bottom: 8, width: 2, background: isDark ? '#334155' : '#d5dbdb' }} />
              {twin.service_history.map((visit, i) => {
                const outcomeColor = visit.outcome === 'completed' ? '#10b981' : visit.outcome === 'partial' ? '#f59e0b' : '#6b7280';
                return (
                  <div key={i} style={{ position: 'relative', marginBottom: 16 }}>
                    <div style={{
                      position: 'absolute', left: -18, top: 6, width: 12, height: 12, borderRadius: '50%',
                      background: outcomeColor, border: `2px solid ${isDark ? '#0f1b2a' : '#fafafa'}`,
                    }} />
                    <div style={{
                      background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 8,
                      padding: '12px 16px', borderLeft: `3px solid ${outcomeColor}`,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontWeight: 600, fontSize: '0.9em' }}>{visit.date}</span>
                          <Badge color={visit.type === 'corrective' ? 'red' : 'blue'}>{visit.type}</Badge>
                          <StatusIndicator type={STATUS_TYPE[visit.outcome] || 'info'}>{visit.outcome}</StatusIndicator>
                        </div>
                        <span style={{ fontSize: '0.8em', color: textSecondary }}>{visit.duration_hours}h — {visit.engineer}</span>
                      </div>
                      {visit.notes && <Box variant="small">{visit.notes}</Box>}
                      {visit.parts_used.length > 0 && (
                        <div style={{ marginTop: 6, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          {visit.parts_used.map((part, j) => (
                            <span key={j} style={{ fontSize: '0.72em', padding: '2px 8px', borderRadius: 4, background: isDark ? '#1e293b' : '#f1f5f9', color: textSecondary }}>{part}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <Box variant="small" color="text-body-secondary">No service visits recorded for this device.</Box>
          )}
        </Container>
      </SpaceBetween>
    </div>
  );
};

export default DeviceDigitalTwin;
