/**
 * NotificationBell — Proactive alert system with real-time polling,
 * toast popup on new alerts, and clear all functionality.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import Badge from '@cloudscape-design/components/badge';
import Box from '@cloudscape-design/components/box';
import Button from '@cloudscape-design/components/button';
import SpaceBetween from '@cloudscape-design/components/space-between';
import StatusIndicator from '@cloudscape-design/components/status-indicator';
import { signedFetch } from './auth';

interface ReasoningFactor {
  factor: string;
  source: string;
  weight: 'high' | 'medium' | 'low';
}

interface Notification {
  notification_id: string;
  patient_id: string;
  patient_name: string;
  room: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  workflow_id: string;
  reasoning: ReasoningFactor[];
  recommended_action?: string;
  timestamp: string;
  acknowledged: boolean;
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#dc2626', HIGH: '#ef4444', MEDIUM: '#f59e0b', LOW: '#3b82f6',
};
const SEVERITY_INDICATOR: Record<string, 'error' | 'warning' | 'info'> = {
  CRITICAL: 'error', HIGH: 'error', MEDIUM: 'warning', LOW: 'info',
};
const WEIGHT_ICONS: Record<string, string> = { high: '●', medium: '◐', low: '○' };

interface NotificationBellProps {
  onInvestigate: (prompt: string) => void;
}

export default function NotificationBell({ onInvestigate }: NotificationBellProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [toast, setToast] = useState<Notification | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<number | null>(null);
  const knownIdsRef = useRef<Set<string>>(new Set());

  const unreadCount = notifications.filter(n => !n.acknowledged).length;

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await signedFetch('?proactive_alerts=unacknowledged');
      const data = await res.json();
      if (data.alerts && Array.isArray(data.alerts)) {
        const newNotifs: Notification[] = [];
        for (const a of data.alerts) {
          const id = a.alert_id || a.notification_id || '';
          if (!id || knownIdsRef.current.has(id)) continue;
          knownIdsRef.current.add(id);
          const notif: Notification = {
            notification_id: id,
            patient_id: a.patient_id || '',
            patient_name: a.patient_name || 'Unknown',
            room: a.room || '',
            severity: a.severity || 'HIGH',
            title: a.title || 'Alert',
            workflow_id: a.workflow_id || '',
            reasoning: Array.isArray(a.reasoning) ? a.reasoning : [],
            recommended_action: a.recommended_action || '',
            timestamp: a.timestamp || new Date().toISOString(),
            acknowledged: false,
          };
          newNotifs.push(notif);
        }
        if (newNotifs.length > 0) {
          setNotifications(prev => [...newNotifs, ...prev]);
          // Show toast for the most severe new alert
          setToast(newNotifs[0]);
          setTimeout(() => setToast(null), 8000);
        }
      }
    } catch {
      // Silently ignore — will retry on next poll
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    pollRef.current = window.setInterval(fetchAlerts, 10000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetchAlerts]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) setIsOpen(false);
    };
    if (isOpen) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [isOpen]);

  const acknowledge = useCallback((id: string) => {
    setNotifications(prev => prev.map(n => n.notification_id === id ? { ...n, acknowledged: true } : n));
    signedFetch(`?acknowledge_alert=${id}`).catch(() => {});
  }, []);

  const clearAll = useCallback(() => {
    notifications.forEach(n => {
      if (!n.acknowledged) signedFetch(`?acknowledge_alert=${n.notification_id}`).catch(() => {});
    });
    setNotifications([]);
    knownIdsRef.current.clear();
  }, [notifications]);

  const handleInvestigate = useCallback((n: Notification) => {
    acknowledge(n.notification_id);
    setIsOpen(false);
    setToast(null);
    const prompts: Record<string, string> = {
      'WF-01': `Investigate fall risk for ${n.patient_name} (${n.patient_id}) in ${n.room}. ${n.reasoning.map(r => r.factor).join('. ')}`,
      'WF-03': `Patient ${n.patient_name} (${n.patient_id}) in ${n.room} is showing deterioration signs. ${n.reasoning.map(r => r.factor).join('. ')}. Activate the deterioration cascade.`,
      'WF-04': `Device failure risk detected: ${n.title}. ${n.reasoning.map(r => r.factor).join('. ')}. Assess patient impact.`,
      'WF-06': `Critical supply shortage: ${n.title}. ${n.reasoning.map(r => r.factor).join('. ')}. Assess patient impact and find alternatives.`,
      'WF-10': `Pressure injury risk for ${n.patient_name} (${n.patient_id}) in ${n.room}. ${n.reasoning.map(r => r.factor).join('. ')}. Investigate and recommend actions.`,
    };
    onInvestigate(prompts[n.workflow_id] || `Investigate alert: ${n.title} for ${n.patient_name} (${n.patient_id})`);
  }, [acknowledge, onInvestigate]);

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    const mins = Math.round((Date.now() - d.getTime()) / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    return `${Math.round(mins / 60)}h ago`;
  };

  return (
    <div ref={panelRef} style={{ position: 'relative' }}>
      {/* Toast popup for new alerts */}
      {toast && (
        <div style={{
          position: 'fixed', top: 20, right: 20, zIndex: 2000,
          width: 420, padding: '16px 20px', borderRadius: 12,
          background: 'var(--color-background-container-content, #fff)',
          border: `2px solid ${SEVERITY_COLORS[toast.severity] || '#ef4444'}`,
          boxShadow: `0 8px 32px ${SEVERITY_COLORS[toast.severity]}30, 0 2px 8px rgba(0,0,0,0.1)`,
          animation: 'slideIn 0.3s ease-out',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <StatusIndicator type={SEVERITY_INDICATOR[toast.severity] || 'error'}>{toast.severity}</StatusIndicator>
                <span style={{ fontFamily: 'monospace', fontSize: '0.75em', color: '#687078' }}>{toast.workflow_id}</span>
              </div>
              <div style={{ fontWeight: 700, fontSize: '1em', marginBottom: 4 }}>{toast.title}</div>
              <div style={{ fontSize: '0.85em', color: '#687078' }}>
                {toast.patient_name} ({toast.patient_id}) — {toast.room}
              </div>
              {toast.reasoning[0] && (
                <div style={{ marginTop: 8, fontSize: '0.82em', padding: '6px 10px', borderRadius: 6, background: `${SEVERITY_COLORS[toast.severity]}08` }}>
                  {toast.reasoning[0].factor}
                </div>
              )}
              {toast.recommended_action && (
                <div style={{ marginTop: 6, fontSize: '0.8em', fontWeight: 500, color: SEVERITY_COLORS[toast.severity] }}>
                  {toast.recommended_action}
                </div>
              )}
            </div>
            <button onClick={() => setToast(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2em', color: '#687078', padding: '0 0 0 8px' }}>x</button>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <Button variant="primary" onClick={() => handleInvestigate(toast)}>Investigate Now</Button>
            <Button variant="normal" onClick={() => { acknowledge(toast.notification_id); setToast(null); }}>Dismiss</Button>
          </div>
          <style>{`@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }`}</style>
        </div>
      )}

      {/* Bell button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label={`Notifications: ${unreadCount} unread`}
        style={{
          background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px',
          position: 'relative', fontSize: '1.3em', lineHeight: 1,
          animation: unreadCount > 0 ? 'bellShake 0.5s ease-in-out' : 'none',
        }}
      >
        🔔
        {unreadCount > 0 && (
          <span style={{
            position: 'absolute', top: 0, right: 2,
            background: '#ef4444', color: '#fff',
            borderRadius: '50%', width: 18, height: 18,
            fontSize: '0.55em', fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {unreadCount}
          </span>
        )}
        <style>{`@keyframes bellShake { 0%,100% { transform: rotate(0); } 25% { transform: rotate(15deg); } 75% { transform: rotate(-15deg); } }`}</style>
      </button>

      {/* Notification panel */}
      {isOpen && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, zIndex: 1000,
          width: 440, maxHeight: '70vh', overflowY: 'auto',
          background: 'var(--color-background-container-content, #fff)',
          border: '1px solid var(--color-border-divider-default, #d5dbdb)',
          borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
        }}>
          <div style={{
            padding: '12px 16px', borderBottom: '1px solid var(--color-border-divider-default, #d5dbdb)',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <Box variant="h4">Proactive Alerts</Box>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Badge color={unreadCount > 0 ? 'red' : 'grey'}>{unreadCount} unread</Badge>
              {notifications.length > 0 && (
                <button onClick={clearAll} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '0.75em', color: '#687078', textDecoration: 'underline' }}>
                  Clear all
                </button>
              )}
            </div>
          </div>
          <div style={{ padding: '8px' }}>
            {notifications.length === 0 ? (
              <Box variant="small" color="text-body-secondary" textAlign="center" padding="l">
                No alerts. Inject abnormal telemetry from the Workflows page to trigger one.
              </Box>
            ) : (
              <SpaceBetween size="xs">
                {notifications.map(n => (
                  <NotificationCard key={n.notification_id} notification={n} onAcknowledge={acknowledge} onInvestigate={handleInvestigate} timeLabel={formatTime(n.timestamp)} />
                ))}
              </SpaceBetween>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function NotificationCard({
  notification: n, onAcknowledge, onInvestigate, timeLabel,
}: {
  notification: Notification; onAcknowledge: (id: string) => void; onInvestigate: (n: Notification) => void; timeLabel: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const color = SEVERITY_COLORS[n.severity] || '#6b7280';

  return (
    <div style={{
      border: `1px solid ${n.acknowledged ? 'var(--color-border-divider-default, #d5dbdb)' : color + '50'}`,
      borderRadius: 10, padding: '12px 14px',
      background: n.acknowledged ? 'transparent' : `${color}06`,
      opacity: n.acknowledged ? 0.6 : 1, transition: 'all 0.2s ease',
      borderLeft: `3px solid ${color}`,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <StatusIndicator type={SEVERITY_INDICATOR[n.severity] || 'info'}>{n.severity}</StatusIndicator>
            <span style={{ fontSize: '0.75em', color: 'var(--color-text-body-secondary, #687078)', fontFamily: 'monospace' }}>{n.workflow_id}</span>
          </div>
          <div style={{ fontWeight: 600, fontSize: '0.92em' }}>{n.title}</div>
          <div style={{ fontSize: '0.82em', color: 'var(--color-text-body-secondary, #687078)', marginTop: 2 }}>
            {n.patient_name} ({n.patient_id}) — {n.room} — {timeLabel}
          </div>
        </div>
      </div>
      <div style={{ marginTop: 8, padding: '6px 10px', borderRadius: 6, background: 'var(--color-background-container-content, #f8f9fa)', fontSize: '0.82em' }}>
        {n.reasoning[0] && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ color }}>{WEIGHT_ICONS[n.reasoning[0]?.weight || 'medium']}</span>
            <span>{n.reasoning[0]?.factor}</span>
          </div>
        )}
        {n.reasoning.length > 1 && !expanded && (
          <button onClick={() => setExpanded(true)} style={{ background: 'none', border: 'none', cursor: 'pointer', color, fontSize: '0.9em', padding: '4px 0 0', fontWeight: 500 }}>
            + {n.reasoning.length - 1} more factors
          </button>
        )}
        {expanded && n.reasoning.slice(1).map((r, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
            <span style={{ color }}>{WEIGHT_ICONS[r.weight]}</span>
            <span>{r.factor}</span>
          </div>
        ))}
        {expanded && n.recommended_action && (
          <div style={{ marginTop: 8, padding: '6px 8px', borderRadius: 4, background: `${color}10`, border: `1px solid ${color}20`, fontWeight: 500 }}>
            Recommended: {n.recommended_action}
          </div>
        )}
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
        <Button variant="primary" onClick={() => onInvestigate(n)}>Investigate</Button>
        {!n.acknowledged && <Button variant="normal" onClick={() => onAcknowledge(n.notification_id)}>Acknowledge</Button>}
      </div>
    </div>
  );
}
