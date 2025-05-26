# orchestrator/agent_management.py

import os
import re
import json
import logging
import importlib
import inspect
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from autogen_core import RoutedAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

logger = logging.getLogger(__name__)

class TemplateError(Exception):
    """Raised when a template cannot be loaded."""
    pass

def load_template(name: str) -> str:
    """Load a template file with error handling."""
    try:
        # Try relative path first (when running from launchonomy directory)
        path = os.path.join("templates", f"{name}.txt")
        if not os.path.exists(path):
            # Fallback to launchonomy package path
            path = os.path.join("launchonomy", "templates", f"{name}.txt")
        
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Template file not found: {path}")
        raise TemplateError(f"Template '{name}' not found")
    except Exception as e:
        logger.error(f"Error loading template {name}: {str(e)}")
        raise TemplateError(f"Error loading template '{name}': {str(e)}")

class AgentManager:
    """
    Handles agent creation, loading, and lifecycle management.
    
    This class provides functionality for:
    - Loading registered agents from the registry
    - Creating new specialized agents dynamically
    - Managing agent instances and their lifecycle
    - Bootstrapping C-Suite agents
    """
    
    def __init__(self, registry, client: OpenAIChatCompletionClient, log_callback=None):
        self.registry = registry
        self.client = client
        self.log_callback = log_callback
        self.agents: Dict[str, RoutedAgent] = {}
        self.c_suite_bootstrapped = False

    def _log(self, message: str, msg_type: str = "info"):
        """Log a message using the callback if available."""
        # Ensure message is a string
        if not isinstance(message, str):
            try:
                message = str(message)
            except (TypeError, ValueError, AttributeError) as e:
                message = f"Failed to convert log message to string: {e}"

        if self.log_callback:
            self.log_callback("AgentManager", message, msg_type)
        # Standard logging as well
        if msg_type == "error":
            logger.error(f"AgentManager: {message}")
        elif msg_type == "warning":
            logger.warning(f"AgentManager: {message}")
        elif msg_type == "debug":
            logger.debug(f"AgentManager: {message}")
        else:
            logger.info(f"AgentManager: {message}")

    def load_registered_agents(self):
        """Load and instantiate all registered agents at startup."""
        self._log("Loading registered agents from registry...", "info")
        
        agent_names = self.registry.list_agent_names()
        loaded_count = 0
        failed_count = 0
        
        for name in agent_names:
            try:
                # Skip self-reference to avoid circular instantiation
                if name == "OrchestrationAgent":
                    continue
                    
                info = self.registry.get_agent_info(name)
                if info and 'module' in info and 'class' in info:
                    # Dynamically import and instantiate the agent
                    try:
                        module = importlib.import_module(info["module"])
                    except ImportError:
                        # Try without the orchestrator prefix if running from root directory
                        if info["module"].startswith("orchestrator."):
                            module_name = info["module"][len("orchestrator."):]
                            module = importlib.import_module(module_name)
                        else:
                            raise
                    cls = getattr(module, info["class"])
                    
                    # Check which parameter name the constructor expects
                    sig = inspect.signature(cls.__init__)
                    param_names = list(sig.parameters.keys())
                    
                    # Instantiate with appropriate parameter name
                    if 'coa' in param_names:
                        agent_instance = cls(registry=self.registry, coa=self)
                    elif 'orchestrator' in param_names:
                        agent_instance = cls(registry=self.registry, orchestrator=self)
                    else:
                        # Fallback: try with registry only
                        agent_instance = cls(registry=self.registry)
                    
                    # Set the client and other attributes
                    agent_instance._client = self.client
                    agent_instance.log_callback = self.log_callback
                    if not hasattr(agent_instance, 'name'):
                        agent_instance.name = name
                    
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

    async def create_agent(self, role_name: str, persona: str, primer: str) -> RoutedAgent:
        """Create a new agent with the given role and primer."""
        try:
            self._log(f"Creating new agent: '{role_name}' ({persona[:50]}...)", "info")
            if role_name in self.agents:
                 self._log(f"Warning: Agent with name '{role_name}' already exists. Overwriting may occur if not handled by caller.", "warning")

            full_system_prompt = f"You are {role_name}. {persona}\n\n{primer}"
            # Agent creation itself is not an LLM call, so no direct cost.
            agent = RoutedAgent(full_system_prompt) 
            agent._client = self.client 
            agent.log_callback = self.log_callback 
            agent.name = role_name 
            self.agents[role_name] = agent # Register agent
            self._log(f"Agent '{role_name}' created successfully.", "info")
            return agent # Return the created agent instance
        except Exception as e:
            self._log(f"Failed to create agent '{role_name}': {str(e)}", "error")
            raise

    async def create_specialized_agent(self, 
                                       decision: str, 
                                       agent_management_logs: List[dict],
                                       json_parsing_logs: List[dict],
                                       communicator
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
                f"Design a specialist agent for this decision: \"{decision}\".\n"
                "The agent should be focused and effective for this specific task. "
                "Reply with JSON containing these keys: "
                "{\"name\":str (a concise, descriptive name for the agent, e.g., \"CodeReviewAgent\"), "
                "\"persona\":str (a brief description of its persona), "
                "\"expertise\":str (comma-separated list of key expertise areas)}."
            )
            # Use a dummy orchestrator agent for spec generation - this would need to be passed in
            # For now, we'll create a simple spec without LLM call
            agent_spec = {
                "name": f"SpecialistAgent_{len(self.agents)}",
                "persona": f"an AI assistant specialized for {decision[:30]}...",
                "expertise": "general problem solving"
            }
            
            creation_event["cost_of_spec_generation"] = 0.0  # No LLM call made
            
            # Use the 'name' from spec as the primary basis for role and template lookup
            agent_name_from_spec = agent_spec.get("name", "SpecialistAgent")
            role = agent_spec.get("role", agent_name_from_spec) 
            persona = agent_spec.get("persona", f"an AI assistant specialized for {decision[:30]}...")
            expertise = agent_spec.get("expertise", "general problem solving")
            
            creation_event["role"] = role
            creation_event["persona"] = persona
            creation_event["expertise"] = expertise

            sane_role_name = re.sub(r'\W+', '_', role)
            if not sane_role_name: 
                sane_role_name = "Specialist"
            base_sane_role_name = sane_role_name
            counter = 1
            while sane_role_name in self.agents:
                sane_role_name = f"{base_sane_role_name}_{counter}"
                counter += 1
            creation_event["agent_name"] = sane_role_name
            
            try:
                # Use the agent_name_from_spec for template lookup
                template_name_to_try = agent_name_from_spec.lower().replace(" ", "_")
                primer = load_template(f"specialist_{template_name_to_try}")
                self._log(f"Loaded template 'specialist_{template_name_to_try}.txt' for role {sane_role_name}", "info")
                creation_event["primer_source"] = f"template: specialist_{template_name_to_try}.txt"
            except TemplateError:
                self._log(f"No specific template for role '{template_name_to_try}'. Constructing primer for {sane_role_name} from spec.", "info")
                primer = (
                    f"You are {sane_role_name}. {persona}.\n"
                    f"Your core expertise lies in: {expertise}.\n"
                    "Focus on your specialized role to address the tasks given to you."
                )
                creation_event["primer_source"] = "generated_from_spec"
            
            created_agent = await self.create_agent(sane_role_name, persona, primer)
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
            
            fallback_agent = await self.create_agent(generic_agent_name, "a generic AI assistant for fallback scenarios", generic_primer)
            agent_management_logs.append(creation_event)
            return fallback_agent, accumulated_creation_cost

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
                agent = await self.create_agent(agent_name, spec['persona'], system_prompt)
                
                # C-Suite agents are managed in AgentManager only, not in registry
                # They are temporary and should not appear in registry listings
                
                self._log(f"✅ Bootstrapped {agent_name}: {spec['persona']}", "info")
                
            except Exception as e:
                self._log(f"❌ Failed to bootstrap {agent_name}: {str(e)}", "error")
                # Continue with other agents even if one fails
        
        self.c_suite_bootstrapped = True
        self._log(f"🎉 C-Suite bootstrap complete! Active agents: {len(self.agents)}", "info")
        
        return bootstrap_cost

    async def cleanup_agents(self):
        """Clean up agents after mission completion."""
        agent_names_to_remove = list(self.agents.keys())
        self._log(f"Starting cleanup of {len(agent_names_to_remove)} agents.", "debug")
        for agent_name in agent_names_to_remove:
            # No explicit client close needed for autogen_ext.models.openai.OpenAIChatCompletionClient
            if agent_name in self.agents:
                 del self.agents[agent_name]
        self._log(f"Cleaned up agents. Active agents now: {len(self.agents)}", "info") 