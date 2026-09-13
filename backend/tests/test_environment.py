# test_environment.py
import asyncio
from backend.app.environment.environment import StrategicEnvironment

async def test():
    env = StrategicEnvironment()
    
    print("🚀 Testing Environment...")
    print(f"Initial State: {env.get_state()}")
    
    # Run some steps
    for i in range(10):
        state, rewards = await env.step('H1', 'S2')
        print(f"\nRound {i+1}:")
        print(f"  State: Eco={state['economic_stability']:.1f}, Tech={state['technology_independence']:.1f}")
        print(f"  Rewards: H={rewards['hegemon']:.3f}, S={rewards['sovereign']:.3f}")
    
    # Get analysis
    print("\n📊 Equilibrium Analysis:")
    eq = env.get_equilibrium_analysis()
    for eq_type, result in eq.items():
        print(f"  {eq_type.value}: {len(result.equilibria)} equilibria found")
    
    print("\n📈 Performance:")
    metrics = env.get_performance_metrics()
    print(f"  Total Rounds: {metrics['total_rounds']}")

asyncio.run(test())