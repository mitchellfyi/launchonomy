import logging
import json
from typing import Dict, List, Tuple, Any, Optional
from autogen_core import RoutedAgent
from autogen_core.models import SystemMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient # Assuming this is the client used

# Assuming agent_comm.py and utils.py are in the same directory or accessible
from .agent_comm import _get_json_response, AgentCommunicationError, _ask_agent
from .utils import load_template, TemplateError

logger = logging.getLogger(__name__)

async def _create_agent(orchestrator_agent_instance: Any, role_name: str, persona: str, primer: str) -> RoutedAgent:
    """Creates a new RoutedAgent."""
    # Ensure the primer is loaded or use the provided string
    system_prompt_content = primer # Use primer directly

    # Create a new client for the agent, possibly a new instance or reuse parts of orchestrator's client
    # This part might need adjustment based on how clients are managed.
    # For now, assume a new client instance is created or orchestrator's client can be used/adapted.
    if not orchestrator_agent_instance._client:
        raise ValueError("Orchestrator's client is not initialized.")
    
    # If OpenAIChatCompletionClient is used and needs specific config:
    # agent_client = OpenAIChatCompletionClient(api_key=os.environ.get("OPENAI_API_KEY")) 
    # This is a placeholder; actual client init might differ based on project setup.
    agent_client = orchestrator_agent_instance._client # Simplification: reuse client

    new_agent = RoutedAgent(system_prompt=SystemMessage(content=system_prompt_content, source="system"), client=agent_client)
    new_agent.name = role_name
    # Add the new agent to the orchestrator's agent dictionary
    orchestrator_agent_instance.agents[role_name] = new_agent
    orchestrator_agent_instance._log(f"Agent '{role_name}' created with persona: '{persona[:50]}...'", "info")
    return new_agent

async def _create_specialized_agent(
    orchestrator_agent_instance: Any,
    decision: str, 
    agent_management_logs: List[dict],
    json_parsing_logs: List[dict]
) -> Tuple[RoutedAgent, float]: # Returns Agent, Cost
    """Creates a new specialized agent based on the decision."""
    total_cost = 0.0
    timestamp = orchestrator_agent_instance._get_timestamp()
    log_entry_base = {"timestamp": timestamp, "decision_focus": decision}

    try:
        # 1. Define Role and Persona for the new agent using the Orchestrator
        role_prompt = (
            f"Consider the decision: '{decision}'. "
            f"Define an expert role and a detailed persona for an AI agent that would be best suited to make this decision. "
            f"The persona should include typical skills, knowledge areas, and operational style. "
            f"Respond in JSON format with keys: 'role_name' (e.g., 'MarketAnalyst', 'LogisticsCoordinator'), "
            f"and 'persona' (a 2-3 sentence description)."
        )
        agent_management_logs.append({**log_entry_base, "event": "request_role_definition", "prompt": role_prompt})
        
        role_data_json, cost = await _get_json_response(
            orchestrator_agent_instance, # Orchestrator asks itself
            role_prompt, 
            "Failed to define agent role/persona", 
            json_parsing_logs,
            orchestrator_agent_instance._log,
            orchestrator_agent_instance._extract_json_from_string,
            retry_count=orchestrator_agent_instance.MAX_JSON_RETRIES
        )
        total_cost += cost
        agent_management_logs[-1].update({"response": role_data_json, "cost": cost, "status": "success"})
        
        role_name = role_data_json.get("role_name", "DefaultSpecialist")
        persona = role_data_json.get("persona", "An expert in the relevant field.")
        orchestrator_agent_instance._log(f"Defined role: {role_name}, Persona: {persona[:50]}... Cost: ${cost:.4f}", "debug")

        # 2. Generate System Primer for the new agent using the Orchestrator
        primer_prompt = (
            f"Generate a concise system primer (around 150-200 words) for an AI agent with the role '{role_name}' and persona '{persona}'. "
            f"This primer will be its main system prompt. It should guide the agent on its core responsibilities, how to approach tasks related to '{decision}', "
            f"key principles to follow, and the expected format of its output (e.g., detailed analysis, specific recommendations). "
            f"Ensure it emphasizes clarity, data-driven insights, and actionable outputs. The agent will be asked to respond in JSON with keys 'analysis', 'reasoning', 'recommendation'."
        )
        agent_management_logs.append({**log_entry_base, "event": "request_primer_generation", "role_name": role_name, "persona": persona, "prompt": primer_prompt})
        
        # For primer, we expect a string, not JSON necessarily, unless we want to structure primer generation more.
        # Let's use _ask_agent directly, assuming orchestrator can generate text well.
        primer_text, cost = await _ask_agent(orchestrator_agent_instance, primer_prompt, orchestrator_agent_instance._log, response_format_json=False) # Orchestrator asks itself
        total_cost += cost
        agent_management_logs[-1].update({"response": primer_text, "cost": cost, "status": "success"})
        orchestrator_agent_instance._log(f"Generated primer for {role_name}. Cost: ${cost:.4f}", "debug")

        # 3. Create the agent instance
        new_agent = await _create_agent(orchestrator_agent_instance, role_name, persona, primer_text)
        agent_management_logs.append({**log_entry_base, "event": "agent_instantiated", "agent_name": new_agent.name, "primer_summary": primer_text[:100]+"..."})
        
        return new_agent, total_cost

    except AgentCommunicationError as e:
        orchestrator_agent_instance._log(f"Error creating specialized agent for '{decision}': {e}", "error")
        agent_management_logs.append({**log_entry_base, "event": "error_creating_agent", "error": str(e)})
        raise # Re-raise to be handled by the caller (e.g., execute_decision_cycle)
    except Exception as e:
        orchestrator_agent_instance._log(f"Unexpected error during specialized agent creation for '{decision}': {e}", "error")
        agent_management_logs.append({**log_entry_base, "event": "unexpected_error_creating_agent", "error": str(e)})
        # Depending on policy, might want to raise or return a default/dummy agent + cost
        raise AgentCommunicationError(f"Failed to create specialist agent due to an unexpected error: {str(e)}") from e

async def _select_or_create_specialist(
    orchestrator_agent_instance: Any,
    decision: str, 
    agent_management_logs: List[dict],
    json_parsing_logs: List[dict]
) -> Tuple[RoutedAgent, float, float]: # Returns: Agent, Confidence, Cost
    """Selects an existing agent or creates a new one if no suitable agent is found."""
    total_cost = 0.0
    timestamp = orchestrator_agent_instance._get_timestamp()

    # Phase 1: Orchestrator determines if an existing agent is suitable
    if not orchestrator_agent_instance.agents: # No agents exist yet
        orchestrator_agent_instance._log("No existing agents. Creating a new specialist.", "info")
        agent_management_logs.append({"timestamp": timestamp, "event": "no_agents_exist", "decision": decision})
        new_agent, creation_cost = await _create_specialized_agent(orchestrator_agent_instance, decision, agent_management_logs, json_parsing_logs)
        total_cost += creation_cost
        return new_agent, 1.0, total_cost # Confidence 1.0 as it's tailor-made

    agent_profiles = []
    for name, agent_obj in orchestrator_agent_instance.agents.items():
        # Try to get persona from system prompt if available
        persona = "General Agent"
        if agent_obj.system_prompt:
            if isinstance(agent_obj.system_prompt, SystemMessage):
                persona = agent_obj.system_prompt.content[:150] + "..." # Summary of primer
            elif isinstance(agent_obj.system_prompt, str):
                persona = agent_obj.system_prompt[:150] + "..."
        agent_profiles.append(f"- Agent Name: {name}, Persona/Primer Summary: {persona}")
    
    profiles_description = "\n".join(agent_profiles)
    
    selection_prompt = (
        f"Given the current decision focus: '{decision}'\n"
        f"And the following available agents with their persona/primer summaries:\n{profiles_description}\n\n"
        f"Which agent is best suited for this decision? "
        f"If a suitable agent exists, respond with a JSON object: \{{\"agent_name\": \"AGENT_NAME\", \"confidence_score\": SCORE (0.0-1.0)\}}. "
        f"If no existing agent is suitable (e.g., confidence < {orchestrator_agent_instance.CONFIDENCE_THRESHOLD}), respond with JSON: \{{\"agent_name\": \"CREATE_NEW\", \"confidence_score\": 0.0\}}. "
        f"Base your confidence score on how well the agent's described persona/skills align with the decision's requirements."
    )
    agent_management_logs.append({"timestamp": timestamp, "event": "request_agent_selection", "decision": decision, "prompt": selection_prompt, "available_agents": list(orchestrator_agent_instance.agents.keys())})
    
    try:
        selection_json, cost = await _get_json_response(
            orchestrator_agent_instance, # Orchestrator asks itself
            selection_prompt, 
            "Failed to get agent selection from orchestrator", 
            json_parsing_logs,
            orchestrator_agent_instance._log,
            orchestrator_agent_instance._extract_json_from_string,
            retry_count=orchestrator_agent_instance.MAX_JSON_RETRIES
        )
        total_cost += cost
        agent_management_logs[-1].update({"response": selection_json, "cost": cost, "status": "success"})
        orchestrator_agent_instance._log(f"Agent selection response: {selection_json}. Cost: ${cost:.4f}", "debug")

        selected_agent_name = selection_json.get("agent_name")
        confidence = float(selection_json.get("confidence_score", 0.0))

        if selected_agent_name != "CREATE_NEW" and selected_agent_name in orchestrator_agent_instance.agents and confidence >= orchestrator_agent_instance.CONFIDENCE_THRESHOLD:
            orchestrator_agent_instance._log(f"Selected existing agent: {selected_agent_name} with confidence {confidence:.2f}", "info")
            agent_management_logs.append({"timestamp": orchestrator_agent_instance._get_timestamp(), "event": "existing_agent_selected", "agent_name": selected_agent_name, "confidence": confidence, "decision": decision})
            return orchestrator_agent_instance.agents[selected_agent_name], confidence, total_cost
        else:
            orchestrator_agent_instance._log(f"Decision to create new agent (or low confidence: {confidence:.2f} for '{selected_agent_name}'). Creating specialist for: {decision}", "info")
            agent_management_logs.append({"timestamp": orchestrator_agent_instance._get_timestamp(), "event": "creating_new_specialist_due_to_selection", "decision": decision, "selection_confidence": confidence, "selected_name_attempt": selected_agent_name})
            new_agent, creation_cost = await _create_specialized_agent(orchestrator_agent_instance, decision, agent_management_logs, json_parsing_logs)
            total_cost += creation_cost
            # Confidence for a newly created agent is high as it's custom-built.
            return new_agent, 1.0, total_cost 
            
    except AgentCommunicationError as e:
        orchestrator_agent_instance._log(f"Error during agent selection/creation for '{decision}': {e}. Defaulting to creating new agent.", "warning")
        agent_management_logs.append({"timestamp": orchestrator_agent_instance._get_timestamp(), "event": "error_in_selection_default_to_create", "decision": decision, "error": str(e)})
        # Fallback: if selection process fails, create a new agent.
        new_agent, creation_cost = await _create_specialized_agent(orchestrator_agent_instance, decision, agent_management_logs, json_parsing_logs)
        total_cost += creation_cost
        return new_agent, 1.0, total_cost # Confidence 1.0 as it's tailor-made
    except Exception as e:
        orchestrator_agent_instance._log(f"Unexpected error during agent selection for '{decision}': {e}. Defaulting to new agent.", "error")
        agent_management_logs.append({"timestamp": orchestrator_agent_instance._get_timestamp(), "event": "unexpected_error_in_selection_default_to_create", "error": str(e)})
        new_agent, creation_cost = await _create_specialized_agent(orchestrator_agent_instance, decision, agent_management_logs, json_parsing_logs)
        total_cost += creation_cost
        return new_agent, 1.0, total_cost

async def _cleanup_agents(orchestrator_agent_instance: Any):
    """Placeholder for agent cleanup logic (e.g., delete agents not in use)."""
    orchestrator_agent_instance._log(f"Cleaning up agents. Currently {len(orchestrator_agent_instance.agents)} agents.", "info")
    # For now, this is a conceptual cleanup. 
    # Actual implementation might involve more sophisticated tracking of agent usage.
    # Example: if agents have a specific client that needs closing:
    # for agent_name, agent_obj in self.agents.items():
    #     if hasattr(agent_obj._client, 'close'):
    #         await agent_obj._client.close()
    #         self._log(f"Closed client for agent {agent_name}", "debug")
    orchestrator_agent_instance.agents.clear()
    orchestrator_agent_instance._log("All agents cleared from orchestrator.", "info") 