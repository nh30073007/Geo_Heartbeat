// frontend/app/components/Dashboard/CountryCard.tsx
'use client';

import { CountryDashboardData } from '@/app/types/country';
import { motion } from 'framer-motion';
import {
  TrendingUp, TrendingDown, AlertTriangle,
  CheckCircle, XCircle, Clock, Users,
  BarChart3, Shield, DollarSign, Building2,
} from 'lucide-react';

interface CountryCardProps {
  data: CountryDashboardData;
  onClose: () => void;
  source?: string | null;
  round?: number | null;
}

export const CountryCard: React.FC<CountryCardProps> = ({ data, onClose, source, round }) => {
  const getStabilityColor = (score: number) => {
    if (score >= 70) return 'text-green-400';
    if (score >= 50) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'stable': return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'unstable': return <XCircle className="w-5 h-5 text-red-400" />;
      default: return <AlertTriangle className="w-5 h-5 text-yellow-400" />;
    }
  };

  const liveSource = source === 'runtime';

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
            <div className="flex items-center gap-2 mt-1">
              {getStatusIcon(data.government.status)}
              <span className={`text-sm font-medium ${getStabilityColor(data.government.stability_score)}`}>
                {data.government.status.charAt(0).toUpperCase() + data.government.status.slice(1)}
              </span>
              <span className="text-xs text-gray-500">
                Last updated: {new Date().toLocaleTimeString()}
              </span>
            </div>

            {/* LIVE indicator */}
            <div className="flex items-center gap-2 mt-2">
              <span
                className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border
                  ${liveSource
                    ? 'bg-green-500/15 text-green-400 border-green-500/30'
                    : source === 'database'
                    ? 'bg-blue-500/15 text-blue-400 border-blue-500/30'
                    : 'bg-gray-500/15 text-gray-400 border-gray-500/30'}`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${liveSource ? 'bg-green-400 animate-pulse' : 'bg-gray-400'}`}
                />
                {liveSource ? 'LIVE' : (source || 'STATIC').toUpperCase()}
              </span>
              {round != null && (
                <span className="text-[10px] text-gray-500">Round {round}</span>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            ✕
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* Economy */}
        <Section title="Economy" icon={<DollarSign className="w-4 h-4" />}>
          <div className="grid grid-cols-2 gap-3">
            <MetricItem label="GDP" value={`$${data.economy.gdp}B`} trend={data.economy.gdp_growth >= 0 ? 1 : -1} />
            <MetricItem label="Growth" value={`${data.economy.gdp_growth}%`} trend={data.economy.gdp_growth > 5 ? 1 : -1} />
            <MetricItem label="Inflation" value={`${data.economy.inflation}%`} trend={data.economy.inflation < 8 ? 1 : -1} />
            <MetricItem label="Unemployment" value={`${data.economy.unemployment}%`} trend={data.economy.unemployment < 5 ? 1 : -1} />
          </div>
          <div className="mt-3 p-3 bg-gray-800/50 rounded-lg">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">Foreign Reserves</span>
              <span className="text-white font-medium">${data.economy.foreign_reserves}B</span>
            </div>
            <div className="flex items-center justify-between text-sm mt-1">
              <span className="text-gray-400">Debt to GDP</span>
              <span className="text-white font-medium">{data.economy.debt_to_gdp}%</span>
            </div>
          </div>
        </Section>

        {/* Government */}
        <Section title="Government" icon={<Building2 className="w-4 h-4" />}>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Party</span>
              <span className="text-white font-medium">{data.government.party_name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Leader</span>
              <span className="text-white font-medium">{data.government.leader_name}</span>
            </div>
            <div className="mt-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Stability Score</span>
                <span className={`font-medium ${getStabilityColor(data.government.stability_score)}`}>
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

        {/* Predicted Tenure */}
        <Section title="Predicted Tenure" icon={<Clock className="w-4 h-4" />}>
          <div className="text-center p-4 bg-gray-800/50 rounded-lg">
            <div className="text-3xl font-bold text-white">
              {Math.round(data.prediction.predicted_tenure_days / 30)} months
            </div>
            <div className="text-sm text-gray-400 mt-1">
              Confidence: {(data.prediction.confidence_score * 100).toFixed(0)}%
            </div>
            <div className="flex justify-center gap-4 mt-3 text-xs">
              <div>
                <span className="text-gray-500">Best</span>
                <span className="ml-1 text-green-400">{Math.round(data.prediction.best_case_tenure / 30)}m</span>
              </div>
              <div>
                <span className="text-gray-500">Likely</span>
                <span className="ml-1 text-white">{Math.round(data.prediction.predicted_tenure_days / 30)}m</span>
              </div>
              <div>
                <span className="text-gray-500">Worst</span>
                <span className="ml-1 text-red-400">{Math.round(data.prediction.worst_case_tenure / 30)}m</span>
              </div>
            </div>
          </div>
        </Section>

        {/* Next Party */}
        <Section title="Next Party Prediction" icon={<Users className="w-4 h-4" />}>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg">
              <span className="text-white font-medium">{data.prediction.predicted_party}</span>
              <span className="text-blue-400 font-bold">
                {(data.prediction.confidence_score * 100).toFixed(0)}%
              </span>
            </div>
            {Object.entries(data.prediction.next_party_probabilities)
              .filter(([party]) => party !== data.prediction.predicted_party)
              .map(([party, probability], idx) => (
                <div key={idx} className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">{party}</span>
                  <span className="text-gray-300">{(Number(probability) * 100).toFixed(0)}%</span>
                </div>
              ))}
          </div>
        </Section>

        {/* Sentiment */}
        <Section title="Public Sentiment" icon={<BarChart3 className="w-4 h-4" />}>
          <div className="space-y-2">
            {Object.entries(data.sentiment.party_support)
              .sort((a, b) => Number(b[1]) - Number(a[1]))
              .map(([party, support]) => (
                <div key={party} className="flex items-center gap-3">
                  <span className="text-sm text-gray-400 w-32 truncate">{party}</span>
                  <div className="flex-1 h-2 bg-gray-700 rounded-full">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all"
                      style={{ width: `${support}%` }}
                    />
                  </div>
                  <span className="text-sm text-white font-medium w-12 text-right">{support}%</span>
                </div>
              ))}
          </div>
        </Section>

        {/* Corruption */}
        <Section title="Corruption Index" icon={<Shield className="w-4 h-4" />}>
          <div className="flex items-center justify-between">
            <div className="text-3xl font-bold text-white">{data.corruption.cpi_score}</div>
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

// Helpers
const Section: React.FC<{ title: string; icon: React.ReactNode; children: React.ReactNode }> = ({ title, icon, children }) => (
  <div className="border border-gray-700/50 rounded-lg p-4">
    <div className="flex items-center gap-2 text-gray-400 text-sm font-medium mb-3">
      {icon}
      {title}
    </div>
    {children}
  </div>
);

const MetricItem: React.FC<{ label: string; value: string; trend: number }> = ({ label, value, trend }) => (
  <div className="p-3 bg-gray-800/30 rounded-lg">
    <div className="text-xs text-gray-400">{label}</div>
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