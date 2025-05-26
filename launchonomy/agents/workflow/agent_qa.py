import logging
import os
import json
import importlib
import sys
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class AgentQA:
    """
    AgentQA specializes in testing and validating newly built agents.
    
    Responsibilities:
    1. Monitor registry for "built" agents that need testing
    2. Run sandbox test suites against new agent implementations
    3. Validate functionality, error handling, and workflow compliance
    4. Log test results and suggest refinements
    5. Propose certification via consensus if tests pass
    """
    
    def __init__(self, registry, orchestrator, mission_context: Optional[Dict[str, Any]] = None):
        """
        Initialize AgentQA.
        
        Args:
            registry: Registry instance for managing agents/tools
            orchestrator: OrchestrationAgent instance
            mission_context: Mission context including workspace information
        """
        self.registry = registry
        self.orchestrator = orchestrator
        self.mission_context = mission_context or {}
        self.name = "AgentQA"
        
    def _log(self, message: str, level: str = "info"):
        """Helper for logging."""
        log_func = getattr(logger, level, logger.info)
        log_func(f"{self.name}: {message}")
        if hasattr(self.orchestrator, '_log_to_monitor') and callable(self.orchestrator._log_to_monitor):
            self.orchestrator._log_to_monitor(self.name, message, level)
    
    def execute(self) -> Dict[str, Any]:
        """
        Main execution method for AgentQA.
        
        Returns:
            Dict containing test results and certification proposals
        """
        self._log("Starting AgentQA execution - testing built agents", "info")
        
        results = {
            "tested_agents": [],
            "certification_proposals": [],
            "errors": [],
            "status": "completed"
        }
        
        try:
            # Find built agents that need testing
            built_agents = self._find_built_agents()
            
            self._log(f"Found {len(built_agents)} built agents to test", "info")
            
            # Test built agents
            for agent_name, agent_spec in built_agents.items():
                try:
                    test_result = self._test_agent(agent_name, agent_spec)
                    results["tested_agents"].append(test_result)
                    
                    if test_result["passed"]:
                        # Propose certification
                        certification_proposal = self._create_certification_proposal("agent", agent_name, test_result)
                        results["certification_proposals"].append(certification_proposal)
                        self._submit_certification_proposal(certification_proposal)
                        
                except Exception as e:
                    error_msg = f"Error testing agent {agent_name}: {str(e)}"
                    self._log(error_msg, "error")
                    results["errors"].append(error_msg)
                    
        except Exception as e:
            error_msg = f"Critical error in AgentQA execution: {str(e)}"
            self._log(error_msg, "error")
            results["errors"].append(error_msg)
            results["status"] = "failed"
        
        self._log(f"AgentQA execution completed. Tested {len(results['tested_agents'])} agents", "info")
        return results
    
    def _find_built_agents(self) -> Dict[str, Dict[str, Any]]:
        """Find agents with 'built' status in registry."""
        built = {}
        for agent_name, agent_spec in self.registry.agents.items():
            if agent_spec.get("status") == "built":
                built[agent_name] = agent_spec
        return built
    
    def _test_agent(self, agent_name: str, agent_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a built agent implementation.
        
        Args:
            agent_name: Name of the agent to test
            agent_spec: Agent specification from registry
            
        Returns:
            Dict containing test results
        """
        self._log(f"Testing agent: {agent_name}", "info")
        
        test_result = {
            "name": agent_name,
            "type": "agent",
            "passed": False,
            "tests_run": [],
            "errors": [],
            "score": 0.0,
            "recommendations": []
        }
        
        try:
            # Load the agent implementation
            built_path = agent_spec.get("built_path")
            if not built_path or not os.path.exists(built_path):
                test_result["errors"].append(f"Built agent file not found: {built_path}")
                return test_result
            
            # Import the agent module
            agent_module = self._import_agent_module(built_path)
            if not agent_module:
                test_result["errors"].append("Failed to import agent module")
                return test_result
            
            # Find the agent class
            agent_class = self._find_agent_class(agent_module, agent_name)
            if not agent_class:
                test_result["errors"].append("Agent class not found in module")
                return test_result
            
            # Run test suite
            test_cases = self._get_agent_test_cases(agent_name, agent_spec)
            passed_tests = 0
            
            for test_case in test_cases:
                try:
                    test_passed = self._run_agent_test_case(agent_class, test_case)
                    test_result["tests_run"].append({
                        "name": test_case["name"],
                        "passed": test_passed,
                        "description": test_case["description"]
                    })
                    if test_passed:
                        passed_tests += 1
                        
                except Exception as e:
                    test_result["tests_run"].append({
                        "name": test_case["name"],
                        "passed": False,
                        "error": str(e),
                        "description": test_case["description"]
                    })
                    test_result["errors"].append(f"Test '{test_case['name']}' failed: {str(e)}")
            
            # Calculate score and determine pass/fail
            if test_cases:
                test_result["score"] = passed_tests / len(test_cases)
                test_result["passed"] = test_result["score"] >= 0.75  # 75% pass threshold
            
            # Generate recommendations
            if test_result["score"] < 1.0:
                test_result["recommendations"].append("Some tests failed - consider improving error handling")
            if test_result["score"] < 0.5:
                test_result["recommendations"].append("Major issues detected - requires significant improvements")
                
        except Exception as e:
            test_result["errors"].append(f"Critical testing error: {str(e)}")
            self._log(f"Error testing agent {agent_name}: {str(e)}", "error")
        
        self._log(f"Agent {agent_name} test completed. Score: {test_result['score']:.2f}, Passed: {test_result['passed']}", "info")
        return test_result
    
    def _import_agent_module(self, agent_path: str):
        """Import agent module from file path."""
        try:
            spec = importlib.util.spec_from_file_location("test_agent", agent_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            self._log(f"Error importing agent module from {agent_path}: {str(e)}", "error")
            return None
    
    def _find_agent_class(self, module, agent_name: str):
        """Find the agent class in the module."""
        # Look for classes ending with 'Agent'
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                attr_name.endswith('Agent') and 
                hasattr(attr, 'execute')):
                return attr
        return None
    
    def _get_agent_test_cases(self, agent_name: str, agent_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get test cases for an agent."""
        base_tests = [
            {
                "name": "basic_instantiation",
                "description": "Test that agent can be instantiated",
                "test_type": "instantiation"
            },
            {
                "name": "basic_execution",
                "description": "Test that agent execute method works",
                "test_type": "execution",
                "context": {"test": True}
            },
            {
                "name": "error_handling",
                "description": "Test agent error handling",
                "test_type": "error_handling",
                "context": None  # This should trigger error handling
            },
            {
                "name": "capabilities_check",
                "description": "Test that agent has required capabilities",
                "test_type": "capabilities"
            }
        ]
        
        # Add workflow-specific tests if this is a workflow agent
        workflow_step = agent_spec.get("spec", {}).get("workflow_step")
        if workflow_step:
            base_tests.extend([
                {
                    "name": "workflow_step_validation",
                    "description": "Test that agent returns correct workflow step",
                    "test_type": "workflow_step"
                },
                {
                    "name": "schema_compliance",
                    "description": "Test that agent output matches expected schema",
                    "test_type": "schema_compliance",
                    "context": {"mission_context": {"test": True}}
                }
            ])
        
        return base_tests
    
    def _run_agent_test_case(self, agent_class, test_case: Dict[str, Any]) -> bool:
        """Run a single test case for an agent."""
        try:
            if test_case["test_type"] == "instantiation":
                # Test instantiation
                agent = agent_class(self.registry, {})
                return agent is not None
                
            elif test_case["test_type"] == "execution":
                # Test execution
                agent = agent_class(self.registry, {})
                result = agent.execute(test_case.get("context"))
                return isinstance(result, dict) and "status" in result
                
            elif test_case["test_type"] == "error_handling":
                # Test error handling
                agent = agent_class(self.registry, {})
                result = agent.execute(test_case.get("context"))
                # Should return a result even with bad input
                return isinstance(result, dict)
                
            elif test_case["test_type"] == "capabilities":
                # Test capabilities
                agent = agent_class(self.registry, {})
                if hasattr(agent, 'get_capabilities'):
                    capabilities = agent.get_capabilities()
                    return isinstance(capabilities, list)
                return True  # Optional method
                
            elif test_case["test_type"] == "workflow_step":
                # Test workflow step
                agent = agent_class(self.registry, {})
                if hasattr(agent, 'get_workflow_step'):
                    workflow_step = agent.get_workflow_step()
                    return isinstance(workflow_step, str) and len(workflow_step) > 0
                return True  # Optional method
                
            elif test_case["test_type"] == "schema_compliance":
                # Test schema compliance
                agent = agent_class(self.registry, {})
                result = agent.execute(test_case.get("context"))
                
                # Check if result has expected structure
                if not isinstance(result, dict):
                    return False
                
                # Check for required fields
                required_fields = ["status", "agent"]
                for field in required_fields:
                    if field not in result:
                        return False
                
                return True
                
        except Exception as e:
            self._log(f"Test case {test_case['name']} failed: {str(e)}", "debug")
            return False
        
        return False
    
    def _create_certification_proposal(self, item_type: str, item_name: str, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a certification proposal for a tested agent."""
        return {
            "type": "certify_item",
            "item_type": item_type,
            "name": item_name,
            "test_results": test_result,
            "proposed_by": self.name,
            "certification_level": "basic" if test_result["score"] >= 0.75 else "conditional"
        }
    
    def _submit_certification_proposal(self, proposal: Dict[str, Any]):
        """Submit certification proposal to consensus."""
        try:
            self._log(f"Submitting certification proposal for {proposal['item_type']} '{proposal['name']}'", "info")
            
            # Import consensus system
            try:
                from launchonomy.utils.consensus import propose_and_vote
            except ImportError:
                from consensus import propose_and_vote
            
            vote_result = propose_and_vote(proposal)
            
            if vote_result:
                self._log(f"Certification proposal for '{proposal['name']}' ACCEPTED by consensus", "info")
                self._apply_certification(proposal)
            else:
                self._log(f"Certification proposal for '{proposal['name']}' REJECTED by consensus", "warning")
                
        except Exception as e:
            self._log(f"Error submitting certification proposal: {str(e)}", "error")
    
    def _apply_certification(self, proposal: Dict[str, Any]):
        """Apply certification to registry."""
        try:
            item_type = proposal["item_type"]
            item_name = proposal["name"]
            
            if item_type == "agent" and item_name in self.registry.agents:
                self.registry.agents[item_name]["status"] = "certified"
                self.registry.agents[item_name]["test_results"] = proposal["test_results"]
                self.registry.agents[item_name]["certification_level"] = proposal["certification_level"]
                self.registry.save()
                self._log(f"Applied certification for {item_type} '{item_name}'", "info")
            
        except Exception as e:
            self._log(f"Error applying certification: {str(e)}", "error") 