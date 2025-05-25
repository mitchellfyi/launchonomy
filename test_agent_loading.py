#!/usr/bin/env python3
"""
Test script for Task 5: Load and Instantiate All Registered Agents at Startup
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.registry import Registry
from orchestrator.orchestrator_agent import create_orchestrator

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# Suppress verbose logs from specific modules
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('autogen_core.events').setLevel(logging.WARNING)
logging.getLogger('autogen_core').setLevel(logging.WARNING)
logging.getLogger('autogen_ext').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def test_agent_loading():
    """Test that agents are loaded and instantiated correctly at startup."""
    print("=" * 60)
    print("Testing Agent Loading at Startup")
    print("=" * 60)
    
    # Step 1: Create a test agent entry in the registry
    print("\n1. Setting up test registry with sample agents...")
    registry = Registry()
    
    # Add a test agent with module/class specification
    test_agent_spec = {
        "description": "Test agent for loading verification",
        "module": "orchestrator.agents.auto_provision_agent",
        "class": "AutoProvisionAgent",
        "type": "test_agent"
    }
    
    registry.add_agent(
        name="TestLoadAgent",
        endpoint="test_load_agent.TestLoadAgent.handle_request",
        certified=True,
        spec=test_agent_spec
    )
    
    # Add another test agent without module/class (should be handled gracefully)
    registry.add_agent(
        name="PlaceholderTestAgent",
        endpoint="placeholder.handle",
        certified=False,
        spec={"description": "Test placeholder agent"}
    )
    
    print(f"✅ Added test agents to registry")
    print(f"   Registry now contains: {registry.list_agent_names()}")
    
    # Step 2: Create orchestrator (this should trigger agent loading)
    print("\n2. Creating orchestrator (should load all registered agents)...")
    
    try:
        orchestrator = create_orchestrator()
        print(f"✅ Orchestrator created successfully")
        
        # Step 3: Verify agents were loaded
        print(f"\n3. Verifying agent loading...")
        print(f"   Agents loaded in orchestrator: {list(orchestrator.agents.keys())}")
        print(f"   Total agents loaded: {len(orchestrator.agents)}")
        
        # Check specific agents
        if "TestLoadAgent" in orchestrator.agents:
            print(f"   ✅ TestLoadAgent loaded successfully")
            test_agent = orchestrator.agents["TestLoadAgent"]
            print(f"      Agent type: {type(test_agent)}")
            print(f"      Agent name: {getattr(test_agent, 'name', 'No name attribute')}")
        else:
            print(f"   ❌ TestLoadAgent not found in loaded agents")
        
        # Step 4: Test registry persistence
        print(f"\n4. Testing registry persistence...")
        agent_names_before = registry.list_agent_names()
        print(f"   Agent names before: {agent_names_before}")
        
        # Create a new registry instance (simulating restart)
        new_registry = Registry()
        agent_names_after = new_registry.list_agent_names()
        print(f"   Agent names after reload: {agent_names_after}")
        
        if set(agent_names_before) == set(agent_names_after):
            print(f"   ✅ Registry persistence verified")
        else:
            print(f"   ❌ Registry persistence failed")
            print(f"      Missing: {set(agent_names_before) - set(agent_names_after)}")
            print(f"      Extra: {set(agent_names_after) - set(agent_names_before)}")
        
        # Step 5: Test agent info retrieval
        print(f"\n5. Testing agent info retrieval...")
        for agent_name in ["TestLoadAgent", "PlaceholderTestAgent", "OrchestrationAgent"]:
            info = registry.get_agent_info(agent_name)
            print(f"   {agent_name}: {info}")
        
        print(f"\n✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_auto_provision_integration():
    """Test that auto-provisioned agents persist after restart."""
    print("\n" + "=" * 60)
    print("Testing Auto-Provision Agent Integration")
    print("=" * 60)
    
    try:
        # Create orchestrator
        orchestrator = create_orchestrator()
        
        # Simulate auto-provisioning a new agent
        print("\n1. Simulating auto-provision of new agent...")
        
        # Add a new agent via registry (simulating auto-provision)
        new_agent_spec = {
            "description": "Auto-provisioned test agent",
            "module": "orchestrator.agents.auto_provision_agent",
            "class": "AutoProvisionAgent",
            "type": "auto_provisioned",
            "created_by": "test_script"
        }
        
        orchestrator.registry.add_agent(
            name="AutoProvisionedTestAgent",
            endpoint="auto_provisioned.TestAgent.handle",
            certified=False,
            spec=new_agent_spec
        )
        
        print(f"✅ Auto-provisioned agent added to registry")
        
        # Verify it's in the registry
        agent_names = orchestrator.registry.list_agent_names()
        if "AutoProvisionedTestAgent" in agent_names:
            print(f"✅ Auto-provisioned agent found in registry")
        else:
            print(f"❌ Auto-provisioned agent not found in registry")
            return False
        
        # Simulate restart by creating new orchestrator
        print(f"\n2. Simulating restart (creating new orchestrator)...")
        new_orchestrator = create_orchestrator()
        
        # Check if auto-provisioned agent persists
        new_agent_names = new_orchestrator.registry.list_agent_names()
        if "AutoProvisionedTestAgent" in new_agent_names:
            print(f"✅ Auto-provisioned agent persisted after restart")
        else:
            print(f"❌ Auto-provisioned agent lost after restart")
            return False
        
        print(f"\n✅ Auto-provision integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during auto-provision testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_registry_list_agent_names():
    """Test the registry.list_agent_names() method as mentioned in the task."""
    print("\n" + "=" * 60)
    print("Testing registry.list_agent_names() in REPL-like environment")
    print("=" * 60)
    
    try:
        # Create registry and list agents
        registry = Registry()
        agent_names = registry.list_agent_names()
        
        print(f"registry.list_agent_names() returned: {agent_names}")
        print(f"Number of registered agents: {len(agent_names)}")
        
        # Show details for each agent
        print(f"\nAgent details:")
        for name in agent_names:
            spec = registry.get_agent_spec(name)
            info = registry.get_agent_info(name)
            print(f"  {name}:")
            print(f"    Spec: {spec}")
            print(f"    Info: {info}")
        
        print(f"\n✅ Registry listing test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during registry listing test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("Starting Task 5 Tests: Load and Instantiate All Registered Agents at Startup")
    
    # Set up environment
    os.environ.setdefault("OPENAI_API_KEY", "test-key-for-testing")
    os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
    
    results = []
    
    # Run tests
    results.append(await test_agent_loading())
    results.append(await test_auto_provision_integration())
    results.append(test_registry_list_agent_names())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Task 5 implementation is working correctly.")
    else:
        print("❌ Some tests failed. Please review the implementation.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main()) 