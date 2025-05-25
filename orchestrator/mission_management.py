# orchestrator/mission_management.py

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)

@dataclass
class MissionLog:
    """Master mission log that tracks all cycles and provides context for resumable missions."""
    mission_name: str
    mission_id: str
    overall_mission: str
    start_timestamp: str
    last_updated: str
    status: str  # "active", "paused", "completed", "failed"
    
    # Cycle tracking
    cycle_ids: List[str] = field(default_factory=list)
    current_cycle_id: Optional[str] = None
    completed_cycles: int = 0
    failed_cycles: int = 0
    
    # Mission-level metrics
    total_mission_cost: float = 0.0
    total_mission_time_minutes: float = 0.0
    
    # Context for resumption
    mission_context: dict = field(default_factory=dict)
    key_learnings: List[str] = field(default_factory=list)
    persistent_agents: List[str] = field(default_factory=list)
    
    # Linking and history
    cycle_summaries: List[dict] = field(default_factory=list)
    mission_milestones: List[dict] = field(default_factory=list)
    
    # Metadata
    created_by: str = "OrchestrationAgent"
    tags: List[str] = field(default_factory=list)

@dataclass
class CycleLog:
    """
    Detailed log for a single decision cycle within a mission.
    
    This class tracks all interactions, costs, and outcomes for a single
    decision-making cycle in the orchestration process.
    """
    mission_id: str
    timestamp: str
    overall_mission: str
    current_decision_focus: str
    status: str
    error_message: Optional[str] = None
    
    agent_management_events: List[dict] = field(default_factory=list)
    orchestrator_interactions: List[dict] = field(default_factory=list)
    specialist_interactions: List[dict] = field(default_factory=list)
    review_interactions: List[dict] = field(default_factory=list)
    execution_attempts: List[dict] = field(default_factory=list)
    
    json_parsing_attempts: List[dict] = field(default_factory=list)

    decisions_archive: List[dict] = field(default_factory=list)
    reviews_archive: List[dict] = field(default_factory=list)
    
    kpi_outcomes: dict = field(default_factory=dict)
    total_loops_in_decision_cycle: int = 0
    total_cycle_cost: float = 0.0

    # Enhanced linking for resumable missions
    previous_cycle_id: Optional[str] = None
    next_cycle_id: Optional[str] = None
    parent_mission_id: Optional[str] = None
    cycle_sequence_number: int = 0
    
    # Context from previous cycles
    previous_cycles_context: List[dict] = field(default_factory=list)
    key_insights_from_previous: List[str] = field(default_factory=list)
    
    # Cycle-specific metadata
    cycle_duration_minutes: float = 0.0
    agents_used: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)

class MissionManager:
    """
    Handles mission logging, persistence, and resumability.
    
    This class manages the lifecycle of missions and cycles, providing
    functionality for creating, saving, loading, and linking mission data.
    """
    
    def __init__(self):
        self.current_mission_log: Optional[MissionLog] = None
        self.mission_logs: List[CycleLog] = []

    def create_or_load_mission(self, mission_name: str, overall_mission: str, resume_existing: bool = True) -> MissionLog:
        """Create a new mission or load an existing one for resumable missions."""
        mission_log_dir = "mission_logs"
        os.makedirs(mission_log_dir, exist_ok=True)
        
        # Generate mission ID based on name and timestamp
        import re
        safe_mission_name = re.sub(r'\W+', '_', mission_name.lower())
        mission_id = f"mission_{safe_mission_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        mission_file_path = os.path.join(mission_log_dir, f"{mission_id}.json")
        
        # Try to find existing mission if resume_existing is True
        if resume_existing:
            existing_mission = self._find_existing_mission(mission_name, overall_mission)
            if existing_mission:
                logger.info(f"Resuming existing mission: {existing_mission.mission_id}")
                self.current_mission_log = existing_mission
                return existing_mission
        
        # Create new mission
        logger.info(f"Creating new mission: {mission_id}")
        mission_log = MissionLog(
            mission_name=mission_name,
            mission_id=mission_id,
            overall_mission=overall_mission,
            start_timestamp=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            status="active",
            mission_context={"overall_mission": overall_mission},
            persistent_agents=[]
        )
        
        # Save mission log
        self._save_mission_log(mission_log)
        self.current_mission_log = mission_log
        return mission_log

    def _find_existing_mission(self, mission_name: str, overall_mission: str) -> Optional[MissionLog]:
        """Find an existing mission that matches the name and mission description."""
        mission_log_dir = "mission_logs"
        if not os.path.exists(mission_log_dir):
            return None
        
        # Look for mission files (not cycle files)
        for filename in os.listdir(mission_log_dir):
            if filename.startswith("mission_") and filename.endswith(".json") and not filename.startswith("cycle_"):
                try:
                    file_path = os.path.join(mission_log_dir, filename)
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    # Check if this matches our mission
                    if (data.get("mission_name") == mission_name and 
                        data.get("overall_mission") == overall_mission and
                        data.get("status") in ["active", "paused"]):
                        
                        # Convert to MissionLog object
                        mission_log = MissionLog(**data)
                        return mission_log
                        
                except Exception as e:
                    logger.warning(f"Error reading mission file {filename}: {str(e)}")
                    continue
        
        return None

    def _save_mission_log(self, mission_log: MissionLog):
        """Save mission log to disk."""
        mission_log_dir = "mission_logs"
        os.makedirs(mission_log_dir, exist_ok=True)
        
        mission_file_path = os.path.join(mission_log_dir, f"{mission_log.mission_id}.json")
        try:
            with open(mission_file_path, "w") as f:
                json.dump(asdict(mission_log), f, indent=2)
            logger.debug(f"Mission log saved to {mission_file_path}")
        except Exception as e:
            logger.error(f"Error saving mission log {mission_file_path}: {str(e)}")

    def update_mission_log(self, cycle_log: CycleLog):
        """Update the current mission log with information from a completed cycle."""
        if not self.current_mission_log:
            logger.warning("No current mission log to update")
            return
        
        # Update mission log with cycle information
        self.current_mission_log.cycle_ids.append(cycle_log.mission_id)
        self.current_mission_log.current_cycle_id = cycle_log.mission_id
        self.current_mission_log.last_updated = datetime.now().isoformat()
        self.current_mission_log.total_mission_cost += cycle_log.total_cycle_cost
        self.current_mission_log.total_mission_time_minutes += cycle_log.cycle_duration_minutes
        
        # Update cycle counts
        if cycle_log.status == "completed_cycle_success":
            self.current_mission_log.completed_cycles += 1
        else:
            self.current_mission_log.failed_cycles += 1
        
        # Add cycle summary for context
        cycle_summary = {
            "cycle_id": cycle_log.mission_id,
            "decision_focus": cycle_log.current_decision_focus,
            "status": cycle_log.status,
            "cost": cycle_log.total_cycle_cost,
            "duration_minutes": cycle_log.cycle_duration_minutes,
            "agents_used": cycle_log.agents_used,
            "key_outcomes": cycle_log.kpi_outcomes,
            "timestamp": cycle_log.timestamp
        }
        self.current_mission_log.cycle_summaries.append(cycle_summary)
        
        # Extract key learnings from retrospective if available
        for interaction in cycle_log.orchestrator_interactions:
            if interaction.get("type") == "retrospective_analysis" and interaction.get("parsed_output"):
                # Extract actionable recommendations from retrospective
                retro_text = interaction["parsed_output"]
                if "Key Learnings" in retro_text or "Actionable Recommendations" in retro_text:
                    learning_entry = f"Cycle {len(self.current_mission_log.cycle_ids)}: {retro_text.split('Key Learnings')[1].split('Actionable Recommendations')[0].strip() if 'Key Learnings' in retro_text else 'General insights from cycle'}"
                    self.current_mission_log.key_learnings.append(learning_entry)
        
        # Save updated mission log
        self._save_mission_log(self.current_mission_log)

    def get_previous_cycles_context(self, limit: int = 5) -> List[dict]:
        """Get context from previous cycles for the current mission."""
        if not self.current_mission_log:
            return []
        
        # Return the most recent cycle summaries (up to limit)
        return self.current_mission_log.cycle_summaries[-limit:] if self.current_mission_log.cycle_summaries else []

    def link_cycle_to_previous(self, current_cycle: CycleLog) -> CycleLog:
        """Link the current cycle to the previous cycle and add context."""
        if not self.current_mission_log:
            return current_cycle
        
        # Set parent mission
        current_cycle.parent_mission_id = self.current_mission_log.mission_id
        current_cycle.cycle_sequence_number = len(self.current_mission_log.cycle_ids) + 1
        
        # Link to previous cycle
        if self.current_mission_log.cycle_ids:
            previous_cycle_id = self.current_mission_log.cycle_ids[-1]
            current_cycle.previous_cycle_id = previous_cycle_id
            
            # Update the previous cycle's next_cycle_id
            self._update_previous_cycle_link(previous_cycle_id, current_cycle.mission_id)
        
        # Add context from previous cycles
        current_cycle.previous_cycles_context = self.get_previous_cycles_context()
        
        # Add key insights from mission learnings
        current_cycle.key_insights_from_previous = self.current_mission_log.key_learnings[-3:] if self.current_mission_log.key_learnings else []
        
        return current_cycle

    def _update_previous_cycle_link(self, previous_cycle_id: str, current_cycle_id: str):
        """Update the previous cycle's next_cycle_id field."""
        log_dir = "mission_logs"
        previous_cycle_file = os.path.join(log_dir, f"{previous_cycle_id}.json")
        
        if os.path.exists(previous_cycle_file):
            try:
                with open(previous_cycle_file, 'r') as f:
                    cycle_data = json.load(f)
                
                cycle_data["next_cycle_id"] = current_cycle_id
                
                with open(previous_cycle_file, 'w') as f:
                    json.dump(cycle_data, f, indent=2)
                
                logger.debug(f"Updated previous cycle {previous_cycle_id} with next_cycle_id: {current_cycle_id}")
            except Exception as e:
                logger.warning(f"Error updating previous cycle link: {str(e)}")

    def get_mission_context_for_agents(self) -> dict:
        """Get comprehensive mission context for agent decision-making."""
        if not self.current_mission_log:
            return {}
        
        return {
            "mission_id": self.current_mission_log.mission_id,
            "overall_mission": self.current_mission_log.overall_mission,
            "cycles_completed": self.current_mission_log.completed_cycles,
            "total_cost_so_far": self.current_mission_log.total_mission_cost,
            "key_learnings": self.current_mission_log.key_learnings,
            "recent_cycles": self.get_previous_cycles_context(3),
            "persistent_agents": self.current_mission_log.persistent_agents,
            "mission_status": self.current_mission_log.status
        } 