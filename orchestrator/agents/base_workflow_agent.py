import json
import logging
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
    
    def __init__(self, name: str, registry=None, orchestrator=None):
        self.name = name
        self.registry = registry
        self.orchestrator = orchestrator
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
        
        if self.registry:
            context["available_agents"] = self.registry.list_agent_names()
            context["available_tools"] = self.registry.list_tool_names()
        
        return context
    
    def _get_tool_from_registry(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get a tool specification from the registry."""
        if self.registry:
            return self.registry.get_tool_spec(tool_name)
        return None
    
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