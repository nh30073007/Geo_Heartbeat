"""Dashboard aggregation/search endpoints.

These endpoints deliberately expose one normalized contract for the UI so the
React dashboard never needs to recreate backend calculations from hardcoded
numbers. WebSocket remains the low-latency transport; these REST endpoints
provide initial hydration, search/filtering, calendar/event data and a safe
recovery path when a socket reconnects.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ...core.runtime import runtime

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
runner = runtime.simulation_runner


def _engine(sim_id: str):
    engine = runner.simulations.get(sim_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return engine


def _global_stability(state: Dict[str, Any]) -> float:
    value = (
        float(state.get("economic_stability", 0))
        + float(state.get("trade_stability", 0))
        + float(state.get("currency_stability", 0))
        + float(state.get("supply_chain_stability", 0))
    ) / 4.0
    value -= float(state.get("strategic_tension", 0)) * 0.18
    value += float(state.get("public_sentiment", 0)) * 4
    return round(max(0, min(100, value)), 2)


def _conflicts(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    tension = float(state.get("strategic_tension", 0))
    base = [
        ("c1", "Russia vs Ukraine", "Military", "Eastern Europe", 82),
        ("c2", "Israel–Hamas", "Proxy War", "Middle East", 76),
        ("c3", "South China Sea", "Territorial", "Indo-Pacific", 59),
        ("c4", "India–Pakistan", "Border Tension", "South Asia", 68),
        ("c5", "Ethiopia Internal", "Civil War", "East Africa", 51),
    ]
    delta = (tension - 31) * 0.6
    result = []
    for cid, name, kind, region, momentum in base:
        m = round(max(5, min(99, momentum + delta)))
        severity = "High" if m >= 70 else "Medium" if m >= 45 else "Low"
        result.append({"id": cid, "name": name, "type": kind, "region": region, "momentum": m, "severity": severity})
    return result


@router.get("/overview/{sim_id}")
async def dashboard_overview(sim_id: str, history_limit: int = Query(120, ge=10, le=500)):
    engine = _engine(sim_id)
    state = engine.get_state()
    env = state.get("environment", {})
    history = engine.get_history(limit=history_limit)

    history_payload = [
        {"round": item.round, "timestamp": item.timestamp.isoformat(), "state": item.state_snapshot}
        for item in history
    ]

    # Agent telemetry is sourced directly from the learning objects.
    agents = {
        "hegemon": {
            "strategy": state.get("hegemon_strategy"),
            "learning": state.get("hegemon_learning"),
            "utility": state.get("hegemon_utility", 0),
        },
        "sovereign": {
            "strategy": state.get("sovereign_strategy"),
            "learning": state.get("sovereign_learning"),
            "utility": state.get("sovereign_utility", 0),
        },
    }

    events = [
        {"type": e.get("type"), "timestamp": e.get("timestamp"), "data": e.get("data", {})}
        for e in engine.events.get_history(limit=50)
    ]

    regions = env.get("regions", [])
    resource_pressure = round(max(0, min(100, 100 - float(env.get("supply_chain_stability", 0)) + float(env.get("strategic_tension", 0)) * 0.25)), 2)

    return {
        "sim_id": sim_id,
        "timestamp": datetime.now().isoformat(),
        "status": state.get("status"),
        "current_round": engine.current_round,
        "max_rounds": engine.config.max_rounds,
        "scenario": getattr(engine, "scenario_name", None),
        "state": env,
        "global_stability": _global_stability(env),
        "resource_pressure": resource_pressure,
        "active_conflicts": _conflicts(env),
        "regions": regions,
        "agents": agents,
        "history": history_payload,
        "events": events,
        "performance": engine.get_performance_metrics(),
    }


@router.get("/search/{sim_id}")
async def dashboard_search(
    sim_id: str,
    q: str = Query("", max_length=100),
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(12, ge=1, le=50),
):
    """Search live dashboard entities, events and countries/regions."""
    engine = _engine(sim_id)
    state = engine.get_state().get("environment", {})
    needle = q.strip().lower()
    conflicts = _conflicts(state)
    regions = state.get("regions", [])
    items: List[Dict[str, Any]] = []

    for c in conflicts:
        items.append({"kind": "conflict", "id": c["id"], "title": c["name"], "subtitle": f"{c['type']} · {c['region']}", "severity": c["severity"].lower(), "target": "section-conflicts"})

    for region in regions:
        name = region.get("region_name", "Region")
        items.append({"kind": "region", "id": name.lower().replace(" ", "-"), "title": name, "subtitle": f"Economic {round(region.get('economic_index', 0))} · Tech {round(region.get('technology_index', 0))}", "severity": "info", "target": "section-world"})

    countries = [
        ("United States", "North America", "info"), ("China", "Asia Pacific", "warning"),
        ("Russia", "Europe", "warning"), ("India", "Asia Pacific", "info"),
        ("European Union", "Europe", "info"), ("Brazil", "South America", "success"),
        ("Australia", "Asia Pacific", "info"),
    ]
    for name, region, sev in countries:
        items.append({"kind": "country", "id": name.lower().replace(" ", "-"), "title": name, "subtitle": region, "severity": sev, "target": "section-world"})

    for event in engine.events.get_history(limit=80):
        data = event.get("data", {}) or {}
        text = f"{event.get('type', '')} {data}"
        items.append({"kind": "event", "id": event.get("id", event.get("timestamp")), "title": event.get("type", "event").replace("_", " ").title(), "subtitle": text[:120], "severity": "critical" if "fail" in event.get("type", "") else "info", "target": "section-analytics"})

    filtered = []
    for item in items:
        if category and item["kind"] != category.lower():
            continue
        if severity and item["severity"] != severity.lower():
            continue
        if needle and needle not in f"{item['title']} {item['subtitle']}".lower():
            continue
        filtered.append(item)
    return {"query": q, "total": len(filtered), "results": filtered[:limit], "timestamp": datetime.now().isoformat()}


@router.get("/events/{sim_id}")
async def dashboard_events(
    sim_id: str,
    q: str = Query("", max_length=100),
    limit: int = Query(30, ge=1, le=100),
):
    engine = _engine(sim_id)
    needle = q.strip().lower()
    events = engine.events.get_history(limit=200)
    result = []
    for event in reversed(events):
        text = f"{event.get('type', '')} {event.get('source', '')} {event.get('data', {})}".lower()
        if needle and needle not in text:
            continue
        result.append(event)
        if len(result) >= limit:
            break
    return {"sim_id": sim_id, "events": result, "timestamp": datetime.now().isoformat()}


@router.get("/calendar/{sim_id}")
async def dashboard_calendar(sim_id: str):
    """Return scenario-aware forecast milestones for the UI calendar."""
    engine = _engine(sim_id)
    base_round = engine.current_round
    milestones = [
        ("Strategic review", "simulation", 5),
        ("Alliance posture review", "diplomacy", 10),
        ("Economic resilience checkpoint", "economy", 20),
        ("Technology capability assessment", "technology", 30),
        ("Global equilibrium review", "analytics", 50),
    ]
    now = datetime.now()
    events = [
        {"id": f"milestone-{i}", "name": name, "type": kind, "round": base_round + offset, "date": (now + timedelta(days=offset)).strftime("%d %b %Y")}
        for i, (name, kind, offset) in enumerate(milestones, 1)
    ]
    return {"sim_id": sim_id, "events": events, "timestamp": now.isoformat()}
