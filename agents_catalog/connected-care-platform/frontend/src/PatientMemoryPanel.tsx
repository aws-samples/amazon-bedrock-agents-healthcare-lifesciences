/**
 * PatientMemoryPanel — Collapsible sidebar showing a patient's memory timeline.
 *
 * Polls the proxy endpoint for memory entries and renders them as a vertical timeline.
 * Updates when a patient ID is detected in the chat.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Box from '@cloudscape-design/components/box';
import Button from '@cloudscape-design/components/button';
import Spinner from '@cloudscape-design/components/spinner';
import { signedFetch } from './auth';

interface MemoryEntry {
  timestamp: string;
  entry_type: string;
  category: string;
  summary: string;
  recorded_by: string;
}

interface PatientMemoryPanelProps {
  patientId: string | null;
  userEmail?: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  baseline: '#8b5cf6',
  medication_response: '#ef4444',
  vitals_change: '#3b82f6',
  clinical_note: '#10b981',
  device_change: '#06b6d4',
  care_plan: '#f59e0b',
  family_update: '#ec4899',
  discharge_planning: '#f97316',
};

const CATEGORY_LABELS: Record<string, string> = {
  baseline: 'Admission Baseline',
  medication_response: 'Medication Response',
  vitals_change: 'Vitals Change',
  clinical_note: 'Clinical Note',
  device_change: 'Device Change',
  care_plan: 'Care Plan',
  family_update: 'Family Update',
  discharge_planning: 'Discharge Planning',
};

const formatTime = (ts: string) => {
  try {
    const d = new Date(ts);
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return ts;
  }
};

const PatientMemoryPanel: React.FC<PatientMemoryPanelProps> = ({ patientId, userEmail }) => {
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [phiDenied, setPhiDenied] = useState(false);
  const pollRef = useRef<number | null>(null);

  const fetchMemory = useCallback(async (pid: string) => {
    try {
      const emailParam = userEmail ? `&actor_email=${encodeURIComponent(userEmail)}` : '';
      const res = await signedFetch(`?patient_memory=${pid}${emailParam}`);
      const data = await res.json();
      if (data.phi_access_denied) {
        setPhiDenied(true);
        setEntries([]);
      } else if (data.entries) {
        setPhiDenied(false);
        setEntries(data.entries);
        setError('');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load memory');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }

    if (!patientId) {
      setEntries([]);
      return;
    }

    setLoading(true);
    fetchMemory(patientId);

    // Poll every 10 seconds for updates
    pollRef.current = window.setInterval(() => fetchMemory(patientId), 10000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [patientId, fetchMemory]);

  const isDark = document.body.classList.contains('awsui-dark');
  const bgColor = isDark ? '#0f1b2a' : '#fafafa';
  const borderColor = isDark ? '#414d5c' : '#d5dbdb';
  const textSecondary = isDark ? '#94a3b8' : '#687078';
  const cardBg = isDark ? '#192534' : '#ffffff';

  if (!patientId) {
    return (
      <div style={{
        padding: 16,
        background: bgColor,
        borderLeft: `1px solid ${borderColor}`,
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <Box variant="small" color="text-body-secondary" textAlign="center">
          Mention a patient ID in the chat to view their memory timeline
        </Box>
      </div>
    );
  }

  return (
    <div style={{
      padding: 16,
      background: bgColor,
      borderLeft: `1px solid ${borderColor}`,
      height: '100%',
      overflowY: 'auto',
    }}>
      <SpaceBetween size="s">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.95em' }}>Patient Memory</div>
            <div style={{ fontSize: '0.8em', color: textSecondary, fontFamily: 'monospace' }}>{patientId}</div>
          </div>
          <Button iconName="refresh" variant="icon" onClick={() => fetchMemory(patientId)} ariaLabel="Refresh memory" />
        </div>

        {loading && entries.length === 0 && (
          <Box textAlign="center" padding="l"><Spinner /> Loading timeline...</Box>
        )}

        {error && (
          <Box variant="small" color="text-status-error">{error}</Box>
        )}

        {phiDenied && (
          <div style={{
            padding: '16px', borderRadius: 8, textAlign: 'center',
            background: 'linear-gradient(135deg, #fef2f210, #fee2e210)',
            border: '1px solid #fca5a540',
          }}>
            <div style={{ fontSize: '0.85em', color: '#ef4444', fontWeight: 500, marginBottom: 4 }}>
              PHI Access Restricted
            </div>
            <Box variant="small" color="text-body-secondary">
              You are not on this patient's care team. Join the care team to view the memory timeline.
            </Box>
          </div>
        )}

        {!phiDenied && entries.length === 0 && !loading && (
          <Box variant="small" color="text-body-secondary">
            No memory entries yet. Admit this patient to initialize memory.
          </Box>
        )}

        {/* Timeline */}
        <div style={{ position: 'relative', paddingLeft: 20 }}>
          {/* Vertical line */}
          {entries.length > 0 && (
            <div style={{
              position: 'absolute',
              left: 7,
              top: 8,
              bottom: 8,
              width: 2,
              background: isDark ? '#334155' : '#d5dbdb',
            }} />
          )}

          {entries.map((entry, i) => {
            const color = CATEGORY_COLORS[entry.category] || '#6b7280';
            const label = CATEGORY_LABELS[entry.category] || entry.category;

            return (
              <div key={i} style={{ position: 'relative', marginBottom: 12 }}>
                {/* Dot on timeline */}
                <div style={{
                  position: 'absolute',
                  left: -16,
                  top: 6,
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: color,
                  border: `2px solid ${bgColor}`,
                }} />

                {/* Entry card */}
                <div style={{
                  background: cardBg,
                  border: `1px solid ${borderColor}`,
                  borderRadius: 8,
                  padding: '10px 12px',
                  borderLeft: `3px solid ${color}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span style={{
                      fontSize: '0.7em',
                      fontWeight: 600,
                      padding: '1px 6px',
                      borderRadius: 3,
                      background: `${color}15`,
                      color,
                    }}>
                      {label}
                    </span>
                    <span style={{ fontSize: '0.68em', color: textSecondary }}>
                      {formatTime(entry.timestamp)}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.82em', lineHeight: 1.4 }}>
                    {entry.summary}
                  </div>
                  {entry.recorded_by && entry.recorded_by !== 'system' && (
                    <div style={{ fontSize: '0.7em', color: textSecondary, marginTop: 4 }}>
                      Recorded by: {entry.recorded_by}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {entries.length > 0 && (
          <SpaceBetween size="xs">
            <Box variant="small" color="text-body-secondary" textAlign="center">
              {entries.length} {entries.length === 1 ? 'entry' : 'entries'} in memory
            </Box>
            <Box textAlign="center">
              <span
                onClick={async () => {
                  if (!patientId || !userEmail) return;
                  try {
                    await signedFetch('', {
                      method: 'POST',
                      body: JSON.stringify({ care_team_action: 'leave', patient_id: patientId, actor_email: userEmail }),
                    });
                    setPhiDenied(true);
                    setEntries([]);
                  } catch { /* ignore */ }
                }}
                role="button"
                tabIndex={0}
                style={{ fontSize: '0.72em', color: textSecondary, cursor: 'pointer', textDecoration: 'underline', textDecorationStyle: 'dotted' }}
              >
                Leave care team
              </span>
            </Box>
          </SpaceBetween>
        )}
      </SpaceBetween>
    </div>
  );
};

export default PatientMemoryPanel;
