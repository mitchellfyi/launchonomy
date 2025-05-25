# Launchonomy - Autonomous Business Mission System

An AI-powered autonomous business mission system that uses a collaborative team of specialized AI agents to achieve business objectives with minimal human intervention. The system features a founding C-Suite team of AI agents that work together through consensus-based decision making to execute business missions.

**Built with**: Cursor IDE + Claude 4 Sonnet + ChatGPT o4-mini

## Key Features

- 🤖 **Autonomous C-Suite Team**: Auto-bootstraps with 9 specialized AI agents (CEO, CRO, CTO, CPO, CMO, CDO, CCO, CFO, CCSO)
- 🔧 **Auto-Provisioning**: Automatically creates missing tools and agents without human intervention
- 🗳️ **Consensus Voting**: All decisions made through unanimous consensus for safety and reliability
- 💰 **Budget-Conscious**: Built-in financial constraints and cost monitoring
- 📊 **Mission-Driven**: KPI-focused execution with comprehensive logging
- 🔄 **Self-Governing**: Agents operate independently within defined constraints
- 📝 **Comprehensive Logging**: Full mission tracking and retrospective analysis

## Architecture

The system is built around an **OrchestratorAgent** that manages a team of specialist agents:

### Core Components

1. **OrchestratorAgent**: Central coordinator that manages missions and agent collaboration
2. **AutoProvisionAgent**: Automatically creates missing tools and agents through consensus voting
3. **C-Suite Founding Team**: 9 specialized agents with distinct roles and expertise
4. **Registry System**: Persistent storage for agents, tools, and capabilities
5. **Consensus Engine**: Ensures all decisions are made through unanimous voting

### C-Suite Founding Team

The system automatically bootstraps with these specialized agents:

- **CEO-Agent**: Strategic leadership and overall mission coordination
- **CRO-Agent**: Revenue optimization and customer relationship management
- **CTO-Agent**: Technology strategy and technical implementation
- **CPO-Agent**: Product development and user experience
- **CMO-Agent**: Marketing strategy and brand management
- **CDO-Agent**: Data strategy and analytics
- **CCO-Agent**: Customer success and support operations
- **CFO-Agent**: Financial planning and budget management
- **CCSO-Agent**: Cybersecurity and risk management

## Prerequisites

- Python 3.9+
- pip package manager
- Local LLM server (recommended) or OpenAI API access

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd launchonomy
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your environment:
Create a `.env` file in the root directory:
```env
# For local LLM (recommended)
OPENAI_API_BASE=http://localhost:1234/v1
OPENAI_API_KEY=123

# For OpenAI API
# OPENAI_API_KEY=your-api-key-here
```

## Usage

### Command Line Interface

**Default Continuous Mode** (recommended for autonomous operation):
```bash
# Run with default mission in continuous mode
python orchestrator/cli.py

# Run with specific mission in continuous mode
python orchestrator/cli.py "Launch a profitable SaaS product in the productivity niche"

# Limit continuous mode iterations
python orchestrator/cli.py --max-iterations 20 "Build an AI-powered app"
```

**Manual Decision Cycle Mode** (for step-by-step control):
```bash
# Run in manual mode with user approval for each decision
python orchestrator/cli.py --manual

# Force new mission in manual mode
python orchestrator/cli.py --manual --new "Create a subscription service"
```

**Continuous Mode** (default) will:
1. Auto-bootstrap the C-Suite founding team
2. Run the continuous launch & growth loop autonomously
3. Execute scan → deploy → campaign → analytics → finance → growth cycles
4. Auto-provision missing tools and agents as needed
5. Monitor financial guardrails and pause if needed
6. Generate revenue and optimize growth automatically

**Manual Mode** will:
1. Auto-bootstrap the C-Suite founding team
2. Present each decision for user approval
3. Allow rejection and revision of recommendations
4. Provide step-by-step control over mission execution

### Example Session

```bash
$ python orchestrator/cli.py
🚀 Launchonomy - Autonomous Business Mission System
What business mission would you like to run? [Build a fully autonomous online business...]: 
Launch a subscription-based newsletter focused on AI industry insights

🤖 Bootstrapping C-Suite founding team...
✅ CEO-Agent initialized
✅ CRO-Agent initialized
✅ CTO-Agent initialized
... (all 9 agents)

📋 Mission Analysis:
- Strategic approach: Content-driven subscription model
- Required capabilities: Content creation, email automation, payment processing
- Auto-provisioning: Email marketing tool, payment gateway, analytics dashboard

🗳️ Consensus Decision: Proceed with newsletter launch strategy
💰 Budget allocation: $500 initial investment approved
🚀 Mission execution initiated...
```

## Mission Monitoring

The CLI provides real-time monitoring with:

1. **Mission Status Panel**
   - Current mission description and progress
   - Active agents and their roles
   - Budget utilization and constraints

2. **Activity Log**
   - Agent decisions and consensus votes
   - Auto-provisioning activities
   - Progress updates and milestones

3. **Results Dashboard**
   - Mission outcomes and KPI achievements
   - Financial performance
   - Next steps and recommendations

## Auto-Provisioning System

The AutoProvisionAgent automatically handles:

- **Tool Creation**: Missing business tools (CRM, analytics, payment processing, etc.)
- **Agent Specialization**: New specialist agents for specific domains
- **API Integrations**: External service connections and webhooks
- **Infrastructure**: Basic technical requirements and endpoints

All auto-provisioning decisions go through unanimous consensus voting for safety.

## Directory Structure

```
launchonomy/
├── mission_logs/           # Mission execution logs and analysis
├── orchestrator/           # Core orchestration system
│   ├── agents/            # Specialist agent implementations
│   │   ├── auto_provision_agent.py  # Auto-provisioning logic
│   │   ├── base_workflow_agent.py   # Base class for workflow agents
│   │   ├── scan_agent.py            # Opportunity scanning agent
│   │   ├── deploy_agent.py          # MVP deployment agent
│   │   ├── campaign_agent.py        # Marketing campaign agent
│   │   ├── analytics_agent.py       # Analytics and metrics agent
│   │   ├── finance_agent.py         # Financial guardrails agent
│   │   ├── growth_agent.py          # Growth optimization agent
│   │   └── __init__.py
│   ├── templates/         # Agent system prompts and schemas
│   ├── cli.py            # Command line interface
│   ├── orchestrator_agent_refactored.py  # Main orchestrator logic
│   ├── agent_management.py          # Agent lifecycle management
│   ├── agent_communication.py       # Agent communication layer
│   ├── mission_management.py        # Mission and cycle logging
│   ├── registry.py       # Agent and tool registry
│   ├── consensus.py      # Consensus voting system
│   ├── logging_utils.py  # Mission logging utilities
│   └── registry.json     # Persistent registry storage
├── .env                  # Environment configuration
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── SYSTEM_STATUS.md     # Current system status and capabilities
```

## Logging and Analysis

Mission logs are automatically stored in `mission_logs/` with:
- JSON execution logs with full decision trails
- Consensus voting records
- Auto-provisioning activities
- KPI tracking and financial monitoring
- Retrospective analysis and lessons learned

## Safety and Constraints

The system operates within strict constraints:
- **Budget Limits**: All spending requires consensus approval
- **Unanimous Voting**: No action taken without full agreement
- **Human Oversight**: Critical decisions can be escalated
- **Audit Trail**: Complete logging of all decisions and actions

## Testing

The system includes a comprehensive test suite located in the `tests/` directory. Tests are organized into categories:

### Running Tests

**Quick Test (No API Key Required):**
```bash
# Test core functionality without external dependencies
python tests/test_agent_loading.py
python tests/test_mission_linking.py
python tests/test_continuous_loop_mock.py
python tests/test_workflow_agents_registration.py
python tests/test_repl_demo.py
```

**Full Test Suite (Requires OPENAI_API_KEY):**
```bash
# Set environment variable
export OPENAI_API_KEY="your-api-key-here"

# Run all tests
for test in tests/test_*.py; do
    echo "Running $test..."
    python "$test"
    echo "---"
done
```

### Test Categories

- **🟢 No API Key Required**: Core functionality, registry, mocks
- **🟡 API Key Required**: Auto-provisioning, continuous loop, workflow agents

See `tests/README.md` for detailed test documentation and troubleshooting.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - feel free to use for any purpose.

## Support

For issues and feature requests, please create an issue in the repository. 