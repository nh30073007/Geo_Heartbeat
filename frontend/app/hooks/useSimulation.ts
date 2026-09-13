"use client";

import { useCallback, useState, useEffect, useRef } from 'react';
import axios from 'axios';
import type { AgentLearningSnapshot, ForecastData, SimulationData, SimulationState } from '../types';

// ✅ FIXED: Proper API URL construction - no double /api
function resolveApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    const base = process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '');
    // If base already ends with /api, don't add another one
    return base.endsWith('/api') ? base : `${base}/api`;
  }
  if (typeof window !== 'undefined') {
    // Use hostname, not window.location.origin to avoid port issues
    return `http://${window.location.hostname}:8000/api`;
  }
  return 'http://localhost:8000/api';
}
const API_BASE = resolveApiBase();

// ✅ Add debug log
console.log('🔧 API_BASE:', API_BASE);

const initialState: SimulationState = {
  economic_stability: 74,
  technology_independence: 69,
  trade_stability: 72,
  currency_stability: 68,
  strategic_tension: 31,
  public_sentiment: 0.18,
  supply_chain_stability: 71,
  ai_capability: 77,
};

const CORE_KEYS: (keyof SimulationState)[] = [
  'economic_stability', 'technology_independence', 'trade_stability',
  'currency_stability', 'strategic_tension', 'public_sentiment',
  'supply_chain_stability', 'ai_capability'
];

function normalizeBackendState(payload: any): SimulationState | null {
  const source = payload?.environment ?? payload?.state ?? payload;
  if (!source || typeof source !== 'object') return null;
  const next: Partial<SimulationState> = {};
  for (const key of CORE_KEYS) {
    const value = Number(source[key]);
    if (Number.isFinite(value)) (next as any)[key] = value;
  }
  return Object.keys(next).length ? ({ ...initialState, ...next } as SimulationState) : null;
}

export interface AgentIntel {
  hegemonStrategy: string | null;
  sovereignStrategy: string | null;
  hegemonLearning: AgentLearningSnapshot | null;
  sovereignLearning: AgentLearningSnapshot | null;
}
const EMPTY_AGENT_INTEL: AgentIntel = {
  hegemonStrategy: null, sovereignStrategy: null,
  hegemonLearning: null, sovereignLearning: null
};

function errorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error)) {
    return String(error.response?.data?.detail || error.message || fallback);
  }
  return error instanceof Error ? error.message : fallback;
}

export function useSimulation() {
  const [simulation, setSimulation] = useState<SimulationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agentIntel, setAgentIntel] = useState<AgentIntel>(EMPTY_AGENT_INTEL);
  const [forecast, setForecast] = useState<ForecastData | null>(null);

  // Polling refs
  const pollingInterval = useRef<NodeJS.Timeout | null>(null);
  const isPolling = useRef(false);
  const currentSimId = useRef<string | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval.current) {
        clearInterval(pollingInterval.current);
        pollingInterval.current = null;
      }
      isPolling.current = false;
    };
  }, []);

  const createLocalSimulation = useCallback((maxRounds = 500) => {
    const local: SimulationData = {
      id: 'demo-local',
      status: 'paused',
      current_round: 0,
      max_rounds: maxRounds,
      year: 2026,
      scenario: 'Local Development Mode',
      state: initialState,
      history: [{ round: 0, state: initialState, timestamp: new Date().toISOString() }],
      events: []
    };
    setSimulation(local);
    return local;
  }, []);

  const setStatus = useCallback((status: SimulationData['status']) => {
    setSimulation(s => s ? { ...s, status } : s);
  }, []);

  // Core fetch functions
  const fetchState = useCallback(async (id: string) => {
    try {
      const url = `${API_BASE}/state/current/${id}`;
      console.log(`📡 Fetching state: ${url}`);
      const { data } = await axios.get(url);
      const normalized = normalizeBackendState(data.state);
      setSimulation(s => {
        if (!s) return s;
        const incomingRound = Number(data.round ?? data.state?.current_round ?? s.current_round);
        if (incomingRound < s.current_round) return s;
        return {
          ...s,
          current_round: incomingRound,
          status: data.state?.status ?? s.status,
          state: normalized ? { ...s.state, ...normalized } : s.state
        };
      });
      setAgentIntel({
        hegemonStrategy: data.state?.hegemon_strategy ?? null,
        sovereignStrategy: data.state?.sovereign_strategy ?? null,
        hegemonLearning: data.state?.hegemon_learning ?? null,
        sovereignLearning: data.state?.sovereign_learning ?? null
      });
      return data;
    } catch (e: any) {
      if (e.response?.status === 404) {
        stopPolling();
        setError(`Simulation ${id} not found. It may have expired.`);
        setSimulation(null);
      }
      return null;
    }
  }, []);

  const fetchHistory = useCallback(async (id: string, limit = 120) => {
    try {
      const url = `${API_BASE}/state/history/${id}?limit=${limit}`;
      console.log(`📡 Fetching history: ${url}`);
      const { data } = await axios.get(url);
      const history = Array.isArray(data.history) ? data.history.map((item: any, index: number) => ({
        round: Number(item?.round ?? index),
        timestamp: item?.timestamp ?? new Date().toISOString(),
        state: normalizeBackendState(item?.state ?? item) ?? initialState
      })) : [];
      setSimulation(s => s ? { ...s, history } : s);
      return data;
    } catch (e: any) {
      if (e.response?.status === 404) {
        stopPolling();
        console.warn('History not found for simulation:', id);
      }
      return null;
    }
  }, []);

  const fetchForecast = useCallback(async (id: string, horizon = 8) => {
    try {
      const url = `${API_BASE}/analytics/forecast/${id}?horizon=${horizon}`;
      console.log(`📡 Fetching forecast: ${url}`);
      const { data } = await axios.get(url);
      if (data?.available) setForecast(data as ForecastData);
      return data;
    } catch {
      return null;
    }
  }, []);

  const fetchAllData = useCallback(async (id: string) => {
    if (!id || id === 'demo-local') return;
    await Promise.all([
      fetchState(id),
      fetchHistory(id),
      fetchForecast(id)
    ]);
  }, [fetchState, fetchHistory, fetchForecast]);

  // Polling control
  const startPolling = useCallback((id: string, intervalMs = 10000) => {
    if (pollingInterval.current) {
      clearInterval(pollingInterval.current);
      pollingInterval.current = null;
    }
    
    isPolling.current = true;
    currentSimId.current = id;
    
    // Immediate first fetch
    fetchAllData(id);
    
    // Set up interval
    pollingInterval.current = setInterval(() => {
      if (isPolling.current && currentSimId.current) {
        fetchAllData(currentSimId.current);
      }
    }, intervalMs);
    
    console.log(`🔄 Started polling for ${id} every ${intervalMs}ms`);
  }, [fetchAllData]);

  const stopPolling = useCallback(() => {
    isPolling.current = false;
    currentSimId.current = null;
    if (pollingInterval.current) {
      clearInterval(pollingInterval.current);
      pollingInterval.current = null;
    }
    console.log('⏹️ Stopped polling');
  }, []);

  const createSimulation = useCallback(async (maxRounds: number = 500, scenarioId?: string) => {
    setLoading(true);
    setError(null);
    try {
      const url = `${API_BASE}/simulation/create`;
      console.log(`📡 Creating simulation: ${url}`);
      const { data } = await axios.post(url, {
        max_rounds: maxRounds,
        stochastic: true,
        mode: 'realtime',
        scenario_id: scenarioId || undefined,
        use_equilibrium: true,
        use_q_learning: true,
        exploration_rate: 0.2,
        learning_rate: 0.1,
        discount_factor: 0.95,
        config: { realtime_interval_seconds: 0.75 },
      });
      
      const normalized = normalizeBackendState(data?.initial_state) || initialState;
      const next: SimulationData = {
        id: data.sim_id,
        status: 'created',
        current_round: 0,
        max_rounds: maxRounds,
        year: 2026,
        scenario: data.scenario_name || data.scenario || 'Multipolar World',
        state: normalized,
        history: [],
        events: []
      };
      setSimulation(next);
      
      // Start polling for this simulation
      startPolling(data.sim_id);
      
      return next;
    } catch (e) {
      setError(errorMessage(e, 'Failed to create simulation'));
      return null;
    } finally {
      setLoading(false);
    }
  }, [startPolling]);

  const startSimulation = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const url = `${API_BASE}/simulation/start/${id}?background=true`;
      console.log(`📡 Starting simulation: ${url}`);
      await axios.post(url);
      setSimulation(s => s ? { ...s, status: 'running' } : s);
      
      if (id !== 'demo-local') {
        startPolling(id);
      }
      
      return true;
    } catch (e) {
      setError(errorMessage(e, 'Failed to start simulation'));
      return false;
    } finally {
      setLoading(false);
    }
  }, [startPolling]);

  const pauseSimulation = useCallback(async (id: string) => {
    try {
      await axios.post(`${API_BASE}/simulation/pause/${id}`);
      setSimulation(s => s ? { ...s, status: 'paused' } : s);
      return true;
    } catch (e) {
      setError(errorMessage(e, 'Failed to pause simulation'));
      return false;
    }
  }, []);

  const resumeSimulation = useCallback(async (id: string) => {
    try {
      await axios.post(`${API_BASE}/simulation/resume/${id}`);
      setSimulation(s => s ? { ...s, status: 'running' } : s);
      
      if (id !== 'demo-local') {
        startPolling(id);
      }
      
      return true;
    } catch (e) {
      setError(errorMessage(e, 'Failed to resume simulation'));
      return false;
    }
  }, [startPolling]);

  const stopSimulation = useCallback(async (id: string) => {
    try {
      await axios.post(`${API_BASE}/simulation/stop/${id}`);
      setSimulation(s => s ? { ...s, status: 'stopped' } : s);
      stopPolling();
      return true;
    } catch (e) {
      setError(errorMessage(e, 'Failed to stop simulation'));
      return false;
    }
  }, [stopPolling]);

  const getState = useCallback(async (id: string) => fetchState(id), [fetchState]);
  const getHistory = useCallback(async (id: string, limit = 120) => fetchHistory(id, limit), [fetchHistory]);
  const getForecast = useCallback(async (id: string, horizon = 8) => fetchForecast(id, horizon), [fetchForecast]);

  const stepSimulation = useCallback(async (id: string) => {
    try {
      const { data } = await axios.post(`${API_BASE}/simulation/step/${id}`);
      const state = normalizeBackendState(data?.state);
      setSimulation(s => s ? {
        ...s,
        current_round: Number(data?.state?.current_round ?? s.current_round),
        status: data?.state?.status ?? 'paused',
        state: state || s.state
      } : s);
      return data;
    } catch (e) {
      setError(errorMessage(e, 'Manual step failed'));
      return null;
    }
  }, []);

  const resetBackendSimulation = useCallback(async (id: string) => {
    try {
      const { data } = await axios.post(`${API_BASE}/simulation/reset/${id}`);
      const state = normalizeBackendState(data?.state);
      setSimulation(s => s ? {
        ...s,
        current_round: 0,
        status: 'paused',
        state: state || s.state,
        history: []
      } : s);
      setForecast(null);
      setAgentIntel(EMPTY_AGENT_INTEL);
      
      if (id !== 'demo-local') {
        startPolling(id);
      }
      
      return data;
    } catch (e) {
      setError(errorMessage(e, 'Reset failed'));
      return null;
    }
  }, [startPolling]);

  const executeAction = useCallback(async (id: string, action: string) => {
    try {
      const { data } = await axios.post(`${API_BASE}/simulation/action/${id}`, { action });
      const state = normalizeBackendState(data?.state);
      setSimulation(s => s ? { ...s, state: state || s.state } : s);
      return data;
    } catch (e) {
      setError(errorMessage(e, `Action failed: ${action}`));
      return null;
    }
  }, []);

  const createCheckpoint = useCallback(async (id: string) => {
    try {
      const { data } = await axios.post(`${API_BASE}/simulation/checkpoint/${id}`);
      return data;
    } catch (e) {
      setError(errorMessage(e, 'Checkpoint failed'));
      return null;
    }
  }, []);

  const exportState = useCallback(async (id: string) => {
    try {
      const { data } = await axios.post(`${API_BASE}/state/export/${id}`);
      return data;
    } catch (e) {
      setError(errorMessage(e, 'Export failed'));
      return null;
    }
  }, []);

  const updateState = useCallback((patch: Partial<SimulationState>, round?: number) => {
    setSimulation(s => {
      if (!s) return s;
      const nextState = { ...s.state, ...patch };
      const nextRound = round ?? s.current_round;
      const point = {
        round: nextRound,
        state: nextState,
        timestamp: new Date().toISOString()
      };
      const history = s.history.length && s.history[s.history.length - 1]?.round === nextRound
        ? [...s.history.slice(0, -1), point]
        : [...s.history, point].slice(-120);
      return { ...s, current_round: nextRound, state: nextState, history };
    });
  }, []);

  const simulateLocalTick = useCallback(() => {
    setSimulation(s => {
      if (!s || s.status !== 'running') return s;
      const drift = () => (Math.random() - 0.5) * 2.2;
      const nextState = { ...s.state,
        economic_stability: Math.max(0, Math.min(100, s.state.economic_stability + drift())),
        technology_independence: Math.max(0, Math.min(100, s.state.technology_independence + drift() * 0.6)),
        trade_stability: Math.max(0, Math.min(100, s.state.trade_stability + drift())),
        currency_stability: Math.max(0, Math.min(100, s.state.currency_stability + drift() * 0.5)),
        strategic_tension: Math.max(0, Math.min(100, s.state.strategic_tension + drift())),
        supply_chain_stability: Math.max(0, Math.min(100, s.state.supply_chain_stability + drift())),
        ai_capability: Math.max(0, Math.min(100, s.state.ai_capability + Math.abs(drift()) * 0.18)),
        public_sentiment: Math.max(-1, Math.min(1, s.state.public_sentiment + drift() / 300)),
      };
      const round = s.current_round + 1;
      return {
        ...s,
        current_round: round,
        state: nextState,
        history: [...s.history, { round, state: nextState, timestamp: new Date().toISOString() }].slice(-120)
      };
    });
  }, []);

  return {
    simulation,
    loading,
    error,
    agentIntel,
    forecast,
    createSimulation,
    createLocalSimulation,
    setStatus,
    startSimulation,
    pauseSimulation,
    resumeSimulation,
    stopSimulation,
    getState,
    getHistory,
    getForecast,
    stepSimulation,
    resetBackendSimulation,
    executeAction,
    createCheckpoint,
    exportState,
    updateState,
    simulateLocalTick,
    startPolling,
    stopPolling
  };
}