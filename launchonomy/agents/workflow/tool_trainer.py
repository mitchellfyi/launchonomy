import logging
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class ToolTrainer:
    """
    ToolTrainer specializes in training and improving tools based on feedback and performance data.
    
    Responsibilities:
    1. Monitor tool performance and test results
    2. Analyze failure patterns and improvement opportunities
    3. Generate enhanced tool specifications and configurations
    4. Propose tool improvements via consensus
    5. Coordinate with ToolDev for implementing improvements
    """
    
    def __init__(self, registry, orchestrator, mission_context: Optional[Dict[str, Any]] = None):
        """
        Initialize ToolTrainer.
        
        Args:
            registry: Registry instance for managing agents/tools
            orchestrator: OrchestrationAgent instance
            mission_context: Mission context including workspace information
        """
        self.registry = registry
        self.orchestrator = orchestrator
        self.mission_context = mission_context or {}
        self.name = "ToolTrainer"
        
    def _log(self, message: str, level: str = "info"):
        """Helper for logging."""
        log_func = getattr(logger, level, logger.info)
        log_func(f"{self.name}: {message}")
        if hasattr(self.coa, '_log_to_monitor') and callable(self.coa._log_to_monitor):
            self.coa._log_to_monitor(self.name, message, level)
    
    def execute(self) -> Dict[str, Any]:
        """
        Main execution method for ToolTrainer.
        
        Returns:
            Dict containing training results and improvement proposals
        """
        self._log("Starting ToolTrainer execution - analyzing tool performance", "info")
        
        results = {
            "analyzed_tools": [],
            "improvement_proposals": [],
            "configuration_updates": [],
            "errors": [],
            "status": "completed"
        }
        
        try:
            # Find tools that need training/improvement
            tools_to_analyze = self._find_tools_for_training()
            
            self._log(f"Found {len(tools_to_analyze)} tools to analyze for training", "info")
            
            # Analyze each tool
            for tool_name, tool_spec in tools_to_analyze.items():
                try:
                    analysis_result = self._analyze_tool_performance(tool_name, tool_spec)
                    results["analyzed_tools"].append(analysis_result)
                    
                    if analysis_result["needs_improvement"]:
                        # Generate improvement proposal
                        improvement_proposal = self._create_improvement_proposal(tool_name, analysis_result)
                        results["improvement_proposals"].append(improvement_proposal)
                        
                        # Submit improvement proposal
                        self._submit_improvement_proposal(improvement_proposal)
                        
                    if analysis_result["configuration_update"]:
                        # Apply configuration updates
                        config_update = self._apply_configuration_update(tool_name, analysis_result["configuration_update"])
                        results["configuration_updates"].append(config_update)
                        
                except Exception as e:
                    error_msg = f"Error analyzing tool {tool_name}: {str(e)}"
                    self._log(error_msg, "error")
                    results["errors"].append(error_msg)
                    
        except Exception as e:
            error_msg = f"Critical error in ToolTrainer execution: {str(e)}"
            self._log(error_msg, "error")
            results["errors"].append(error_msg)
            results["status"] = "failed"
        
        self._log(f"ToolTrainer execution completed. Analyzed {len(results['analyzed_tools'])} tools", "info")
        return results
    
    def _find_tools_for_training(self) -> Dict[str, Dict[str, Any]]:
        """Find tools that need training or improvement."""
        tools_to_train = {}
        
        for tool_name, tool_spec in self.registry.tools.items():
            # Include tools that have test results (certified or failed)
            if tool_spec.get("test_results") or tool_spec.get("status") in ["certified", "failed"]:
                tools_to_train[tool_name] = tool_spec
                
        return tools_to_train
    
    def _analyze_tool_performance(self, tool_name: str, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze tool performance and identify improvement opportunities.
        
        Args:
            tool_name: Name of the tool to analyze
            tool_spec: Tool specification from registry
            
        Returns:
            Dict containing analysis results
        """
        self._log(f"Analyzing performance for tool: {tool_name}", "info")
        
        analysis = {
            "tool_name": tool_name,
            "current_status": tool_spec.get("status", "unknown"),
            "needs_improvement": False,
            "configuration_update": None,
            "improvement_areas": [],
            "performance_score": 0.0,
            "recommendations": []
        }
        
        try:
            # Analyze test results if available
            test_results = tool_spec.get("test_results")
            if test_results:
                analysis["performance_score"] = test_results.get("score", 0.0)
                
                # Check if performance is below threshold
                if analysis["performance_score"] < 0.9:  # 90% threshold for improvement
                    analysis["needs_improvement"] = True
                    
                    # Analyze failed tests
                    failed_tests = [test for test in test_results.get("tests_run", []) if not test.get("passed")]
                    for failed_test in failed_tests:
                        analysis["improvement_areas"].append({
                            "area": failed_test.get("name"),
                            "description": failed_test.get("description"),
                            "error": failed_test.get("error", "Unknown error")
                        })
                
                # Extract existing recommendations
                analysis["recommendations"].extend(test_results.get("recommendations", []))
            
            # Analyze tool specification for potential improvements
            spec_analysis = self._analyze_tool_specification(tool_spec)
            analysis["improvement_areas"].extend(spec_analysis["areas"])
            analysis["recommendations"].extend(spec_analysis["recommendations"])
            
            # Generate configuration updates if needed
            if analysis["needs_improvement"] or len(analysis["improvement_areas"]) > 0:
                config_update = self._generate_configuration_update(tool_name, tool_spec, analysis)
                analysis["configuration_update"] = config_update
                
        except Exception as e:
            self._log(f"Error analyzing tool {tool_name}: {str(e)}", "error")
            analysis["recommendations"].append(f"Analysis failed: {str(e)}")
        
        return analysis
    
    def _analyze_tool_specification(self, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze tool specification for potential improvements."""
        analysis = {
            "areas": [],
            "recommendations": []
        }
        
        # Check description quality
        description = tool_spec.get("description", "")
        if len(description) < 30:
            analysis["areas"].append({
                "area": "description",
                "description": "Tool description is too short",
                "severity": "medium"
            })
            analysis["recommendations"].append("Expand tool description with more details")
        
        # Check endpoint configuration for webhook tools
        if tool_spec.get("type") == "webhook":
            endpoint_details = tool_spec.get("endpoint_details", {})
            if not endpoint_details.get("url"):
                analysis["areas"].append({
                    "area": "endpoint_url",
                    "description": "Webhook tool missing endpoint URL",
                    "severity": "high"
                })
                analysis["recommendations"].append("Configure proper endpoint URL for webhook tool")
        
        # Check schema definitions
        if not tool_spec.get("request_schema"):
            analysis["areas"].append({
                "area": "request_schema",
                "description": "Tool missing request schema",
                "severity": "medium"
            })
            analysis["recommendations"].append("Define request schema for better validation")
        
        if not tool_spec.get("response_schema"):
            analysis["areas"].append({
                "area": "response_schema",
                "description": "Tool missing response schema",
                "severity": "medium"
            })
            analysis["recommendations"].append("Define response schema for better validation")
        
        # Check authentication configuration
        auth_config = tool_spec.get("authentication", {})
        if tool_spec.get("type") in ["api", "webhook"] and not auth_config:
            analysis["areas"].append({
                "area": "authentication",
                "description": "API/webhook tool missing authentication configuration",
                "severity": "medium"
            })
            analysis["recommendations"].append("Configure authentication for secure API access")
        
        return analysis
    
    def _generate_configuration_update(self, tool_name: str, tool_spec: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate configuration updates based on analysis."""
        config_update = {
            "tool_name": tool_name,
            "updates": {},
            "rationale": []
        }
        
        # Improve description if too short
        current_description = tool_spec.get("description", "")
        if len(current_description) < 30:
            improved_description = self._improve_description(current_description, tool_name, tool_spec)
            config_update["updates"]["description"] = improved_description
            config_update["rationale"].append("Enhanced tool description")
        
        # Add missing schemas
        if not tool_spec.get("request_schema"):
            request_schema = self._generate_request_schema(tool_spec)
            config_update["updates"]["request_schema"] = request_schema
            config_update["rationale"].append("Added request schema for validation")
        
        if not tool_spec.get("response_schema"):
            response_schema = self._generate_response_schema(tool_spec)
            config_update["updates"]["response_schema"] = response_schema
            config_update["rationale"].append("Added response schema for validation")
        
        # Improve endpoint configuration
        if tool_spec.get("type") == "webhook":
            endpoint_improvements = self._improve_endpoint_configuration(tool_spec, analysis)
            if endpoint_improvements:
                config_update["updates"]["endpoint_details"] = endpoint_improvements
                config_update["rationale"].append("Improved endpoint configuration")
        
        # Add authentication configuration if missing
        if tool_spec.get("type") in ["api", "webhook"] and not tool_spec.get("authentication"):
            auth_config = self._generate_authentication_config(tool_spec)
            config_update["updates"]["authentication"] = auth_config
            config_update["rationale"].append("Added authentication configuration")
        
        return config_update
    
    def _improve_description(self, current_description: str, tool_name: str, tool_spec: Dict[str, Any]) -> str:
        """Improve tool description."""
        if current_description:
            improved_description = current_description
        else:
            improved_description = f"Auto-generated tool for {tool_name}"
        
        # Add tool type information
        tool_type = tool_spec.get("type", "generic")
        if tool_type not in improved_description.lower():
            improved_description += f" ({tool_type} tool)"
        
        # Add capability information
        if tool_type == "webhook":
            improved_description += ". Provides webhook-based integration capabilities."
        elif tool_type == "api":
            improved_description += ". Provides API-based integration capabilities."
        elif tool_type == "local":
            improved_description += ". Provides local processing capabilities."
        
        return improved_description
    
    def _generate_request_schema(self, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a basic request schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "Description of the task to perform"
                },
                "data": {
                    "type": "object",
                    "description": "Data for the task"
                }
            },
            "required": ["task_description"]
        }
    
    def _generate_response_schema(self, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a basic response schema for the tool."""
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["completed", "failed"],
                    "description": "Status of the operation"
                },
                "tool": {
                    "type": "string",
                    "description": "Name of the tool that processed the request"
                },
                "result": {
                    "type": "object",
                    "description": "Result data from the tool"
                }
            },
            "required": ["status", "tool"]
        }
    
    def _improve_endpoint_configuration(self, tool_spec: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Improve endpoint configuration for webhook tools."""
        current_endpoint = tool_spec.get("endpoint_details", {})
        
        # Check if endpoint URL is missing or placeholder
        current_url = current_endpoint.get("url", "")
        if not current_url or "placeholder" in current_url.lower():
            # Generate a more realistic placeholder URL
            tool_name = tool_spec.get("name", "unknown").lower().replace(" ", "_")
            improved_endpoint = current_endpoint.copy()
            improved_endpoint["url"] = f"https://api.example.com/webhooks/{tool_name}"
            improved_endpoint["method"] = current_endpoint.get("method", "POST")
            
            # Add timeout configuration
            if "timeout" not in improved_endpoint:
                improved_endpoint["timeout"] = 30
            
            return improved_endpoint
        
        return None
    
    def _generate_authentication_config(self, tool_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic authentication configuration."""
        tool_type = tool_spec.get("type", "webhook")
        
        if tool_type == "api":
            return {
                "type": "api_key",
                "header": "Authorization",
                "format": "Bearer {api_key}",
                "description": "API key authentication"
            }
        else:  # webhook or other
            return {
                "type": "none",
                "description": "No authentication required"
            }
    
    def _create_improvement_proposal(self, tool_name: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create an improvement proposal for a tool."""
        return {
            "type": "improve_tool",
            "tool_name": tool_name,
            "current_score": analysis["performance_score"],
            "improvement_areas": analysis["improvement_areas"],
            "configuration_update": analysis["configuration_update"],
            "proposed_by": self.name,
            "priority": "high" if analysis["performance_score"] < 0.5 else "medium"
        }
    
    def _submit_improvement_proposal(self, proposal: Dict[str, Any]):
        """Submit improvement proposal to consensus."""
        try:
            self._log(f"Submitting improvement proposal for tool '{proposal['tool_name']}'", "info")
            
            # For now, auto-apply improvements that are clearly beneficial
            # In a full implementation, this would go through consensus
            if proposal["current_score"] < 0.75:  # Clear improvement needed
                self._log(f"Auto-applying improvement for tool '{proposal['tool_name']}' (score: {proposal['current_score']:.2f})", "info")
                self._apply_improvement(proposal)
            else:
                self._log(f"Improvement proposal for '{proposal['tool_name']}' requires consensus review", "info")
                
        except Exception as e:
            self._log(f"Error submitting improvement proposal: {str(e)}", "error")
    
    def _apply_improvement(self, proposal: Dict[str, Any]):
        """Apply improvement to tool in registry."""
        try:
            tool_name = proposal["tool_name"]
            config_update = proposal["configuration_update"]
            
            if tool_name in self.registry.tools and config_update:
                # Apply updates to registry
                for key, value in config_update.get("updates", {}).items():
                    self.registry.tools[tool_name][key] = value
                
                # Mark tool for rebuilding
                self.registry.tools[tool_name]["status"] = "pending"
                self.registry.tools[tool_name]["improvement_applied"] = True
                self.registry.tools[tool_name]["improvement_rationale"] = config_update.get("rationale", [])
                
                self.registry.save()
                self._log(f"Applied improvement to tool '{tool_name}'", "info")
                
                # Trigger ToolDev to rebuild the improved tool
                self._trigger_tool_dev()
            
        except Exception as e:
            self._log(f"Error applying improvement: {str(e)}", "error")
    
    def _apply_configuration_update(self, tool_name: str, config_update: Dict[str, Any]) -> Dict[str, Any]:
        """Apply configuration update to tool."""
        try:
            if tool_name in self.registry.tools:
                # Apply the configuration update
                for key, value in config_update.get("updates", {}).items():
                    self.registry.tools[tool_name][key] = value
                
                self.registry.save()
                
                return {
                    "tool_name": tool_name,
                    "status": "applied",
                    "updates": config_update.get("updates", {}),
                    "rationale": config_update.get("rationale", [])
                }
            
        except Exception as e:
            self._log(f"Error applying configuration update: {str(e)}", "error")
            return {
                "tool_name": tool_name,
                "status": "failed",
                "error": str(e)
            }
    
    def _trigger_tool_dev(self):
        """Trigger ToolDev to rebuild improved tools."""
        try:
            if hasattr(self.coa, 'enqueue_task'):
                self.coa.enqueue_task("ToolDev")
            else:
                self._log("COA does not support task queuing, ToolDev will run on next cycle", "warning")
        except Exception as e:
            self._log(f"Error triggering ToolDev: {str(e)}", "error") 