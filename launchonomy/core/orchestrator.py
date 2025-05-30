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

# Import our modular components
from ..registry import Registry
from ..agents.workflow.auto_provision_agent import AutoProvisionAgent
from ..agents.retrieval_agent import RetrievalAgent
from .mission_manager import MissionManager, MissionLog, CycleLog
from .communication import AgentCommunicator, ReviewManager, AgentCommunicationError
from .agent_manager import AgentManager, TemplateError, load_template
from .vector_memory import create_mission_memory, ChromaDBVectorMemory
from ..utils.memory_helper import MemoryHelper

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
        self.registry = Registry(orchestrator=self)
        self.mission_manager = MissionManager()
        self.communicator = AgentCommunicator()
        self.review_manager = ReviewManager(self.communicator)
        self.agent_manager = AgentManager(self.registry, client, self.log_callback)
        
        # Initialize memory system (will be set up per mission)
        self.mission_memory: Optional[ChromaDBVectorMemory] = None
        self.memory_helper: Optional[MemoryHelper] = None
        self.retrieval_agent: Optional[RetrievalAgent] = None
        self.current_mission_id: Optional[str] = None
        
        # Load and instantiate all registered agents at startup
        self.agent_manager.load_registered_agents()
        
        # Ensure AutoProvisionAgent is initialized correctly
        self.auto_provision_agent = AutoProvisionAgent(registry=self.registry, orchestrator=self, mission_context={})
        
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
            except (TypeError, ValueError, AttributeError) as e:
                message = f"Failed to convert log message to string: {e}"

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
        mission_log = self.mission_manager.create_or_load_mission(mission_name, overall_mission, resume_existing)
        
        # Initialize memory system for this mission
        self._initialize_mission_memory(mission_log.mission_id)
        
        return mission_log
    
    def _initialize_mission_memory(self, mission_id: str):
        """Initialize the memory system for a specific mission."""
        try:
            # Generate or use existing mission ID
            self.current_mission_id = mission_id
            
            # Get workspace path for ChromaDB storage if available
            chromadb_base_dir = None
            if self.current_mission_log and self.current_mission_log.workspace_path:
                # Store ChromaDB in the mission workspace
                chromadb_base_dir = os.path.join(self.current_mission_log.workspace_path, "memory", "chromadb")
                self._log(f"Using workspace directory for ChromaDB: {chromadb_base_dir}", "info")
            else:
                # Fallback to default directory
                chromadb_base_dir = os.path.expanduser("~/.chromadb_launchonomy")
                self._log(f"Using default directory for ChromaDB: {chromadb_base_dir}", "info")
            
            # Create mission-specific memory store
            self.mission_memory = create_mission_memory(mission_id, chromadb_base_dir)
            
            # Initialize memory helper
            self.memory_helper = MemoryHelper(self.mission_memory, mission_id)
            
            # Initialize retrieval agent
            self.retrieval_agent = RetrievalAgent(self.mission_memory)
            
            # Add retrieval agent to the agent manager's agents
            self.agent_manager.agents["RetrievalAgent"] = self.retrieval_agent
            
            self._log(f"Initialized memory system for mission: {mission_id}", "info")
            
        except Exception as e:
            self._log(f"Error initializing memory system: {str(e)}", "error")
            # Continue without memory system if initialization fails
            self.mission_memory = None
            self.memory_helper = None
            self.retrieval_agent = None

    def get_mission_context_for_agents(self) -> dict:
        return self.mission_manager.get_mission_context_for_agents()
    
    async def _log_workflow_step_to_memory(self, step_name: str, result: Any, status: str):
        """Log a workflow step result to the mission memory."""
        if not self.memory_helper:
            return  # Memory system not initialized
        
        try:
            # Create summary based on result type and status
            if status == "success":
                if hasattr(result, 'data') and isinstance(result.data, dict):
                    # Handle WorkflowOutput objects
                    summary = f"{step_name} completed successfully"
                    details = {
                        "status": result.status if hasattr(result, 'status') else "success",
                        "cost": result.cost if hasattr(result, 'cost') else 0.0,
                        "confidence": result.confidence if hasattr(result, 'confidence') else 1.0
                    }
                    
                    # Add key data points
                    if result.data:
                        for key, value in result.data.items():
                            if key in ["revenue", "opportunities", "deployment_summary", "performance", "metrics"]:
                                details[key] = str(value)[:200]  # Truncate long values
                                
                elif isinstance(result, dict):
                    summary = f"{step_name} completed successfully"
                    details = {k: str(v)[:200] for k, v in result.items() if k in ["status", "revenue", "cost", "performance"]}
                else:
                    summary = f"{step_name} completed successfully"
                    details = {"result": str(result)[:200]}
                
                # Log as workflow event
                self.memory_helper.log_workflow_event(step_name.lower(), summary, details)
                
            elif status == "failed":
                summary = f"{step_name} failed with error"
                details = result if isinstance(result, dict) else {"error": str(result)}
                
                # Log as error
                self.memory_helper.log_error_or_failure(step_name.lower(), summary, details)
                
        except Exception as e:
            self._log(f"Error logging to memory: {str(e)}", "warning")

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
        mission_id = f"{cycle_start_time.strftime('%Y%m%d_%H%M%S')}_cycle_{re.sub(r'\W+','_',current_decision_focus[:20])}"
        
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

            # Step 4: Execution with Guardrails
            self._log(f"Executing recommendation from {decision_agent_name_for_log}", "info")
            execution_output, execution_cost = await self._execute_with_guardrails(
                decision_agent,
                recommendation_text,
                {},  # constraints
                mission_log.execution_attempts,
                mission_log.json_parsing_attempts
            )
            mission_log.total_cycle_cost += execution_cost

            # Step 5: Final Review
            final_reviews_summary = review_details_from_loop

            mission_log.status = "success"
            self._log(f"Decision cycle for '{current_decision_focus[:50]}...' completed successfully", "info")

        except Exception as e:
            mission_log.status = "failed"
            mission_log.error_message = str(e)
            self._log(f"Decision cycle focused on '{current_decision_focus[:50]}...' failed: {str(e)}", "error")

        # Step 6: Archive and Retrospect
        self._log(f"Archiving cycle log and running retrospective for '{current_decision_focus[:50]}...'", "info")
        retro_cost = await self._archive_and_retrospect(mission_log)
        mission_log.total_cycle_cost += retro_cost

        # Calculate cycle duration
        cycle_end_time = datetime.now()
        mission_log.cycle_duration_minutes = (cycle_end_time - cycle_start_time).total_seconds() / 60.0

        self._log(f"Decision cycle for '{current_decision_focus[:50]}...' finished. Total cycle cost: {mission_log.total_cycle_cost:.4f}, Duration: {mission_log.cycle_duration_minutes:.2f} minutes", "info")

        # Save cycle log to workspace using Mission Workspace System
        success = self.mission_manager.save_cycle_log_to_workspace(mission_log)
        if success:
            self._log(f"Cycle log saved to workspace successfully", "info")
        else:
            self._log(f"Failed to save cycle log to workspace", "warning")
        
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
            "workspace_path": self.current_mission_log.workspace_path if self.current_mission_log else None
        }

    async def run_continuous_launch_growth_loop(self, mission_context: Dict[str, Any], max_iterations: int = 100) -> Dict[str, Any]:
        """
        Run the C-Suite orchestrated mission loop.
        
        This implements the Launchonomy approach:
        1. C-Suite strategic decision-making (CEO, CRO, CTO, CFO consensus)
        2. Workflow agents execute operational tasks when needed
        3. C-Suite reviews results and makes next strategic decisions
        4. Repeat until mission complete or max iterations reached
        
        Args:
            mission_context: Mission context including overall_mission and constraints
            max_iterations: Maximum number of iterations to run
            
        Returns:
            Dictionary with loop results and execution summary
        """
        self._log("Starting C-Suite orchestrated mission", "info")
        
        loop_results = {
            "mode": "continuous_launch_growth_with_csuite",
            "status": "running",
            "total_iterations": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "total_revenue_generated": 0.0,
            "guardrail_breaches": 0,
            "execution_log": [],
            "csuite_decisions": [],
            "final_status": "incomplete"
        }
        
        # Workflow agent sequence
        workflow_sequence = [
            "ScanAgent",
            "DeployAgent", 
            "CampaignAgent",
            "AnalyticsAgent",
            "FinanceAgent",
            "GrowthAgent"
        ]
        
        # C-Suite strategic agents for decision-making
        strategic_csuite = ["CEO-Agent", "CRO-Agent", "CTO-Agent", "CFO-Agent"]
        
        try:
            for iteration in range(max_iterations):
                # self._log(f"Starting iteration {iteration + 1}/{max_iterations}", "info")
                loop_results["total_iterations"] = iteration + 1
                
                cycle_log = {
                    "iteration": iteration + 1,
                    "timestamp": datetime.now().isoformat(),
                    "csuite_planning": {},
                    "steps": {},
                    "csuite_review": {},
                    "revenue_generated": 0.0,
                    "errors": [],
                    "guardrail_status": "OK"
                }
                
                cycle_successful = True
                
                # Phase 1: C-Suite Strategic Planning (if C-Suite agents are available)
                if iteration == 0 or loop_results["total_revenue_generated"] > 0:  # Plan on first iteration or when revenue changes
                    self._log("Phase 1: C-Suite strategic planning session...", "info")
                    csuite_planning = await self._conduct_csuite_planning(
                        strategic_csuite, mission_context, loop_results, cycle_log
                    )
                    cycle_log["csuite_planning"] = csuite_planning
                    loop_results["csuite_decisions"].append({
                        "iteration": iteration + 1,
                        "type": "planning",
                        "decisions": csuite_planning
                    })
                
                # Phase 2: Execute workflow agents in sequence
                self._log("Phase 2: Executing workflow agent sequence...", "info")
                for agent_name in workflow_sequence:
                    try:
                        # self._log(f"Executing {agent_name}...", "info")
                        
                        # Get agent from registry
                        agent = self.registry.get_agent(agent_name, mission_context)
                        if not agent:
                            error_msg = f"Failed to get {agent_name} from registry"
                            self._log(error_msg, "error")
                            cycle_log["errors"].append(error_msg)
                            cycle_successful = False
                            continue
                        
                        # Prepare input data based on agent type and C-Suite guidance
                        input_data = self._prepare_agent_input(agent_name, mission_context, cycle_log)
                        
                        # Add C-Suite strategic guidance to input
                        if cycle_log.get("csuite_planning"):
                            input_data["csuite_guidance"] = cycle_log["csuite_planning"]
                        
                        # Execute the agent
                        if hasattr(agent, 'execute'):
                            result = agent.execute(input_data)
                            # Handle async execution if needed
                            if hasattr(result, '__await__'):
                                result = await result
                        else:
                            error_msg = f"{agent_name} does not have execute method"
                            self._log(error_msg, "error")
                            cycle_log["errors"].append(error_msg)
                            cycle_successful = False
                            continue
                        
                        # Process result
                        cycle_log["steps"][agent_name] = {
                            "status": "success",
                            "result": result,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Log to memory system
                        await self._log_workflow_step_to_memory(agent_name, result, "success")
                        
                        # Extract revenue if available
                        if agent_name == "AnalyticsAgent":
                            # Handle WorkflowOutput object
                            if hasattr(result, 'data') and isinstance(result.data, dict):
                                revenue = result.data.get("revenue", 0.0)
                                if isinstance(revenue, (int, float)):
                                    cycle_log["revenue_generated"] += revenue
                                    loop_results["total_revenue_generated"] += revenue
                            elif isinstance(result, dict):
                                revenue = result.get("revenue", 0.0)
                                if isinstance(revenue, (int, float)):
                                    cycle_log["revenue_generated"] += revenue
                                    loop_results["total_revenue_generated"] += revenue
                        
                        # self._log(f"{agent_name} completed successfully", "info")
                        
                    except Exception as e:
                        error_msg = f"Error executing {agent_name}: {str(e)}"
                        self._log(error_msg, "error")
                        cycle_log["errors"].append(error_msg)
                        cycle_log["steps"][agent_name] = {
                            "status": "failed",
                            "error": str(e),
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Log error to memory system
                        await self._log_workflow_step_to_memory(agent_name, {"error": str(e)}, "failed")
                        
                        cycle_successful = False
                
                # Phase 3: C-Suite Review and Strategic Adjustment
                if len(cycle_log["steps"]) > 0:  # Only review if we executed some agents
                    self._log("Phase 3: C-Suite review and strategic adjustment...", "info")
                    csuite_review = await self._conduct_csuite_review(
                        strategic_csuite, cycle_log, loop_results
                    )
                    cycle_log["csuite_review"] = csuite_review
                    loop_results["csuite_decisions"].append({
                        "iteration": iteration + 1,
                        "type": "review",
                        "decisions": csuite_review
                    })
                    
                    # Apply C-Suite strategic adjustments
                    if csuite_review.get("strategic_adjustments"):
                        # self._log("Applying C-Suite strategic adjustments...", "info")
                        # Update mission context based on C-Suite feedback
                        mission_context.update(csuite_review.get("context_updates", {}))
                
                # Check financial guardrails with CFO oversight
                if cycle_log["revenue_generated"] > 0:
                    # Only run GrowthAgent if we have revenue and CFO approves
                    if "GrowthAgent" not in cycle_log["steps"] or cycle_log["steps"]["GrowthAgent"]["status"] != "success":
                        try:
                            self._log("Revenue detected, consulting CFO and executing GrowthAgent...", "info")
                            
                            # Get CFO approval for growth investment
                            cfo_approval = await self._get_cfo_growth_approval(cycle_log["revenue_generated"])
                            
                            if cfo_approval.get("approved", False):
                                growth_agent = self.registry.get_agent("GrowthAgent", mission_context)
                                if growth_agent and hasattr(growth_agent, 'execute'):
                                    growth_input = {
                                        "growth_phase": "scaling",
                                        "current_metrics": {"revenue": cycle_log["revenue_generated"]},
                                        "experiment_budget": cfo_approval.get("approved_budget", 100),
                                        "cfo_guidance": cfo_approval
                                    }
                                    growth_result = growth_agent.execute(growth_input)
                                    if hasattr(growth_result, '__await__'):
                                        growth_result = await growth_result
                                    
                                    cycle_log["steps"]["GrowthAgent"] = {
                                        "status": "success",
                                        "result": growth_result,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                    self._log("GrowthAgent completed successfully with CFO approval", "info")
                            else:
                                self._log("CFO declined growth investment for this cycle", "warning")
                                cycle_log["steps"]["GrowthAgent"] = {
                                    "status": "declined_by_cfo",
                                    "reason": cfo_approval.get("reason", "Budget constraints"),
                                    "timestamp": datetime.now().isoformat()
                                }
                        except Exception as e:
                            error_msg = f"Error executing GrowthAgent: {str(e)}"
                            self._log(error_msg, "error")
                            cycle_log["errors"].append(error_msg)
                
                # Update loop results
                if cycle_successful and len(cycle_log["errors"]) == 0:
                    loop_results["successful_cycles"] += 1
                else:
                    loop_results["failed_cycles"] += 1
                
                cycle_log["cycle_successful"] = cycle_successful
                loop_results["execution_log"].append(cycle_log)
                
                # Check if mission should continue (with C-Suite consensus)
                if loop_results["total_revenue_generated"] > 1000:  # Success threshold
                    # Get C-Suite consensus on mission completion
                    completion_consensus = await self._get_csuite_mission_completion_consensus(loop_results)
                    if completion_consensus.get("mission_complete", False):
                        loop_results["final_status"] = "success_csuite_consensus"
                        self._log("C-Suite consensus: Mission successfully completed!", "info")
                        break
                
                if loop_results["failed_cycles"] > 3:  # Too many failures
                    loop_results["final_status"] = "too_many_failures"
                    self._log("Too many failed cycles, stopping mission", "warning")
                    break
                
                # Brief pause between iterations
                await asyncio.sleep(1)
            
            if loop_results["final_status"] == "incomplete":
                loop_results["final_status"] = "max_iterations_reached"
            
            loop_results["status"] = "completed"
            self._log(f"Continuous loop with C-Suite oversight completed: {loop_results['successful_cycles']} successful, {loop_results['failed_cycles']} failed", "info")
            
        except Exception as e:
            loop_results["status"] = "failed"
            loop_results["final_status"] = "critical_error"
            loop_results["error"] = str(e)
            self._log(f"Critical error in continuous loop: {str(e)}", "error")
        
        return loop_results

    def _prepare_agent_input(self, agent_name: str, mission_context: Dict[str, Any], cycle_log: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input data for a specific workflow agent."""
        base_input = {
            "mission_context": mission_context,
            "cycle_context": cycle_log
        }
        
        if agent_name == "ScanAgent":
            return {
                **base_input,
                "focus_areas": ["saas", "automation", "ai"],
                "max_opportunities": 5
            }
        elif agent_name == "DeployAgent":
            # Get opportunity from ScanAgent if available
            scan_step = cycle_log.get("steps", {}).get("ScanAgent", {})
            scan_result = scan_step.get("result", {})
            
            # Handle WorkflowOutput object
            if hasattr(scan_result, 'data') and isinstance(scan_result.data, dict):
                opportunities = scan_result.data.get("opportunities", [])
            elif isinstance(scan_result, dict):
                opportunities = scan_result.get("opportunities", [])
            else:
                opportunities = []
            
            selected_opportunity = opportunities[0] if opportunities else {"name": "Default SaaS Product", "type": "web_application"}
            
            return {
                **base_input,
                "opportunity": selected_opportunity,
                "requirements": {},
                "budget_limit": 500
            }
        elif agent_name == "CampaignAgent":
            # Get product details from DeployAgent if available
            deploy_step = cycle_log.get("steps", {}).get("DeployAgent", {})
            deploy_result = deploy_step.get("result", {})
            
            # Handle WorkflowOutput object
            if hasattr(deploy_result, 'data') and isinstance(deploy_result.data, dict):
                product_details = deploy_result.data.get("product_details", {"name": "Default Product"})
            elif isinstance(deploy_result, dict):
                product_details = deploy_result.get("product_details", {"name": "Default Product"})
            else:
                product_details = {"name": "Default Product"}
            
            return {
                **base_input,
                "campaign_type": "launch",
                "product_details": product_details,
                "budget_allocation": {"total_budget": 200}
            }
        elif agent_name == "AnalyticsAgent":
            return {
                **base_input,
                "analysis_type": "comprehensive",
                "time_period": "current_month",
                "specific_metrics": ["revenue", "users", "conversion_rate"]
            }
        elif agent_name == "FinanceAgent":
            return {
                **base_input,
                "operation_type": "marketing_campaign",
                "estimated_cost": 100.0,
                "time_period": "monthly"
            }
        elif agent_name == "GrowthAgent":
            return {
                **base_input,
                "growth_phase": "early",
                "current_metrics": {},
                "experiment_budget": 100
            }
        else:
            return base_input

    async def execute_continuous_mode(self, mission_context: Dict[str, Any], max_iterations: int = 10) -> Dict[str, Any]:
        """Execute continuous mode - wrapper for run_continuous_launch_growth_loop."""
        return await self.run_continuous_launch_growth_loop(mission_context, max_iterations)

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
            
            # Save retrospective to workspace
            if self.current_mission_log and self.current_mission_log.workspace_path:
                # Save to workspace docs/generated directory
                docs_dir = os.path.join(self.current_mission_log.workspace_path, "docs", "generated")
                os.makedirs(docs_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                retro_file = os.path.join(docs_dir, f"{timestamp}_retrospective_analysis.txt")
                with open(retro_file, "w") as f:
                    f.write(analysis)
                
                # Also save as an asset
                self.mission_manager.save_mission_asset(
                    asset_name=f"{timestamp}_retrospective_analysis.txt",
                    asset_data=analysis,
                    asset_type="retrospective",
                    category="docs"
                )
            else:
                # Save to workspace docs/generated directory
                if hasattr(mission_log, 'workspace_path') and mission_log.workspace_path:
                    retro_file = f"{mission_log.workspace_path}/docs/generated/{mission_log.mission_id}_retro.txt"
                    os.makedirs(os.path.dirname(retro_file), exist_ok=True)
                    with open(retro_file, "w") as f:
                        f.write(analysis)
                else:
                    self._log("Warning: No workspace available for retrospective analysis", "warning")
            
            return cost
        except Exception as e:
            self._log(f"Error in retrospective: {str(e)}", "error")
            return 0.0

    async def _conduct_csuite_planning(self, strategic_csuite: List[str], mission_context: Dict[str, Any], 
                                     loop_results: Dict[str, Any], cycle_log: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct C-Suite strategic planning session."""
        iteration = cycle_log.get("iteration", 1)
        # self._log(f"🏛️ C-Suite strategic planning session starting for iteration {iteration}...", "info")
        
        planning_results = {
            "strategic_focus": "customer_acquisition",
            "budget_allocation": {"marketing": 200, "development": 150, "operations": 100},
            "key_decisions": [],
            "consensus_reached": True,
            "next_actions": []
        }
        
        try:
            # Get available C-Suite agents
            available_csuite = []
            for agent_name in strategic_csuite:
                if agent_name in self.agents:
                    available_csuite.append(agent_name)
            
            if not available_csuite:
                self._log("⚠️ No C-Suite agents available for planning - proceeding with default strategy", "warning")
                return planning_results
            
            # self._log(f"📋 C-Suite planning participants: {', '.join(available_csuite)}", "info")
            
            # Conduct planning with available C-Suite agents
            planning_context = {
                "mission": mission_context.get("overall_mission", ""),
                "current_iteration": cycle_log.get("iteration", 1),
                "previous_revenue": loop_results.get("total_revenue_generated", 0.0),
                "previous_cycles": len(loop_results.get("execution_log", []))
            }
            
            # Get strategic input from each C-Suite agent
            for agent_name in available_csuite[:3]:  # Limit to 3 agents to avoid too many calls
                try:
                    self._log(f"🎯 Consulting {agent_name} for strategic input...", "info")
                    agent = self.agents[agent_name]
                    planning_prompt = f"""
                    Mission Context: {json.dumps(planning_context, indent=2)}
                    
                    As {agent_name}, provide your strategic input for this iteration:
                    1. What should be our primary focus this cycle?
                    2. How should we allocate our budget?
                    3. What are the key risks and opportunities?
                    
                    Respond with JSON: {{"focus": "...", "budget_recommendation": {{}}, "risks": [], "opportunities": []}}
                    """
                    
                    response, cost = await self._ask_agent(agent, planning_prompt, response_format_json=False)
                    
                    # Parse response and add to planning results - handle both JSON and natural language
                    try:
                        # Try to parse as JSON first
                        agent_input = json.loads(response)
                        focus = agent_input.get("focus", "general_strategy")
                        self._log(f"💡 {agent_name} recommends focus: {focus}", "info")
                        
                        # Log budget recommendations
                        budget_rec = agent_input.get("budget_recommendation", {})
                        if budget_rec:
                            budget_summary = ", ".join([f"{k}: ${v}" for k, v in budget_rec.items()])
                            self._log(f"💰 {agent_name} budget allocation: {budget_summary}", "info")
                        
                        # Log key risks and opportunities
                        risks = agent_input.get("risks", [])
                        if risks:
                            self._log(f"⚠️ {agent_name} identifies risks: {', '.join(risks[:2])}", "info")
                        
                        opportunities = agent_input.get("opportunities", [])
                        if opportunities:
                            self._log(f"🚀 {agent_name} sees opportunities: {', '.join(opportunities[:2])}", "info")
                        
                        planning_results["key_decisions"].append({
                            "agent": agent_name,
                            "input": agent_input
                        })
                    except json.JSONDecodeError:
                        # If JSON parsing fails, create structured data from natural language response
                        self._log(f"Converting natural language response from {agent_name} to structured format", "debug")
                        agent_input = {
                            "focus": "customer_acquisition" if "customer" in response.lower() else "product_development",
                            "budget_recommendation": {"marketing": 150, "development": 100, "operations": 50},
                            "risks": ["market_competition", "budget_constraints"],
                            "opportunities": ["ai_automation", "saas_growth"],
                            "raw_response": response[:200] + "..." if len(response) > 200 else response
                        }
                        
                        # Log the interpreted decision
                        self._log(f"💡 {agent_name} recommends focus: {agent_input['focus']} (interpreted)", "info")
                        
                        planning_results["key_decisions"].append({
                            "agent": agent_name,
                            "input": agent_input
                        })
                        
                except Exception as e:
                    self._log(f"Error getting input from {agent_name}: {str(e)}", "warning")
            
            # Synthesize C-Suite consensus
            if planning_results["key_decisions"]:
                planning_results["consensus_reached"] = True
                
                # Determine primary strategic focus from C-Suite input
                focus_votes = {}
                for decision in planning_results["key_decisions"]:
                    focus = decision["input"].get("focus", "general_strategy")
                    focus_votes[focus] = focus_votes.get(focus, 0) + 1
                
                if focus_votes:
                    primary_focus = max(focus_votes, key=focus_votes.get)
                    planning_results["strategic_focus"] = primary_focus
                    self._log(f"🎯 C-Suite consensus: Primary focus is '{primary_focus}'", "info")
                
                # Generate specific next actions based on focus
                if primary_focus == "customer_acquisition":
                    planning_results["next_actions"] = [
                        "Execute ScanAgent to identify high-conversion opportunities",
                        "Deploy customer acquisition campaigns via CampaignAgent",
                        "Monitor conversion metrics and customer feedback"
                    ]
                elif primary_focus == "product_development":
                    planning_results["next_actions"] = [
                        "Execute DeployAgent for rapid MVP development",
                        "Implement A/B testing for product features",
                        "Gather user feedback and iterate quickly"
                    ]
                elif primary_focus == "growth_acceleration":
                    planning_results["next_actions"] = [
                        "Execute GrowthAgent for viral growth experiments",
                        "Scale successful marketing channels",
                        "Optimize conversion funnels and retention"
                    ]
                else:
                    planning_results["next_actions"] = [
                        "Execute workflow agents based on strategic focus",
                        "Monitor budget utilization and ROI",
                        "Track key performance indicators"
                    ]
                
                # Log the planned next actions
                self._log(f"📋 Next actions planned:", "info")
                for i, action in enumerate(planning_results["next_actions"], 1):
                    self._log(f"   {i}. {action}", "info")
            else:
                self._log("⚠️ No C-Suite decisions received - using default strategy", "warning")
            
        except Exception as e:
            self._log(f"Error in C-Suite planning: {str(e)}", "error")
            planning_results["consensus_reached"] = False
        
        return planning_results

    async def _conduct_csuite_review(self, strategic_csuite: List[str], cycle_log: Dict[str, Any], 
                                   loop_results: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct C-Suite review of cycle results."""
        iteration = cycle_log.get("iteration", 1)
        revenue = cycle_log.get("revenue_generated", 0.0)
        # self._log(f"📊 C-Suite review session starting for iteration {iteration} (Revenue: ${revenue:.2f})...", "info")
        
        review_results = {
            "overall_assessment": "satisfactory",
            "strategic_adjustments": [],
            "budget_status": "on_track",
            "next_iteration_focus": "continue_current_strategy",
            "context_updates": {}
        }
        
        try:
            # Get available C-Suite agents
            available_csuite = []
            for agent_name in strategic_csuite:
                if agent_name in self.agents:
                    available_csuite.append(agent_name)
            
            if not available_csuite:
                self._log("⚠️ No C-Suite agents available for review - using default assessment", "warning")
                return review_results
            
            # self._log(f"👥 C-Suite review participants: {', '.join(available_csuite)}", "info")
            
            # Review context
            review_context = {
                "cycle_results": {
                    "revenue_generated": cycle_log.get("revenue_generated", 0.0),
                    "agents_executed": list(cycle_log.get("steps", {}).keys()),
                    "errors": cycle_log.get("errors", []),
                    "successful": cycle_log.get("cycle_successful", False)
                },
                "cumulative_results": {
                    "total_revenue": loop_results.get("total_revenue_generated", 0.0),
                    "successful_cycles": loop_results.get("successful_cycles", 0),
                    "failed_cycles": loop_results.get("failed_cycles", 0)
                }
            }
            
            # Log cycle performance summary - calculate success based on current state
            agents_executed = list(cycle_log.get("steps", {}).keys())
            errors = cycle_log.get("errors", [])
            
            # Calculate success: all agents executed successfully and no errors
            successful_steps = sum(1 for step in cycle_log.get("steps", {}).values() 
                                 if step.get("status") == "success")
            total_expected_agents = len(["ScanAgent", "DeployAgent", "CampaignAgent", "AnalyticsAgent", "FinanceAgent", "GrowthAgent"])
            cycle_success = (successful_steps >= total_expected_agents and len(errors) == 0)
            
            self._log(f"📈 Cycle Performance Summary:", "info")
            self._log(f"   • Success: {'✅' if cycle_success else '❌'}", "info")
            self._log(f"   • Agents executed: {len(agents_executed)}", "info")
            if errors:
                self._log(f"   • Errors encountered: {len(errors)}", "warning")
                for i, error in enumerate(errors[:3]):  # Show first 3 errors
                    self._log(f"     {i+1}. {error}", "warning")
                if len(errors) > 3:
                    self._log(f"     ... and {len(errors) - 3} more errors", "warning")
            # else:
            #     self._log(f"   • No errors encountered", "info")
            
            # Get review input from key C-Suite agents
            for agent_name in available_csuite[:2]:  # Limit to 2 agents for review
                try:
                    # self._log(f"🔍 Getting performance review from {agent_name}...", "info")
                    agent = self.agents[agent_name]
                    review_prompt = f"""
                    Cycle Results: {json.dumps(review_context, indent=2)}
                    
                    As {agent_name}, review this cycle's performance:
                    1. How do you assess this cycle's results?
                    2. What strategic adjustments should we make?
                    3. What should be our focus for the next iteration?
                    
                    Respond with JSON: {{"assessment": "...", "adjustments": [], "next_focus": "..."}}
                    """
                    
                    response, cost = await self._ask_agent(agent, review_prompt, response_format_json=False)
                    
                    # Parse response and incorporate into review - handle both JSON and natural language
                    try:
                        # Try to parse as JSON first
                        agent_review = json.loads(response)
                        
                        # Log the agent's assessment
                        assessment = agent_review.get("assessment", "no assessment provided")
                        self._log(f"📝 {agent_name} assessment: {assessment}", "info")
                        
                        # Log strategic adjustments
                        adjustments = agent_review.get("adjustments", [])
                        if adjustments:
                            self._log(f"🔧 {agent_name} recommends adjustments:", "info")
                            for adj in adjustments[:2]:  # Limit to first 2 adjustments
                                self._log(f"   • {adj}", "info")
                            review_results["strategic_adjustments"].extend(adjustments)
                        
                        # Log next focus recommendation
                        next_focus = agent_review.get("next_focus", "")
                        if next_focus:
                            self._log(f"🎯 {agent_name} recommends next focus: {next_focus}", "info")
                            review_results["next_iteration_focus"] = next_focus
                            
                    except json.JSONDecodeError:
                        # If JSON parsing fails, extract insights from natural language response
                        self._log(f"Converting natural language review from {agent_name} to structured format", "debug")
                        
                        # Extract key insights from natural language
                        if "adjust" in response.lower() or "change" in response.lower():
                            adjustment = f"{agent_name}: {response[:100]}..."
                            review_results["strategic_adjustments"].append(adjustment)
                            self._log(f"🔧 {agent_name} suggests adjustment (interpreted)", "info")
                        
                        if "focus" in response.lower():
                            if "marketing" in response.lower():
                                review_results["next_iteration_focus"] = "marketing_optimization"
                                self._log(f"🎯 {agent_name} recommends focus: marketing_optimization (interpreted)", "info")
                            elif "product" in response.lower():
                                review_results["next_iteration_focus"] = "product_development"
                                self._log(f"🎯 {agent_name} recommends focus: product_development (interpreted)", "info")
                            elif "growth" in response.lower():
                                review_results["next_iteration_focus"] = "growth_acceleration"
                                self._log(f"🎯 {agent_name} recommends focus: growth_acceleration (interpreted)", "info")
                        
                        # Store raw response for reference
                        review_results[f"{agent_name}_raw_review"] = response[:200] + "..." if len(response) > 200 else response
                        
                except Exception as e:
                    self._log(f"Error getting review from {agent_name}: {str(e)}", "warning")
            
        except Exception as e:
            self._log(f"Error in C-Suite review: {str(e)}", "error")
        
        # Log review summary
        self._log(f"📋 C-Suite Review Summary:", "info")
        self._log(f"   • Overall assessment: {review_results['overall_assessment']}", "info")
        self._log(f"   • Next iteration focus: {review_results['next_iteration_focus']}", "info")
        if review_results["strategic_adjustments"]:
            self._log(f"   • Strategic adjustments: {len(review_results['strategic_adjustments'])} recommended", "info")
        else:
            self._log(f"   • Strategic adjustments: None recommended", "info")
        
        return review_results

    async def _get_cfo_growth_approval(self, revenue_generated: float) -> Dict[str, Any]:
        """Get CFO approval for growth investment."""
        self._log(f"💰 Requesting CFO approval for growth investment (Current revenue: ${revenue_generated:.2f})...", "info")
        
        approval_result = {
            "approved": False,
            "approved_budget": 0.0,
            "reason": "CFO not available"
        }
        
        try:
            if "CFO-Agent" in self.agents:
                self._log(f"🏦 Consulting CFO-Agent for growth investment approval...", "info")
                cfo_agent = self.agents["CFO-Agent"]
                
                approval_prompt = f"""
                Current revenue generated: ${revenue_generated:.2f}
                
                As CFO-Agent, should we approve growth investment for this cycle?
                Consider our profit guardrail: total costs never exceed 20% of revenue.
                
                Respond with JSON: {{"approved": true/false, "budget": amount, "reason": "explanation"}}
                """
                
                response, cost = await self._ask_agent(cfo_agent, approval_prompt, response_format_json=False)
                
                try:
                    # Try to parse as JSON first
                    cfo_decision = json.loads(response)
                    approved = cfo_decision.get("approved", False)
                    budget = cfo_decision.get("budget", 0.0)
                    reason = cfo_decision.get("reason", "CFO decision")
                    
                    self._log(f"💼 CFO Decision: {'APPROVED' if approved else 'DENIED'} - Budget: ${budget:.2f}", "info")
                    self._log(f"💭 CFO Reasoning: {reason[:100]}...", "info")
                    
                    approval_result = {
                        "approved": approved,
                        "approved_budget": budget,
                        "reason": reason
                    }
                except json.JSONDecodeError:
                    # If JSON parsing fails, interpret natural language response
                    self._log("Converting natural language CFO response to structured format", "debug")
                    
                    # Simple natural language interpretation
                    response_lower = response.lower()
                    if any(word in response_lower for word in ["yes", "approve", "approved", "go ahead", "proceed"]):
                        max_budget = revenue_generated * 0.15  # Conservative 15% of revenue
                        budget = min(100, max_budget)
                        self._log(f"💼 CFO Decision: APPROVED (interpreted) - Budget: ${budget:.2f}", "info")
                        approval_result = {
                            "approved": True,
                            "approved_budget": budget,
                            "reason": f"CFO approved based on natural language response: {response[:100]}..."
                        }
                    else:
                        self._log(f"💼 CFO Decision: DENIED (interpreted)", "info")
                        approval_result = {
                            "approved": False,
                            "approved_budget": 0.0,
                            "reason": f"CFO declined based on natural language response: {response[:100]}..."
                        }
            else:
                # Default approval logic if CFO not available
                self._log(f"🤖 CFO-Agent not available - using automatic approval logic", "info")
                max_budget = revenue_generated * 0.2  # 20% of revenue
                if max_budget > 50:  # Minimum threshold
                    budget = min(100, max_budget)
                    self._log(f"💼 Automatic Decision: APPROVED - Budget: ${budget:.2f} (based on revenue threshold)", "info")
                    approval_result = {
                        "approved": True,
                        "approved_budget": budget,
                        "reason": "Automatic approval based on revenue threshold"
                    }
                else:
                    self._log(f"💼 Automatic Decision: DENIED - Insufficient revenue (${revenue_generated:.2f})", "info")
                
        except Exception as e:
            self._log(f"Error getting CFO approval: {str(e)}", "error")
        
        # Log final approval summary
        if approval_result["approved"]:
            self._log(f"✅ Growth investment APPROVED: ${approval_result['approved_budget']:.2f}", "info")
        else:
            self._log(f"❌ Growth investment DENIED: {approval_result['reason']}", "info")
        
        return approval_result

    async def _get_csuite_mission_completion_consensus(self, loop_results: Dict[str, Any]) -> Dict[str, Any]:
        """Get C-Suite consensus on mission completion."""
        total_revenue = loop_results.get("total_revenue_generated", 0.0)
        successful_cycles = loop_results.get("successful_cycles", 0)
        self._log(f"🏁 Requesting C-Suite consensus on mission completion (Revenue: ${total_revenue:.2f}, Successful cycles: {successful_cycles})...", "info")
        
        consensus_result = {
            "mission_complete": False,
            "consensus_reached": False,
            "reasoning": "Insufficient progress"
        }
        
        try:
            # Check if we have significant progress
            if total_revenue > 1000 and successful_cycles >= 3:
                self._log(f"📊 Mission progress meets completion criteria - consulting C-Suite...", "info")
                # Get C-Suite input on completion
                available_csuite = ["CEO-Agent", "CRO-Agent", "CFO-Agent"]
                completion_votes = []
                
                for agent_name in available_csuite:
                    if agent_name in self.agents:
                        try:
                            self._log(f"🗳️ Getting mission completion vote from {agent_name}...", "info")
                            agent = self.agents[agent_name]
                            completion_prompt = f"""
                            Mission Progress:
                            - Total Revenue: ${total_revenue:.2f}
                            - Successful Cycles: {successful_cycles}
                            - Total Iterations: {loop_results.get('total_iterations', 0)}
                            
                            As {agent_name}, do you believe our mission is complete?
                            Consider: Have we achieved sustainable, profitable growth?
                            
                            Respond with JSON: {{"mission_complete": true/false, "reasoning": "explanation"}}
                            """
                            
                            response, cost = await self._ask_agent(agent, completion_prompt, response_format_json=False)
                            
                            try:
                                # Try to parse as JSON first
                                vote = json.loads(response)
                                vote_result = vote.get("mission_complete", False)
                                reasoning = vote.get("reasoning", "No reasoning provided")
                                self._log(f"✅ {agent_name} votes: {'COMPLETE' if vote_result else 'CONTINUE'} - {reasoning[:50]}...", "info")
                                completion_votes.append(vote_result)
                            except json.JSONDecodeError:
                                # If JSON parsing fails, interpret natural language response
                                response_lower = response.lower()
                                if any(word in response_lower for word in ["yes", "complete", "finished", "achieved", "success"]):
                                    self._log(f"✅ {agent_name} votes: COMPLETE (interpreted from natural language)", "info")
                                    completion_votes.append(True)
                                else:
                                    self._log(f"🔄 {agent_name} votes: CONTINUE (interpreted from natural language)", "info")
                                    completion_votes.append(False)
                                
                        except Exception as e:
                            self._log(f"Error getting completion vote from {agent_name}: {str(e)}", "warning")
                            completion_votes.append(False)
                
                # Require unanimous consensus
                if completion_votes and all(completion_votes):
                    self._log(f"🎉 Unanimous C-Suite consensus: Mission is COMPLETE!", "info")
                    consensus_result = {
                        "mission_complete": True,
                        "consensus_reached": True,
                        "reasoning": "Unanimous C-Suite consensus: Mission objectives achieved"
                    }
                elif completion_votes:
                    complete_votes = sum(completion_votes)
                    total_votes = len(completion_votes)
                    self._log(f"🔄 C-Suite consensus: {complete_votes}/{total_votes} vote to complete - mission continues", "info")
                else:
                    self._log(f"⚠️ No C-Suite votes received - mission continues by default", "warning")
            else:
                self._log(f"📊 Mission progress insufficient for completion (Revenue: ${total_revenue:.2f}, Cycles: {successful_cycles})", "info")
                
        except Exception as e:
            self._log(f"Error getting mission completion consensus: {str(e)}", "error")
        
        return consensus_result

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