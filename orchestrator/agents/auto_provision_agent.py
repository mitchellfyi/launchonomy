import logging
from typing import Dict, Any, Optional

# Assuming Registry is in orchestrator.registry
# from orchestrator.registry import Registry 
# Assuming OrchestratorAgent (COA) will be passed and has propose_and_vote
# from orchestrator.orchestrator_agent import OrchestratorAgent 

logger = logging.getLogger(__name__)

class AutoProvisionAgent:
    """
    Watches for any user prompt or missing-tool error that meets
    "trivial" criteria, then auto-proposes the minimal agent or tool
    to handle it, submits it to consensus, and—if accepted—installs it.
    """
    def __init__(self, registry, coa): # Type hints will be added once COA structure is clear
        """
        Initializes the AutoProvisionAgent.
        :param registry: An instance of the Registry class.
        :param coa: The Consensus Orchestration Authority (likely OrchestratorAgent) 
                    which has a method like propose_and_vote(proposal, voters).
        """
        self.registry = registry
        self.coa = coa
        self.name = "AutoProvisionAgent" # For logging and identification

    def _log(self, message: str, level: str = "info"):
        # Helper for logging, assuming coa might have a more complex logger setup
        log_func = getattr(logger, level, logger.info)
        log_func(f"{self.name}: {message}")
        if hasattr(self.coa, '_log_to_monitor') and callable(self.coa._log_to_monitor):
             # If COA has a way to log to the main UI monitor
            self.coa._log_to_monitor(self.name, message, level)


    def is_trivial(self, context: Dict, missing_item_details: Dict) -> bool:
        """
        Determines if a missing item request is "trivial" enough for auto-provisioning.
        
        :param context: Current operational context (e.g., overall mission, current step).
        :param missing_item_details: Dict with info like {"type": "tool"/"agent", "name": "ItemName", "reason": "not_found"/"user_request", "details": "..."}
        :return: True if trivial, False otherwise.
        """
        # Placeholder: For now, let's consider any missing tool triggered by a "not_found" reason as potentially trivial.
        # A more sophisticated check would involve LLM evaluation of 'details' or specific keywords.
        item_type = missing_item_details.get("type")
        item_name = missing_item_details.get("name")
        reason = missing_item_details.get("reason")

        self._log(f"Assessing triviality for {item_type} '{item_name}'. Reason: {reason}", "debug")

        if item_type == "tool" and reason == "not_found":
            # Example: if context suggests low complexity or it's a known simple tool type
            if "spreadsheet" in item_name.lower() or "calendar" in item_name.lower() or "file_operation" in item_name.lower():
                self._log(f"'{item_name}' considered TRIVIAL for auto-provisioning.", "info")
                return True
        
        # Add criteria for trivial agent requests if necessary
        # if item_type == "agent" and reason == "user_request":
        #     # e.g. if user asks for a very simple task like "summarize this text"
        #     pass

        self._log(f"'{item_name}' NOT considered trivial.", "info")
        return False

    def generate_stub_spec(self, item_name: str, item_type: str, context: Optional[Dict] = None) -> Dict:
        """
        Generates a minimal stub specification for a new tool or agent.
        
        :param item_name: Name of the tool/agent.
        :param item_type: "tool" or "agent".
        :param context: Optional context that might influence the stub.
        :return: A dictionary representing the item's specification.
        """
        self._log(f"Generating stub spec for {item_type} '{item_name}'.", "info")
        if item_type == "tool":
            # For tools, create an n8n/webhook like skeleton
            sanitized_name = item_name.lower().replace(" ", "_").replace("-", "_")
            return {
                "description": f"Auto-provisioned stub for tool: {item_name}",
                "type": "webhook", # Defaulting to webhook type
                "endpoint_details": {
                    "url": f"http://localhost:5678/webhook-test/{sanitized_name}-placeholder", # n8n-like placeholder
                    "method": "POST"
                },
                "authentication": {"type": "none"}, # Placeholder auth
                "request_schema": { # Basic request schema
                    "type": "object",
                    "properties": {
                        "task_description": {"type": "string"},
                        "data": {"type": "object"}
                    },
                    "required": ["task_description"]
                },
                "response_schema": { # Basic response schema
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "result": {"type": "object"}
                    }
                },
                "source": "auto-provisioned"
            }
        elif item_type == "agent":
            # For agents, a minimal spec
            return {
                "description": f"Auto-provisioned stub for agent: {item_name}",
                "capabilities": ["general_task_execution_stub"], # A generic capability
                "tools_required": [], # Initially no specific tools
                "config": {}, # Placeholder for any future config
                "source": "auto-provisioned"
            }
        else:
            self._log(f"Unknown item type for stub spec generation: {item_type}", "error")
            raise ValueError(f"Unknown item type for stub spec generation: {item_type}")

    def handle_trivial_request(self, context: Dict, missing_item_details: Dict) -> Optional[str]:
        """
        Handles a potentially trivial request for a missing tool or agent.
        If deemed trivial, proposes it for consensus and applies if accepted.
        
        :param context: Current operational context.
        :param missing_item_details: Details of the missing item.
        :return: A string message if auto-provisioned, None otherwise.
        """
        item_type = missing_item_details.get("type")
        item_name = missing_item_details.get("name")

        self._log(f"Handling request for missing {item_type}: '{item_name}'", "info")

        if not self.is_trivial(context, missing_item_details):
            return None

        stub_spec = self.generate_stub_spec(item_name, item_type, context)
        
        proposal = {
            "type": f"add_{item_type}", # e.g., "add_tool" or "add_agent"
            "name": item_name,
            "spec": stub_spec
        }
        
        if item_type == "agent":
            # Agents also need an endpoint. For stubs, this could be a placeholder
            # or a pointer to a generic handler within a dynamic agent execution framework.
            # For now, registry.apply_proposal has a default if endpoint isn't provided.
            proposal["endpoint"] = f"stub_agents.{item_name.lower()}.handle_request" # Example

        self._log(f"Generated proposal for '{item_name}': {proposal}", "debug")

        # Use the centralized consensus system
        self._log(f"Submitting proposal for {item_type} '{item_name}' to consensus.", "info")
        try:
            # Import consensus system
            try:
                from orchestrator.consensus import propose_and_vote
            except ImportError:
                from consensus import propose_and_vote
            
            vote_result = propose_and_vote(proposal)
        except Exception as e:
            self._log(f"Error during consensus voting for {item_name}: {e}", "error")
            return None # Or handle error more gracefully

        if vote_result:
            self._log(f"Proposal for '{item_name}' ACCEPTED by consensus.", "info")
            try:
                self.registry.apply_proposal(proposal)
                self._log(f"Successfully auto-provisioned {item_type} '{item_name}' and updated registry.", "info")
                # Here, one might trigger actual n8n workflow creation if item_type is tool
                # e.g., await self.setup_n8n_webhook_placeholder(item_name, stub_spec)
                return f"Auto-provisioned {item_type} '{item_name}'. You can now use it."
            except Exception as e:
                self._log(f"Error applying accepted proposal for {item_name} to registry: {e}", "error")
                return f"Error applying auto-provisioned {item_type} '{item_name}' to registry after acceptance."
        else:
            self._log(f"Proposal for '{item_name}' REJECTED by consensus.", "warning")
            return None
            
# Example (conceptual) for n8n interaction - to be developed if n8n API is available and configured
# async def setup_n8n_webhook_placeholder(self, tool_name: str, tool_spec: Dict):
#     if tool_spec.get("type") == "webhook" and "n8n.local" in tool_spec.get("endpoint_details", {}).get("url", ""):
#         self._log(f"Attempting to set up n8n webhook placeholder for {tool_name}", "info")
#         # 1. Check if n8n API client is available/configured
#         # 2. Prepare a minimal n8n workflow JSON that listens to the placeholder URL
#         #    and perhaps just returns a static success or logs the input.
#         # 3. Use n8n API to create/import this workflow.
#         # This is a complex step dependent on n8n's API and auth.
#         self._log(f"(Placeholder) n8n webhook for {tool_name} would be set up here.", "info")
#         pass

# To ensure the orchestrator/agents directory is considered a package for imports if needed:
# Create an __init__.py file in orchestrator/agents/
# (This edit_file call will do that, or it can be done manually) 