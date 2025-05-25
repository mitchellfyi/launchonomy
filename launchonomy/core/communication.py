# orchestrator/agent_communication.py

import json
import re
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from autogen_core import RoutedAgent
from autogen_core.models import SystemMessage, UserMessage

logger = logging.getLogger(__name__)

class AgentCommunicationError(Exception):
    """Raised when agent communication fails."""
    pass

class AgentCommunicator:
    """
    Handles all agent communication, JSON parsing, and review processes.
    
    This class provides unified methods for agent interactions, JSON response
    handling with retries, and peer review coordination.
    """
    
    def __init__(self, max_json_retries: int = 2):
        self.MAX_JSON_RETRIES = max_json_retries

    async def ask_agent(self, agent: RoutedAgent, prompt: str, system_prompt: Optional[str] = None, response_format_json: bool = False) -> Tuple[str, float]:
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
            logger.debug(f"Augmented prompt for JSON response from {agent_name}.")
        else:
            logger.debug(f"Standard response format for {agent_name}.")

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
            
            logger.debug(f"Asking {agent_name}: '{final_prompt[:150]}...' with sys_prompt: '{str(current_system_prompt_content)[:100]}...'")
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
                #     logger.debug(f"Cost not found in resp.usage or is not a number. Usage object: {resp.usage}")

            return resp.content.strip(), cost
        except Exception as e:
            logger.error(f"Error in agent communication with {agent_name}: {str(e)}")
            raise AgentCommunicationError(f"Failed to communicate with agent {agent_name}: {str(e)}")

    def extract_json_from_string(self, text: str) -> Optional[str]:
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

    async def get_json_response(self, 
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
            raw_response, cost_of_call = await self.ask_agent(agent, prompt, response_format_json=True)
            accumulated_cost += cost_of_call
            parsing_attempt_log["raw_response"] = raw_response
            parsing_attempt_log["cost_of_this_attempt"] = cost_of_call
            
            json_string = self.extract_json_from_string(raw_response)
            parsing_attempt_log["extracted_json_string"] = json_string
            
            if not json_string:
                logger.warning(f"No JSON block found in response from {agent_name}. Raw: '{raw_response[:200]}...'")
                raise json.JSONDecodeError("No JSON object found in response", raw_response, 0)
            
            parsed_json = json.loads(json_string)
            parsing_attempt_log["parsed_json"] = parsed_json
            json_parsing_log_list.append(parsing_attempt_log)
            return parsed_json, accumulated_cost

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from {agent_name} (attempt {retry_count + 1}): {str(e)}. Raw response: '{raw_response[:200]}...'")
            parsing_attempt_log["error"] = f"JSONDecodeError: {str(e)}"
            json_parsing_log_list.append(parsing_attempt_log) # Log failed attempt

            if retry_count < self.MAX_JSON_RETRIES:
                logger.warning(f"Retrying JSON request to {agent_name} (attempt {retry_count + 2}/{self.MAX_JSON_RETRIES + 1})")
                retry_prompt = (
                    f"{prompt}\n\n" # Keep original prompt for context
                    f"Your previous response was not valid JSON. Please ensure your entire response is a single, valid JSON object (starting with {{ and ending with }} or starting with [ and ending with ]) without any surrounding text or explanations. "
                    f"The error was: {str(e)}. The raw response started with: '{raw_response[:100]}...'"
                )
                await asyncio.sleep(1.5) # Small delay before retry
                # Recursively call and add cost
                parsed_json_result, cost_from_retry = await self.get_json_response(agent, retry_prompt, error_msg, json_parsing_log_list, retry_count + 1)
                accumulated_cost += cost_from_retry
                return parsed_json_result, accumulated_cost
            else:
                logger.error(f"Max JSON retries reached for {agent_name}. Giving up.")
                raise AgentCommunicationError(f"{error_msg}: Invalid JSON response after multiple retries. Last error: {str(e)}")
        except AgentCommunicationError as e: # Catch specific error from ask_agent
            logger.error(f"Agent communication error while expecting JSON from {agent_name}: {str(e)}")
            parsing_attempt_log["error"] = f"AgentCommunicationError: {str(e)}"
            json_parsing_log_list.append(parsing_attempt_log)
            raise
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"Unexpected error getting JSON response from {agent_name}: {str(e)}")
            parsing_attempt_log["error"] = f"UnexpectedError: {str(e)}"
            json_parsing_log_list.append(parsing_attempt_log)
            raise AgentCommunicationError(f"{error_msg}: Unexpected error: {str(e)}")

class ReviewManager:
    """
    Handles peer review processes and consensus checking.
    
    This class manages the coordination of peer reviews between agents
    and determines consensus based on review outcomes.
    """
    
    def __init__(self, communicator: AgentCommunicator):
        self.communicator = communicator

    async def batch_peer_review(self, 
                                subject_agent_name: str, 
                                content_to_review: str, 
                                available_agents: Dict[str, RoutedAgent],
                                review_interaction_logs: List[dict], # Log list for detailed review interactions
                                json_parsing_logs: List[dict],     # Log list for JSON parsing attempts by reviewers
                                final: bool = False
                                ) -> Tuple[List[dict], float]: # Returns list of review dicts, total_review_cost
        """Run batch peer review. Logs interaction details. Returns review dicts and total cost."""
        
        all_reviews_from_batch: List[dict] = [] # This will store the structured JSON responses from reviewers
        accumulated_review_cost = 0.0

        if not isinstance(content_to_review, str):
            content_to_review = json.dumps(content_to_review) if isinstance(content_to_review, dict) else str(content_to_review)

        reviewers = [agent for name, agent in available_agents.items() 
                    if name != subject_agent_name and hasattr(agent, 'name') and name not in ["OrchestrationAgent", "RetrospectiveAnalyser"]]
        
        if not reviewers:
            logger.warning(f"No other suitable agents available to review output from {subject_agent_name}. Skipping peer review.")
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

        logger.info(f"Starting batch peer review of output from {subject_agent_name} by {len(reviewers)} agents.")
        
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
                    f"Please critically review this {'final execution result ' if final else 'recommendation '}from agent '{subject_agent_name}':"
                    f"\n---BEGIN CONTENT---\n{content_to_review}\n---END CONTENT---\n\n"
                    "Focus on validity, potential issues, and alignment with overall mission goals. "
                    "Provide specific, actionable feedback. If there are multiple issues, list them clearly. "
                    "If you approve, explain why. "
                    "Your response MUST be a JSON object with the following keys: "
                    "{\"approved\": bool, \"feedback\": str (detailed feedback/reasons for approval/disapproval), \"estimated_confidence_if_approved\": float (0.0-1.0, your confidence in the content IF you approved it, otherwise 0.0)}."
                )
                review_log_entry["prompt"] = review_prompt
                
                # get_json_response handles retries, logs to json_parsing_logs, and returns cost
                review_json, cost = await self.communicator.get_json_response(
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
                    logger.info(f"Review from {agent_instance_name}: Valid={review_json.get('valid')}, Issue: {issue_summary}")
                else:
                    logger.info(f"Review from {agent_instance_name}: Valid={review_json.get('valid')}, No issues")

            except (AgentCommunicationError, json.JSONDecodeError) as e: # Catch errors from get_json_response
                logger.warning(f"Error during peer review from {agent_instance_name}: {str(e)}")
                review_log_entry["error"] = str(e)
                # Cost accumulated by get_json_response before failure is already part of `cost` if error was during parsing.
                # If ask_agent failed before parsing, cost might be 0 or partial from retries.
                # `cost` variable above will hold the cost from the failed get_json_response call.
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

    def check_review_consensus(self, reviews: List[dict]) -> bool:
        """Check if there is consensus among peer reviews."""
        if not reviews: 
            return False
        # Check both new format (approved) and legacy format (valid) for compatibility
        valid_reviews = [r for r in reviews if r.get("valid", False) or r.get("approved", False)]
        # Stricter: all must be valid for consensus, or a high threshold.
        # For now, let's stick to the 75% threshold.
        return len(valid_reviews) >= len(reviews) * 0.75 