import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WorkflowOutput:
    """Standardized output format for all workflow agents."""
    status: str  # "success", "failure", "requires_human", "requires_tools"
    data: Dict[str, Any]  # Main output data
    cost: float = 0.0  # Estimated cost of this operation
    next_steps: Optional[List[str]] = None  # Suggested next actions
    tools_used: Optional[List[str]] = None  # Tools that were utilized
    human_task_description: Optional[str] = None  # If human intervention needed
    error_message: Optional[str] = None  # If status is "failure"
    confidence: float = 1.0  # Confidence in the output (0.0-1.0)

class BaseWorkflowAgent(ABC):
    """Base class for all workflow agents in the Launchonomy system."""
    
    def __init__(self, name: str, registry=None, orchestrator=None, mission_context: Optional[Dict[str, Any]] = None):
        self.name = name
        self.registry = registry
        self.orchestrator = orchestrator
        self.mission_context = mission_context or {}
        self.logger = logging.getLogger(f"workflow.{name}")
        
    def _log(self, message: str, level: str = "info"):
        """Log messages with agent context."""
        if level == "error":
            self.logger.error(f"{self.name}: {message}")
        elif level == "warning":
            self.logger.warning(f"{self.name}: {message}")
        elif level == "debug":
            self.logger.debug(f"{self.name}: {message}")
        else:
            self.logger.info(f"{self.name}: {message}")
    
    def _get_launchonomy_context(self) -> Dict[str, Any]:
        """Get current Launchonomy context including mission, constraints, and registry snapshot."""
        context = {
            "timestamp": datetime.now().isoformat(),
            "agent_name": self.name,
            "budget_constraint": "$500 initial budget, costs never exceed 20% of revenue",
            "objective": "Acquire the first paying customer as fast as possible, then ignite exponential, profitable growth",
            "governance": "Unanimous consensus voting for all proposals, no human approval needed except for system-critical failures"
        }
        
        # Include mission context if available
        if self.mission_context:
            context.update(self.mission_context)
        
        if self.registry:
            context["available_agents"] = self.registry.list_agent_names()
            context["available_tools"] = self.registry.list_tool_names()
        
        return context
    
    def _save_asset_to_workspace(self, asset_name: str, asset_data: Any, category: str = "data") -> bool:
        """
        Save an asset to the mission workspace.
        
        Args:
            asset_name: Name of the asset file
            asset_data: Asset content (string, dict, etc.)
            category: Asset category (code, configs, data, media)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get mission ID from mission context
            mission_id = self.mission_context.get("mission_id")
            if not mission_id:
                self._log("No mission_id in context, cannot save asset to workspace", "warning")
                return False
            
            # Get workspace manager from orchestrator
            if not self.orchestrator or not hasattr(self.orchestrator, 'mission_manager'):
                self._log("No workspace manager available, cannot save asset", "warning")
                return False
            
            workspace_manager = self.orchestrator.mission_manager.workspace_manager
            if not workspace_manager:
                self._log("Workspace manager not initialized", "warning")
                return False
            
            # Save asset to workspace
            asset_path = workspace_manager.save_asset(
                mission_id=mission_id,
                asset_name=asset_name,
                asset_data=asset_data,
                category=category
            )
            
            if asset_path:
                self._log(f"Saved asset to workspace: {asset_path}", "info")
                return True
            else:
                self._log(f"Failed to save asset: {asset_name}", "error")
                return False
                
        except Exception as e:
            self._log(f"Error saving asset to workspace: {e}", "error")
            return False
    
    async def _get_relevant_memories(self, current_intent: str, k: int = 3) -> str:
        """
        Retrieve relevant memories from the mission's vector store.
        
        Args:
            current_intent: Description of what the agent is trying to do
            k: Number of memories to retrieve
            
        Returns:
            Formatted string with relevant memories or empty string if no memories
        """
        try:
            # Get retrieval agent from orchestrator if available
            if (self.orchestrator and 
                hasattr(self.orchestrator, 'retrieval_agent') and 
                self.orchestrator.retrieval_agent):
                
                retrieval_agent = self.orchestrator.retrieval_agent
                memories = await retrieval_agent.retrieve(current_intent, k=k)
                
                if memories:
                    memory_text = "\n".join([f"- {memory}" for memory in memories])
                    return f"\nRelevant Mission Memory:\n{memory_text}\n"
                else:
                    return ""
            else:
                return ""
                
        except Exception as e:
            self._log(f"Error retrieving memories: {str(e)}", "warning")
            return ""
    
    async def _get_tool_from_registry(self, tool_name: str, context: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Get a tool specification from the registry. If not found, attempts auto-provisioning."""
        if not self.registry:
            return None
            
        # First, check if tool exists in registry
        tool_spec = self.registry.get_tool_spec(tool_name)
        if tool_spec:
            return tool_spec
        
        # Tool not found, attempt auto-provisioning if orchestrator is available
        if self.orchestrator and hasattr(self.orchestrator, 'auto_provision_agent'):
            self._log(f"Tool '{tool_name}' not found in registry. Attempting auto-provisioning.", "info")
            
            missing_item_details = {
                "type": "tool",
                "name": tool_name,
                "reason": "not_found",
                "details": f"Tool '{tool_name}' was requested by {self.name} but not found in registry."
            }
            
            try:
                auto_provision_result = await self.orchestrator.auto_provision_agent.handle_trivial_request(
                    context or self._get_launchonomy_context(), missing_item_details
                )
                
                if auto_provision_result:
                    self._log(f"Auto-provisioning successful for tool '{tool_name}': {auto_provision_result}", "info")
                    # Re-check registry after auto-provisioning
                    tool_spec = self.registry.get_tool_spec(tool_name)
                    return tool_spec
                else:
                    self._log(f"Auto-provisioning declined for tool '{tool_name}' (not trivial or rejected).", "warning")
                    
            except Exception as e:
                self._log(f"Error during auto-provisioning attempt for tool '{tool_name}': {str(e)}", "error")
        
        return None
    
    async def _execute_tool(self, tool_spec: Dict[str, Any], parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with the given parameters by making real API calls."""
        if not tool_spec:
            return {"status": "error", "error": "No tool specification provided"}
        
        try:
            tool_name = tool_spec.get("description", "Unknown Tool")
            self._log(f"Executing real tool: {tool_name}", "info")
            
            # Check if this is a webhook-based tool
            if tool_spec.get("type") == "webhook":
                endpoint_details = tool_spec.get("endpoint_details", {})
                url = endpoint_details.get("url")
                method = endpoint_details.get("method", "POST")
                
                if not url:
                    return {"status": "error", "error": "No webhook URL specified in tool spec"}
                
                # Make real HTTP request to the tool endpoint
                import aiohttp
                import json as json_lib
                
                async with aiohttp.ClientSession() as session:
                    headers = {"Content-Type": "application/json"}
                    
                    # Add authentication if specified
                    auth_config = tool_spec.get("authentication", {})
                    if auth_config.get("type") == "bearer":
                        token = auth_config.get("token")
                        if token:
                            headers["Authorization"] = f"Bearer {token}"
                    elif auth_config.get("type") == "api_key":
                        api_key = auth_config.get("api_key")
                        key_header = auth_config.get("header_name", "X-API-Key")
                        if api_key:
                            headers[key_header] = api_key
                    
                    # Prepare request payload
                    payload = {
                        "task_description": f"Execute {tool_name}",
                        "data": parameters,
                        "agent_name": self.name,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    try:
                        if method.upper() == "POST":
                            async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                                if response.status == 200:
                                    result = await response.json()
                                    self._log(f"Tool {tool_name} executed successfully", "info")
                                    return result
                                else:
                                    error_text = await response.text()
                                    self._log(f"Tool {tool_name} returned status {response.status}: {error_text}", "error")
                                    return {
                                        "status": "error",
                                        "error": f"HTTP {response.status}: {error_text}",
                                        "tool_name": tool_name
                                    }
                        elif method.upper() == "GET":
                            async with session.get(url, params=payload, headers=headers, timeout=30) as response:
                                if response.status == 200:
                                    result = await response.json()
                                    self._log(f"Tool {tool_name} executed successfully", "info")
                                    return result
                                else:
                                    error_text = await response.text()
                                    self._log(f"Tool {tool_name} returned status {response.status}: {error_text}", "error")
                                    return {
                                        "status": "error",
                                        "error": f"HTTP {response.status}: {error_text}",
                                        "tool_name": tool_name
                                    }
                        else:
                            return {
                                "status": "error",
                                "error": f"Unsupported HTTP method: {method}",
                                "tool_name": tool_name
                            }
                            
                    except asyncio.TimeoutError:
                        self._log(f"Tool {tool_name} timed out", "error")
                        return {
                            "status": "error",
                            "error": "Request timed out",
                            "tool_name": tool_name
                        }
                    except Exception as e:
                        self._log(f"Tool {tool_name} connection error: {str(e)}", "error")
                        return {
                            "status": "error",
                            "error": f"Connection error: {str(e)}",
                            "tool_name": tool_name
                        }
            else:
                # For non-webhook tools, we need to implement specific logic
                # This should not happen if tools are properly configured as webhooks
                self._log(f"Tool {tool_name} is not a webhook tool. Tool type: {tool_spec.get('type')}", "error")
                return {
                    "status": "error",
                    "error": f"Tool type '{tool_spec.get('type')}' not supported. Only webhook tools are supported.",
                    "tool_name": tool_name
                }
                
        except Exception as e:
            self._log(f"Error executing tool {tool_name}: {str(e)}", "error")
            return {
                "status": "error",
                "error": str(e),
                "tool_name": tool_name
            }
    
    def _format_output(self, status: str, data: Dict[str, Any], **kwargs) -> WorkflowOutput:
        """Format output in standardized format."""
        return WorkflowOutput(
            status=status,
            data=data,
            **kwargs
        )
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> WorkflowOutput:
        """Execute the workflow step. Must be implemented by subclasses."""
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return agent capabilities and requirements."""
        return {
            "name": self.name,
            "type": "workflow_agent",
            "description": self.__class__.__doc__ or f"Workflow agent: {self.name}",
            "required_tools": getattr(self, 'REQUIRED_TOOLS', []),
            "optional_tools": getattr(self, 'OPTIONAL_TOOLS', [])
        } 