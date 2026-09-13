"""
Simulation Runner - Manages simulation lifecycle with persistence
"""
from typing import Dict, Any, Optional, List
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
import logging

from .engine import SimulationEngine, SimulationConfig, SimulationMode, SimulationStatus
from ..environment.environment import StrategicEnvironment

logger = logging.getLogger(__name__)

class SimulationRunner:
    """
    Simulation Runner with:
    - Multiple simulation management
    - Batch processing
    - Result aggregation
    - Report generation
    - Persistence support
    """
    
    def __init__(self):
        self.simulations: Dict[str, SimulationEngine] = {}
        self.results: Dict[str, Any] = {}
        self.active_simulation: Optional[str] = None
        # One engine may only have one autonomous run task at a time.  This
        # prevents double-starts from creating duplicate rounds/events.
        self._run_tasks: Dict[str, asyncio.Task] = {}
        # Per-simulation lifecycle locks close the small race where two
        # HTTP requests schedule start tasks before either task has begun.
        self._run_locks: Dict[str, asyncio.Lock] = {}
        
        # Setup directories
        Path("data/reports").mkdir(parents=True, exist_ok=True)
        Path("data/results").mkdir(parents=True, exist_ok=True)
        Path("data/cache").mkdir(parents=True, exist_ok=True)
        
        logger.info("🏃 Simulation Runner initialized")
    
    def create_simulation(
        self,
        sim_id: str,
        config: Optional[SimulationConfig] = None,
        environment: Optional[StrategicEnvironment] = None
    ) -> SimulationEngine:
        """
        Create a new simulation
        """
        if sim_id in self.simulations:
            # Check if it's cached
            logger.warning(f"⚠️ Simulation {sim_id} already exists in memory")
            return self.simulations[sim_id]
        
        config = config or SimulationConfig()
        environment = environment or StrategicEnvironment(stochastic=config.stochastic)
        
        engine = SimulationEngine(config, environment)
        engine.sim_id = sim_id
        engine.created_at = datetime.now()
        self.simulations[sim_id] = engine
        
        logger.info(f"📋 Created simulation: {sim_id}")
        return engine
    
    async def run_simulation(self, sim_id: str) -> Dict[str, Any]:
        """Run one simulation with an idempotent, race-safe lifecycle."""
        lock = self._run_locks.setdefault(sim_id, asyncio.Lock())
        async with lock:
            if sim_id not in self.simulations:
                from ..core.runtime import runtime
                engine = runtime._load_simulation_from_cache(sim_id)
                if engine:
                    self.simulations[sim_id] = engine
                    logger.info(f"♻️ Recovered simulation from cache: {sim_id}")
                else:
                    raise ValueError(f"Simulation {sim_id} not found")

            existing = self._run_tasks.get(sim_id)
            if existing and not existing.done() and existing is not asyncio.current_task():
                logger.warning(f"⏭️ Duplicate start suppressed for active simulation: {sim_id}")
                return {
                    'status': 'already_running',
                    'sim_id': sim_id,
                    'current_round': self.simulations[sim_id].current_round,
                }

            engine = self.simulations[sim_id]
            if engine.status == SimulationStatus.COMPLETED:
                return {'status': 'completed', 'sim_id': sim_id, 'current_round': engine.current_round}

            task = asyncio.current_task()
            if task is not None:
                self._run_tasks[sim_id] = task
            self.active_simulation = sim_id
            logger.info(
                "▶️ RUN CLAIMED sim=%s task=%s",
                sim_id, id(task) if task else None
            )

            try:
                result = await engine.run()
                self.results[sim_id] = result
                self._save_result(sim_id, result)
                return {
                    'status': 'success',
                    'result': result.__dict__ if hasattr(result, '__dict__') else result
                }
            except Exception as e:
                logger.error(f"Simulation {sim_id} failed: {e}")
                return {'status': 'failed', 'error': str(e)}
            finally:
                if task is not None and self._run_tasks.get(sim_id) is task:
                    self._run_tasks.pop(sim_id, None)
                if self.active_simulation == sim_id:
                    self.active_simulation = None
                logger.info(
                    "⏹️ RUN RELEASED sim=%s task=%s round=%s",
                    sim_id, id(task) if task else None,
                    self.simulations.get(sim_id).current_round if sim_id in self.simulations else None,
                )

    def stop_simulation(self, sim_id: str):
        """Stop a running simulation"""
        if sim_id in self.simulations:
            self.simulations[sim_id].stop()
            logger.info(f"⏹️ Stopping simulation: {sim_id}")
    
    def pause_simulation(self, sim_id: str):
        """Pause a running simulation"""
        if sim_id in self.simulations:
            self.simulations[sim_id].pause()
            logger.info(f"⏸️ Pausing simulation: {sim_id}")
    
    def resume_simulation(self, sim_id: str):
        """Resume a paused simulation"""
        if sim_id in self.simulations:
            self.simulations[sim_id].resume()
            logger.info(f"▶️ Resuming simulation: {sim_id}")
    
    async def step_simulation(self, sim_id: str) -> Dict[str, Any]:
        """Advance exactly one round for interactive dashboard controls."""
        if sim_id not in self.simulations:
            # Try to recover from cache
            from ..core.runtime import runtime
            engine = runtime._load_simulation_from_cache(sim_id)
            if engine:
                self.simulations[sim_id] = engine
                logger.info(f"♻️ Recovered simulation for step: {sim_id}")
            else:
                raise ValueError(f"Simulation {sim_id} not found")
        
        engine = self.simulations[sim_id]
        if engine.status == SimulationStatus.RUNNING:
            raise ValueError("Pause the simulation before manual stepping")
        if engine.status == SimulationStatus.COMPLETED:
            return engine.get_state()
        
        engine.status = SimulationStatus.RUNNING
        await engine._run_round()
        # _run_round() owns the round increment.  Do not increment here or a
        # manual step would skip every second round and corrupt history.
        engine.performance_metrics['total_rounds'] = engine.current_round
        engine.status = (
            SimulationStatus.COMPLETED
            if engine.current_round >= engine.config.max_rounds
            else SimulationStatus.PAUSED
        )
        
        # Cache after step
        from ..core.runtime import runtime
        runtime._save_simulation_to_cache(sim_id)
        
        return engine.get_state()

    def reset_simulation(self, sim_id: str):
        """Reset a simulation to its initial environment and agent state."""
        if sim_id not in self.simulations:
            # Try to recover from cache
            from ..core.runtime import runtime
            engine = runtime._load_simulation_from_cache(sim_id)
            if engine:
                self.simulations[sim_id] = engine
                logger.info(f"♻️ Recovered simulation for reset: {sim_id}")
            else:
                raise ValueError(f"Simulation {sim_id} not found")
        
        engine = self.simulations[sim_id]
        engine.stop()
        engine.environment.reset()
        engine.current_round = 0
        engine.status = SimulationStatus.IDLE
        engine.start_time = None
        engine.end_time = None
        engine.pause_time = None
        engine.total_pause_duration = timedelta(0)
        engine._stop_requested = False
        engine._pause_requested = False
        engine._is_paused = False
        engine.state_history.clear()
        engine.checkpoints.clear()
        engine.current_checkpoint_id = None
        engine.performance_metrics = {
            'round_times': [], 'average_round_time': 0.0, 'max_round_time': 0.0,
            'total_rounds': 0, 'successful_rounds': 0, 'failed_rounds': 0,
            'errors': [], 'warnings': []
        }
        for agent in (engine.hegemon, engine.sovereign):
            agent.reset()
            agent.learning_rate = float(engine.config.learning_rate)
            agent.gamma = float(engine.config.discount_factor)
            agent.exploration_rate = float(engine.config.exploration_rate)
            agent.epsilon_min = float(engine.config.epsilon_min)
            agent.epsilon_decay = float(engine.config.epsilon_decay)
        
        # Cache after reset
        from ..core.runtime import runtime
        runtime._save_simulation_to_cache(sim_id)
        
        return engine.get_state()

    async def run_batch(
        self,
        configs: List[Dict[str, Any]],
        parallel: int = 2
    ) -> Dict[str, Any]:
        """
        Run multiple simulations in batch
        """
        results = {}
        semaphore = asyncio.Semaphore(parallel)
        
        async def run_with_semaphore(sim_id: str, config: Dict[str, Any]):
            async with semaphore:
                config_obj = SimulationConfig(**config)
                engine = self.create_simulation(sim_id, config_obj)
                return await self.run_simulation(sim_id)
        
        tasks = []
        for i, config in enumerate(configs):
            sim_id = f"batch_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            tasks.append(run_with_semaphore(sim_id, config))
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(batch_results):
            sim_id = f"batch_{i}"
            if isinstance(result, Exception):
                results[sim_id] = {'status': 'failed', 'error': str(result)}
            else:
                results[sim_id] = result
        
        # Generate batch report
        self._generate_batch_report(results)
        
        return results
    
    def _json_safe(self, value):
        """Recursively convert enums/dataclasses into JSON-safe primitives."""
        from enum import Enum
        from dataclasses import asdict, is_dataclass
        import numpy as np
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
        if is_dataclass(value):
            return self._json_safe(asdict(value))
        if isinstance(value, dict):
            return {str(self._json_safe(k)): self._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._json_safe(v) for v in value]
        return value

    def _save_result(self, sim_id: str, result):
        """Save simulation result in a portable JSON representation."""
        result_file = Path(f"data/results/{sim_id}_result.json")
        with open(result_file, 'w') as f:
            json.dump(self._json_safe(result), f, indent=2, default=str)
    
    def _generate_batch_report(self, results: Dict[str, Any]):
        """Generate batch report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_simulations': len(results),
            'successful': sum(1 for r in results.values() if r.get('status') == 'success'),
            'failed': sum(1 for r in results.values() if r.get('status') == 'failed'),
            'results': results
        }
        
        report_file = Path(
            f"data/reports/batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📊 Batch report generated: {report_file}")
    
    def get_result(self, sim_id: str) -> Optional[Dict[str, Any]]:
        """Get simulation result"""
        if sim_id in self.results:
            return self._json_safe(self.results[sim_id])
        return None
    
    def get_all_results(self) -> Dict[str, Any]:
        """Get all simulation results"""
        return {
            sim_id: result.__dict__ if hasattr(result, '__dict__') else result
            for sim_id, result in self.results.items()
        }
    
    def get_status(self, sim_id: str) -> Dict[str, Any]:
        """Get simulation status"""
        if sim_id in self.simulations:
            engine = self.simulations[sim_id]
            return {
                'id': sim_id,
                'status': engine.status.value,
                'current_round': engine.current_round,
                'max_rounds': engine.config.max_rounds,
                'is_active': engine.status.value in ['running', 'paused'],
                'config': engine.config.to_dict() if hasattr(engine.config, 'to_dict') else {}
            }
        return {'error': 'Simulation not found'}
    
    def delete_simulation(self, sim_id: str):
        """Delete simulation and its data"""
        if sim_id in self.simulations:
            if self.simulations[sim_id].status.value in ['running', 'paused']:
                self.stop_simulation(sim_id)
            del self.simulations[sim_id]
            
            if sim_id in self.results:
                del self.results[sim_id]
            
            # Remove cache file
            cache_file = Path(f"data/cache/{sim_id}.pkl")
            if cache_file.exists():
                cache_file.unlink()
            
            logger.info(f"🗑️ Deleted simulation: {sim_id}")