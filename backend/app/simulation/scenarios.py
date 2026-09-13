"""
Pre-defined Simulation Scenarios with:
- Historical scenarios
- Hypothetical scenarios
- Stress test scenarios
- Custom scenario builder
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from enum import Enum

from ..environment.state import EnvironmentState, RegionalMetrics

logger = logging.getLogger(__name__)

class ScenarioCategory(Enum):
    """Categories of scenarios"""
    HISTORICAL = "historical"
    HYPOTHETICAL = "hypothetical"
    STRESS_TEST = "stress_test"
    EDUCATIONAL = "educational"
    CUSTOM = "custom"

class ScenarioDifficulty(Enum):
    """Difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"

@dataclass
class Scenario:
    """Complete scenario definition"""
    id: str
    name: str
    description: str
    category: ScenarioCategory
    difficulty: ScenarioDifficulty
    initial_state: Dict[str, float]
    regional_states: Optional[List[Dict[str, float]]] = None
    hegemon_strategy_bias: Optional[Dict[str, float]] = None
    sovereign_strategy_bias: Optional[Dict[str, float]] = None
    termination_conditions: Dict[str, Any] = field(default_factory=dict)
    expected_outcomes: Optional[Dict[str, float]] = None
    tags: List[str] = field(default_factory=list)
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scenario to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'difficulty': self.difficulty.value,
            'initial_state': self.initial_state,
            'regional_states': self.regional_states,
            'hegemon_strategy_bias': self.hegemon_strategy_bias,
            'sovereign_strategy_bias': self.sovereign_strategy_bias,
            'termination_conditions': self.termination_conditions,
            'expected_outcomes': self.expected_outcomes,
            'tags': self.tags,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'version': self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scenario':
        """Create scenario from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            category=ScenarioCategory(data['category']),
            difficulty=ScenarioDifficulty(data['difficulty']),
            initial_state=data['initial_state'],
            regional_states=data.get('regional_states'),
            hegemon_strategy_bias=data.get('hegemon_strategy_bias'),
            sovereign_strategy_bias=data.get('sovereign_strategy_bias'),
            termination_conditions=data.get('termination_conditions', {}),
            expected_outcomes=data.get('expected_outcomes'),
            tags=data.get('tags', []),
            created_by=data.get('created_by', 'system'),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.now(),
            version=data.get('version', '1.0')
        )

class ScenarioManager:
    """
    Manage pre-defined and custom scenarios
    """
    
    def __init__(self):
        self.scenarios: Dict[str, Scenario] = {}
        self._initialize_scenarios()
        logger.info("📚 Scenario Manager initialized")
    
    def _initialize_scenarios(self):
        """Initialize default scenarios"""
        
        # 1. Cold War Revival
        self.scenarios['cold_war_revival'] = Scenario(
            id='cold_war_revival',
            name='Cold War Revival',
            description='A scenario mimicking Cold War tensions with modern technology',
            category=ScenarioCategory.HISTORICAL,
            difficulty=ScenarioDifficulty.MEDIUM,
            initial_state={
                'economic_stability': 65.0,
                'technology_independence': 60.0,
                'trade_stability': 55.0,
                'currency_stability': 60.0,
                'supply_chain_stability': 50.0,
                'strategic_tension': 70.0,
                'ai_capability': 55.0,
                'public_sentiment': -0.15
            },
            regional_states=[
                {'region_name': 'North America', 'economic_index': 75.0, 'technology_index': 80.0, 
                 'trade_stability': 65.0, 'sentiment': -0.10, 'resilience': 70.0},
                {'region_name': 'Europe', 'economic_index': 70.0, 'technology_index': 75.0, 
                 'trade_stability': 60.0, 'sentiment': -0.05, 'resilience': 65.0},
                {'region_name': 'Asia Pacific', 'economic_index': 60.0, 'technology_index': 55.0, 
                 'trade_stability': 50.0, 'sentiment': -0.20, 'resilience': 55.0},
            ],
            hegemon_strategy_bias={'H1': 0.4, 'H2': 0.3, 'H3': 0.2, 'H4': 0.1},
            sovereign_strategy_bias={'S1': 0.3, 'S2': 0.3, 'S3': 0.2, 'S4': 0.2},
            termination_conditions={'max_tension': 85, 'min_stability': 15},
            expected_outcomes={'hegemon_utility': 0.6, 'sovereign_utility': 0.4},
            tags=['tension', 'cold_war', 'historical']
        )
        
        # 2. Technological Supremacy
        self.scenarios['tech_supremacy'] = Scenario(
            id='tech_supremacy',
            name='Technological Supremacy',
            description='Scenario focused on AI and technology dominance',
            category=ScenarioCategory.HYPOTHETICAL,
            difficulty=ScenarioDifficulty.HARD,
            initial_state={
                'economic_stability': 70.0,
                'technology_independence': 40.0,
                'trade_stability': 65.0,
                'currency_stability': 68.0,
                'supply_chain_stability': 60.0,
                'strategic_tension': 45.0,
                'ai_capability': 35.0,
                'public_sentiment': 0.10
            },
            regional_states=[
                {'region_name': 'North America', 'economic_index': 80.0, 'technology_index': 90.0, 
                 'trade_stability': 75.0, 'sentiment': 0.20, 'resilience': 75.0},
                {'region_name': 'Asia Pacific', 'economic_index': 65.0, 'technology_index': 50.0, 
                 'trade_stability': 60.0, 'sentiment': 0.05, 'resilience': 60.0},
            ],
            hegemon_strategy_bias={'H1': 0.2, 'H2': 0.4, 'H3': 0.2, 'H4': 0.2},
            sovereign_strategy_bias={'S1': 0.2, 'S2': 0.5, 'S3': 0.2, 'S4': 0.1},
            termination_conditions={'tech_independence': 80, 'ai_capability': 85},
            expected_outcomes={'hegemon_utility': 0.7, 'sovereign_utility': 0.5},
            tags=['technology', 'ai', 'future']
        )
        
        # 3. Economic Crisis
        self.scenarios['economic_crisis'] = Scenario(
            id='economic_crisis',
            name='Global Economic Crisis',
            description='Scenario simulating a global economic downturn',
            category=ScenarioCategory.STRESS_TEST,
            difficulty=ScenarioDifficulty.EXPERT,
            initial_state={
                'economic_stability': 30.0,
                'technology_independence': 45.0,
                'trade_stability': 35.0,
                'currency_stability': 25.0,
                'supply_chain_stability': 30.0,
                'strategic_tension': 60.0,
                'ai_capability': 40.0,
                'public_sentiment': -0.40
            },
            regional_states=[
                {'region_name': 'North America', 'economic_index': 35.0, 'technology_index': 60.0, 
                 'trade_stability': 30.0, 'sentiment': -0.35, 'resilience': 40.0},
                {'region_name': 'Europe', 'economic_index': 30.0, 'technology_index': 55.0, 
                 'trade_stability': 25.0, 'sentiment': -0.40, 'resilience': 35.0},
                {'region_name': 'Asia Pacific', 'economic_index': 40.0, 'technology_index': 45.0, 
                 'trade_stability': 35.0, 'sentiment': -0.30, 'resilience': 45.0},
            ],
            hegemon_strategy_bias={'H1': 0.5, 'H2': 0.2, 'H3': 0.2, 'H4': 0.1},
            sovereign_strategy_bias={'S1': 0.4, 'S2': 0.2, 'S3': 0.3, 'S4': 0.1},
            termination_conditions={'min_economic': 10, 'max_tension': 90},
            expected_outcomes={'hegemon_utility': 0.3, 'sovereign_utility': 0.6},
            tags=['crisis', 'economic', 'stress_test']
        )
        
        # 4. Multipolar World
        self.scenarios['multipolar_world'] = Scenario(
            id='multipolar_world',
            name='Multipolar World Order',
            description='Scenario with multiple power centers',
            category=ScenarioCategory.HYPOTHETICAL,
            difficulty=ScenarioDifficulty.MEDIUM,
            initial_state={
                'economic_stability': 72.0,
                'technology_independence': 65.0,
                'trade_stability': 68.0,
                'currency_stability': 64.0,
                'supply_chain_stability': 70.0,
                'strategic_tension': 35.0,
                'ai_capability': 62.0,
                'public_sentiment': 0.15
            },
            regional_states=[
                {'region_name': 'North America', 'economic_index': 78.0, 'technology_index': 85.0, 
                 'trade_stability': 72.0, 'sentiment': 0.20, 'resilience': 75.0},
                {'region_name': 'Europe', 'economic_index': 75.0, 'technology_index': 80.0, 
                 'trade_stability': 78.0, 'sentiment': 0.25, 'resilience': 78.0},
                {'region_name': 'Asia Pacific', 'economic_index': 70.0, 'technology_index': 68.0, 
                 'trade_stability': 65.0, 'sentiment': 0.10, 'resilience': 68.0},
                {'region_name': 'South America', 'economic_index': 60.0, 'technology_index': 55.0, 
                 'trade_stability': 58.0, 'sentiment': 0.05, 'resilience': 60.0},
            ],
            hegemon_strategy_bias={'H1': 0.25, 'H2': 0.25, 'H3': 0.25, 'H4': 0.25},
            sovereign_strategy_bias={'S1': 0.25, 'S2': 0.25, 'S3': 0.25, 'S4': 0.25},
            termination_conditions={'max_rounds': 100},
            expected_outcomes={'hegemon_utility': 0.5, 'sovereign_utility': 0.5},
            tags=['multipolar', 'balanced', 'future']
        )
        
        # 5. Alliance Formation
        self.scenarios['alliance_formation'] = Scenario(
            id='alliance_formation',
            name='Strategic Alliance Formation',
            description='Scenario focused on forming and managing alliances',
            category=ScenarioCategory.EDUCATIONAL,
            difficulty=ScenarioDifficulty.EASY,
            initial_state={
                'economic_stability': 68.0,
                'technology_independence': 55.0,
                'trade_stability': 62.0,
                'currency_stability': 60.0,
                'supply_chain_stability': 58.0,
                'strategic_tension': 50.0,
                'ai_capability': 50.0,
                'public_sentiment': 0.0
            },
            regional_states=[
                {'region_name': 'North America', 'economic_index': 80.0, 'technology_index': 85.0, 
                 'trade_stability': 75.0, 'sentiment': 0.10, 'resilience': 80.0},
                {'region_name': 'Europe', 'economic_index': 72.0, 'technology_index': 78.0, 
                 'trade_stability': 70.0, 'sentiment': 0.05, 'resilience': 75.0},
                {'region_name': 'Middle East', 'economic_index': 55.0, 'technology_index': 45.0, 
                 'trade_stability': 50.0, 'sentiment': -0.10, 'resilience': 50.0},
            ],
            hegemon_strategy_bias={'H1': 0.3, 'H2': 0.3, 'H3': 0.2, 'H4': 0.2},
            sovereign_strategy_bias={'S1': 0.2, 'S2': 0.2, 'S3': 0.3, 'S4': 0.3},
            termination_conditions={'max_rounds': 50},
            expected_outcomes={'hegemon_utility': 0.4, 'sovereign_utility': 0.6},
            tags=['alliance', 'diplomacy', 'educational']
        )
        
        logger.info(f"✅ Initialized {len(self.scenarios)} scenarios")
    
    def get_scenario(self, scenario_id: str) -> Optional[Scenario]:
        """Get a scenario by ID"""
        return self.scenarios.get(scenario_id)
    
    def get_all_scenarios(self) -> List[Scenario]:
        """Get all scenarios"""
        return list(self.scenarios.values())
    
    def get_scenarios_by_category(self, category: ScenarioCategory) -> List[Scenario]:
        """Get scenarios by category"""
        return [s for s in self.scenarios.values() if s.category == category]
    
    def get_scenarios_by_difficulty(self, difficulty: ScenarioDifficulty) -> List[Scenario]:
        """Get scenarios by difficulty"""
        return [s for s in self.scenarios.values() if s.difficulty == difficulty]
    
    def get_scenarios_by_tag(self, tag: str) -> List[Scenario]:
        """Get scenarios by tag"""
        return [s for s in self.scenarios.values() if tag in s.tags]
    
    def create_custom_scenario(
        self,
        name: str,
        description: str,
        initial_state: Dict[str, float],
        **kwargs
    ) -> Scenario:
        """Create a custom scenario"""
        scenario_id = f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        scenario = Scenario(
            id=scenario_id,
            name=name,
            description=description,
            category=ScenarioCategory.CUSTOM,
            difficulty=kwargs.get('difficulty', ScenarioDifficulty.MEDIUM),
            initial_state=initial_state,
            regional_states=kwargs.get('regional_states'),
            hegemon_strategy_bias=kwargs.get('hegemon_strategy_bias'),
            sovereign_strategy_bias=kwargs.get('sovereign_strategy_bias'),
            termination_conditions=kwargs.get('termination_conditions', {}),
            expected_outcomes=kwargs.get('expected_outcomes'),
            tags=kwargs.get('tags', []),
            created_by=kwargs.get('created_by', 'user')
        )
        
        self.scenarios[scenario_id] = scenario
        logger.info(f"✅ Created custom scenario: {scenario_id}")
        
        return scenario
    
    def delete_scenario(self, scenario_id: str):
        """Delete a scenario"""
        if scenario_id in self.scenarios:
            del self.scenarios[scenario_id]
            logger.info(f"🗑️ Deleted scenario: {scenario_id}")
    
    def save_scenario(self, scenario_id: str, filepath: str):
        """Save scenario to file"""
        scenario = self.get_scenario(scenario_id)
        if scenario:
            with open(filepath, 'w') as f:
                json.dump(scenario.to_dict(), f, indent=2)
            logger.info(f"💾 Saved scenario: {scenario_id}")
    
    def load_scenario(self, filepath: str) -> Scenario:
        """Load scenario from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        scenario = Scenario.from_dict(data)
        self.scenarios[scenario.id] = scenario
        logger.info(f"📂 Loaded scenario: {scenario.id}")
        
        return scenario
    
    def apply_scenario_to_environment(
        self,
        scenario_id: str,
        environment
    ):
        """Apply scenario to environment"""
        scenario = self.get_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")
        
        # Reset environment
        environment.reset()
        
        # Apply initial state
        environment.state.update(scenario.initial_state, stochastic=False)
        
        # Apply regional states
        if scenario.regional_states:
            for region_state in scenario.regional_states:
                region_name = region_state.get('region_name')
                if region_name:
                    environment.state.update_region(region_name, region_state)
        
        logger.info(f"✅ Applied scenario: {scenario.name}")
        return environment
    
    def get_scenario_analysis(self, scenario_id: str) -> Dict[str, Any]:
        """Analyze scenario characteristics"""
        scenario = self.get_scenario(scenario_id)
        if not scenario:
            return {'error': 'Scenario not found'}
        
        # Analyze initial state
        initial = scenario.initial_state
        analysis = {
            'scenario_id': scenario.id,
            'name': scenario.name,
            'category': scenario.category.value,
            'difficulty': scenario.difficulty.value,
            'tags': scenario.tags,
            'state_analysis': {
                'economic_stability': initial.get('economic_stability', 50),
                'technology_independence': initial.get('technology_independence', 50),
                'trade_stability': initial.get('trade_stability', 50),
                'strategic_tension': initial.get('strategic_tension', 50),
                'public_sentiment': initial.get('public_sentiment', 0),
                'overall_stability': sum([
                    initial.get('economic_stability', 50),
                    initial.get('technology_independence', 50),
                    initial.get('trade_stability', 50)
                ]) / 3
            },
            'risk_level': self._calculate_risk_level(scenario),
            'complexity_score': self._calculate_complexity(scenario),
            'strategy_bias': {
                'hegemon': scenario.hegemon_strategy_bias,
                'sovereign': scenario.sovereign_strategy_bias
            }
        }
        
        return analysis
    
    def _calculate_risk_level(self, scenario: Scenario) -> str:
        """Calculate risk level of scenario"""
        initial = scenario.initial_state
        tension = initial.get('strategic_tension', 50)
        
        if tension > 70:
            return 'high'
        elif tension > 50:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_complexity(self, scenario: Scenario) -> float:
        """Calculate complexity score (0-1)"""
        initial = scenario.initial_state
        
        # More regions = more complex
        region_complexity = len(scenario.regional_states or []) / 6
        
        # More variables = more complex
        var_complexity = len(initial.keys()) / 8
        
        # Strategy biases = more complex
        bias_complexity = 0
        if scenario.hegemon_strategy_bias:
            bias_complexity += 0.2
        if scenario.sovereign_strategy_bias:
            bias_complexity += 0.2
        
        complexity = (region_complexity * 0.3 + var_complexity * 0.3 + bias_complexity * 0.4)
        
        return min(1.0, complexity)