# backend/app/agents/base_agent.py
"""
Secure Base Agent with:
- Authentication
- Rate Limiting
- Audit Logging
- Input Validation
- Encryption
- FIXED: RL Learning Support with better hyperparameters
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import logging
import asyncio
import random
from collections import defaultdict
import jwt
from cryptography.fernet import Fernet
from pydantic import BaseModel, ValidationError, validator
import numpy as np
import os

# Setup logging
logger = logging.getLogger(__name__)

# Security Constants
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
ALGORITHM = "HS256"
ENCRYPTION_KEY = Fernet.generate_key()
cipher = Fernet(ENCRYPTION_KEY)

class Strategy(BaseModel):
    """Strategy model with validation"""
    id: str
    name: str
    description: str
    risk_level: float = 0.5
    implementation_cost: float = 0.5
    expected_duration: int = 30
    
    @validator('risk_level')
    def validate_risk(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Risk level must be between 0 and 1')
        return v
    
    @validator('implementation_cost')
    def validate_cost(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Cost must be between 0 and 1')
        return v

class AgentAction(BaseModel):
    """Agent action with validation"""
    strategy_id: str
    context: Dict[str, Any]
    timestamp: datetime = datetime.now()
    confidence: float = 0.0
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Confidence must be between 0 and 1')
        return v

@dataclass
class AuditLog:
    """Audit log entry"""
    timestamp: datetime
    agent_id: str
    action: str
    strategy: str
    state_snapshot: Dict[str, float]
    utility: float
    ip_address: Optional[str] = None
    session_id: Optional[str] = None

class RateLimiter:
    """Rate limiting for agent actions"""
    
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
    
    def is_allowed(self, agent_id: str) -> bool:
        """Check if agent can make request"""
        now = datetime.now()
        self.requests[agent_id] = [
            req for req in self.requests[agent_id]
            if (now - req).seconds < self.time_window
        ]
        
        if len(self.requests[agent_id]) >= self.max_requests:
            return False
        
        self.requests[agent_id].append(now)
        return True
    
    def get_remaining(self, agent_id: str) -> int:
        """Get remaining requests"""
        now = datetime.now()
        self.requests[agent_id] = [
            req for req in self.requests[agent_id]
            if (now - req).seconds < self.time_window
        ]
        return self.max_requests - len(self.requests[agent_id])

class SecureAgent(ABC):
    """
    Abstract Secure Agent with FIXED RL parameters
    """
    
    def __init__(
        self,
        agent_id: str,
        secret_key: str = SECRET_KEY,
        max_requests: int = 100,
        time_window: int = 60
    ):
        self.agent_id = agent_id
        self.secret_key = secret_key
        self.rate_limiter = RateLimiter(max_requests, time_window)
        self.strategies: List[Strategy] = []
        self.strategy_objects: List[Strategy] = []
        self.history: List[Dict[str, Any]] = []
        self.strategy_history: Dict[str, List[float]] = defaultdict(list)
        self.audit_logs: List[AuditLog] = []
        self.total_utility: float = 0
        self.session_token: Optional[str] = None
        self.encryption_key = ENCRYPTION_KEY

        # --- FIXED: Reinforcement learning (tabular Q-learning) ---
        self.q_table: Dict[Tuple[str, str], float] = {}
        
        # FIXED: Better hyperparameters for stable learning
        self.gamma: float = 0.95          # Discount factor (higher = future matters more)
        self.learning_rate: float = 0.15  # Learning rate (faster learning)
        self.exploration_rate: float = 0.3  # Start with more exploration
        self.epsilon_min: float = 0.1     # Keep exploring longer
        self.epsilon_decay: float = 0.9995  # MUCH SLOWER decay
        self.reward_history: List[float] = []

        # Optional neural RL backend; tabular Q-learning remains the safe default.
        self.rl_backend = os.getenv("RL_BACKEND", "q_learning").strip().lower()
        self.dqn = None
        self._dqn_keys = [
            "economic_stability", "strategic_tension", "technology_independence",
            "trade_stability", "economic_resilience", "currency_stability",
            "ai_capability", "public_sentiment"
        ]
        if self.rl_backend == "dqn":
            try:
                from .dqn import DQNPolicy
                self.dqn = DQNPolicy(len(self._dqn_keys), 4)
            except Exception as exc:
                logger.warning("DQN unavailable; falling back to Q-learning: %s", exc)
                self.rl_backend = "q_learning"
        
        # Secure storage
        self._secure_storage: Dict[str, Any] = {}
        
        # Performance tracking
        self.performance: Dict[str, Any] = {
            'total_actions': 0,
            'successful_actions': 0,
            'failed_actions': 0,
            'avg_response_time': 0.0,
            'strategy_usage': defaultdict(int)
        }
        
        # Initialize strategies
        self._initialize_strategies()
        self.strategy_objects = self.strategies
        
        # Generate JWT token
        self._generate_token()
        
        logger.info(f"🔐 Agent {agent_id} initialized with FIXED RL params (ε={self.exploration_rate:.3f}, α={self.learning_rate:.3f}, γ={self.gamma:.3f})")
    
    def _generate_token(self):
        """Generate JWT token for agent"""
        payload = {
            'agent_id': self.agent_id,
            'exp': datetime.now() + timedelta(hours=24),
            'iat': datetime.now(),
            'type': 'agent'
        }
        self.session_token = jwt.encode(payload, self.secret_key, algorithm=ALGORITHM)
    
    def verify_token(self, token: str) -> bool:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[ALGORITHM])
            return payload.get('agent_id') == self.agent_id
        except jwt.ExpiredSignatureError:
            logger.warning(f"Token expired for agent {self.agent_id}")
            return False
        except jwt.InvalidTokenError:
            logger.warning(f"Invalid token for agent {self.agent_id}")
            return False
    
    def refresh_token(self) -> str:
        """Refresh JWT token"""
        self._generate_token()
        return self.session_token
    
    @abstractmethod
    def _initialize_strategies(self):
        """Initialize agent strategies"""
        pass
    
    @abstractmethod
    def select_strategy(
        self,
        state: Dict[str, float],
        opponent_strategy: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Select strategy with security checks"""
        pass
    
    @abstractmethod
    def calculate_utility(self, state: Dict[str, float]) -> float:
        """Calculate utility for current state"""
        pass
    
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """Validate agent action"""
        try:
            validated = AgentAction(**action)
            return True
        except ValidationError as e:
            logger.error(f"Action validation failed: {e}")
            return False
    
    def secure_action(
        self,
        action: Dict[str, Any],
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Tuple[bool, Any]:
        """Execute action with security checks"""
        start_time = datetime.now()
        
        if not self.rate_limiter.is_allowed(self.agent_id):
            logger.warning(f"Rate limit exceeded for agent {self.agent_id}")
            self.performance['failed_actions'] += 1
            return False, {"error": "Rate limit exceeded"}
        
        if not self.validate_action(action):
            self.performance['failed_actions'] += 1
            return False, {"error": "Invalid action"}
        
        if 'token' in action:
            if not self.verify_token(action['token']):
                self.performance['failed_actions'] += 1
                return False, {"error": "Invalid token"}
        
        try:
            result = self._execute_action(action)
            self.performance['total_actions'] += 1
            self.performance['successful_actions'] += 1
            
            self._log_audit(
                action=action['strategy_id'],
                strategy=action.get('strategy_id', ''),
                state_snapshot=action.get('state', {}),
                utility=result.get('utility', 0),
                ip_address=ip_address,
                session_id=session_id
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            self.performance['avg_response_time'] = (
                (self.performance['avg_response_time'] * 
                 (self.performance['total_actions'] - 1) + elapsed) /
                self.performance['total_actions']
            )
            
            return True, result
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            self.performance['failed_actions'] += 1
            return False, {"error": str(e)}
    
    def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute validated action"""
        strategy_id = action['strategy_id']
        state = action.get('state', {})
        
        self.performance['strategy_usage'][strategy_id] += 1
        utility = self.calculate_utility(state)
        
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'strategy': strategy_id,
            'utility': utility,
            'state': state
        })
        
        self.total_utility += utility
        self._encrypt_storage(
            f"action_{len(self.history)}",
            {'strategy': strategy_id, 'utility': utility}
        )
        
        return {
            'strategy': strategy_id,
            'utility': utility,
            'total_utility': self.total_utility,
            'performance': self.performance
        }
    
    def _log_audit(
        self,
        action: str,
        strategy: str,
        state_snapshot: Dict[str, float],
        utility: float,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log audit entry"""
        audit = AuditLog(
            timestamp=datetime.now(),
            agent_id=self.agent_id,
            action=action,
            strategy=strategy,
            state_snapshot=state_snapshot,
            utility=utility,
            ip_address=ip_address,
            session_id=session_id
        )
        self.audit_logs.append(audit)
        
        if len(self.audit_logs) > 1000:
            self.audit_logs = self.audit_logs[-1000:]
    
    def _encrypt_storage(self, key: str, data: Any):
        """Encrypt and store sensitive data"""
        try:
            json_data = json.dumps(data)
            encrypted = cipher.encrypt(json_data.encode())
            self._secure_storage[key] = encrypted
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
    
    def _decrypt_storage(self, key: str) -> Optional[Any]:
        """Decrypt stored data"""
        try:
            encrypted = self._secure_storage.get(key)
            if encrypted:
                decrypted = cipher.decrypt(encrypted)
                return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
        return None
    
    def get_audit_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get filtered audit logs"""
        logs = [log.__dict__ for log in self.audit_logs]
        
        if start_time:
            logs = [l for l in logs if l['timestamp'] >= start_time]
        if end_time:
            logs = [l for l in logs if l['timestamp'] <= end_time]
        
        return logs
    
    # ------------------------------------------------------------------
    # FIXED: Reinforcement learning - Better discretization
    # ------------------------------------------------------------------
    def dqn_strategy(self, state: Dict[str, float]) -> Optional[str]:
        if self.dqn is None or not self.strategies:
            return None
        idx = self.dqn.select(state, self._dqn_keys)
        return self.strategies[min(idx, len(self.strategies)-1)].id

    def dqn_learn(self, state: Dict[str, float], action: str, reward: float,
                  next_state: Dict[str, float], done: bool = False) -> float:
        if self.dqn is None:
            return 0.0
        ids = [s.id for s in self.strategies]
        if action not in ids:
            return 0.0
        return self.dqn.learn(state, ids.index(action), reward, next_state,
                              self._dqn_keys, done)

    def discretize_state(self, state: Dict[str, float]) -> str:
        """
        FIXED: Better state discretization with more granularity (5 bins each)
        
        Using 5 bins for each of 4 key metrics = 5^4 = 625 possible states
        This is a good balance between learning speed and accuracy
        """
        # Get key metrics with defaults
        economy = state.get('economic_stability', 50.0)
        tension = state.get('strategic_tension', 50.0)
        tech = state.get('technology_independence', 50.0)
        trade = state.get('trade_stability', 50.0)
        
        # More granular bins (5 bins each instead of 3)
        def bin_value(v: float, bins: int = 5) -> int:
            return min(bins - 1, int(v / (100.0 / bins)))
        
        # Create state key with 5 bins for each dimension
        eco_bin = bin_value(economy, 5)
        tension_bin = bin_value(tension, 5)
        tech_bin = bin_value(tech, 5)
        trade_bin = bin_value(trade, 5)
        
        return f"E{eco_bin}T{tension_bin}Tech{tech_bin}Tr{trade_bin}"
    
    def q_value(self, state_bucket: str, strategy_id: str) -> float:
        """Get Q-value for a state-action pair"""
        return self.q_table.get((state_bucket, strategy_id), 0.0)
    
    def best_q_strategy(self, state_bucket: str) -> Optional[str]:
        """Get best strategy for a state bucket"""
        if not self.strategies:
            return None
        
        best = None
        best_value = float('-inf')
        
        for strategy in self.strategies:
            value = self.q_value(state_bucket, strategy.id)
            if value > best_value:
                best_value = value
                best = strategy.id
        
        return best
    
    def q_learn(
        self,
        prev_bucket: str,
        action: str,
        reward: float,
        next_bucket: str,
    ) -> float:
        """
        FIXED: Q-learning update with better parameters
        
        Returns: New Q-value
        """
        next_max = max(
            (self.q_value(next_bucket, s.id) for s in self.strategies),
            default=0.0,
        )
        old_q = self.q_value(prev_bucket, action)
        new_q = old_q + self.learning_rate * (reward + self.gamma * next_max - old_q)
        self.q_table[(prev_bucket, action)] = new_q

        # FIXED: MUCH slower decay to keep exploring
        old_epsilon = self.exploration_rate
        self.exploration_rate = max(
            self.epsilon_min, 
            self.exploration_rate * self.epsilon_decay
        )
        
        # Log exploration rate periodically
        if len(self.reward_history) % 50 == 0 and len(self.reward_history) > 0:
            logger.info(f"🔍 {self.agent_id} ε={self.exploration_rate:.4f} (was {old_epsilon:.4f})")

        self.reward_history.append(reward)
        if len(self.reward_history) > 200:
            self.reward_history = self.reward_history[-200:]

        return new_q
    
    def q_strategy(self, state: Dict[str, float]) -> Optional[str]:
        """
        FIXED: Select strategy using Q-learning with epsilon-greedy
        Returns None if no learned values exist yet
        """
        if not self.strategies:
            return None
        
        state_bucket = self.discretize_state(state)
        
        # FIXED: Check if ANY Q-value exists for this state
        has_learned = any(
            (state_bucket, strategy.id) in self.q_table 
            for strategy in self.strategies
        )
        
        if not has_learned:
            return None
        
        # Epsilon-greedy exploration
        if random.random() < self.exploration_rate:
            return random.choice([s.id for s in self.strategies])
        
        # Exploit: best strategy
        return self.best_q_strategy(state_bucket)
    
    def record_outcome(self, strategy_id: str, utility: float, state: Dict[str, float]):
        """Record an outcome for history"""
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'strategy': strategy_id,
            'utility': utility,
            'state': state,
        })
        if len(self.history) > 500:
            self.history = self.history[-500:]
        self.total_utility += utility
        self.performance['strategy_usage'][strategy_id] += 1
    
    def learning_snapshot(self) -> Dict[str, Any]:
        """Compact telemetry for the dashboard's agent-intelligence panel"""
        recent = self.reward_history[-20:] if self.reward_history else []
        return {
            'epsilon': round(self.exploration_rate, 4),
            'q_states_learned': len({b for b, _ in self.q_table}),
            'q_entries': len(self.q_table),
            'avg_recent_reward': round(sum(recent) / len(recent), 4) if recent else 0.0,
            'rounds_observed': len(self.reward_history),
            'strategies': [s.dict() if hasattr(s, 'dict') else s for s in self.strategies],
            'total_utility': round(self.total_utility, 4),
            'learning_rate': self.learning_rate,
            'gamma': self.gamma,
            'epsilon_min': self.epsilon_min
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        return {
            'agent_id': self.agent_id,
            'total_actions': self.performance['total_actions'],
            'success_rate': (
                self.performance['successful_actions'] / 
                max(1, self.performance['total_actions'])
            ),
            'avg_response_time': self.performance['avg_response_time'],
            'total_utility': self.total_utility,
            'strategy_usage': dict(self.performance['strategy_usage']),
            'rate_limit_remaining': self.rate_limiter.get_remaining(self.agent_id),
            'session_valid': self.verify_token(self.session_token),
            'exploration_rate': self.exploration_rate,
            'q_table_size': len(self.q_table)
        }
    
    def get_strategies(self) -> List[Dict[str, Any]]:
        """Get available strategies"""
        return [s.dict() for s in self.strategy_objects]
    
    def get_history(
        self,
        limit: int = 100,
        decrypt: bool = False
    ) -> List[Dict[str, Any]]:
        """Get agent history"""
        history = self.history[-limit:]
        
        if decrypt:
            for entry in history:
                if 'encrypted' in entry:
                    decrypted = self._decrypt_storage(entry['encrypted'])
                    if decrypted:
                        entry['data'] = decrypted
        
        return history
    
    def reset(self):
        """Reset agent state"""
        self.history = []
        self.total_utility = 0
        self.performance = {
            'total_actions': 0,
            'successful_actions': 0,
            'failed_actions': 0,
            'avg_response_time': 0.0,
            'strategy_usage': defaultdict(int)
        }
        self.audit_logs = []
        self._secure_storage = {}
        self.q_table = {}
        self.reward_history = []
        self.exploration_rate = 0.3  # Reset to initial
        self._generate_token()
        
        logger.info(f"🔄 Agent {self.agent_id} reset")
    
    def get_strategy_score(self, strategy: str) -> float:
        """Get score for a strategy based on history"""
        if hasattr(self, 'history'):
            scores = []
            for entry in self.history[-100:]:
                if entry.get('strategy') == strategy:
                    scores.append(entry.get('utility', 0))
            if scores:
                return sum(scores) / len(scores)
        return 0.0
    
    def get_q_values(self) -> Dict[str, float]:
        """Get Q-values for debugging"""
        if hasattr(self, 'q_table'):
            return {f"{state}|{action}": value 
                    for (state, action), value in self.q_table.items()}
        return {}
    
    def get_best_action(self, state: Any) -> str:
        """Get best action from Q-table"""
        if not hasattr(self, 'q_table') or not self.strategies:
            return random.choice([s.id for s in self.strategies]) if self.strategies else 'H1'
        
        state_bucket = self.discretize_state(state) if isinstance(state, dict) else str(state)
        best = self.best_q_strategy(state_bucket)
        return best if best else random.choice([s.id for s in self.strategies])
    
    def update_from_history(self):
        """
        Update agent state from history - for compatibility
        This is called by engine.py
        """
        # We already update in real-time via record_outcome()
        # So this is just a placeholder for compatibility
        pass