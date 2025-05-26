# Mission Workspace System

## 🎯 Overview

The Launchonomy Mission Workspace System provides organized, filesystem-based workspaces for each mission, enabling the storage and management of mission-specific agents, tools, assets, and state. This system supports the C-Suite workflow by creating dedicated environments where mission-specific capabilities can be developed, tested, and deployed.

## 🏗️ Architecture

### Core Components

1. **WorkspaceManager** - Central management of mission workspaces
2. **MissionManager Integration** - Automatic workspace creation during mission initialization
3. **AssetManifest** - Tracking and cataloging of all mission assets
4. **CLI Interface** - Command-line tools for workspace management

### Directory Structure

Each mission workspace follows a standardized structure with timestamp-first naming for chronological ordering:

```
.launchonomy/
└── {YYYYMMDD_HHMMSS}_{mission_type}_{sanitized_name}/
    ├── workspace_config.json      # Workspace configuration
    ├── asset_manifest.json        # Asset tracking manifest
    ├── README.md                  # Auto-generated documentation
    ├── .gitignore                 # Version control exclusions
    ├── agents/                    # Mission-specific agents
    │   └── {AgentName}/
    │       ├── spec.json          # Agent specification
    │       └── {agentname}.py     # Agent implementation
    ├── tools/                     # Mission-specific tools
    │   └── {ToolName}/
    │       ├── spec.json          # Tool specification
    │       └── {toolname}.py      # Tool implementation
    ├── assets/                    # Generated assets and files
    │   ├── code/                  # Generated code files
    │   ├── data/                  # Data files and datasets
    │   ├── configs/               # Configuration files
    │   └── media/                 # Images, videos, media
    ├── logs/                      # Mission and agent logs
    │   ├── agents/                # Agent-specific logs
    │   └── cycles/                # Decision cycle logs
    ├── state/                     # Mission state management
    │   ├── current_state.json     # Current mission state
    │   ├── checkpoints/           # Named checkpoints
    │   └── progress/              # Progress tracking
    └── docs/                      # Documentation
        ├── generated/             # Auto-generated docs
        └── templates/             # Document templates
```

## 🚀 Key Features

### 1. Automatic Workspace Creation
- Workspaces are automatically created when missions are initialized
- Integrated with existing `MissionManager` for seamless operation
- Standardized directory structure ensures consistency

### 2. Asset Management
- **Agents**: Mission-specific agent implementations with specifications
- **Tools**: Custom tools developed for the mission
- **Generated Files**: Code, configs, data, and media assets
- **State Management**: Mission state and checkpoint system

### 3. Asset Manifest Tracking
- Comprehensive tracking of all workspace assets
- Metadata including creation time, file paths, and asset types
- Automatic updates when assets are added or modified

### 4. Integration Points
- **C-Suite Workflow**: Supports the "identify → create → train → certify" cycle
- **DevAgent/QAAgent**: Workspace for storing generated and tested code
- **Mission Resumption**: State persistence for resumable missions

## 📋 Usage Examples

### Creating a Workspace via CLI

```bash
# Create a new mission workspace
python -m launchonomy.cli_workspace create "AI Chatbot" "Build customer service chatbot" "ai,chatbot"

# List all workspaces
python -m launchonomy.cli_workspace list

# Inspect a specific workspace
python -m launchonomy.cli_workspace inspect 20250526_120000_mission_ai_chatbot

# Show workspace statistics
python -m launchonomy.cli_workspace status

# Archive a completed workspace
python -m launchonomy.cli_workspace archive 20250526_120000_mission_ai_chatbot
```

### Programmatic Usage

```python
from launchonomy.core.workspace_manager import WorkspaceManager
from launchonomy.core.mission_manager import MissionManager

# Initialize workspace manager
workspace_manager = WorkspaceManager(".launchonomy")

# Create a workspace
config = workspace_manager.create_workspace(
    mission_id="20250526_120000_mission_example",
    mission_name="Example Mission",
    overall_mission="Demonstrate workspace functionality",
    tags=["example", "demo"]
)

# Add an agent to the workspace
workspace_manager.add_agent_to_workspace(
    mission_id=config.mission_id,
    agent_name="ExampleAgent",
    agent_spec={"description": "Example agent for demo"},
    agent_code="class ExampleAgent:\n    pass"
)

# Save mission assets
workspace_manager.save_asset(
    mission_id=config.mission_id,
    asset_name="config.json",
    asset_data={"setting": "value"},
    category="configs"
)

# Save mission state
workspace_manager.save_mission_state(
    mission_id=config.mission_id,
    state_data={"phase": "development", "progress": 0.5},
    checkpoint_name="milestone_1"
)
```

### Integration with MissionManager

```python
# Mission manager automatically creates workspaces
mission_manager = MissionManager(".launchonomy")

# Create mission (workspace created automatically)
mission_log = mission_manager.create_or_load_mission(
    mission_name="E-commerce Platform",
    overall_mission="Build complete e-commerce solution",
    resume_existing=False
)

# Add assets through mission manager
mission_manager.add_agent_to_mission_workspace(
    agent_name="ProductAgent",
    agent_spec={"description": "Manages product catalog"}
)

mission_manager.save_mission_asset(
    asset_name="product_schema.json",
    asset_data={"fields": ["name", "price", "description"]},
    category="data"
)
```

## 🔄 C-Suite Workflow Integration

The workspace system directly supports the proposed C-Suite workflow:

### 1. Understand the Problem
- Mission context stored in `workspace_config.json`
- Problem analysis saved in `docs/` directory

### 2. Plan to Solve the Problem
- Planning documents stored in `docs/generated/`
- Strategic decisions logged in mission state

### 3. Identify Agents/Tools Required
- Requirements tracked in asset manifest
- Gap analysis stored in planning documents

### 4. Create, Train & Certify Missing Capabilities
- **DevAgent** creates code in `agents/` and `tools/` directories
- **QAAgent** stores test results and certification status
- Certification metadata tracked in asset manifest

### 5. Execute the Plan
- Execution logs stored in `logs/cycles/`
- Generated outputs saved in appropriate `assets/` subdirectories

### 6. Review Outputs Against Mission
- Review results stored in `state/checkpoints/`
- Mission progress tracked in `state/current_state.json`

## 📊 Asset Manifest System

The asset manifest (`asset_manifest.json`) provides comprehensive tracking:

```json
{
  "mission_id": "20250526_120000_mission_example",
  "created_at": "2025-05-26T12:00:00.000000",
  "last_updated": "2025-05-26T12:30:00.000000",
  "agents": {
    "ExampleAgent": {
      "type": "agent",
      "spec_file": "agents/ExampleAgent/spec.json",
      "code_file": "agents/ExampleAgent/exampleagent.py",
      "created_at": "2025-05-26T12:15:00.000000",
      "status": "active"
    }
  },
  "tools": {
    "ExampleTool": {
      "type": "tool",
      "spec_file": "tools/ExampleTool/spec.json",
      "code_file": "tools/ExampleTool/exampletool.py",
      "created_at": "2025-05-26T12:20:00.000000",
      "status": "certified"
    }
  },
  "generated_files": {
    "config.json": {
      "type": "config",
      "category": "configs",
      "file_path": "assets/configs/config.json",
      "created_at": "2025-05-26T12:25:00.000000",
      "size_bytes": 1024
    }
  },
  "total_assets": 3,
  "storage_size_mb": 0.05
}
```

## 🔧 Configuration

### Workspace Configuration

Each workspace has a `workspace_config.json` file:

```json
{
  "mission_id": "mission_example_20250526_120000",
  "mission_name": "Example Mission",
  "overall_mission": "Demonstrate workspace functionality",
  "created_at": "2025-05-26T12:00:00.000000",
  "workspace_path": "/path/to/.launchonomy/mission_example_20250526_120000_example_mission",
  "status": "active",
  "agents_dir": "agents",
  "tools_dir": "tools",
  "assets_dir": "assets",
  "logs_dir": "logs",
  "state_dir": "state",
  "docs_dir": "docs",
  "tags": ["example", "demo"],
  "description": "Demonstrate workspace functionality",
  "last_updated": "2025-05-26T12:30:00.000000"
}
```

### Environment Variables

- `LAUNCHONOMY_WORKSPACE_DIR`: Override default workspace directory (default: `.launchonomy`)
- `LAUNCHONOMY_WORKSPACE_MAX_SIZE`: Maximum workspace size in MB (default: unlimited)

## 🛡️ Security and Privacy

### File Permissions
- Workspaces created with appropriate file permissions
- Sensitive state files excluded from version control via `.gitignore`

### Data Isolation
- Each mission has its own isolated workspace
- No cross-mission data leakage
- Clear separation of concerns

### Cleanup and Archiving
- Automatic archiving of completed missions
- Configurable retention policies
- Secure deletion of sensitive data

## 🔮 Future Enhancements

### Planned Features
1. **Workspace Templates**: Pre-configured workspace templates for common mission types
2. **Asset Sharing**: Cross-mission asset sharing and reuse
3. **Backup and Sync**: Cloud backup and synchronization capabilities
4. **Workspace Analytics**: Usage analytics and optimization recommendations
5. **Integration APIs**: REST APIs for external tool integration

### Extensibility Points
- Custom asset types and categories
- Pluggable storage backends
- Custom workspace layouts
- Integration with external version control systems

## 📚 API Reference

### WorkspaceManager

```python
class WorkspaceManager:
    def __init__(self, base_workspace_dir: str = ".launchonomy")
    def create_workspace(self, mission_id: str, mission_name: str, overall_mission: str, tags: Optional[List[str]] = None) -> WorkspaceConfig
    def get_workspace(self, mission_id: str) -> Optional[WorkspaceConfig]
    def add_agent_to_workspace(self, mission_id: str, agent_name: str, agent_spec: Dict[str, Any], agent_code: Optional[str] = None) -> bool
    def add_tool_to_workspace(self, mission_id: str, tool_name: str, tool_spec: Dict[str, Any], tool_code: Optional[str] = None) -> bool
    def save_asset(self, mission_id: str, asset_name: str, asset_data: Union[str, bytes, Dict], asset_type: str = "file", category: str = "general") -> Optional[str]
    def save_mission_state(self, mission_id: str, state_data: Dict[str, Any], checkpoint_name: Optional[str] = None) -> bool
    def load_mission_state(self, mission_id: str, checkpoint_name: Optional[str] = None) -> Optional[Dict[str, Any]]
    def archive_workspace(self, mission_id: str, archive_path: Optional[str] = None) -> bool
    def list_workspaces(self, status_filter: Optional[str] = None) -> List[WorkspaceConfig]
    def get_workspace_summary(self, mission_id: str) -> Optional[Dict[str, Any]]
```

### MissionManager Integration

```python
class MissionManager:
    def add_agent_to_mission_workspace(self, agent_name: str, agent_spec: Dict[str, Any], agent_code: Optional[str] = None) -> bool
    def add_tool_to_mission_workspace(self, tool_name: str, tool_spec: Dict[str, Any], tool_code: Optional[str] = None) -> bool
    def save_mission_asset(self, asset_name: str, asset_data: Any, asset_type: str = "file", category: str = "general") -> Optional[str]
    def save_mission_state_to_workspace(self, state_data: Dict[str, Any], checkpoint_name: Optional[str] = None) -> bool
    def load_mission_state_from_workspace(self, checkpoint_name: Optional[str] = None) -> Optional[Dict[str, Any]]
    def get_workspace_summary(self) -> Optional[Dict[str, Any]]
    def archive_mission_workspace(self) -> bool
```

## 🎉 Conclusion

The Mission Workspace System provides a robust foundation for organizing and managing mission-specific assets in Launchonomy. It seamlessly integrates with the existing mission management infrastructure while providing the filesystem-based organization needed to support the C-Suite workflow and dynamic agent/tool creation process.

The system is designed to be:
- **Scalable**: Handles multiple concurrent missions
- **Organized**: Standardized structure for consistency
- **Integrated**: Works seamlessly with existing components
- **Extensible**: Easy to add new features and capabilities
- **User-Friendly**: Simple CLI and programmatic interfaces

This workspace system enables the vision of mission-specific agent and tool development while maintaining clear organization and traceability of all mission assets. 