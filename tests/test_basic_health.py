#!/usr/bin/env python3
"""
Basic codebase health test without external dependencies.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all core modules can be imported."""
    print("Testing imports...")
    
    try:
        import launchonomy
        print("✅ launchonomy package imported")
    except ImportError as e:
        print(f"❌ Failed to import launchonomy: {e}")
        return False
    
    try:
        from launchonomy.core.orchestrator import create_orchestrator
        print("✅ orchestrator imported")
    except ImportError as e:
        print(f"❌ Failed to import orchestrator: {e}")
        return False
    
    try:
        from launchonomy.registry.registry import Registry
        print("✅ registry imported")
    except ImportError as e:
        print(f"❌ Failed to import registry: {e}")
        return False
    
    try:
        from launchonomy.utils.logging import OverallMissionLog
        print("✅ logging utils imported")
    except ImportError as e:
        print(f"❌ Failed to import logging utils: {e}")
        return False
    
    try:
        from launchonomy.utils.cost_calculator import calculate_token_cost
        print("✅ cost calculator imported")
    except ImportError as e:
        print(f"❌ Failed to import cost calculator: {e}")
        return False
    
    try:
        from launchonomy.utils.schema_validator import validate_input
        print("✅ schema validator imported")
    except ImportError as e:
        print(f"❌ Failed to import schema validator: {e}")
        return False
    
    try:
        from launchonomy.utils.optional_imports import check_optional_dependencies
        print("✅ optional imports imported")
    except ImportError as e:
        print(f"❌ Failed to import optional imports: {e}")
        return False
    
    return True

def test_agent_imports():
    """Test agent imports."""
    print("\nTesting agent imports...")
    
    try:
        from launchonomy.agents import BaseWorkflowAgent
        print("✅ BaseWorkflowAgent imported")
    except ImportError as e:
        print(f"❌ Failed to import BaseWorkflowAgent: {e}")
        return False
    
    try:
        from launchonomy.agents.workflow import (
            ScanAgent, DeployAgent, CampaignAgent, 
            AnalyticsAgent, FinanceAgent, GrowthAgent
        )
        print("✅ All workflow agents imported")
    except ImportError as e:
        print(f"❌ Failed to import workflow agents: {e}")
        return False
    
    return True

def test_registry_functionality():
    """Test basic registry functionality."""
    print("\nTesting registry functionality...")
    
    try:
        from launchonomy.registry.registry import Registry
        
        registry = Registry()
        agent_names = registry.list_agent_names()
        print(f"✅ Registry loaded with {len(agent_names)} agents")
        
        if len(agent_names) == 0:
            print("⚠️ Warning: No agents found in registry")
            return False
        
        # Test getting agent info for first few agents
        for name in agent_names[:3]:
            info = registry.get_agent_info(name)
            if info:
                print(f"✅ Agent {name} has valid info")
            else:
                print(f"⚠️ Agent {name} has no info")
        
        return True
        
    except Exception as e:
        print(f"❌ Registry test failed: {e}")
        return False

def test_cost_calculation():
    """Test cost calculation functionality."""
    print("\nTesting cost calculation...")
    
    try:
        from launchonomy.utils.cost_calculator import calculate_token_cost, calculate_cycle_cost
        
        # Test token cost calculation
        cost = calculate_token_cost(1000, 500, "gpt-4")
        if cost > 0:
            print(f"✅ Token cost calculation works: ${cost:.4f}")
        else:
            print("❌ Token cost calculation returned 0")
            return False
        
        # Test cycle cost calculation
        cycle_log = {
            "csuite_planning": {
                "CEO": {"token_usage": {"input_tokens": 100, "output_tokens": 50, "model": "gpt-4"}}
            },
            "steps": {
                "scan": {"cost": 0.05}
            }
        }
        
        cycle_cost = calculate_cycle_cost(cycle_log)
        if cycle_cost > 0:
            print(f"✅ Cycle cost calculation works: ${cycle_cost:.4f}")
        else:
            print("❌ Cycle cost calculation returned 0")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Cost calculation test failed: {e}")
        return False

def test_schema_validation():
    """Test schema validation functionality."""
    print("\nTesting schema validation...")
    
    try:
        from launchonomy.utils.schema_validator import validate_input, create_example_input
        
        # Test valid input
        valid_data = {
            "task_description": "Test task",
            "context": {"test": True}
        }
        result = validate_input("ScanAgent", valid_data)
        if result.is_valid:
            print("✅ Valid input validation works")
        else:
            print(f"❌ Valid input validation failed: {result.errors}")
            return False
        
        # Test invalid input
        invalid_data = {}
        result = validate_input("ScanAgent", invalid_data)
        if not result.is_valid:
            print("✅ Invalid input validation works")
        else:
            print("❌ Invalid input validation should have failed")
            return False
        
        # Test example generation
        example = create_example_input("ScanAgent")
        if "task_description" in example:
            print("✅ Example input generation works")
        else:
            print("❌ Example input generation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Schema validation test failed: {e}")
        return False

def test_optional_dependencies():
    """Test optional dependency handling."""
    print("\nTesting optional dependencies...")
    
    try:
        from launchonomy.utils.optional_imports import (
            check_optional_dependencies, 
            get_missing_dependencies,
            safe_json_dumps,
            safe_json_loads
        )
        
        # Test dependency check
        deps = check_optional_dependencies()
        missing = get_missing_dependencies()
        print(f"✅ Dependency check works: {len(missing)} missing dependencies")
        
        # Test safe JSON operations
        test_data = {"test": "data", "number": 42}
        json_str = safe_json_dumps(test_data)
        parsed_data = safe_json_loads(json_str)
        
        if parsed_data == test_data:
            print("✅ Safe JSON operations work")
        else:
            print("❌ Safe JSON operations failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Optional dependencies test failed: {e}")
        return False

def test_cli_import():
    """Test CLI import."""
    print("\nTesting CLI import...")
    
    try:
        from launchonomy.cli import main
        if callable(main):
            print("✅ CLI main function imported")
            return True
        else:
            print("❌ CLI main is not callable")
            return False
    except ImportError as e:
        print(f"❌ CLI import failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🔍 Running Launchonomy Codebase Health Check")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_agent_imports,
        test_registry_functionality,
        test_cost_calculation,
        test_schema_validation,
        test_optional_dependencies,
        test_cli_import
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Codebase is healthy.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 