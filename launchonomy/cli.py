#!/usr/bin/env python3

import sys
import json
import asyncio
import logging
import os
import glob

# Add project root to Python path for proper orchestrator package imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, List, Dict, Any
import click
from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich import print as rprint
from rich.spinner import Spinner
from rich.text import Text
from rich.columns import Columns
from rich.table import Table
from .core.orchestrator import create_orchestrator
from autogen_ext.models.openai import OpenAIChatCompletionClient
from .utils.logging import OverallMissionLog, get_timestamp
from .utils.cost_calculator import calculate_cycle_cost
import re

# Note: load_dotenv() is called in main() to ensure it runs from user's working directory

# Configure rich console
console = Console()

# Configure logging with rich
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, console=console)]
)
logger = logging.getLogger("cli")

# Suppress other loggers during Live display to prevent UI interference
def suppress_external_loggers():
    """Suppress external loggers that interfere with Rich Live display."""
    # Get all existing loggers and suppress the ones that cause UI interference
    for name in logging.Logger.manager.loggerDict:
        if name.startswith(('workflow.', 'autogen', 'openai', 'launchonomy.agents', 'launchonomy.tools')):
            external_logger = logging.getLogger(name)
            external_logger.setLevel(logging.CRITICAL)  # Only show critical errors
            # Remove any handlers that might print to console
            for handler in external_logger.handlers[:]:
                if isinstance(handler, logging.StreamHandler):
                    external_logger.removeHandler(handler)
    
    # Also suppress the root logger's console output during Live display
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler.stream.name == '<stderr>':
            # Temporarily increase level to suppress warnings
            handler.setLevel(logging.CRITICAL)

def restore_external_loggers():
    """Restore normal logging levels after Live display ends."""
    # Restore external loggers to WARNING level
    for name in logging.Logger.manager.loggerDict:
        if name.startswith(('workflow.', 'autogen', 'openai', 'launchonomy.agents', 'launchonomy.tools')):
            external_logger = logging.getLogger(name)
            external_logger.setLevel(logging.WARNING)
    
    # Restore root logger handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler.stream.name == '<stderr>':
            handler.setLevel(logging.WARNING)

class EnhancedOpenAIClient:
    """Enhanced OpenAI client with AutoGen v0.4 improvements."""
    
    def __init__(self, monitor: 'MissionMonitor', **client_kwargs):
        """Initialize with AutoGen's enhanced features."""
        # Set up enhanced client configuration
        enhanced_config = {
            'timeout': 60.0,  # Proper timeout handling
            'max_retries': 3,  # Built-in retry logic
            'retry_delay': 1.0,  # Exponential backoff
            **client_kwargs
        }
        
        self._client = OpenAIChatCompletionClient(**enhanced_config)
        self._monitor = monitor
        logger.info(f"Enhanced OpenAI client initialized with model: {enhanced_config.get('model', 'default')}")
    
    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped client."""
        return getattr(self._client, name)
    
    async def create(self, messages, **kwargs):
        """Enhanced create method with better error handling and token tracking."""
        try:
            # AutoGen v0.4 has built-in token tracking in the response
            response = await self._client.create(messages, **kwargs)
            
            # AutoGen v0.4 standardized usage tracking
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                # AutoGen v0.4 uses consistent naming
                input_tokens = getattr(usage, 'prompt_tokens', 0)
                output_tokens = getattr(usage, 'completion_tokens', 0)
                
                if input_tokens > 0 or output_tokens > 0:
                    self._monitor.add_tokens(input_tokens, output_tokens)
                    logger.debug(f"Token usage: {input_tokens} prompt + {output_tokens} completion = {input_tokens + output_tokens} total")
            
            return response
            
        except Exception as e:
            logger.error(f"Enhanced OpenAI client error: {e}")
            # AutoGen v0.4 has better error categorization
            if "rate_limit" in str(e).lower():
                logger.warning("Rate limit hit - AutoGen's retry logic will handle this")
            elif "timeout" in str(e).lower():
                logger.warning("Request timeout - consider adjusting timeout settings")
            raise
    
    async def close(self):
        """Properly close the client connection."""
        if hasattr(self._client, 'close'):
            await self._client.close()
            logger.debug("OpenAI client connection closed")

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
        self.brief_activity_log_max_lines = 30 # For tall terminals - shows recent activity
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
            max_brief_len = 120  # Allow longer messages for better readability
            brief_log_entry = message # Use message directly, not full_log_entry with timestamp
            if len(brief_log_entry) > max_brief_len:
                brief_log_entry = brief_log_entry[:max_brief_len-3] + "..."
            
            self.brief_activity_log.append(brief_log_entry) 
            # Always keep the most recent entries (scroll from bottom)
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
            
            # Simply truncate to 100 characters
            if len(activity_msg) > 70:
                activity_msg = activity_msg[:67] + "..."
            
            activity_text.append(activity_msg, style="italic dim")
            status_lines.append(activity_text)
            
            # Add additional activity lines if they exist
            for line in activity_lines[1:]:
                status_lines.append(Text(line, style="italic dim"))
        else:
            status_lines.append(Text("Activity: Idle", style="dim"))
        
        # Line: Timer and Token usage
        timer_token_line = Text()
        if self._current_operation_start_time and self._mission_is_running:
            # Always calculate elapsed time fresh for real-time updates
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
        # Format activity log with colored agent names (natural chronological order)
        log_content = Text()
        
        # Get terminal height and calculate available space for logs
        try:
            import shutil
            terminal_height = shutil.get_terminal_size().lines
            # Account for: mission(3) + status(5) + agents(7) + panel borders/titles(~6) = ~21 lines
            available_log_height = max(5, terminal_height - 21)
        except:
            available_log_height = 15  # Fallback for smaller terminals
        
        # Show the most recent entries that fit in available space (auto-scroll to bottom)
        visible_entries = self.brief_activity_log[-available_log_height:] if len(self.brief_activity_log) > available_log_height else self.brief_activity_log
        
        for i, entry in enumerate(visible_entries):
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
                title=f"Activity Log"
            )
        )

def load_mission_log(mission_file_path: str) -> Optional[OverallMissionLog]:
    """Load a mission log from a JSON file."""
    try:
        with open(mission_file_path, 'r') as f:
            data = json.load(f)
        
        # Convert dict back to OverallMissionLog dataclass
        mission_log = OverallMissionLog(
            mission_id=data["mission_id"],
            timestamp=data["timestamp"],
            overall_mission=data["overall_mission"],
            final_status=data.get("final_status", "Initialized"),
            total_mission_cost=data.get("total_mission_cost", 0.0),
            total_decision_cycles=data.get("total_decision_cycles", 0),
            total_input_tokens=data.get("total_input_tokens", 0),
            total_output_tokens=data.get("total_output_tokens", 0),
            decision_cycles_summary=data.get("decision_cycles_summary", []),
            created_agents=data.get("created_agents", []),
            current_decision_focus=data.get("current_decision_focus"),
            last_activity_description=data.get("last_activity_description"),
            kpi_outcomes=data.get("kpi_outcomes", {}),
            error_message=data.get("error_message"),
            retrospective_analysis=data.get("retrospective_analysis", {})
        )
        return mission_log
    except Exception as e:
        logger.error(f"Failed to load mission log from {mission_file_path}: {e}")
        return None

def format_token_count(tokens: int) -> str:
    """Format token count in human-friendly format."""
    if tokens == 0:
        return "0"
    elif tokens < 1000:
        return str(tokens)
    elif tokens < 1000000:
        return f"~{round(tokens/1000)}k"
    else:
        return f"~{tokens/1000000:.1f}M"

def get_recent_missions(limit: int = 5) -> List[Dict[str, Any]]:
    """Get the most recent mission logs with summary information."""
    mission_files = glob.glob("mission_logs/mission_*.json")
    
    # Sort by modification time (most recent first)
    mission_files.sort(key=os.path.getmtime, reverse=True)
    
    recent_missions = []
    for mission_file in mission_files[:limit]:
        mission_log = load_mission_log(mission_file)
        if mission_log:
            # Create a summary for display
            summary = {
                "file_path": mission_file,
                "mission_id": mission_log.mission_id,
                "mission": mission_log.overall_mission,
                "status": mission_log.final_status,
                "cycles": mission_log.total_decision_cycles,
                "cost": mission_log.total_mission_cost,
                "timestamp": mission_log.timestamp,
                "last_modified": datetime.fromtimestamp(os.path.getmtime(mission_file)).strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Determine if mission can be resumed
            resumable_statuses = ["started", "ended_unexpectedly", "CRITICAL_ERROR"]
            summary["can_resume"] = mission_log.final_status in resumable_statuses
            
            # Get last activity description - prefer the stored description, fallback to decision focus
            if mission_log.last_activity_description:
                last_activity = mission_log.last_activity_description
            elif mission_log.current_decision_focus:
                last_activity = f"Working on: {mission_log.current_decision_focus}"
            elif mission_log.decision_cycles_summary:
                last_cycle = mission_log.decision_cycles_summary[-1]
                last_activity = last_cycle.get("decision_focus", "Unknown activity")
            else:
                last_activity = "No cycles completed"
            
            # Truncate long descriptions
            if len(last_activity) > 80:
                summary["last_activity"] = last_activity[:77] + "..."
            else:
                summary["last_activity"] = last_activity
            
            # Add token count
            summary["total_tokens"] = mission_log.total_input_tokens + mission_log.total_output_tokens
            
            # Add human-friendly last modified time
            import time
            file_time = os.path.getmtime(mission_file)
            now = time.time()
            diff_seconds = now - file_time
            
            if diff_seconds < 60:
                summary["human_time"] = "just now"
            elif diff_seconds < 3600:
                minutes = int(diff_seconds / 60)
                summary["human_time"] = f"{minutes}m ago"
            elif diff_seconds < 86400:
                hours = int(diff_seconds / 3600)
                summary["human_time"] = f"{hours}h ago"
            elif diff_seconds < 604800:
                days = int(diff_seconds / 86400)
                summary["human_time"] = f"{days}d ago"
            else:
                weeks = int(diff_seconds / 604800)
                summary["human_time"] = f"{weeks}w ago"
            
            recent_missions.append(summary)
    
    return recent_missions

def display_mission_selection_menu() -> Optional[str]:
    """Display a menu for selecting between new mission or resuming existing one."""
    
    console.print("\n[bold cyan]🚀 Launchonomy Autonomous AI Agents Business System[/bold cyan]")
    console.print("=" * 60)
    
    # Get recent missions
    recent_missions = get_recent_missions(5)
    resumable_missions = [m for m in recent_missions if m["can_resume"]]
    
    if not resumable_missions:
        console.print("[yellow]No resumable missions found. Starting new mission...[/yellow]")
        return None
    
    console.print(f"\n[bold]Found {len(resumable_missions)} resumable mission(s):[/bold]")
    
    # Create table for mission display
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="bold dim", width=2, no_wrap=True)
    table.add_column("Mission", style="cyan", width=28)
    table.add_column("Status", style="yellow", width=9)
    table.add_column("Cyc", style="green", width=3)
    table.add_column("Tokens", style="magenta", width=6)
    table.add_column("Modified", style="dim", width=8)
    table.add_column("Last Activity", style="blue", width=30)
    
    for i, mission in enumerate(resumable_missions, 1):
        status_color = "red" if mission["status"] == "CRITICAL_ERROR" else "yellow"
        table.add_row(
            str(i),
            mission["mission"][:28] + ("..." if len(mission["mission"]) > 28 else ""),
            f"[{status_color}]{mission['status'][:9]}[/{status_color}]",
            str(mission["cycles"]),
            format_token_count(mission['total_tokens']),
            mission.get("human_time", "unknown"),
            mission["last_activity"][:30] + ("..." if len(mission["last_activity"]) > 30 else "")
        )
    
    console.print(table)
    
    # Get user choice
    console.print(f"\n[bold]Options:[/bold]")
    console.print(f"  [cyan]1-{len(resumable_missions)}[/cyan]: Resume mission")
    console.print("  [cyan]n[/cyan]: Start new mission")
    console.print("  [cyan]q[/cyan]: Quit")
    
    while True:
        choice = Prompt.ask("\nSelect option", default="n").lower().strip()
        
        if choice == "q":
            console.print("Goodbye!")
            sys.exit(0)
        elif choice == "n":
            return None  # Start new mission
        elif choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(resumable_missions):
                selected_mission = resumable_missions[choice_num - 1]
                
                # Show mission details and confirm
                console.print(f"\n[bold]Selected Mission:[/bold]")
                console.print(f"  Mission: {selected_mission['mission']}")
                console.print(f"  Status: {selected_mission['status']}")
                console.print(f"  Cycles Completed: {selected_mission['cycles']}")
                console.print(f"  Total Cost: ${selected_mission['cost']:.4f}")
                console.print(f"  Last Activity: {selected_mission['last_activity']}")
                
                if Confirm.ask("\nResume this mission?", default=True):
                    return selected_mission["file_path"]
            else:
                console.print(f"[red]Invalid choice. Please enter 1-{len(resumable_missions)}, 'n', or 'q'[/red]")
        else:
            console.print(f"[red]Invalid choice. Please enter 1-{len(resumable_missions)}, 'n', or 'q'[/red]")

async def run_mission_cli(overall_mission_string: str, agent_logger: AgentLogger, debug_mode: bool, resume_mission_log: Optional[OverallMissionLog] = None, continuous_mode: bool = True, max_iterations: int = 10):
    """Runs the mission with the orchestrator, including CLI interactions for accept/reject."""
    if debug_mode:
        logger.setLevel(logging.DEBUG)
        agent_logger.console.print("[bold yellow]DEBUG mode enabled.[/bold yellow]")

    # Handle mission resume or create new mission
    if resume_mission_log:
        # Resuming existing mission
        overall_log = resume_mission_log
        overall_log.final_status = "resumed"  # Update status to indicate resume
        total_mission_cost = overall_log.total_mission_cost
        console.print(f"[green]Resuming mission: {overall_log.mission_id}[/green]")
        console.print(f"[dim]Previous cycles: {overall_log.total_decision_cycles}, Cost: ${total_mission_cost:.4f}, Tokens: {overall_log.total_input_tokens + overall_log.total_output_tokens:,}[/dim]")
    else:
        # Generate a unique ID for the overall mission
        # Clean mission name: lowercase, replace spaces/special chars with underscores, remove extra underscores
        clean_mission_name = re.sub(r'[^\w\s-]', '', overall_mission_string[:30].lower())
        clean_mission_name = re.sub(r'[-\s]+', '_', clean_mission_name).strip('_')
        overall_mission_log_id = f"mission_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{clean_mission_name}"
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
            rprint("[bold red]Error: OPENAI_API_KEY environment variable not set.[/bold red]")
            rprint("\n[yellow]To fix this, you can either:[/yellow]")
            rprint("1. Create a .env file in your current directory with:")
            rprint("   [cyan]OPENAI_API_KEY=your-api-key-here[/cyan]")
            rprint("2. Set it as an environment variable:")
            rprint("   [cyan]export OPENAI_API_KEY=your-api-key-here[/cyan]")
            rprint(f"\n[dim]Current working directory: {os.getcwd()}[/dim]")
            return

        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        logger.info(f"Initializing Enhanced OpenAI client with model: {model_name}")
        
        monitor = MissionMonitor()
        
        # If resuming, restore token counts to monitor
        if resume_mission_log:
            monitor.total_input_tokens = resume_mission_log.total_input_tokens
            monitor.total_output_tokens = resume_mission_log.total_output_tokens
        
        # Create enhanced client with AutoGen v0.4 improvements
        enhanced_client = EnhancedOpenAIClient(
            monitor=monitor,
            api_key=api_key,
            model=model_name,
            # AutoGen v0.4 enhancements
            timeout=60.0,
            max_retries=3,
            retry_delay=1.0
        )
        
        orchestrator = create_orchestrator(client=enhanced_client)
        monitor.set_orchestrator(orchestrator)  # Set orchestrator reference for registry access
        
        # Suppress external loggers to prevent UI interference
        suppress_external_loggers()
        
        with Live(monitor.layout, refresh_per_second=3, console=console, vertical_overflow="visible") as live:
            
            # Background task to update timer display
            async def timer_update_task():
                while live.is_started:
                    if monitor._mission_is_running:
                        monitor.update(overall_mission_string)
                    await asyncio.sleep(0.33)  # Update every 1/3 second
            
            # Start the timer update task
            timer_task = asyncio.create_task(timer_update_task())
            
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
                            # Update mission log with new agent
                            if new_agent_name not in overall_log.created_agents:
                                overall_log.created_agents.append(new_agent_name)
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

            # Handle agent context restoration for resumed missions
            if resume_mission_log and resume_mission_log.created_agents:
                monitor.set_overall_status("Restoring agent context from previous mission...", is_running=True)
                monitor.update(overall_mission_string)
                
                # Restore C-Suite agents first (they should always exist)
                await orchestrator.bootstrap_c_suite(overall_mission_string)
                
                # Add all known agents to monitor (C-Suite + any specialists)
                for agent_name in resume_mission_log.created_agents:
                    monitor.add_agent(agent_name)
                
                # Update mission log with current agent list
                overall_log.created_agents = list(orchestrator.agents.keys())
                
                console.print(f"[cyan]Restored {len(resume_mission_log.created_agents)} agents from previous mission[/cyan]")
            else:
                # Bootstrap C-Suite agents as per orchestrator primer for new missions
                monitor.set_overall_status("Bootstrapping C-Suite founding team...", is_running=True)
                monitor.update(overall_mission_string)
                await orchestrator.bootstrap_c_suite(overall_mission_string)
                
                # Add C-Suite agents to monitor
                for agent_name in orchestrator.agents.keys():
                    if agent_name not in [orchestrator.name]:
                        monitor.add_agent(agent_name)
                
                # Track created agents in mission log
                overall_log.created_agents = list(orchestrator.agents.keys())
            
            monitor.update(overall_mission_string)

            # Handle resume vs new mission logic
            if resume_mission_log and resume_mission_log.decision_cycles_summary:
                # Resuming mission - extract accepted cycles and determine next step
                accepted_cycle_outcomes_summary = []
                for cycle in resume_mission_log.decision_cycles_summary:
                    if cycle.get("status", "").startswith("success") or "completed" in cycle.get("status", ""):
                        # Extract successful cycle summary
                        cycle_summary = {
                            "decision_focus": cycle.get("decision_focus", ""),
                            "execution_type": cycle.get("execution_output", {}).get("execution_type", "unknown"),
                            "summary": cycle.get("execution_output", {}).get("description", cycle.get("recommendation_text", "")),
                            "output_data": cycle.get("execution_output", {}).get("output_data", {})
                        }
                        accepted_cycle_outcomes_summary.append(cycle_summary)
                
                monitor.set_overall_status("Orchestrator: Resuming mission and determining next step...", is_running=True)
                console.print(f"[cyan]Resuming from {len(accepted_cycle_outcomes_summary)} completed cycles[/cyan]")
                await asyncio.sleep(0.1)
                current_decision_focus = await orchestrator.determine_next_strategic_step(
                    overall_mission_string, 
                    accepted_cycle_outcomes_summary
                )
            else:
                # New mission
                accepted_cycle_outcomes_summary: List[Dict[str, Any]] = []
                
                monitor.set_overall_status("Orchestrator: Determining initial strategic step...", is_running=True)
                await asyncio.sleep(0.1)
                current_decision_focus = await orchestrator.determine_next_strategic_step(
                    overall_mission_string, 
                    []
                )

            # C-SUITE ORCHESTRATED MODE - Run continuous C-Suite orchestration with workflow support
            monitor.set_overall_status("Starting C-Suite Orchestrated Mission...", is_running=True)
            monitor.update(overall_mission_string)
            
            mission_context = {
                "overall_mission": overall_mission_string,
                "accepted_cycles": accepted_cycle_outcomes_summary
            }
            
            # Run continuous loop with user continuation option
            total_iterations_run = 0
            all_execution_logs = []
            all_csuite_decisions = []
            final_loop_results = None
            
            while True:
                loop_results = await orchestrator.run_continuous_launch_growth_loop(
                    mission_context=mission_context,
                    max_iterations=max_iterations
                )
                
                # Accumulate results
                total_iterations_run += loop_results.get("total_iterations", 0)
                all_execution_logs.extend(loop_results.get("execution_log", []))
                all_csuite_decisions.extend(loop_results.get("csuite_decisions", []))
                final_loop_results = loop_results
                
                # Check if max iterations were reached
                if loop_results.get("final_status") == "max_iterations_reached":
                    # Stop the live display to show user prompt
                    monitor.set_overall_status(f"Reached {max_iterations} iterations. Asking user to continue...", is_running=False)
                    live.update(monitor.layout)
                    live.stop()
                    
                    # Show current progress
                    rprint(Panel(
                        f"[bold]Iterations Completed:[/bold] {total_iterations_run}\n"
                        f"[bold]Successful Cycles:[/bold] {loop_results.get('successful_cycles', 0)}\n"
                        f"[bold]Failed Cycles:[/bold] {loop_results.get('failed_cycles', 0)}\n"
                        f"[bold]Revenue Generated:[/bold] ${loop_results.get('total_revenue_generated', 0.0):.2f}\n"
                        f"[bold]Status:[/bold] {loop_results.get('final_status', 'unknown')}",
                        title="[bold yellow]Mission Progress Update[/bold yellow]",
                        border_style="yellow"
                    ))
                    
                    # Ask user if they want to continue
                    continue_mission = Confirm.ask(
                        f"\n[bold cyan]Maximum iterations ({max_iterations}) reached. Continue with another {max_iterations} iterations?[/bold cyan]",
                        default=True
                    )
                    
                    if continue_mission:
                        # Restart live display and continue
                        live.start()
                        monitor.set_overall_status("Continuing C-Suite Orchestrated Mission...", is_running=True)
                        monitor.update(overall_mission_string)
                        
                        # Update mission context with latest results for next iteration batch
                        mission_context["previous_results"] = {
                            "total_iterations": total_iterations_run,
                            "revenue_generated": loop_results.get("total_revenue_generated", 0.0),
                            "successful_cycles": loop_results.get("successful_cycles", 0),
                            "failed_cycles": loop_results.get("failed_cycles", 0)
                        }
                        continue
                    else:
                        # User chose to stop
                        final_loop_results["final_status"] = "stopped_by_user"
                        break
                else:
                    # Mission completed naturally (success, failure, etc.)
                    break
            
            # Combine all results for final reporting
            combined_results = {
                **final_loop_results,
                "total_iterations": total_iterations_run,
                "execution_log": all_execution_logs,
                "csuite_decisions": all_csuite_decisions
            }
            
            # Update mission log with continuous loop results
            overall_log.total_mission_cost += combined_results.get("total_cost", 0.0)
            overall_log.final_status = combined_results.get("final_status", "completed")
            overall_log.last_activity_description = f"C-Suite orchestrated: {combined_results.get('successful_cycles', 0)} successful cycles, ${combined_results.get('total_revenue_generated', 0.0):.2f} revenue"
            
            # Convert continuous loop execution log to decision cycles format
            execution_log = combined_results.get("execution_log", [])
            for cycle_log in execution_log:
                cycle_summary = {
                    "cycle_id": f"csuite_cycle_{cycle_log.get('iteration', 0)}",
                    "timestamp": cycle_log.get("timestamp", datetime.now().isoformat()),
                    "decision_focus": f"C-Suite orchestrated iteration {cycle_log.get('iteration', 0)}",
                    "status": "success" if cycle_log.get("cycle_successful", False) else "failed",
                    "execution_output": {
                        "execution_type": "csuite_orchestrated",
                        "description": f"C-Suite planning + workflow execution: {', '.join(cycle_log.get('steps', {}).keys())}",
                        "output_data": {
                            "csuite_planning": cycle_log.get("csuite_planning", {}),
                            "workflow_steps": cycle_log.get("steps", {}),
                            "csuite_review": cycle_log.get("csuite_review", {}),
                            "revenue_generated": cycle_log.get("revenue_generated", 0.0),
                            "errors": cycle_log.get("errors", []),
                            "guardrail_status": cycle_log.get("guardrail_status", "OK")
                        }
                    },
                    "total_cycle_cost": calculate_cycle_cost(cycle_log),
                    "recommendation_text": f"C-Suite cycle {cycle_log.get('iteration', 0)} - Strategic planning + {len(cycle_log.get('steps', {}))} workflow agents"
                }
                overall_log.decision_cycles_summary.append(cycle_summary)
            
            # Update total decision cycles count
            overall_log.total_decision_cycles = len(overall_log.decision_cycles_summary)
            
            # Display final results
            if not live.is_started:
                live.start()
            monitor.set_overall_status(f"C-Suite Mission Complete: {combined_results.get('final_status', 'unknown')}", is_running=False)
            live.update(monitor.layout)
            live.stop()
            
            status_color = "green" if combined_results.get("status") == "completed" else "red"
            rprint(Panel(
                f"[bold]Mode:[/bold] C-Suite Orchestrated Mission\n"
                f"[bold]Status:[/bold] {combined_results.get('final_status', 'unknown')}\n"
                f"[bold]Total Iterations:[/bold] {combined_results.get('total_iterations', 0)}\n"
                f"[bold]Successful Cycles:[/bold] {combined_results.get('successful_cycles', 0)}\n"
                f"[bold]Failed Cycles:[/bold] {combined_results.get('failed_cycles', 0)}\n"
                f"[bold]Revenue Generated:[/bold] ${combined_results.get('total_revenue_generated', 0.0):.2f}\n"
                f"[bold]C-Suite Decisions:[/bold] {len(combined_results.get('csuite_decisions', []))}",
                title=f"[bold {status_color}]Final Mission Results[/bold {status_color}]",
                border_style=status_color
            ))
            
            if combined_results.get("error"):
                rprint(Panel(f"[bold red]Error:[/bold red] {combined_results.get('error')}", title="Execution Error"))

    except Exception as e:
        logger.error(f"Critical error during mission execution: {str(e)}", exc_info=True)
        console.print(f"[bold red]Critical error during mission execution:[/bold red] {str(e)}")
        if 'live' in locals() and live.is_started:
            live.stop()
        overall_log.final_status = "CRITICAL_ERROR"
        overall_log.error_message = str(e)
        sys.exit(1)
    finally:
        # Cancel timer task if it exists
        if 'timer_task' in locals() and not timer_task.done():
            timer_task.cancel()
            try:
                await timer_task
            except asyncio.CancelledError:
                pass
        
        if 'live' in locals() and live.is_started:
            live.stop()
        
        # Restore normal logging levels
        restore_external_loggers()
        
        if overall_log.final_status == "started":
            overall_log.final_status = "ended_unexpectedly"

        # Final update of context and token counts
        if 'monitor' in locals():
            overall_log.total_input_tokens = monitor.total_input_tokens
            overall_log.total_output_tokens = monitor.total_output_tokens
        overall_log.created_agents = list(orchestrator.agents.keys()) if 'orchestrator' in locals() else overall_log.created_agents

        overall_log.save_log()
        console.print(f"Overall mission log saved to mission_logs/{overall_log.mission_id}.json")
        
        # Properly close the enhanced client
        if 'enhanced_client' in locals():
            try:
                await enhanced_client.close()
                logger.debug("Enhanced OpenAI client closed successfully")
            except Exception as e:
                logger.warning(f"Error closing client: {e}")
        
        console.print("CLI session ended.")

@click.command()
@click.argument('mission', required=False)
@click.option('--debug', is_flag=True, help="Enable DEBUG level logging.")
@click.option('--new', is_flag=True, help="Force start a new mission (skip resume menu).")
@click.option('--max-iterations', default=10, help="Maximum iterations for continuous mode (default: 10).")
def main(mission: Optional[str] = None, debug: bool = False, new: bool = False, max_iterations: int = 10):
    """Run an autonomous business mission with C-Suite orchestration and workflow automation.
    
    The system runs in CONTINUOUS MODE where the C-Suite agents make strategic decisions
    and workflow agents provide operational support when needed.
    
    On startup, you'll see a menu to either resume a previous mission or start a new one.
    The system shows the 5 most recent missions with their status and progress.
    
    MISSION: Optional mission description. If not provided, you'll be prompted.
    
    Options:
    --debug: Enable detailed debug logging
    --new: Skip the resume menu and force start a new mission
    --max-iterations: Maximum iterations for continuous mode (default: 10)
    
    Examples:
    python orchestrator/cli.py                    # Standard C-Suite orchestrated mode
    python orchestrator/cli.py --new              # Force new mission
    python orchestrator/cli.py "Build an app"     # New mission with description
    """
    # Load environment variables from .env file in current working directory
    # This ensures the .env file is loaded from where the user runs the command
    import os
    current_dir = os.getcwd()
    env_file_path = os.path.join(current_dir, '.env')
    
    if debug:
        console.print(f"[dim]Debug: Looking for .env file at: {env_file_path}[/dim]")
        console.print(f"[dim]Debug: .env file exists: {os.path.exists(env_file_path)}[/dim]")
    
    # Load .env file if it exists, otherwise load_dotenv will just do nothing
    load_dotenv(dotenv_path=env_file_path)
    
    if debug:
        api_key_found = bool(os.environ.get("OPENAI_API_KEY"))
        console.print(f"[dim]Debug: OPENAI_API_KEY found after load_dotenv: {api_key_found}[/dim]")
    
    resume_mission_log = None
    
    # Show mission selection menu unless --new flag is used
    if not new:
        try:
            selected_mission_file = display_mission_selection_menu()
            if selected_mission_file:
                resume_mission_log = load_mission_log(selected_mission_file)
                if resume_mission_log:
                    mission = resume_mission_log.overall_mission
                    console.print(f"[green]Loaded mission: {mission}[/green]")
                else:
                    console.print("[red]Failed to load selected mission. Starting new mission...[/red]")
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled by user.[/yellow]")
            sys.exit(0)
    
    # Get mission string if not resuming
    if not mission:
        mission = Prompt.ask(
            "[bold cyan]Enter the overall business mission[/bold cyan]",
            default="Build a fully autonomous online business that earns its first paying customer asap and remains profitable."
        )
    
    agent_logger = AgentLogger()
    asyncio.run(run_mission_cli(mission, agent_logger, debug, resume_mission_log, True, max_iterations))

if __name__ == "__main__":
    main() 