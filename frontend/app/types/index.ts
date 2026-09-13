export type SimulationStatus = 'idle' | 'created' | 'running' | 'paused' | 'completed' | 'stopped' | 'failed';

export interface SimulationState {
  economic_stability: number;
  technology_independence: number;
  trade_stability: number;
  currency_stability: number;
  strategic_tension: number;
  public_sentiment: number;
  supply_chain_stability: number;
  ai_capability: number;
}

export interface SimulationHistoryPoint {
  round: number;
  state: SimulationState;
  timestamp: string;
}

export interface SimulationEvent {
  id?: string;
  type: string;
  title?: string;
  description?: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  round: number;
  timestamp: string;
  actor?: string;
}

export interface SimulationData {
  id: string;
  status: SimulationStatus;
  current_round: number;
  max_rounds: number;
  year: number;
  scenario: string;
  state: SimulationState;
  history: SimulationHistoryPoint[];
  events: SimulationEvent[];
}

export interface AgentLearningSnapshot {
  epsilon: number;
  q_states_learned: number;
  q_entries: number;
  avg_recent_reward: number;
  rounds_observed: number;
}

export interface ForecastMetric {
  predicted: number[];
  lower: number[];
  upper: number[];
  trend: 'rising' | 'falling' | 'flat';
  slope_per_round: number;
  history: number[];
}

export interface ForecastData {
  available: boolean;
  horizon?: number;
  last_round?: number;
  future_rounds?: number[];
  metrics: Partial<Record<keyof SimulationState, ForecastMetric>>;
}

export interface WebSocketMessage<T = unknown> {
  type: string;
  data?: T;
  timestamp?: string;
  sim_id?: string;
}

export interface Conflict {
  id: string;
  name: string;
  type: string;
  severity: 'Low' | 'Medium' | 'High' | 'Critical';
  region: string;
  momentum: number;
}

export interface CountryPower {
  name: string;
  value: number;
  code: string;
  tone: 'blue' | 'red' | 'violet' | 'amber' | 'green' | 'slate';
}

export interface IntelligenceItem {
  id: string;
  time: string;
  title: string;
  detail: string;
  severity: 'info' | 'success' | 'warning' | 'critical';
}
