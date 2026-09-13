"use client";
import { ArrowDown, ArrowUp, Minus, TrendingUp } from 'lucide-react';
import { Panel } from './Panel';
import type { ForecastData, ForecastMetric } from '../../types';

const LABELS: Record<string, string> = {
  economic_stability: 'Economic Stability',
  strategic_tension: 'Strategic Tension',
  technology_independence: 'Technology Independence',
  public_sentiment: 'Public Sentiment',
};

function TrendIcon({ trend }: { trend: ForecastMetric['trend'] }) {
  if (trend === 'rising') return <ArrowUp size={12} />;
  if (trend === 'falling') return <ArrowDown size={12} />;
  return <Minus size={12} />;
}

// Renders the metric's recent history plus the projected future band as a
// single SVG sparkline: solid line = observed, dashed line = predicted,
// shaded ribbon = the 80% confidence band the backend already computes.
// This is a linear-trend projection, not RL -- it answers "where is this
// number headed", not "what should the agent do".
function MetricSparkline({ metric }: { metric: ForecastMetric }) {
  const hist = metric.history ?? [];
  const pred = metric.predicted ?? [];
  const lower = metric.lower ?? [];
  const upper = metric.upper ?? [];
  const total = hist.length + pred.length;
  if (total < 2) return <div className="forecast-empty">Not enough data yet</div>;

  const allVals = [...hist, ...pred, ...lower, ...upper];
  const min = Math.min(...allVals, 0);
  const max = Math.max(...allVals, 100);
  const range = Math.max(1, max - min);
  const x = (i: number) => (i / Math.max(1, total - 1)) * 100;
  const y = (v: number) => 100 - ((v - min) / range) * 100;

  const histPts = hist.map((v, i) => `${x(i)},${y(v)}`).join(' ');
  const predPts = pred.map((v, i) => `${x(hist.length - 1 + i + 1)},${y(v)}`).join(' ');
  // Join the last observed point to the first predicted point so the
  // dashed projection visually continues from the solid history line.
  const bridge = hist.length ? `${x(hist.length - 1)},${y(hist[hist.length - 1])} ` : '';
  const bandTop = pred.map((_, i) => `${x(hist.length - 1 + i + 1)},${y(upper[i])}`).join(' ');
  const bandBottom = pred.map((_, i) => `${x(hist.length - 1 + i + 1)},${y(lower[i])}`).reverse().join(' ');
  const bandStart = hist.length ? `${x(hist.length - 1)},${y(hist[hist.length - 1])} ` : '';

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="forecast-spark">
      {pred.length > 0 && (
        <polygon points={`${bandStart}${bandTop} ${bandBottom}`} className="forecast-band" />
      )}
      <polyline points={histPts} className="forecast-history" />
      {pred.length > 0 && <polyline points={`${bridge}${predPts}`} className="forecast-projected" />}
    </svg>
  );
}

function ForecastRow({ metricKey, metric }: { metricKey: string; metric: ForecastMetric }) {
  const label = LABELS[metricKey] ?? metricKey;
  const nextVal = metric.predicted?.[metric.predicted.length - 1];
  return (
    <div className="forecast-row">
      <div className="forecast-row-head">
        <span>{label}</span>
        <b className={`forecast-trend ${metric.trend}`}><TrendIcon trend={metric.trend} /> {metric.trend}</b>
      </div>
      <MetricSparkline metric={metric} />
      <div className="forecast-row-foot">
        <span>Slope: {metric.slope_per_round >= 0 ? '+' : ''}{metric.slope_per_round}/round</span>
        {nextVal != null && <span>Projected: <b>{nextVal}</b></span>}
      </div>
    </div>
  );
}

export function ForecastPanel({ forecast }: { forecast: ForecastData | null }) {
  const entries = forecast?.available ? Object.entries(forecast.metrics) : [];
  return (
    <Panel eyebrow="LINEAR TREND PROJECTION" title="Forecast" action={<span className="feed-live"><TrendingUp size={13}/> {forecast?.horizon ?? 0}-round outlook</span>}>
      {entries.length === 0 ? (
        <div className="forecast-empty">Collecting rounds before a projection is reliable…</div>
      ) : (
        <div className="forecast-grid">
          {entries.map(([key, metric]) => metric && <ForecastRow key={key} metricKey={key} metric={metric} />)}
        </div>
      )}
      <div className="feed-footer"><span>Least-squares trend over recent rounds, not a decision model — see Agent Intelligence for the actual RL policy.</span></div>
    </Panel>
  );
}
