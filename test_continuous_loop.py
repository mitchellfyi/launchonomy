#!/usr/bin/env python3
"""
Test script for the Continuous Launch & Growth Loop functionality.

This script tests the new continuous loop implementation that uses dynamic agent calls
through the registry system as specified in Task 3.
"""

import asyncio
import os
import sys
import logging
from datetime import datetime

# Add the orchestrator directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'orchestrator'))

from orchestrator_agent import create_orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_continuous_loop():
    """Test the continuous launch and growth loop functionality."""
    
    print("=" * 60)
    print("Testing Continuous Launch & Growth Loop")
    print("=" * 60)
    
    try:
        # Create orchestrator instance
        print("Creating orchestrator...")
        orchestrator = create_orchestrator()
        
        # Define test mission context
        mission_context = {
            "overall_mission": "Build and launch a profitable SaaS application for small businesses",
            "constraints": {
                "budget_limit": 1000.0,
                "timeline": "30 days",
                "target_market": "small businesses"
            }
        }
        
        print(f"Mission: {mission_context['overall_mission']}")
        print(f"Budget Limit: ${mission_context['constraints']['budget_limit']}")
        print()
        
        # Test the continuous mode execution
        print("Starting continuous mode execution...")
        print("(Limited to 3 iterations for testing)")
        
        results = await orchestrator.execute_continuous_mode(
            mission_context=mission_context,
            max_iterations=3  # Limited for testing
        )
        
        print("\n" + "=" * 60)
        print("EXECUTION RESULTS")
        print("=" * 60)
        
        print(f"Mode: {results.get('mode', 'unknown')}")
        print(f"Status: {results.get('status', 'unknown')}")
        print(f"Message: {results.get('message', 'No message')}")
        
        if 'loop_results' in results:
            loop_results = results['loop_results']
            print(f"\nLoop Summary:")
            print(f"  Total Iterations: {loop_results.get('total_iterations', 0)}")
            print(f"  Successful Cycles: {loop_results.get('successful_cycles', 0)}")
            print(f"  Failed Cycles: {loop_results.get('failed_cycles', 0)}")
            print(f"  Total Revenue: ${loop_results.get('total_revenue_generated', 0.0):.2f}")
            print(f"  Guardrail Breaches: {loop_results.get('guardrail_breaches', 0)}")
            print(f"  Final Status: {loop_results.get('final_status', 'unknown')}")
            
            # Show execution log summary
            if 'execution_log' in loop_results:
                print(f"\nExecution Log ({len(loop_results['execution_log'])} cycles):")
                for i, cycle in enumerate(loop_results['execution_log'], 1):
                    print(f"  Cycle {i}:")
                    print(f"    Revenue: ${cycle.get('revenue_generated', 0.0):.2f}")
                    print(f"    Steps Completed: {len(cycle.get('steps', {}))}")
                    if cycle.get('errors'):
                        print(f"    Errors: {len(cycle['errors'])}")
                        for error in cycle['errors'][:2]:  # Show first 2 errors
                            print(f"      - {error[:100]}...")
        
        if 'error' in results:
            print(f"\nError Details: {results['error']}")
        
        print("\n" + "=" * 60)
        print("Test completed successfully!")
        
        return results
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        logger.error(f"Test execution failed: {str(e)}", exc_info=True)
        return None

async def test_registry_agent_access():
    """Test that agents can be accessed through the registry."""
    
    print("\n" + "=" * 60)
    print("Testing Registry Agent Access")
    print("=" * 60)
    
    try:
        orchestrator = create_orchestrator()
        
        # Test accessing each workflow agent
        agent_names = ["ScanAgent", "DeployAgent", "CampaignAgent", "AnalyticsAgent", "FinanceAgent", "GrowthAgent"]
        
        mission_context = {"overall_mission": "Test mission"}
        
        for agent_name in agent_names:
            print(f"Testing {agent_name}...")
            
            # Check if agent is in registry
            agent_spec = orchestrator.registry.get_agent_spec(agent_name)
            if agent_spec:
                print(f"  ✓ Found in registry: {agent_spec.get('spec', {}).get('description', 'No description')}")
                
                # Try to instantiate the agent
                agent = orchestrator.registry.get_agent(agent_name, mission_context)
                if agent:
                    print(f"  ✓ Successfully instantiated")
                    
                    # Test if agent has execute method
                    if hasattr(agent, 'execute'):
                        print(f"  ✓ Has execute method")
                    else:
                        print(f"  ⚠ Missing execute method")
                else:
                    print(f"  ✗ Failed to instantiate")
            else:
                print(f"  ✗ Not found in registry")
            
            print()
        
        print("Registry agent access test completed!")
        
    except Exception as e:
        print(f"Registry test failed: {str(e)}")
        logger.error(f"Registry test failed: {str(e)}", exc_info=True)

def main():
    """Main test function."""
    print("Continuous Launch & Growth Loop Test Suite")
    print(f"Started at: {datetime.now().isoformat()}")
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Some tests may fail.")
    
    # Run tests
    asyncio.run(test_registry_agent_access())
    asyncio.run(test_continuous_loop())
    
    print(f"\nTest suite completed at: {datetime.now().isoformat()}")

if __name__ == "__main__":
    main() 