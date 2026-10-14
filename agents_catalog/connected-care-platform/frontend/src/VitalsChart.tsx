import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';

interface VitalConfig {
  key: string;
  label: string;
  unit: string;
  color: string;
  gradient: [string, string];
  normalLow?: number;
  normalHigh?: number;
}

const VITAL_CONFIGS: VitalConfig[] = [
  { key: 'heart_rate', label: 'Heart Rate', unit: 'bpm', color: '#ef4444', gradient: ['#fca5a5', '#ef4444'], normalLow: 60, normalHigh: 100 },
  { key: 'blood_pressure_systolic', label: 'BP Systolic', unit: 'mmHg', color: '#3b82f6', gradient: ['#93c5fd', '#3b82f6'], normalLow: 90, normalHigh: 140 },
  { key: 'blood_pressure_diastolic', label: 'BP Diastolic', unit: 'mmHg', color: '#6366f1', gradient: ['#a5b4fc', '#6366f1'], normalLow: 60, normalHigh: 90 },
  { key: 'temperature', label: 'Temperature', unit: '°F', color: '#f59e0b', gradient: ['#fcd34d', '#f59e0b'], normalLow: 97, normalHigh: 99.5 },
  { key: 'spo2', label: 'SpO2', unit: '%', color: '#10b981', gradient: ['#6ee7b7', '#10b981'], normalLow: 95, normalHigh: 100 },
  { key: 'respiratory_rate', label: 'Resp Rate', unit: '/min', color: '#8b5cf6', gradient: ['#c4b5fd', '#8b5cf6'], normalLow: 12, normalHigh: 20 },
  { key: 'blood_glucose', label: 'Blood Glucose', unit: 'mg/dL', color: '#ec4899', gradient: ['#f9a8d4', '#ec4899'], normalLow: 70, normalHigh: 140 },
];

interface VitalsChartProps {
  data: Record<string, number | string>[];
}

const CustomTooltip = ({ active, payload, label, isDark }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: isDark ? '#1e293b' : '#ffffff',
      border: `1px solid ${isDark ? '#475569' : '#d5dbdb'}`,
      borderRadius: 8,
      padding: '0.5rem 0.75rem', fontSize: '0.8rem',
      boxShadow: isDark ? 'none' : '0 2px 8px rgba(0,0,0,0.1)',
    }}>
      <p style={{ color: isDark ? '#94a3b8' : '#64748b', margin: 0 }}>{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color, margin: '2px 0', fontWeight: 600 }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}
        </p>
      ))}
    </div>
  );
};

const VitalsChart: React.FC<VitalsChartProps> = ({ data }) => {
  if (!data || data.length === 0) return null;

  // Detect dark mode from Cloudscape's body class
  const isDark = document.body.classList.contains('awsui-dark');
  const gridColor = isDark ? '#334155' : '#e2e8f0';
  const tickColor = isDark ? '#94a3b8' : '#64748b';
  const cardBg = isDark ? '#0f1b2a' : '#ffffff';
  const cardBorder = isDark ? '#414d5c' : '#d5dbdb';

  // Determine which vitals are present in the data
  const presentVitals = VITAL_CONFIGS.filter(v =>
    data.some(d => d[v.key] !== undefined && d[v.key] !== null)
  );

  // Format timestamps for display
  const chartData = data.map(d => ({
    ...d,
    time: typeof d.timestamp === 'string'
      ? new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : d.timestamp,
  })) as Record<string, number | string>[];

  return (
    <div className="vitals-charts" data-testid="vitals-charts">
      <div className="charts-grid">
        {presentVitals.map(vital => {
          const values = chartData.map(d => Number(d[vital.key])).filter(v => !isNaN(v));
          const min = Math.min(...values);
          const max = Math.max(...values);
          const padding = (max - min) * 0.15 || 5;
          const latest = values[values.length - 1];
          const isAbnormal = (vital.normalLow && latest < vital.normalLow) ||
                             (vital.normalHigh && latest > vital.normalHigh);

          return (
            <div key={vital.key} className={`chart-card ${isAbnormal ? 'abnormal' : ''}`}
                 style={{ background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 10, padding: '12px' }}>
              <div className="chart-header">
                <span className="chart-label" style={{ color: tickColor }}>{vital.label}</span>
                <span className={`chart-value ${isAbnormal ? 'text-danger' : ''}`}
                      style={{ color: isAbnormal ? '#ef4444' : vital.color }}>
                  {latest?.toFixed(vital.key === 'temperature' ? 1 : 0)} {vital.unit}
                </span>
              </div>
              <ResponsiveContainer width="100%" height={120}>
                <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id={`grad-${vital.key}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={vital.gradient[1]} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={vital.gradient[0]} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                  <XAxis dataKey="time" tick={{ fontSize: 10, fill: tickColor }} />
                  <YAxis domain={[min - padding, max + padding]} tick={{ fontSize: 10, fill: tickColor }} />
                  <Tooltip content={<CustomTooltip isDark={isDark} />} />
                  {vital.normalLow && (
                    <ReferenceLine y={vital.normalLow} stroke="#22c55e" strokeDasharray="4 4" strokeOpacity={0.5} />
                  )}
                  {vital.normalHigh && (
                    <ReferenceLine y={vital.normalHigh} stroke="#22c55e" strokeDasharray="4 4" strokeOpacity={0.5} />
                  )}
                  <Area
                    type="monotone" dataKey={vital.key} name={vital.label}
                    stroke={vital.color} strokeWidth={2}
                    fill={`url(#grad-${vital.key})`}
                    dot={{ r: 2, fill: vital.color }}
                    activeDot={{ r: 4, fill: vital.color, stroke: '#fff', strokeWidth: 2 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default VitalsChart;
