import json
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_FILE = "registry.json"  # Default filename in the same directory

class Registry:
    """
    Central registry for managing agents and tools in the Launchonomy system.
    
    The Registry provides persistent storage and management for:
    - Agent specifications and instances
    - Tool definitions and configurations
    - Auto-provisioning capabilities
    - Dynamic agent instantiation
    
    Features:
    - JSON-based persistence
    - Agent instance caching
    - Auto-provisioning support
    - Tool stub generation
    - Module/class-based agent loading
    
    Attributes:
        filepath: Path to the registry JSON file
        agents: Dictionary of agent specifications
        tools: Dictionary of tool specifications
        _agent_instances: Cache of instantiated agent objects
    """
    
    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath if filepath else os.path.join(os.path.dirname(__file__), DEFAULT_REGISTRY_FILE)
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._agent_instances: Dict[str, Any] = {}  # Cache for instantiated agents
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

    def add_agent(self, name: str, endpoint: str, certified: bool = False, spec: Optional[Dict[str, Any]] = None, persist: bool = True):
        """Adds or updates an agent in the registry."""
        if not name or not endpoint:
            logger.warning("Agent name and endpoint are required to add an agent.")
            return
        self.agents[name] = {"endpoint": endpoint, "certified": certified, "spec": spec or {}}
        logger.info(f"Agent '{name}' added/updated in the registry.")
        if persist:
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

    def get_agent(self, agent_name: str, mission_context: Optional[Dict[str, Any]] = None):
        """
        Get an instantiated agent by name. Returns cached instance if available,
        otherwise creates a new instance based on the registry specification.
        
        Args:
            agent_name: Name of the agent to retrieve
            mission_context: Optional mission context to pass to workflow agents
            
        Returns:
            Agent instance or None if not found/failed to instantiate
        """
        # Return cached instance if available
        if agent_name in self._agent_instances:
            return self._agent_instances[agent_name]
        
        # Get agent specification
        agent_spec = self.get_agent_spec(agent_name)
        if not agent_spec:
            logger.error(f"Agent '{agent_name}' not found in registry")
            return None
        
        try:
            # Handle workflow agents (those with module/class specification)
            if 'module' in agent_spec and 'class' in agent_spec:
                module_name = agent_spec['module']
                class_name = agent_spec['class']
                
                # Import the module and get the class
                import importlib
                module = importlib.import_module(module_name)
                agent_class = getattr(module, class_name)
                
                # Instantiate workflow agent with registry and mission context
                agent_instance = agent_class(self, mission_context or {})
                
            else:
                # Handle other agent types (like C-Suite agents)
                # For now, return a placeholder that can execute basic operations
                logger.warning(f"Agent '{agent_name}' does not have module/class specification. Creating placeholder.")
                agent_instance = AgentPlaceholder(agent_name, agent_spec)
            
            # Cache the instance
            self._agent_instances[agent_name] = agent_instance
            logger.info(f"Successfully instantiated agent: {agent_name}")
            return agent_instance
            
        except Exception as e:
            logger.error(f"Failed to instantiate agent '{agent_name}': {str(e)}", exc_info=True)
            return None

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
            # Emit stub file for the new tool
            self._emit_tool_stub(name, spec)
        else:
            logger.warning(f"Unknown proposal type: {proposal_type}")

    def _emit_tool_stub(self, tool_name: str, tool_spec: Dict[str, Any]):
        """Emits a stub JSON file for a tool in tools/stubs/ directory."""
        try:
            # Create the stubs directory if it doesn't exist
            stubs_dir = "tools/stubs"
            os.makedirs(stubs_dir, exist_ok=True)
            
            # Handle name collisions by checking if file exists and appending version suffix
            base_filename = f"{tool_name}.json"
            stub_filepath = os.path.join(stubs_dir, base_filename)
            
            # If file exists, append version suffix
            if os.path.exists(stub_filepath):
                version = 1
                while True:
                    versioned_filename = f"{tool_name}_v{version}.json"
                    versioned_filepath = os.path.join(stubs_dir, versioned_filename)
                    if not os.path.exists(versioned_filepath):
                        stub_filepath = versioned_filepath
                        logger.info(f"Tool stub file already exists, creating versioned file: {versioned_filename}")
                        break
                    version += 1
            
            # Write the tool spec to the stub file
            with open(stub_filepath, "w") as f:
                json.dump(tool_spec, f, indent=2)
            
            logger.info(f"Tool stub file created: {stub_filepath}")
            
        except Exception as e:
            logger.error(f"Error creating tool stub file for '{tool_name}': {e}", exc_info=True)

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

    def get_agent_info(self, agent_name: str) -> Optional[Dict[str, str]]:
        """
        Retrieves agent module and class information for instantiation.
        Returns dict with 'module' and 'class' keys if available.
        """
        agent_spec = self.get_agent_spec(agent_name)
        if not agent_spec:
            return None
        
        # First check if module and class are at the top level (new format)
        if 'module' in agent_spec and 'class' in agent_spec:
            return {
                "module": agent_spec['module'],
                "class": agent_spec['class']
            }
        
        # Then check if module and class are in the spec (alternative format)
        spec = agent_spec.get('spec', {})
        if 'module' in spec and 'class' in spec:
            return {
                "module": spec['module'],
                "class": spec['class']
            }
        
        # Fallback: try to derive from endpoint for backward compatibility
        endpoint = agent_spec.get('endpoint', '')
        if '.' in endpoint:
            parts = endpoint.split('.')
            if len(parts) >= 2:
                # Assume format like "module.ClassName.method" or "module.ClassName"
                module = parts[0]
                class_name = parts[1]
                return {
                    "module": module,
                    "class": class_name
                }
        
        return None


class AgentPlaceholder:
    """Placeholder for agents that don't have direct module/class implementations."""
    
    def __init__(self, name: str, spec: Dict[str, Any]):
        self.name = name
        self.spec = spec
        
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute method for placeholder agents."""
        logger.info(f"Executing placeholder agent: {self.name}")
        
        # Return a basic response structure
        return {
            "agent": self.name,
            "status": "executed",
            "message": f"Placeholder execution for {self.name}",
            "context_received": bool(context),
            "spec": self.spec.get('spec', {})
        }


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