#!/usr/bin/env python3

import sys
import json
import asyncio
import logging
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, Union, List, Dict, Any
import click
from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Prompt
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich import print as rprint
from rich.spinner import Spinner
from rich.text import Text
from rich.columns import Columns
try:
    from orchestrator.orchestrator_agent import create_orchestrator
except ImportError:
    # Fallback for when running from within orchestrator directory
    from orchestrator_agent import create_orchestrator
from autogen_ext.models.openai import OpenAIChatCompletionClient
from typing import Any, AsyncIterator
try:
    from orchestrator.logging_utils import OverallMissionLog, get_timestamp
except ImportError:
    # Fallback for when running from within orchestrator directory
    from logging_utils import OverallMissionLog, get_timestamp
import re

load_dotenv()

# Configure rich console
console = Console()

# Configure logging with rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, console=console)]
)
logger = logging.getLogger("cli")

class TokenTrackingOpenAIClient:
    """Wrapper around OpenAIChatCompletionClient that tracks token usage."""
    
    def __init__(self, client: OpenAIChatCompletionClient, monitor: 'MissionMonitor'):
        self._client = client
        self._monitor = monitor
    
    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped client."""
        return getattr(self._client, name)
    
    async def create(self, messages, **kwargs):
        """Wrap the create method to track token usage."""
        try:
            response = await self._client.create(messages, **kwargs)
            
            # Extract token usage from response - try different possible attribute names
            usage = None
            if hasattr(response, 'usage'):
                usage = response.usage
            elif hasattr(response, 'token_usage'):
                usage = response.token_usage
            elif hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
            
            if usage:
                # Try different possible attribute names for token counts
                input_tokens = (getattr(usage, 'prompt_tokens', 0) or 
                              getattr(usage, 'input_tokens', 0) or 
                              getattr(usage, 'prompt_token_count', 0))
                output_tokens = (getattr(usage, 'completion_tokens', 0) or 
                               getattr(usage, 'output_tokens', 0) or 
                               getattr(usage, 'completion_token_count', 0))
                
                if input_tokens > 0 or output_tokens > 0:
                    self._monitor.add_tokens(input_tokens, output_tokens)
                    logger.debug(f"Token usage tracked: {input_tokens} input, {output_tokens} output")
            else:
                logger.debug("No token usage information found in response")
            
            return response
        except Exception as e:
            logger.error(f"Error in OpenAI API call: {e}")
            raise

class AgentLogger:
    def __init__(self):
        self.console = Console()
        
    def log_agent(self, agent_name: str, message: str, message_type: str = "info"):
        """Log agent messages with nice formatting."""
        color = {
            "info": "blue",
            "decision": "yellow",
            "success": "green",
            "error": "red",
            "warning": "orange3",
            "debug": "grey50"
        }.get(message_type, "white")
        
        if message_type == "debug" and not logger.isEnabledFor(logging.DEBUG):
            return
            
        self.console.print(f"[bold {color}]{agent_name}[/bold {color}]: {message}")

class MissionMonitor:
    def __init__(self):
        self.layout = Layout()
        self.layout.split_column(
            Layout(name="mission", size=3),
            Layout(name="status", size=5),  # Set to 5 lines
            Layout(name="agents", size=7),
            Layout(name="logs", ratio=1)
        )
        self.logs = []
        self._overall_status_message = "Initializing..."
        self._detail_activity_message = ""
        self._mission_is_running = True 
        self._current_operation_start_time = datetime.now()
        self.current_cycle_agents = set()
        self.all_known_agents = set()
        self.spinner = Spinner("dots", text=Text(self._overall_status_message, style="blue"))
        self.brief_activity_log_max_lines = 10 # For the UI panel
        self.brief_activity_log = [] # Separate list for UI panel
        self.orchestrator = None  # Will be set to access registry
        
        # Token tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        # Tools in use tracking
        self.tools_in_use = set()

    def set_overall_status(self, message: str, is_running: bool):
        self._overall_status_message = message
        if self.spinner:
            self.spinner.update(text=Text(message, style="blue"))
        
        if is_running and not self._mission_is_running:
            self._current_operation_start_time = datetime.now()
        
        self._mission_is_running = is_running
        if is_running and self._current_operation_start_time is None:
            self._current_operation_start_time = datetime.now()

    def set_detail_activity(self, message: str):
        # Allow longer messages for 3-line display
        max_len = 210  # Approximately 70 chars per line * 3 lines
        if len(message) > max_len:
            self._detail_activity_message = message[:max_len-3] + "..."
        else:
            self._detail_activity_message = message
    
    def add_tokens(self, input_tokens: int, output_tokens: int):
        """Add token usage to the running total."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        logger.debug(f"Tokens added: +{input_tokens} input, +{output_tokens} output. Total: {self.total_input_tokens} input, {self.total_output_tokens} output")
    
    def add_tool_in_use(self, tool_name: str):
        """Add a tool to the active tools list."""
        self.tools_in_use.add(tool_name)
    
    def remove_tool_in_use(self, tool_name: str):
        """Remove a tool from the active tools list."""
        self.tools_in_use.discard(tool_name)
        
    def add_log(self, message: str, msg_type: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_log_entry = f"[{timestamp}] {message}"
        self.logs.append(full_log_entry) # Keep full internal log
        if len(self.logs) > 200: # Prune internal log
            self.logs = self.logs[-100:] 

        # Update brief activity log for UI (excluding debug, truncating others)
        if msg_type != "debug":
            max_brief_len = 400  # Approximately 80 chars per line * 5 lines
            brief_log_entry = message # Use message directly, not full_log_entry with timestamp
            if len(brief_log_entry) > max_brief_len:
                brief_log_entry = brief_log_entry[:max_brief_len-3] + "..."
            
            self.brief_activity_log.append(brief_log_entry) 
            if len(self.brief_activity_log) > self.brief_activity_log_max_lines:
                self.brief_activity_log = self.brief_activity_log[-self.brief_activity_log_max_lines:]
        
    def add_agent(self, agent: str):
        self.current_cycle_agents.add(agent)
        self.all_known_agents.add(agent)
        
    def remove_agent(self, agent: str):
        self.current_cycle_agents.discard(agent)
    
    def set_orchestrator(self, orchestrator):
        """Set orchestrator reference to access registry information."""
        self.orchestrator = orchestrator

    def update(self, mission_title: str):
        self.layout["mission"].update(
            Panel(Text(mission_title, overflow="fold"), title="Overall Mission")
        )

        textual_parts_for_status_line = []
        if not self._mission_is_running:
            textual_parts_for_status_line.append(Text(self._overall_status_message, style="blue"))

        if self._detail_activity_message:
            textual_parts_for_status_line.append(Text.assemble(Text(" [", style="dim"), Text(self._detail_activity_message, style="italic dim"), Text("]", style="dim")))

        if self._current_operation_start_time and self._mission_is_running: 
            elapsed_seconds = (datetime.now() - self._current_operation_start_time).total_seconds()
            textual_parts_for_status_line.append(f" ({elapsed_seconds:.1f}s)")
        
        assembled_main_text = Text.assemble(*textual_parts_for_status_line)

        panel_renderable: Union[Text, Columns]
        if self._mission_is_running:
            elements_for_columns = [self.spinner]
            if self._detail_activity_message or (self._current_operation_start_time and self._mission_is_running):
                elements_for_columns.append(Text(" "))
                detail_and_timer_parts = []
                if self._detail_activity_message:
                    detail_and_timer_parts.append(Text.assemble(Text(" [", style="dim"), Text(self._detail_activity_message, style="italic dim"), Text("]", style="dim")))
                if self._current_operation_start_time and self._mission_is_running:
                    elapsed_seconds = (datetime.now() - self._current_operation_start_time).total_seconds()
                    detail_and_timer_parts.append(Text(f" ({elapsed_seconds:.1f}s)", style="dim"))
                elements_for_columns.append(Text.assemble(*detail_and_timer_parts))

            panel_renderable = Columns(elements_for_columns, padding=0, expand=False)
        else:
            panel_renderable = assembled_main_text

        # Create expanded status display
        status_lines = []
        
        # Line 1: Main status
        if self._mission_is_running:
            # Create status line with spinner indicator
            status_line = Text()
            status_line.append("● ", style="bold blue")  # Use bullet instead of spinner for static display
            status_line.append(self._overall_status_message, style="blue")
            status_lines.append(status_line)
        else:
            status_lines.append(Text(self._overall_status_message, style="blue"))
        
        # Lines 2-4: Detail activity (up to 3 lines)
        if self._detail_activity_message:
            activity_text = Text()
            activity_text.append("Activity: ", style="dim")
            
            # Split long activity messages into multiple lines (max 70 chars per line)
            activity_msg = self._detail_activity_message
            line_length = 70
            activity_lines = []
            
            while activity_msg:
                if len(activity_msg) <= line_length:
                    activity_lines.append(activity_msg)
                    break
                else:
                    # Find a good break point (space or punctuation)
                    break_point = line_length
                    for i in range(line_length, max(0, line_length - 20), -1):
                        if activity_msg[i] in ' .,;:-':
                            break_point = i
                            break
                    
                    activity_lines.append(activity_msg[:break_point].strip())
                    activity_msg = activity_msg[break_point:].strip()
                    
                    if len(activity_lines) >= 3:  # Limit to 3 lines
                        if activity_msg:
                            activity_lines[-1] += "..."
                        break
            
            # Add the first activity line
            activity_text.append(activity_lines[0] if activity_lines else "", style="italic dim")
            status_lines.append(activity_text)
            
            # Add additional activity lines if they exist
            for line in activity_lines[1:]:
                status_lines.append(Text.assemble(Text("         ", style="dim"), Text(line, style="italic dim")))
        else:
            status_lines.append(Text("Activity: Idle", style="dim"))
        
        # Line: Timer and Token usage
        timer_token_line = Text()
        if self._current_operation_start_time and self._mission_is_running:
            elapsed_seconds = (datetime.now() - self._current_operation_start_time).total_seconds()
            timer_token_line.append(f"Elapsed: {elapsed_seconds:.1f}s", style="dim")
        else:
            timer_token_line.append("Elapsed: --", style="dim")
        
        # Add token usage
        timer_token_line.append(" | ", style="dim")
        timer_token_line.append(f"Tokens: ", style="dim")
        timer_token_line.append(f"↑{self.total_input_tokens:,}", style="green")
        timer_token_line.append(" ", style="dim")
        timer_token_line.append(f"↓{self.total_output_tokens:,}", style="cyan")
        
        status_lines.append(timer_token_line)
        
        status_content = Text("\n").join(status_lines)
        
        self.layout["status"].update(
            Panel(status_content, title="Status")
        )

        # Create simple CSV format agent list
        agent_names = sorted(self.all_known_agents)
        
        # Create comma-separated list with styling
        agents_csv = Text()
        for i, agent_name in enumerate(agent_names):
            if i > 0:
                agents_csv.append(", ", style="dim")
            agents_csv.append(agent_name, style="cyan")
        
        # Add agents information
        agents_content = Text()
        agents_content.append("Agents: ", style="bold white")
        agents_content.append(agents_csv)
        
        # Show tools in use (if any are being actively used)
        if self.tools_in_use:
            agents_content.append(f"\n\nTools in Use: ", style="bold white")
            tools_csv = Text()
            sorted_tools = sorted(self.tools_in_use)
            for i, tool in enumerate(sorted_tools):
                if i > 0:
                    tools_csv.append(", ", style="dim")
                tools_csv.append(tool, style="yellow")
            agents_content.append(tools_csv)
        else:
            # Show a simple indicator that no tools are currently active
            agents_content.append(f"\n\nTools in Use: ", style="bold white")
            agents_content.append("None active", style="dim")
        
        self.layout["agents"].update(
            Panel(agents_content, title="Known Agents")
        )
        # Format activity log with colored agent names
        log_content = Text()
        
        for i, entry in enumerate(self.brief_activity_log):
            if i > 0:
                log_content.append("\n")
            
            # Extract agent name and message for coloring
            if ": " in entry:
                agent_name, message = entry.split(": ", 1)
                
                # Color all agent names in cyan (same as Known Agents panel)
                log_content.append(agent_name, style="cyan")
                log_content.append(": ", style="dim")
                log_content.append(message)
            else:
                # No agent name found, use plain text
                log_content.append(entry)
        
        self.layout["logs"].update(
            Panel(
                log_content,
                title="Recent Activity Log"
            )
        )

async def run_mission_cli(overall_mission_string: str, agent_logger: AgentLogger, debug_mode: bool):
    """Runs the mission with the orchestrator, including CLI interactions for accept/reject."""
    if debug_mode:
        logger.setLevel(logging.DEBUG)
        agent_logger.console.print("[bold yellow]DEBUG mode enabled.[/bold yellow]")

    # Generate a unique ID for the overall mission
    overall_mission_log_id = f"mission_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{re.sub(r'\\W+','_',overall_mission_string[:30])}"
    overall_log = OverallMissionLog(
        mission_id=overall_mission_log_id,
        timestamp=get_timestamp(),
        overall_mission=overall_mission_string,
        final_status="started" 
    )
    total_mission_cost = 0.0

    try:
        # Initialize the OpenAI client here
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.critical("OPENAI_API_KEY environment variable not set.")
            rprint("[bold red]Error: OPENAI_API_KEY environment variable not set. Please set it in your .env file or system environment.[/bold red]")
            return

        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        logger.info(f"Initializing OpenAIChatCompletionClient with model: {model_name}")
        
        openai_client = OpenAIChatCompletionClient(
            api_key=api_key,
            model=model_name
        )

        monitor = MissionMonitor()
        
        # Create token tracking wrapper
        token_tracking_client = TokenTrackingOpenAIClient(openai_client, monitor)
        
        orchestrator = create_orchestrator(client=token_tracking_client)
        monitor.set_orchestrator(orchestrator)  # Set orchestrator reference for registry access
        
        with Live(monitor.layout, refresh_per_second=10, console=console, vertical_overflow="visible") as live:
            
            # Define a wrapper for log_patch that has access to the live object
            def live_aware_log_patch(agent_name: str, msg: str, msg_type: str = "info"):
                # agent_logger.log_agent is for direct console prints, separate from Rich logging handler
                # Only print directly if Live is not started (e.g. before Live starts, or after it stops, or during Prompt)
                if not live.is_started: 
                    agent_logger.log_agent(agent_name, msg, msg_type)
                
                # Token tracking is now handled by TokenTrackingOpenAIClient wrapper
                
                # Extract tool usage from log messages
                tool_usage_patterns = [
                    r'using tool[:\s]+(\w+)',
                    r'calling tool[:\s]+(\w+)',
                    r'executing tool[:\s]+(\w+)',
                    r'tool[:\s]+(\w+)[:\s]+(?:called|executed|used)',
                    r'(?:spreadsheet|calendar|email|crm|analytics|payment|webhook|api|database)',
                ]
                
                # Check for specific tool mentions
                for pattern in tool_usage_patterns:
                    tool_match = re.search(pattern, msg.lower())
                    if tool_match:
                        if tool_match.groups():
                            tool_name = tool_match.group(1)
                        else:
                            tool_name = tool_match.group(0)
                        monitor.add_tool_in_use(tool_name)
                        break
                
                # Check for tool completion/stopping
                if any(phrase in msg.lower() for phrase in ['tool completed', 'tool finished', 'tool stopped']):
                    # Could extract specific tool name and remove it, but for now just note completion
                    pass
                
                # The rest of log_patch logic for updating monitor panels remains the same
                monitor.add_log(f"{agent_name}: {msg}", msg_type)

                if agent_name not in monitor.current_cycle_agents:
                    monitor.add_agent(agent_name)

                if agent_name == orchestrator.name: 
                    creation_match = re.search(r"Creating new agent: '([^']*)'", msg)
                    if creation_match:
                        new_agent_name = creation_match.group(1)
                        if new_agent_name not in monitor.all_known_agents:
                            monitor.add_agent(new_agent_name)
                            logger.debug(f"Detected and added new agent from log: {new_agent_name}")
                    
                    created_match = re.search(r"Agent '([^']*)' created successfully", msg)
                    if created_match:
                        new_agent_name = created_match.group(1)
                        if new_agent_name not in monitor.all_known_agents:
                            monitor.add_agent(new_agent_name)
                            logger.debug(f"Detected and added confirmed agent from log: {new_agent_name}")
                
                new_overall_status = ""
                activity_detail = ""
                is_processing = True 

                if "MISSION_COMPLETE" in msg:
                    new_overall_status = "Mission Complete!"
                    activity_detail = f"{agent_name}: {msg}"
                    is_processing = False
                elif "MISSION_HALTED" in msg:
                    new_overall_status = "Mission Halted!"
                    activity_detail = f"{agent_name}: {msg}"
                    is_processing = False
                elif msg == "Cycle Complete. Awaiting User Review.": 
                    new_overall_status = msg
                    activity_detail = "Waiting for user decision on cycle outcome"
                    is_processing = False
                elif agent_name == orchestrator.name:
                    if "Determining next strategic step" in msg:
                        new_overall_status = "Orchestrator: Planning next strategy..."
                        activity_detail = f"Analyzing previous cycles and determining next strategic step"
                    elif "Revising rejected cycle" in msg:
                        new_overall_status = "Orchestrator: Revising plan after feedback..."
                        activity_detail = f"Processing user feedback and revising approach"
                    elif "Selecting or creating specialist" in msg:
                        new_overall_status = "Orchestrator: Delegating to specialist..."
                        activity_detail = f"Finding or creating appropriate specialist agent"
                    elif "Starting decision loop with" in msg:
                        match = re.search(r"Starting decision loop with (\w+)", msg)
                        specialist = match.group(1) if match else "specialist"
                        new_overall_status = f"Orchestrator: Consulting {specialist}..."
                        activity_detail = f"Running decision loop with {specialist} for recommendations"
                    elif "Assigning execution task to" in msg:
                        match = re.search(r"Assigning execution task to (\w+)", msg)
                        executor = match.group(1) if match else "agent"
                        new_overall_status = f"Orchestrator: Tasking {executor}..."
                        activity_detail = f"Delegating execution task to {executor}"
                    elif "Attempting to execute recommendation via" in msg:
                        match = re.search(r"via (\w+)", msg)
                        executor = match.group(1) if match else "agent"
                        new_overall_status = f"Orchestrator: {executor} executing..."
                        activity_detail = f"{executor} is executing the recommended action"
                    elif "Performing final smoke-test review" in msg:
                        new_overall_status = "Orchestrator: Reviewing outcome..."
                        activity_detail = f"Conducting final review of execution results"
                    elif "Archiving cycle log and running retrospective" in msg:
                        new_overall_status = "Orchestrator: Finalizing cycle..."
                        activity_detail = f"Archiving logs and running retrospective analysis"
                    elif "Asking" in msg and "Agent" in msg:
                        # Handle agent communication messages
                        agent_match = re.search(r"Asking (\w+[-]?\w*)", msg)
                        if agent_match:
                            target_agent = agent_match.group(1)
                            new_overall_status = f"Orchestrator: Consulting {target_agent}..."
                            activity_detail = f"Requesting input from {target_agent}"
                        else:
                            activity_detail = f"{agent_name}: {msg}"
                    else:
                        activity_detail = f"{agent_name}: {msg}"
                elif agent_name != orchestrator.name: 
                    if "Executing task:" in msg or "Executing an task:" in msg :
                        new_overall_status = f"{agent_name}: Executing task..."
                        activity_detail = f"{agent_name} is working on assigned task"
                    elif "Task complete" in msg or "Task finished" in msg:
                        new_overall_status = f"{agent_name}: Task finished."
                        activity_detail = f"{agent_name} has completed their assigned task"
                    elif "Error during execution" in msg:
                        new_overall_status = f"{agent_name}: Error reported."
                        activity_detail = f"{agent_name}: {msg}"
                    else:
                        activity_detail = f"{agent_name}: {msg}"
                
                # Only update overall status if we have a specific one, otherwise keep current
                if new_overall_status and new_overall_status != monitor._overall_status_message:
                    monitor.set_overall_status(new_overall_status, is_running=is_processing)
                
                # Always update activity detail if we have one
                if activity_detail:
                    monitor.set_detail_activity(activity_detail)

                monitor.update(overall_mission_string)

            orchestrator.set_log_callback(live_aware_log_patch) # Set callback here

            monitor.set_overall_status("Initializing Mission...", is_running=True)
            monitor.add_agent(orchestrator.name)
            monitor.update(overall_mission_string)

            # Bootstrap C-Suite agents as per orchestrator primer
            monitor.set_overall_status("Bootstrapping C-Suite founding team...", is_running=True)
            monitor.update(overall_mission_string)
            await orchestrator.bootstrap_c_suite(overall_mission_string)
            
            # Add C-Suite agents to monitor
            for agent_name in orchestrator.agents.keys():
                if agent_name not in [orchestrator.name]:
                    monitor.add_agent(agent_name)
            monitor.update(overall_mission_string)

            accepted_cycle_outcomes_summary: List[Dict[str, Any]] = []
            
            monitor.set_overall_status("Orchestrator: Determining initial strategic step...", is_running=True)
            await asyncio.sleep(0.1)
            current_decision_focus = await orchestrator.determine_next_strategic_step(
                overall_mission_string, 
                []
            )

            while True:
                if current_decision_focus.upper() == "MISSION_COMPLETE":
                    monitor.set_overall_status("Mission Deemed Complete by AI!", is_running=False)
                    live.update(monitor.layout)
                    rprint(Panel("[bold green]Mission Deemed Complete by AI![/bold green]"))
                    break

                monitor.set_overall_status(f"Cycle Focus: {current_decision_focus[:60]}...", is_running=True)
                monitor.set_detail_activity("Orchestrator preparing for decision cycle...")
                monitor.update(overall_mission_string)
                
                cycle_result = await orchestrator.execute_decision_cycle(
                    current_decision_focus=current_decision_focus,
                    mission_context={"overall_mission": overall_mission_string}
                )
                monitor.current_cycle_agents.clear()
                monitor.add_agent(orchestrator.name)

                # Add cycle result to overall log
                overall_log.decision_cycles_summary.append(cycle_result)
                total_mission_cost += cycle_result.get("total_cycle_cost", 0.0)
                overall_log.total_mission_cost = total_mission_cost
                overall_log.total_decision_cycles += 1

                monitor.set_overall_status("Cycle Complete. Awaiting User Review.", is_running=False)
                live.update(monitor.layout)
                live.stop()

                # Now that Live is stopped, print the static summary information below it.
                outcome_to_display = cycle_result.get("execution_result") or cycle_result.get("recommendation") or {"info": "No specific execution or recommendation output."}
                status_color = "green" if cycle_result.get("status", "").startswith("success") else "red"
                
                rprint(Panel(json.dumps(outcome_to_display, indent=2, default=str), 
                             title=f"[bold {status_color}]Cycle Outcome for: {current_decision_focus[:60]}[/bold {status_color}]",
                             border_style=status_color))
                if cycle_result.get("error"):
                    rprint(Panel(f"[bold red]Error in cycle:[/bold red] {cycle_result.get('error')}", title="Cycle Error"))

                # Concise summary before prompting for action
                summary_title = f"[bold yellow]Decision Point for: {current_decision_focus[:60]}...[/bold yellow]"
                summary_content = "Proposed action/outcome summary:\n"
                if cycle_result.get("execution_result") and isinstance(cycle_result["execution_result"], dict):
                    exec_res = cycle_result["execution_result"]
                    summary_content += exec_res.get("description", "No description available.")
                    if exec_res.get("human_task_description"):
                        summary_content += f"\n  [bold]Human Task:[/bold] {exec_res.get('human_task_description')}"
                elif cycle_result.get("recommendation_text"):
                    summary_content += cycle_result["recommendation_text"]
                else:
                    summary_content += "No specific action or recommendation was detailed for this cycle."
                
                # Ensure the summary panel is printed clearly before the prompt
                console.print(Panel(Text(summary_content, style="yellow"), title=summary_title))
                console.line() # Add a blank line for separation

                # Determine if auto-acceptance is possible
                action = ""
                auto_accepted = False
                if cycle_result.get("status", "").startswith("success") and \
                   isinstance(cycle_result.get("execution_result"), dict) and \
                   not cycle_result["execution_result"].get("human_task_description") and \
                   not cycle_result.get("error"): # Also ensure no top-level error
                    
                    rprint(Panel("[bold green]Outcome Auto-Accepted[/bold green]: No human task required and cycle was successful.", 
                                 title="[green]Auto-Acceptance[/green]"))
                    console.line()
                    action = "y"
                    auto_accepted = True

                if not auto_accepted:
                    # live.stop() was already called before printing summaries
                    action_prompt_text = "[bold]Action[/bold]: [Y]es to accept, [N]o to reject, or [Q]uit mission? (y/n/q)"
                    action_choices = ["y", "n", "q"]
                    action = Prompt.ask(action_prompt_text, choices=action_choices, default="y").lower()
                
                live.start() # Restart the live display after action is determined (auto or by prompt)

                if action == "q":
                    monitor.set_overall_status("Mission Terminated by User.", is_running=False)
                    live.update(monitor.layout)
                    rprint(Panel("[bold yellow]Mission Terminated by User.[/bold yellow]"))
                    break
                elif action == "y":
                    if cycle_result.get("status", "").startswith("success") and cycle_result.get("execution_result"):
                        execution_summary = cycle_result["execution_result"].get("description", "No description provided.")
                        human_task = cycle_result["execution_result"].get("human_task_description")
                        if human_task:
                            execution_summary += f" (Human Task: {human_task})"
                        
                        accepted_cycle_outcomes_summary.append({
                            "decision_focus": current_decision_focus,
                            "execution_type": cycle_result["execution_result"].get("execution_type", "unknown_type"),
                            "summary": execution_summary,
                            "output_data": cycle_result["execution_result"].get("output_data")
                        })
                    else:
                        summary_info = cycle_result.get("recommendation_text") or cycle_result.get("status", "unknown status")
                        accepted_cycle_outcomes_summary.append({
                            "decision_focus": current_decision_focus,
                            "summary": summary_info 
                        })

                    monitor.set_overall_status("Outcome Accepted. Orchestrator determining next step...", is_running=True)
                    live.update(monitor.layout); await asyncio.sleep(0.1)
                    current_decision_focus = await orchestrator.determine_next_strategic_step(
                        overall_mission_string, 
                        accepted_cycle_outcomes_summary
                    )
                elif action == "n":
                    live.stop()
                    rejection_reason = Prompt.ask("  Please provide a brief reason for rejection")
                    live.start()
                    monitor.set_overall_status("Outcome Rejected. Orchestrator processing feedback...", is_running=True)
                    live.update(monitor.layout); await asyncio.sleep(0.1)
                    
                    current_decision_focus = await orchestrator.revise_rejected_cycle(
                        rejected_decision_focus=current_decision_focus,
                        rejected_recommendation=cycle_result.get("recommendation_text"),
                        rejected_execution_result=cycle_result.get("execution_output"),
                        rejection_reason=rejection_reason,
                        mission_context={"overall_mission": overall_mission_string},
                        previous_accepted_cycles_summary=accepted_cycle_outcomes_summary 
                    )
                if action in ["y", "n"] and not current_decision_focus.upper() == "MISSION_COMPLETE" and not current_decision_focus.upper().startswith("MISSION_HALTED"):
                    live.refresh()
                else:
                    overall_log.final_status = current_decision_focus.upper()
                    live.update(monitor.layout)

                if current_decision_focus.upper().startswith("MISSION_HALTED"):
                    rprint(Panel(f"[bold red]Mission Halted:[/bold red] {current_decision_focus}", title="Mission Status"))

    except Exception as e:
        logger.error(f"Critical error during mission execution: {str(e)}", exc_info=True)
        console.print(f"[bold red]Critical error during mission execution:[/bold red] {str(e)}")
        if 'live' in locals() and live.is_started:
            live.stop()
        overall_log.final_status = "CRITICAL_ERROR"
        overall_log.error_message = str(e)
        sys.exit(1)
    finally:
        if 'live' in locals() and live.is_started:
            live.stop()
        
        if overall_log.final_status == "started":
            overall_log.final_status = "ended_unexpectedly"

        overall_log.save_log()
        console.print(f"Overall mission log saved to mission_logs/{overall_log.mission_id}.json")
        console.print("CLI session ended.")

@click.command()
@click.argument('mission', required=False)
@click.option('--debug', is_flag=True, help="Enable DEBUG level logging.")
def main(mission: Optional[str] = None, debug: bool = False):
    """Run an autonomous business mission with orchestrator and user interaction.
    
    If no mission is provided, you will be prompted for one.
    """
    if not mission:
        mission = Prompt.ask(
            "[bold cyan]Enter the overall business mission[/bold cyan]",
            default="Build a fully autonomous online business that earns its first paying customer asap and remains profitable."
        )
    
    agent_logger = AgentLogger()
    asyncio.run(run_mission_cli(mission, agent_logger, debug))

if __name__ == "__main__":
    main() 