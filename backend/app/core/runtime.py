"""Shared application runtime with persistence support.

A single process owns the simulation runner, scenario manager, event manager,
and websocket manager. Route modules import this object instead of creating
independent managers, which keeps simulation state consistent across APIs.
"""
from __future__ import annotations

import asyncio
import json
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Set

from ..realtime import EventManager
from ..realtime.websocket import WebSocketManager, WebSocketMessage
from ..simulation import SimulationRunner, ScenarioManager, SimulationEvent

logger = logging.getLogger(__name__)


class ApplicationRuntime:
    def __init__(self) -> None:
        self.simulation_runner = SimulationRunner()
        self.scenario_manager = ScenarioManager()
        self.event_manager = EventManager()
        self.websocket_manager = WebSocketManager(self.event_manager)
        self._attached: Set[str] = set()
        
        # Persistence setup
        self._cache_dir = Path("data/cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load cached simulations on startup
        self._load_cached_simulations()
        
        # Cleanup task
        self._cleanup_task = None
        self._initialized = False

    async def start(self) -> None:
        """Start background tasks"""
        if self._initialized:
            return
        self._initialized = True
        
        # Start cleanup loop
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        # Start WebSocket heartbeat
        await self.websocket_manager.start_heartbeat()
        
        logger.info("✅ Application runtime started with persistence")

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup expired runners"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._cleanup_expired_runners()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _cleanup_expired_runners(self) -> None:
        """Remove runners older than 24 hours"""
        now = datetime.now()
        expired = []
        
        for sim_id in list(self.simulation_runner.simulations.keys()):
            engine = self.simulation_runner.simulations.get(sim_id)
            if engine and hasattr(engine, 'created_at'):
                if now - engine.created_at > timedelta(hours=24):
                    expired.append(sim_id)
        
        for sim_id in expired:
            logger.info(f"🧹 Cleaning up expired simulation: {sim_id}")
            self._save_simulation_to_cache(sim_id)
            del self.simulation_runner.simulations[sim_id]
            if sim_id in self._attached:
                self._attached.remove(sim_id)

    def _load_cached_simulations(self) -> None:
        """Load all cached simulations from disk"""
        try:
            cache_files = list(self._cache_dir.glob("sim_*.pkl"))
            for cache_file in cache_files:
                try:
                    with open(cache_file, 'rb') as f:
                        engine = pickle.load(f)
                        sim_id = cache_file.stem
                        if getattr(engine, 'events', None) is None:
                            engine.events = SimulationEvent()
                        engine.sim_id = sim_id
                        self.simulation_runner.simulations[sim_id] = engine
                        logger.info(f"📂 Loaded cached simulation: {sim_id}")
                except Exception as e:
                    logger.warning(f"Failed to load cache {cache_file}: {e}")
        except Exception as e:
            logger.error(f"Error loading cached simulations: {e}")

    def _save_simulation_to_cache(self, sim_id: str) -> None:
        """Persist an engine without serializing runtime-only event handlers."""
        try:
            engine = self.simulation_runner.simulations.get(sim_id)
            if not engine:
                return
            cache_file = self._cache_dir / f"{sim_id}.pkl"

            # Event handlers contain closures bound to this runtime and cannot
            # be pickled. Preserve the event history while replacing only the
            # runtime callback registry for the duration of serialization.
            original_events = engine.events
            cache_events = SimulationEvent()
            if original_events is not None:
                cache_events.event_history = list(original_events.event_history[-cache_events.max_history:])
            engine.events = cache_events
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(engine, f)
            finally:
                engine.events = original_events
            logger.info(f"💾 Saved simulation to cache: {sim_id}")
        except Exception as e:
            logger.error(f"Failed to cache simulation {sim_id}: {e}")

    def _load_simulation_from_cache(self, sim_id: str) -> Optional[Any]:
        """Load simulation engine from disk cache"""
        try:
            cache_file = self._cache_dir / f"{sim_id}.pkl"
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    engine = pickle.load(f)
                    if getattr(engine, 'events', None) is None:
                        engine.events = SimulationEvent()
                    engine.sim_id = sim_id
                    logger.info(f"📂 Loaded simulation from cache: {sim_id}")
                    return engine
        except Exception as e:
            logger.error(f"Failed to load simulation {sim_id} from cache: {e}")
        return None

    def get_or_create_engine(self, sim_id: str, create_fn) -> Any:
        """Get existing engine or create new one with persistence"""
        # Check memory first
        if sim_id in self.simulation_runner.simulations:
            return self.simulation_runner.simulations[sim_id]
        
        # Try cache
        cached = self._load_simulation_from_cache(sim_id)
        if cached:
            self.simulation_runner.simulations[sim_id] = cached
            return cached
        
        # Create new
        engine = create_fn()
        self.simulation_runner.simulations[sim_id] = engine
        return engine

    def room_for_simulation(self, sim_id: str) -> str:
        return f"simulation:{sim_id}"

    def attach_simulation(self, sim_id: str) -> None:
        """Bridge engine events to the simulation's websocket room."""
        if sim_id in self._attached:
            return
        engine = self.simulation_runner.simulations.get(sim_id)
        if engine is None:
            return

        async def forward(event: Dict[str, Any]) -> None:
            payload = event.get("data", {}) or {}
            room = self.room_for_simulation(sim_id)
            if event.get("type") == "round_completed":
                # Never pass raw Pydantic/enums/datetime objects into the
                # websocket layer. Keep the event bridge JSON-safe even when
                # future dashboard telemetry adds richer model objects.
                state = engine._json_safe(engine.get_state())
                message = WebSocketMessage(
                    type="state_update",
                    data={
                        "sim_id": sim_id,
                        "round": int(payload.get("round", engine.current_round)),
                        "status": engine.status.value,
                        "state": state,
                        "event": event,
                    },
                    sender="simulation-engine",
                    room=room,
                )
            else:
                message = WebSocketMessage(
                    type="simulation_event",
                    data={"sim_id": sim_id, "event": event},
                    sender="simulation-engine",
                    room=room,
                )
            await self.websocket_manager.broadcast(message, room=room)

        # Register event handlers
        for event_type in (
            "round_completed",
            "simulation_paused",
            "simulation_resumed",
            "simulation_completed",
            "termination_triggered",
            "checkpoint_created",
        ):
            engine.events.register_handler(event_type, forward)
        
        self._attached.add(sim_id)
        logger.info(f"🔗 Attached simulation: {sim_id}")

    async def broadcast_api_event(self, sim_id: str, event_type: str, data: Dict[str, Any]) -> None:
        room = self.room_for_simulation(sim_id)
        await self.websocket_manager.broadcast(
            WebSocketMessage(
                type="simulation_event",
                data={"sim_id": sim_id, "event": {"type": event_type, "data": data}},
                sender="api",
                room=room,
            ),
            room=room,
        )

    async def shutdown(self) -> None:
        """Clean shutdown with persistence"""
        logger.info("🛑 Shutting down runtime...")
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Save all simulations
        for sim_id in list(self.simulation_runner.simulations.keys()):
            self._save_simulation_to_cache(sim_id)
        
        # Close WebSocket connections
        await self.websocket_manager.close_all()
        
        logger.info("✅ Runtime shutdown complete")


# Global runtime instance
runtime = ApplicationRuntime()