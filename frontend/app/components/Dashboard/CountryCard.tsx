// frontend/app/components/Dashboard/CountryCard.tsx
'use client';

import { CountryDashboardData, MetricSource } from '@/app/types/country';
import { useNews } from '@/app/hooks/useNews';
import { motion } from 'framer-motion';
import {
  TrendingUp, TrendingDown, AlertTriangle,
  CheckCircle, XCircle, Clock, Users,
  BarChart3, Shield, DollarSign, Building2,
  Newspaper, ExternalLink, RefreshCw, Activity,
} from 'lucide-react';

interface CountryCardProps {
  data: CountryDashboardData;
  onClose: () => void;
  source?: string | null;
  round?: number | null;
  /** STEP 3: field-path → source type */
  sources?: Record<string, MetricSource>;
}

// ============================================================
// STEP 3A: DataBadge component
// ============================================================
const DataBadge: React.FC<{
  source?: MetricSource;
  title?: string;
}> = ({ source, title }) => {
  if (!source) return null;

  const labels: Record<MetricSource, string> = {
    live: 'LIVE',
    simulated: 'SIM',
    hybrid: 'HYBRID',
    static: 'STATIC',
  };

  const tooltips: Record<MetricSource, string> = {
    live: 'Live data from real source (WorldBank / RSS feeds)',
    simulated: 'Simulated by RL agents — not real-world data',
    hybrid: 'Real data with simulated extrapolation',
    static: 'Static reference value (seed data)',
  };

  return (
    <span
      className={`data-badge ${source}`}
      title={title || tooltips[source]}
    >
      <span className="dot" />
      {labels[source]}
    </span>
  );
};

// ============================================================
// Section header with optional badge
// ============================================================
const SectionHead: React.FC<{
  title: string;
  icon: React.ReactNode;
  source?: MetricSource;
  action?: React.ReactNode;
}> = ({ title, icon, source, action }) => (
  <div className="flex items-center justify-between gap-2 text-gray-400 text-sm font-medium mb-3">
    <div className="flex items-center gap-2">
      {icon}
      <span>{title}</span>
      <DataBadge source={source} />
    </div>
    {action}
  </div>
);

// ============================================================
// Main component
// ============================================================
export const CountryCard: React.FC<CountryCardProps> = ({
  data,
  onClose,
  source,
  round,
  sources = {},
}) => {
  // ---- Live news hook ----
  const { news, loading: newsLoading, error: newsError, refresh: refreshNews } =
    useNews(data.country.id);

  const getStabilityColor = (score: number) => {
    if (score >= 70) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'stable':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'unstable':
        return <XCircle className="w-5 h-5 text-red-400" />;
      default:
        return <AlertTriangle className="w-5 h-5 text-yellow-400" />;
    }
  };

  const liveSource = source === 'runtime';
  const hasLiveNews = !!news && news.article_count > 0;

  // STEP 3 helper — resolve source for a given field-path
  const srcOf = (path: string): MetricSource | undefined => sources[path];

  // STEP 3A: government status is RL-simulated (unless backend marks otherwise)
  const govStatusSource: MetricSource =
    srcOf('government.status') || 'simulated';

  return (
    <motion.div
      initial={{ opacity: 0, x: 300 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 300 }}
      className="fixed right-0 top-0 h-full w-[420px] bg-gray-900/95 backdrop-blur-xl
                 border-l border-gray-700/50 shadow-2xl z-50 overflow-y-auto"
    >
      {/* Header */}
      <div className="sticky top-0 bg-gray-900/95 backdrop-blur-xl border-b border-gray-700/50 p-6 z-10">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              {data.country.name}
              <span className="text-sm font-normal text-gray-400">
                ({data.country.code.toUpperCase()})
              </span>
            </h2>
            {/* STEP 3A: government status now carries SIM badge */}
            <div className="flex items-center gap-2 mt-1">
              {getStatusIcon(data.government.status)}
              <span
                className={`text-sm font-medium ${getStabilityColor(
                  data.government.stability_score,
                )}`}
              >
                {data.government.status.charAt(0).toUpperCase() +
                  data.government.status.slice(1)}
              </span>
              <DataBadge source={govStatusSource} />
              <span className="text-xs text-gray-500">
                Last updated: {new Date().toLocaleTimeString()}
              </span>
            </div>

            {/* LIVE indicator */}
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span
                className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border
                  ${
                    liveSource
                      ? 'bg-green-500/15 text-green-400 border-green-500/30'
                      : source === 'database'
                      ? 'bg-blue-500/15 text-blue-400 border-blue-500/30'
                      : 'bg-gray-500/15 text-gray-400 border-gray-500/30'
                  }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    liveSource ? 'bg-green-400 animate-pulse' : 'bg-gray-400'
                  }`}
                />
                {liveSource
                  ? 'LIVE'
                  : (source || 'STATIC').toUpperCase()}
              </span>
              {round != null && (
                <span className="text-[10px] text-gray-500">
                  Round {round}
                </span>
              )}
              {hasLiveNews && (
                <span
                  className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full
                             bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
                  title={`${news.article_count} articles from ${news.source_breakdown.rss} RSS feeds`}
                >
                  <Newspaper className="w-2.5 h-2.5" />
                  {news.article_count} NEWS
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* ============================================ */}
        {/* LIVE NEWS */}
        {/* ============================================ */}
        <Section
          title="Live Intelligence"
          icon={<Newspaper className="w-4 h-4" />}
          source="live"
          action={
            <button
              onClick={refreshNews}
              disabled={newsLoading}
              className="text-gray-400 hover:text-white transition-colors disabled:opacity-50"
              title="Refresh news"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${newsLoading ? 'animate-spin' : ''}`}
              />
            </button>
          }
        >
          {newsLoading && !news && (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="h-12 bg-gray-800/50 rounded-lg animate-pulse"
                />
              ))}
            </div>
          )}

          {newsError && !news && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
              {newsError}
            </div>
          )}

          {news && (
            <>
              <div className="flex items-center justify-between gap-3 mb-3">
                <SentimentBadge score={news.sentiment_score} />
                <div className="flex items-center gap-2 text-[10px] text-gray-400">
                  <span className="flex items-center gap-1">
                    <Activity className="w-3 h-3 text-cyan-400" />
                    RSS {news.source_breakdown.rss}
                  </span>
                  {news.source_breakdown.gdelt > 0 && (
                    <span className="flex items-center gap-1">
                      <Activity className="w-3 h-3 text-purple-400" />
                      GDELT {news.source_breakdown.gdelt}
                    </span>
                  )}
                </div>
              </div>

              {news.article_count > 0 && (
                <ToneBar
                  positive={news.tone_distribution.positive}
                  neutral={news.tone_distribution.neutral}
                  negative={news.tone_distribution.negative}
                />
              )}

              {news.top_headlines.length > 0 ? (
                <div className="mt-3 space-y-2">
                  {news.top_headlines.slice(0, 5).map((h, idx) => (
                    <HeadlineRow
                      key={idx}
                      title={h.title}
                      url={h.url}
                      source={h.source}
                      tone={h.tone}
                      date={h.seendate}
                    />
                  ))}
                </div>
              ) : (
                <div className="mt-3 p-3 bg-gray-800/30 rounded-lg text-sm text-gray-400 text-center">
                  No live headlines available
                </div>
              )}

              {news.economic_indicators &&
                Object.keys(news.economic_indicators).length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-700/50">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[10px] text-gray-500 uppercase tracking-wide">
                        Live Economic Indicators
                      </span>
                      <DataBadge source="live" />
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {news.economic_indicators.gdp_growth !== undefined && (
                        <MiniStat
                          label="GDP Growth"
                          value={`${news.economic_indicators.gdp_growth.toFixed(
                            2,
                          )}%`}
                          positive={news.economic_indicators.gdp_growth >= 0}
                        />
                      )}
                      {news.economic_indicators.inflation !== undefined && (
                        <MiniStat
                          label="Inflation"
                          value={`${news.economic_indicators.inflation.toFixed(
                            2,
                          )}%`}
                          positive={news.economic_indicators.inflation < 5}
                        />
                      )}
                      {news.economic_indicators.unemployment !== undefined && (
                        <MiniStat
                          label="Unemployment"
                          value={`${news.economic_indicators.unemployment.toFixed(
                            2,
                          )}%`}
                          positive={
                            news.economic_indicators.unemployment < 5
                          }
                        />
                      )}
                      {news.economic_indicators.population !== undefined && (
                        <MiniStat
                          label="Population"
                          value={`${(
                            news.economic_indicators.population / 1_000_000
                          ).toFixed(1)}M`}
                          positive={true}
                        />
                      )}
                    </div>
                  </div>
                )}

              <div className="mt-3 text-[10px] text-gray-500 text-right">
                Updated: {new Date(news.fetched_at).toLocaleTimeString()}
              </div>
            </>
          )}
        </Section>

        {/* ============================================ */}
        {/* Economy */}
        {/* ============================================ */}
        <Section
          title="Economy"
          icon={<DollarSign className="w-4 h-4" />}
          source={srcOf('economy.gdp')}
        >
          <div className="grid grid-cols-2 gap-3">
            <MetricItem
              label="GDP"
              value={`$${data.economy.gdp}B`}
              trend={data.economy.gdp_growth >= 0 ? 1 : -1}
              source={srcOf('economy.gdp')}
            />
            <MetricItem
              label="Growth"
              value={`${data.economy.gdp_growth}%`}
              trend={data.economy.gdp_growth > 5 ? 1 : -1}
              source={srcOf('economy.gdp_growth')}
            />
            <MetricItem
              label="Inflation"
              value={`${data.economy.inflation}%`}
              trend={data.economy.inflation < 8 ? 1 : -1}
              source={srcOf('economy.inflation')}
            />
            <MetricItem
              label="Unemployment"
              value={`${data.economy.unemployment}%`}
              trend={data.economy.unemployment < 5 ? 1 : -1}
              source={srcOf('economy.unemployment')}
            />
          </div>
          <div className="mt-3 p-3 bg-gray-800/50 rounded-lg">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">Foreign Reserves</span>
              <span className="text-white font-medium">
                ${data.economy.foreign_reserves}B
              </span>
            </div>
            <div className="flex items-center justify-between text-sm mt-1">
              <span className="text-gray-400">Debt to GDP</span>
              <span className="text-white font-medium">
                {data.economy.debt_to_gdp}%
              </span>
            </div>
          </div>
        </Section>

        {/* ============================================ */}
        {/* Government (SIMULATED) */}
        {/* ============================================ */}
        <Section
          title="Government"
          icon={<Building2 className="w-4 h-4" />}
          source={srcOf('government.stability_score')}
        >
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Party</span>
              <span className="text-white font-medium">
                {data.government.party_name}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Leader</span>
              <span className="text-white font-medium">
                {data.government.leader_name}
              </span>
            </div>
            <div className="mt-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400 flex items-center gap-2">
                  Stability Score
                  <DataBadge source={srcOf('government.stability_score')} />
                </span>
                <span
                  className={`font-medium ${getStabilityColor(
                    data.government.stability_score,
                  )}`}
                >
                  {data.government.stability_score}%
                </span>
              </div>
              <div className="w-full h-2 bg-gray-700 rounded-full mt-1">
                <div
                  className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 rounded-full transition-all"
                  style={{ width: `${data.government.stability_score}%` }}
                />
              </div>
            </div>
          </div>
        </Section>

        {/* ============================================ */}
        {/* Predicted Tenure (SIMULATED) */}
        {/* ============================================ */}
        <Section
          title="Predicted Tenure"
          icon={<Clock className="w-4 h-4" />}
          source={srcOf('prediction.predicted_tenure_days')}
        >
          <div className="text-center p-4 bg-gray-800/50 rounded-lg">
            <div className="text-3xl font-bold text-white">
              {Math.round(data.prediction.predicted_tenure_days / 30)} months
            </div>
            <div className="text-sm text-gray-400 mt-1">
              Confidence:{' '}
              {(data.prediction.confidence_score * 100).toFixed(0)}%
            </div>
            <div className="flex justify-center gap-4 mt-3 text-xs">
              <div>
                <span className="text-gray-500">Best</span>
                <span className="ml-1 text-green-400">
                  {Math.round(data.prediction.best_case_tenure / 30)}m
                </span>
              </div>
              <div>
                <span className="text-gray-500">Likely</span>
                <span className="ml-1 text-white">
                  {Math.round(data.prediction.predicted_tenure_days / 30)}m
                </span>
              </div>
              <div>
                <span className="text-gray-500">Worst</span>
                <span className="ml-1 text-red-400">
                  {Math.round(data.prediction.worst_case_tenure / 30)}m
                </span>
              </div>
            </div>
          </div>
        </Section>

        {/* ============================================ */}
        {/* Next Party */}
        {/* ============================================ */}
        <Section
          title="Next Party Prediction"
          icon={<Users className="w-4 h-4" />}
          source={srcOf('prediction.predicted_party')}
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <span className="text-white font-medium">
                {data.prediction.predicted_party}
              </span>
              <span className="text-blue-400 font-bold">
                {(data.prediction.confidence_score * 100).toFixed(0)}%
              </span>
            </div>
            {Object.entries(data.prediction.next_party_probabilities)
              .filter(
                ([party]) => party !== data.prediction.predicted_party,
              )
              .map(([party, probability], idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-gray-400">{party}</span>
                  <span className="text-gray-300">
                    {(Number(probability) * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
          </div>
        </Section>

        {/* ============================================ */}
        {/* Sentiment (HYBRID) */}
        {/* ============================================ */}
        <Section
          title="Public Sentiment"
          icon={<BarChart3 className="w-4 h-4" />}
          source={srcOf('sentiment.party_support')}
        >
          <div className="space-y-2">
            {Object.entries(data.sentiment.party_support)
              .sort((a, b) => Number(b[1]) - Number(a[1]))
              .map(([party, support]) => (
                <div key={party} className="flex items-center gap-3">
                  <span className="text-sm text-gray-400 w-32 truncate">
                    {party}
                  </span>
                  <div className="flex-1 h-2 bg-gray-700 rounded-full">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all"
                      style={{ width: `${support}%` }}
                    />
                  </div>
                  <span className="text-sm text-white font-medium w-12 text-right">
                    {support}%
                  </span>
                </div>
              ))}
          </div>
        </Section>

        {/* ============================================ */}
        {/* Corruption (STATIC) */}
        {/* ============================================ */}
        <Section
          title="Corruption Index"
          icon={<Shield className="w-4 h-4" />}
          source={srcOf('corruption.cpi_score')}
        >
          <div className="flex items-center justify-between">
            <div className="text-3xl font-bold text-white">
              {data.corruption.cpi_score}
            </div>
            <div className="text-sm text-gray-400">
              Rank: #{data.corruption.global_rank}/180
              <span className="ml-2 text-xs">
                {data.corruption.trend === 'improving' ? (
                  <span className="text-green-400">↑ Improving</span>
                ) : (
                  <span className="text-red-400">↓ Declining</span>
                )}
              </span>
            </div>
          </div>
        </Section>
      </div>
    </motion.div>
  );
};

// ============================================================
// Helper components
// ============================================================

const Section: React.FC<{
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  action?: React.ReactNode;
  source?: MetricSource;
}> = ({ title, icon, children, action, source }) => (
  <div className="border border-gray-700/50 rounded-lg p-4">
    <SectionHead title={title} icon={icon} source={source} action={action} />
    {children}
  </div>
);

const MetricItem: React.FC<{
  label: string;
  value: string;
  trend: number;
  source?: MetricSource;
}> = ({ label, value, trend, source }) => (
  <div className="p-3 bg-gray-800/30 rounded-lg">
    <div className="flex items-center justify-between">
      <div className="text-xs text-gray-400">{label}</div>
      {source && <DataBadge source={source} />}
    </div>
    <div className="flex items-center gap-1 mt-1">
      <span className="text-white font-medium">{value}</span>
      {trend > 0 ? (
        <TrendingUp className="w-3 h-3 text-green-400" />
      ) : (
        <TrendingDown className="w-3 h-3 text-red-400" />
      )}
    </div>
  </div>
);

const SentimentBadge: React.FC<{ score: number }> = ({ score }) => {
  const label =
    score > 0.15 ? 'Positive' : score < -0.15 ? 'Negative' : 'Neutral';
  const cls =
    score > 0.15
      ? 'bg-green-500/15 text-green-400 border-green-500/30'
      : score < -0.15
      ? 'bg-red-500/15 text-red-400 border-red-500/30'
      : 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30';

  return (
    <span
      className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full border ${cls}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {label} {score >= 0 ? '+' : ''}
      {score.toFixed(2)}
    </span>
  );
};

const ToneBar: React.FC<{
  positive: number;
  neutral: number;
  negative: number;
}> = ({ positive, neutral, negative }) => {
  const total = positive + neutral + negative || 1;
  const pct = (v: number) => `${(v / total) * 100}%`;

  return (
    <div className="space-y-1">
      <div className="flex h-1.5 rounded-full overflow-hidden bg-gray-800">
        <div className="bg-green-500" style={{ width: pct(positive) }} />
        <div className="bg-gray-500" style={{ width: pct(neutral) }} />
        <div className="bg-red-500" style={{ width: pct(negative) }} />
      </div>
      <div className="flex justify-between text-[10px] text-gray-500">
        <span className="text-green-400">+{positive}</span>
        <span>{neutral}</span>
        <span className="text-red-400">-{negative}</span>
      </div>
    </div>
  );
};

const HeadlineRow: React.FC<{
  title: string;
  url: string;
  source: string;
  tone: number;
  date: string;
}> = ({ title, url, source, tone, date }) => {
  const toneColor =
    tone > 0.15
      ? 'text-green-400'
      : tone < -0.15
      ? 'text-red-400'
      : 'text-gray-500';
  const toneIcon = tone > 0.15 ? '▲' : tone < -0.15 ? '▼' : '—';

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="block p-2 rounded-lg bg-gray-800/30 hover:bg-gray-800/60
                 transition-colors group"
    >
      <div className="flex items-start gap-2">
        <span className={`text-[10px] mt-0.5 ${toneColor}`} aria-hidden>
          {toneIcon}
        </span>
        <div className="flex-1 min-w-0">
          <div className="text-sm text-white line-clamp-2 group-hover:text-cyan-300 transition-colors">
            {title}
          </div>
          <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-500">
            <span className="truncate">{source}</span>
            {date && (
              <>
                <span>·</span>
                <span className="whitespace-nowrap">
                  {formatRelative(date)}
                </span>
              </>
            )}
            <ExternalLink className="w-2.5 h-2.5 ml-auto opacity-0 group-hover:opacity-100" />
          </div>
        </div>
      </div>
    </a>
  );
};

const MiniStat: React.FC<{
  label: string;
  value: string;
  positive: boolean;
}> = ({ label, value, positive }) => (
  <div className="p-2 bg-gray-800/40 rounded">
    <div className="text-[10px] text-gray-500 uppercase tracking-wide">
      {label}
    </div>
    <div
      className={`text-xs font-medium mt-0.5 ${
        positive ? 'text-green-400' : 'text-red-400'
      }`}
    >
      {value}
    </div>
  </div>
);

// ---------- utils ----------
function formatRelative(dateStr: string): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr.slice(0, 16);

  const diffMs = Date.now() - d.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  return d.toLocaleDateString();
}