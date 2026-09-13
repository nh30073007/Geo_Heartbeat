# backend/app/simulation/engine.py
"""
Advanced Simulation Engine with:
- Async/await architecture
- Event-driven design
- State persistence
- Checkpoint system
- Error recovery
- Performance monitoring
- Type safety
- FIXED: RL learning with proper rewards
"""
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import json
import logging
from ..game_theory.reward_shaper import SemanticRewardShaper
import uuid
import random
import os
from enum import Enum
import numpy as np
from pathlib import Path

from ..environment.environment import StrategicEnvironment
from ..agents.hegemon_agent import HegemonAgent
from ..agents.sovereign_agent import SovereignAgent
from ..game_theory.payoff import AdaptivePayoffMatrix
from ..game_theory.equilibrium import EquilibriumAnalyzer

# Setup logging
logger = logging.getLogger(__name__)

class SimulationStatus(Enum):
    """Simulation status"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"

class SimulationMode(Enum):
    """Simulation modes"""
    INTERACTIVE = "interactive"  # Step by step
    BATCH = "batch"              # Run full simulation
    REALTIME = "realtime"        # Continuous with UI
    TRAINING = "training"        # For RL training

@dataclass
class SimulationConfig:
    """Configuration for simulation"""
    max_rounds: int = 500
    log_interval: int = 10
    save_interval: int = 50
    checkpoint_interval: int = 100
    auto_save: bool = True
    stochastic: bool = True
    mode: SimulationMode = SimulationMode.REALTIME
    seed: Optional[int] = None
    max_history: int = 10000
    error_tolerance: float = 0.1
    realtime_interval_seconds: float = 0.75
    
    # FIXED: Better RL hyperparameters
    use_q_learning: bool = True
    use_equilibrium: bool = True
    learning_rate: float = 0.15        # Higher for faster learning
    discount_factor: float = 0.95      # Future reward importance
    exploration_rate: float = 0.3      # More exploration
    epsilon_min: float = 0.1           # Keep exploring longer
    epsilon_decay: float = 0.9995      # MUCH slower decay
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'max_rounds': self.max_rounds,
            'log_interval': self.log_interval,
            'save_interval': self.save_interval,
            'checkpoint_interval': self.checkpoint_interval,
            'auto_save': self.auto_save,
            'stochastic': self.stochastic,
            'mode': self.mode.value,
            'seed': self.seed,
            'max_history': self.max_history,
            'error_tolerance': self.error_tolerance,
            'realtime_interval_seconds': self.realtime_interval_seconds,
            'use_q_learning': self.use_q_learning,
            'use_equilibrium': self.use_equilibrium,
            'learning_rate': self.learning_rate,
            'discount_factor': self.discount_factor,
            'exploration_rate': self.exploration_rate,
            'epsilon_min': self.epsilon_min,
            'epsilon_decay': self.epsilon_decay
        }

@dataclass
class SimulationState:
    """State of simulation at any point"""
    round: int
    timestamp: datetime
    status: SimulationStatus
    state_snapshot: Dict[str, float]
    hegemon_strategy: str
    sovereign_strategy: str
    hegemon_utility: float
    sovereign_utility: float
    events: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    checkpoint_id: Optional[str] = None

@dataclass
class SimulationResult:
    """Final simulation result"""
    rounds_completed: int
    total_duration: float
    final_state: Dict[str, float]
    hegemon_total_utility: float
    sovereign_total_utility: float
    equilibrium_analysis: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    events: List[Dict[str, Any]]
    status: SimulationStatus
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class SimulationEvent:
    """Simulation event system"""
    
    def __init__(self):
        self.handlers: Dict[str, List] = {}
        self.event_history: List[Dict[str, Any]] = []
        self.max_history = 10000
    
    def register_handler(self, event_type: str, handler):
        """Register event handler"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    async def emit(self, event_type: str, data: Dict[str, Any]):
        """Emit event to all handlers"""
        event = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'id': str(uuid.uuid4())
        }
        
        # Store event
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]
        
        # Call handlers
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")
    
    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get event history"""
        events = self.event_history
        if event_type:
            events = [e for e in events if e['type'] == event_type]
        return events[-limit:]

class SimulationEngine:
    """
    Main Simulation Engine with FIXED RL learning
    """
    
    def __init__(
        self,
        config: Optional[SimulationConfig] = None,
        environment: Optional[StrategicEnvironment] = None
    ):
        # Initialize configuration
        self.config = config or SimulationConfig()
        self.environment = environment or StrategicEnvironment(
            stochastic=self.config.stochastic
        )
        self.reward_shaper = SemanticRewardShaper()
        
        # Set random seed
        if self.config.seed:
            np.random.seed(self.config.seed)
            random.seed(self.config.seed)
        
        # Initialize agents
        self.hegemon = HegemonAgent()
        self.sovereign = SovereignAgent()

        # FIXED: Apply better RL hyperparameters to agents
        for agent in (self.hegemon, self.sovereign):
            agent.learning_rate = float(self.config.learning_rate)
            agent.gamma = float(self.config.discount_factor)
            agent.exploration_rate = float(self.config.exploration_rate)
            agent.epsilon_min = float(self.config.epsilon_min)
            agent.epsilon_decay = float(self.config.epsilon_decay)
            
            logger.info(
                f"📊 {agent.agent_id} RL params: "
                f"α={agent.learning_rate:.3f}, γ={agent.gamma:.3f}, "
                f"ε={agent.exploration_rate:.3f}, decay={agent.epsilon_decay:.4f}"
            )
        
        # Initialize game theory components
        self.payoff_matrix = AdaptivePayoffMatrix()
        self.equilibrium_analyzer = EquilibriumAnalyzer(self.payoff_matrix)
        
        # Set payoff matrices for agents
        self.hegemon.set_payoff_matrix(self.payoff_matrix)
        self.sovereign.set_payoff_matrix(self.payoff_matrix)
        
        # Initialize state
        self.current_round: int = 0
        self.status: SimulationStatus = SimulationStatus.IDLE
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.pause_time: Optional[datetime] = None
        self.total_pause_duration: timedelta = timedelta(0)
        
        # Event system
        self.events = SimulationEvent()
        
        # History and checkpoints
        self.state_history: List[SimulationState] = []
        self.checkpoints: Dict[str, SimulationState] = {}
        self.current_checkpoint_id: Optional[str] = None
        
        # Performance monitoring
        self.performance_metrics: Dict[str, Any] = {
            'round_times': [],
            'average_round_time': 0.0,
            'max_round_time': 0.0,
            'total_rounds': 0,
            'successful_rounds': 0,
            'failed_rounds': 0,
            'errors': [],
            'warnings': [],
            # FIXED: Add RL tracking
            'q_table_growth': {
                'hegemon': [],
                'sovereign': []
            },
            'epsilon_history': {
                'hegemon': [],
                'sovereign': []
            },
            'reward_history': {
                'hegemon': [],
                'sovereign': []
            }
        }
        
        # Control flags
        self._stop_requested: bool = False
        self._pause_requested: bool = False
        self._is_paused: bool = False
        self._lock = asyncio.Lock()
        
        # Setup directories
        self._setup_directories()
        
        logger.info("🚀 Simulation Engine initialized with FIXED RL parameters")
    
    def _setup_directories(self):
        """Setup required directories"""
        directories = [
            Path("data/simulations"),
            Path("data/checkpoints"),
            Path("data/logs"),
            Path("data/backups")
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def run(self) -> SimulationResult:
        """
        Main simulation loop
        """
        try:
            self.status = SimulationStatus.INITIALIZING
            await self._emit_event('simulation_started', {
                'config': self.config.to_dict()
            })
            
            self.start_time = datetime.now()
            self.status = SimulationStatus.RUNNING
            
            logger.info(f"▶️ Starting simulation, mode: {self.config.mode.value}, max_rounds: {self.config.max_rounds}")
            
            # Main loop
            while self.current_round < self.config.max_rounds:
                # Check stop/pause
                if self._stop_requested:
                    logger.info(f"⏹️ Stop requested at round {self.current_round}")
                    break
                
                if self._pause_requested:
                    await self._handle_pause()
                
                # Run a single round
                round_start = datetime.now()
                
                try:
                    # FIXED: Run the round with proper RL
                    await self._run_round()
                    
                    # Update performance
                    round_time = (datetime.now() - round_start).total_seconds()
                    self.performance_metrics['round_times'].append(round_time)
                    self.performance_metrics['average_round_time'] = np.mean(
                        self.performance_metrics['round_times'][-100:]
                    ) if self.performance_metrics['round_times'] else 0.0
                    self.performance_metrics['max_round_time'] = max(
                        self.performance_metrics['max_round_time'],
                        round_time
                    )
                    self.performance_metrics['successful_rounds'] += 1
                    
                except Exception as e:
                    logger.error(f"❌ Round {self.current_round} failed: {e}")
                    self.performance_metrics['errors'].append({
                        'round': self.current_round,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                    self.performance_metrics['failed_rounds'] += 1
                    
                    # Try recovery
                    if not await self._handle_error(e):
                        self.status = SimulationStatus.FAILED
                        break

                # Realtime mode: yield control to let dashboard update
                if self.config.mode == SimulationMode.REALTIME:
                    await asyncio.sleep(max(0.05, self.config.realtime_interval_seconds))
            
            # Simulation completed
            self.end_time = datetime.now()
            total_duration = (self.end_time - self.start_time).total_seconds()
            
            if self.status != SimulationStatus.FAILED:
                self.status = (
                    SimulationStatus.STOPPED
                    if self._stop_requested or self.current_round < self.config.max_rounds
                    else SimulationStatus.COMPLETED
                )
            
            # Generate final result
            result = await self._generate_result(total_duration)
            
            await self._emit_event('simulation_completed', {
                'result': self._json_safe(result.__dict__)
            })
            
            logger.info(f"✅ Simulation completed: {self.current_round} rounds in {total_duration:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            self.status = SimulationStatus.FAILED
            raise
        finally:
            self._stop_requested = False
            self._pause_requested = False
    
    # ======================================================================
    # FIXED: _run_round - The most critical method for RL
    # ======================================================================
    async def _run_round(self):
        """
        FIXED: Execute a single simulation round with proper RL learning
        
        This method now:
        1. Uses Q-learning for strategy selection
        2. Receives proper rewards from environment (with negative values)
        3. Updates Q-table with correct Bellman equation
        4. Tracks learning metrics for dashboard
        """
        try:
            # Get current state from environment
            current_state = self.environment.get_state()
            
            # Get state buckets BEFORE action (for Q-learning update)
            prev_h_bucket = self.hegemon.discretize_state(current_state)
            prev_s_bucket = self.sovereign.discretize_state(current_state)

            # FIXED: Select strategies using Q-learning
            if self.config.use_q_learning:
                hegemon_strategy = self.hegemon.select_strategy(
                    current_state,
                    context={'learning': True, 'round': self.current_round + 1},
                )
                sovereign_strategy = self.sovereign.select_strategy(
                    current_state,
                    context={'learning': True, 'round': self.current_round + 1},
                )
                
                # Log strategy selection with epsilon
                logger.info(
                    "🧠 RL strategies: Hegemon=%s (ε=%.3f), Sovereign=%s (ε=%.3f)",
                    hegemon_strategy, self.hegemon.exploration_rate,
                    sovereign_strategy, self.sovereign.exploration_rate,
                )
            else:
                # Heuristic mode (no learning)
                hegemon_strategy = self.hegemon.select_strategy(current_state)
                sovereign_strategy = self.sovereign.select_strategy(current_state)
                logger.info("🎯 Heuristic strategy mode (Q-learning disabled)")
            
            # Store current strategies
            self.hegemon.current_strategy = hegemon_strategy
            self.sovereign.current_strategy = sovereign_strategy
            
            # FIXED: Execute strategies in environment - gets proper rewards
            try:
                new_state, rewards = await self.environment.step(
                    hegemon_strategy,
                    sovereign_strategy
                )
                logger.info(f"📊 New state: Eco={new_state.get('economic_stability', 0):.1f}, Tension={new_state.get('strategic_tension', 0):.1f}")
            except Exception as e:
                logger.error(f"❌ environment.step failed: {e}")
                new_state = current_state
                rewards = {'hegemon': 0.0, 'sovereign': 0.0}
                logger.info(f"⚠️ Using current state as fallback")
            
            # Bound and optionally shape rewards with public sentiment.
            hegemon_reward = await self.reward_shaper.shape(
                float(rewards.get('hegemon', 0.0)), new_state
            )
            sovereign_reward = await self.reward_shaper.shape(
                float(rewards.get('sovereign', 0.0)), new_state
            )
            rewards['hegemon'] = hegemon_reward
            rewards['sovereign'] = sovereign_reward
            
            logger.info(f"💰 Rewards: H={hegemon_reward:.3f}, S={sovereign_reward:.3f}")
            
            # Get state buckets AFTER action (for Q-learning update)
            next_h_bucket = self.hegemon.discretize_state(new_state)
            next_s_bucket = self.sovereign.discretize_state(new_state)
            
            # FIXED: Q-learning update with proper rewards
            if self.config.use_q_learning:
                h_q_update = self.hegemon.q_learn(
                    prev_h_bucket, hegemon_strategy,
                    hegemon_reward, next_h_bucket,
                )
                s_q_update = self.sovereign.q_learn(
                    prev_s_bucket, sovereign_strategy,
                    sovereign_reward, next_s_bucket,
                )
                logger.info("🧠 Q update: H=%+.4f S=%+.4f", h_q_update, s_q_update)
            
            # Record outcomes for history
            self.hegemon.record_outcome(hegemon_strategy, hegemon_reward, new_state)
            self.sovereign.record_outcome(sovereign_strategy, sovereign_reward, new_state)
            
            # Update heuristic statistics
            self.hegemon.update_from_history()
            self.sovereign.update_from_history()
            
            # FIXED: Track RL metrics
            self.performance_metrics['q_table_growth']['hegemon'].append(len(self.hegemon.q_table))
            self.performance_metrics['q_table_growth']['sovereign'].append(len(self.sovereign.q_table))
            self.performance_metrics['epsilon_history']['hegemon'].append(self.hegemon.exploration_rate)
            self.performance_metrics['epsilon_history']['sovereign'].append(self.sovereign.exploration_rate)
            self.performance_metrics['reward_history']['hegemon'].append(hegemon_reward)
            self.performance_metrics['reward_history']['sovereign'].append(sovereign_reward)
            
            # Increment the engine round
            self.current_round += 1
            self.performance_metrics['total_rounds'] = self.current_round
            
            # Create state snapshot with enhanced metrics
            state_snapshot = SimulationState(
                round=self.current_round,
                timestamp=datetime.now(),
                status=self.status,
                state_snapshot=self.environment.get_state(),
                hegemon_strategy=hegemon_strategy,
                sovereign_strategy=sovereign_strategy,
                hegemon_utility=hegemon_reward,
                sovereign_utility=sovereign_reward,
                events=[],
                performance_metrics={
                    'hegemon_total_utility': self.hegemon.total_utility,
                    'sovereign_total_utility': self.sovereign.total_utility,
                    'hegemon_epsilon': self.hegemon.exploration_rate,
                    'sovereign_epsilon': self.sovereign.exploration_rate,
                    'hegemon_q_table_size': len(self.hegemon.q_table),
                    'sovereign_q_table_size': len(self.sovereign.q_table),
                    'hegemon_reward': hegemon_reward,
                    'sovereign_reward': sovereign_reward
                }
            )
            
            # Add to history
            self.state_history.append(state_snapshot)
            if len(self.state_history) > self.config.max_history:
                self.state_history = self.state_history[-self.config.max_history:]
            
            # FIXED: Emit enhanced event with RL metrics
            await self._emit_event('round_completed', {
                'round': self.current_round,
                'hegemon_strategy': hegemon_strategy,
                'sovereign_strategy': sovereign_strategy,
                'hegemon_reward': hegemon_reward,
                'sovereign_reward': sovereign_reward,
                'state': new_state,
                'epsilon': {
                    'hegemon': self.hegemon.exploration_rate,
                    'sovereign': self.sovereign.exploration_rate
                },
                'q_table_sizes': {
                    'hegemon': len(self.hegemon.q_table),
                    'sovereign': len(self.sovereign.q_table)
                },
                'q_updates': {
                    'hegemon': h_q_update if self.config.use_q_learning else 0.0,
                    'sovereign': s_q_update if self.config.use_q_learning else 0.0
                }
            })
            
            # FIXED: Log progress with RL metrics every 10 rounds
            if self.current_round % 10 == 0:
                logger.info(
                    f"✅ Round {self.current_round}/{self.config.max_rounds} | "
                    f"H-Q: {len(self.hegemon.q_table)}, "
                    f"S-Q: {len(self.sovereign.q_table)}, "
                    f"H-ε: {self.hegemon.exploration_rate:.3f}, "
                    f"S-ε: {self.sovereign.exploration_rate:.3f}, "
                    f"H-R: {hegemon_reward:+.3f}, "
                    f"S-R: {sovereign_reward:+.3f}"
                )
                
        except Exception as e:
            logger.error(f"❌ Round execution failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def _check_termination(self) -> bool:
        """
        Check if simulation should terminate early
        """
        state = self.environment.get_state()
        
        # Check for critical thresholds
        if state.get('strategic_tension', 0) > 90:
            await self._emit_event('termination_triggered', {
                'reason': 'strategic_tension_too_high',
                'value': state['strategic_tension']
            })
            return True
        
        if state.get('economic_stability', 0) < 10:
            await self._emit_event('termination_triggered', {
                'reason': 'economic_collapse',
                'value': state['economic_stability']
            })
            return True
        
        # Check for convergence
        if len(self.state_history) > 20:
            recent = self.state_history[-20:]
            stability_values = [s.state_snapshot.get('economic_stability', 0) for s in recent]
            
            if len(stability_values) == 20:
                variance = np.var(stability_values)
                if variance < 0.1:
                    await self._emit_event('termination_triggered', {
                        'reason': 'convergence_achieved',
                        'variance': variance
                    })
                    return True
        
        return False
    
    async def _handle_error(self, error: Exception) -> bool:
        """
        Handle simulation errors
        Returns: True if can continue, False if should stop
        """
        error_str = str(error)
        
        if 'timeout' in error_str.lower():
            logger.warning("Timeout occurred, continuing...")
            return True
        
        if 'memory' in error_str.lower():
            self.state_history = self.state_history[-1000:]
            logger.warning("Memory issue - trimmed history")
            return True
        
        if self.current_checkpoint_id:
            try:
                await self._restore_checkpoint(self.current_checkpoint_id)
                logger.info(f"Recovered from checkpoint {self.current_checkpoint_id}")
                return True
            except Exception as e:
                logger.error(f"Checkpoint recovery failed: {e}")
                return False
        
        return False
    
    async def _handle_pause(self):
        """Handle pause/resume"""
        if not self._is_paused:
            self._is_paused = True
            self.pause_time = datetime.now()
            self.status = SimulationStatus.PAUSED
            await self._emit_event('simulation_paused', {
                'round': self.current_round
            })
            
            while self._pause_requested and not self._stop_requested:
                await asyncio.sleep(0.1)
            
            if self.pause_time:
                self.total_pause_duration += datetime.now() - self.pause_time
                self.pause_time = None
            
            self._is_paused = False
            self.status = SimulationStatus.RUNNING
            await self._emit_event('simulation_resumed', {
                'round': self.current_round
            })
    
    async def _create_checkpoint(self):
        """Create a checkpoint"""
        checkpoint_id = f"checkpoint_{self.current_round}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        checkpoint_data = {
            'id': checkpoint_id,
            'round': self.current_round,
            'state': self.environment.get_state(),
            'hegemon_history': self.hegemon.history[-100:] if hasattr(self.hegemon, 'history') else [],
            'sovereign_history': self.sovereign.history[-100:] if hasattr(self.sovereign, 'history') else [],
            'hegemon_total_utility': self.hegemon.total_utility,
            'sovereign_total_utility': self.sovereign.total_utility,
            'hegemon_q_table': dict(self.hegemon.q_table) if hasattr(self.hegemon, 'q_table') else {},
            'sovereign_q_table': dict(self.sovereign.q_table) if hasattr(self.sovereign, 'q_table') else {},
            'hegemon_epsilon': self.hegemon.exploration_rate,
            'sovereign_epsilon': self.sovereign.exploration_rate,
            'timestamp': datetime.now().isoformat()
        }
        
        checkpoint_file = Path(f"data/checkpoints/{checkpoint_id}.json")
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2, default=str)
        
        self.current_checkpoint_id = checkpoint_id
        
        await self._emit_event('checkpoint_created', {
            'checkpoint_id': checkpoint_id,
            'round': self.current_round
        })
        
        logger.info(f"💾 Checkpoint {checkpoint_id} created")
    
    async def _restore_checkpoint(self, checkpoint_id: str):
        """
        Restore from checkpoint
        """
        checkpoint_file = Path(f"data/checkpoints/{checkpoint_id}.json")
        
        if not checkpoint_file.exists():
            raise FileNotFoundError(f"Checkpoint {checkpoint_id} not found")
        
        with open(checkpoint_file, 'r') as f:
            checkpoint_data = json.load(f)
        
        self.environment.state.update(checkpoint_data['state'])
        self.current_round = checkpoint_data['round']
        
        # Restore Q-tables if available
        if 'hegemon_q_table' in checkpoint_data:
            for key, value in checkpoint_data['hegemon_q_table'].items():
                # Convert string key back to tuple if needed
                if isinstance(key, str):
                    # Parse state|action format
                    parts = key.split('|')
                    if len(parts) == 2:
                        self.hegemon.q_table[(parts[0], parts[1])] = value
                else:
                    self.hegemon.q_table[key] = value
        
        if 'sovereign_q_table' in checkpoint_data:
            for key, value in checkpoint_data['sovereign_q_table'].items():
                if isinstance(key, str):
                    parts = key.split('|')
                    if len(parts) == 2:
                        self.sovereign.q_table[(parts[0], parts[1])] = value
                else:
                    self.sovereign.q_table[key] = value
        
        # Restore epsilon
        if 'hegemon_epsilon' in checkpoint_data:
            self.hegemon.exploration_rate = checkpoint_data['hegemon_epsilon']
        if 'sovereign_epsilon' in checkpoint_data:
            self.sovereign.exploration_rate = checkpoint_data['sovereign_epsilon']
        
        await self._emit_event('checkpoint_restored', {
            'checkpoint_id': checkpoint_id,
            'round': self.current_round
        })
        
        logger.info(f"🔄 Restored from checkpoint {checkpoint_id}")
    
    async def _auto_save(self):
        """Auto-save simulation state"""
        save_data = {
            'config': self.config.to_dict(),
            'current_round': self.current_round,
            'state': self.environment.get_state(),
            'hegemon': {
                'total_utility': self.hegemon.total_utility,
                'history': self.hegemon.history[-500:] if hasattr(self.hegemon, 'history') else [],
                'q_table': dict(self.hegemon.q_table) if hasattr(self.hegemon, 'q_table') else {},
                'epsilon': self.hegemon.exploration_rate
            },
            'sovereign': {
                'total_utility': self.sovereign.total_utility,
                'history': self.sovereign.history[-500:] if hasattr(self.sovereign, 'history') else [],
                'q_table': dict(self.sovereign.q_table) if hasattr(self.sovereign, 'q_table') else {},
                'epsilon': self.sovereign.exploration_rate
            },
            'events': self.events.get_history(limit=100),
            'performance': self.performance_metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        save_file = Path(
            f"data/simulations/simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        with open(save_file, 'w') as f:
            json.dump(save_data, f, indent=2, default=str)
        
        await self._emit_event('auto_save_created', {
            'file': str(save_file),
            'round': self.current_round
        })
    
    async def _log_progress(self):
        """Log simulation progress"""
        state = self.environment.get_state()
        
        logger.info(
            f"📊 Round {self.current_round}/{self.config.max_rounds} | "
            f"Eco: {state.get('economic_stability', 0):.1f} | "
            f"Tech: {state.get('technology_independence', 0):.1f} | "
            f"Trade: {state.get('trade_stability', 0):.1f} | "
            f"Sentiment: {state.get('public_sentiment', 0):.3f} | "
            f"Tension: {state.get('strategic_tension', 0):.1f} | "
            f"H: {self.hegemon.total_utility:.2f} | "
            f"S: {self.sovereign.total_utility:.2f} | "
            f"H-Q: {len(self.hegemon.q_table)} | "
            f"S-Q: {len(self.sovereign.q_table)}"
        )
    
    async def _generate_result(self, total_duration: float) -> SimulationResult:
        """
        Generate final simulation result
        """
        final_state = self.environment.get_state()
        
        return SimulationResult(
            rounds_completed=self.current_round,
            total_duration=total_duration,
            final_state=final_state,
            hegemon_total_utility=self.hegemon.total_utility,
            sovereign_total_utility=self.sovereign.total_utility,
            equilibrium_analysis=self.equilibrium_analyzer.analyze_all(final_state),
            performance_metrics=self.performance_metrics,
            events=self.events.get_history(limit=1000),
            status=self.status,
            errors=self.performance_metrics['errors'],
            warnings=self.performance_metrics['warnings']
        )
    
    def _json_safe(self, value: Any):
        """Convert non-JSON-serializable objects to JSON-safe format"""
        from enum import Enum
        from dataclasses import asdict, is_dataclass
        if isinstance(value, Enum):
            return value.value
        if is_dataclass(value):
            return self._json_safe(asdict(value))
        if isinstance(value, dict):
            return {str(self._json_safe(k)): self._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._json_safe(v) for v in value]
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, timedelta):
            return value.total_seconds()
        return value

    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit simulation event"""
        await self.events.emit(event_type, data)
    
    # ======================================================================
    # Control methods
    # ======================================================================
    
    def stop(self):
        """Stop simulation"""
        self._stop_requested = True
        logger.info("⏹️ Stop requested")
    
    def pause(self):
        """Pause simulation"""
        if self.status == SimulationStatus.RUNNING:
            self._pause_requested = True
            logger.info("⏸️ Pause requested")
    
    def resume(self):
        """Resume simulation"""
        if self._is_paused:
            self._pause_requested = False
            logger.info("▶️ Resume requested")
    
    def get_global_state(self) -> Dict[str, float]:
        """Return global environment metrics."""
        return self.environment.get_global_state()

    def get_region_state(self, region_name: str) -> Optional[Dict[str, float]]:
        """Return a named regional state."""
        return self.environment.get_region_state(region_name)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Return engine metrics with environment-level trend data."""
        metrics = dict(self.performance_metrics)
        metrics["agent_performance"] = {
            "hegemon_utility": self.hegemon.total_utility,
            "sovereign_utility": self.sovereign.total_utility,
        }
        metrics["rl_metrics"] = {
            "hegemon_q_table_size": len(self.hegemon.q_table),
            "sovereign_q_table_size": len(self.sovereign.q_table),
            "hegemon_epsilon": self.hegemon.exploration_rate,
            "sovereign_epsilon": self.sovereign.exploration_rate,
            "hegemon_learning_rate": self.hegemon.learning_rate,
            "sovereign_learning_rate": self.sovereign.learning_rate,
        }
        return metrics

    def get_state(self) -> Dict[str, Any]:
        """Get current simulation state"""
        latest_state = self.environment.get_state()
        
        return {
            'status': self.status.value,
            'current_round': self.current_round,
            'max_rounds': self.config.max_rounds,
            'environment': latest_state,
            'hegemon_utility': self.hegemon.total_utility,
            'sovereign_utility': self.sovereign.total_utility,
            'hegemon_strategy': getattr(self.hegemon, 'current_strategy', None),
            'sovereign_strategy': getattr(self.sovereign, 'current_strategy', None),
            'hegemon_learning': self.hegemon.learning_snapshot() if hasattr(self.hegemon, 'learning_snapshot') else None,
            'sovereign_learning': self.sovereign.learning_snapshot() if hasattr(self.sovereign, 'learning_snapshot') else None,
            'performance': self.performance_metrics,
            'rl_metrics': {
                'hegemon_q_table_size': len(self.hegemon.q_table),
                'sovereign_q_table_size': len(self.sovereign.q_table),
                'hegemon_epsilon': self.hegemon.exploration_rate,
                'sovereign_epsilon': self.sovereign.exploration_rate,
            }
        }
    
    def get_history(
        self,
        start_round: Optional[int] = None,
        end_round: Optional[int] = None,
        limit: int = 100
    ) -> List[SimulationState]:
        """Get simulation history"""
        history = self.state_history
        
        if start_round is not None:
            history = [s for s in history if s.round >= start_round]
        
        if end_round is not None:
            history = [s for s in history if s.round <= end_round]
        
        return history[-limit:]
    
    def get_checkpoints(self) -> List[str]:
        """Get list of available checkpoints"""
        checkpoint_files = Path("data/checkpoints").glob("*.json")
        return [f.stem for f in checkpoint_files]
    
    async def load_checkpoint(self, checkpoint_id: str):
        """Load checkpoint by ID"""
        await self._restore_checkpoint(checkpoint_id)