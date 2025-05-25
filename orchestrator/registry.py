import json
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_FILE = "registry.json"  # Default filename in the same directory

class Registry:
    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath if filepath else os.path.join(os.path.dirname(__file__), DEFAULT_REGISTRY_FILE)
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self):
        """Loads the registry from the JSON file."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                    self.agents = data.get("agents", {})
                    self.tools = data.get("tools", {})
                logger.info(f"Registry loaded from {self.filepath}")
            else:
                logger.info(f"Registry file {self.filepath} not found. Starting with an empty registry.")
                self.agents = {}
                self.tools = {}
        except Exception as e:
            logger.error(f"Error loading registry from {self.filepath}: {e}", exc_info=True)
            self.agents = {}
            self.tools = {}

    def save(self):
        """Saves the current registry to the JSON file."""
        try:
            with open(self.filepath, 'w') as f:
                json.dump({"agents": self.agents, "tools": self.tools}, f, indent=2)
            logger.info(f"Registry saved to {self.filepath}")
        except Exception as e:
            logger.error(f"Error saving registry to {self.filepath}: {e}", exc_info=True)

    def add_agent(self, name: str, endpoint: str, certified: bool = False, spec: Optional[Dict[str, Any]] = None):
        """Adds or updates an agent in the registry."""
        if not name or not endpoint:
            logger.warning("Agent name and endpoint are required to add an agent.")
            return
        self.agents[name] = {"endpoint": endpoint, "certified": certified, "spec": spec or {}}
        logger.info(f"Agent '{name}' added/updated in the registry.")
        self.save()

    def add_tool(self, name: str, spec: Dict[str, Any]):
        """Adds or updates a tool in the registry."""
        if not name or not spec:
            logger.warning("Tool name and specification are required to add a tool.")
            return
        self.tools[name] = spec
        logger.info(f"Tool '{name}' added/updated in the registry.")
        self.save()

    def get_agent_spec(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieves an agent's full specification entry."""
        return self.agents.get(name)

    def get_tool_spec(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a tool's specification."""
        return self.tools.get(name)

    def apply_proposal(self, proposal: Dict[str, Any]):
        """Applies a provisioning proposal to the registry."""
        proposal_type = proposal.get("type")
        name = proposal.get("name")
        spec = proposal.get("spec")
        endpoint = proposal.get("endpoint")  # For agents

        if not proposal_type or not name or not spec:
            logger.warning(f"Invalid proposal: {proposal}. Missing type, name, or spec.")
            return

        if proposal_type == "add_agent":
            if not endpoint:
                endpoint = f"auto_provisioned_agents.{name.lower()}.handle_request" 
            self.add_agent(name, endpoint=endpoint, certified=False, spec=spec)
        elif proposal_type == "add_tool":
            self.add_tool(name, spec)
        else:
            logger.warning(f"Unknown proposal type: {proposal_type}")

    def list_agent_names(self) -> List[str]:
        """Returns a list of all registered agent names."""
        return list(self.agents.keys())

    def list_tool_names(self) -> List[str]:
        """Returns a list of all registered tool names."""
        return list(self.tools.keys())

    def get_agent_endpoint(self, agent_name: str) -> Optional[str]:
        """Retrieves the endpoint for a given agent."""
        agent_info = self.agents.get(agent_name)
        return agent_info.get("endpoint") if agent_info else None

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    
    registry_dir = os.path.dirname(__file__)
    if not os.path.exists(registry_dir):
        os.makedirs(registry_dir)

    registry = Registry()

    registry.add_agent("OrchestrationAgent", endpoint="orchestrator_agent.OrchestrationAgent", certified=True)
    registry.add_agent("AutoProvisionAgent", endpoint="auto_provision_agent.AutoProvisionAgent.handle_trivial_request", certified=True)
    registry.add_tool("NamecheapDomainAPI", {"url": "https://api.namecheap.com/xml.response", "auth_type": "api_key"})

    print("Current Agents:", registry.list_agent_names())
    print("Research Agent Spec:", registry.get_agent_spec("Research"))
    print("AutoProvision Agent Spec:", registry.get_agent_spec("AutoProvisionAgent"))
    print("Namecheap Tool Spec:", registry.get_tool_spec("NamecheapDomainAPI"))

    new_tool_proposal = {
        "type": "add_tool",
        "name": "SimpleSpreadsheetTool",
        "spec": {
            "description": "A basic tool for spreadsheet operations",
            "webhook_url": "https://n8n.local/webhook/simplespreadsheettool",
            "methods": ["POST"],
            "payload_schema": {"type": "object", "properties": {"data": {"type": "array"}}}
        }
    }
    registry.apply_proposal(new_tool_proposal)
    print("SimpleSpreadsheetTool Spec:", registry.get_tool_spec("SimpleSpreadsheetTool"))

    new_agent_proposal = {
        "type": "add_agent",
        "name": "QuickResponderAgent",
        "endpoint": "quick_responder.handle",
        "spec": {
            "description": "Responds quickly to simple queries.",
            "capabilities": ["faq", "greeting"]
        }
    }
    registry.apply_proposal(new_agent_proposal)
    print("QuickResponderAgent Spec:", registry.get_agent_spec("QuickResponderAgent")) 