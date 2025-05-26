"""
Mission Workspace Manager for Launchonomy.

This module provides filesystem-based workspace management for missions,
creating organized directories for mission-specific agents, tools, assets,
and state management.
"""

import os
import json
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)

@dataclass
class WorkspaceConfig:
    """Configuration for a mission workspace."""
    mission_id: str
    mission_name: str
    overall_mission: str
    created_at: str
    workspace_path: str
    status: str = "active"  # active, paused, completed, archived
    
    # Directory structure
    agents_dir: str = "agents"
    tools_dir: str = "tools" 
    assets_dir: str = "assets"
    logs_dir: str = "logs"
    state_dir: str = "state"
    docs_dir: str = "docs"
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    last_updated: Optional[str] = None

@dataclass
class AssetManifest:
    """Manifest tracking all assets in a mission workspace."""
    mission_id: str
    created_at: str
    last_updated: str
    
    # Asset categories
    agents: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tools: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    generated_files: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    external_resources: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Metrics
    total_assets: int = 0
    storage_size_mb: float = 0.0

class WorkspaceManager:
    """
    Manages mission-specific workspaces on the filesystem.
    
    Creates organized directory structures for each mission containing:
    - Mission-specific agents and tools
    - Generated assets (code, configs, data)
    - Mission state and progress tracking
    - Logs and documentation
    - External resources and dependencies
    
    Features:
    - Automatic workspace creation and cleanup
    - Asset tracking and manifest management
    - Integration with existing mission management
    - Workspace archiving and restoration
    - Cross-mission asset sharing
    """
    
    def __init__(self, base_workspace_dir: str = ".launchonomy"):
        """
        Initialize the workspace manager.
        
        Args:
            base_workspace_dir: Base directory for all mission workspaces
        """
        self.base_dir = Path(base_workspace_dir).resolve()
        self.workspaces: Dict[str, WorkspaceConfig] = {}
        self.current_workspace: Optional[str] = None
        
        # Ensure base directory exists
        self.base_dir.mkdir(exist_ok=True)
        
        # Load existing workspaces
        self._load_existing_workspaces()
        
        logger.info(f"WorkspaceManager initialized with base directory: {self.base_dir}")
    
    def _load_existing_workspaces(self):
        """Load existing workspace configurations."""
        try:
            for item in self.base_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    config_file = item / "workspace_config.json"
                    if config_file.exists():
                        with open(config_file, 'r') as f:
                            config_data = json.load(f)
                            config = WorkspaceConfig(**config_data)
                            self.workspaces[config.mission_id] = config
                            logger.debug(f"Loaded workspace: {config.mission_id}")
        except Exception as e:
            logger.error(f"Error loading existing workspaces: {e}")
    
    def create_workspace(self, mission_id: str, mission_name: str, overall_mission: str, 
                        tags: Optional[List[str]] = None) -> WorkspaceConfig:
        """
        Create a new mission workspace.
        
        Args:
            mission_id: Unique mission identifier
            mission_name: Human-readable mission name
            overall_mission: Mission description
            tags: Optional tags for categorization
            
        Returns:
            WorkspaceConfig for the created workspace
        """
        # Sanitize mission name for filesystem
        safe_name = self._sanitize_name(mission_name)
        workspace_path = self.base_dir / f"{mission_id}_{safe_name}"
        
        # Create workspace config
        config = WorkspaceConfig(
            mission_id=mission_id,
            mission_name=mission_name,
            overall_mission=overall_mission,
            created_at=datetime.now().isoformat(),
            workspace_path=str(workspace_path),
            tags=tags or [],
            description=overall_mission
        )
        
        # Create directory structure
        self._create_directory_structure(workspace_path, config)
        
        # Save workspace config
        self._save_workspace_config(config)
        
        # Create initial asset manifest
        self._create_asset_manifest(config)
        
        # Register workspace
        self.workspaces[mission_id] = config
        self.current_workspace = mission_id
        
        logger.info(f"Created workspace for mission: {mission_id} at {workspace_path}")
        return config
    
    def _create_directory_structure(self, workspace_path: Path, config: WorkspaceConfig):
        """Create the standard directory structure for a mission workspace."""
        workspace_path.mkdir(exist_ok=True)
        
        # Create standard directories
        directories = [
            config.agents_dir,
            config.tools_dir,
            config.assets_dir,
            config.logs_dir,
            config.state_dir,
            config.docs_dir,
            f"{config.assets_dir}/code",
            f"{config.assets_dir}/data",
            f"{config.assets_dir}/configs",
            f"{config.assets_dir}/media",
            f"{config.state_dir}/checkpoints",
            f"{config.state_dir}/progress",
            f"{config.logs_dir}/agents",
            f"{config.logs_dir}/cycles",
            f"{config.docs_dir}/generated",
            f"{config.docs_dir}/templates"
        ]
        
        for dir_name in directories:
            (workspace_path / dir_name).mkdir(parents=True, exist_ok=True)
        
        # Create README
        readme_content = self._generate_workspace_readme(config)
        (workspace_path / "README.md").write_text(readme_content)
        
        # Create .gitignore
        gitignore_content = self._generate_gitignore()
        (workspace_path / ".gitignore").write_text(gitignore_content)
    
    def _save_workspace_config(self, config: WorkspaceConfig):
        """Save workspace configuration to file."""
        config_path = Path(config.workspace_path) / "workspace_config.json"
        config.last_updated = datetime.now().isoformat()
        
        with open(config_path, 'w') as f:
            json.dump(asdict(config), f, indent=2)
    
    def _create_asset_manifest(self, config: WorkspaceConfig):
        """Create initial asset manifest for the workspace."""
        manifest = AssetManifest(
            mission_id=config.mission_id,
            created_at=config.created_at,
            last_updated=datetime.now().isoformat()
        )
        
        manifest_path = Path(config.workspace_path) / "asset_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(asdict(manifest), f, indent=2)
    
    def get_workspace(self, mission_id: str) -> Optional[WorkspaceConfig]:
        """Get workspace configuration for a mission."""
        return self.workspaces.get(mission_id)
    
    def set_current_workspace(self, mission_id: str) -> bool:
        """Set the current active workspace."""
        if mission_id in self.workspaces:
            self.current_workspace = mission_id
            logger.info(f"Set current workspace to: {mission_id}")
            return True
        return False
    
    def get_current_workspace(self) -> Optional[WorkspaceConfig]:
        """Get the current active workspace configuration."""
        if self.current_workspace:
            return self.workspaces.get(self.current_workspace)
        return None
    
    def add_agent_to_workspace(self, mission_id: str, agent_name: str, 
                              agent_spec: Dict[str, Any], agent_code: Optional[str] = None) -> bool:
        """
        Add a mission-specific agent to the workspace.
        
        Args:
            mission_id: Mission identifier
            agent_name: Name of the agent
            agent_spec: Agent specification/configuration
            agent_code: Optional agent implementation code
            
        Returns:
            True if successful, False otherwise
        """
        workspace = self.get_workspace(mission_id)
        if not workspace:
            logger.error(f"Workspace not found for mission: {mission_id}")
            return False
        
        try:
            # Create agent directory
            agent_dir = Path(workspace.workspace_path) / workspace.agents_dir / agent_name
            agent_dir.mkdir(exist_ok=True)
            
            # Save agent specification
            spec_file = agent_dir / "spec.json"
            with open(spec_file, 'w') as f:
                json.dump(agent_spec, f, indent=2)
            
            # Save agent code if provided
            if agent_code:
                code_file = agent_dir / f"{agent_name.lower()}.py"
                with open(code_file, 'w') as f:
                    f.write(agent_code)
            
            # Update asset manifest
            self._update_asset_manifest(mission_id, "agents", agent_name, {
                "type": "agent",
                "spec_file": str(spec_file.relative_to(Path(workspace.workspace_path))),
                "code_file": str(code_file.relative_to(Path(workspace.workspace_path))) if agent_code else None,
                "created_at": datetime.now().isoformat(),
                "status": "active"
            })
            
            logger.info(f"Added agent {agent_name} to workspace {mission_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding agent to workspace: {e}")
            return False
    
    def add_tool_to_workspace(self, mission_id: str, tool_name: str, 
                             tool_spec: Dict[str, Any], tool_code: Optional[str] = None) -> bool:
        """
        Add a mission-specific tool to the workspace.
        
        Args:
            mission_id: Mission identifier
            tool_name: Name of the tool
            tool_spec: Tool specification/configuration
            tool_code: Optional tool implementation code
            
        Returns:
            True if successful, False otherwise
        """
        workspace = self.get_workspace(mission_id)
        if not workspace:
            logger.error(f"Workspace not found for mission: {mission_id}")
            return False
        
        try:
            # Create tool directory
            tool_dir = Path(workspace.workspace_path) / workspace.tools_dir / tool_name
            tool_dir.mkdir(exist_ok=True)
            
            # Save tool specification
            spec_file = tool_dir / "spec.json"
            with open(spec_file, 'w') as f:
                json.dump(tool_spec, f, indent=2)
            
            # Save tool code if provided
            if tool_code:
                code_file = tool_dir / f"{tool_name.lower()}.py"
                with open(code_file, 'w') as f:
                    f.write(tool_code)
            
            # Update asset manifest
            self._update_asset_manifest(mission_id, "tools", tool_name, {
                "type": "tool",
                "spec_file": str(spec_file.relative_to(Path(workspace.workspace_path))),
                "code_file": str(code_file.relative_to(Path(workspace.workspace_path))) if tool_code else None,
                "created_at": datetime.now().isoformat(),
                "status": "active"
            })
            
            logger.info(f"Added tool {tool_name} to workspace {mission_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding tool to workspace: {e}")
            return False
    
    def save_asset(self, mission_id: str, asset_name: str, asset_data: Union[str, bytes, Dict], 
                   asset_type: str = "file", category: str = "general") -> Optional[str]:
        """
        Save an asset to the mission workspace.
        
        Args:
            mission_id: Mission identifier
            asset_name: Name of the asset
            asset_data: Asset content (string, bytes, or dict)
            asset_type: Type of asset (file, config, data, etc.)
            category: Asset category (code, data, configs, media)
            
        Returns:
            Path to saved asset relative to workspace, or None if failed
        """
        workspace = self.get_workspace(mission_id)
        if not workspace:
            logger.error(f"Workspace not found for mission: {mission_id}")
            return None
        
        try:
            # Determine file path
            asset_dir = Path(workspace.workspace_path) / workspace.assets_dir / category
            asset_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine file extension based on data type with timestamp prefix
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if isinstance(asset_data, dict):
                asset_file = asset_dir / f"{timestamp}_{asset_name}.json"
                with open(asset_file, 'w') as f:
                    json.dump(asset_data, f, indent=2)
            elif isinstance(asset_data, bytes):
                asset_file = asset_dir / f"{timestamp}_{asset_name}"
                with open(asset_file, 'wb') as f:
                    f.write(asset_data)
            else:
                # String data
                asset_file = asset_dir / f"{timestamp}_{asset_name}"
                with open(asset_file, 'w') as f:
                    f.write(str(asset_data))
            
            # Update asset manifest
            relative_path = asset_file.relative_to(Path(workspace.workspace_path))
            self._update_asset_manifest(mission_id, "generated_files", asset_name, {
                "type": asset_type,
                "category": category,
                "file_path": str(relative_path),
                "created_at": datetime.now().isoformat(),
                "size_bytes": asset_file.stat().st_size
            })
            
            logger.info(f"Saved asset {asset_name} to workspace {mission_id}")
            return str(relative_path)
            
        except Exception as e:
            logger.error(f"Error saving asset to workspace: {e}")
            return None
    
    def get_asset_path(self, mission_id: str, asset_name: str) -> Optional[Path]:
        """Get the full path to an asset in the workspace."""
        workspace = self.get_workspace(mission_id)
        if not workspace:
            return None
        
        manifest = self._load_asset_manifest(mission_id)
        if not manifest:
            return None
        
        # Check all asset categories
        for category in ["agents", "tools", "generated_files", "external_resources"]:
            assets = getattr(manifest, category, {})
            if asset_name in assets:
                asset_info = assets[asset_name]
                if "file_path" in asset_info:
                    return Path(workspace.workspace_path) / asset_info["file_path"]
                elif "spec_file" in asset_info:
                    return Path(workspace.workspace_path) / asset_info["spec_file"]
        
        return None
    
    def save_mission_state(self, mission_id: str, state_data: Dict[str, Any], 
                          checkpoint_name: Optional[str] = None) -> bool:
        """
        Save mission state to the workspace.
        
        Args:
            mission_id: Mission identifier
            state_data: State data to save
            checkpoint_name: Optional checkpoint name, defaults to timestamp
            
        Returns:
            True if successful, False otherwise
        """
        workspace = self.get_workspace(mission_id)
        if not workspace:
            logger.error(f"Workspace not found for mission: {mission_id}")
            return False
        
        try:
            state_dir = Path(workspace.workspace_path) / workspace.state_dir
            
            # Save current state
            current_state_file = state_dir / "current_state.json"
            with open(current_state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            # Save checkpoint if requested
            if checkpoint_name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                checkpoint_file = state_dir / "checkpoints" / f"{timestamp}_{checkpoint_name}.json"
                checkpoint_file.parent.mkdir(exist_ok=True)
                with open(checkpoint_file, 'w') as f:
                    json.dump(state_data, f, indent=2)
            
            logger.info(f"Saved mission state for {mission_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving mission state: {e}")
            return False
    
    def load_mission_state(self, mission_id: str, checkpoint_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load mission state from the workspace.
        
        Args:
            mission_id: Mission identifier
            checkpoint_name: Optional checkpoint name, defaults to current state
            
        Returns:
            State data or None if not found
        """
        workspace = self.get_workspace(mission_id)
        if not workspace:
            return None
        
        try:
            state_dir = Path(workspace.workspace_path) / workspace.state_dir
            
            if checkpoint_name:
                # Look for the most recent checkpoint with this name
                checkpoints_dir = state_dir / "checkpoints"
                if checkpoints_dir.exists():
                    # Find all checkpoint files with this name (with timestamp prefix)
                    checkpoint_files = list(checkpoints_dir.glob(f"*_{checkpoint_name}.json"))
                    if checkpoint_files:
                        # Sort by filename (timestamp prefix) and get the most recent
                        state_file = sorted(checkpoint_files)[-1]
                    else:
                        # Fallback to old naming convention
                        state_file = checkpoints_dir / f"{checkpoint_name}.json"
                else:
                    state_file = state_dir / "checkpoints" / f"{checkpoint_name}.json"
            else:
                state_file = state_dir / "current_state.json"
            
            if state_file.exists():
                with open(state_file, 'r') as f:
                    return json.load(f)
            
        except Exception as e:
            logger.error(f"Error loading mission state: {e}")
        
        return None
    
    def archive_workspace(self, mission_id: str, archive_path: Optional[str] = None) -> bool:
        """
        Archive a mission workspace.
        
        Args:
            mission_id: Mission identifier
            archive_path: Optional custom archive path
            
        Returns:
            True if successful, False otherwise
        """
        workspace = self.get_workspace(mission_id)
        if not workspace:
            logger.error(f"Workspace not found for mission: {mission_id}")
            return False
        
        try:
            if not archive_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                workspace_name = Path(workspace.workspace_path).name
                archive_dir = Path(workspace.workspace_path).parent / "archives"
                archive_dir.mkdir(exist_ok=True)
                archive_path = str(archive_dir / f"{timestamp}_archived_{workspace_name}")
            
            # Create archive
            shutil.make_archive(archive_path, 'zip', workspace.workspace_path)
            
            # Update workspace status
            workspace.status = "archived"
            workspace.last_updated = datetime.now().isoformat()
            self._save_workspace_config(workspace)
            
            logger.info(f"Archived workspace {mission_id} to {archive_path}.zip")
            return True
            
        except Exception as e:
            logger.error(f"Error archiving workspace: {e}")
            return False
    
    def list_workspaces(self, status_filter: Optional[str] = None) -> List[WorkspaceConfig]:
        """
        List all workspaces, optionally filtered by status.
        
        Args:
            status_filter: Optional status to filter by
            
        Returns:
            List of workspace configurations
        """
        workspaces = list(self.workspaces.values())
        
        if status_filter:
            workspaces = [w for w in workspaces if w.status == status_filter]
        
        return sorted(workspaces, key=lambda w: w.created_at, reverse=True)
    
    def get_workspace_summary(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of workspace contents and metrics."""
        workspace = self.get_workspace(mission_id)
        if not workspace:
            return None
        
        manifest = self._load_asset_manifest(mission_id)
        if not manifest:
            return None
        
        workspace_path = Path(workspace.workspace_path)
        
        # Calculate directory sizes
        total_size = sum(f.stat().st_size for f in workspace_path.rglob('*') if f.is_file())
        
        return {
            "mission_id": mission_id,
            "mission_name": workspace.mission_name,
            "status": workspace.status,
            "created_at": workspace.created_at,
            "last_updated": workspace.last_updated,
            "workspace_path": workspace.workspace_path,
            "total_size_mb": total_size / (1024 * 1024),
            "asset_counts": {
                "agents": len(manifest.agents),
                "tools": len(manifest.tools),
                "generated_files": len(manifest.generated_files),
                "external_resources": len(manifest.external_resources)
            },
            "tags": workspace.tags
        }
    
    def _update_asset_manifest(self, mission_id: str, category: str, asset_name: str, asset_info: Dict[str, Any]):
        """Update the asset manifest with new asset information."""
        manifest = self._load_asset_manifest(mission_id)
        if not manifest:
            return
        
        # Update the appropriate category
        category_dict = getattr(manifest, category, {})
        category_dict[asset_name] = asset_info
        setattr(manifest, category, category_dict)
        
        # Update metadata
        manifest.last_updated = datetime.now().isoformat()
        manifest.total_assets = sum(len(getattr(manifest, cat, {})) for cat in ["agents", "tools", "generated_files", "external_resources"])
        
        # Save updated manifest
        workspace = self.get_workspace(mission_id)
        if workspace:
            manifest_path = Path(workspace.workspace_path) / "asset_manifest.json"
            with open(manifest_path, 'w') as f:
                json.dump(asdict(manifest), f, indent=2)
    
    def _load_asset_manifest(self, mission_id: str) -> Optional[AssetManifest]:
        """Load the asset manifest for a workspace."""
        workspace = self.get_workspace(mission_id)
        if not workspace:
            return None
        
        manifest_path = Path(workspace.workspace_path) / "asset_manifest.json"
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
                return AssetManifest(**manifest_data)
        except Exception as e:
            logger.error(f"Error loading asset manifest: {e}")
            return None
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for filesystem use."""
        import re
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r'[^\w\s-]', '', name.lower())
        sanitized = re.sub(r'[-\s]+', '_', sanitized).strip('_')
        return sanitized[:50]  # Limit length
    
    def _generate_workspace_readme(self, config: WorkspaceConfig) -> str:
        """Generate a README file for the workspace."""
        return f"""# Mission Workspace: {config.mission_name}

**Mission ID:** `{config.mission_id}`
**Created:** {config.created_at}
**Status:** {config.status}

## Mission Description
{config.overall_mission}

## Directory Structure

- `{config.agents_dir}/` - Mission-specific agents
- `{config.tools_dir}/` - Mission-specific tools  
- `{config.assets_dir}/` - Generated assets and files
  - `code/` - Generated code files
  - `data/` - Data files and datasets
  - `configs/` - Configuration files
  - `media/` - Images, videos, and other media
- `{config.logs_dir}/` - Mission and agent logs
- `{config.state_dir}/` - Mission state and checkpoints
- `{config.docs_dir}/` - Documentation and templates

## Asset Management

This workspace uses an asset manifest (`asset_manifest.json`) to track all mission-specific resources. The manifest is automatically updated when assets are added or modified.

## Tags
{', '.join(config.tags) if config.tags else 'None'}

---
*This workspace was created by Launchonomy WorkspaceManager*
"""
    
    def _generate_gitignore(self) -> str:
        """Generate a .gitignore file for the workspace."""
        return """# Launchonomy Mission Workspace

# Temporary files
*.tmp
*.temp
.DS_Store
Thumbs.db

# Logs
*.log
logs/*.log

# State files (may contain sensitive data)
state/current_state.json
state/checkpoints/*.json
memory/

# Large data files
assets/data/*.csv
assets/data/*.json
assets/data/*.db
assets/media/*

# API keys and secrets
.env
*.key
secrets.json

# Python cache
__pycache__/
*.pyc
*.pyo

# IDE files
.vscode/
.idea/
*.swp
*.swo
""" 