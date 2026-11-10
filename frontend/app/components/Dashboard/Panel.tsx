import type { ReactNode } from 'react';

/**
 * STEP 3A: Panel with optional source badge for transparency.
 *
 * source="live"       → 🟢 LIVE   (real external data — RSS, WorldBank)
 * source="simulated"  → 🟠 SIM    (RL-simulated strategic scenario)
 * source="hybrid"     → 🔵 HYB    (real data + simulated extrapolation)
 * source="static"     → ⚪ STC    (static reference value)
 *
 * If `source` is not provided, no badge is rendered.
 */
export type PanelSource = 'live' | 'simulated' | 'hybrid' | 'static';

const SOURCE_LABEL: Record<PanelSource, string> = {
  live: 'LIVE',
  simulated: 'SIM',
  hybrid: 'HYB',
  static: 'STC',
};

const SOURCE_TOOLTIP: Record<PanelSource, string> = {
  live: 'Live data from real external source (RSS / World Bank / etc.)',
  simulated: 'RL-simulated strategic scenario — not real-world data',
  hybrid: 'Real data combined with simulated extrapolation',
  static: 'Static reference value (seed data, not updated live)',
};

export function SourceBadge({ source }: { source: PanelSource }) {
  return (
    <span
      className={`panel-source-badge ${source}`}
      title={SOURCE_TOOLTIP[source]}
      aria-label={SOURCE_TOOLTIP[source]}
    >
      {SOURCE_LABEL[source]}
    </span>
  );
}

export function Panel({
  title,
  eyebrow,
  action,
  children,
  className = '',
  source,
}: {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  source?: PanelSource;
}) {
  return (
    <section className={`panel ${className}`}>
      {(eyebrow || title || action || source) && (
        <header className="panel-header">
          <div>
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            {title && (
              <h2 className={`panel-title${source ? ' has-badge' : ''}`}>
                {title}
                {source && <SourceBadge source={source} />}
              </h2>
            )}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}