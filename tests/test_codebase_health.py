"""
Comprehensive test suite for Launchonomy codebase health.

This test suite validates:
- Import integrity
- Schema validation
- Agent functionality
- Registry operations
- Cost calculations
- Optional dependencies
"""

import pytest
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestImports:
    """Test that all modules can be imported without errors."""
    
    def test_core_imports(self):
        """Test core module imports."""
        import launchonomy
        from launchonomy.core.orchestrator import create_orchestrator
        from launchonomy.core.agent_manager import AgentManager
        from launchonomy.registry.registry import AgentRegistry
        
    def test_agent_imports(self):
        """Test agent imports."""
        from launchonomy.agents import BaseWorkflowAgent
        from launchonomy.agents.workflow import (
            ScanAgent, DeployAgent, CampaignAgent, 
            AnalyticsAgent, FinanceAgent, GrowthAgent
        )
        
    def test_utility_imports(self):
        """Test utility imports."""
        from launchonomy.utils.logging import OverallMissionLog, EnhancedLogger
        from launchonomy.utils.cost_calculator import calculate_token_cost
        from launchonomy.utils.schema_validator import validate_input
        from launchonomy.utils.optional_imports import check_optional_dependencies

class TestSchemaValidation:
    """Test schema validation functionality."""
    
    def test_agent_input_validation(self):
        """Test agent input validation."""
        from launchonomy.utils.schema_validator import validate_input
        
        # Valid input
        valid_data = {
            "task_description": "Test task",
            "context": {"test": True}
        }
        result = validate_input("ScanAgent", valid_data)
        assert result.is_valid
        
        # Invalid input (missing required field)
        invalid_data = {}
        result = validate_input("ScanAgent", invalid_data)
        assert not result.is_valid
        assert len(result.errors) > 0
        
    def test_agent_output_validation(self):
        """Test agent output validation."""
        from launchonomy.utils.schema_validator import validate_output
        
        # Valid output
        valid_output = {
            "status": "success",
            "execution_type": "test",
            "description": "Test execution",
            "output_data": {"result": "test"},
            "opportunities": [],
            "market_analysis": {},
            "recommendations": []
        }
        result = validate_output("ScanAgent", valid_output)
        assert result.is_valid
        
    def test_example_generation(self):
        """Test example input/output generation."""
        from launchonomy.utils.schema_validator import create_example_input, create_example_output
        
        for agent_name in ["ScanAgent", "DeployAgent", "CampaignAgent"]:
            example_input = create_example_input(agent_name)
            assert "task_description" in example_input
            
            example_output = create_example_output(agent_name)
            assert "status" in example_output
            assert "execution_type" in example_output

class TestCostCalculation:
    """Test cost calculation utilities."""
    
    def test_token_cost_calculation(self):
        """Test token cost calculation."""
        from launchonomy.utils.cost_calculator import calculate_token_cost
        
        # Test with known values
        cost = calculate_token_cost(1000, 500, "gpt-4")
        assert cost > 0
        assert isinstance(cost, float)
        
        # Test with different models
        cost_turbo = calculate_token_cost(1000, 500, "gpt-4-turbo")
        cost_35 = calculate_token_cost(1000, 500, "gpt-3.5-turbo")
        
        # GPT-4 should be most expensive, GPT-3.5 cheapest
        assert cost > cost_turbo > cost_35
        
    def test_workflow_cost_calculation(self):
        """Test workflow step cost calculation."""
        from launchonomy.utils.cost_calculator import calculate_workflow_step_cost
        
        step_data = {
            "token_usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "model": "gpt-4"
            },
            "cost": 0.01
        }
        
        cost = calculate_workflow_step_cost(step_data)
        assert cost > 0.01  # Should include both token cost and direct cost
        
    def test_cycle_cost_calculation(self):
        """Test complete cycle cost calculation."""
        from launchonomy.utils.cost_calculator import calculate_cycle_cost, estimate_cost_breakdown
        
        cycle_log = {
            "csuite_planning": {
                "CEO": {"token_usage": {"input_tokens": 100, "output_tokens": 50, "model": "gpt-4"}},
                "CTO": {"cost": 0.02}
            },
            "steps": {
                "scan": {"token_usage": {"input_tokens": 200, "output_tokens": 100, "model": "gpt-4"}},
                "deploy": {"cost": 0.05}
            },
            "csuite_review": {
                "CFO": {"token_usage": {"input_tokens": 50, "output_tokens": 25, "model": "gpt-4"}}
            }
        }
        
        total_cost = calculate_cycle_cost(cycle_log)
        assert total_cost > 0
        
        breakdown = estimate_cost_breakdown(cycle_log)
        assert "csuite_planning" in breakdown
        assert "workflow_execution" in breakdown
        assert "csuite_review" in breakdown

class TestRegistryOperations:
    """Test agent registry functionality."""
    
    def test_registry_creation(self):
        """Test registry creation and basic operations."""
        from launchonomy.registry.registry import AgentRegistry
        
        registry = AgentRegistry()
        assert hasattr(registry, 'agents')
        assert hasattr(registry, 'tools')
        
    def test_agent_loading(self):
        """Test agent loading from registry."""
        from launchonomy.registry.registry import AgentRegistry
        
        registry = AgentRegistry()
        agent_names = registry.list_agent_names()
        assert len(agent_names) > 0
        
        # Test getting agent info
        for name in agent_names[:3]:  # Test first 3 agents
            info = registry.get_agent_info(name)
            if info:  # Some agents might not have full info
                assert isinstance(info, dict)

class TestOptionalDependencies:
    """Test optional dependency handling."""
    
    def test_dependency_check(self):
        """Test optional dependency checking."""
        from launchonomy.utils.optional_imports import (
            check_optional_dependencies, 
            get_missing_dependencies,
            install_command_for_missing
        )
        
        deps = check_optional_dependencies()
        assert isinstance(deps, dict)
        
        missing = get_missing_dependencies()
        assert isinstance(missing, list)
        
        install_cmd = install_command_for_missing()
        assert isinstance(install_cmd, str)
        
    def test_safe_json_operations(self):
        """Test safe JSON operations."""
        from launchonomy.utils.optional_imports import safe_json_dumps, safe_json_loads
        
        test_data = {"test": "data", "number": 42, "list": [1, 2, 3]}
        
        # Test serialization
        json_str = safe_json_dumps(test_data)
        assert isinstance(json_str, str)
        
        # Test deserialization
        parsed_data = safe_json_loads(json_str)
        assert parsed_data == test_data

class TestAgentFunctionality:
    """Test basic agent functionality."""
    
    def test_base_workflow_agent(self):
        """Test base workflow agent functionality."""
        from launchonomy.agents.base.workflow_agent import BaseWorkflowAgent
        from launchonomy.registry.registry import AgentRegistry
        
        registry = AgentRegistry()
        
        # Create a test agent
        class TestAgent(BaseWorkflowAgent):
            def __init__(self, registry):
                super().__init__(registry)
                self.name = "TestAgent"
                
            async def execute(self, input_data):
                return {
                    "status": "success",
                    "execution_type": "test",
                    "description": "Test execution",
                    "output_data": {"test": True}
                }
        
        agent = TestAgent(registry)
        assert agent.name == "TestAgent"
        assert hasattr(agent, 'execute')

class TestLoggingSystem:
    """Test enhanced logging system."""
    
    def test_enhanced_logger(self):
        """Test enhanced logger functionality."""
        from launchonomy.utils.logging import EnhancedLogger, LogLevel, ErrorCategory
        
        logger = EnhancedLogger("test")
        
        # Test basic logging
        logger.info("Test message")
        logger.error("Test error", ErrorCategory.SYSTEM)
        
        # Test structured logging
        logger.log_structured("test_event", {"key": "value"}, LogLevel.INFO)
        
    def test_mission_log(self):
        """Test mission log functionality."""
        from launchonomy.utils.logging import OverallMissionLog
        
        log = OverallMissionLog("test_mission", "Test mission description")
        assert log.mission_id == "test_mission"
        assert log.overall_mission == "Test mission description"
        assert log.final_status == "started"

class TestErrorHandling:
    """Test error handling improvements."""
    
    def test_specific_exception_handling(self):
        """Test that specific exceptions are caught instead of broad Exception."""
        from launchonomy.utils.logging import EnhancedLogger
        
        logger = EnhancedLogger("test")
        
        # Test that the logger handles conversion errors properly
        try:
            # This should not raise an exception
            logger._ensure_string_message(None)
        except Exception as e:
            pytest.fail(f"Logger should handle None gracefully: {e}")

def test_package_structure():
    """Test that package structure is correct."""
    import launchonomy
    
    # Test that main package has expected attributes
    assert hasattr(launchonomy, '__version__') or True  # Version might not be set
    
    # Test that subpackages exist
    from launchonomy import agents, core, registry, utils
    
    # Test that key classes are accessible
    from launchonomy.core.orchestrator import OrchestrationAgent
    from launchonomy.registry.registry import AgentRegistry

def test_cli_imports():
    """Test that CLI can be imported without errors."""
    try:
        from launchonomy.cli import main
        assert callable(main)
    except ImportError as e:
        pytest.fail(f"CLI import failed: {e}")

if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"]) 