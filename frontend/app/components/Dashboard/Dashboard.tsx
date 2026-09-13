"use client";
import { useEffect, useRef, useState, useCallback } from 'react';
import axios from 'axios';
import { Activity, CheckCircle2, Download, FileText, Gauge, RefreshCw, Settings2, ShieldCheck, X, Search, Database } from 'lucide-react';
import { useSimulation } from '../../hooks/useSimulation';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useCountry } from '../../hooks/useCountry';
import type { SimulationState, WebSocketMessage, SimulationHistoryPoint } from '../../types';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { KpiStrip } from './KpiStrip';
import { WorldMap } from './WorldMap';
import { CountryCard } from './CountryCard';
import { PowerBalance } from './PowerBalance';
import { EconomicHealth } from './EconomicHealth';
import { TechnologyIndex } from './TechnologyIndex';
import { ResourcePressure } from './ResourcePressure';
import { GlobalStability } from './GlobalStability';
import { QuickActions } from './QuickActions';
import { ActiveConflicts } from './ActiveConflicts';
import { UpcomingEvents } from './UpcomingEvents';
import { MilitaryOverview } from './MilitaryOverview';
import { DiplomaticRelations } from './DiplomaticRelations';
import { IntelligenceFeed } from './IntelligenceFeed';
import { Timeline } from './Timeline';
import { ScenarioControls } from './ScenarioControls';
import { AdvancedChart } from './AdvancedChart';
import { AgentIntelligence } from './AgentIntelligence';
import { ForecastPanel } from './ForecastPanel';

const demo: SimulationState = {
  economic_stability: 74,
  technology_independence: 69,
  trade_stability: 72,
  currency_stability: 68,
  strategic_tension: 31,
  public_sentiment: 0.18,
  supply_chain_stability: 71,
  ai_capability: 77
};

function resolveApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    const base = process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '');
    return base.endsWith('/api') ? base : `${base}/api`;
  }
  if (typeof window !== 'undefined') {
    return `http://${window.location.hostname}:8000/api`;
  }
  return 'http://localhost:8000/api';
}
const API = resolveApiBase();

function resolveWsBase() {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL.replace(/\/$/, '');
  if (typeof window !== 'undefined') return `ws://${window.location.hostname}:8000/ws`;
  return 'ws://localhost:8000/ws';
}
const WS_BASE = resolveWsBase();

type Scenario = {
  id: string; name: string; description: string;
  difficulty: string; category: string; tags: string[];
};
type SearchResult = { kind: string; id: string; title: string; subtitle: string; severity: string; target: string };
type CalendarEvent = { id: string; name: string; type: string; round: number; date: string };

export default function Dashboard() {
  const sim = useSimulation();
  const {
    simulation, loading, error, agentIntel, forecast,
    createSimulation, createLocalSimulation, setStatus,
    startSimulation, pauseSimulation, resumeSimulation,
    getState, getHistory, getForecast, stepSimulation,
    resetBackendSimulation, executeAction, createCheckpoint,
    exportState, updateState, simulateLocalTick, stopPolling
  } = sim;

  // Country panel state
  const country = useCountry();
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);

  const [mobileOpen, setMobileOpen] = useState(false);
  const [toast, setToast] = useState('');
  const [running, setRunning] = useState(false);
  const [booted, setBooted] = useState(false);
  const [modal, setModal] = useState<'scenario' | 'reports' | 'settings' | 'notifications' | 'profile' | 'calendar' | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenarioFilter, setScenarioFilter] = useState('all');
  const [scenarioDifficulty, setScenarioDifficulty] = useState('all');
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [calendar, setCalendar] = useState<CalendarEvent[]>([]);
  const [events, setEvents] = useState<any[]>([]);

  const bootedRef = useRef(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const simId = simulation?.id;

  const wsUrl = simId && simId !== 'demo-local' ? `${WS_BASE}?room=${encodeURIComponent(simId)}` : WS_BASE;
  const { isConnected, lastMessage } = useWebSocket(wsUrl, { enabled: true });

  const notify = (text: string) => {
    setToast(text);
    window.setTimeout(() => setToast(''), 2600);
  };

  const hydrate = async (id: string) => {
    try {
      const [overview, cal, eventData] = await Promise.all([
        axios.get(`${API}/dashboard/overview/${id}?history_limit=120`),
        axios.get(`${API}/dashboard/calendar/${id}`),
        axios.get(`${API}/dashboard/events/${id}?limit=30`)
      ]);
      const o = overview.data;
      const normalized = o?.state;
      if (normalized) updateState(normalized, Number(o.current_round || 0));
      setCalendar(cal.data.events || []);
      setEvents(eventData.data.events || []);
    } catch (e) {
      console.warn('Hydration failed, WebSocket will recover:', e);
    }
  };

  // Boot simulation once
  useEffect(() => {
    if (bootedRef.current) return;
    bootedRef.current = true;

    (async () => {
      try {
        const r = await axios.get(`${API}/simulation/scenarios`);
        setScenarios(r.data.scenarios || []);
      } catch {
        setScenarios([]);
      }

      localStorage.removeItem('activeSimulationId');

      const created = await createSimulation(500, 'multipolar_world');
      if (created) {
        localStorage.setItem('activeSimulationId', created.id);
        const ok = await startSimulation(created.id);
        setRunning(ok);
        await hydrate(created.id);
        notify('✅ Simulation initialized successfully');
      } else {
        createLocalSimulation(500);
        setRunning(false);
        notify('⚠️ Backend unavailable — local mode active');
      }
      setBooted(true);
    })();

    return () => { stopPolling(); };
  }, [createSimulation, startSimulation, createLocalSimulation, stopPolling]);

  // WebSocket handler — also refresh country card
  useEffect(() => {
    if (!lastMessage) return;
    const msg = lastMessage as WebSocketMessage<any>;

    if (msg.type === 'state_update' && msg.data) {
      const payload = msg.data.state;
      const source = payload?.environment ?? payload;
      const incomingRound = Number(msg.data.round ?? payload?.current_round ?? 0);
      if (incomingRound >= (simulation?.current_round ?? 0)) {
        updateState(source || {}, incomingRound);
      }
      if (payload?.status) setRunning(payload.status === 'running');

      // Refresh open country card so it reflects the new round immediately
      if (selectedCountry) country.refresh();
    }

    if (msg.type === 'simulation_event') {
      const e = msg.data?.event || {};
      const t = e?.type;
      if (t) setEvents(prev => [{ ...e, id: e.id || `${t}-${Date.now()}` }, ...prev].slice(0, 30));
      if (t === 'simulation_paused') setRunning(false);
      if (t === 'simulation_resumed') setRunning(true);
      if (t === 'simulation_completed' || t === 'simulation_stopped') setRunning(false);
    }
  }, [lastMessage, updateState, simulation?.current_round, selectedCountry, country]);

  // Country selection handler
  const handleSelectCountry = useCallback((countryId: string) => {
    setSelectedCountry(countryId);
    country.fetchCountry(countryId);
  }, [country]);

  const handleCloseCountry = useCallback(() => {
    setSelectedCountry(null);
    country.reset();
  }, [country]);

  const state = simulation?.state || demo;
  const globalStability = Math.max(0, Math.min(100, Math.round(
    (state.economic_stability + state.trade_stability + state.currency_stability + state.supply_chain_stability) / 4 -
    state.strategic_tension * 0.18 +
    state.public_sentiment * 4
  )));
  const turn = simulation?.current_round || 0;
  const conflicts = 5;
  const selectedScenario = scenarios.find(s => s.id === 'multipolar_world');
  const filteredScenarios = scenarios.filter(s =>
    (scenarioFilter === 'all' || s.category === scenarioFilter) &&
    (scenarioDifficulty === 'all' || s.difficulty === scenarioDifficulty)
  );

  const handleNavigate = (label: string, sectionId: string | null) => {
    if (label === 'Reports' || label === 'Settings' || label === 'Notifications' || label === 'Profile') {
      setModal(label === 'Reports' ? 'reports' : label === 'Settings' ? 'settings' : label === 'Notifications' ? 'notifications' : 'profile');
      return;
    }
    if (label === 'Dashboard') { window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
    if (sectionId) document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const handleSearch = (value: string) => {
    setSearch(value);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!value.trim()) { setSearchResults([]); return; }
    searchTimer.current = setTimeout(async () => {
      try {
        const r = await axios.get(`${API}/dashboard/search/${simId}`, { params: { q: value, limit: 10 } });
        setSearchResults(r.data.results || []);
      } catch { setSearchResults([]); }
    }, 250);
  };

  const selectSearch = (item: SearchResult) => {
    document.getElementById(item.target)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setSearch(''); setSearchResults([]);
  };

  const toggle = async () => {
    if (!simulation) return;
    if (running) {
      if (simId !== 'demo-local') await pauseSimulation(simulation.id);
      setStatus('paused'); setRunning(false); notify('⏸️ Simulation paused');
    } else {
      if (simId === 'demo-local') {
        setRunning(true); setStatus('running'); notify('▶️ Local simulation resumed');
      } else {
        const ok = simulation.status === 'created' || simulation.status === 'stopped'
          ? await startSimulation(simulation.id)
          : await resumeSimulation(simulation.id);
        setRunning(Boolean(ok));
        notify(ok ? '▶️ Simulation resumed' : '❌ Failed to resume');
      }
    }
  };

  const advance = async () => {
    if (!simulation) return;
    if (simId === 'demo-local') { simulateLocalTick(); notify('⏩ Local turn advanced'); return; }
    if (running) { await getState(simulation.id); notify('📊 Live telemetry refreshed'); }
    else {
      const result = await stepSimulation(simulation.id);
      if (result) { await getHistory(simulation.id); notify('⏩ One strategic turn advanced'); }
    }
    // If a country card is open, refresh it
    if (selectedCountry) country.refresh();
  };

  const reset = async () => {
    if (!simulation) return;
    if (simId === 'demo-local') { createLocalSimulation(500); setRunning(false); notify('🔄 Local simulation reset'); return; }
    await resetBackendSimulation(simulation.id);
    setRunning(false);
    await hydrate(simulation.id);
    if (selectedCountry) country.refresh();
    notify('🔄 Simulation reset to baseline');
  };

  const action = async (name: string) => {
    if (!simulation) return;
    if (simId === 'demo-local') {
      const delta = name === 'Create Crisis' ? 4 : name === 'Peace Negotiation' ? -4 : -1;
      updateState({ strategic_tension: Math.max(0, Math.min(100, state.strategic_tension + delta)) });
      notify(`${name} applied locally`); return;
    }
    const result = await executeAction(simulation.id, name);
    if (result) {
      setEvents(prev => [{ type: 'user_action', data: { action: name, round: turn }, timestamp: new Date().toISOString() }, ...prev].slice(0, 30));
      if (selectedCountry) country.refresh();
      notify(`${name} applied to environment`);
    }
  };

  const checkpoint = async () => {
    if (simId && simId !== 'demo-local') {
      const r = await createCheckpoint(simId);
      if (r) notify(`📸 Checkpoint ${r.checkpoint_id} created`);
    } else notify('Checkpoint available when backend is connected');
  };

  const downloadReport = async (format: 'json' | 'csv') => {
    if (!simId || simId === 'demo-local') { notify('Run a backend simulation before exporting'); return; }
    try {
      if (format === 'csv') {
        const r = await axios.get(`${API}/analytics/report/${simId}?format=csv`, { responseType: 'blob' });
        const url = URL.createObjectURL(r.data);
        const a = document.createElement('a'); a.href = url; a.download = `geopolis-report-${simId}.csv`; a.click();
        URL.revokeObjectURL(url);
      } else {
        const r = await axios.get(`${API}/analytics/report/${simId}?format=json`);
        const blob = new Blob([JSON.stringify(r.data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = `geopolis-report-${simId}.json`; a.click();
        URL.revokeObjectURL(url);
      }
      notify(`${format.toUpperCase()} report exported`);
    } catch { notify('Report export failed'); }
  };

  const doExport = async () => {
    if (simId && simId !== 'demo-local') {
      const r = await exportState(simId);
      if (r) {
        const blob = new Blob([JSON.stringify(r, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = `state-${simId}.json`; a.click();
        URL.revokeObjectURL(url);
        notify('Current state exported');
      }
    }
  };

  const loadScenario = async (s: Scenario) => {
    setModal(null);
    if (simId && simId !== 'demo-local') await pauseSimulation(simId);
    const created = await createSimulation(500, s.id);
    if (created) {
      localStorage.setItem('activeSimulationId', created.id);
      const ok = await startSimulation(created.id);
      setRunning(Boolean(ok));
      notify(`${s.name} loaded`);
      await hydrate(created.id);
      if (selectedCountry) country.refresh();
    }
  };

  if (!booted && !simulation) {
    return (
      <div className="boot-screen">
        <div className="boot-card">
          <div className="boot-orbit"><Activity size={28} /></div>
          <b>INITIALIZING GEOPOLIS</b>
          <span>Connecting simulation engine…</span>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar open={mobileOpen} onClose={() => setMobileOpen(false)} onNavigate={handleNavigate} />
      <main className="main">
        <TopBar
          isConnected={isConnected}
          scenario={simulation?.scenario || selectedScenario?.name || 'Multipolar World'}
          turn={turn}
          year={2026}
          onMenu={() => setMobileOpen(true)}
          onScenario={() => setModal('scenario')}
          onSearch={handleSearch}
          onNotifications={() => setModal('notifications')}
          onProfile={() => setModal('profile')}
        />
        <div className="dashboard">
          <div className="status-strip">
            <div><span className="live-dot" /> REAL-TIME SIMULATION</div>
            <span>REST hydration · WebSocket telemetry · {simulation?.id || 'initializing'}</span>
            {(error || toast) && <b>{toast || error}</b>}
          </div>

          {searchResults.length > 0 && (
            <div className="search-results">
              <div className="search-results-head">
                <Search size={13} /> Backend search results
                <button onClick={() => setSearchResults([])}><X size={13} /></button>
              </div>
              {searchResults.map(r => (
                <button key={`${r.kind}-${r.id}`} onClick={() => selectSearch(r)}>
                  <span className={`search-kind ${r.severity}`}>{r.kind}</span>
                  <div><b>{r.title}</b><small>{r.subtitle}</small></div>
                </button>
              ))}
            </div>
          )}

          <KpiStrip
            stability={globalStability}
            tension={state.strategic_tension}
            tech={state.technology_independence}
            economic={state.economic_stability}
            history={simulation?.history || []}
            conflicts={conflicts}
          />

          <div className="layout-main">
            <div className="left-rail">
              <GlobalStability score={globalStability} />
              <PowerBalance state={state} />
              <div id="section-economy"><EconomicHealth score={state.economic_stability} /></div>
              <div id="section-technology">
                <TechnologyIndex
                  score={state.technology_independence}
                  ai={state.ai_capability}
                  supply={state.supply_chain_stability}
                  tension={state.strategic_tension}
                />
              </div>
            </div>

            <div className="center-rail">
              <div id="section-world">
                <WorldMap
                  state={state}
                  selectedId={selectedCountry}
                  onTool={(tool) => notify(tool === 'fullscreen' ? 'Map fullscreen control ready' : `${tool} layer control applied`)}
                  onSelectCountry={handleSelectCountry}
                />
              </div>
              <div className="two-col">
                <MilitaryOverview state={state} />
                <div id="section-treaties"><DiplomaticRelations state={state} /></div>
              </div>
              <div id="section-analytics"><AdvancedChart history={simulation?.history || []} /></div>
              <div className="two-col">
                <div id="section-agents">
                  <AgentIntelligence
                    hegemonStrategy={agentIntel.hegemonStrategy}
                    sovereignStrategy={agentIntel.sovereignStrategy}
                    hegemonLearning={agentIntel.hegemonLearning}
                    sovereignLearning={agentIntel.sovereignLearning}
                  />
                </div>
                <ForecastPanel forecast={forecast} />
              </div>
            </div>

            <div className="right-rail">
              <div id="section-conflicts">
                <ActiveConflicts state={state} onViewAll={() => { setSearch('conflict'); handleSearch('conflict'); }} />
              </div>
              <UpcomingEvents events={calendar} onOpen={() => setModal('calendar')} />
              <div id="section-resources">
                <ResourcePressure
                  score={Math.max(0, Math.min(100, 100 - state.supply_chain_stability + state.strategic_tension * 0.25))}
                  supply={state.supply_chain_stability}
                  economic={state.economic_stability}
                />
              </div>
              <IntelligenceFeed state={state} round={turn} events={events} />
            </div>
          </div>

          <div className="lower-grid">
            <QuickActions onAction={action} />
            <ScenarioControls running={running} onToggle={toggle} onEnd={advance} onReset={reset} />
          </div>
          <Timeline
            turn={turn}
            running={running}
            onToggle={toggle}
            onAdvance={advance}
            maxRounds={simulation?.max_rounds || 500}
            onReset={reset}
          />
        </div>
      </main>
      {loading && <div className="loading-bar" />}
      <div className="footer-status">
        <span><span className={`status-dot ${isConnected ? 'on' : ''}`} />{isConnected ? 'WebSocket connected' : 'Reconnecting…'}</span>
        <span>REST API + live event bus · telemetry protected</span>
      </div>

      {/* Country Card — fixed panel */}
      {country.data && (
        <CountryCard
          data={country.data}
          onClose={handleCloseCountry}
          source={country.source}
          round={country.round}
        />
      )}

      {modal && (
        <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setModal(null); }}>
          <section className="modal-card">
            <div className="modal-head">
              <div>
                <span className="eyebrow">GEOPOLIS CONTROL</span>
                <h2>
                  {modal === 'scenario' ? 'Scenario Library' :
                   modal === 'reports' ? 'Reports & Export' :
                   modal === 'settings' ? 'Runtime Settings' :
                   modal === 'notifications' ? 'Event Stream' :
                   modal === 'calendar' ? 'Forecast Calendar' :
                   'Commander Profile'}
                </h2>
              </div>
              <button className="icon-button" onClick={() => setModal(null)}><X size={17} /></button>
            </div>

            {modal === 'scenario' && (
              <div className="modal-body">
                <p className="modal-muted">Filters and scenario metadata are loaded from the backend. Selecting one creates a fresh server-side simulation and reconnects telemetry.</p>
                <div className="filter-row">
                  <select value={scenarioFilter} onChange={e => setScenarioFilter(e.target.value)}>
                    <option value="all">All categories</option>
                    {[...new Set(scenarios.map(s => s.category))].map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                  <select value={scenarioDifficulty} onChange={e => setScenarioDifficulty(e.target.value)}>
                    <option value="all">All difficulty</option>
                    {[...new Set(scenarios.map(s => s.difficulty))].map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                </div>
                <div className="scenario-grid">
                  {filteredScenarios.map(s => (
                    <button key={s.id} className={`scenario-card ${s.id === simulation?.id ? 'selected' : ''}`} onClick={() => loadScenario(s)}>
                      <div><b>{s.name}</b><span>{s.category} · {s.difficulty}</span></div>
                      <small>{s.description}</small>
                      <em>{s.tags?.slice(0, 3).join(' · ')}</em>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {modal === 'reports' && (
              <div className="modal-body">
                <div className="report-grid">
                  <button onClick={() => downloadReport('json')}>
                    <FileText size={18} /><b>JSON report</b><small>Full live analytics payload</small>
                  </button>
                  <button onClick={() => downloadReport('csv')}>
                    <Download size={18} /><b>CSV report</b><small>Performance table</small>
                  </button>
                  <button onClick={doExport}>
                    <Download size={18} /><b>State snapshot</b><small>Current simulation state</small>
                  </button>
                  <button onClick={checkpoint}>
                    <ShieldCheck size={18} /><b>Create checkpoint</b><small>Recoverable engine state</small>
                  </button>
                </div>
                <div className="modal-info"><CheckCircle2 size={15} /> Reports are generated from the live engine, not placeholder dashboard values.</div>
              </div>
            )}

            {modal === 'calendar' && (
              <div className="modal-body">
                <div className="notification-list">
                  {calendar.map(e => (
                    <div key={e.id}>
                      <span className="live-dot" />
                      <p><b>{e.name}</b> · {e.type} · Round {e.round} · {e.date}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {modal === 'settings' && (
              <div className="modal-body">
                <div className="settings-row">
                  <div><b>Engine mode</b><small>Realtime event-driven execution</small></div>
                  <span className="setting-pill">REALTIME</span>
                </div>
                <div className="settings-row">
                  <div><b>REST API</b><small>{API}</small></div>
                  <Database size={17} />
                </div>
                <div className="settings-row">
                  <div><b>WebSocket</b><small>{isConnected ? 'Connected with heartbeat' : 'Reconnecting automatically'}</small></div>
                  <span className={`setting-pill ${isConnected ? 'good' : ''}`}>{isConnected ? 'ONLINE' : 'OFFLINE'}</span>
                </div>
                <div className="settings-row">
                  <div><b>Simulation rounds</b><small>{simulation?.current_round || 0} / {simulation?.max_rounds || 500}</small></div>
                  <Gauge size={17} />
                </div>
                <div className="settings-row">
                  <div><b>Data integrity</b><small>REST hydration + WS telemetry + backend event history</small></div>
                  <Settings2 size={17} />
                </div>
              </div>
            )}

            {modal === 'notifications' && (
              <div className="modal-body">
                <div className="notification-list">
                  {events.length ? events.map((e, i) => (
                    <div key={`${e.id || e.type}-${i}`}>
                      <span className="live-dot" />
                      <p>{e.timestamp ? String(e.timestamp).replace('T', ' ').slice(0, 19) : ''} · {String(e.type || 'event').replaceAll('_', ' ')} · {e.data?.action || e.data?.round || ''}</p>
                    </div>
                  )) : (
                    <div className="empty-state"><RefreshCw size={18} /><p>Waiting for engine events…</p></div>
                  )}
                </div>
              </div>
            )}

            {modal === 'profile' && (
              <div className="modal-body">
                <div className="profile-card">
                  <div className="profile-avatar">CA</div>
                  <div>
                    <b>Commander</b>
                    <span>Global Analyst · Simulation Operator</span>
                    <small>Session: local development operator</small>
                  </div>
                </div>
                <div className="modal-info"><CheckCircle2 size={15} /> Control actions are audited by the backend event layer.</div>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}