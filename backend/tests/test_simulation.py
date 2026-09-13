# test_complete.py
import asyncio
from backend.app.simulation import (
    SimulationEngine, SimulationConfig,
    ScenarioManager, ScenarioCategory,
    SimulationReplay, PlaybackSpeed
)

async def test_all():
    print("🚀 Testing Complete Simulation System...")
    
    # 1. Test Scenarios
    print("\n📚 Testing Scenarios...")
    scenario_manager = ScenarioManager()
    scenarios = scenario_manager.get_all_scenarios()
    print(f"   Total scenarios: {len(scenarios)}")
    
    for scenario in scenarios[:3]:
        print(f"   - {scenario.name} ({scenario.difficulty.value})")
    
    # 2. Test Simulation with Scenario
    print("\n⚙️ Testing Simulation with Scenario...")
    config = SimulationConfig(max_rounds=30, log_interval=5)
    engine = SimulationEngine(config)
    
    # Apply scenario
    scenario = scenario_manager.get_scenario('tech_supremacy')
    scenario_manager.apply_scenario_to_environment(scenario.id, engine.environment)
    
    # Run
    result = await engine.run()
    print(f"   Completed: {result.rounds_completed} rounds")
    print(f"   Hegemon Utility: {result.hegemon_total_utility:.3f}")
    
    # 3. Test Replay
    print("\n🎬 Testing Replay...")
    replay = SimulationReplay()
    replay.load_from_simulation(result)
    
    print(f"   Frames loaded: {len(replay.frames)}")
    print(f"   Key events: {len(replay.stats.key_events)}")
    
    # Get current frame
    current = replay.get_current_frame()
    if current:
        print(f"   Current state: Eco={current.state.get('economic_stability', 0):.1f}")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_all())