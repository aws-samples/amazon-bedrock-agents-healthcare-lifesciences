/**
 * MedTech Charts — Visual chart components for Field Service and Account Intelligence agents.
 *
 * Parses agent text responses for structured data patterns and renders
 * Recharts visualizations below the chat bubble text.
 */

import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie, Legend,
} from 'recharts';

// ==========================================
// Chart Data Types
// ==========================================

interface FleetHealthItem {
  site_name: string;
  critical: number;
  moderate: number;
  healthy: number;
}

interface AccountHealthItem {
  site_name: string;
  health_score: number;
  risk_level: string;
}

interface FirmwareItem {
  firmware: string;
  devices: number;
  avg_errors: number;
}

export interface MedTechChartData {
  type: 'fleet_health' | 'account_health' | 'firmware_comparison';
  data: FleetHealthItem[] | AccountHealthItem[] | FirmwareItem[];
}

// ==========================================
// Color Constants
// ==========================================

const SCORE_COLOR = (score: number) =>
  score >= 75 ? '#10b981' : score >= 50 ? '#f59e0b' : '#ef4444';

// ==========================================
// Dark Mode Detection
// ==========================================

const useDarkMode = () => document.body.classList.contains('awsui-dark');

// ==========================================
// Fleet Health Chart (stacked bar by site)
// ==========================================

const FleetHealthChart: React.FC<{ data: FleetHealthItem[] }> = ({ data }) => {
  const isDark = useDarkMode();
  const gridColor = isDark ? '#334155' : '#e2e8f0';
  const tickColor = isDark ? '#94a3b8' : '#64748b';

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: '0.85em', fontWeight: 600, marginBottom: 8, color: tickColor }}>
        Fleet Health by Hospital Site
      </div>
      <ResponsiveContainer width="100%" height={Math.max(180, data.length * 60)}>
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis type="number" tick={{ fontSize: 11, fill: tickColor }} />
          <YAxis dataKey="site_name" type="category" tick={{ fontSize: 11, fill: tickColor }} width={180} />
          <Tooltip
            contentStyle={{
              background: isDark ? '#1e293b' : '#fff',
              border: `1px solid ${isDark ? '#475569' : '#d5dbdb'}`,
              borderRadius: 8, fontSize: '0.85em',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '0.8em' }} />
          <Bar dataKey="critical" stackId="risk" fill="#ef4444" name="Critical" />
          <Bar dataKey="moderate" stackId="risk" fill="#f59e0b" name="Moderate" />
          <Bar dataKey="healthy" stackId="risk" fill="#10b981" name="Healthy" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// ==========================================
// Account Health Scorecards
// ==========================================

const AccountHealthChart: React.FC<{ data: AccountHealthItem[] }> = ({ data }) => {
  const isDark = useDarkMode();
  const cardBg = isDark ? '#0f1b2a' : '#ffffff';
  const cardBorder = isDark ? '#414d5c' : '#d5dbdb';
  const textSecondary = isDark ? '#94a3b8' : '#687078';

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: '0.85em', fontWeight: 600, marginBottom: 8, color: textSecondary }}>
        Account Health Scores
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
        {data.map((account, i) => {
          const color = SCORE_COLOR(account.health_score);
          return (
            <div key={i} style={{
              background: cardBg,
              border: `1px solid ${cardBorder}`,
              borderRadius: 10,
              padding: 16,
              borderLeft: `4px solid ${color}`,
            }}>
              <div style={{ fontSize: '0.82em', color: textSecondary, marginBottom: 4 }}>
                {account.site_name}
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <span style={{ fontSize: '2em', fontWeight: 700, color, lineHeight: 1 }}>
                  {account.health_score}
                </span>
                <span style={{ fontSize: '0.85em', color: textSecondary }}>/100</span>
              </div>
              <div style={{
                marginTop: 6,
                fontSize: '0.75em',
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: 4,
                display: 'inline-block',
                background: `${color}15`,
                color,
              }}>
                {account.risk_level}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ==========================================
// Firmware Comparison Chart
// ==========================================

const FirmwareComparisonChart: React.FC<{ data: FirmwareItem[] }> = ({ data }) => {
  const isDark = useDarkMode();
  const gridColor = isDark ? '#334155' : '#e2e8f0';
  const tickColor = isDark ? '#94a3b8' : '#64748b';

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: '0.85em', fontWeight: 600, marginBottom: 8, color: tickColor }}>
        Firmware Version Performance
      </div>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 250 }}>
          <div style={{ fontSize: '0.78em', color: tickColor, marginBottom: 4 }}>Avg Error Count by Firmware</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
              <XAxis dataKey="firmware" tick={{ fontSize: 10, fill: tickColor }} />
              <YAxis tick={{ fontSize: 10, fill: tickColor }} />
              <Tooltip
                contentStyle={{
                  background: isDark ? '#1e293b' : '#fff',
                  border: `1px solid ${isDark ? '#475569' : '#d5dbdb'}`,
                  borderRadius: 8, fontSize: '0.85em',
                }}
              />
              <Bar dataKey="avg_errors" name="Avg Errors" radius={[4, 4, 0, 0]}>
                {data.map((entry, i) => (
                  <Cell key={i} fill={entry.avg_errors > 50 ? '#ef4444' : entry.avg_errors > 20 ? '#f59e0b' : '#10b981'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <div style={{ fontSize: '0.78em', color: tickColor, marginBottom: 4 }}>Device Distribution</div>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={data}
                dataKey="devices"
                nameKey="firmware"
                cx="50%"
                cy="50%"
                outerRadius={65}
                label={({ firmware, devices }) => `${firmware} (${devices})`}
                labelLine={{ stroke: tickColor }}
              >
                {data.map((_entry, i) => (
                  <Cell key={i} fill={['#3b82f6', '#06b6d4', '#8b5cf6', '#10b981', '#f59e0b'][i % 5]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

// ==========================================
// Chart Data Extraction from Agent Response
// ==========================================

export function extractMedTechChartData(text: string, agentId: string): MedTechChartData | undefined {
  if (!text) return undefined;

  // Only process for medtech agents and orchestrator
  const medtechAgents = ['field-service', 'account-intelligence', 'orchestrator'];
  if (!medtechAgents.includes(agentId)) return undefined;

  // --- Account Health Scorecards ---
  if (text.includes('Health Score') && text.includes('/100')) {
    const scorePattern = /([A-Za-z\s]+(?:Hospital|Center|Clinic))\s*[\n|]*\s*.*?Health Score[:\s]*(\d+)\s*\/\s*100\s*.*?(HEALTHY|AT RISK|MODERATE|CRITICAL)/gi;
    const accounts: AccountHealthItem[] = [];
    let match;
    while ((match = scorePattern.exec(text)) !== null) {
      accounts.push({
        site_name: match[1].trim(),
        health_score: parseInt(match[2]),
        risk_level: match[3].toUpperCase(),
      });
    }
    // Fallback: try table format
    if (accounts.length === 0) {
      const tablePattern = /\|\s*([^|]*(?:Hospital|Center|Clinic)[^|]*)\s*\|[^|]*\|\s*(\d+)\s*(?:\/100)?\s*.*?(HEALTHY|AT RISK|MODERATE|CRITICAL)/gi;
      while ((match = tablePattern.exec(text)) !== null) {
        accounts.push({
          site_name: match[1].trim(),
          health_score: parseInt(match[2]),
          risk_level: match[3].toUpperCase(),
        });
      }
    }
    if (accounts.length > 0) return { type: 'account_health', data: accounts };
  }

  // --- Fleet Health (risk distribution by site) ---
  if ((text.toLowerCase().includes('installed base') || text.toLowerCase().includes('fleet')) &&
      (text.includes('CRITICAL') || text.includes('critical'))) {
    const siteRisks: Record<string, FleetHealthItem> = {};
    // Parse from markdown tables: look for site name + risk level patterns
    const riskPattern = /\|\s*([A-Z][\w-]+)\s*\|[^|]*\|[^|]*\|[^|]*\|\s*(active|maintenance|offline)\s*\|\s*(critical|moderate|healthy)\s*\|/gi;
    let match;
    while ((match = riskPattern.exec(text)) !== null) {
      // Try to find which site section we're in
      const beforeMatch = text.substring(0, match.index);
      const siteMatch = beforeMatch.match(/###\s*([^\n]*(?:Hospital|Center|Clinic)[^\n]*)/gi);
      const siteName = siteMatch ? siteMatch[siteMatch.length - 1].replace(/^###\s*/, '').trim() : 'Unknown';
      if (!siteRisks[siteName]) {
        siteRisks[siteName] = { site_name: siteName, critical: 0, moderate: 0, healthy: 0 };
      }
      const risk = match[3].toLowerCase() as 'critical' | 'moderate' | 'healthy';
      siteRisks[siteName][risk]++;
    }
    // Fallback: count risk keywords per site section
    if (Object.keys(siteRisks).length === 0) {
      const sections = text.split(/###\s+/);
      for (const section of sections) {
        const nameMatch = section.match(/([^\n]*(?:Hospital|Center|Clinic)[^\n]*)/i);
        if (nameMatch) {
          const name = nameMatch[1].replace(/[*_#]/g, '').trim();
          const critCount = (section.match(/\bcritical\b/gi) || []).length;
          const modCount = (section.match(/\bmoderate\b/gi) || []).length;
          const healthyCount = (section.match(/\bhealthy\b/gi) || []).length;
          if (critCount + modCount + healthyCount > 0) {
            siteRisks[name] = { site_name: name, critical: critCount, moderate: modCount, healthy: healthyCount };
          }
        }
      }
    }
    const fleetData = Object.values(siteRisks);
    if (fleetData.length > 0) return { type: 'fleet_health', data: fleetData };
  }

  // --- Firmware Comparison ---
  if (text.toLowerCase().includes('firmware') &&
      (text.includes('9.19') || text.includes('9.28') || text.includes('9.33') ||
       text.includes('3.0') || text.includes('3.1') || text.includes('2.8'))) {
    const fwPattern = /\|\s*([\d.]+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*(?:errors?)?\s*\|/gi;
    const firmwares: FirmwareItem[] = [];
    let match;
    while ((match = fwPattern.exec(text)) !== null) {
      firmwares.push({
        firmware: match[1],
        devices: parseInt(match[2]),
        avg_errors: parseFloat(match[3]),
      });
    }
    if (firmwares.length > 0) return { type: 'firmware_comparison', data: firmwares };
  }

  return undefined;
}

// ==========================================
// Main Chart Renderer
// ==========================================

const MedTechChart: React.FC<{ chartData: MedTechChartData }> = ({ chartData }) => {
  switch (chartData.type) {
    case 'fleet_health':
      return <FleetHealthChart data={chartData.data as FleetHealthItem[]} />;
    case 'account_health':
      return <AccountHealthChart data={chartData.data as AccountHealthItem[]} />;
    case 'firmware_comparison':
      return <FirmwareComparisonChart data={chartData.data as FirmwareItem[]} />;
    default:
      return null;
  }
};

export default MedTechChart;
