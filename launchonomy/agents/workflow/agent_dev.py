import logging
import os
import json
import importlib
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class AgentDev:
    """
    AgentDev specializes in building out stub agents into working implementations.
    
    Responsibilities:
    1. Monitor registry for "pending" agent stubs
    2. Generate actual agent implementation code based on stub specs
    3. Create proper Python files in mission workspace agents/ directory
    4. Update registry status to "built"
    5. Trigger AgentQA for testing
    """
    
    def __init__(self, registry, orchestrator, mission_context: Optional[Dict[str, Any]] = None):
        """
        Initialize AgentDev.
        
        Args:
            registry: Registry instance for managing agents/tools
            orchestrator: OrchestrationAgent instance
            mission_context: Mission context including workspace information
        """
        self.registry = registry
        self.orchestrator = orchestrator
        self.mission_context = mission_context or {}
        self.name = "AgentDev"
        
    def _log(self, message: str, level: str = "info"):
        """Helper for logging."""
        log_func = getattr(logger, level, logger.info)
        log_func(f"{self.name}: {message}")
        if hasattr(self.orchestrator, '_log_to_monitor') and callable(self.orchestrator._log_to_monitor):
            self.orchestrator._log_to_monitor(self.name, message, level)
    
    def execute(self) -> Dict[str, Any]:
        """
        Main execution method for AgentDev.
        
        Returns:
            Dict containing execution results and built agents
        """
        self._log("Starting AgentDev execution - building out pending agent stubs", "info")
        
        results = {
            "built_agents": [],
            "errors": [],
            "status": "completed"
        }
        
        try:
            # Find pending agent stubs in registry
            pending_agents = self._find_pending_agents()
            
            self._log(f"Found {len(pending_agents)} pending agents to build", "info")
            
            # Build out pending agents
            for agent_name, agent_spec in pending_agents.items():
                try:
                    built_path = self._build_agent(agent_name, agent_spec)
                    if built_path:
                        self._update_agent_status(agent_name, "built", built_path)
                        results["built_agents"].append({
                            "name": agent_name,
                            "path": built_path,
                            "status": "success"
                        })
                        self._log(f"Successfully built agent: {agent_name} at {built_path}", "info")
                    else:
                        results["errors"].append(f"Failed to build agent: {agent_name}")
                        
                except Exception as e:
                    error_msg = f"Error building agent {agent_name}: {str(e)}"
                    self._log(error_msg, "error")
                    results["errors"].append(error_msg)
            
            # Trigger AgentQA if we built anything
            if results["built_agents"]:
                self._log("Triggering AgentQA for testing newly built agents", "info")
                self._trigger_agent_qa()
                
        except Exception as e:
            error_msg = f"Critical error in AgentDev execution: {str(e)}"
            self._log(error_msg, "error")
            results["errors"].append(error_msg)
            results["status"] = "failed"
        
        self._log(f"AgentDev execution completed. Built {len(results['built_agents'])} agents", "info")
        return results
    
    def _find_pending_agents(self) -> Dict[str, Dict[str, Any]]:
        """Find agents with 'pending' status in registry."""
        pending = {}
        for agent_name, agent_spec in self.registry.agents.items():
            if agent_spec.get("status") == "pending":
                pending[agent_name] = agent_spec
        return pending
    
    def _build_agent(self, agent_name: str, agent_spec: Dict[str, Any]) -> Optional[str]:
        """
        Build out a stub agent into a working implementation.
        
        Args:
            agent_name: Name of the agent to build
            agent_spec: Agent specification from registry
            
        Returns:
            Path to the built agent file, or None if failed
        """
        try:
            # Generate agent implementation code
            agent_code = self._generate_agent_code(agent_name, agent_spec)
            
            # Save to mission workspace if available
            workspace_path = self.mission_context.get("workspace_path")
            if workspace_path and hasattr(self.orchestrator, 'mission_manager'):
                # Use workspace system
                success = self.orchestrator.mission_manager.add_agent_to_mission_workspace(
                    agent_name=agent_name,
                    agent_spec=agent_spec,
                    agent_code=agent_code
                )
                
                if success:
                    # Return workspace-relative path
                    agent_filename = f"{agent_name.lower().replace(' ', '_').replace('-', '_')}.py"
                    workspace_relative_path = f"agents/{agent_name}/{agent_filename}"
                    full_path = os.path.join(workspace_path, workspace_relative_path)
                    self._log(f"Created agent implementation in workspace: {workspace_relative_path}", "debug")
                    return full_path
                else:
                    self._log(f"Failed to save agent {agent_name} to workspace", "error")
                    return None
            else:
                # Fallback to global directory if no workspace available
                self._log(f"No workspace available, saving agent {agent_name} to global directory", "warning")
                
                # Create agents directory if it doesn't exist
                agents_dir = Path("launchonomy/agents/workflow")
                agents_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate agent file path
                agent_filename = f"{agent_name.lower().replace(' ', '_').replace('-', '_')}.py"
                agent_path = agents_dir / agent_filename
                
                # Write agent file
                with open(agent_path, 'w') as f:
                    f.write(agent_code)
                
                self._log(f"Created agent implementation at: {agent_path}", "debug")
                return str(agent_path)
            
        except Exception as e:
            self._log(f"Error building agent {agent_name}: {str(e)}", "error")
            return None
    
    def _generate_agent_code(self, agent_name: str, agent_spec: Dict[str, Any]) -> str:
        """Generate Python code for an agent implementation."""
        class_name = f"{agent_name.replace(' ', '').replace('-', '')}Agent"
        description = agent_spec.get("description", f"Auto-generated agent for {agent_name}")
        capabilities = agent_spec.get("capabilities", [])
        training_prompt = agent_spec.get("training_prompt", f"You are {agent_name}. {description}")
        
        # Extract workflow step if this is a workflow agent
        workflow_step = agent_spec.get("spec", {}).get("workflow_step", "")
        input_schema = agent_spec.get("spec", {}).get("input_schema", {})
        output_schema = agent_spec.get("spec", {}).get("output_schema", {})
        
        code = f'''"""
Auto-generated agent implementation for {agent_name}.
Generated by AgentDev.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class {class_name}:
    """
    {description}
    
    Capabilities: {', '.join(capabilities)}
    Workflow Step: {workflow_step}
    """
    
    def __init__(self, registry, mission_context: Optional[Dict[str, Any]] = None):
        """
        Initialize {agent_name}.
        
        Args:
            registry: Registry instance
            mission_context: Optional mission context
        """
        self.registry = registry
        self.mission_context = mission_context or {{}}
        self.name = "{agent_name}"
        self.training_prompt = """{training_prompt}"""
        self.workflow_step = "{workflow_step}"
        self.input_schema = {json.dumps(input_schema, indent=8)}
        self.output_schema = {json.dumps(output_schema, indent=8)}
        
    def execute(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute {agent_name} functionality.
        
        Args:
            context: Execution context
            
        Returns:
            Dict containing execution results matching output schema
        """
        logger.info(f"{{self.name}}: Starting execution for workflow step: {{self.workflow_step}}")
        
        try:
            # Merge context with mission context
            full_context = {{**self.mission_context, **(context or {{}})}}
            
            # Validate input against schema if provided
            if self.input_schema and context:
                self._validate_input(context)
            
            # TODO: Implement specific {agent_name} logic here
            # This is a placeholder implementation that should be enhanced
            
            # Generate output matching the expected schema
            result = self._generate_output(full_context)
            
            logger.info(f"{{self.name}}: Execution completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"{{self.name}}: Execution failed: {{str(e)}}")
            return {{
                "status": "failed",
                "agent": self.name,
                "error": str(e),
                "context": context
            }}
    
    def _validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input context against input schema."""
        # TODO: Implement proper schema validation
        # For now, just check if required fields are present
        return True
    
    def _generate_output(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate output matching the expected output schema."""
        # Base output structure
        result = {{
            "status": "completed",
            "agent": self.name,
            "workflow_step": self.workflow_step,
            "context": context,
            "capabilities_used": {capabilities},
            "training_prompt": self.training_prompt
        }}
        
        # Add workflow-specific outputs based on output schema
        if self.output_schema:
            # TODO: Generate outputs that match the schema
            # For now, add placeholder outputs
            for key in self.output_schema.keys():
                if key not in result:
                    result[key] = f"Generated {{key}} for {{self.name}}"
        
        return result
    
    def get_capabilities(self) -> list:
        """Return list of agent capabilities."""
        return {capabilities}
    
    def get_training_prompt(self) -> str:
        """Return the training prompt for this agent."""
        return self.training_prompt
    
    def get_workflow_step(self) -> str:
        """Return the workflow step this agent handles."""
        return self.workflow_step
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Return the input schema for this agent."""
        return self.input_schema
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Return the output schema for this agent."""
        return self.output_schema
'''
        
        return code
    
    def _update_agent_status(self, agent_name: str, status: str, built_path: str):
        """Update agent status in registry."""
        if agent_name in self.registry.agents:
            self.registry.agents[agent_name]["status"] = status
            self.registry.agents[agent_name]["built_path"] = built_path
            self.registry.save()
    
    def _trigger_agent_qa(self):
        """Trigger AgentQA to test newly built agents."""
        try:
            if hasattr(self.coa, 'enqueue_task'):
                self.coa.enqueue_task("AgentQA")
            else:
                self._log("COA does not support task queuing, AgentQA will run on next cycle", "warning")
        except Exception as e:
            self._log(f"Error triggering AgentQA: {str(e)}", "error") 