import logging
from typing import Tuple, Optional, Any, Dict
from autogen_core import RoutedAgent
from autogen_core.models import SystemMessage, UserMessage
import json
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class AgentCommunicationError(Exception):
    """Raised when agent communication fails."""
    pass

async def _ask_agent(agent: RoutedAgent, prompt: str, log_callback: Any, system_prompt: Optional[str] = None, response_format_json: bool = False) -> Tuple[str, float]:
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
        if log_callback:
            log_callback(agent_name, f"Augmented prompt for JSON response from {agent_name}.", "debug")
    else:
        if log_callback:
            log_callback(agent_name, f"Standard response format for {agent_name}.", "debug")

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
        
        if log_callback:
            log_callback(agent_name, f"Asking {agent_name}: '{final_prompt[:150]}...' with sys_prompt: '{str(current_system_prompt_content)[:100]}...'", "debug")
        resp = await agent._client.create(msgs)

        if not resp or not resp.content:
            raise AgentCommunicationError(f"Empty response from agent {agent_name}")
        
        # Attempt to get cost from response if available (depends on client implementation)
        if hasattr(resp, 'cost') and isinstance(resp.cost, (int, float)):
            cost = float(resp.cost)
        elif hasattr(resp, 'usage') and resp.usage and 'total_cost' in resp.usage: # Anthropic style
            cost = float(resp.usage['total_cost'])

        return resp.content.strip(), cost
    except Exception as e:
        if log_callback:
            log_callback(agent_name, f"Error in agent communication with {agent_name}: {str(e)}", "error")
        raise AgentCommunicationError(f"Failed to communicate with agent {agent_name}: {str(e)}")

async def _ask_orchestrator(agent: RoutedAgent, prompt: str, log_callback: Any, response_format_json: bool = False) -> Tuple[str, float]:
    """Ask the orchestrator agent (self) a question. Returns response content and cost."""
    return await _ask_agent(agent, prompt, log_callback, response_format_json=response_format_json)

async def _get_json_response(agent: RoutedAgent, 
                             prompt: str, 
                             error_msg: str, 
                             json_parsing_log_list: list[dict], # Pass the list to log attempts
                             log_callback: Any,
                             _extract_json_from_string: Any, # function dependency
                             retry_count: int = 0) -> Tuple[Dict[str, Any], float]:
    """
    Get JSON response from an agent with extraction, error handling, and retries.
    Logs attempts to json_parsing_log_list.
    Returns the parsed JSON and accumulated cost.
    """
    agent_name = getattr(agent, 'name', 'UnnamedAgent')
    raw_response = ""
    accumulated_cost = 0.0
    MAX_JSON_RETRIES = 2 # Max retries for getting valid JSON, should be a class member or config
    RETRY_DELAY_SECONDS = 2 # Delay between retries

    for attempt in range(retry_count + 1):
        try:
            raw_response, cost = await _ask_agent(agent, prompt, log_callback, response_format_json=True)
            accumulated_cost += cost
            
            extracted_json_str = _extract_json_from_string(raw_response)
            
            if extracted_json_str:
                parsed_json = json.loads(extracted_json_str)
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "agent_name": agent_name,
                    "prompt": prompt,
                    "raw_response": raw_response,
                    "extracted_json_string": extracted_json_str,
                    "parsed_json": parsed_json,
                    "status": "success",
                    "attempt": attempt + 1
                }
                json_parsing_log_list.append(log_entry)
                return parsed_json, accumulated_cost
            else:
                raise ValueError("No JSON found in response string after extraction.")

        except (json.JSONDecodeError, ValueError) as e:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "agent_name": agent_name,
                "prompt": prompt,
                "raw_response": raw_response,
                "error": str(e),
                "status": "failed_parsing",
                "attempt": attempt + 1
            }
            json_parsing_log_list.append(log_entry)
            
            if log_callback:
                log_callback(agent_name, f"Attempt {attempt + 1}/{retry_count + 1} to get JSON from {agent_name} failed: {str(e)}. Raw response: {raw_response[:200]}...", "warning")

            if attempt < retry_count:
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                prompt += "\n\nReminder: Your response MUST be a valid JSON object. Please ensure it is correctly formatted. Previous attempt failed." # Modify prompt for retry
            else:
                if log_callback:
                    log_callback(agent_name, f"Max retries reached for {agent_name} on prompt: {prompt}. {error_msg}", "error")
                raise AgentCommunicationError(f"{error_msg} from {agent_name} after {retry_count + 1} attempts. Last error: {str(e)}") from e
        except AgentCommunicationError as e: # Catch errors from _ask_agent
            # Log already done in _ask_agent for this type
            # We re-raise as this is a terminal failure for this attempt, and possibly the function
            if attempt < retry_count:
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                # Potentially modify prompt or just retry if it was a transient comms issue
                prompt += "\n\nThere was a communication issue on the previous attempt. Retrying."
                continue # Go to next attempt
            else:
                 raise # Re-raise if max retries reached

    # This part should ideally not be reached if logic is correct, but as a fallback:
    raise AgentCommunicationError(f"Failed to get valid JSON response from {agent_name} after {retry_count + 1} attempts due to unexpected exit from retry loop.") 