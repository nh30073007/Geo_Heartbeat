# test_backend.py
import httpx
import asyncio
import json
import time

async def test_backend():
    print("=" * 60)
    print("🚀 Testing Strategic AI Nexus Backend")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        base_url = "http://localhost:8000"
        
        # 1. Health Check
        print("\n📋 1. Health Check:")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Status: {data.get('status', 'unknown')}")
                print(f"   ✅ Uptime: {data.get('uptime', 0):.2f}s")
            else:
                print(f"   ❌ Error: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # 2. Create Simulation
        print("\n📋 2. Create Simulation:")
        try:
            response = await client.post(f"{base_url}/api/simulation/create")
            if response.status_code == 200:
                sim_data = response.json()
                sim_id = sim_data.get('sim_id')
                print(f"   ✅ Simulation ID: {sim_id}")
            else:
                print(f"   ❌ Error: Status {response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # 3. Start Simulation
        print("\n📋 3. Start Simulation:")
        try:
            response = await client.post(f"{base_url}/api/simulation/start/{sim_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Status: {data.get('status', 'unknown')}")
            else:
                print(f"   ❌ Error: Status {response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # 4. Wait for simulation to start
        print("\n📋 4. Waiting for simulation to start...")
        await asyncio.sleep(3)  # Wait 3 seconds
        
        # 5. Get Status (with retry)
        print("\n📋 5. Get Status:")
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = await client.get(f"{base_url}/api/simulation/status/{sim_id}")
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status', 'unknown')
                    current_round = data.get('current_round', 0)
                    max_rounds = data.get('max_rounds', 100)
                    progress = data.get('progress', 0)
                    
                    print(f"   ✅ Status: {status}")
                    print(f"   ✅ Round: {current_round}/{max_rounds}")
                    print(f"   ✅ Progress: {progress*100:.1f}%")
                    break
                else:
                    print(f"   ⚠️ Attempt {attempt+1}: Status {response.status_code}")
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"   ⚠️ Attempt {attempt+1}: {e}")
                await asyncio.sleep(1)
        else:
            print("   ❌ Failed to get status after retries")
            return
        
        # 6. Get Current State
        print("\n📋 6. Get Current State:")
        try:
            response = await client.get(f"{base_url}/api/state/current/{sim_id}")
            if response.status_code == 200:
                data = response.json()
                state = data.get('state', {})
                print(f"   ✅ Economic Stability: {state.get('economic_stability', 0):.1f}")
                print(f"   ✅ Technology Independence: {state.get('technology_independence', 0):.1f}")
                print(f"   ✅ Trade Stability: {state.get('trade_stability', 0):.1f}")
                print(f"   ✅ Public Sentiment: {state.get('public_sentiment', 0):.3f}")
                print(f"   ✅ Strategic Tension: {state.get('strategic_tension', 0):.1f}")
                print(f"   ✅ AI Capability: {state.get('ai_capability', 0):.1f}")
            else:
                print(f"   ❌ Error: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 7. Get History
        print("\n📋 7. Get History (last 3):")
        try:
            response = await client.get(f"{base_url}/api/state/history/{sim_id}?limit=3")
            if response.status_code == 200:
                data = response.json()
                history = data.get('history', [])
                print(f"   ✅ Total History: {data.get('total', 0)} entries")
                print(f"   ✅ Latest rounds: {[h.get('round', 0) for h in history]}")
            else:
                print(f"   ❌ Error: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 8. Get Analytics
        print("\n📋 8. Get Analytics:")
        try:
            response = await client.get(f"{base_url}/api/analytics/performance/{sim_id}")
            if response.status_code == 200:
                data = response.json()
                metrics = data.get('metrics', {})
                print(f"   ✅ Total Rounds: {metrics.get('total_rounds', 0)}")
                print(f"   ✅ Status: {metrics.get('status', 'unknown')}")
                print(f"   ✅ Events: {metrics.get('events_count', 0)}")
            else:
                print(f"   ❌ Error: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 9. Stop Simulation
        print("\n📋 9. Stop Simulation:")
        try:
            response = await client.post(f"{base_url}/api/simulation/stop/{sim_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Status: {data.get('status', 'unknown')}")
            else:
                print(f"   ❌ Error: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 60)
        print("✅ All Tests Completed!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_backend())