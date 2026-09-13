# test_agents.py
import asyncio
from backend.app.agents.hegemon_agent import HegemonAgent
from backend.app.agents.sovereign_agent import SovereignAgent

async def test_agents():
    print("🚀 Testing Agents with Security...")
    
    # Initialize agents
    hegemon = HegemonAgent()
    sovereign = SovereignAgent()
    
    print(f"✅ Hegemon Token: {hegemon.session_token[:20]}...")
    print(f"✅ Sovereign Token: {sovereign.session_token[:20]}...")
    
    # Test state
    state = {
        'economic_stability': 75,
        'technology_independence': 62,
        'trade_stability': 70,
        'currency_stability': 68,
        'public_sentiment': 0.22,
        'strategic_tension': 25,
        'economic_influence': 70,
        'technology_advantage': 65,
        'strategic_utility': 68,
        'stability': 72,
        'economic_resilience': 65,
        'sovereignty': 60
    }
    
    # Test strategy selection
    print("\n📊 Strategy Selection:")
    for i in range(5):
        h_strategy = hegemon.select_strategy(state)
        s_strategy = sovereign.select_strategy(state, h_strategy)
        
        print(f"  Round {i+1}: H={h_strategy}, S={s_strategy}")
        
        # Execute actions securely
        h_action = {
            'strategy_id': h_strategy,
            'state': state,
            'token': hegemon.session_token
        }
        success, result = hegemon.secure_action(h_action)
        if success:
            print(f"    Hegemon Utility: {result['utility']:.3f}")
        
        s_action = {
            'strategy_id': s_strategy,
            'state': state,
            'token': sovereign.session_token
        }
        success, result = sovereign.secure_action(s_action)
        if success:
            print(f"    Sovereign Utility: {result['utility']:.3f}")
    
    # Get performance
    print("\n📈 Performance Metrics:")
    print(f"  Hegemon: {hegemon.get_performance_metrics()}")
    print(f"  Sovereign: {sovereign.get_performance_metrics()}")
    
    # Get audit logs
    print("\n🔐 Audit Logs:")
    h_logs = hegemon.get_audit_logs()
    print(f"  Hegemon Logs: {len(h_logs)} entries")
    
    s_logs = sovereign.get_audit_logs()
    print(f"  Sovereign Logs: {len(s_logs)} entries")

asyncio.run(test_agents())