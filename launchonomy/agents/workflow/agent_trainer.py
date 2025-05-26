import logging
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class AgentTrainer:
    """
    AgentTrainer specializes in training and improving agents based on feedback and performance data.
    
    Responsibilities:
    1. Monitor agent performance and test results
    2. Analyze failure patterns and improvement opportunities
    3. Generate enhanced training prompts and specifications
    4. Propose agent improvements via consensus
    5. Coordinate with AgentDev for implementing improvements
    """
    
    def __init__(self, registry, orchestrator, mission_context: Optional[Dict[str, Any]] = None):
        """
        Initialize AgentTrainer.
        
        Args:
            registry: Registry instance for managing agents/tools
            orchestrator: OrchestrationAgent instance
            mission_context: Mission context including workspace information
        """
        self.registry = registry
        self.orchestrator = orchestrator
        self.mission_context = mission_context or {}
        self.name = "AgentTrainer"
        
    def _log(self, message: str, level: str = "info"):
        """Helper for logging."""
        log_func = getattr(logger, level, logger.info)
        log_func(f"{self.name}: {message}")
        if hasattr(self.orchestrator, '_log_to_monitor') and callable(self.orchestrator._log_to_monitor):
            self.orchestrator._log_to_monitor(self.name, message, level)
    
    def execute(self) -> Dict[str, Any]:
        """
        Main execution method for AgentTrainer.
        
        Returns:
            Dict containing training results and improvement proposals
        """
        self._log("Starting AgentTrainer execution - analyzing agent performance", "info")
        
        results = {
            "analyzed_agents": [],
            "improvement_proposals": [],
            "training_updates": [],
            "errors": [],
            "status": "completed"
        }
        
        try:
            # Find agents that need training/improvement
            agents_to_analyze = self._find_agents_for_training()
            
            self._log(f"Found {len(agents_to_analyze)} agents to analyze for training", "info")
            
            # Analyze each agent
            for agent_name, agent_spec in agents_to_analyze.items():
                try:
                    analysis_result = self._analyze_agent_performance(agent_name, agent_spec)
                    results["analyzed_agents"].append(analysis_result)
                    
                    if analysis_result["needs_improvement"]:
                        # Generate improvement proposal
                        improvement_proposal = self._create_improvement_proposal(agent_name, analysis_result)
                        results["improvement_proposals"].append(improvement_proposal)
                        
                        # Submit improvement proposal
                        self._submit_improvement_proposal(improvement_proposal)
                        
                    if analysis_result["training_update"]:
                        # Apply training updates
                        training_update = self._apply_training_update(agent_name, analysis_result["training_update"])
                        results["training_updates"].append(training_update)
                        
                except Exception as e:
                    error_msg = f"Error analyzing agent {agent_name}: {str(e)}"
                    self._log(error_msg, "error")
                    results["errors"].append(error_msg)
                    
        except Exception as e:
            error_msg = f"Critical error in AgentTrainer execution: {str(e)}"
            self._log(error_msg, "error")
            results["errors"].append(error_msg)
            results["status"] = "failed"
        
        self._log(f"AgentTrainer execution completed. Analyzed {len(results['analyzed_agents'])} agents", "info")
        return results
    
    def _find_agents_for_training(self) -> Dict[str, Dict[str, Any]]:
        """Find agents that need training or improvement."""
        agents_to_train = {}
        
        for agent_name, agent_spec in self.registry.agents.items():
            # Include agents that have test results (certified or failed)
            if agent_spec.get("test_results") or agent_spec.get("status") in ["certified", "failed"]:
                agents_to_train[agent_name] = agent_spec
                
        return agents_to_train
    
    def _analyze_agent_performance(self, agent_name: str, agent_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze agent performance and identify improvement opportunities.
        
        Args:
            agent_name: Name of the agent to analyze
            agent_spec: Agent specification from registry
            
        Returns:
            Dict containing analysis results
        """
        self._log(f"Analyzing performance for agent: {agent_name}", "info")
        
        analysis = {
            "agent_name": agent_name,
            "current_status": agent_spec.get("status", "unknown"),
            "needs_improvement": False,
            "training_update": None,
            "improvement_areas": [],
            "performance_score": 0.0,
            "recommendations": []
        }
        
        try:
            # Analyze test results if available
            test_results = agent_spec.get("test_results")
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
            
            # Analyze agent specification for potential improvements
            spec_analysis = self._analyze_agent_specification(agent_spec)
            analysis["improvement_areas"].extend(spec_analysis["areas"])
            analysis["recommendations"].extend(spec_analysis["recommendations"])
            
            # Generate training updates if needed
            if analysis["needs_improvement"] or len(analysis["improvement_areas"]) > 0:
                training_update = self._generate_training_update(agent_name, agent_spec, analysis)
                analysis["training_update"] = training_update
                
        except Exception as e:
            self._log(f"Error analyzing agent {agent_name}: {str(e)}", "error")
            analysis["recommendations"].append(f"Analysis failed: {str(e)}")
        
        return analysis
    
    def _analyze_agent_specification(self, agent_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze agent specification for potential improvements."""
        analysis = {
            "areas": [],
            "recommendations": []
        }
        
        # Check training prompt quality
        training_prompt = agent_spec.get("training_prompt", "")
        if len(training_prompt) < 50:
            analysis["areas"].append({
                "area": "training_prompt",
                "description": "Training prompt is too short",
                "severity": "medium"
            })
            analysis["recommendations"].append("Expand training prompt with more detailed instructions")
        
        # Check capabilities definition
        capabilities = agent_spec.get("capabilities", [])
        if len(capabilities) == 0:
            analysis["areas"].append({
                "area": "capabilities",
                "description": "No capabilities defined",
                "severity": "high"
            })
            analysis["recommendations"].append("Define specific capabilities for the agent")
        
        # Check workflow step definition for workflow agents
        workflow_step = agent_spec.get("spec", {}).get("workflow_step")
        if workflow_step and not agent_spec.get("spec", {}).get("input_schema"):
            analysis["areas"].append({
                "area": "input_schema",
                "description": "Workflow agent missing input schema",
                "severity": "medium"
            })
            analysis["recommendations"].append("Define input schema for workflow agent")
        
        return analysis
    
    def _generate_training_update(self, agent_name: str, agent_spec: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate training updates based on analysis."""
        training_update = {
            "agent_name": agent_name,
            "updates": {},
            "rationale": []
        }
        
        # Improve training prompt based on failed tests
        current_prompt = agent_spec.get("training_prompt", "")
        improved_prompt = self._improve_training_prompt(current_prompt, analysis)
        if improved_prompt != current_prompt:
            training_update["updates"]["training_prompt"] = improved_prompt
            training_update["rationale"].append("Enhanced training prompt based on test failures")
        
        # Add missing capabilities
        current_capabilities = agent_spec.get("capabilities", [])
        improved_capabilities = self._improve_capabilities(current_capabilities, analysis)
        if improved_capabilities != current_capabilities:
            training_update["updates"]["capabilities"] = improved_capabilities
            training_update["rationale"].append("Added missing capabilities")
        
        # Improve specification
        spec_improvements = self._improve_specification(agent_spec.get("spec", {}), analysis)
        if spec_improvements:
            training_update["updates"]["spec"] = spec_improvements
            training_update["rationale"].append("Enhanced agent specification")
        
        return training_update
    
    def _improve_training_prompt(self, current_prompt: str, analysis: Dict[str, Any]) -> str:
        """Improve training prompt based on analysis."""
        improved_prompt = current_prompt
        
        # Add error handling instructions if error handling tests failed
        error_handling_failed = any(
            area.get("area") == "error_handling" 
            for area in analysis.get("improvement_areas", [])
        )
        if error_handling_failed and "error handling" not in improved_prompt.lower():
            improved_prompt += "\n\nIMPORTANT: Always handle errors gracefully and return a structured response even when inputs are invalid or operations fail."
        
        # Add schema compliance instructions if schema tests failed
        schema_failed = any(
            "schema" in area.get("area", "").lower() 
            for area in analysis.get("improvement_areas", [])
        )
        if schema_failed and "schema" not in improved_prompt.lower():
            improved_prompt += "\n\nEnsure all outputs conform to the expected schema format with required fields."
        
        # Add workflow instructions if workflow tests failed
        workflow_failed = any(
            "workflow" in area.get("area", "").lower() 
            for area in analysis.get("improvement_areas", [])
        )
        if workflow_failed and "workflow" not in improved_prompt.lower():
            improved_prompt += "\n\nAs a workflow agent, ensure you properly handle the workflow step and maintain context between operations."
        
        return improved_prompt
    
    def _improve_capabilities(self, current_capabilities: List[str], analysis: Dict[str, Any]) -> List[str]:
        """Improve capabilities list based on analysis."""
        improved_capabilities = current_capabilities.copy()
        
        # Add error handling capability if missing
        if "error_handling" not in improved_capabilities:
            error_handling_needed = any(
                "error" in area.get("area", "").lower() 
                for area in analysis.get("improvement_areas", [])
            )
            if error_handling_needed:
                improved_capabilities.append("error_handling")
        
        # Add validation capability if missing
        if "validation" not in improved_capabilities:
            validation_needed = any(
                "validation" in area.get("area", "").lower() or "schema" in area.get("area", "").lower()
                for area in analysis.get("improvement_areas", [])
            )
            if validation_needed:
                improved_capabilities.append("validation")
        
        return improved_capabilities
    
    def _improve_specification(self, current_spec: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Improve agent specification based on analysis."""
        improved_spec = current_spec.copy()
        
        # Add input schema if missing for workflow agents
        if current_spec.get("workflow_step") and not current_spec.get("input_schema"):
            improved_spec["input_schema"] = {
                "type": "object",
                "properties": {
                    "context": {"type": "object"},
                    "mission_context": {"type": "object"}
                }
            }
        
        # Add output schema if missing for workflow agents
        if current_spec.get("workflow_step") and not current_spec.get("output_schema"):
            improved_spec["output_schema"] = {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "agent": {"type": "string"},
                    "workflow_step": {"type": "string"}
                },
                "required": ["status", "agent"]
            }
        
        return improved_spec if improved_spec != current_spec else {}
    
    def _create_improvement_proposal(self, agent_name: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create an improvement proposal for an agent."""
        return {
            "type": "improve_agent",
            "agent_name": agent_name,
            "current_score": analysis["performance_score"],
            "improvement_areas": analysis["improvement_areas"],
            "training_update": analysis["training_update"],
            "proposed_by": self.name,
            "priority": "high" if analysis["performance_score"] < 0.5 else "medium"
        }
    
    def _submit_improvement_proposal(self, proposal: Dict[str, Any]):
        """Submit improvement proposal to consensus."""
        try:
            self._log(f"Submitting improvement proposal for agent '{proposal['agent_name']}'", "info")
            
            # For now, auto-apply improvements that are clearly beneficial
            # In a full implementation, this would go through consensus
            if proposal["current_score"] < 0.75:  # Clear improvement needed
                self._log(f"Auto-applying improvement for agent '{proposal['agent_name']}' (score: {proposal['current_score']:.2f})", "info")
                self._apply_improvement(proposal)
            else:
                self._log(f"Improvement proposal for '{proposal['agent_name']}' requires consensus review", "info")
                
        except Exception as e:
            self._log(f"Error submitting improvement proposal: {str(e)}", "error")
    
    def _apply_improvement(self, proposal: Dict[str, Any]):
        """Apply improvement to agent in registry."""
        try:
            agent_name = proposal["agent_name"]
            training_update = proposal["training_update"]
            
            if agent_name in self.registry.agents and training_update:
                # Apply updates to registry
                for key, value in training_update.get("updates", {}).items():
                    if key == "spec":
                        # Merge spec updates
                        current_spec = self.registry.agents[agent_name].get("spec", {})
                        current_spec.update(value)
                        self.registry.agents[agent_name]["spec"] = current_spec
                    else:
                        self.registry.agents[agent_name][key] = value
                
                # Mark agent for rebuilding
                self.registry.agents[agent_name]["status"] = "pending"
                self.registry.agents[agent_name]["improvement_applied"] = True
                self.registry.agents[agent_name]["improvement_rationale"] = training_update.get("rationale", [])
                
                self.registry.save()
                self._log(f"Applied improvement to agent '{agent_name}'", "info")
                
                # Trigger AgentDev to rebuild the improved agent
                self._trigger_agent_dev()
            
        except Exception as e:
            self._log(f"Error applying improvement: {str(e)}", "error")
    
    def _apply_training_update(self, agent_name: str, training_update: Dict[str, Any]) -> Dict[str, Any]:
        """Apply training update to agent."""
        try:
            if agent_name in self.registry.agents:
                # Apply the training update
                for key, value in training_update.get("updates", {}).items():
                    if key == "spec":
                        current_spec = self.registry.agents[agent_name].get("spec", {})
                        current_spec.update(value)
                        self.registry.agents[agent_name]["spec"] = current_spec
                    else:
                        self.registry.agents[agent_name][key] = value
                
                self.registry.save()
                
                return {
                    "agent_name": agent_name,
                    "status": "applied",
                    "updates": training_update.get("updates", {}),
                    "rationale": training_update.get("rationale", [])
                }
            
        except Exception as e:
            self._log(f"Error applying training update: {str(e)}", "error")
            return {
                "agent_name": agent_name,
                "status": "failed",
                "error": str(e)
            }
    
    def _trigger_agent_dev(self):
        """Trigger AgentDev to rebuild improved agents."""
        try:
            if hasattr(self.orchestrator, 'enqueue_task'):
                self.orchestrator.enqueue_task("AgentDev")
            else:
                self._log("Orchestrator does not support task queuing, AgentDev will run on next cycle", "warning")
        except Exception as e:
            self._log(f"Error triggering AgentDev: {str(e)}", "error") 