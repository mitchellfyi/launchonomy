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
            Layout(name="status", size=3),
            Layout(name="agents", size=10),
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
        max_len = 70
        if len(message) > max_len:
            self._detail_activity_message = message[:max_len-3] + "..."
        else:
            self._detail_activity_message = message
        
    def add_log(self, message: str, msg_type: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_log_entry = f"[{timestamp}] {message}"
        self.logs.append(full_log_entry) # Keep full internal log
        if len(self.logs) > 200: # Prune internal log
            self.logs = self.logs[-100:] 

        # Update brief activity log for UI (excluding debug, truncating others)
        if msg_type != "debug":
            max_brief_len = 80
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

        self.layout["status"].update(
            Panel(panel_renderable, title="Status")
        )

        self.layout["agents"].update(
            Panel(
                Text("\n".join(f"• {agent}" for agent in sorted(self.all_known_agents))),
                title="Known Agents (All Created)"
            )
        )
        self.layout["logs"].update(
            Panel(
                Text("\n".join(self.brief_activity_log)), # Use the new brief_activity_log
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

        orchestrator = create_orchestrator(client=openai_client)
        monitor = MissionMonitor()
        
        with Live(monitor.layout, refresh_per_second=10, console=console, vertical_overflow="visible") as live:
            
            # Define a wrapper for log_patch that has access to the live object
            def live_aware_log_patch(agent_name: str, msg: str, msg_type: str = "info"):
                # agent_logger.log_agent is for direct console prints, separate from Rich logging handler
                # Only print directly if Live is not started (e.g. before Live starts, or after it stops, or during Prompt)
                if not live.is_started: 
                    agent_logger.log_agent(agent_name, msg, msg_type)
                
                # The rest of log_patch logic for updating monitor panels remains the same
                monitor.add_log(f"{agent_name}: {msg}", msg_type)
                current_activity_detail = f"{agent_name}: {msg[:100]}"
                monitor.set_detail_activity(current_activity_detail)

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
                is_processing = True 

                if "MISSION_COMPLETE" in msg:
                    new_overall_status = "Mission Complete!"
                    is_processing = False
                elif "MISSION_HALTED" in msg:
                    new_overall_status = "Mission Halted!"
                    is_processing = False
                elif msg == "Cycle Complete. Awaiting User Review.": 
                    new_overall_status = msg
                    is_processing = False
                elif agent_name == orchestrator.name:
                    if "Determining next strategic step" in msg:
                        new_overall_status = "Orchestrator: Planning next strategy..."
                    elif "Revising rejected cycle" in msg:
                        new_overall_status = "Orchestrator: Revising plan after feedback..."
                    elif "Selecting or creating specialist" in msg:
                        new_overall_status = "Orchestrator: Delegating to specialist..."
                    elif "Starting decision loop with" in msg:
                        match = re.search(r"Starting decision loop with (\w+)", msg)
                        specialist = match.group(1) if match else "specialist"
                        new_overall_status = f"Orchestrator: Consulting {specialist}..."
                    elif "Assigning execution task to" in msg:
                        match = re.search(r"Assigning execution task to (\w+)", msg)
                        executor = match.group(1) if match else "agent"
                        new_overall_status = f"Orchestrator: Tasking {executor}..."
                    elif "Attempting to execute recommendation via" in msg:
                        match = re.search(r"via (\w+)", msg)
                        executor = match.group(1) if match else "agent"
                        new_overall_status = f"Orchestrator: {executor} executing..."
                    elif "Performing final smoke-test review" in msg:
                        new_overall_status = "Orchestrator: Reviewing outcome..."
                    elif "Archiving cycle log and running retrospective" in msg:
                        new_overall_status = "Orchestrator: Finalizing cycle..."
                elif agent_name != orchestrator.name: 
                    if "Executing task:" in msg or "Executing an task:" in msg :
                        new_overall_status = f"{agent_name}: Executing task..."
                    elif "Task complete" in msg or "Task finished" in msg:
                        new_overall_status = f"{agent_name}: Task finished."
                    elif "Error during execution" in msg:
                        new_overall_status = f"{agent_name}: Error reported."
                
                if not new_overall_status: 
                    max_len = 70
                    truncated_msg = msg[:max_len] + "..." if len(msg) > max_len else msg
                    new_overall_status = f"{agent_name}: {truncated_msg}"

                if new_overall_status != monitor._overall_status_message:
                     monitor.set_overall_status(new_overall_status, is_running=is_processing)

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