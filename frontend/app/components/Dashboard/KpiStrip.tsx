"use client";
import { Activity, Cpu, DollarSign, Gauge, Globe2, Package, Info } from 'lucide-react';
import type { SimulationHistoryPoint } from '../../types';
import type { LucideIcon } from 'lucide-react';

/**
 * STEP 3A: All KPIs on this strip are derived from the RL simulation engine,
 * NOT from real-world sources. Each tile shows a SIMULATED badge and a
 * tooltip explaining the source.
 */

function Sparkline({ values = [], tone = 'blue' }: { values?: number[]; tone?: string }) {
  const nums = values.length ? values.slice(-18) : [50, 51, 49, 52];
  const min = Math.min(...nums), max = Math.max(...nums), range = Math.max(1, max - min);
  const pts = nums.map((v, i) => `${(i / Math.max(1, nums.length - 1)) * 100},${21 - ((v - min) / range) * 17}`).join(' ');
  return (
    <svg className={`spark ${tone}`} viewBox="0 0 100 24" preserveAspectRatio="none">
      <polyline points={pts} fill="none" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

// STEP 3A: small source badge for KPI tiles
function SourceBadge({ source }: { source: 'simulated' | 'live' | 'hybrid' | 'static' }) {
  const labels: Record<string, string> = {
    simulated: 'SIM',
    live: 'LIVE',
    hybrid: 'HYB',
    static: 'STC',
  };
  const tooltips: Record<string, string> = {
    simulated: 'RL-simulated strategic scenario — not real-world data',
    live: 'Live data from real external source',
    hybrid: 'Real data + simulated extrapolation',
    static: 'Static reference value',
  };
  return (
    <span
      className={`kpi-source-badge ${source}`}
      title={tooltips[source]}
      aria-label={tooltips[source]}
    >
      {labels[source]}
    </span>
  );
}

export function KpiStrip({
  stability,
  tension,
  tech,
  economic,
  history = [],
  conflicts = 5,
}: {
  stability: number;
  tension: number;
  tech: number;
  economic: number;
  history?: SimulationHistoryPoint[];
  conflicts?: number;
}) {
  const values = (key: keyof SimulationHistoryPoint['state']) =>
    history.map((p) => Number(p.state[key])).filter(Number.isFinite);

  // Each card: [label, value, unit, delta, tone, Icon, progress, series, source]
  const cards: Array<
    [string, string, string, string, string, LucideIcon, number, number[], 'simulated' | 'live' | 'hybrid']
  > = [
    [
      'GLOBAL STABILITY',
      `${Math.round(stability)}`,
      '/100',
      stability > 70 ? 'Stable' : 'Watch',
      'red',
      Globe2,
      stability,
      [...history.map((p) => Number(p.state.economic_stability))],
      'simulated',
    ],
    [
      'POWER BALANCE',
      'MULTI',
      'POLAR',
      'Dynamic',
      'amber',
      Activity,
      64,
      [...history.map((p) => 100 - Number(p.state.strategic_tension))],
      'simulated',
    ],
    [
      'ECONOMIC HEALTH',
      `$${(100 + economic * 0.063).toFixed(1)}`,
      'T',
      economic >= 74 ? '+2.3%' : '-0.4%',
      'green',
      DollarSign,
      economic,
      values('economic_stability'),
      'simulated',
    ],
    [
      'TECHNOLOGY INDEX',
      `${(tech / 10).toFixed(1)}`,
      '/10',
      tech >= 70 ? '+0.8%' : '-0.2%',
      'blue',
      Cpu,
      tech,
      values('technology_independence'),
      'simulated',
    ],
    [
      'RESOURCE PRESSURE',
      `${Math.round(tension)}`,
      '/100',
      tension > 70 ? 'High' : 'Moderate',
      'red',
      Package,
      tension,
      [...history.map((p) => Number(p.state.strategic_tension))],
      'simulated',
    ],
    [
      'ACTIVE CONFLICTS',
      String(conflicts).padStart(2, '0'),
      '',
      conflicts > 5 ? 'Elevated' : 'Active',
      'red',
      Gauge,
      Math.min(100, conflicts * 16),
      [...history.map((p) => Number(p.state.strategic_tension))],
      'simulated',
    ],
  ];

  return (
    <div className="kpi-grid">
      {cards.map(
        ([label, value, unit, delta, tone, Icon, progress, series, source]) => (
          <div className={`kpi-card ${tone}`} key={label}>
            <div className="kpi-top">
              <span>{label}</span>
              <div className="kpi-top-right">
                <SourceBadge source={source} />
                <div className="kpi-icon">
                  <Icon size={17} />
                </div>
              </div>
            </div>
            <div className="kpi-value">
              {value}
              <em>{unit}</em>
            </div>
            <div className="kpi-bottom">
              <b>{delta}</b>
              <span>live</span>
            </div>
            <Sparkline tone={tone} values={series} />
            <div className="kpi-bar">
              <span
                style={{
                  width: `${Math.min(100, Math.max(0, Number(progress)))}%`,
                }}
              />
            </div>
          </div>
        )
      )}
    </div>
  );
}

// STEP 3A: helper export for anyone who wants to add tooltips in other panels
export { SourceBadge };