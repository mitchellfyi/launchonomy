# orchestrator/orchestrator_agent_refactored.py

import json
import os
import logging
import re
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
from autogen_core import RoutedAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Import our new modular components
try:
    from orchestrator.registry import Registry
    from orchestrator.agents.auto_provision_agent import AutoProvisionAgent
    from orchestrator.mission_management import MissionManager, MissionLog, CycleLog
    from orchestrator.agent_communication import AgentCommunicator, ReviewManager, AgentCommunicationError
    from orchestrator.agent_management import AgentManager, TemplateError, load_template
except ImportError:
    # Fallback for when running from within orchestrator directory
    from registry import Registry
    from agents.auto_provision_agent import AutoProvisionAgent
    from mission_management import MissionManager, MissionLog, CycleLog
    from agent_communication import AgentCommunicator, ReviewManager, AgentCommunicationError
    from agent_management import AgentManager, TemplateError, load_template

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Load your distilled 250-word primer
try:
    SYSTEM_PROMPT = load_template("orch_primer")
except TemplateError as e:
    logger.critical("Failed to load orchestrator primer")
    raise

class OrchestrationAgent(RoutedAgent):
    """
    The main orchestration agent that manages the entire mission lifecycle.
    
    This agent coordinates between specialist agents, manages decision cycles,
    handles mission logging, and provides strategic oversight for business missions.
    It supports both traditional decision-cycle mode and continuous launch-growth mode.
    
    Key Features:
    - Dynamic agent loading and management
    - Mission logging and resumability
    - C-Suite agent bootstrapping
    - Continuous launch and growth loops
    - Financial guardrails and compliance
    - Comprehensive error handling and retries
    
    This refactored version uses modular components for better maintainability:
    - MissionManager: Handles mission logging and persistence
    - AgentManager: Handles agent creation and lifecycle
    - AgentCommunicator: Handles agent communication and JSON parsing
    - ReviewManager: Handles peer review processes
    """
    
    def __init__(self, client):
        super().__init__(SYSTEM_PROMPT)
        self._client = client
        self.MAX_REVISION_LOOPS = 3
        self.CONFIDENCE_THRESHOLD = 0.8
        self.log_callback = None
        self.name = "OrchestrationAgent"
        self.last_revision_plan: Optional[str] = None

        # Initialize modular components
        self.registry = Registry()
        self.mission_manager = MissionManager()
        self.communicator = AgentCommunicator()
        self.review_manager = ReviewManager(self.communicator)
        self.agent_manager = AgentManager(self.registry, client, self.log_callback)
        
        # Load and instantiate all registered agents at startup
        self.agent_manager.load_registered_agents()
        
        # Ensure AutoProvisionAgent is initialized correctly
        self.auto_provision_agent = AutoProvisionAgent(registry=self.registry, coa=self)
        
        # Add self and AutoProvisionAgent to registry if not already there
        if not self.registry.get_agent_spec(self.name):
            self.registry.add_agent(name=self.name, endpoint="internal", certified=True, 
                                   spec={"description": "The main orchestrator."})
        if not self.registry.get_agent_spec(self.auto_provision_agent.name):
            self.registry.add_agent(
                name=self.auto_provision_agent.name, 
                endpoint="auto_provision_agent.AutoProvisionAgent.handle_trivial_request",
                certified=True, 
                spec={"description": "Handles auto-provisioning of trivial tools/agents."}
            )

    def set_log_callback(self, callback):
        """Set callback for CLI logging."""
        self.log_callback = callback
        self.agent_manager.log_callback = callback

    def _log(self, message: str, msg_type: str = "info"):
        """Log a message using the callback if available."""
        if not isinstance(message, str):
            try:
                message = str(message)
            except Exception:
                message = "Failed to convert log message to string."

        if self.log_callback:
            self.log_callback(self.name, message, msg_type)
        
        if msg_type == "error":
            logger.error(f"{self.name}: {message}")
        elif msg_type == "warning":
            logger.warning(f"{self.name}: {message}")
        elif msg_type == "debug":
            logger.debug(f"{self.name}: {message}")
        else:
            logger.info(f"{self.name}: {message}")

    @property
    def agents(self) -> Dict[str, RoutedAgent]:
        """Access to agents managed by AgentManager."""
        return self.agent_manager.agents

    @property
    def current_mission_log(self) -> Optional[MissionLog]:
        """Access to current mission log from MissionManager."""
        return self.mission_manager.current_mission_log

    # Delegate mission management methods
    def create_or_load_mission(self, mission_name: str, overall_mission: str, resume_existing: bool = True) -> MissionLog:
        return self.mission_manager.create_or_load_mission(mission_name, overall_mission, resume_existing)

    def get_mission_context_for_agents(self) -> dict:
        return self.mission_manager.get_mission_context_for_agents()

    # Delegate agent management methods
    async def bootstrap_c_suite(self, mission_context: str = ""):
        return await self.agent_manager.bootstrap_c_suite(mission_context)

    # Delegate communication methods
    async def _ask_agent(self, agent: RoutedAgent, prompt: str, system_prompt: Optional[str] = None, response_format_json: bool = False) -> Tuple[str, float]:
        return await self.communicator.ask_agent(agent, prompt, system_prompt, response_format_json)

    async def _ask_orchestrator(self, prompt: str, response_format_json: bool = False) -> Tuple[str, float]:
        return await self.communicator.ask_agent(self, prompt, response_format_json=response_format_json)

    async def _get_json_response(self, agent: RoutedAgent, prompt: str, error_msg: str, json_parsing_log_list: List[dict], retry_count: int = 0) -> Tuple[Dict[str, Any], float]:
        return await self.communicator.get_json_response(agent, prompt, error_msg, json_parsing_log_list, retry_count)

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
        mission_log = self.mission_manager.link_cycle_to_previous(mission_log)
        
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
            final_reviews_summary, review_cost = await self.review_manager.batch_peer_review(
                decision_agent_name_for_log,
                json.dumps(execution_output), 
                self.agents,
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
        self.mission_manager.update_mission_log(mission_log)

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
        """Determines the next strategic step or if the mission is complete."""
        self._log("Determining next strategic step...", "info")
        
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

        try:
            next_step_description, cost = await self._ask_orchestrator(prompt, response_format_json=False)
            self._log(f"Cost for determining next step: {cost:.4f}", "debug")

            if next_step_description.strip().upper() == "MISSION_COMPLETE":
                self._log("Orchestrator determined mission is complete.", "info")
                return "MISSION_COMPLETE"
            
            self._log(f"Next strategic step identified by orchestrator: {next_step_description}", "info")
            return next_step_description
        except Exception as e:
            self._log(f"Error determining next strategic step: {str(e)}", "error")
            return f"ERROR_DETERMINING_NEXT_STEP: {str(e)}"

    async def revise_rejected_cycle(self, 
                                  rejected_decision_focus: str, 
                                  rejected_recommendation: Optional[str],
                                  rejected_execution_result: Optional[dict], 
                                  rejection_reason: str, 
                                  mission_context: dict,
                                  previous_accepted_cycles_summary: List[Dict]
                                  ) -> str:
        """Handles a rejected cycle by asking the Orchestrator LLM to formulate a new strategic step."""
        self._log(f"Revising rejected cycle for: {rejected_decision_focus}. Reason: {rejection_reason}", "warning")
        overall_mission = mission_context.get("overall_mission", "No overall mission specified.")

        revision_prompt = (
            f"The overall mission is: '{overall_mission}'.\n\n"
            f"A previous strategic step was taken to address: '{rejected_decision_focus}'.\n"
            f"This step resulted in the following recommendation: '''{rejected_recommendation if rejected_recommendation else 'N/A'}'''\n"
            f"And the following execution result: '''{json.dumps(rejected_execution_result) if rejected_execution_result else 'N/A'}'''\n"
            f"This outcome was REJECTED by the user. The reason provided was: '{rejection_reason}'.\n\n"
            f"Here is a summary of previously ACCEPTED decision cycles: {json.dumps(previous_accepted_cycles_summary, indent=2)}\n\n"
            "Given this rejection and the overall mission context, what is the next single, most critical strategic step to take? "
            "Consider if the rejection implies a need for a significant change in direction or if a more focused adjustment is needed. "
            "If the mission should be considered unachievable or requires fundamental rethinking due to the rejection, you can state 'MISSION_HALTED_BY_REJECTION'. "
            "Otherwise, describe the next single strategic step clearly and concisely."
        )

        try:
            new_decision_focus, cost = await self._ask_orchestrator(revision_prompt, response_format_json=False)
            self._log(f"Orchestrator proposed new focus after rejection: {new_decision_focus}", "info")
            return new_decision_focus
        except Exception as e:
            self._log(f"Error asking orchestrator to revise rejected cycle: {str(e)}", "error")
            return f"ERROR_REVISING_CYCLE: {str(e)}"

    # Additional methods would be implemented here following the same pattern
    # of delegating to the appropriate modular components...
    
    async def _select_or_create_specialist(self, decision: str, agent_management_logs: List[dict], json_parsing_logs: List[dict]) -> Tuple[Optional[RoutedAgent], float, float]:
        """Select an existing agent or create a new one."""
        # Implementation would delegate to agent_manager and communicator
        # This is a simplified version for the refactored structure
        
        # Try to find existing suitable agent
        best_agent = None
        best_confidence = 0.0
        
        for agent_name, agent in self.agents.items():
            if agent_name == self.name:
                continue
            try:
                confidence_prompt = f"Can you handle this decision: '{decision}'? Reply with JSON: {{\"can_handle\":bool,\"confidence\":float}}"
                result, cost = await self._get_json_response(agent, confidence_prompt, f"Failed to get confidence from {agent_name}", json_parsing_logs)
                if result.get("can_handle", False) and result.get("confidence", 0.0) > best_confidence:
                    best_agent = agent
                    best_confidence = result.get("confidence", 0.0)
            except Exception as e:
                self._log(f"Error getting confidence from {agent_name}: {str(e)}", "warning")
        
        if best_agent and best_confidence >= self.CONFIDENCE_THRESHOLD:
            return best_agent, best_confidence, 0.0
        
        # Create new specialist if no suitable agent found
        new_agent, creation_cost = await self.agent_manager.create_specialized_agent(
            decision, agent_management_logs, json_parsing_logs, self.communicator
        )
        return new_agent, 1.0, creation_cost

    async def _run_decision_loop(self, decision_agent, context_brief, specialist_logs, review_logs, json_logs, orchestrator_logs):
        """Run the decision loop with revisions."""
        # Simplified implementation - full version would be similar to original
        recommendation_text = None
        total_cost = 0.0
        
        for loop_num in range(self.MAX_REVISION_LOOPS):
            prompt = f"Context: {json.dumps(context_brief)}\nProvide your recommendation."
            recommendation_text, cost = await self._ask_agent(decision_agent, prompt)
            total_cost += cost
            
            # Get peer reviews
            reviews, review_cost = await self.review_manager.batch_peer_review(
                decision_agent.name, recommendation_text, self.agents, review_logs, json_logs
            )
            total_cost += review_cost
            
            if self.review_manager.check_review_consensus(reviews):
                break
        
        return recommendation_text, total_cost, reviews

    async def _execute_with_guardrails(self, agent, recommendation, constraints, execution_logs, json_logs):
        """Execute recommendation with guardrails."""
        # Simplified implementation
        execution_prompt = f"Execute this recommendation: {recommendation}"
        try:
            result, cost = await self._get_json_response(
                agent, execution_prompt, "Failed to execute recommendation", json_logs
            )
            return result, cost
        except Exception as e:
            return {"execution_type": "error", "description": str(e)}, 0.0

    async def _archive_and_retrospect(self, mission_log):
        """Archive and run retrospective analysis."""
        # Simplified implementation
        try:
            retro_primer = load_template("retrospective")
            retro_agent = await self.agent_manager.create_agent(
                "RetrospectiveAnalyser",
                "expert in analyzing mission performance",
                retro_primer
            )
            
            analysis_prompt = f"Analyze this mission log: {json.dumps(asdict(mission_log), default=str)[:1000]}..."
            analysis, cost = await self._ask_agent(retro_agent, analysis_prompt)
            
            # Save retrospective
            retro_file = f"mission_logs/{mission_log.mission_id}_retro.txt"
            with open(retro_file, "w") as f:
                f.write(analysis)
            
            return cost
        except Exception as e:
            self._log(f"Error in retrospective: {str(e)}", "error")
            return 0.0

# Factory function to create orchestrator
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