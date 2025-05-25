# orchestrator/orchestrator_agent.py

import json
import os
import logging
import re # Added for regex in JSON parsing
import asyncio # Added for sleep in retries
import importlib # Added for dynamic agent loading
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, asdict, field # Added field
from autogen_core import RoutedAgent
from autogen_core.models import SystemMessage, UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
try:
    from orchestrator.registry import Registry
    from orchestrator.agents.auto_provision_agent import AutoProvisionAgent
except ImportError:
    # Fallback for when running from within orchestrator directory
    from registry import Registry
    from agents.auto_provision_agent import AutoProvisionAgent

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class TemplateError(Exception):
    """Raised when a template cannot be loaded."""
    pass

class AgentCommunicationError(Exception):
    """Raised when agent communication fails."""
    pass

def load_template(name: str) -> str:
    """Load a template file with error handling."""
    try:
        # Try relative path first (when running from orchestrator directory)
        path = os.path.join("templates", f"{name}.txt")
        if not os.path.exists(path):
            # Fallback to absolute path (when running from parent directory)
            path = os.path.join("orchestrator", "templates", f"{name}.txt")
        
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Template file not found: {path}")
        raise TemplateError(f"Template '{name}' not found")
    except Exception as e:
        logger.error(f"Error loading template {name}: {str(e)}")
        raise TemplateError(f"Error loading template '{name}': {str(e)}")

# Load your distilled 250-word primer
try:
    SYSTEM_PROMPT = load_template("orch_primer")
except TemplateError as e:
    logger.critical("Failed to load orchestrator primer")
    raise

@dataclass
class MissionLog:
    """Master mission log that tracks all cycles and provides context for resumable missions."""
    mission_name: str
    mission_id: str
    overall_mission: str
    start_timestamp: str
    last_updated: str
    status: str  # "active", "paused", "completed", "failed"
    
    # Cycle tracking
    cycle_ids: List[str] = field(default_factory=list)
    current_cycle_id: Optional[str] = None
    completed_cycles: int = 0
    failed_cycles: int = 0
    
    # Mission-level metrics
    total_mission_cost: float = 0.0
    total_mission_time_minutes: float = 0.0
    
    # Context for resumption
    mission_context: dict = field(default_factory=dict)
    key_learnings: List[str] = field(default_factory=list)
    persistent_agents: List[str] = field(default_factory=list)
    
    # Linking and history
    cycle_summaries: List[dict] = field(default_factory=list)
    mission_milestones: List[dict] = field(default_factory=list)
    
    # Metadata
    created_by: str = "OrchestrationAgent"
    tags: List[str] = field(default_factory=list)

@dataclass
class CycleLog:
    mission_id: str
    timestamp: str
    overall_mission: str
    current_decision_focus: str
    status: str
    error_message: Optional[str] = None
    
    agent_management_events: List[dict] = field(default_factory=list)
    orchestrator_interactions: List[dict] = field(default_factory=list)
    specialist_interactions: List[dict] = field(default_factory=list)
    review_interactions: List[dict] = field(default_factory=list)
    execution_attempts: List[dict] = field(default_factory=list)
    
    json_parsing_attempts: List[dict] = field(default_factory=list)

    decisions_archive: List[dict] = field(default_factory=list)
    reviews_archive: List[dict] = field(default_factory=list)
    
    kpi_outcomes: dict = field(default_factory=dict)
    total_loops_in_decision_cycle: int = 0
    total_cycle_cost: float = 0.0

    # Enhanced linking for resumable missions
    previous_cycle_id: Optional[str] = None
    next_cycle_id: Optional[str] = None
    parent_mission_id: Optional[str] = None
    cycle_sequence_number: int = 0
    
    # Context from previous cycles
    previous_cycles_context: List[dict] = field(default_factory=list)
    key_insights_from_previous: List[str] = field(default_factory=list)
    
    # Cycle-specific metadata
    cycle_duration_minutes: float = 0.0
    agents_used: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)

class OrchestrationAgent(RoutedAgent):
    def __init__(self, client):
        super().__init__(SYSTEM_PROMPT)
        self._client = client
        self.mission_logs: List[CycleLog] = []
        self.current_mission_log: Optional[MissionLog] = None
        self.MAX_REVISION_LOOPS = 3
        self.MAX_JSON_RETRIES = 2 # Max retries for getting valid JSON
        self.CONFIDENCE_THRESHOLD = 0.8
        self.log_callback = None
        self.name = "OrchestrationAgent"
        self.last_revision_plan: Optional[str] = None # For decision loop

        # Load registry and instantiate all registered agents
        self.registry = Registry() # Will load from orchestrator/registry.json
        self.agents: Dict[str, RoutedAgent] = {}
        
        # Load and instantiate all registered agents at startup
        self._load_registered_agents()
        
        # Ensure AutoProvisionAgent is initialized correctly
        self.auto_provision_agent = AutoProvisionAgent(registry=self.registry, coa=self)
        
        # Add self and AutoProvisionAgent to registry if not already there (for awareness)
        # The endpoint for OrchestrationAgent itself isn't typically called like a specialist
        if not self.registry.get_agent_spec(self.name):
            self.registry.add_agent(name=self.name, endpoint="internal", certified=True, spec={"description": "The main orchestrator."})
        if not self.registry.get_agent_spec(self.auto_provision_agent.name):
            self.registry.add_agent(
                name=self.auto_provision_agent.name, 
                endpoint="auto_provision_agent.AutoProvisionAgent.handle_trivial_request", # As per previous setup
                certified=True, 
                spec={"description": "Handles auto-provisioning of trivial tools/agents."}
            )
        
        # Bootstrap C-Suite agents as described in the primer
        self.c_suite_bootstrapped = False  # Track if bootstrap has been called

    def set_log_callback(self, callback):
        """Set callback for CLI logging."""
        self.log_callback = callback

    def _load_registered_agents(self):
        """Load and instantiate all registered agents at startup."""
        self._log("Loading registered agents from registry...", "info")
        
        agent_names = self.registry.list_agent_names()
        loaded_count = 0
        failed_count = 0
        
        for name in agent_names:
            try:
                # Skip self-reference to avoid circular instantiation
                if name == self.name:
                    continue
                    
                info = self.registry.get_agent_info(name)
                if info and 'module' in info and 'class' in info:
                    # Dynamically import and instantiate the agent
                    module = importlib.import_module(info["module"])
                    cls = getattr(module, info["class"])
                    
                    # Instantiate with registry and self as COA (Chief Orchestration Agent)
                    agent_instance = cls(registry=self.registry, coa=self)
                    self.agents[name] = agent_instance
                    loaded_count += 1
                    self._log(f"✅ Loaded agent: {name} from {info['module']}.{info['class']}", "debug")
                    
                else:
                    # For agents without module/class info, create placeholder or skip
                    agent_spec = self.registry.get_agent_spec(name)
                    if agent_spec:
                        self._log(f"⚠️ Agent {name} has no module/class info, will be handled dynamically", "debug")
                    else:
                        self._log(f"❌ Agent {name} has no specification", "warning")
                        failed_count += 1
                        
            except Exception as e:
                self._log(f"❌ Failed to load agent {name}: {str(e)}", "error")
                failed_count += 1
        
        self._log(f"Agent loading complete: {loaded_count} loaded, {failed_count} failed, {len(agent_names)} total", "info")

    def create_or_load_mission(self, mission_name: str, overall_mission: str, resume_existing: bool = True) -> MissionLog:
        """Create a new mission or load an existing one for resumable missions."""
        mission_log_dir = "mission_logs"
        os.makedirs(mission_log_dir, exist_ok=True)
        
        # Generate mission ID based on name and timestamp
        safe_mission_name = re.sub(r'\W+', '_', mission_name.lower())
        mission_id = f"mission_{safe_mission_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        mission_file_path = os.path.join(mission_log_dir, f"{mission_id}.json")
        
        # Try to find existing mission if resume_existing is True
        if resume_existing:
            existing_mission = self._find_existing_mission(mission_name, overall_mission)
            if existing_mission:
                self._log(f"Resuming existing mission: {existing_mission.mission_id}", "info")
                self.current_mission_log = existing_mission
                return existing_mission
        
        # Create new mission
        self._log(f"Creating new mission: {mission_id}", "info")
        mission_log = MissionLog(
            mission_name=mission_name,
            mission_id=mission_id,
            overall_mission=overall_mission,
            start_timestamp=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            status="active",
            mission_context={"overall_mission": overall_mission},
            persistent_agents=list(self.agents.keys())
        )
        
        # Save mission log
        self._save_mission_log(mission_log)
        self.current_mission_log = mission_log
        return mission_log

    def _find_existing_mission(self, mission_name: str, overall_mission: str) -> Optional[MissionLog]:
        """Find an existing mission that matches the name and mission description."""
        mission_log_dir = "mission_logs"
        if not os.path.exists(mission_log_dir):
            return None
        
        # Look for mission files (not cycle files)
        for filename in os.listdir(mission_log_dir):
            if filename.startswith("mission_") and filename.endswith(".json") and not filename.startswith("cycle_"):
                try:
                    file_path = os.path.join(mission_log_dir, filename)
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    # Check if this matches our mission
                    if (data.get("mission_name") == mission_name and 
                        data.get("overall_mission") == overall_mission and
                        data.get("status") in ["active", "paused"]):
                        
                        # Convert to MissionLog object
                        mission_log = MissionLog(**data)
                        return mission_log
                        
                except Exception as e:
                    self._log(f"Error reading mission file {filename}: {str(e)}", "warning")
                    continue
        
        return None

    def _save_mission_log(self, mission_log: MissionLog):
        """Save mission log to disk."""
        mission_log_dir = "mission_logs"
        os.makedirs(mission_log_dir, exist_ok=True)
        
        mission_file_path = os.path.join(mission_log_dir, f"{mission_log.mission_id}.json")
        try:
            with open(mission_file_path, "w") as f:
                json.dump(asdict(mission_log), f, indent=2)
            self._log(f"Mission log saved to {mission_file_path}", "debug")
        except Exception as e:
            self._log(f"Error saving mission log {mission_file_path}: {str(e)}", "error")

    def _update_mission_log(self, cycle_log: CycleLog):
        """Update the current mission log with information from a completed cycle."""
        if not self.current_mission_log:
            self._log("No current mission log to update", "warning")
            return
        
        # Update mission log with cycle information
        self.current_mission_log.cycle_ids.append(cycle_log.mission_id)
        self.current_mission_log.current_cycle_id = cycle_log.mission_id
        self.current_mission_log.last_updated = datetime.now().isoformat()
        self.current_mission_log.total_mission_cost += cycle_log.total_cycle_cost
        self.current_mission_log.total_mission_time_minutes += cycle_log.cycle_duration_minutes
        
        # Update cycle counts
        if cycle_log.status == "completed_cycle_success":
            self.current_mission_log.completed_cycles += 1
        else:
            self.current_mission_log.failed_cycles += 1
        
        # Add cycle summary for context
        cycle_summary = {
            "cycle_id": cycle_log.mission_id,
            "decision_focus": cycle_log.current_decision_focus,
            "status": cycle_log.status,
            "cost": cycle_log.total_cycle_cost,
            "duration_minutes": cycle_log.cycle_duration_minutes,
            "agents_used": cycle_log.agents_used,
            "key_outcomes": cycle_log.kpi_outcomes,
            "timestamp": cycle_log.timestamp
        }
        self.current_mission_log.cycle_summaries.append(cycle_summary)
        
        # Extract key learnings from retrospective if available
        for interaction in cycle_log.orchestrator_interactions:
            if interaction.get("type") == "retrospective_analysis" and interaction.get("parsed_output"):
                # Extract actionable recommendations from retrospective
                retro_text = interaction["parsed_output"]
                if "Key Learnings" in retro_text or "Actionable Recommendations" in retro_text:
                    learning_entry = f"Cycle {len(self.current_mission_log.cycle_ids)}: {retro_text.split('Key Learnings')[1].split('Actionable Recommendations')[0].strip() if 'Key Learnings' in retro_text else 'General insights from cycle'}"
                    self.current_mission_log.key_learnings.append(learning_entry)
        
        # Save updated mission log
        self._save_mission_log(self.current_mission_log)

    def _get_previous_cycles_context(self, limit: int = 5) -> List[dict]:
        """Get context from previous cycles for the current mission."""
        if not self.current_mission_log:
            return []
        
        # Return the most recent cycle summaries (up to limit)
        return self.current_mission_log.cycle_summaries[-limit:] if self.current_mission_log.cycle_summaries else []

    def _link_cycle_to_previous(self, current_cycle: CycleLog) -> CycleLog:
        """Link the current cycle to the previous cycle and add context."""
        if not self.current_mission_log:
            return current_cycle
        
        # Set parent mission
        current_cycle.parent_mission_id = self.current_mission_log.mission_id
        current_cycle.cycle_sequence_number = len(self.current_mission_log.cycle_ids) + 1
        
        # Link to previous cycle
        if self.current_mission_log.cycle_ids:
            previous_cycle_id = self.current_mission_log.cycle_ids[-1]
            current_cycle.previous_cycle_id = previous_cycle_id
            
            # Update the previous cycle's next_cycle_id
            self._update_previous_cycle_link(previous_cycle_id, current_cycle.mission_id)
        
        # Add context from previous cycles
        current_cycle.previous_cycles_context = self._get_previous_cycles_context()
        
        # Add key insights from mission learnings
        current_cycle.key_insights_from_previous = self.current_mission_log.key_learnings[-3:] if self.current_mission_log.key_learnings else []
        
        return current_cycle

    def _update_previous_cycle_link(self, previous_cycle_id: str, current_cycle_id: str):
        """Update the previous cycle's next_cycle_id field."""
        log_dir = "mission_logs"
        previous_cycle_file = os.path.join(log_dir, f"{previous_cycle_id}.json")
        
        if os.path.exists(previous_cycle_file):
            try:
                with open(previous_cycle_file, 'r') as f:
                    cycle_data = json.load(f)
                
                cycle_data["next_cycle_id"] = current_cycle_id
                
                with open(previous_cycle_file, 'w') as f:
                    json.dump(cycle_data, f, indent=2)
                
                self._log(f"Updated previous cycle {previous_cycle_id} with next_cycle_id: {current_cycle_id}", "debug")
            except Exception as e:
                self._log(f"Error updating previous cycle link: {str(e)}", "warning")

    def get_mission_context_for_agents(self) -> dict:
        """Get comprehensive mission context for agent decision-making."""
        if not self.current_mission_log:
            return {}
        
        return {
            "mission_id": self.current_mission_log.mission_id,
            "overall_mission": self.current_mission_log.overall_mission,
            "cycles_completed": self.current_mission_log.completed_cycles,
            "total_cost_so_far": self.current_mission_log.total_mission_cost,
            "key_learnings": self.current_mission_log.key_learnings,
            "recent_cycles": self._get_previous_cycles_context(3),
            "persistent_agents": self.current_mission_log.persistent_agents,
            "mission_status": self.current_mission_log.status
        }

    async def bootstrap_c_suite(self, mission_context: str = ""):
        """
        Bootstrap the C-Suite agents as described in the orchestrator primer.
        Each agent is seeded with the full current context in their initial system prompt.
        """
        if self.c_suite_bootstrapped:
            self._log("C-Suite already bootstrapped, skipping.", "info")
            return

        self._log("Bootstrapping C-Suite agents as per orchestrator primer...", "info")
        
        # Define the C-Suite agents as specified in the primer
        c_suite_specs = {
            "CEO-Agent": {
                "persona": "Chief Executive Officer focused on vision & prioritization",
                "expertise": "strategic vision, business prioritization, executive decision-making, market positioning",
                "responsibilities": "defines vision & prioritization for the business mission"
            },
            "CRO-Agent": {
                "persona": "Chief Revenue Officer focused on customer acquisition & revenue",
                "expertise": "sales strategy, customer acquisition, revenue optimization, conversion funnels",
                "responsibilities": "focuses on customer acquisition & revenue generation"
            },
            "CTO-Agent": {
                "persona": "Chief Technology Officer owning technical infrastructure & tools",
                "expertise": "technical architecture, infrastructure, development tools, system integration",
                "responsibilities": "owns technical infrastructure & tools implementation"
            },
            "CPO-Agent": {
                "persona": "Chief Product Officer owning product/UX experiments & A/B tests",
                "expertise": "product strategy, user experience, A/B testing, product optimization",
                "responsibilities": "owns product/UX experiments & A/B tests"
            },
            "CMO-Agent": {
                "persona": "Chief Marketing Officer owning marketing channels & growth hacks",
                "expertise": "marketing strategy, growth hacking, channel optimization, brand positioning",
                "responsibilities": "owns marketing channels & growth hacks"
            },
            "CDO-Agent": {
                "persona": "Chief Data Officer owning data strategy, quality, and insights",
                "expertise": "data strategy, analytics, data quality, business intelligence",
                "responsibilities": "owns data strategy, quality, and insights"
            },
            "CCO-Agent": {
                "persona": "Chief Compliance Officer owning compliance, legal, and regulatory risk",
                "expertise": "legal compliance, regulatory requirements, risk management, business law",
                "responsibilities": "owns compliance, legal, and regulatory risk"
            },
            "CFO-Agent": {
                "persona": "Chief Financial Officer overseeing budgets, profitability & reinvestment strategy",
                "expertise": "financial planning, budget management, profitability analysis, investment strategy",
                "responsibilities": "oversees budgets, profitability & reinvestment strategy"
            },
            "CCSO-Agent": {
                "persona": "Chief Customer Success Officer owning post-purchase journey: onboarding, support, retention & advocacy",
                "expertise": "customer success, onboarding, support systems, retention strategies",
                "responsibilities": "owns post-purchase journey: onboarding, support, retention & advocacy"
            }
        }

        bootstrap_cost = 0.0
        
        for agent_name, spec in c_suite_specs.items():
            try:
                # Check if agent already exists
                if agent_name in self.agents:
                    self._log(f"C-Suite agent {agent_name} already exists, skipping creation.", "debug")
                    continue
                
                # Create comprehensive system prompt with mission context
                system_prompt = f"""You are {agent_name}, the {spec['persona']}.

Mission Context: {mission_context}

Your Role & Responsibilities:
{spec['responsibilities']}

Your Core Expertise:
{spec['expertise']}

Operating Principles (from Launchonomy Primer):
• Objective: Acquire the first paying customer as fast as possible, then ignite exponential, profitable growth—automatically and without human plan approvals
• Budget Constraint: Initial budget $500, profit guardrail: total costs never exceed 20% of revenue
• Self-Governing: You participate in unanimous consensus voting for all proposals
• Specialization: When faced with tasks beyond your scope, propose creation of new agents/tools
• No Human Approval: Plans never go to humans—only system-critical failures do

You are part of the founding C-Suite team working together through consensus to achieve the mission. Always consider your specialized perspective while collaborating with other C-Suite agents for unanimous decisions."""

                # Create the agent
                agent = await self._create_agent(agent_name, spec['persona'], system_prompt)
                
                # Add to registry with C-Suite designation
                self.registry.add_agent(
                    name=agent_name,
                    endpoint=f"c_suite.{agent_name.lower().replace('-', '_')}.handle_request",
                    certified=True,
                    spec={
                        "description": spec['persona'],
                        "expertise": spec['expertise'],
                        "responsibilities": spec['responsibilities'],
                        "type": "c_suite_founding_member",
                        "source": "bootstrapped"
                    }
                )
                
                self._log(f"✅ Bootstrapped {agent_name}: {spec['persona']}", "info")
                
            except Exception as e:
                self._log(f"❌ Failed to bootstrap {agent_name}: {str(e)}", "error")
                # Continue with other agents even if one fails
        
        self.c_suite_bootstrapped = True
        self._log(f"🎉 C-Suite bootstrap complete! Active agents: {len(self.agents)}", "info")
        
        return bootstrap_cost

    def _log(self, message: str, msg_type: str = "info"):
        """Log a message using the callback if available."""
        # Ensure message is a string
        if not isinstance(message, str):
            try:
                message = str(message)
            except Exception:
                message = "Failed to convert log message to string."

        if self.log_callback:
            self.log_callback(self.name, message, msg_type)
        # Standard logging as well
        if msg_type == "error":
            logger.error(f"{self.name}: {message}")
        elif msg_type == "warning":
            logger.warning(f"{self.name}: {message}")
        elif msg_type == "debug":
            logger.debug(f"{self.name}: {message}")
        else:
            logger.info(f"{self.name}: {message}")

    async def _ask_agent(self, agent: RoutedAgent, prompt: str, system_prompt: Optional[str] = None, response_format_json: bool = False) -> Tuple[str, float]:
        """
        Unified method for agent interactions. If response_format_json is True, it will augment the prompt to request JSON.
        Returns the response content and the cost of the call.
        """
        agent_name = getattr(agent, 'name', 'UnnamedAgent')
        cost = 0.0 # Initialize cost
        
        # Augment prompt if JSON is expected, to comply with OpenAI's JSON mode requirement if it were enabled at client level
        # or to simply improve chances of getting JSON via prompt engineering.
        final_prompt = prompt
        if response_format_json:
            if "json" not in prompt.lower(): # Avoid duplicating if already there
                final_prompt += "\n\nYour response MUST be a valid JSON object. Do not include any other text before or after the JSON object."
            self._log(f"Augmented prompt for JSON response from {agent_name}.", "debug")
        else:
            self._log(f"Standard response format for {agent_name}.", "debug")

        try:
            msgs = [UserMessage(content=final_prompt, source="user")]
            
            current_system_prompt_content = system_prompt
            
            if not current_system_prompt_content:
                if hasattr(agent, 'system_prompt'):
                    agent_native_prompt = agent.system_prompt
                    if isinstance(agent_native_prompt, SystemMessage):
                        current_system_prompt_content = agent_native_prompt.content
                    elif isinstance(agent_native_prompt, str):
                        current_system_prompt_content = agent_native_prompt

            if current_system_prompt_content:
                msgs.insert(0, SystemMessage(content=current_system_prompt_content, source="system"))
            
            self._log(f"Asking {agent_name}: '{final_prompt[:150]}...' with sys_prompt: '{str(current_system_prompt_content)[:100]}...'", "debug")
            resp = await agent._client.create(msgs)

            if not resp or not resp.content:
                raise AgentCommunicationError(f"Empty response from agent {agent_name}")
            
            # Attempt to get cost from response if available (depends on client implementation)
            if hasattr(resp, 'cost') and isinstance(resp.cost, (int, float)):
                cost = float(resp.cost)
            elif hasattr(resp, 'usage') and resp.usage: # Check if usage attribute exists and is not None
                # Try accessing as an attribute first (common for objects)
                if hasattr(resp.usage, 'total_cost') and isinstance(resp.usage.total_cost, (int, float)):
                    cost = float(resp.usage.total_cost)
                # Else, try accessing as a dictionary key (common for dicts)
                elif isinstance(resp.usage, dict) and 'total_cost' in resp.usage and isinstance(resp.usage['total_cost'], (int, float)):
                    cost = float(resp.usage['total_cost'])
                # Fallback or further checks can be added here if needed, e.g., for total_tokens
                # else:
                #     self._log(f"Cost not found in resp.usage or is not a number. Usage object: {resp.usage}", "debug")

            return resp.content.strip(), cost
        except Exception as e:
            self._log(f"Error in agent communication with {agent_name}: {str(e)}", "error")
            raise AgentCommunicationError(f"Failed to communicate with agent {agent_name}: {str(e)}")

    async def _ask_orchestrator(self, prompt: str, response_format_json: bool = False) -> Tuple[str, float]:
        """Ask the orchestrator agent (self) a question. Returns response content and cost."""
        return await self._ask_agent(self, prompt, response_format_json=response_format_json)

    def _extract_json_from_string(self, text: str) -> Optional[str]:
        """Extracts the first valid JSON object from a string, looking for ```json ... ``` or raw object."""
        # First try to find JSON in code blocks: ```json ... ```
        json_block_match = re.search(r'```json\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```', text, re.DOTALL)
        if json_block_match:
            return json_block_match.group(1)
        
        # Then try to find raw JSON objects or arrays
        raw_json_match = re.search(r'(\{[\s\S]*?\}|\[[\s\S]*?\])', text, re.DOTALL)
        if raw_json_match:
            return raw_json_match.group(1)
        
        return None

    async def _get_json_response(self, 
                                 agent: RoutedAgent, 
                                 prompt: str, 
                                 error_msg: str, 
                                 json_parsing_log_list: List[dict], # Pass the list to log attempts
                                 retry_count: int = 0) -> Tuple[Dict[str, Any], float]:
        """
        Get JSON response from an agent with extraction, error handling, and retries.
        Logs attempts to json_parsing_log_list.
        Returns the parsed JSON and accumulated cost.
        """
        agent_name = getattr(agent, 'name', 'UnnamedAgent')
        raw_response = ""
        accumulated_cost = 0.0
        
        parsing_attempt_log = {
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "prompt": prompt, # Log the prompt that led to this attempt
            "retry_attempt_number": retry_count + 1,
            "raw_response": None,
            "extracted_json_string": None,
            "parsed_json": None,
            "error": None,
            "cost_of_this_attempt": 0.0
        }

        try:
            raw_response, cost_of_call = await self._ask_agent(agent, prompt, response_format_json=True)
            accumulated_cost += cost_of_call
            parsing_attempt_log["raw_response"] = raw_response
            parsing_attempt_log["cost_of_this_attempt"] = cost_of_call
            
            json_string = self._extract_json_from_string(raw_response)
            parsing_attempt_log["extracted_json_string"] = json_string
            
            if not json_string:
                self._log(f"No JSON block found in response from {agent_name}. Raw: '{raw_response[:200]}...'", "warning")
                raise json.JSONDecodeError("No JSON object found in response", raw_response, 0)
            
            parsed_json = json.loads(json_string)
            parsing_attempt_log["parsed_json"] = parsed_json
            json_parsing_log_list.append(parsing_attempt_log)
            return parsed_json, accumulated_cost

        except json.JSONDecodeError as e:
            self._log(f"Invalid JSON response from {agent_name} (attempt {retry_count + 1}): {str(e)}. Raw response: '{raw_response[:200]}...'", "error")
            parsing_attempt_log["error"] = f"JSONDecodeError: {str(e)}"
            json_parsing_log_list.append(parsing_attempt_log) # Log failed attempt

            if retry_count < self.MAX_JSON_RETRIES:
                self._log(f"Retrying JSON request to {agent_name} (attempt {retry_count + 2}/{self.MAX_JSON_RETRIES + 1})", "warning")
                retry_prompt = (
                    f"{prompt}\\n\\n" # Keep original prompt for context
                    f"Your previous response was not valid JSON. Please ensure your entire response is a single, valid JSON object (starting with {{ and ending with }} or starting with [ and ending with ]) without any surrounding text or explanations. "
                    f"The error was: {str(e)}. The raw response started with: '{raw_response[:100]}...'"
                )
                await asyncio.sleep(1.5) # Small delay before retry
                # Recursively call and add cost
                parsed_json_result, cost_from_retry = await self._get_json_response(agent, retry_prompt, error_msg, json_parsing_log_list, retry_count + 1)
                accumulated_cost += cost_from_retry
                return parsed_json_result, accumulated_cost
            else:
                self._log(f"Max JSON retries reached for {agent_name}. Giving up.", "error")
                raise AgentCommunicationError(f"{error_msg}: Invalid JSON response after multiple retries. Last error: {str(e)}")
        except AgentCommunicationError as e: # Catch specific error from _ask_agent
            self._log(f"Agent communication error while expecting JSON from {agent_name}: {str(e)}", "error")
            parsing_attempt_log["error"] = f"AgentCommunicationError: {str(e)}"
            json_parsing_log_list.append(parsing_attempt_log)
            raise
        except Exception as e: # Catch any other unexpected errors
            self._log(f"Unexpected error getting JSON response from {agent_name}: {str(e)}", "error")
            parsing_attempt_log["error"] = f"UnexpectedError: {str(e)}"
            json_parsing_log_list.append(parsing_attempt_log)
            raise AgentCommunicationError(f"{error_msg}: Unexpected error: {str(e)}")

    async def execute_decision_cycle(self, current_decision_focus: str, mission_context: dict):
        """Executes one full cycle: specialist selection, decision, execution, review for a given decision focus."""
        self._log(f"Starting new decision cycle focused on: {current_decision_focus}", "info")
        
        overall_mission = mission_context.get("overall_mission", "No overall mission specified.")
        cycle_start_time = datetime.now()
        mission_id = f"cycle_{cycle_start_time.strftime('%Y%m%d_%H%M%S')}_{re.sub(r'\W+','_',current_decision_focus[:20])}"
        
        # Initialize CycleLog for this cycle
        mission_log = CycleLog(
            mission_id=mission_id,
            timestamp=cycle_start_time.isoformat(),
            overall_mission=overall_mission,
            current_decision_focus=current_decision_focus,
            status="started"
        )
        
        # Link this cycle to the mission and previous cycles
        mission_log = self._link_cycle_to_previous(mission_log)
        
        recommendation_text: Optional[str] = None
        execution_output: Optional[dict] = None
        final_reviews_summary: Optional[List[dict]] = None
        decision_agent_name_for_log = "UnknownSpecialist"

        try:
            # Step 1: Confidence check & dynamic specialist creation
            self._log(f"Selecting or creating specialist for: {current_decision_focus[:100]}...", "info")
            decision_agent, confidence, cost_select_create = await self._select_or_create_specialist(
                current_decision_focus, 
                mission_log.agent_management_events,
                mission_log.json_parsing_attempts
            )
            mission_log.total_cycle_cost += cost_select_create
            decision_agent_name_for_log = getattr(decision_agent, 'name', 'UnnamedSpecialist')
            
            if confidence < self.CONFIDENCE_THRESHOLD and not decision_agent_name_for_log.startswith("Fallback"):
                self._log(f"Low confidence ({confidence:.2f}) from {decision_agent_name_for_log}. Creating new specialist.", "warning")
                # _create_specialized_agent is called within _select_or_create_specialist or directly if needed
                # decision_agent is already the potentially new one here
                pass # Agent creation logic is handled in _select_or_create_specialist

            # Step 2: Context Prep
            context_brief = {"overall_mission": overall_mission, "current_decision_focus": current_decision_focus}
            self._log(f"Context brief prepared for {decision_agent_name_for_log}", "debug")

            # Step 3: Decision Loop
            self._log(f"Starting decision loop with {decision_agent_name_for_log} for '{current_decision_focus[:50]}...'", "info")
            recommendation_text, decision_loop_cost, review_details_from_loop = await self._run_decision_loop(
                decision_agent,
                context_brief,
                mission_log.specialist_interactions,
                mission_log.review_interactions,
                mission_log.json_parsing_attempts,
                mission_log.orchestrator_interactions
            )
            mission_log.total_cycle_cost += decision_loop_cost
            mission_log.reviews_archive.extend(review_details_from_loop)
            mission_log.total_loops_in_decision_cycle = len(mission_log.specialist_interactions)
            self._log(f"Decision loop completed. Final Recommendation: {recommendation_text[:100]}...", "info")

            # Step 4: Execution Assignment
            self._log(f"Assigning execution of '{recommendation_text[:50]}...' to {decision_agent_name_for_log}", "info")
            execution_output, execution_cost = await self._execute_with_guardrails(
                decision_agent,
                recommendation_text,
                {},
                mission_log.execution_attempts,
                mission_log.json_parsing_attempts
            )
            mission_log.total_cycle_cost += execution_cost
            self._log(f"Execution result: {execution_output}", "info")

            # Step 5: Final Smoke-Test Review
            self._log(f"Performing final smoke-test review for '{current_decision_focus[:50]}...'", "info")
            final_reviews_summary, review_cost = await self._batch_peer_review(
                decision_agent_name_for_log,
                json.dumps(execution_output), 
                mission_log.review_interactions,
                mission_log.json_parsing_attempts,
                final=True
            )
            mission_log.total_cycle_cost += review_cost
            self._log(f"Final reviews received: {len(final_reviews_summary)} reviews", "info")
            
            mission_log.status = "completed_cycle_success"
            mission_log.kpi_outcomes["status"] = "success_cycle_completed"

        except Exception as e:
            self._log(f"Decision cycle focused on '{current_decision_focus[:50]}...' failed: {str(e)}", "error")
            mission_log.status = "failed_cycle"
            mission_log.error_message = str(e)
            mission_log.kpi_outcomes["status"] = "failed_cycle"
            mission_log.kpi_outcomes["error"] = str(e)
        
        # Step 6: Archive & Retrospective
        self._log(f"Archiving cycle log and running retrospective for '{current_decision_focus[:50]}...'", "info")
        retro_cost = await self._archive_and_retrospect(mission_log) 
        mission_log.total_cycle_cost += retro_cost

        # Calculate cycle duration and track agents used
        cycle_end_time = datetime.now()
        mission_log.cycle_duration_minutes = (cycle_end_time - cycle_start_time).total_seconds() / 60.0
        
        # Track agents used in this cycle
        agents_used = set()
        for interaction in mission_log.specialist_interactions:
            if interaction.get("agent_name"):
                agents_used.add(interaction["agent_name"])
        for event in mission_log.agent_management_events:
            if event.get("agent_name") or event.get("selected_agent_name"):
                agents_used.add(event.get("agent_name") or event.get("selected_agent_name"))
        mission_log.agents_used = list(agents_used)

        self._log(f"Decision cycle for '{current_decision_focus[:50]}...' finished. Total cycle cost: {mission_log.total_cycle_cost:.4f}, Duration: {mission_log.cycle_duration_minutes:.2f} minutes", "info")
        
        # Save the final cycle log
        log_dir = "mission_logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, f"{mission_log.mission_id}.json")
        try:
            with open(log_file_path, "w") as f:
                json.dump(asdict(mission_log), f, indent=2)
            self._log(f"Full mission cycle log archived to {log_file_path}", "info")
        except Exception as e:
            self._log(f"Error archiving final mission log {log_file_path}: {str(e)}", "error")
        
        # Update the master mission log with this cycle's information
        self._update_mission_log(mission_log)

        return {
            "cycle_id": mission_id,
            "decision_focus": current_decision_focus,
            "status": mission_log.status,
            "error": mission_log.error_message,
            "recommendation_text": recommendation_text,
            "execution_output": execution_output,
            "final_reviews_summary": final_reviews_summary,
            "total_loops_in_decision": mission_log.total_loops_in_decision_cycle,
            "total_cycle_cost": mission_log.total_cycle_cost,
            "mission_log_path": log_file_path 
        }

    async def determine_next_strategic_step(self, overall_mission: str, previous_cycles_summary: List[Dict]) -> str:
        """Determines the next strategic step or if the mission is complete. Logs its own interaction."""
        self._log("Determining next strategic step...", "info")
        interaction_log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "determine_next_step",
            "prompt": None, # Will be set below
            "raw_response": None,
            "parsed_output": None,
            "cost": 0.0,
            "error": None
        }

        # Get enhanced context from mission log
        mission_context = self.get_mission_context_for_agents()
        
        prompt = (
            f"Given the overall mission: '{overall_mission}'\n\n"
            f"Mission Context: {json.dumps(mission_context, indent=2)}\n\n"
            f"Previous decision cycles summary: {json.dumps(previous_cycles_summary, indent=2)}\n\n"
            "What is the next single, most critical strategic step to advance the mission? "
            "Consider the key learnings from previous cycles and the current mission status. "
            "If the mission appears to be fully achieved based on the previous cycles, respond with only the words 'MISSION_COMPLETE'. "
            "Otherwise, describe the next single strategic step clearly and concisely."
        )
        interaction_log_entry["prompt"] = prompt

        try:
            next_step_description, cost = await self._ask_orchestrator(prompt, response_format_json=False)
            interaction_log_entry["raw_response"] = next_step_description
            interaction_log_entry["cost"] = cost
            # No mission_log object available here to append to or update total cost directly.
            # This method is called by the CLI outside a specific cycle's CycleLog context.
            # The cost here is for this specific determination.
            self._log(f"Cost for determining next step: {cost:.4f}", "debug")

            if next_step_description.strip().upper() == "MISSION_COMPLETE":
                self._log("Orchestrator determined mission is complete.", "info")
                interaction_log_entry["parsed_output"] = "MISSION_COMPLETE"
                # How to log this? For now, it's just standard log.
                return "MISSION_COMPLETE"
            
            self._log(f"Next strategic step identified by orchestrator: {next_step_description}", "info")
            interaction_log_entry["parsed_output"] = next_step_description
            return next_step_description
        except Exception as e:
            self._log(f"Error determining next strategic step: {str(e)}", "error")
            interaction_log_entry["error"] = str(e)
            # How to log this? For now, just re-raise or return error indicator.
            # Re-raising might be too disruptive for the CLI. Let's return an error string.
            return f"ERROR_DETERMINING_NEXT_STEP: {str(e)}"
        finally:
            # This interaction isn't part of a specific CycleLog cycle object here.
            # We could have a separate log for these CLI-level orchestrator calls if needed.
            # For now, the standard logger and the return value convey the info.
            # Ensure orchestrator_interactions (if available on self) is logged
            if hasattr(self, 'mission_log_for_cli_interactions') and self.mission_log_for_cli_interactions: # Check if such a log exists
                self.mission_log_for_cli_interactions.append(interaction_log_entry)
            pass

    async def revise_rejected_cycle(self, 
                                  rejected_decision_focus: str, 
                                  rejected_recommendation: Optional[str],
                                  rejected_execution_result: Optional[dict], 
                                  rejection_reason: str, 
                                  mission_context: dict, # Contains overall_mission
                                  previous_accepted_cycles_summary: List[Dict] # Added
                                  ) -> str: # Returns new decision_focus string or error/complete
        """
        Handles a rejected cycle by asking the Orchestrator LLM to formulate a new strategic step.
        """
        self._log(f"Revising rejected cycle for: {rejected_decision_focus}. Reason: {rejection_reason}", "warning")
        overall_mission = mission_context.get("overall_mission", "No overall mission specified.")

        interaction_log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "revise_rejected_cycle",
            "rejected_decision_focus": rejected_decision_focus,
            "rejection_reason": rejection_reason,
            "rejected_recommendation": rejected_recommendation,
            "rejected_execution_result": rejected_execution_result,
            "prompt": None, "raw_response": None, "parsed_output": None, "cost": 0.0, "error": None
        }

        revision_prompt = (
            f"The overall mission is: '{overall_mission}'.\\n\\n"
            f"A previous strategic step was taken to address: '{rejected_decision_focus}'.\\n"
            f"This step resulted in the following recommendation: '''{rejected_recommendation if rejected_recommendation else 'N/A'}'''\\n"
            f"And the following execution result: '''{json.dumps(rejected_execution_result) if rejected_execution_result else 'N/A'}'''\\n"
            f"This outcome was REJECTED by the user. The reason provided was: '{rejection_reason}'.\\n\\n"
            f"Here is a summary of previously ACCEPTED decision cycles: {json.dumps(previous_accepted_cycles_summary, indent=2)}\\n\\n"
            "Given this rejection and the overall mission context, what is the next single, most critical strategic step to take? "
            "Consider if the rejection implies a need for a significant change in direction or if a more focused adjustment is needed. "
            "If the mission should be considered unachievable or requires fundamental rethinking due to the rejection, you can state 'MISSION_HALTED_BY_REJECTION'. "
            "Otherwise, describe the next single strategic step clearly and concisely."
        )
        interaction_log_entry["prompt"] = revision_prompt

        try:
            new_decision_focus, cost = await self._ask_orchestrator(revision_prompt, response_format_json=False)
            interaction_log_entry["raw_response"] = new_decision_focus
            interaction_log_entry["cost"] = cost
            interaction_log_entry["parsed_output"] = new_decision_focus
            self._log(f"Orchestrator proposed new focus after rejection: {new_decision_focus}", "info")
            return new_decision_focus # This is the new decision focus string
        except Exception as e:
            self._log(f"Error asking orchestrator to revise rejected cycle: {str(e)}", "error")
            interaction_log_entry["error"] = str(e)
            return f"ERROR_REVISING_CYCLE: {str(e)}"
        finally:
            # Log this interaction
            if hasattr(self, 'mission_log_for_cli_interactions') and self.mission_log_for_cli_interactions: # Check if such a log exists
                 self.mission_log_for_cli_interactions.append(interaction_log_entry)

    async def _run_decision_loop(self, 
                                 decision_agent: RoutedAgent, 
                                 context_brief: dict, 
                                 specialist_interaction_logs: List[dict],
                                 review_interaction_logs: List[dict],
                                 json_parsing_logs: List[dict],
                                 orchestrator_interaction_logs: List[dict]
                                 ) -> Tuple[str, float, List[dict]]: # Returns: recommendation_text, total_cost_of_loop, raw_reviews
        
        recommendation_text: Optional[str] = None
        self.last_revision_plan = None 
        accumulated_cost_of_loop = 0.0
        raw_reviews_from_loop: List[dict] = [] # Store raw review dicts from _batch_peer_review

        for loop_num in range(self.MAX_REVISION_LOOPS):
            self._log(f"Decision loop iteration {loop_num + 1}/{self.MAX_REVISION_LOOPS} with {decision_agent.name}", "debug")
            
            current_loop_interaction_log = {
                "timestamp": datetime.now().isoformat(),
                "agent_name": decision_agent.name,
                "loop_iteration": loop_num + 1,
                "type": "recommendation_request",
                "prompt": None, "raw_response": None, "parsed_output": None, # Parsed output is the recommendation itself
                "cost": 0.0, "error": None
            }

            prompt_content_for_agent: str
            if loop_num == 0:
                prompt_content_for_agent = (
                    f"Context: {json.dumps(context_brief)}\\n"
                    "Please provide your recommendation, reasoning, and projected KPI impact. "
                    "Your response should be a clear, actionable text." # Not JSON for the recommendation itself
                )
            else:
                if not self.last_revision_plan:
                    self._log("Error: Revision loop entered without a revision plan. Using generic.", "error")
                    self.last_revision_plan = "The previous recommendation had issues. Please revise your approach and provide a new recommendation."
                
                prompt_content_for_agent = (
                    f"Previous recommendation: {recommendation_text}\\n\\n"
                    f"Revision instructions from Orchestrator: {self.last_revision_plan}\\n\\n"
                    "Please provide your revised recommendation based on the feedback. "
                    "Your response should be a clear, actionable text."
                )
            current_loop_interaction_log["prompt"] = prompt_content_for_agent

            try:
                recommendation_text, cost = await self._ask_agent(decision_agent, prompt_content_for_agent, response_format_json=False)
                accumulated_cost_of_loop += cost
                current_loop_interaction_log["cost"] = cost
                current_loop_interaction_log["raw_response"] = recommendation_text
                current_loop_interaction_log["parsed_output"] = recommendation_text # Recommendation is the "parsed" output here
                self._log(f"Agent {decision_agent.name} (Loop {loop_num + 1}) Recommendation: {recommendation_text[:200]}...", "decision")
                specialist_interaction_logs.append(current_loop_interaction_log)
            except Exception as e:
                self._log(f"Error asking {decision_agent.name} for recommendation: {str(e)}", "error")
                current_loop_interaction_log["error"] = str(e)
                specialist_interaction_logs.append(current_loop_interaction_log)
                # Decide if we should re-raise or try to continue/default
                if loop_num == 0: # If first attempt fails, critical
                    raise AgentCommunicationError(f"Failed to get initial recommendation from {decision_agent.name}: {str(e)}")
                else: # If a revision fails, maybe use previous recommendation? Or just end loop.
                    self._log("Failed to get revised recommendation. Ending decision loop.", "warning")
                    break # Exit loop, recommendation_text will hold the last good one (or None)

            # Peer Review Step
            # _batch_peer_review logs its own interactions to review_interaction_logs and json_parsing_logs
            # It returns the list of review dicts and the cost of the review process.
            current_reviews, review_cost = await self._batch_peer_review(
                decision_agent.name,
                recommendation_text, # Pass the text recommendation
                review_interaction_logs,
                json_parsing_logs
            )
            accumulated_cost_of_loop += review_cost
            raw_reviews_from_loop.extend(current_reviews) # Add to this loop's collected reviews
            
            if self._check_review_consensus(current_reviews):
                self._log(f"Consensus reached after {loop_num + 1} review round(s).", "info")
                break
            
            self._log(f"Consensus not reached after {loop_num + 1} review round(s). Max loops: {self.MAX_REVISION_LOOPS}", "info")
            if loop_num < self.MAX_REVISION_LOOPS - 1:
                issues_for_revision = "\\n".join(
                    f"- {r.get('agent', 'Unknown Agent')}: {r.get('feedback', 'No specific feedback provided') if not r.get('approved', r.get('valid', True)) else ', '.join(r.get('issues', ['No specific issues cited'])) if r.get('issues') else 'No specific issues cited.'}" 
                    for r in current_reviews if not (r.get('valid', True) or r.get('approved', True)) or r.get('issues')
                )
                if not issues_for_revision.strip():
                    issues_for_revision = "General concerns about the recommendation were raised. Please re-evaluate and provide specific revision instructions."

                # Orchestrator plans the revision
                orchestrator_revision_log = {
                    "timestamp": datetime.now().isoformat(), "agent_name": self.name, "type": "revision_planning",
                    "prompt": None, "raw_response": None, "parsed_output": None, "cost": 0.0, "error": None
                }
                revision_plan_prompt = (
                    f"The recommendation from {decision_agent.name} was reviewed. Issues found:\\n{issues_for_revision}\\n"
                    f"Original Context: {json.dumps(context_brief)}\\n"
                    f"Original Recommendation: {recommendation_text[:300]}...\\n\\n" 
                    f"🔧 How should {decision_agent.name} revise its recommendation? Provide a concise textual plan for the agent. This plan will be given to the agent."
                )
                orchestrator_revision_log["prompt"] = revision_plan_prompt
                try:
                    self.last_revision_plan, revision_plan_cost = await self._ask_orchestrator(revision_plan_prompt, response_format_json=False)
                    accumulated_cost_of_loop += revision_plan_cost
                    orchestrator_revision_log["cost"] = revision_plan_cost
                    orchestrator_revision_log["raw_response"] = self.last_revision_plan
                    orchestrator_revision_log["parsed_output"] = self.last_revision_plan
                    self._log(f"Orchestrator Revision Plan for {decision_agent.name}: {self.last_revision_plan}", "decision")
                except Exception as e:
                    self._log(f"Error getting revision plan from orchestrator: {str(e)}", "error")
                    orchestrator_revision_log["error"] = str(e)
                    self.last_revision_plan = "An error occurred while generating the revision plan. Please try to improve the recommendation generally."
                orchestrator_interaction_logs.append(orchestrator_revision_log)
            else:
                self._log(f"Max revision loops ({self.MAX_REVISION_LOOPS}) reached without consensus for {decision_agent.name}.", "warning")
                break 
        
        if recommendation_text is None:
            self._log("No recommendation generated from decision loop.", "error")
            raise ValueError("Decision loop failed to produce a recommendation.")

        return recommendation_text, accumulated_cost_of_loop, raw_reviews_from_loop

    async def _execute_with_guardrails(self, 
                                       agent: RoutedAgent, 
                                       recommendation: str, 
                                       constraints: dict, # Will be {}
                                       execution_attempts_log: List[dict],
                                       json_parsing_logs: List[dict]
                                       ) -> Tuple[Dict[str, Any], float]: # Returns: execution_output_dict, cost
        agent_name = getattr(agent, 'name', 'UnnamedAgent')
        self._log(f"Attempting to execute recommendation via {agent_name}: '{recommendation[:100]}...'", "info")
        
        # Enhanced tool detection and auto-provisioning
        available_tools = {}
        tool_lookup_cost = 0.0
        
        # Enhanced keyword-based tool detection with more comprehensive patterns
        tool_patterns = [
            "spreadsheet", "calendar", "email", "database", "api", "webhook", 
            "crm", "analytics", "payment", "file", "document", "storage",
            "social media", "marketing", "automation", "integration"
        ]
        
        context = {
            "overall_mission": "execution_context", 
            "recommendation": recommendation,
            "agent_name": agent_name
        }
        
        # Scan recommendation for tool mentions and attempt auto-provisioning
        for tool_pattern in tool_patterns:
            if tool_pattern in recommendation.lower():
                self._log(f"Detected potential tool requirement: {tool_pattern}", "debug")
                tool = await self._get_tool_from_registry(tool_pattern, context)
                if tool:
                    available_tools[tool_pattern] = tool
                    self._log(f"Tool '{tool_pattern}' made available for execution.", "info")
        
        attempt_log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_name": agent_name,
            "recommendation_to_execute": recommendation,
            "available_tools": list(available_tools.keys()),
            "prompt": None, # Will be set below
            "raw_response": None,
            "parsed_json_output": None,
            "cost": 0.0,
            "error": None
        }

        # Build execution prompt with available tools information
        tools_info = ""
        if available_tools:
            tools_info = f"\n\nAVAILABLE TOOLS:\n"
            for tool_name, tool_spec in available_tools.items():
                tools_info += f"- {tool_name}: {tool_spec.get('description', 'No description available')}\n"
                if 'endpoint_details' in tool_spec:
                    endpoint = tool_spec['endpoint_details']
                    tools_info += f"  Endpoint: {endpoint.get('method', 'POST')} {endpoint.get('url', 'No URL')}\n"
            tools_info += "You can reference these tools in your execution plan.\n"

        execution_prompt = (
            f"You are to facilitate the EXECUTION of the following recommendation in a REAL-WORLD context for an online business. This is not a simulation.\\n\\n"
            f"Final Recommendation:\\n'''{recommendation}'''{tools_info}\n\n"
            f"Consider the following:\\n"
            f"1. Can this task be FULLY automated by you (an AI with text capabilities) and completed NOW? If so, describe the exact steps you are taking as if you are performing them, and then provide the outcome.\\n"
            f"2. Does this task require coding, API interaction, or filesystem operations that you cannot directly perform? If so, clearly state what code needs to be written, what API needs to be called (with example parameters if possible), or what manual operation is needed. Frame this as a request for another specialist (e.g., a 'CodeExecutionAgent') or for the 'Human User'.\n"
            f"3. Does this task inherently require HUMAN judgment, physical action, or access to external accounts/systems you don't have? If so, clearly state the task that the 'Human User' needs to perform and what information they would need from you to do it.\n\n"
            f"Your response MUST be a JSON object with the following strict structure. Do not include any text outside of this JSON object:\\n"
            f"```json\n"
            f"{{\n"
            f"  \"execution_type\": \"automated_by_ai\" | \"requires_coding_api\" | \"requires_human_intervention\",\n"
            f"  \"description\": \"Detailed description of what you did (if automated), or what needs to be done (if requires coding/API/human). Include any outputs or results here if automated.\",\n"
            f"  \"cost\": 0.0, // Estimated cost of this step, if applicable, otherwise 0.0\n"
            f"  \"output_data\": {{}}, // any structured data produced, e.g., generated text for a file, code, API call structure. Null if not applicable.\n"
            f"  \"human_task_description\": null, // Clear, actionable instruction for the Human User if intervention is needed. Null otherwise.\n"
            f"  \"next_steps_if_human\": null // What happens after the human completes their task. Null otherwise.\n"
            f"}}\n"
            f"```\n"
            f"Focus on practical, real-world execution or clear handoff. Ensure the output is ONLY the JSON object itself."
        )
        attempt_log_entry["prompt"] = execution_prompt
        total_cost_for_execution = tool_lookup_cost  # Include any cost from tool lookups

        try:
            # _get_json_response handles JSON extraction, retries, and logging to json_parsing_logs.
            # It also returns the accumulated cost for its calls.
            result_json, cost = await self._get_json_response(
                agent,
                execution_prompt,
                f"Failed to get structured execution result from {agent_name}",
                json_parsing_logs # Pass the list for detailed JSON parsing logging
            )
            total_cost_for_execution += cost
            attempt_log_entry["raw_response"] = "See json_parsing_logs for raw responses if errors occurred during parsing." # Placeholder, actual raw is in json_parsing_logs
            attempt_log_entry["parsed_json_output"] = result_json
            attempt_log_entry["cost"] = total_cost_for_execution # Cost of this successful attempt
            
            required_keys = ["execution_type", "description"]
            for key in required_keys:
                if key not in result_json:
                    # This error will be caught by the outer try-except and logged in attempt_log_entry["error"]
                    raise AgentCommunicationError(f"Execution result from {agent_name} missing required key: {key}. Result: {result_json}")

            if "cost" in result_json and isinstance(result_json["cost"], (int, float)):
                 self._log(f"Execution by {agent_name} reported task cost: {result_json['cost']}", "info")
                 # This is the cost *reported by the agent for the task*, not the LLM call cost.
                 # We might want to add this to a different field in the log if we want to track it.
            else:
                self._log(f"Execution result from {agent_name} did not specify a valid task cost. Defaulting to 0.0.", "warning")
                result_json["cost"] = result_json.get("cost", 0.0) 

            self._log(f"Execution attempt by {agent_name} ({result_json['execution_type']}) successful: {result_json['description'][:100]}...", "success")
            
            # Intercept human intervention requests and attempt auto-provisioning
            if result_json.get('execution_type') == 'requires_human_intervention' and result_json.get('human_task_description'):
                human_task = result_json.get('human_task_description')
                self._log(f"Human intervention required: {human_task[:100]}...", "info")
                
                # Check if AutoProvisionAgent can handle this as a trivial request
                missing_item_details = {
                    "type": "tool",  # Assume it's a tool requirement for now
                    "name": f"human_task_{agent_name}",
                    "reason": "requires_human_intervention", 
                    "details": human_task
                }
                
                try:
                    auto_provision_result = await self.auto_provision_agent.handle_trivial_request(
                        context, missing_item_details
                    )
                    
                    if auto_provision_result:
                        self._log(f"AutoProvisionAgent handled human task: {auto_provision_result}", "info")
                        # Update the execution result to indicate auto-handling
                        result_json['execution_type'] = 'automated_by_ai'
                        result_json['description'] += f"\n\nAuto-handled by AutoProvisionAgent: {auto_provision_result}"
                        result_json['human_task_description'] = None
                        result_json['next_steps_if_human'] = None
                        
                except Exception as e:
                    self._log(f"AutoProvisionAgent could not handle human task: {str(e)}", "debug")
                    # Continue with original human intervention requirement
            
            execution_attempts_log.append(attempt_log_entry)
            return result_json, total_cost_for_execution
            
        except Exception as e:
            self._log(f"Error in execution process with {agent_name}: {str(e)}", "error")
            attempt_log_entry["error"] = str(e)
            # The cost here would be whatever accumulated before the error in _get_json_response or _ask_agent
            attempt_log_entry["cost"] = total_cost_for_execution # Log cost accumulated up to the error
            execution_attempts_log.append(attempt_log_entry)
            
            # Return a structured error for the CLI to handle gracefully
            error_output = {
                "execution_type": "error_in_execution",
                "description": f"Failed to execute task via {agent_name}: {str(e)}",
                "cost": 0.0, # Task cost is 0 as it failed
                "output_data": None,
                "human_task_description": "An internal error occurred during execution. Please review logs.",
                "next_steps_if_human": None,
                "original_error": str(e)
            }
            return error_output, total_cost_for_execution # Return error dict and cost incurred

    def _check_review_consensus(self, reviews: List[dict]) -> bool:
        """Check if there is consensus among peer reviews."""
        if not reviews: return False
        # Check both new format (approved) and legacy format (valid) for compatibility
        valid_reviews = [r for r in reviews if r.get("valid", False) or r.get("approved", False)]
        # Stricter: all must be valid for consensus, or a high threshold.
        # For now, let's stick to the 75% threshold.
        return len(valid_reviews) >= len(reviews) * 0.75 

    async def _select_or_create_specialist(self, 
                                           decision: str, 
                                           agent_management_logs: List[dict],
                                           json_parsing_logs: List[dict]
                                           ) -> Tuple[Optional[RoutedAgent], float, float]: # Agent, Confidence, Cost
        """Select an existing agent or create a new one. Logs creation/selection events."""
        accumulated_cost = 0.0
        selection_event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "specialist_selection_attempt",
            "decision_context": decision,
            "selected_agent_name": None,
            "confidence": 0.0,
            "reason": None,
            "cost": 0.0 # Cost for confidence checks
        }

        if self.agents:
            best_agent_name: Optional[str] = None
            best_confidence: float = -1.0
            agent_candidates = list(self.agents.values())

            for agent_instance in agent_candidates:
                agent_instance_name = getattr(agent_instance, 'name', 'UnnamedAgent')
                confidence_check_cost_total = 0.0
                try:
                    confidence_prompt = (
                        f"Regarding the decision: \"{decision}\". "
                        "Can you effectively handle this specific decision? "
                        "Reply with JSON: {\"can_handle\":bool,\"confidence\":float (0.0-1.0, where 1.0 is highest confidence)}."
                    )
                    # _get_json_response logs to json_parsing_logs
                    result, cost = await self._get_json_response(
                        agent_instance, confidence_prompt,
                        f"Failed to get agent confidence from {agent_instance_name}",
                        json_parsing_logs 
                    )
                    confidence_check_cost_total += cost
                    if result.get("can_handle", False):
                        confidence_val = float(result.get("confidence", 0.0))
                        if confidence_val > best_confidence:
                            best_agent_name = agent_instance_name
                            best_confidence = confidence_val
                except (AgentCommunicationError, ValueError, TypeError, json.JSONDecodeError) as e:
                    self._log(f"Error getting agent confidence from {agent_instance_name}: {str(e)}", "warning")
                    # Cost is already handled by _get_json_response for its call
                accumulated_cost += confidence_check_cost_total # Add cost of this confidence check
            
            selection_event["cost"] = accumulated_cost # Total cost for all confidence checks
            if best_agent_name and best_agent_name in self.agents:
                self._log(f"Selected existing agent '{best_agent_name}' for decision with confidence: {best_confidence:.2f}", "info")
                selection_event["selected_agent_name"] = best_agent_name
                selection_event["confidence"] = best_confidence
                selection_event["reason"] = f"Selected existing agent {best_agent_name} with best confidence."
                agent_management_logs.append(selection_event)
                return self.agents[best_agent_name], best_confidence, accumulated_cost

        # Before creating a new specialist, check if AutoProvisionAgent can handle this as a trivial agent request
        self._log(f"No suitable existing agent found for decision: '{decision[:100]}...'. Checking if AutoProvisionAgent can handle this.", "info")
        
        missing_item_details = {
            "type": "agent",
            "name": f"specialist_for_{decision[:30].replace(' ', '_')}",
            "reason": "not_found",
            "details": f"No suitable agent found for decision: {decision}"
        }
        
        context = {"overall_mission": "agent_selection", "decision": decision}
        
        try:
            auto_provision_result = await self.auto_provision_agent.handle_trivial_request(
                context, missing_item_details
            )
            
            if auto_provision_result:
                self._log(f"AutoProvisionAgent handled agent creation: {auto_provision_result}", "info")
                # Check if the agent was actually added to registry and try to use it
                agent_name = missing_item_details["name"]
                if agent_name in self.agents:
                    selection_event["selected_agent_name"] = agent_name
                    selection_event["confidence"] = 1.0
                    selection_event["reason"] = f"Auto-provisioned by AutoProvisionAgent: {auto_provision_result}"
                    agent_management_logs.append(selection_event)
                    return self.agents[agent_name], 1.0, accumulated_cost
                    
        except Exception as e:
            self._log(f"AutoProvisionAgent could not handle agent creation: {str(e)}", "debug")
        
        # Fallback to creating new specialist if auto-provisioning didn't work
        self._log(f"AutoProvisionAgent declined or failed. Creating a new specialist manually.", "info")
        selection_event["reason"] = "No suitable existing agent found, AutoProvisionAgent declined, proceeding to create new specialist."
        # Cost of _create_specialized_agent will be added separately
        new_agent, creation_cost = await self._create_specialized_agent(decision, agent_management_logs, json_parsing_logs)
        accumulated_cost += creation_cost
        
        selection_event["selected_agent_name"] = getattr(new_agent, 'name', 'UnnamedNewSpecialist')
        selection_event["confidence"] = 1.0 # Assuming new agent is 100% confident for the task it was made for
        # Update the original selection_event's cost if it's the one being logged, or log a new creation event.
        # _create_specialized_agent already logs its own 'agent_creation' event.
        agent_management_logs.append(selection_event) # Log the decision to create.

        return new_agent, 1.0, accumulated_cost

    async def _create_specialized_agent(self, 
                                        decision: str, 
                                        agent_management_logs: List[dict],
                                        json_parsing_logs: List[dict]
                                        ) -> Tuple[RoutedAgent, float]: # Returns Agent, Cost
        """Create a specialized agent. Logs creation event. Returns agent and creation cost."""
        creation_event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "agent_creation_attempt",
            "decision_context": decision,
            "agent_name": None, "role": None, "persona": None, "expertise": None,
            "primer_source": None, "status": "pending", "error": None,
            "cost_of_spec_generation": 0.0,
            "cost_of_agent_object_creation": 0.0 # Negligible, but for completeness
        }
        accumulated_creation_cost = 0.0

        try:
            agent_spec_prompt = (
                f"Design a specialist agent for this decision: \"{decision}\".\\n"
                "The agent should be focused and effective for this specific task. "
                "Reply with JSON containing these keys: "
                "{\"name\":str (a concise, descriptive name for the agent, e.g., \"CodeReviewAgent\"), "
                "\"persona\":str (a brief description of its persona), "
                "\"expertise\":str (comma-separated list of key expertise areas)}."
            )
            # _get_json_response logs to json_parsing_logs and returns cost
            agent_spec, spec_gen_cost = await self._get_json_response(
                self, # Orchestrator (self) designs the agent
                agent_spec_prompt,
                "Failed to get specialized agent specification from orchestrator",
                json_parsing_logs
            )
            accumulated_creation_cost += spec_gen_cost
            creation_event["cost_of_spec_generation"] = spec_gen_cost
            
            # Use the 'name' from spec as the primary basis for role and template lookup
            # If 'name' is missing, then default to "SpecialistAgent"
            agent_name_from_spec = agent_spec.get("name", "SpecialistAgent")
            # If 'role' is explicitly in spec, use it, otherwise default to agent_name_from_spec
            role = agent_spec.get("role", agent_name_from_spec) 
            persona = agent_spec.get("persona", f"an AI assistant specialized for {decision[:30]}...")
            expertise = agent_spec.get("expertise", "general problem solving")
            
            creation_event["role"] = role
            creation_event["persona"] = persona
            creation_event["expertise"] = expertise

            sane_role_name = re.sub(r'\W+', '_', role)
            if not sane_role_name: sane_role_name = "Specialist" # Should not happen if role defaults to agent_name_from_spec
            base_sane_role_name = sane_role_name
            counter = 1
            while sane_role_name in self.agents:
                sane_role_name = f"{base_sane_role_name}_{counter}"
                counter += 1
            creation_event["agent_name"] = sane_role_name
            
            try:
                # Use the agent_name_from_spec (e.g., TestMissionPlanner) for template lookup primarily
                template_name_to_try = agent_name_from_spec.lower().replace(" ", "_")
                primer = load_template(f"specialist_{template_name_to_try}")
                self._log(f"Loaded template 'specialist_{template_name_to_try}.txt' for role {sane_role_name}", "info")
                creation_event["primer_source"] = f"template: specialist_{template_name_to_try}.txt"
            except TemplateError:
                self._log(f"No specific template for role '{template_name_to_try}' (derived from spec name/role '{role}'). Constructing primer for {sane_role_name} from spec.", "info")
                primer = (
                    f"You are {sane_role_name}. {persona}.\n"
                    f"Your core expertise lies in: {expertise}.\n"
                    "Focus on your specialized role to address the tasks given to you."
                )
                creation_event["primer_source"] = "generated_from_spec"
            
            # _create_agent itself does not have LLM calls, so its cost is mainly object instantiation.
            created_agent = await self._create_agent(sane_role_name, persona, primer) # No direct cost here
            creation_event["status"] = "success"
            agent_management_logs.append(creation_event)
            return created_agent, accumulated_creation_cost

        except Exception as e:
            self._log(f"Error creating specialized agent for decision '{decision[:50]}...': {str(e)}. Falling back.", "error")
            creation_event["status"] = "fallback_triggered"
            creation_event["error"] = f"Error in spec creation: {str(e)}"
            
            try:
                generic_primer = load_template("specialist_generic") 
                creation_event["primer_source"] = "template: specialist_generic.txt (fallback)"
            except TemplateError:
                self._log("specialist_generic.txt template not found for fallback.", "warning")
                generic_primer = "You are a generic specialist AI agent. Use your analytical skills to address the task."
                creation_event["primer_source"] = "hardcoded_generic (fallback)"

            generic_agent_name = "FallbackGenericSpecialist"
            counter = 1
            while generic_agent_name in self.agents:
                generic_agent_name = f"FallbackGenericSpecialist_{counter}"
                counter += 1
            
            creation_event["agent_name"] = generic_agent_name
            creation_event["role"] = "FallbackGenericSpecialist"
            
            fallback_agent = await self._create_agent(generic_agent_name, "a generic AI assistant for fallback scenarios", generic_primer)
            agent_management_logs.append(creation_event) # Log the event that led to fallback
            return fallback_agent, accumulated_creation_cost # Cost is for the failed spec attempt

    async def _archive_and_retrospect(self, mission_log: CycleLog) -> float: # Returns cost of retro
        """Archive mission results and run retrospective analysis. Modifies mission_log with retro interaction."""
        self._log("Starting retrospective analysis...", "debug")
        # Archiving of the main mission_log happens *after* this method in execute_decision_cycle
        
        retro_interaction_log = {
            "timestamp": datetime.now().isoformat(),
            "type": "retrospective_analysis",
            "agent_name": None, # Set when/if retro agent is created
            "prompt": None, "raw_response": None, "parsed_output": None, # Parsed output is the analysis text
            "cost": 0.0, "error": None
        }
        accumulated_retro_cost = 0.0

        try:
            try:
                retro_primer = load_template("retrospective")
            except TemplateError:
                self._log("Retrospective template not found. Skipping retrospective analysis.", "warning")
                retro_interaction_log["error"] = "Retrospective template not found."
                mission_log.orchestrator_interactions.append(retro_interaction_log) # Log skip
                return 0.0 # No cost if skipped

            retro_agent_name = "RetrospectiveAnalyser"
            # Ensure unique name if multiple retrospectives run in one orchestrator lifetime (unlikely for now)
            # This agent is temporary for this analysis.
            
            # Agent creation event for retro agent (if it's dynamic)
            # For now, assume _create_agent is cheap and not a major cost driver itself for retro.
            # If retro agent creation itself used an LLM, that would be different.
            retro_agent_creation_event = {
                "timestamp": datetime.now().isoformat(), "event_type": "agent_creation", 
                "decision_context": "retrospective_analysis", "agent_name": retro_agent_name,
                "role": "RetrospectiveAnalyser", "status": "success", "cost": 0.0
            }
            retro_agent = await self._create_agent(
                retro_agent_name,
                "an expert in analyzing mission performance and suggesting improvements",
                retro_primer
            )
            mission_log.agent_management_events.append(retro_agent_creation_event)
            retro_interaction_log["agent_name"] = retro_agent_name

            # Prepare mission log dump for prompt, summarize if too large
            mission_log_dict_for_prompt = asdict(mission_log)
            # Remove potentially huge fields from the version sent to LLM for retro
            # to avoid excessive token usage for the retro itself.
            # The full log is saved to disk.
            fields_to_summarize_or_remove = [
                "orchestrator_interactions", "specialist_interactions", 
                "review_interactions", "execution_attempts", "json_parsing_attempts"
            ]
            summary_indicators = {}
            for field_name in fields_to_summarize_or_remove:
                if field_name in mission_log_dict_for_prompt and mission_log_dict_for_prompt[field_name]:
                    summary_indicators[f"{field_name}_count"] = len(mission_log_dict_for_prompt[field_name])
                    mission_log_dict_for_prompt[field_name] = f"[Log entries for {field_name} omitted for brevity, count: {summary_indicators[f'{field_name}_count']}]"
            
            mission_log_dict_for_prompt.update(summary_indicators) # Add counts to the main dict
            mission_log_dump_for_prompt = json.dumps(mission_log_dict_for_prompt, indent=2)

            # Simple length check, might need to be more sophisticated (token counting)
            # Max prompt size is an estimate, depends on model.
            # This check is very basic.
            MAX_PROMPT_LEN_ESTIMATE = 15000 # Approx chars for a large-ish prompt (e.g. 4k tokens)
            if len(mission_log_dump_for_prompt) > MAX_PROMPT_LEN_ESTIMATE:
                 # If still too long, create an even more aggressive summary
                 brief_summary = {
                    "mission_id": mission_log.mission_id,
                    "overall_mission": mission_log.overall_mission,
                    "current_decision_focus": mission_log.current_decision_focus,
                    "status": mission_log.status,
                    "error_message": mission_log.error_message,
                    "total_cycle_cost": mission_log.total_cycle_cost,
                    "total_loops_in_decision_cycle": mission_log.total_loops_in_decision_cycle,
                    "agent_management_events_count": len(mission_log.agent_management_events),
                    "kpi_outcomes": mission_log.kpi_outcomes
                 }
                 mission_log_dump_for_prompt = json.dumps(brief_summary, indent=2)
                 self._log("Mission log dump for retro was still too large, using very brief summary.", "warning")

            analysis_prompt = (
                f"Analyze this mission log (or its summary):\n{mission_log_dump_for_prompt}\n\n"
                "Provide insights on (be concise, use markdown for readability):\n"
                "1. Performance: How did the cycle perform against its decision focus? Was the outcome successful?\n"
                "2. Effectiveness: Were the agent selection, decision-making, and review processes effective? Any bottlenecks?\n"
                "3. Challenges & Errors: Any significant challenges, errors, or inefficiencies observed (e.g., repeated JSON failures, low confidence)?\n"
                "4. Cost: Comment on the cycle cost if it seems notable for the work done.\n"
                "5. Key Learnings: What are 1-2 key learnings from this cycle?\n"
                "6. Actionable Recommendations: Suggest 1-2 specific, actionable improvements for future similar cycles or for the orchestrator's logic/prompts."
            )
            retro_interaction_log["prompt"] = analysis_prompt
            
            analysis_text, cost = await self._ask_agent(retro_agent, analysis_prompt, response_format_json=False)
            accumulated_retro_cost += cost
            retro_interaction_log["cost"] = cost
            retro_interaction_log["raw_response"] = analysis_text
            retro_interaction_log["parsed_output"] = analysis_text # Analysis is the "parsed" output

            retro_file_path = os.path.join("mission_logs", f"{mission_log.mission_id}_retro.txt")
            with open(retro_file_path, "w") as f:
                f.write(f"Retrospective Analysis for Mission Cycle: {mission_log.mission_id}\n")
                f.write(f"Overall Mission: {mission_log.overall_mission}\n")
                f.write(f"Cycle Decision Focus: {mission_log.current_decision_focus}\n")
                f.write(f"Cycle Status: {mission_log.status}\n")
                if mission_log.error_message:
                    f.write(f"Cycle Error: {mission_log.error_message}\n")
                f.write(f"Total Cycle Cost: {mission_log.total_cycle_cost:.4f}\n\n")
                f.write("--- Analysis ---\n")
                f.write(analysis_text)
            self._log(f"Retrospective analysis archived to {retro_file_path}", "info")
            
            # Clean up the temporary retrospective agent if it was created dynamically and uniquely for this
            if retro_agent_name in self.agents and retro_agent_name == "RetrospectiveAnalyser": # Basic check
                del self.agents[retro_agent_name]
                self._log(f"Cleaned up temporary agent: {retro_agent_name}", "debug")
                cleanup_event = {
                    "timestamp": datetime.now().isoformat(), "event_type": "agent_cleanup",
                    "agent_name": retro_agent_name, "reason": "Temporary retro agent"
                }
                mission_log.agent_management_events.append(cleanup_event)

        except Exception as e:
            self._log(f"Error in retrospective analysis: {str(e)}", "error")
            retro_interaction_log["error"] = str(e)
        
        mission_log.orchestrator_interactions.append(retro_interaction_log)
        return accumulated_retro_cost

    async def _cleanup_agents(self):
        """Clean up agents after mission completion."""
        agent_names_to_remove = list(self.agents.keys())
        self._log(f"Starting cleanup of {len(agent_names_to_remove)} agents.", "debug")
        for agent_name in agent_names_to_remove:
            # No explicit client close needed for autogen_ext.models.openai.OpenAIChatCompletionClient
            if agent_name in self.agents:
                 del self.agents[agent_name]
        self._log(f"Cleaned up agents. Active agents now: {len(self.agents)}", "info")

    async def _create_agent(self, role_name: str, persona: str, primer: str) -> RoutedAgent:
        """Create a new agent with the given role and primer."""
        try:
            self._log(f"Creating new agent: '{role_name}' ({persona[:50]}...)", "info")
            if role_name in self.agents:
                 self._log(f"Warning: Agent with name '{role_name}' already exists. Overwriting may occur if not handled by caller.", "warning")

            full_system_prompt = f"You are {role_name}. {persona}\\n\\n{primer}"
            # Agent creation itself is not an LLM call, so no direct cost.
            agent = RoutedAgent(full_system_prompt) 
            agent._client = self._client 
            agent.log_callback = self.log_callback 
            agent.name = role_name 
            self.agents[role_name] = agent # Register agent
            self._log(f"Agent '{role_name}' created successfully.", "info")
            return agent # Return the created agent instance
        except Exception as e:
            self._log(f"Failed to create agent '{role_name}': {str(e)}", "error")
            raise

    async def _batch_peer_review(self, 
                                 subject_agent_name: str, 
                                 content_to_review: str, 
                                 review_interaction_logs: List[dict], # Log list for detailed review interactions
                                 json_parsing_logs: List[dict],     # Log list for JSON parsing attempts by reviewers
                                 final: bool = False
                                 ) -> Tuple[List[dict], float]: # Returns list of review dicts, total_review_cost
        """Run batch peer review. Logs interaction details. Returns review dicts and total cost."""
        
        all_reviews_from_batch: List[dict] = [] # This will store the structured JSON responses from reviewers
        accumulated_review_cost = 0.0

        if not isinstance(content_to_review, str):
            content_to_review = json.dumps(content_to_review) if isinstance(content_to_review, dict) else str(content_to_review)

        reviewers = [agent for name, agent in self.agents.items() if name != subject_agent_name and hasattr(agent, 'name') and name != self.name and name != "RetrospectiveAnalyser"] # Exclude self, retro
        if not reviewers:
            self._log(f"No other suitable agents available to review output from {subject_agent_name}. Skipping peer review.", "warning")
            # Return a system "review" indicating no reviewers, and 0 cost
            return [{
                "agent": "System", 
                "approved": True,
                "feedback": "No reviewers available - auto-approved",
                "estimated_confidence_if_approved": 1.0,
                "valid": True,  # Legacy compatibility
                "issues": ["No reviewers available"],  # Legacy compatibility
                "kpi_valid": True, "kpi_issues": []
            }], 0.0

        self._log(f"Starting batch peer review of output from {subject_agent_name} by {len(reviewers)} agents.", "info")
        
        for agent_instance in reviewers:
            agent_instance_name = getattr(agent_instance, 'name', 'UnnamedReviewer')
            
            review_log_entry = {
                "timestamp": datetime.now().isoformat(),
                "reviewer_agent_name": agent_instance_name,
                "subject_agent_name": subject_agent_name,
                "content_reviewed_snippet": content_to_review[:200] + "..." if len(content_to_review) > 200 else content_to_review,
                "is_final_review": final,
                "prompt": None, # Will be set below
                "raw_response": None, # Will be from json_parsing_logs if needed
                "parsed_review_json": None,
                "cost": 0.0,
                "error": None
            }

            try:
                review_prompt = (
                    f"Please critically review this {{'final execution result ' if final else 'recommendation '}}from agent '{subject_agent_name}':"
                    f"\\n---BEGIN CONTENT---\\n{content_to_review}\\n---END CONTENT---\\n\\n"
                    "Focus on validity, potential issues, and alignment with overall mission goals. "
                    "Provide specific, actionable feedback. If there are multiple issues, list them clearly. "
                    "If you approve, explain why. "
                    "Your response MUST be a JSON object with the following keys: "
                    "{\"approved\": bool, \"feedback\": str (detailed feedback/reasons for approval/disapproval), \"estimated_confidence_if_approved\": float (0.0-1.0, your confidence in the content IF you approved it, otherwise 0.0)}."
                )
                review_log_entry["prompt"] = review_prompt
                
                # _get_json_response handles retries, logs to json_parsing_logs, and returns cost
                review_json, cost = await self._get_json_response(
                    agent_instance, review_prompt,
                    f"Failed to get peer review from {agent_instance_name}",
                    json_parsing_logs # Pass the list for detailed JSON logging
                )
                accumulated_review_cost += cost
                review_log_entry["cost"] = cost # Cost for this specific review call
                review_log_entry["parsed_review_json"] = review_json
                
                # Ensure the review dict from agent has 'agent' field for backward compatibility if needed,
                # though review_log_entry already has reviewer_agent_name.
                review_json["agent"] = agent_instance_name 
                
                # Convert new review format to legacy format for compatibility
                review_json["valid"] = review_json.get("approved", False)
                review_json["issues"] = [] if review_json.get("approved", False) else [review_json.get("feedback", "No feedback provided")]
                
                all_reviews_from_batch.append(review_json)
                
                # Create a summary of issues for logging
                issues = review_json.get('issues', [])
                if issues:
                    # Show first issue as summary, truncate if too long
                    issue_summary = issues[0] if issues else "No specific issue"
                    if len(issue_summary) > 80:
                        issue_summary = issue_summary[:77] + "..."
                    if len(issues) > 1:
                        issue_summary += f" (+{len(issues)-1} more)"
                    self._log(f"Review from {agent_instance_name}: Valid={review_json.get('valid')}, Issue: {issue_summary}", "info")
                else:
                    self._log(f"Review from {agent_instance_name}: Valid={review_json.get('valid')}, No issues", "info")

            except (AgentCommunicationError, json.JSONDecodeError) as e: # Catch errors from _get_json_response
                self._log(f"Error during peer review from {agent_instance_name}: {str(e)}", "warning")
                review_log_entry["error"] = str(e)
                # Cost accumulated by _get_json_response before failure is already part of `cost` if error was during parsing.
                # If _ask_agent failed before parsing, cost might be 0 or partial from retries.
                # `cost` variable above will hold the cost from the failed _get_json_response call.
                accumulated_review_cost += review_log_entry.get("cost",0.0) # Ensure cost is added if error was after cost was set

                # Append a structured error review
                error_review = {
                    "agent": agent_instance_name, 
                    "approved": False,
                    "feedback": f"Review generation error: {str(e)}",
                    "estimated_confidence_if_approved": 0.0,
                    "valid": False,  # Legacy compatibility
                    "issues": [f"Review generation error: {str(e)}"],  # Legacy compatibility
                    "kpi_valid": False, "kpi_issues": [f"Review generation error: {str(e)}"],
                    "error_detail": str(e)
                }
                all_reviews_from_batch.append(error_review)
                review_log_entry["parsed_review_json"] = error_review # Log the error structure
            
            review_interaction_logs.append(review_log_entry) # Log after each review attempt
            
        return all_reviews_from_batch, accumulated_review_cost

    async def _get_tool_from_registry(self, tool_name: str, context: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves a tool from the registry. If not found, attempts auto-provisioning via AutoProvisionAgent.
        Returns the tool spec if found/provisioned, None otherwise.
        """
        self._log(f"Looking up tool '{tool_name}' in registry.", "debug")
        
        # First, check if tool exists in registry
        tool_spec = self.registry.get_tool_spec(tool_name)
        if tool_spec:
            self._log(f"Tool '{tool_name}' found in registry.", "info")
            return tool_spec
        
        # Tool not found, attempt auto-provisioning
        self._log(f"Tool '{tool_name}' not found in registry. Attempting auto-provisioning.", "info")
        
        missing_item_details = {
            "type": "tool",
            "name": tool_name,
            "reason": "not_found",
            "details": f"Tool '{tool_name}' was requested but not found in registry."
        }
        
        try:
            auto_provision_result = await self.auto_provision_agent.handle_trivial_request(
                context or {}, missing_item_details
            )
            
            if auto_provision_result:
                self._log(f"Auto-provisioning successful for tool '{tool_name}': {auto_provision_result}", "info")
                # Re-check registry after auto-provisioning
                tool_spec = self.registry.get_tool_spec(tool_name)
                return tool_spec
            else:
                self._log(f"Auto-provisioning declined for tool '{tool_name}' (not trivial or rejected).", "warning")
                return None
                
        except Exception as e:
            self._log(f"Error during auto-provisioning attempt for tool '{tool_name}': {str(e)}", "error")
            return None

    async def run_continuous_launch_growth_loop(self, mission_context: Dict[str, Any], max_iterations: int = 100) -> Dict[str, Any]:
        """
        Run the continuous launch and growth loop using dynamic agent calls through the registry.
        
        This replaces one-off calls with a persistent while True loop that orchestrates via 
        registry-looked-up agents as specified in Task 3.
        
        Args:
            mission_context: Dictionary containing mission details and constraints
            max_iterations: Maximum number of loop iterations to prevent infinite loops
            
        Returns:
            Dictionary with loop execution summary and final state
        """
        self._log("Starting Continuous Launch & Growth Loop", "info")
        
        # Initialize context with mission details
        context = {
            "mission": mission_context.get("overall_mission", ""),
            "constraints": mission_context.get("constraints", {}),
            "iteration": 0,
            "total_revenue": 0.0,
            "loop_history": []
        }
        
        loop_summary = {
            "total_iterations": 0,
            "total_revenue_generated": 0.0,
            "guardrail_breaches": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "final_status": "unknown",
            "execution_log": []
        }
        
        try:
            iteration = 0
            while iteration < max_iterations:
                iteration += 1
                context["iteration"] = iteration
                
                self._log(f"Starting loop iteration {iteration}", "info")
                cycle_log = {
                    "iteration": iteration,
                    "timestamp": datetime.now().isoformat(),
                    "steps": {},
                    "errors": [],
                    "revenue_generated": 0.0
                }
                
                try:
                    # Step 1: Scan for opportunities
                    self._log("Executing ScanAgent", "info")
                    scan_agent = self.agents.get("ScanAgent") or self.registry.get_agent("ScanAgent", mission_context)
                    if not scan_agent:
                        raise Exception("ScanAgent not available in registry")
                    
                    scan_out = scan_agent.execute(context)
                    if hasattr(scan_out, '__await__'):
                        scan_out = await scan_out
                    
                    cycle_log["steps"]["scan"] = {
                        "status": "completed",
                        "output_summary": str(scan_out)[:200] + "..." if len(str(scan_out)) > 200 else str(scan_out)
                    }
                    
                    # Step 2: Deploy MVP
                    self._log("Executing DeployAgent", "info")
                    deploy_agent = self.agents.get("DeployAgent") or self.registry.get_agent("DeployAgent", mission_context)
                    if not deploy_agent:
                        raise Exception("DeployAgent not available in registry")
                    
                    deploy_out = deploy_agent.execute(scan_out)
                    if hasattr(deploy_out, '__await__'):
                        deploy_out = await deploy_out
                    
                    cycle_log["steps"]["deploy"] = {
                        "status": "completed",
                        "output_summary": str(deploy_out)[:200] + "..." if len(str(deploy_out)) > 200 else str(deploy_out)
                    }
                    
                    # Step 3: Run marketing campaigns
                    self._log("Executing CampaignAgent", "info")
                    campaign_agent = self.agents.get("CampaignAgent") or self.registry.get_agent("CampaignAgent", mission_context)
                    if not campaign_agent:
                        raise Exception("CampaignAgent not available in registry")
                    
                    campaign_out = campaign_agent.execute(deploy_out)
                    if hasattr(campaign_out, '__await__'):
                        campaign_out = await campaign_out
                    
                    cycle_log["steps"]["campaign"] = {
                        "status": "completed",
                        "output_summary": str(campaign_out)[:200] + "..." if len(str(campaign_out)) > 200 else str(campaign_out)
                    }
                    
                    # Step 4: Collect and analyze metrics
                    self._log("Executing AnalyticsAgent", "info")
                    analytics_agent = self.agents.get("AnalyticsAgent") or self.registry.get_agent("AnalyticsAgent", mission_context)
                    if not analytics_agent:
                        raise Exception("AnalyticsAgent not available in registry")
                    
                    metrics = analytics_agent.execute(campaign_out)
                    if hasattr(metrics, '__await__'):
                        metrics = await metrics
                    
                    cycle_log["steps"]["analytics"] = {
                        "status": "completed",
                        "output_summary": str(metrics)[:200] + "..." if len(str(metrics)) > 200 else str(metrics)
                    }
                    
                    # Extract revenue from metrics (handle different possible formats)
                    revenue = 0.0
                    if isinstance(metrics, dict):
                        revenue = metrics.get("revenue", 0.0)
                        if isinstance(revenue, str):
                            try:
                                revenue = float(revenue)
                            except ValueError:
                                revenue = 0.0
                    elif hasattr(metrics, 'data') and isinstance(metrics.data, dict):
                        revenue = metrics.data.get("revenue", 0.0)
                    
                    cycle_log["revenue_generated"] = revenue
                    context["total_revenue"] += revenue
                    
                    # Step 5: Financial guardrail check
                    self._log("Executing FinanceAgent for guardrail check", "info")
                    finance_agent = self.agents.get("FinanceAgent") or self.registry.get_agent("FinanceAgent", mission_context)
                    if not finance_agent:
                        raise Exception("FinanceAgent not available in registry")
                    
                    guard = finance_agent.execute(metrics)
                    if hasattr(guard, '__await__'):
                        guard = await guard
                    
                    cycle_log["steps"]["finance_guard"] = {
                        "status": "completed",
                        "output_summary": str(guard)[:200] + "..." if len(str(guard)) > 200 else str(guard)
                    }
                    
                    # Check guardrail response
                    guard_status = "OK"
                    if isinstance(guard, dict):
                        guard_status = guard.get("approval_status", "OK")
                    elif isinstance(guard, str):
                        guard_status = guard
                    elif hasattr(guard, 'data') and isinstance(guard.data, dict):
                        guard_status = guard.data.get("approval_status", "OK")
                    
                    if guard_status == "PAUSE" or "PAUSE" in str(guard_status).upper():
                        self._log("Guardrail breached; pausing pipeline", "warning")
                        loop_summary["guardrail_breaches"] += 1
                        loop_summary["final_status"] = "guardrail_breach"
                        cycle_log["steps"]["finance_guard"]["breach"] = True
                        break
                    
                    # Step 6: Growth optimization (if revenue > 0)
                    if revenue > 0:
                        self._log("Revenue detected, executing GrowthAgent", "info")
                        growth_agent = self.agents.get("GrowthAgent") or self.registry.get_agent("GrowthAgent", mission_context)
                        if growth_agent:
                            growth_out = growth_agent.execute(metrics)
                            if hasattr(growth_out, '__await__'):
                                growth_out = await growth_out
                            
                            cycle_log["steps"]["growth"] = {
                                "status": "completed",
                                "output_summary": str(growth_out)[:200] + "..." if len(str(growth_out)) > 200 else str(growth_out)
                            }
                        else:
                            self._log("GrowthAgent not available, skipping growth optimization", "warning")
                            cycle_log["steps"]["growth"] = {
                                "status": "skipped",
                                "reason": "GrowthAgent not available"
                            }
                    else:
                        cycle_log["steps"]["growth"] = {
                            "status": "skipped",
                            "reason": "No revenue generated"
                        }
                    
                    # Update context for next iteration
                    context["loop_history"].append({
                        "iteration": iteration,
                        "revenue": revenue,
                        "total_revenue": context["total_revenue"],
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    loop_summary["successful_cycles"] += 1
                    self._log(f"Loop iteration {iteration} completed successfully. Revenue: ${revenue:.2f}", "info")
                    
                except Exception as e:
                    self._log(f"Error in loop iteration {iteration}: {str(e)}", "error")
                    cycle_log["errors"].append(str(e))
                    loop_summary["failed_cycles"] += 1
                    
                    # Continue to next iteration unless it's a critical error
                    if "not available in registry" in str(e):
                        self._log("Critical agent missing, stopping loop", "error")
                        loop_summary["final_status"] = "critical_agent_missing"
                        break
                
                loop_summary["execution_log"].append(cycle_log)
                
                # Add a small delay between iterations to prevent overwhelming
                await asyncio.sleep(1)
            
            # Set final status if not already set
            if loop_summary["final_status"] == "unknown":
                if iteration >= max_iterations:
                    loop_summary["final_status"] = "max_iterations_reached"
                else:
                    loop_summary["final_status"] = "completed"
            
            loop_summary["total_iterations"] = iteration
            loop_summary["total_revenue_generated"] = context["total_revenue"]
            
            self._log(f"Continuous Launch & Growth Loop completed. Total iterations: {iteration}, Total revenue: ${context['total_revenue']:.2f}", "info")
            
        except Exception as e:
            self._log(f"Critical error in continuous loop: {str(e)}", "error")
            loop_summary["final_status"] = "critical_error"
            loop_summary["error"] = str(e)
        
        return loop_summary

    def alert(self, message: str):
        """Alert method for guardrail breaches and other important notifications."""
        self._log(f"ALERT: {message}", "warning")
        # In a real implementation, this could send notifications, emails, etc.

    async def execute_continuous_mode(self, mission_context: Dict[str, Any], max_iterations: int = 10) -> Dict[str, Any]:
        """
        Execute the orchestrator in continuous mode, replacing the traditional decision cycle approach.
        
        This method bootstraps the C-Suite agents and then runs the continuous launch and growth loop.
        
        Args:
            mission_context: Dictionary containing mission details and constraints
            max_iterations: Maximum number of loop iterations (default 10 for safety)
            
        Returns:
            Dictionary with execution summary and results
        """
        self._log("Starting Orchestrator in Continuous Mode", "info")
        
        try:
            # Bootstrap C-Suite agents first
            await self.bootstrap_c_suite(mission_context.get("overall_mission", ""))
            
            # Run the continuous launch and growth loop
            loop_results = await self.run_continuous_launch_growth_loop(mission_context, max_iterations)
            
            return {
                "mode": "continuous",
                "status": "completed",
                "loop_results": loop_results,
                "message": f"Continuous mode completed with {loop_results['total_iterations']} iterations"
            }
            
        except Exception as e:
            self._log(f"Error in continuous mode execution: {str(e)}", "error")
            return {
                "mode": "continuous",
                "status": "error",
                "error": str(e),
                "message": f"Continuous mode failed: {str(e)}"
            }



# Factory function to create orchestrator (if needed by CLI or other parts)
def create_orchestrator(client: Optional[OpenAIChatCompletionClient] = None) -> OrchestrationAgent:
    if not client:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not set and no client provided.")
            raise ValueError("OPENAI_API_KEY environment variable not set and no client provided.")
        
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        logger.info(f"Initializing OpenAIChatCompletionClient with model: {model_name} using API key from environment.")
        client = OpenAIChatCompletionClient(
            api_key=api_key,
            model=model_name
        )
    else:
        logger.info("Using provided OpenAIChatCompletionClient instance.")
        
    return OrchestrationAgent(client=client)
