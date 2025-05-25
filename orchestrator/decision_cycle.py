import logging
from typing import Dict, List, Optional, Any, Tuple
from autogen_core import RoutedAgent

# Assuming agent_comm.py, agent_manager.py, review.py, execution.py contain necessary functions
# These will be placeholders for now and resolved later
from .agent_comm import _get_json_response, _ask_orchestrator, AgentCommunicationError # placeholder
from .agent_manager import _select_or_create_specialist # placeholder
from .review import _batch_peer_review # placeholder
from .execution import _execute_with_guardrails # placeholder

logger = logging.getLogger(__name__)

async def execute_decision_cycle(orchestrator_agent: Any, current_decision_focus: str, mission_context: dict) -> dict:
    """Orchestrates a single decision cycle."""
    # Initialize local logs for this cycle
    specialist_interaction_logs: List[dict] = []
    review_interaction_logs: List[dict] = []
    json_parsing_logs: List[dict] = [] # Centralized JSON parsing log
    orchestrator_interaction_logs: List[dict] = []
    agent_management_logs: List[dict] = []
    execution_attempts_log: List[dict] = []
    
    total_cycle_cost = 0.0
    
    orchestrator_agent._log(f"Starting decision cycle: {current_decision_focus}", "info")
    orchestrator_interaction_logs.append({"timestamp": orchestrator_agent._get_timestamp(), "event": "decision_cycle_start", "focus": current_decision_focus, "context": mission_context})

    try:
        # 1. Select or Create Specialist Agent
        orchestrator_agent._log(f"Selecting/creating specialist for: {current_decision_focus}", "info")
        decision_agent, confidence, agent_creation_cost = await _select_or_create_specialist(
            orchestrator_agent, # Pass orchestrator_agent
            current_decision_focus,
            agent_management_logs, 
            json_parsing_logs
        )
        total_cycle_cost += agent_creation_cost
        orchestrator_agent._log(f"Specialist '{decision_agent.name}' selected/created with confidence {confidence:.2f}. Cost: ${agent_creation_cost:.4f}", "info")
        agent_management_logs.append({"timestamp": orchestrator_agent._get_timestamp(), "event": "specialist_selected_created", "agent_name": decision_agent.name, "decision_focus": current_decision_focus, "confidence": confidence, "cost": agent_creation_cost})

        # 2. Run Decision Loop with Specialist
        context_brief = {"overall_mission": mission_context.get("overall_mission"), "current_decision_focus": current_decision_focus}
        orchestrator_agent._log(f"Running decision loop with {decision_agent.name}", "info")
        
        recommendation_text, decision_loop_cost, raw_reviews = await _run_decision_loop(
            orchestrator_agent, # Pass orchestrator_agent
            decision_agent, 
            context_brief, 
            specialist_interaction_logs, 
            review_interaction_logs, 
            json_parsing_logs,
            orchestrator_interaction_logs
        )
        total_cycle_cost += decision_loop_cost
        orchestrator_agent._log(f"Decision loop completed. Recommendation: '{recommendation_text[:100]}...'. Cost: ${decision_loop_cost:.4f}", "info")

        # 3. Execute Recommendation with Guardrails
        orchestrator_agent._log(f"Executing recommendation from {decision_agent.name}", "info")
        execution_output, execution_cost = await _execute_with_guardrails(
            orchestrator_agent, # Pass orchestrator_agent
            decision_agent, 
            recommendation_text, 
            {}, # Empty constraints for now
            execution_attempts_log, 
            json_parsing_logs
        )
        total_cycle_cost += execution_cost
        orchestrator_agent._log(f"Execution completed. Output: {execution_output}. Cost: ${execution_cost:.4f}", "info")
        
        status = "completed"
        error_message = None

    except AgentCommunicationError as e:
        orchestrator_agent._log(f"Agent communication error in decision cycle: {str(e)}", "error")
        status = "error"
        error_message = f"AgentCommunicationError: {str(e)}"
        # execution_output might not be defined here, ensure it has a default
        execution_output = {"error": str(e)}
        recommendation_text = "Error in communication, no recommendation."
        raw_reviews = [] # Ensure it has a default

    except Exception as e:
        orchestrator_agent._log(f"Unexpected error in decision cycle: {str(e)}", "error")
        status = "error"
        error_message = f"UnexpectedError: {str(e)}"
        execution_output = {"error": str(e)}
        recommendation_text = "Error in processing, no recommendation."
        raw_reviews = [] # Ensure it has a default

    # Construct and return the cycle log (subset of MissionLog for this cycle)
    cycle_result = {
        "decision_focus": current_decision_focus,
        "status": status,
        "recommendation": recommendation_text,
        "execution_result": execution_output,
        "reviews": raw_reviews, # Actual review objects/dicts
        "cost": total_cycle_cost,
        "error_message": error_message,
        "logs": {
            "agent_management": agent_management_logs,
            "orchestrator_interactions": orchestrator_interaction_logs,
            "specialist_interactions": specialist_interaction_logs,
            "review_interactions": review_interaction_logs,
            "execution_attempts": execution_attempts_log,
            "json_parsing": json_parsing_logs
        }
    }
    orchestrator_agent._log(f"Decision cycle for '{current_decision_focus}' finished with status: {status}. Total cost: ${total_cycle_cost:.4f}", "info")
    orchestrator_interaction_logs.append({"timestamp": orchestrator_agent._get_timestamp(), "event": "decision_cycle_end", "focus": current_decision_focus, "status": status, "cost": total_cycle_cost})
    return cycle_result

async def determine_next_strategic_step(orchestrator_agent: Any, overall_mission: str, previous_cycles_summary: List[Dict]) -> str:
    """Determines the next strategic step or if the mission is complete."""
    orchestrator_agent._log("Determining next strategic step...", "info")
    
    # Prepare a summary of previous cycles for the orchestrator
    if not previous_cycles_summary:
        history_summary = "This is the first decision cycle."
    else:
        history_summary = "Summary of previous decision cycles:\n"
        for i, cycle in enumerate(previous_cycles_summary):
            history_summary += f"{i+1}. Focus: {cycle.get('decision_focus', 'N/A')}, Status: {cycle.get('status', 'N/A')}, Recommendation: {cycle.get('recommendation', 'N/A')[:100]}...\n"

    prompt = (
        f"Given the overall mission: '{overall_mission}'\n"
        f"And the history of previous decision cycles:\n{history_summary}\n\n"
        f"Based on this information, what is the single most critical next decision to focus on to advance the mission? "
        f"If you believe the mission is complete based on the history, respond with 'MISSION_COMPLETE'. "
        f"Otherwise, state the next decision focus clearly and concisely. For example: 'Develop marketing strategy' or 'Analyze competitor X pricing'."
    )
    
    try:
        # Using _ask_orchestrator which is now in agent_comm module
        # We assume orchestrator_agent has _ask_orchestrator method or it's passed correctly
        response_text, cost = await _ask_orchestrator(orchestrator_agent, orchestrator_agent, prompt, orchestrator_agent.log_callback, response_format_json=False) # Pass self as agent
        orchestrator_agent._log(f"Orchestrator decision for next step: '{response_text}'. Cost: ${cost:.4f}", "info")
        # Record this interaction in the current mission log if it exists, or handle appropriately
        # This cost should be tracked as part of the ongoing mission, not a specific cycle.
        # For now, we log it here and assume it gets aggregated.
        return response_text.strip()
    except AgentCommunicationError as e:
        orchestrator_agent._log(f"Error determining next step: {e}", "error")
        # Fallback strategy: could be to retry, or halt, or ask user.
        # For now, we'll indicate a need for review or manual intervention.
        return "ERROR_DETERMINING_NEXT_STEP_CHECK_LOGS"

async def revise_rejected_cycle(
    orchestrator_agent: Any, 
    rejected_decision_focus: str, 
    rejected_recommendation: Optional[str],
    rejected_execution_result: Optional[dict], 
    rejection_reason: str, 
    mission_context: dict # Contains overall_mission
) -> dict: # Returns a cycle-like result for CLI
    orchestrator_agent._log(f"Revising rejected cycle for: {rejected_decision_focus}. Reason: {rejection_reason}", "info")
    # This is a simplified revision. A more complex one might involve new agent selection or different loops.
    
    # For now, we'll treat this as a new decision cycle with the revision context.
    # The current_decision_focus becomes about revising the previous one.
    revised_decision_focus = f"Revise rejected decision: {rejected_decision_focus} due to '{rejection_reason}'"
    
    # Augment mission_context with rejection details for the new cycle
    augmented_mission_context = mission_context.copy()
    augmented_mission_context["revision_details"] = {
        "original_focus": rejected_decision_focus,
        "rejected_recommendation": rejected_recommendation,
        "rejected_execution_result": rejected_execution_result,
        "rejection_reason": rejection_reason
    }
    if orchestrator_agent.last_revision_plan: # from previous attempt
        augmented_mission_context["previous_revision_plan"] = orchestrator_agent.last_revision_plan
        orchestrator_agent._log(f"Carrying over previous revision plan: {orchestrator_agent.last_revision_plan}", "debug")

    # Create a prompt for the Orchestrator itself to generate a revision plan
    # This is meta-work: the orchestrator is deciding how to approach the revision.
    plan_prompt = (
        f"The previous decision cycle for '{rejected_decision_focus}' was rejected. "
        f"Reason: '{rejection_reason}'."
    )
    if rejected_recommendation:
        plan_prompt += f" The rejected recommendation was: '{rejected_recommendation[:200]}...'."
    if rejected_execution_result:
        plan_prompt += f" The result of its attempted execution was: '{str(rejected_execution_result)[:200]}...'."
    if augmented_mission_context.get("previous_revision_plan"):
        plan_prompt += f" A previous attempt to revise this failed with the plan: '{augmented_mission_context['previous_revision_plan']}'. Avoid repeating this failed approach."
    
    plan_prompt += (
        f"\n\nYour task is to create a concise plan to address this rejection. This plan will guide the next decision cycle. "
        f"Focus on what needs to be done differently. For example: 'Re-evaluate data sources and consult legal expert before re-submitting recommendation for {rejected_decision_focus}'. "
        f"The output should be a single string representing this revision plan."
    )

    orchestrator_agent._log("Asking Orchestrator for a revision plan...", "info")
    try:
        revision_plan_text, plan_cost = await _ask_orchestrator(orchestrator_agent, orchestrator_agent, plan_prompt, orchestrator_agent.log_callback, response_format_json=False)
        orchestrator_agent._log(f"Orchestrator revision plan: '{revision_plan_text}'. Cost: ${plan_cost:.4f}", "info")
        orchestrator_agent.last_revision_plan = revision_plan_text # Store for future revisions if this one also fails
        # This cost should be added to the mission log or current cycle costs
    except AgentCommunicationError as e:
        orchestrator_agent._log(f"Failed to get revision plan from orchestrator: {e}", "error")
        return {
            "decision_focus": revised_decision_focus,
            "status": "error",
            "recommendation": "Failed to generate revision plan.",
            "execution_result": None,
            "reviews": [],
            "cost": 0, # Or include cost incurred so far
            "error_message": f"AgentCommunicationError: {str(e)}",
            "logs": {}
        }

    # The new "decision focus" is the revision plan itself.
    # The specialist for this might be the orchestrator or a generalist agent.
    # For simplicity, we'll run a standard decision cycle with this new focus.
    orchestrator_agent._log(f"Executing revised decision cycle with focus: {revision_plan_text}", "info")
    revised_cycle_result = await execute_decision_cycle(orchestrator_agent, revision_plan_text, augmented_mission_context)
    revised_cycle_result["original_rejected_focus"] = rejected_decision_focus # Add for clarity
    revised_cycle_result["cost"] += plan_cost # Add planning cost

    if revised_cycle_result["status"] == "completed":
        orchestrator_agent.last_revision_plan = None # Clear plan if successful

    return revised_cycle_result

async def _run_decision_loop(
    orchestrator_agent: Any, 
    decision_agent: RoutedAgent, 
    context_brief: dict, 
    specialist_interaction_logs: List[dict],
    review_interaction_logs: List[dict],
    json_parsing_logs: List[dict],
    orchestrator_interaction_logs: List[dict]
) -> Tuple[str, float, List[dict]]: # Returns: recommendation_text, total_cost_of_loop, raw_reviews
    
    total_loop_cost = 0.0
    
    # Construct initial prompt for the specialist
    initial_prompt_parts = [
        f"You are {decision_agent.name}. Your current task is to analyze the following decision focus: '{context_brief['current_decision_focus']}'",
        f"within the context of the overall mission: '{context_brief['overall_mission']}'."
    ]
    if context_brief.get("revision_details"):
        rev_details = context_brief["revision_details"]
        initial_prompt_parts.append(
            f"This is a revision of a previously rejected decision. "
            f"Original focus: '{rev_details.get('original_focus')}'. "
            f"Rejection reason: '{rev_details.get('rejection_reason')}'."
        )
        if rev_details.get("rejected_recommendation"):
            initial_prompt_parts.append(f"Rejected recommendation: '{rev_details.get('rejected_recommendation')}'.")

    initial_prompt_parts.append(
        "Please provide your detailed analysis, reasoning, and a specific, actionable recommendation. "
        "Structure your response as a JSON object with keys 'analysis', 'reasoning', and 'recommendation'."
    )
    initial_prompt_for_specialist = "\n".join(initial_prompt_parts)

    recommendation_text = ""
    raw_reviews_for_cycle: List[Dict] = []

    for loop_count in range(orchestrator_agent.MAX_REVISION_LOOPS):
        orchestrator_agent._log(f"Decision loop iteration {loop_count + 1}/{orchestrator_agent.MAX_REVISION_LOOPS} with {decision_agent.name}", "info")
        orchestrator_interaction_logs.append({"timestamp": orchestrator_agent._get_timestamp(), "event": "decision_loop_iteration_start", "agent": decision_agent.name, "iteration": loop_count + 1})

        # 1. Get Recommendation from Specialist
        orchestrator_agent._log(f"Getting recommendation from {decision_agent.name}", "info")
        current_prompt = initial_prompt_for_specialist
        if loop_count > 0: # If it's a revision loop based on peer feedback
            # Modify prompt to include feedback from previous iteration's reviews
            feedback_summary = "\n\nPrevious peer review feedback to incorporate:"
            for review in raw_reviews_for_cycle: # Use reviews from this decision loop
                if review.get("feedback") and review.get("status") != "approved":
                    feedback_summary += f"\n- Reviewer {review.get('reviewer_id','Unknown')} ({review.get('status')}): {review.get('feedback')}"
            current_prompt += feedback_summary
            current_prompt += "\n\nPlease provide an updated JSON response with 'analysis', 'reasoning', and 'recommendation', addressing the feedback."
        
        # Log specialist interaction before the call
        log_entry_before_ask = {
            "timestamp": orchestrator_agent._get_timestamp(),
            "agent_name": decision_agent.name,
            "prompt": current_prompt,
            "type": "request_recommendation"
        }
        specialist_interaction_logs.append(log_entry_before_ask)

        try:
            response_json, cost = await _get_json_response(
                decision_agent, 
                current_prompt, 
                "Failed to get valid recommendation JSON",
                json_parsing_logs, 
                orchestrator_agent._log,
                orchestrator_agent._extract_json_from_string,
                retry_count=orchestrator_agent.MAX_JSON_RETRIES
            )
            total_loop_cost += cost
            log_entry_before_ask["raw_response"] = response_json # Or the string from which it was parsed, if available
            log_entry_before_ask["cost"] = cost
            log_entry_before_ask["parsed_response"] = response_json
            log_entry_before_ask["status"] = "success"

            recommendation_text = response_json.get("recommendation", "Error: Recommendation not found in JSON.")
            orchestrator_agent._log(f"Recommendation from {decision_agent.name}: '{recommendation_text[:100]}...'. Cost: ${cost:.4f}", "info")

        except AgentCommunicationError as e:
            orchestrator_agent._log(f"Error getting recommendation from {decision_agent.name}: {e}", "error")
            log_entry_before_ask["error"] = str(e)
            log_entry_before_ask["status"] = "error"
            # This is a critical failure for the loop, re-raise to be caught by execute_decision_cycle
            raise
        
        # 2. Peer Review (if not final loop and recommendation is substantial)
        final_loop = (loop_count == orchestrator_agent.MAX_REVISION_LOOPS - 1)
        if not recommendation_text or "Error:" in recommendation_text:
            orchestrator_agent._log(f"Skipping review due to invalid recommendation from {decision_agent.name}.", "warning")
            if final_loop:
                raise AgentCommunicationError(f"Failed to get a valid recommendation from {decision_agent.name} after {orchestrator_agent.MAX_REVISION_LOOPS} attempts.")
            continue # Should not happen if _get_json_response raises on error, but as a safeguard

        orchestrator_agent._log(f"Initiating peer review for {decision_agent.name}'s recommendation (Loop {loop_count + 1})", "info")
        reviews, review_cost = await _batch_peer_review(
            orchestrator_agent,
            decision_agent.name, 
            recommendation_text, 
            review_interaction_logs, 
            json_parsing_logs,
            final=final_loop # Signal if it's the final review round
        )
        total_loop_cost += review_cost
        raw_reviews_for_cycle = reviews # Store reviews for this iteration
        orchestrator_agent._log(f"Peer review completed. Cost: ${review_cost:.4f}", "info")
        orchestrator_interaction_logs.append({
            "timestamp": orchestrator_agent._get_timestamp(), 
            "event": "peer_review_completed", 
            "subject_agent": decision_agent.name, 
            "recommendation_reviewed": recommendation_text,
            "reviews_summary": [{k: r[k] for k in ('reviewer_id', 'status', 'feedback') if k in r} for r in reviews],
            "cost": review_cost
        })

        # 3. Check Consensus
        consensus = orchestrator_agent._check_review_consensus(reviews)
        orchestrator_agent._log(f"Review consensus: {consensus}", "info")
        orchestrator_interaction_logs.append({"timestamp": orchestrator_agent._get_timestamp(), "event": "consensus_check", "consensus": consensus})

        if consensus:
            orchestrator_agent._log(f"Consensus reached for {decision_agent.name}'s recommendation.", "info")
            break # Exit loop, recommendation is approved
        else:
            orchestrator_agent._log(f"No consensus. Iteration {loop_count + 1} of {orchestrator_agent.MAX_REVISION_LOOPS}. Revising...", "warning")
            if final_loop:
                orchestrator_agent._log(f"Max revision loops reached for {decision_agent.name}. Proceeding with last recommendation despite lack of full consensus or using fallback.", "warning")
                # Decide if we proceed with the current recommendation or fail the cycle.
                # For now, let's assume we proceed with the last recommendation if it's not empty.
                if not recommendation_text:
                     raise AgentCommunicationError(f"Max revision loops reached and no valid recommendation obtained for {decision_agent.name}.")
                break # Exit loop, proceed with current recommendation
            # Prepare for next iteration by ensuring `initial_prompt_for_specialist` now includes review feedback.
            # This is handled at the start of the loop.

    orchestrator_interaction_logs.append({"timestamp": orchestrator_agent._get_timestamp(), "event": "decision_loop_end", "agent": decision_agent.name, "final_recommendation": recommendation_text, "total_loop_cost": total_loop_cost})
    return recommendation_text, total_loop_cost, raw_reviews_for_cycle 