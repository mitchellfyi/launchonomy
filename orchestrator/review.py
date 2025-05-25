import logging
import asyncio
from typing import List, Dict, Any, Tuple
from autogen_core import RoutedAgent

# Placeholder for agent_comm and utils, assuming they are in the same directory or accessible
from .agent_comm import _get_json_response, AgentCommunicationError, _ask_agent
from .utils import load_template, TemplateError # TemplateError might not be directly used here but good for consistency

logger = logging.getLogger(__name__)

def _check_review_consensus(reviews: List[dict]) -> bool:
    """Checks if all reviews are positive (approved)."""
    if not reviews: # No reviews means no explicit approval, could be treated as non-consensus or an edge case
        return False
    for review in reviews:
        if review.get("status") != "approved":
            return False
    return True

async def _batch_peer_review(
    orchestrator_agent_instance: Any, 
    subject_agent_name: str, 
    content_to_review: str, 
    review_interaction_logs: List[dict], # Log list for detailed review interactions
    json_parsing_logs: List[dict],     # Log list for JSON parsing attempts by reviewers
    final: bool = False
) -> Tuple[List[dict], float]: # Returns list of review dicts, total_review_cost
    """Manages batch peer review of content by available agents (excluding the subject agent)."""
    total_review_cost = 0.0
    review_results = []    
    reviewers_queried_count = 0

    # Dynamically load reviewer agent persona and primer
    try:
        reviewer_persona = load_template("reviewer_persona") 
        reviewer_primer = load_template("reviewer_primer") 
    except TemplateError as e:
        orchestrator_agent_instance._log(f"Failed to load reviewer templates: {e}. Cannot conduct reviews.", "error")
        review_interaction_logs.append({
            "timestamp": orchestrator_agent_instance._get_timestamp(),
            "event": "reviewer_template_load_failure",
            "error": str(e)
        })
        return [], 0.0 # Cannot proceed without reviewer templates

    # Identify potential reviewers (all agents except the one whose content is being reviewed)
    potential_reviewers = []
    for name, agent_obj in orchestrator_agent_instance.agents.items():
        if name != subject_agent_name:
            potential_reviewers.append(agent_obj)

    if not potential_reviewers:
        orchestrator_agent_instance._log(f"No other agents available to review {subject_agent_name}'s content.", "warning")
        review_interaction_logs.append({"timestamp": orchestrator_agent_instance._get_timestamp(), "event": "no_reviewers_available", "subject_agent": subject_agent_name})
        # If no reviewers, it could be considered an automatic approval or a specific state.
        # For now, let's assume it means no formal review, thus "approved" by default of no objection.
        # This might need refinement based on desired process logic.
        return [], 0.0 

    orchestrator_agent_instance._log(f"Starting batch peer review for {subject_agent_name}'s content by {len(potential_reviewers)} potential reviewers.", "info")

    review_tasks = []
    for reviewer_agent in potential_reviewers:
        reviewers_queried_count += 1
        # Construct prompt for the reviewer agent
        # The common reviewer_primer and reviewer_persona are used for all reviewers.
        # The specific instruction about what to review is inserted into the prompt.
        review_prompt = (
            f"{reviewer_persona}\n\n"
            f"You are reviewing content from agent: {subject_agent_name}.\n"
            f"Content to review: '{content_to_review}'.\n\n"
            f"Your task is to assess this content based on criteria such as clarity, accuracy, completeness, and alignment with the overall mission. "
            f"Provide constructive feedback and a status. "
            f"Respond with a JSON object containing: \{{\"status\": \"approved\" OR \"needs_revision\" OR \"rejected\", \"feedback\": \"YOUR_DETAILED_FEEDBACK\"}}\n"
            f"If 'approved', feedback can be minimal. If 'needs_revision' or 'rejected', detailed feedback is crucial."
        )
        if final:
            review_prompt += "\nThis is the FINAL review round. Be decisive. If it's not good enough, reject it."
        
        # Log before calling the agent
        log_entry_before_ask = {
            "timestamp": orchestrator_agent_instance._get_timestamp(),
            "event": "review_request_sent",
            "reviewer_id": reviewer_agent.name,
            "subject_agent": subject_agent_name,
            "content_snippet": content_to_review[:150] + "...",
            "prompt": review_prompt
        }
        review_interaction_logs.append(log_entry_before_ask)
        
        # Each reviewer uses its own instance but with the *common* reviewer primer for this task.
        # This assumes _get_json_response can take an agent instance and a specific system_prompt for that call.
        # If _get_json_response or _ask_agent doesn't support overriding system_prompt per call, this needs adjustment.
        # Current _ask_agent in agent_comm.py does support a system_prompt override.
        review_tasks.append(
            _get_json_response(
                reviewer_agent, 
                review_prompt, 
                f"Failed to get review from {reviewer_agent.name}",
                json_parsing_logs,
                orchestrator_agent_instance._log,
                orchestrator_agent_instance._extract_json_from_string,
                retry_count=1, # Maybe fewer retries for reviews?
                # Pass the generic reviewer_primer as the system_prompt for this specific call
                # This requires _get_json_response -> _ask_agent to correctly use this passed system_prompt
                # This functionality is not explicitly in the provided _ask_agent, so it would use reviewer_agent.system_prompt if not handled. 
                # For now, let's assume _ask_agent uses reviewer_agent.system_prompt as primary and then the override. 
                # We need to make sure this agent is primed correctly or that the override is effective.
                # A better approach might be to have a dedicated ReviewerAgent class or ensure _create_agent allows setting system_prompt for reviewers temporarily.
                # For simplicity here, we're relying on the prompt itself and the agent's base persona being somewhat general.
                # A better way: _ask_agent takes system_prompt as an override.
            )
        )

    # Gather review results
    review_responses = await asyncio.gather(*review_tasks, return_exceptions=True)

    for i, response_or_exc in enumerate(review_responses):
        reviewer_agent = potential_reviewers[i] # Assuming order is maintained
        log_entry = review_interaction_logs[-(reviewers_queried_count - i)] # Match to the request log

        if isinstance(response_or_exc, AgentCommunicationError):
            orchestrator_agent_instance._log(f"Agent communication error during review by {reviewer_agent.name}: {response_or_exc}", "error")
            review_results.append({"reviewer_id": reviewer_agent.name, "status": "error_communication", "feedback": str(response_or_exc)})
            log_entry.update({"status": "error_communication", "error": str(response_or_exc)})
        elif isinstance(response_or_exc, Exception):
            orchestrator_agent_instance._log(f"Unexpected error during review by {reviewer_agent.name}: {response_or_exc}", "error")
            review_results.append({"reviewer_id": reviewer_agent.name, "status": "error_unexpected", "feedback": str(response_or_exc)})
            log_entry.update({"status": "error_unexpected", "error": str(response_or_exc)})
        else:
            review_json, cost = response_or_exc # Unpack if successful
            total_review_cost += cost
            # Validate JSON structure
            if not isinstance(review_json, dict) or "status" not in review_json or "feedback" not in review_json:
                orchestrator_agent_instance._log(f"Invalid review JSON format from {reviewer_agent.name}: {review_json}", "warning")
                review_results.append({"reviewer_id": reviewer_agent.name, "status": "error_invalid_format", "feedback": "Received malformed JSON response.", "raw_response": str(review_json)})
                log_entry.update({"status": "error_invalid_format", "raw_response": str(review_json), "cost":cost})
            else:
                review_results.append({"reviewer_id": reviewer_agent.name, **review_json})
                orchestrator_agent_instance._log(f"Review from {reviewer_agent.name}: Status - {review_json.get('status')}, Feedback - '{review_json.get('feedback')[:50]}...'. Cost: ${cost:.4f}", "debug")
                log_entry.update({"status": "success", "review_data": review_json, "cost":cost})

    orchestrator_agent_instance._log(f"Batch peer review finished. Total review cost: ${total_review_cost:.4f}", "info")
    return review_results, total_review_cost 