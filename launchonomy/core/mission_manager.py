# orchestrator/mission_management.py

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

# Import the new workspace manager
from .workspace_manager import WorkspaceManager, WorkspaceConfig

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
    
    # Workspace integration
    workspace_path: Optional[str] = None
    workspace_config: Optional[Dict[str, Any]] = None

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
    Handles mission logging, persistence, and resumability using workspace system.
    
    This class manages the lifecycle of missions and cycles, providing
    functionality for creating, saving, loading, and linking mission data.
            All data is stored in mission-specific workspaces using the Mission Workspace System.
    """
    
    def __init__(self, workspace_base_dir: str = ".launchonomy"):
        self.current_mission_log: Optional[MissionLog] = None
        self.mission_logs: List[CycleLog] = []
        
        # Initialize workspace manager
        self.workspace_manager = WorkspaceManager(workspace_base_dir)

    def create_or_load_mission(self, mission_name: str, overall_mission: str, resume_existing: bool = True) -> MissionLog:
        """Create a new mission or load an existing one for resumable missions."""
        
        # Generate mission ID with timestamp first for chronological ordering
        import re
        safe_mission_name = re.sub(r'\W+', '_', mission_name.lower())
        mission_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_mission_{safe_mission_name}"
        
        # Try to find existing mission if resume_existing is True
        if resume_existing:
            existing_mission = self._find_existing_mission(mission_name, overall_mission)
            if existing_mission:
                logger.info(f"Resuming existing mission: {existing_mission.mission_id}")
                self.current_mission_log = existing_mission
                
                # Set current workspace if mission has one
                if existing_mission.workspace_path:
                    self.workspace_manager.set_current_workspace(existing_mission.mission_id)
                
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
        
        # Create mission workspace
        try:
            workspace_config = self.workspace_manager.create_workspace(
                mission_id=mission_id,
                mission_name=mission_name,
                overall_mission=overall_mission,
                tags=["mission", "active"]
            )
            
            # Link workspace to mission
            mission_log.workspace_path = workspace_config.workspace_path
            mission_log.workspace_config = {
                "workspace_path": workspace_config.workspace_path,
                "created_at": workspace_config.created_at,
                "status": workspace_config.status
            }
            
            logger.info(f"Created workspace for mission {mission_id} at {workspace_config.workspace_path}")
            
        except Exception as e:
            logger.error(f"Failed to create workspace for mission {mission_id}: {e}")
            # Continue without workspace if creation fails
            mission_log.workspace_path = None
            mission_log.workspace_config = None
        
        # Save mission log to workspace
        self._save_mission_log_to_workspace(mission_log)
        self.current_mission_log = mission_log
        return mission_log

    def _find_existing_mission(self, mission_name: str, overall_mission: str) -> Optional[MissionLog]:
        """Find an existing mission that matches the name and mission description."""
        # Look through all workspaces for matching missions
        workspaces = self.workspace_manager.list_workspaces(status_filter="active")
        
        for workspace in workspaces:
            if (workspace.mission_name == mission_name and 
                workspace.overall_mission == overall_mission):
                
                # Load mission log from workspace
                mission_log = self._load_mission_log_from_workspace(workspace.mission_id)
                if mission_log and mission_log.status in ["active", "paused"]:
                    return mission_log
        
        return None

    def _save_mission_log_to_workspace(self, mission_log: MissionLog):
        """Save mission log to workspace."""
        if not mission_log.workspace_path:
            logger.warning(f"No workspace path for mission {mission_log.mission_id}, cannot save mission log")
            return
        
        try:
            # Save to workspace state directory
            mission_log_file = os.path.join(mission_log.workspace_path, "state", "mission_log.json")
            os.makedirs(os.path.dirname(mission_log_file), exist_ok=True)
            
            with open(mission_log_file, "w") as f:
                json.dump(asdict(mission_log), f, indent=2)
            
            # Also save as an asset for easy access
            self.workspace_manager.save_asset(
                mission_id=mission_log.mission_id,
                asset_name="mission_log.json",
                asset_data=asdict(mission_log),
                asset_type="mission_log",
                category="logs"
            )
            
            logger.debug(f"Mission log saved to workspace: {mission_log_file}")
        except Exception as e:
            logger.error(f"Error saving mission log to workspace: {str(e)}")

    def _load_mission_log_from_workspace(self, mission_id: str) -> Optional[MissionLog]:
        """Load mission log from workspace."""
        workspace = self.workspace_manager.get_workspace(mission_id)
        if not workspace:
            return None
        
        try:
            mission_log_file = os.path.join(workspace.workspace_path, "state", "mission_log.json")
            if os.path.exists(mission_log_file):
                with open(mission_log_file, 'r') as f:
                    data = json.load(f)
                return MissionLog(**data)
        except Exception as e:
            logger.error(f"Error loading mission log from workspace: {str(e)}")
        
        return None

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
        if cycle_log.status == "success":
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
        
        # Extract key learnings from successful cycles
        if cycle_log.status == "success" and cycle_log.kpi_outcomes:
            learning = f"Cycle {len(self.current_mission_log.cycle_summaries)}: {cycle_log.current_decision_focus} - {cycle_log.kpi_outcomes.get('summary', 'Completed successfully')}"
            self.current_mission_log.key_learnings.append(learning)
        
        # Update persistent agents list
        for agent in cycle_log.agents_used:
            if agent not in self.current_mission_log.persistent_agents:
                self.current_mission_log.persistent_agents.append(agent)
        
        # Save updated mission log to workspace
        self._save_mission_log_to_workspace(self.current_mission_log)

    def link_cycle_to_previous(self, cycle_log: CycleLog) -> CycleLog:
        """Link a cycle to the previous cycle in the mission for resumable context."""
        if not self.current_mission_log:
            logger.warning("No current mission log to link cycle to")
            return cycle_log
        
        # Set parent mission ID
        cycle_log.parent_mission_id = self.current_mission_log.mission_id
        
        # Set sequence number
        cycle_log.cycle_sequence_number = len(self.current_mission_log.cycle_ids) + 1
        
        # Link to previous cycle if exists
        if self.current_mission_log.current_cycle_id:
            cycle_log.previous_cycle_id = self.current_mission_log.current_cycle_id
            
            # Update previous cycle's next_cycle_id in workspace
            self._update_previous_cycle_link_in_workspace(
                self.current_mission_log.current_cycle_id, 
                cycle_log.mission_id
            )
        
        # Add context from previous cycles (last 3 cycles for efficiency)
        recent_cycles = self.current_mission_log.cycle_summaries[-3:] if self.current_mission_log.cycle_summaries else []
        cycle_log.previous_cycles_context = recent_cycles
        
        # Extract key insights from previous cycles
        cycle_log.key_insights_from_previous = self.current_mission_log.key_learnings[-5:] if self.current_mission_log.key_learnings else []
        
        return cycle_log

    def _update_previous_cycle_link_in_workspace(self, previous_cycle_id: str, current_cycle_id: str):
        """Update the previous cycle's next_cycle_id field in workspace."""
        if not self.current_mission_log or not self.current_mission_log.workspace_path:
            return
        
        try:
            # Load previous cycle log from workspace
            previous_cycle_file = os.path.join(
                self.current_mission_log.workspace_path, 
                "logs", "cycles", 
                f"{previous_cycle_id}.json"
            )
            
            if os.path.exists(previous_cycle_file):
                with open(previous_cycle_file, 'r') as f:
                    cycle_data = json.load(f)
                
                cycle_data["next_cycle_id"] = current_cycle_id
                
                with open(previous_cycle_file, 'w') as f:
                    json.dump(cycle_data, f, indent=2)
                
                logger.debug(f"Updated previous cycle {previous_cycle_id} with next_cycle_id: {current_cycle_id}")
        except Exception as e:
            logger.warning(f"Error updating previous cycle link in workspace: {str(e)}")

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
            "mission_status": self.current_mission_log.status,
            "workspace_path": self.current_mission_log.workspace_path
        }

    def get_previous_cycles_context(self, limit: int = 5) -> List[dict]:
        """Get context from previous cycles for informed decision-making."""
        if not self.current_mission_log:
            return []
        
        return self.current_mission_log.cycle_summaries[-limit:] if self.current_mission_log.cycle_summaries else []

    def get_mission_summary(self) -> Optional[dict]:
        """Get a comprehensive summary of the current mission."""
        if not self.current_mission_log:
            return None
        
        workspace_summary = self.get_workspace_summary()
        
        return {
            "mission_id": self.current_mission_log.mission_id,
            "mission_name": self.current_mission_log.mission_name,
            "overall_mission": self.current_mission_log.overall_mission,
            "status": self.current_mission_log.status,
            "started": self.current_mission_log.start_timestamp,
            "last_updated": self.current_mission_log.last_updated,
            "cycles_completed": self.current_mission_log.completed_cycles,
            "cycles_failed": self.current_mission_log.failed_cycles,
            "total_cost": self.current_mission_log.total_mission_cost,
            "total_time_minutes": self.current_mission_log.total_mission_time_minutes,
            "persistent_agents": self.current_mission_log.persistent_agents,
            "key_learnings": self.current_mission_log.key_learnings,
            "workspace_summary": workspace_summary
        }

    # Workspace integration methods
    def add_agent_to_mission_workspace(self, agent_name: str, agent_spec: Dict[str, Any], agent_code: Optional[str] = None) -> bool:
        """Add an agent to the current mission workspace."""
        if not self.current_mission_log:
            logger.warning("No current mission log, cannot add agent to workspace")
            return False
        
        return self.workspace_manager.add_agent_to_workspace(
            mission_id=self.current_mission_log.mission_id,
            agent_name=agent_name,
            agent_spec=agent_spec,
            agent_code=agent_code
        )
    
    def add_tool_to_mission_workspace(self, tool_name: str, tool_spec: Dict[str, Any], tool_code: Optional[str] = None) -> bool:
        """Add a tool to the current mission workspace."""
        if not self.current_mission_log:
            logger.warning("No current mission log, cannot add tool to workspace")
            return False
        
        return self.workspace_manager.add_tool_to_workspace(
            mission_id=self.current_mission_log.mission_id,
            tool_name=tool_name,
            tool_spec=tool_spec,
            tool_code=tool_code
        )
    
    def save_mission_asset(self, asset_name: str, asset_data: Any, asset_type: str = "file", category: str = "general") -> Optional[str]:
        """Save an asset to the current mission workspace."""
        if not self.current_mission_log:
            logger.warning("No current mission log, cannot save asset")
            return None
        
        return self.workspace_manager.save_asset(
            mission_id=self.current_mission_log.mission_id,
            asset_name=asset_name,
            asset_data=asset_data,
            asset_type=asset_type,
            category=category
        )
    
    def save_mission_state_to_workspace(self, state_data: dict, checkpoint_name: str = "checkpoint"):
        """Save mission state to workspace."""
        if not self.current_mission_log:
            logger.warning("No current mission log, cannot save state")
            return
        
        self.workspace_manager.save_mission_state(
            mission_id=self.current_mission_log.mission_id,
            state_data=state_data,
            checkpoint_name=checkpoint_name
        )
    
    def load_mission_state_from_workspace(self, checkpoint_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load mission state from the workspace."""
        if not self.current_mission_log or not self.current_mission_log.workspace_path:
            logger.warning("No active mission workspace to load state from")
            return None
        
        return self.workspace_manager.load_mission_state(
            mission_id=self.current_mission_log.mission_id,
            checkpoint_name=checkpoint_name
        )
    
    def get_workspace_summary(self) -> Optional[dict]:
        """Get a comprehensive summary of the current mission workspace."""
        if not self.current_mission_log or not self.current_mission_log.workspace_path:
            return None
        
        return self.workspace_manager.get_workspace_summary(self.current_mission_log.mission_id)
    
    def archive_mission_workspace(self) -> bool:
        """Archive the current mission's workspace."""
        if not self.current_mission_log or not self.current_mission_log.workspace_path:
            logger.warning("No active mission workspace to archive")
            return False
        
        success = self.workspace_manager.archive_workspace(self.current_mission_log.mission_id)
        
        if success and self.current_mission_log:
            # Update mission status
            self.current_mission_log.status = "archived"
            self.current_mission_log.last_updated = datetime.now().isoformat()
            self._save_mission_log_to_workspace(self.current_mission_log)
        
        return success

    def save_cycle_log_to_workspace(self, cycle_log: CycleLog) -> bool:
        """Save a cycle log to the mission workspace."""
        if not self.current_mission_log or not self.current_mission_log.workspace_path:
            logger.warning("No active mission workspace to save cycle log to")
            return False
        
        try:
            # Save to workspace logs/cycles directory
            cycles_dir = os.path.join(self.current_mission_log.workspace_path, "logs", "cycles")
            os.makedirs(cycles_dir, exist_ok=True)
            
            cycle_file = os.path.join(cycles_dir, f"{cycle_log.mission_id}.json")
            with open(cycle_file, "w") as f:
                json.dump(asdict(cycle_log), f, indent=2)
            
            # Also save as an asset
            self.workspace_manager.save_asset(
                mission_id=self.current_mission_log.mission_id,
                asset_name=f"cycle_{cycle_log.mission_id}.json",
                asset_data=asdict(cycle_log),
                asset_type="cycle_log",
                category="logs"
            )
            
            logger.info(f"Cycle log saved to workspace: {cycle_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving cycle log to workspace: {str(e)}")
            return False

    def list_all_missions(self) -> List[Dict[str, Any]]:
        """List all missions from workspaces."""
        missions = []
        
        try:
            workspaces = self.workspace_manager.list_workspaces()
            
            for workspace in workspaces:
                # Try to load mission log from workspace
                mission_log_file = os.path.join(workspace.workspace_path, "state", "mission_log.json")
                
                if os.path.exists(mission_log_file):
                    try:
                        with open(mission_log_file, 'r') as f:
                            mission_data = json.load(f)
                        
                        mission_info = {
                            "mission_id": mission_data.get("mission_id", workspace.mission_id),
                            "overall_mission": mission_data.get("overall_mission", workspace.mission_name),
                            "status": mission_data.get("status", workspace.status),
                            "cycles_completed": mission_data.get("completed_cycles", 0),
                            "total_cost": mission_data.get("total_mission_cost", 0.0),
                            "started": mission_data.get("start_timestamp", workspace.created_at),
                            "last_updated": mission_data.get("last_updated", workspace.created_at),
                            "workspace_path": workspace.workspace_path,
                            "key_learnings": mission_data.get("key_learnings", [])
                        }
                        
                        missions.append(mission_info)
                        
                    except Exception as e:
                        logger.warning(f"Error reading mission log from workspace {workspace.mission_id}: {e}")
                        # Create basic info from workspace config
                        mission_info = {
                            "mission_id": workspace.mission_id,
                            "overall_mission": workspace.mission_name,
                            "status": workspace.status,
                            "cycles_completed": 0,
                            "total_cost": 0.0,
                            "started": workspace.created_at,
                            "last_updated": workspace.created_at,
                            "workspace_path": workspace.workspace_path,
                            "key_learnings": []
                        }
                        
                        missions.append(mission_info)
                else:
                    # Create basic info from workspace config if no mission log
                    mission_info = {
                        "mission_id": workspace.mission_id,
                        "overall_mission": workspace.mission_name,
                        "status": workspace.status,
                        "cycles_completed": 0,
                        "total_cost": 0.0,
                        "started": workspace.created_at,
                        "last_updated": workspace.created_at,
                        "workspace_path": workspace.workspace_path,
                        "key_learnings": []
                    }
                    
                    missions.append(mission_info)
            
            # Sort by last_updated (most recent first)
            missions.sort(key=lambda x: x["last_updated"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error listing missions from workspaces: {e}")
        
        return missions 