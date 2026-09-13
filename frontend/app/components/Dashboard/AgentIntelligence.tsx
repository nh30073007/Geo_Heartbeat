import { Bot, Crosshair, ShieldHalf } from 'lucide-react';
import { Panel } from './Panel';
import type { AgentLearningSnapshot } from '../../types';

const STRATEGY_NAMES: Record<string, string> = {
  H1: 'Economic Pressure', H2: 'Information Influence', H3: 'Financial Pressure', H4: 'High Escalation',
  S1: 'De-dollarized Trade', S2: 'Local Open-Source AI', S3: 'Trade Diversification', S4: 'Defensive Alliance',
};

function AgentRow({ label, tone, strategy, learning }: { label: string; tone: 'blue' | 'amber'; strategy: string | null; learning: AgentLearningSnapshot | null }) {
  const epsilon = learning?.epsilon ?? null;
  // epsilon starts near ~0.15-0.2 and decays toward epsilon_min (0.05) as
  // the agent accumulates experience -- lower % explored = more confident.
  const confidencePct = epsilon != null ? Math.round((1 - epsilon) * 100) : null;
  return (
    <div className="agent-row">
      <div className={`agent-icon ${tone}`}>{tone === 'blue' ? <Crosshair size={15}/> : <ShieldHalf size={15}/>}</div>
      <div className="agent-main">
        <div className="agent-top"><b>{label}</b><span>{strategy ? (STRATEGY_NAMES[strategy] ?? strategy) : 'Waiting for first move…'}</span></div>
        <div className="mini-progress"><i style={{ width: `${confidencePct ?? 0}%` }} /></div>
        <div className="agent-stats">
          <span>Confidence: <b>{confidencePct != null ? `${confidencePct}%` : '—'}</b></span>
          <span>States learned: <b>{learning?.q_states_learned ?? 0}</b></span>
          <span>Avg reward: <b>{learning?.avg_recent_reward ?? 0}</b></span>
        </div>
      </div>
    </div>
  );
}

export function AgentIntelligence({ hegemonStrategy, sovereignStrategy, hegemonLearning, sovereignLearning }: {
  hegemonStrategy: string | null;
  sovereignStrategy: string | null;
  hegemonLearning: AgentLearningSnapshot | null;
  sovereignLearning: AgentLearningSnapshot | null;
}) {
  const rounds = hegemonLearning?.rounds_observed ?? 0;
  return (
    <Panel eyebrow="TABULAR Q-LEARNING" title="Agent Intelligence" action={<span className="feed-live"><Bot size={13}/> {rounds} rounds learned</span>}>
      <div className="agent-list">
        <AgentRow label="Hegemon" tone="blue" strategy={hegemonStrategy} learning={hegemonLearning} />
        <AgentRow label="Sovereign" tone="amber" strategy={sovereignStrategy} learning={sovereignLearning} />
      </div>
      <div className="feed-footer"><span>Both agents update Q(s,a) every round from the environment's real reward signal — exploration decays as confidence rises.</span></div>
    </Panel>
  );
}
