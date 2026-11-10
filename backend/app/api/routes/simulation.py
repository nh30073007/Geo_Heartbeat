"""
Advanced Simulation Routes with:
- Full CRUD operations
- Validation
- Rate limiting
- Error handling
- Response caching
- Async support
- STEP 2A: country-aware simulation + real-data injection endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import asyncio
import uuid
import os
from pydantic import BaseModel, Field, validator

from ...simulation import (
    SimulationEngine,
    SimulationConfig,
    SimulationMode,
    SimulationStatus,
    SimulationRunner,
    ScenarioManager,
    Scenario
)
from ...realtime import EventType, EventCategory, EventPriority
from ...core.runtime import runtime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation", tags=["simulation"])

# Global instances
simulation_runner = runtime.simulation_runner
scenario_manager = runtime.scenario_manager
event_manager = runtime.event_manager


# ============================================================
# Request/Response Models
# ============================================================
class SimulationCreateRequest(BaseModel):
    """Request to create simulation"""
    config: Optional[Dict[str, Any]] = None
    scenario_id: Optional[str] = None
    mode: str = "realtime"
    max_rounds: int = Field(500, ge=1, le=10000)
    stochastic: bool = True
    seed: Optional[int] = None
    use_q_learning: bool = True
    use_equilibrium: bool = True
    exploration_rate: float = Field(0.2, ge=0.0, le=1.0)
    learning_rate: float = Field(0.1, gt=0.0, le=1.0)
    discount_factor: float = Field(0.95, ge=0.0, le=0.9999)
    epsilon_min: float = Field(0.05, ge=0.0, le=1.0)
    epsilon_decay: float = Field(0.997, gt=0.0, le=1.0)

    # STEP 2A: which country's real data to inject
    country_id: str = Field(
        default_factory=lambda: os.getenv("SIM_DEFAULT_COUNTRY", "bd"),
        description="Country id (bd, in, pk, ...) for real data injection",
    )

    @validator('mode')
    def validate_mode(cls, v):
        valid_modes = ['batch', 'interactive', 'realtime', 'training']
        if v not in valid_modes:
            raise ValueError(f'Mode must be one of: {valid_modes}')
        return v


class SimulationStartRequest(BaseModel):
    """Request to start simulation"""
    sim_id: str
    background: bool = True


class SimulationResponse(BaseModel):
    """Simulation response"""
    id: str
    status: str
    current_round: int
    max_rounds: int
    progress: float
    created_at: datetime
    updated_at: datetime
    config: Dict[str, Any]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SimulationListResponse(BaseModel):
    """List of simulations"""
    total: int
    simulations: List[SimulationResponse]


# ============================================================
# Scenarios
# ============================================================
@router.get("/scenarios")
async def list_scenarios(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    tag: Optional[str] = None
):
    """List all available scenarios with filters"""
    try:
        scenarios = scenario_manager.get_all_scenarios()

        if category:
            from ...simulation import ScenarioCategory
            scenarios = [s for s in scenarios if s.category.value == category]

        if difficulty:
            from ...simulation import ScenarioDifficulty
            scenarios = [s for s in scenarios if s.difficulty.value == difficulty]

        if tag:
            scenarios = [s for s in scenarios if tag in s.tags]

        return {
            'total': len(scenarios),
            'scenarios': [s.to_dict() for s in scenarios],
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to list scenarios: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Get scenario details"""
    try:
        scenario = scenario_manager.get_scenario(scenario_id)

        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")

        analysis = scenario_manager.get_scenario_analysis(scenario_id)

        return {
            'scenario': scenario.to_dict(),
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scenario: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# Create / Start / Stop / Pause / Resume
# ============================================================
@router.post("/create", response_model=Dict[str, Any])
async def create_simulation(request: SimulationCreateRequest):
    """
    Create a new simulation (STEP 2A: country-aware + real data).
    """
    try:
        config = SimulationConfig(
            max_rounds=request.max_rounds,
            stochastic=request.stochastic,
            seed=request.seed,
            mode=SimulationMode(request.mode),
            realtime_interval_seconds=float(
                (request.config or {}).get('realtime_interval_seconds', 0.75)
            ),
            country_id=request.country_id,   # STEP 2A
            use_q_learning=request.use_q_learning,
            use_equilibrium=request.use_equilibrium,
            learning_rate=request.learning_rate,
            discount_factor=request.discount_factor,
            exploration_rate=request.exploration_rate,
            epsilon_min=request.epsilon_min,
            epsilon_decay=request.epsilon_decay,
        )

        logger.info(
            f"📋 Creating simulation: mode={config.mode.value}, "
            f"max_rounds={config.max_rounds}, country={config.country_id}"
        )

        # Apply scenario if provided
        environment = None
        scenario_name = 'Custom Simulation'
        if request.scenario_id:
            scenario = scenario_manager.get_scenario(request.scenario_id)
            if scenario:
                from ...environment import StrategicEnvironment
                environment = StrategicEnvironment(
                    stochastic=request.stochastic,
                    country_id=request.country_id,   # STEP 2A
                )
                scenario_manager.apply_scenario_to_environment(
                    request.scenario_id,
                    environment
                )
                scenario_name = scenario.name

        sim_id = (
            f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_"
            f"{uuid.uuid4().hex[:6]}"
        )
        engine = simulation_runner.create_simulation(sim_id, config, environment)

        runtime.attach_simulation(sim_id)

        event = event_manager.create_event(
            event_type=EventType.SIMULATION_STARTED,
            category=EventCategory.SIMULATION,
            source='api',
            data={
                'sim_id': sim_id,
                'country_id': request.country_id,
                'config': request.dict(),
            },
            priority=EventPriority.NORMAL
        )
        event_manager.emit(event)

        return {
            'status': 'success',
            'sim_id': sim_id,
            'country_id': request.country_id,
            'config': config.to_dict(),
            'scenario': request.scenario_id,
            'scenario_name': scenario_name,
            'initial_state': engine.environment.get_state(),
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to create simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/start/{sim_id}", response_model=Dict[str, Any])
async def start_simulation(
    sim_id: str,
    background_tasks: BackgroundTasks,
    background: bool = True
):
    """Start a simulation"""
    try:
        if sim_id not in simulation_runner.simulations:
            raise HTTPException(status_code=404, detail="Simulation not found")

        runtime.attach_simulation(sim_id)

        engine = simulation_runner.simulations[sim_id]
        logger.info(
            f"▶️ Starting simulation {sim_id}: "
            f"mode={engine.config.mode.value}, "
            f"country={engine.config.country_id}"
        )

        if background:
            background_tasks.add_task(simulation_runner.run_simulation, sim_id)
            return {
                'status': 'started',
                'sim_id': sim_id,
                'mode': 'background',
                'timestamp': datetime.now().isoformat()
            }
        else:
            result = await simulation_runner.run_simulation(sim_id)
            return {
                'status': 'completed',
                'sim_id': sim_id,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Failed to start simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop/{sim_id}")
async def stop_simulation(sim_id: str):
    """Stop a running simulation"""
    try:
        simulation_runner.stop_simulation(sim_id)

        event = event_manager.create_event(
            event_type=EventType.SIMULATION_STOPPED,
            category=EventCategory.SIMULATION,
            source='api',
            data={'sim_id': sim_id},
            priority=EventPriority.NORMAL
        )
        event_manager.emit(event)

        return {
            'status': 'stopped',
            'sim_id': sim_id,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to stop simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pause/{sim_id}")
async def pause_simulation(sim_id: str):
    """Pause a simulation"""
    try:
        simulation_runner.pause_simulation(sim_id)

        event = event_manager.create_event(
            event_type=EventType.SIMULATION_PAUSED,
            category=EventCategory.SIMULATION,
            source='api',
            data={'sim_id': sim_id},
            priority=EventPriority.NORMAL
        )
        event_manager.emit(event)

        return {
            'status': 'paused',
            'sim_id': sim_id,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to pause simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resume/{sim_id}")
async def resume_simulation(sim_id: str):
    """Resume a paused simulation"""
    try:
        simulation_runner.resume_simulation(sim_id)

        event = event_manager.create_event(
            event_type=EventType.SIMULATION_RESUMED,
            category=EventCategory.SIMULATION,
            source='api',
            data={'sim_id': sim_id},
            priority=EventPriority.NORMAL
        )
        event_manager.emit(event)

        return {
            'status': 'resumed',
            'sim_id': sim_id,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to resume simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/step/{sim_id}")
async def step_simulation(sim_id: str):
    try:
        result = await simulation_runner.step_simulation(sim_id)
        await runtime.broadcast_api_event(
            sim_id, 'manual_step',
            {'round': result.get('current_round', 0), 'status': result.get('status')}
        )
        return {
            'status': 'success',
            'sim_id': sim_id,
            'state': result,
            'timestamp': datetime.now().isoformat()
        }
    except ValueError as e:
        raise HTTPException(
            status_code=409 if 'Pause' in str(e) else 404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to step simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset/{sim_id}")
async def reset_simulation(sim_id: str):
    try:
        state = simulation_runner.reset_simulation(sim_id)
        await runtime.broadcast_api_event(sim_id, 'simulation_reset', {'round': 0})
        return {
            'status': 'reset',
            'sim_id': sim_id,
            'state': state,
            'timestamp': datetime.now().isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to reset simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/checkpoint/{sim_id}")
async def create_checkpoint(sim_id: str):
    try:
        if sim_id not in simulation_runner.simulations:
            raise HTTPException(status_code=404, detail='Simulation not found')
        engine = simulation_runner.simulations[sim_id]
        await engine._create_checkpoint()
        return {
            'status': 'checkpoint_created',
            'sim_id': sim_id,
            'checkpoint_id': engine.current_checkpoint_id,
            'round': engine.current_round,
            'timestamp': datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create checkpoint: {e}")
        raise HTTPException(status_code=400, detail=str(e))


class SimulationActionRequest(BaseModel):
    action: str


@router.post("/action/{sim_id}")
async def execute_action(sim_id: str, request: SimulationActionRequest):
    try:
        if sim_id not in simulation_runner.simulations:
            raise HTTPException(status_code=404, detail='Simulation not found')
        engine = simulation_runner.simulations[sim_id]
        action = request.action.strip().lower()
        effects = {
            'create crisis': {
                'strategic_tension': 4.0, 'trade_stability': -1.5,
                'public_sentiment': -0.03,
            },
            'diplomatic meeting': {
                'strategic_tension': -2.0, 'trade_stability': 1.2,
                'public_sentiment': 0.02,
            },
            'economic sanction': {
                'economic_stability': -2.0, 'trade_stability': -2.5,
                'strategic_tension': 2.5,
            },
            'peace negotiation': {
                'strategic_tension': -4.0, 'economic_stability': 1.0,
                'public_sentiment': 0.04,
            },
            'deploy peacekeeping': {
                'strategic_tension': -2.5, 'supply_chain_stability': 0.8,
                'economic_stability': -0.5,
            },
        }
        if action not in effects:
            raise HTTPException(status_code=400, detail=f'Unknown action: {request.action}')
        patch = effects[action]
        current = engine.environment.get_global_state()
        next_state = dict(current)
        for key, delta in patch.items():
            value = next_state.get(key, 0) + delta
            next_state[key] = (
                max(-1.0, min(1.0, value))
                if key == 'public_sentiment'
                else max(0.0, min(100.0, value))
            )
        for key, value in next_state.items():
            if hasattr(engine.environment.state, key):
                setattr(engine.environment.state, key, value)
        engine.environment.state._calculate_derived_metrics()
        engine.environment.state.timestamp = datetime.now()
        await runtime.broadcast_api_event(
            sim_id, 'user_action',
            {'action': request.action, 'effects': patch, 'round': engine.current_round}
        )
        return {
            'status': 'applied',
            'sim_id': sim_id,
            'action': request.action,
            'effects': patch,
            'state': engine.get_state(),
            'timestamp': datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute action: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# List / Status / Result
# ============================================================
@router.get("/list", response_model=SimulationListResponse)
async def list_simulations(
    status: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List all simulations with optional filtering"""
    try:
        sim_ids = list(simulation_runner.simulations.keys())
        sim_ids = sim_ids[offset:offset + limit]

        simulations = []
        for sim_id in sim_ids:
            status_info = simulation_runner.get_status(sim_id)
            if status and status_info.get('status') != status:
                continue

            simulations.append(SimulationResponse(
                id=sim_id,
                status=status_info.get('status', 'unknown'),
                current_round=status_info.get('current_round', 0),
                max_rounds=status_info.get('max_rounds', 0),
                progress=(
                    status_info.get('current_round', 0)
                    / max(1, status_info.get('max_rounds', 1))
                ),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                config=status_info.get('config', {})
            ))

        return SimulationListResponse(
            total=len(simulation_runner.simulations),
            simulations=simulations
        )

    except Exception as e:
        logger.error(f"Failed to list simulations: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# STEP 2A: Global (no sim_id) status — latest active simulation
# ============================================================
@router.get("/status")
async def get_global_status():
    """
    Global simulation status (no sim_id required).

    Returns the most recently created simulation's status + real-data info.
    If no simulation is running, returns a compact idle snapshot.
    """
    try:
        sims = simulation_runner.simulations
        if not sims:
            return {
                'status': 'idle',
                'sim_id': None,
                'country_id': os.getenv("SIM_DEFAULT_COUNTRY", "bd"),
                'current_round': 0,
                'max_rounds': 0,
                'real_data': None,
                'timestamp': datetime.now().isoformat(),
            }

        # Latest by insertion order (dict is ordered in Py3.7+)
        sim_id = list(sims.keys())[-1]
        engine = sims[sim_id]
        status_info = simulation_runner.get_status(sim_id)

        real_data = None
        try:
            env_metrics = engine.environment.get_performance_metrics()
            real_data = env_metrics.get('real_data', None)
        except Exception:
            real_data = None

        return {
            'status': status_info.get('status', 'unknown'),
            'sim_id': sim_id,
            'country_id': getattr(engine.config, 'country_id', None),
            'current_round': status_info.get('current_round', 0),
            'max_rounds': status_info.get('max_rounds', 0),
            'config': status_info.get('config', {}),
            'real_data': real_data,
            'rl_metrics': {
                'hegemon_q_table_size': len(engine.hegemon.q_table),
                'sovereign_q_table_size': len(engine.sovereign.q_table),
                'hegemon_epsilon': engine.hegemon.exploration_rate,
                'sovereign_epsilon': engine.sovereign.exploration_rate,
            },
            'timestamp': datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get global status: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# STEP 2A: Real data injection endpoint
# ============================================================
@router.get("/real-data/{sim_id}")
async def get_real_data_injection(sim_id: str):
    """
    Get real-world data injection log for a simulation.

    Returns latest news sentiment, economic indicators, and the last
    few injection events.
    """
    try:
        if sim_id not in simulation_runner.simulations:
            raise HTTPException(status_code=404, detail='Simulation not found')

        engine = simulation_runner.simulations[sim_id]
        env_metrics = engine.environment.get_performance_metrics()

        return {
            'sim_id': sim_id,
            'country_id': getattr(engine.config, 'country_id', None),
            'real_data': env_metrics.get('real_data', {}),
            'timestamp': datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get real data: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{sim_id}")
async def get_simulation_status(sim_id: str):
    """Get simulation status"""
    try:
        status = simulation_runner.get_status(sim_id)

        if 'error' in status:
            raise HTTPException(status_code=404, detail=status['error'])

        return {
            'sim_id': sim_id,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get simulation status: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/result/{sim_id}")
async def get_simulation_result(sim_id: str):
    """Get simulation result"""
    try:
        result = simulation_runner.get_result(sim_id)

        if not result:
            raise HTTPException(status_code=404, detail="Result not found")

        return {
            'sim_id': sim_id,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get simulation result: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{sim_id}")
async def delete_simulation(sim_id: str):
    """Delete a simulation"""
    try:
        simulation_runner.delete_simulation(sim_id)

        return {
            'status': 'deleted',
            'sim_id': sim_id,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to delete simulation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# Batch
# ============================================================
@router.post("/batch")
async def run_batch_simulations(
    configs: List[Dict[str, Any]],
    parallel: int = Query(2, ge=1, le=10)
):
    """Run multiple simulations in batch"""
    try:
        results = await simulation_runner.run_batch(configs, parallel)

        return {
            'status': 'completed',
            'total': len(results),
            'results': results,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Batch simulation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))