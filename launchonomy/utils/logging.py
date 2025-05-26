import logging
import os # For _log when not in class context, if needed
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field, asdict
import json
from enum import Enum

logger = logging.getLogger(__name__) # For module-level logging if any

# Enhanced logging with AutoGen v0.4 patterns
class LogLevel(Enum):
    """Standardized log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Categorize errors for better handling."""
    COMMUNICATION = "communication"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    SYSTEM = "system"
    USER_INPUT = "user_input"

@dataclass
class StructuredLogEntry:
    """Structured log entry for better analysis."""
    timestamp: str
    level: LogLevel
    component: str
    message: str
    context: Optional[Dict[str, Any]] = None
    error_category: Optional[ErrorCategory] = None
    agent_id: Optional[str] = None
    cost: Optional[float] = None
    tokens_used: Optional[int] = None

class EnhancedLogger:
    """Enhanced logging with AutoGen v0.4 improvements."""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.logger = logging.getLogger(component_name)
        self.structured_logs: List[StructuredLogEntry] = []
    
    def _create_entry(self, level: LogLevel, message: str, **kwargs) -> StructuredLogEntry:
        """Create structured log entry."""
        return StructuredLogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            component=self.component_name,
            message=message,
            **kwargs
        )
    
    def debug(self, message: str, **kwargs):
        """Enhanced debug logging."""
        entry = self._create_entry(LogLevel.DEBUG, message, **kwargs)
        self.structured_logs.append(entry)
        self.logger.debug(f"[{self.component_name}] {message}")
    
    def info(self, message: str, **kwargs):
        """Enhanced info logging."""
        entry = self._create_entry(LogLevel.INFO, message, **kwargs)
        self.structured_logs.append(entry)
        self.logger.info(f"[{self.component_name}] {message}")
    
    def warning(self, message: str, error_category: Optional[ErrorCategory] = None, **kwargs):
        """Enhanced warning logging with categorization."""
        entry = self._create_entry(LogLevel.WARNING, message, error_category=error_category, **kwargs)
        self.structured_logs.append(entry)
        self.logger.warning(f"[{self.component_name}] {message}")
    
    def error(self, message: str, error_category: Optional[ErrorCategory] = None, **kwargs):
        """Enhanced error logging with categorization."""
        entry = self._create_entry(LogLevel.ERROR, message, error_category=error_category, **kwargs)
        self.structured_logs.append(entry)
        self.logger.error(f"[{self.component_name}] {message}")
    
    def critical(self, message: str, error_category: Optional[ErrorCategory] = None, **kwargs):
        """Enhanced critical logging."""
        entry = self._create_entry(LogLevel.CRITICAL, message, error_category=error_category, **kwargs)
        self.structured_logs.append(entry)
        self.logger.critical(f"[{self.component_name}] {message}")
    
    def log_agent_interaction(self, agent_id: str, message: str, cost: float = 0.0, tokens: int = 0):
        """Log agent interactions with cost tracking."""
        self.info(
            f"Agent interaction: {message}",
            agent_id=agent_id,
            cost=cost,
            tokens_used=tokens
        )
    
    def log_error_with_context(self, error: Exception, context: Dict[str, Any], category: ErrorCategory):
        """Log errors with full context for debugging."""
        self.error(
            f"Error occurred: {str(error)}",
            error_category=category,
            context={
                **context,
                "error_type": type(error).__name__,
                "error_details": str(error)
            }
        )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors by category."""
        error_counts = {}
        for entry in self.structured_logs:
            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL] and entry.error_category:
                category = entry.error_category.value
                error_counts[category] = error_counts.get(category, 0) + 1
        
        return {
            "total_errors": len([e for e in self.structured_logs if e.level in [LogLevel.ERROR, LogLevel.CRITICAL]]),
            "by_category": error_counts,
            "recent_errors": [
                asdict(e) for e in self.structured_logs[-10:] 
                if e.level in [LogLevel.ERROR, LogLevel.CRITICAL]
            ]
        }
    
    def export_logs(self, filepath: str):
        """Export structured logs to file."""
        with open(filepath, 'w') as f:
            json.dump([asdict(entry) for entry in self.structured_logs], f, indent=2)

# Renamed from MissionLog to OverallMissionLog
@dataclass
class OverallMissionLog:
    mission_id: str
    timestamp: str # ISO format timestamp for the start of the mission log
    overall_mission: str
    # Fields to store aggregated results from all decision cycles
    final_status: str = "Initialized" # e.g., "In Progress", "Completed", "Failed", "Halted"
    total_mission_cost: float = 0.0
    total_decision_cycles: int = 0
    # Token tracking
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    # Log of all decision cycles that occurred during the mission
    decision_cycles_summary: List[Dict[str, Any]] = field(default_factory=list)
    # Orchestrator context for resume
    created_agents: List[str] = field(default_factory=list) # List of agent names that were created
    current_decision_focus: Optional[str] = None # Last decision focus being worked on
    last_activity_description: Optional[str] = None # Human-readable description of last activity
    # Detailed logs if needed, or these can be part of each cycle_summary
    # For example, keeping the detailed logs within each cycle in decision_cycles_summary might be cleaner
    # agent_management_events: List[dict] = field(default_factory=list) 
    # orchestrator_interactions: List[dict] = field(default_factory=list)
    # specialist_interactions: List[dict] = field(default_factory=list)
    # review_interactions: List[dict] = field(default_factory=list)
    # execution_attempts: List[dict] = field(default_factory=list)
    # json_parsing_attempts: List[dict] = field(default_factory=list)
    kpi_outcomes: Dict[str, Any] = field(default_factory=dict) # Final KPIs achieved
    error_message: Optional[str] = None # If the mission failed overall
    retrospective_analysis: Optional[Dict[str, Any]] = field(default_factory=dict) # For storing insights from RetrospectiveAgent

    # Method to save the log to a file
    def save_log(self, mission_id: Optional[str] = None):
        log_id = mission_id if mission_id else self.mission_id
        # Ensure mission_logs directory exists
        if not os.path.exists("mission_logs"):
            os.makedirs("mission_logs")
        # Fallback for nested structure if running from parent
        elif not os.path.exists("../mission_logs") and os.path.basename(os.getcwd()) == "orchestrator":
             if not os.path.exists("../mission_logs"):
                os.makedirs("../mission_logs")
             log_file_path = os.path.join("..", "mission_logs", f"{log_id}.json")
        else:
            log_file_path = os.path.join("mission_logs", f"{log_id}.json")
        
        # If still not found (e.g. running from autogen/autogen)
        if not os.path.exists(os.path.dirname(log_file_path)):
            alt_path = os.path.join("orchestrator", "mission_logs")
            if not os.path.exists(alt_path):
                 os.makedirs(alt_path)
            log_file_path = os.path.join(alt_path, f"{log_id}.json")

        try:
            with open(log_file_path, 'w') as f:
                json.dump(asdict(self), f, indent=4)
            # Global logger, not class-specific logger here unless passed
            logging.info(f"Mission log saved to {log_file_path}") 
        except (IOError, OSError, PermissionError, json.JSONEncodeError) as e:
            logging.error(f"Failed to save mission log {log_id}: {e}")

# Generic Log function (can be part of OrchestratorAgent or a utility)
# If it's used by OrchestratorAgent instance, it should be a method of that class
# to use self.log_callback and self.name correctly.
# For now, placing a slightly adapted version here for completeness if needed elsewhere,
# but the primary _log method should remain in OrchestratorAgent or be passed its context.

def log_message(log_callback: Optional[Any], logger_instance: logging.Logger, source_name: str, message: str, msg_type: str = "info"):
    """Log a message using a callback and standard logger."""
    if not isinstance(message, str):
        try:
            message = str(message)
        except (TypeError, ValueError, AttributeError) as e:
            message = f"Failed to convert log message to string: {e}"

    if log_callback:
        log_callback(source_name, message, msg_type)
    
    # Standard logging
    if msg_type == "error":
        logger_instance.error(f"{source_name}: {message}")
    elif msg_type == "warning":
        logger_instance.warning(f"{source_name}: {message}")
    elif msg_type == "debug":
        logger_instance.debug(f"{source_name}: {message}")
    else:
        logger_instance.info(f"{source_name}: {message}")

# Helper for timestamp, can be static or a global utility
def get_timestamp() -> str:
    return datetime.now().isoformat() 