#!/usr/bin/env python3
"""
Test suite to ensure C-Suite agents are properly separated from the registry.

This test verifies that:
1. C-Suite agents are not added to the persistent registry
2. C-Suite agents exist only in AgentManager during missions
3. Registry listings remain clean of C-Suite agents
4. C-Suite agents can still be accessed for strategic operations
"""

import asyncio
import tempfile
import os
import json
from unittest.mock import patch

# Try to import pytest, but make it optional
try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    # Create a dummy pytest module for basic functionality
    class DummyPytest:
        class mark:
            @staticmethod
            def asyncio(func):
                return func
        
        @staticmethod
        def fixture(func):
            return func
    
    pytest = DummyPytest()

from launchonomy.core.orchestrator import create_orchestrator
from launchonomy.registry.registry import Registry


class TestCSuiteRegistrySeparation:
    """Test C-Suite agent registry separation."""
    
    def create_temp_registry_file(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            # Create a minimal registry with only workflow agents
            test_registry = {
                "agents": {
                    "OrchestrationAgent": {
                        "endpoint": "internal",
                        "certified": True,
                        "spec": {"description": "Main orchestrator"}
                    },
                    "AutoProvisionAgent": {
                        "endpoint": "auto_provision_agent.AutoProvisionAgent.handle_trivial_request",
                        "certified": True,
                        "spec": {"description": "Auto-provisioning agent"}
                    },
                    "ScanAgent": {
                        "module": "launchonomy.agents.workflow.scan",
                        "class": "ScanAgent",
                        "certified": True,
                        "spec": {"description": "Market scanning agent", "type": "workflow_agent"}
                    }
                },
                "tools": {}
            }
            json.dump(test_registry, f, indent=2)
            return f.name
    
    async def test_csuite_not_in_registry_after_bootstrap(self):
        """Test that C-Suite agents are not added to registry during bootstrap."""
        
        temp_registry_file = self.create_temp_registry_file()
        
        try:
            # Create registry with temp file
            with patch('launchonomy.registry.registry.DEFAULT_REGISTRY_FILE', temp_registry_file):
                registry = Registry()
                
                # Verify initial state - no C-Suite agents in registry
                initial_agents = registry.list_agent_names()
                csuite_agents = [name for name in initial_agents if name.endswith('-Agent')]
                assert len(csuite_agents) == 0, f"Registry should not contain C-Suite agents initially, found: {csuite_agents}"
                
                # Create orchestrator (this will use our temp registry)
                orchestrator = create_orchestrator()
                orchestrator.registry = registry  # Use our test registry
                
                # Bootstrap C-Suite
                await orchestrator.bootstrap_c_suite("Test mission for registry separation")
                
                # Verify C-Suite agents are NOT in registry after bootstrap
                post_bootstrap_registry_agents = registry.list_agent_names()
                csuite_in_registry = [name for name in post_bootstrap_registry_agents if name.endswith('-Agent')]
                assert len(csuite_in_registry) == 0, f"C-Suite agents should NOT be in registry after bootstrap, found: {csuite_in_registry}"
                
                # Verify C-Suite agents ARE in AgentManager
                agent_manager_agents = list(orchestrator.agents.keys())
                csuite_in_agent_manager = [name for name in agent_manager_agents if name.endswith('-Agent')]
                expected_csuite = ["CEO-Agent", "CRO-Agent", "CTO-Agent", "CPO-Agent", "CMO-Agent", "CDO-Agent", "CCO-Agent", "CFO-Agent", "CCSO-Agent"]
                
                assert len(csuite_in_agent_manager) == len(expected_csuite), f"Expected {len(expected_csuite)} C-Suite agents in AgentManager, found {len(csuite_in_agent_manager)}"
                
                for expected_agent in expected_csuite:
                    assert expected_agent in csuite_in_agent_manager, f"Expected C-Suite agent {expected_agent} not found in AgentManager"
                
                print("✅ test_csuite_not_in_registry_after_bootstrap passed")
                
        finally:
            if os.path.exists(temp_registry_file):
                os.unlink(temp_registry_file)
    
    async def test_registry_persistence_excludes_csuite(self):
        """Test that registry save/load operations don't include C-Suite agents."""
        
        temp_registry_file = self.create_temp_registry_file()
        
        try:
            with patch('launchonomy.registry.registry.DEFAULT_REGISTRY_FILE', temp_registry_file):
                # Create orchestrator and bootstrap C-Suite
                orchestrator = create_orchestrator()
                registry = Registry()
                orchestrator.registry = registry
                
                await orchestrator.bootstrap_c_suite("Test mission")
                
                # Force registry save
                registry.save()
                
                # Create new registry instance and load from file
                new_registry = Registry()
                loaded_agents = new_registry.list_agent_names()
                
                # Verify no C-Suite agents in loaded registry
                csuite_in_loaded = [name for name in loaded_agents if name.endswith('-Agent')]
                assert len(csuite_in_loaded) == 0, f"Loaded registry should not contain C-Suite agents, found: {csuite_in_loaded}"
                
                print("✅ test_registry_persistence_excludes_csuite passed")
                
        finally:
            if os.path.exists(temp_registry_file):
                os.unlink(temp_registry_file)
    
    async def test_csuite_agents_functional_but_not_persistent(self):
        """Test that C-Suite agents are functional but not persistent."""
        
        temp_registry_file = self.create_temp_registry_file()
        
        try:
            with patch('launchonomy.registry.registry.DEFAULT_REGISTRY_FILE', temp_registry_file):
                orchestrator = create_orchestrator()
                registry = Registry()
                orchestrator.registry = registry
                
                # Bootstrap C-Suite
                await orchestrator.bootstrap_c_suite("Test mission")
                
                # Verify C-Suite agents are accessible and functional
                ceo_agent = orchestrator.agents.get("CEO-Agent")
                assert ceo_agent is not None, "CEO-Agent should be accessible in AgentManager"
                assert hasattr(ceo_agent, 'name'), "CEO-Agent should have name attribute"
                assert ceo_agent.name == "CEO-Agent", "CEO-Agent should have correct name"
                
                # Verify C-Suite agent is NOT in registry
                ceo_spec = registry.get_agent_spec("CEO-Agent")
                assert ceo_spec is None, "CEO-Agent should NOT have a registry specification"
                
                # Verify registry.get_agent() returns None for C-Suite agents
                ceo_from_registry = registry.get_agent("CEO-Agent")
                assert ceo_from_registry is None, "Registry should not be able to instantiate C-Suite agents"
                
                print("✅ test_csuite_agents_functional_but_not_persistent passed")
                
        finally:
            if os.path.exists(temp_registry_file):
                os.unlink(temp_registry_file)
    
    async def test_multiple_bootstrap_calls_safe(self):
        """Test that multiple bootstrap calls don't cause registry pollution."""
        
        temp_registry_file = self.create_temp_registry_file()
        
        try:
            with patch('launchonomy.registry.registry.DEFAULT_REGISTRY_FILE', temp_registry_file):
                orchestrator = create_orchestrator()
                registry = Registry()
                orchestrator.registry = registry
                
                # Bootstrap C-Suite multiple times
                await orchestrator.bootstrap_c_suite("Test mission 1")
                initial_registry_agents = set(registry.list_agent_names())
                
                await orchestrator.bootstrap_c_suite("Test mission 2")
                second_registry_agents = set(registry.list_agent_names())
                
                await orchestrator.bootstrap_c_suite("Test mission 3")
                third_registry_agents = set(registry.list_agent_names())
                
                # Registry should remain unchanged across multiple bootstrap calls
                assert initial_registry_agents == second_registry_agents == third_registry_agents, \
                    "Registry agent list should remain stable across multiple C-Suite bootstrap calls"
                
                # No C-Suite agents should be in any of the registry snapshots
                for agent_set in [initial_registry_agents, second_registry_agents, third_registry_agents]:
                    csuite_in_set = [name for name in agent_set if name.endswith('-Agent')]
                    assert len(csuite_in_set) == 0, f"No C-Suite agents should be in registry, found: {csuite_in_set}"
                
                print("✅ test_multiple_bootstrap_calls_safe passed")
                
        finally:
            if os.path.exists(temp_registry_file):
                os.unlink(temp_registry_file)


async def run_all_tests():
    """Run all C-Suite registry separation tests."""
    print("🧪 Running C-Suite Registry Separation Tests")
    print("=" * 50)
    
    test_suite = TestCSuiteRegistrySeparation()
    
    try:
        await test_suite.test_csuite_not_in_registry_after_bootstrap()
        await test_suite.test_registry_persistence_excludes_csuite()
        await test_suite.test_csuite_agents_functional_but_not_persistent()
        await test_suite.test_multiple_bootstrap_calls_safe()
        
        print("\n🎉 All C-Suite registry separation tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_csuite_registry_separation_integration():
    """Integration test for C-Suite registry separation."""
    
    async def test_csuite_separation_async():
        """Async integration test."""
        # Create temporary registry
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_registry = {
                "agents": {
                    "OrchestrationAgent": {
                        "endpoint": "internal",
                        "certified": True,
                        "spec": {"description": "Main orchestrator"}
                    }
                },
                "tools": {}
            }
            json.dump(test_registry, f, indent=2)
            temp_file = f.name
        
        try:
            with patch('launchonomy.registry.registry.DEFAULT_REGISTRY_FILE', temp_file):
                # Test the complete flow
                orchestrator = create_orchestrator()
                
                # Before bootstrap
                pre_bootstrap_registry = set(orchestrator.registry.list_agent_names())
                pre_bootstrap_agents = set(orchestrator.agents.keys())
                
                # Bootstrap
                await orchestrator.bootstrap_c_suite("Integration test mission")
                
                # After bootstrap
                post_bootstrap_registry = set(orchestrator.registry.list_agent_names())
                post_bootstrap_agents = set(orchestrator.agents.keys())
                
                # Assertions
                assert pre_bootstrap_registry == post_bootstrap_registry, \
                    "Registry should be unchanged by C-Suite bootstrap"
                
                assert len(post_bootstrap_agents) > len(pre_bootstrap_agents), \
                    "AgentManager should have more agents after bootstrap"
                
                csuite_agents = [name for name in post_bootstrap_agents if name.endswith('-Agent')]
                assert len(csuite_agents) == 9, f"Should have 9 C-Suite agents, found {len(csuite_agents)}"
                
                return True
                
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    # Run the test
    result = asyncio.run(test_csuite_separation_async())
    assert result is True, "Integration test should pass"
    return result


if __name__ == "__main__":
    # Run tests when called directly
    if PYTEST_AVAILABLE:
        print("✅ pytest is available - you can run: pytest tests/test_csuite_registry_separation.py")
    
    print("🧪 Running basic integration test...")
    
    try:
        # Run basic integration test
        test_csuite_registry_separation_integration()
        print("✅ Integration test passed!")
        
        # Run comprehensive test suite
        result = asyncio.run(run_all_tests())
        
        if result:
            print("\n🎉 All C-Suite registry separation tests completed successfully!")
            print("✅ C-Suite agents are properly separated from the registry.")
        else:
            print("\n❌ Some tests failed!")
            exit(1)
            
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1) 