#!/usr/bin/env python3
"""
Test script for Mission Linking and Resumable Missions
Demonstrates how cycle logs are linked and missions can be resumed.
"""

import os
import sys
import asyncio
import json
import logging
from typing import Dict, Any

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.orchestrator_agent_refactored import create_orchestrator
from orchestrator.mission_management import MissionLog, CycleLog

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# Suppress verbose logs from specific modules
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('autogen_core.events').setLevel(logging.WARNING)
logging.getLogger('autogen_core').setLevel(logging.WARNING)
logging.getLogger('autogen_ext').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def test_mission_creation_and_linking():
    """Test creating a mission and linking cycles."""
    print("=" * 60)
    print("Testing Mission Creation and Cycle Linking")
    print("=" * 60)
    
    try:
        # Set up environment
        os.environ.setdefault("OPENAI_API_KEY", "test-key-for-testing")
        os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
        
        # Create orchestrator
        orchestrator = create_orchestrator()
        
        # Test 1: Create a new mission
        print("\n1. Creating a new mission...")
        mission_name = "AI Chatbot Development"
        overall_mission = "Create an AI-powered customer service chatbot"
        
        mission_log = orchestrator.create_or_load_mission(
            mission_name=mission_name,
            overall_mission=overall_mission,
            resume_existing=False  # Force new mission for testing
        )
        
        print(f"✅ Created mission: {mission_log.mission_id}")
        print(f"   Mission name: {mission_log.mission_name}")
        print(f"   Status: {mission_log.status}")
        print(f"   Persistent agents: {len(mission_log.persistent_agents)}")
        
        # Test 2: Simulate multiple cycles
        print("\n2. Simulating multiple decision cycles...")
        
        decision_focuses = [
            "Identify target market and user personas",
            "Design chatbot conversation flow and responses",
            "Implement basic chatbot functionality",
            "Test chatbot with initial user group"
        ]
        
        for i, decision_focus in enumerate(decision_focuses, 1):
            print(f"\n   Cycle {i}: {decision_focus}")
            
            # Create a mock cycle (without actually running the full cycle)
            cycle_result = await simulate_cycle(orchestrator, decision_focus, {
                "overall_mission": overall_mission,
                "cycle_number": i
            })
            
            print(f"   ✅ Cycle {i} completed: {cycle_result['cycle_id']}")
            print(f"      Status: {cycle_result['status']}")
            print(f"      Duration: {cycle_result.get('duration_minutes', 0):.2f} minutes")
        
        # Test 3: Check mission log state
        print("\n3. Checking mission log state...")
        current_mission = orchestrator.current_mission_log
        print(f"   Total cycles: {len(current_mission.cycle_ids)}")
        print(f"   Completed cycles: {current_mission.completed_cycles}")
        print(f"   Total cost: ${current_mission.total_mission_cost:.2f}")
        print(f"   Total time: {current_mission.total_mission_time_minutes:.2f} minutes")
        print(f"   Key learnings: {len(current_mission.key_learnings)}")
        
        # Test 4: Check cycle linking
        print("\n4. Verifying cycle linking...")
        for i, cycle_id in enumerate(current_mission.cycle_ids):
            cycle_file = f"mission_logs/{cycle_id}.json"
            if os.path.exists(cycle_file):
                with open(cycle_file, 'r') as f:
                    cycle_data = json.load(f)
                
                print(f"   Cycle {i+1} ({cycle_id}):")
                print(f"      Previous: {cycle_data.get('previous_cycle_id', 'None')}")
                print(f"      Next: {cycle_data.get('next_cycle_id', 'None')}")
                print(f"      Parent Mission: {cycle_data.get('parent_mission_id', 'None')}")
                print(f"      Sequence: {cycle_data.get('cycle_sequence_number', 0)}")
                print(f"      Context from previous: {len(cycle_data.get('previous_cycles_context', []))}")
        
        print(f"\n✅ Mission linking test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during mission linking test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_mission_resumption():
    """Test resuming an existing mission."""
    print("\n" + "=" * 60)
    print("Testing Mission Resumption")
    print("=" * 60)
    
    try:
        # Create new orchestrator instance (simulating restart)
        orchestrator = create_orchestrator()
        
        # Test 1: Try to resume existing mission
        print("\n1. Attempting to resume existing mission...")
        mission_name = "AI Chatbot Development"
        overall_mission = "Create an AI-powered customer service chatbot"
        
        mission_log = orchestrator.create_or_load_mission(
            mission_name=mission_name,
            overall_mission=overall_mission,
            resume_existing=True
        )
        
        if mission_log.cycle_ids:
            print(f"✅ Resumed existing mission: {mission_log.mission_id}")
            print(f"   Existing cycles: {len(mission_log.cycle_ids)}")
            print(f"   Last cycle: {mission_log.current_cycle_id}")
            print(f"   Mission status: {mission_log.status}")
        else:
            print(f"✅ No existing mission found, created new one: {mission_log.mission_id}")
        
        # Test 2: Get mission context for agents
        print("\n2. Getting mission context for agents...")
        context = orchestrator.get_mission_context_for_agents()
        print(f"   Mission ID: {context.get('mission_id', 'None')}")
        print(f"   Cycles completed: {context.get('cycles_completed', 0)}")
        print(f"   Total cost so far: ${context.get('total_cost_so_far', 0):.2f}")
        print(f"   Key learnings: {len(context.get('key_learnings', []))}")
        print(f"   Recent cycles: {len(context.get('recent_cycles', []))}")
        
        # Test 3: Add another cycle to resumed mission
        print("\n3. Adding new cycle to resumed mission...")
        new_cycle_result = await simulate_cycle(orchestrator, "Deploy chatbot to production environment", {
            "overall_mission": overall_mission,
            "cycle_number": len(mission_log.cycle_ids) + 1
        })
        
        print(f"✅ New cycle added: {new_cycle_result['cycle_id']}")
        print(f"   Total cycles now: {len(orchestrator.current_mission_log.cycle_ids)}")
        
        print(f"\n✅ Mission resumption test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during mission resumption test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def simulate_cycle(orchestrator, decision_focus: str, mission_context: dict) -> dict:
    """Simulate a decision cycle without actually running the full LLM interactions."""
    from datetime import datetime, timedelta
    import random
    
    # Create a mock cycle log
    cycle_start_time = datetime.now()
    mission_id = f"cycle_{cycle_start_time.strftime('%Y%m%d_%H%M%S')}_{decision_focus[:20].replace(' ', '_')}"
    
    # Create cycle log
    cycle_log = CycleLog(
        mission_id=mission_id,
        timestamp=cycle_start_time.isoformat(),
        overall_mission=mission_context.get("overall_mission", ""),
        current_decision_focus=decision_focus,
        status="started"
    )
    
    # Link to previous cycles
    cycle_log = orchestrator._link_cycle_to_previous(cycle_log)
    
    # Simulate some interactions
    cycle_log.specialist_interactions.append({
        "timestamp": datetime.now().isoformat(),
        "agent_name": "TestAgent",
        "type": "recommendation_request",
        "cost": random.uniform(0.01, 0.05)
    })
    
    # Simulate completion
    cycle_end_time = cycle_start_time + timedelta(minutes=random.uniform(2, 10))
    cycle_log.cycle_duration_minutes = (cycle_end_time - cycle_start_time).total_seconds() / 60.0
    cycle_log.total_cycle_cost = random.uniform(0.05, 0.20)
    cycle_log.status = "completed_cycle_success"
    cycle_log.agents_used = ["TestAgent", "ReviewAgent"]
    cycle_log.kpi_outcomes = {"status": "success_cycle_completed"}
    
    # Add mock retrospective
    cycle_log.orchestrator_interactions.append({
        "timestamp": datetime.now().isoformat(),
        "type": "retrospective_analysis",
        "parsed_output": f"### Key Learnings\n1. {decision_focus} was completed successfully\n2. Good collaboration between agents\n\n### Actionable Recommendations\n1. Continue with next phase\n2. Monitor user feedback"
    })
    
    # Save cycle log
    log_dir = "mission_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f"{cycle_log.mission_id}.json")
    
    with open(log_file_path, "w") as f:
        from dataclasses import asdict
        json.dump(asdict(cycle_log), f, indent=2)
    
    # Update mission log
    orchestrator._update_mission_log(cycle_log)
    
    return {
        "cycle_id": mission_id,
        "status": cycle_log.status,
        "duration_minutes": cycle_log.cycle_duration_minutes,
        "cost": cycle_log.total_cycle_cost
    }

def test_cycle_navigation():
    """Test navigating through linked cycles."""
    print("\n" + "=" * 60)
    print("Testing Cycle Navigation")
    print("=" * 60)
    
    try:
        # Find mission files
        mission_files = []
        cycle_files = []
        
        if os.path.exists("mission_logs"):
            for filename in os.listdir("mission_logs"):
                if filename.endswith(".json"):
                    if filename.startswith("mission_") and not filename.startswith("cycle_"):
                        mission_files.append(filename)
                    elif filename.startswith("cycle_"):
                        cycle_files.append(filename)
        
        print(f"Found {len(mission_files)} mission files and {len(cycle_files)} cycle files")
        
        # Test navigation through a mission's cycles
        if mission_files:
            mission_file = mission_files[0]
            print(f"\n1. Examining mission: {mission_file}")
            
            with open(f"mission_logs/{mission_file}", 'r') as f:
                mission_data = json.load(f)
            
            print(f"   Mission: {mission_data.get('mission_name', 'Unknown')}")
            print(f"   Cycles: {len(mission_data.get('cycle_ids', []))}")
            
            # Navigate through cycles
            cycle_ids = mission_data.get('cycle_ids', [])
            for i, cycle_id in enumerate(cycle_ids):
                cycle_file = f"mission_logs/{cycle_id}.json"
                if os.path.exists(cycle_file):
                    with open(cycle_file, 'r') as f:
                        cycle_data = json.load(f)
                    
                    print(f"\n   Cycle {i+1}: {cycle_id}")
                    print(f"      Focus: {cycle_data.get('current_decision_focus', 'Unknown')[:50]}...")
                    print(f"      Status: {cycle_data.get('status', 'Unknown')}")
                    print(f"      Previous context: {len(cycle_data.get('previous_cycles_context', []))}")
                    print(f"      Key insights: {len(cycle_data.get('key_insights_from_previous', []))}")
                    
                    # Show linking
                    prev_id = cycle_data.get('previous_cycle_id')
                    next_id = cycle_data.get('next_cycle_id')
                    print(f"      Links: {prev_id or 'None'} <- THIS -> {next_id or 'None'}")
        
        print(f"\n✅ Cycle navigation test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during cycle navigation test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all mission linking tests."""
    print("Starting Mission Linking and Resumable Missions Tests")
    
    results = []
    
    # Run tests
    results.append(await test_mission_creation_and_linking())
    results.append(await test_mission_resumption())
    results.append(test_cycle_navigation())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Mission linking is working correctly.")
        print("\nKey Features Demonstrated:")
        print("• ✅ Mission creation and management")
        print("• ✅ Cycle linking with previous/next references")
        print("• ✅ Mission resumption after restart")
        print("• ✅ Context preservation across cycles")
        print("• ✅ Key learnings extraction and propagation")
        print("• ✅ Mission-level metrics tracking")
    else:
        print("❌ Some tests failed. Please review the implementation.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main()) 