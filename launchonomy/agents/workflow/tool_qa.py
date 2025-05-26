import logging
import os
import json
import importlib
import sys
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class ToolQA:
    """
    ToolQA specializes in testing and validating newly built tools.
    
    Responsibilities:
    1. Monitor registry for "built" tools that need testing
    2. Run sandbox test suites against new tool implementations
    3. Validate functionality, error handling, and API compliance
    4. Log test results and suggest refinements
    5. Propose certification via consensus if tests pass
    """
    
    def __init__(self, registry, coa):
        """
        Initialize ToolQA.
        
        Args:
            registry: Registry instance for managing agents/tools
            coa: Consensus Orchestration Authority (OrchestrationAgent)
        """
        self.registry = registry
        self.coa = coa
        self.name = "ToolQA"
        
    def _log(self, message: str, level: str = "info"):
        """Helper for logging."""
        log_func = getattr(logger, level, logger.info)
        log_func(f"{self.name}: {message}")
        if hasattr(self.coa, '_log_to_monitor') and callable(self.coa._log_to_monitor):
            self.coa._log_to_monitor(self.name, message, level)
    
    def execute(self) -> Dict[str, Any]:
        """
        Main execution method for ToolQA.
        
        Returns:
            Dict containing test results and certification proposals
        """
        self._log("Starting ToolQA execution - testing built tools", "info")
        
        results = {
            "tested_tools": [],
            "certification_proposals": [],
            "errors": [],
            "status": "completed"
        }
        
        try:
            # Find built tools that need testing
            built_tools = self._find_built_tools()
            
            self._log(f"Found {len(built_tools)} built tools to test", "info")
            
            # Test built tools
            for tool_name, tool_spec in built_tools.items():
                try:
                    test_result = self._test_tool(tool_name, tool_spec)
                    results["tested_tools"].append(test_result)
                    
                    if test_result["passed"]:
                        # Propose certification
                        certification_proposal = self._create_certification_proposal("tool", tool_name, test_result)
                        results["certification_proposals"].append(certification_proposal)
                        self._submit_certification_proposal(certification_proposal)
                        
                except Exception as e:
                    error_msg = f"Error testing tool {tool_name}: {str(e)}"
                    self._log(error_msg, "error")
                    results["errors"].append(error_msg)
                    
        except Exception as e:
            error_msg = f"Critical error in ToolQA execution: {str(e)}"
            self._log(error_msg, "error")
            results["errors"].append(error_msg)
            results["status"] = "failed"
        
        self._log(f"ToolQA execution completed. Tested {len(results['tested_tools'])} tools", "info")
        return results
    
    def _find_built_tools(self) -> Dict[str, Dict[str, Any]]:
        """Find tools with 'built' status in registry."""
        built = {}
        for tool_name, tool_spec in self.registry.tools.items():
            if tool_spec.get("status") == "built":
                built[tool_name] = tool_spec
        return built
    
    def _test_tool(self, tool_name: str, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a built tool implementation.
        
        Args:
            tool_name: Name of the tool to test
            tool_spec: Tool specification from registry
            
        Returns:
            Dict containing test results
        """
        self._log(f"Testing tool: {tool_name}", "info")
        
        test_result = {
            "name": tool_name,
            "type": "tool",
            "passed": False,
            "tests_run": [],
            "errors": [],
            "score": 0.0,
            "recommendations": []
        }
        
        try:
            # Load the tool implementation
            built_path = tool_spec.get("built_path")
            if not built_path or not os.path.exists(built_path):
                test_result["errors"].append(f"Built tool file not found: {built_path}")
                return test_result
            
            # Import the tool module
            tool_module = self._import_tool_module(built_path)
            if not tool_module:
                test_result["errors"].append("Failed to import tool module")
                return test_result
            
            # Find the tool class
            tool_class = self._find_tool_class(tool_module, tool_name)
            if not tool_class:
                test_result["errors"].append("Tool class not found in module")
                return test_result
            
            # Run test suite
            test_cases = self._get_tool_test_cases(tool_name, tool_spec)
            passed_tests = 0
            
            for test_case in test_cases:
                try:
                    test_passed = self._run_tool_test_case(tool_class, test_case)
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
            self._log(f"Error testing tool {tool_name}: {str(e)}", "error")
        
        self._log(f"Tool {tool_name} test completed. Score: {test_result['score']:.2f}, Passed: {test_result['passed']}", "info")
        return test_result
    
    def _import_tool_module(self, tool_path: str):
        """Import tool module from file path."""
        try:
            spec = importlib.util.spec_from_file_location("test_tool", tool_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            self._log(f"Error importing tool module from {tool_path}: {str(e)}", "error")
            return None
    
    def _find_tool_class(self, module, tool_name: str):
        """Find the tool class in the module."""
        # Look for classes ending with 'Tool'
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                attr_name.endswith('Tool') and 
                hasattr(attr, 'execute')):
                return attr
        return None
    
    def _get_tool_test_cases(self, tool_name: str, tool_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get test cases for a tool."""
        base_tests = [
            {
                "name": "basic_instantiation",
                "description": "Test that tool can be instantiated",
                "test_type": "instantiation"
            },
            {
                "name": "basic_execution",
                "description": "Test that tool execute method works",
                "test_type": "execution",
                "task_description": "Test task",
                "data": {"test": True}
            },
            {
                "name": "error_handling",
                "description": "Test tool error handling",
                "test_type": "error_handling",
                "task_description": "",  # Empty task should be handled gracefully
                "data": None
            },
            {
                "name": "spec_validation",
                "description": "Test that tool has valid specification",
                "test_type": "spec_validation"
            }
        ]
        
        # Add tool-type specific tests
        tool_type = tool_spec.get("type", "webhook")
        if tool_type == "webhook":
            base_tests.extend([
                {
                    "name": "webhook_endpoint_validation",
                    "description": "Test that webhook endpoint is properly configured",
                    "test_type": "webhook_validation"
                },
                {
                    "name": "connection_test",
                    "description": "Test connection to webhook endpoint",
                    "test_type": "connection_test"
                }
            ])
        elif tool_type == "api":
            base_tests.extend([
                {
                    "name": "api_authentication",
                    "description": "Test API authentication",
                    "test_type": "api_auth"
                },
                {
                    "name": "api_response_validation",
                    "description": "Test API response format",
                    "test_type": "api_response"
                }
            ])
        
        # Add schema validation tests if schemas are defined
        if tool_spec.get("request_schema"):
            base_tests.append({
                "name": "request_schema_validation",
                "description": "Test request schema validation",
                "test_type": "request_schema"
            })
        
        if tool_spec.get("response_schema"):
            base_tests.append({
                "name": "response_schema_validation",
                "description": "Test response schema validation",
                "test_type": "response_schema"
            })
        
        return base_tests
    
    def _run_tool_test_case(self, tool_class, test_case: Dict[str, Any]) -> bool:
        """Run a single test case for a tool."""
        try:
            if test_case["test_type"] == "instantiation":
                # Test instantiation
                tool = tool_class({})
                return tool is not None
                
            elif test_case["test_type"] == "execution":
                # Test execution
                tool = tool_class({})
                result = tool.execute(
                    test_case.get("task_description", "test"),
                    test_case.get("data")
                )
                return isinstance(result, dict) and "status" in result
                
            elif test_case["test_type"] == "error_handling":
                # Test error handling
                tool = tool_class({})
                result = tool.execute(
                    test_case.get("task_description", ""),
                    test_case.get("data")
                )
                # Should return a result even with bad input
                return isinstance(result, dict)
                
            elif test_case["test_type"] == "spec_validation":
                # Test spec validation
                tool = tool_class({})
                if hasattr(tool, 'get_spec'):
                    spec = tool.get_spec()
                    return isinstance(spec, dict)
                return True  # Optional method
                
            elif test_case["test_type"] == "webhook_validation":
                # Test webhook configuration
                tool = tool_class({})
                if hasattr(tool, 'endpoint_url'):
                    endpoint = tool.endpoint_url
                    return isinstance(endpoint, str) and len(endpoint) > 0
                return True
                
            elif test_case["test_type"] == "connection_test":
                # Test connection
                tool = tool_class({})
                if hasattr(tool, 'test_connection'):
                    result = tool.test_connection()
                    return isinstance(result, dict) and "connection_status" in result
                return True  # Optional method
                
            elif test_case["test_type"] == "api_auth":
                # Test API authentication
                tool = tool_class({})
                if hasattr(tool, 'get_authentication_info'):
                    auth_info = tool.get_authentication_info()
                    return isinstance(auth_info, dict)
                return True
                
            elif test_case["test_type"] == "api_response":
                # Test API response handling
                tool = tool_class({})
                result = tool.execute("test_api_response", {"test": True})
                return isinstance(result, dict) and "status" in result
                
            elif test_case["test_type"] == "request_schema":
                # Test request schema validation
                tool = tool_class({})
                if hasattr(tool, 'get_request_schema'):
                    schema = tool.get_request_schema()
                    return isinstance(schema, dict)
                return True
                
            elif test_case["test_type"] == "response_schema":
                # Test response schema validation
                tool = tool_class({})
                if hasattr(tool, 'get_response_schema'):
                    schema = tool.get_response_schema()
                    return isinstance(schema, dict)
                return True
                
        except Exception as e:
            self._log(f"Test case {test_case['name']} failed: {str(e)}", "debug")
            return False
        
        return False
    
    def _create_certification_proposal(self, item_type: str, item_name: str, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a certification proposal for a tested tool."""
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
            
            if item_type == "tool" and item_name in self.registry.tools:
                self.registry.tools[item_name]["status"] = "certified"
                self.registry.tools[item_name]["test_results"] = proposal["test_results"]
                self.registry.tools[item_name]["certification_level"] = proposal["certification_level"]
                self.registry.save()
                self._log(f"Applied certification for {item_type} '{item_name}'", "info")
            
        except Exception as e:
            self._log(f"Error applying certification: {str(e)}", "error") 