# 🚀 Launchonomy - Autonomous AI Business Orchestration System

A comprehensive system for orchestrating AI agents to build and grow autonomous businesses through C-Suite strategic decision-making and workflow automation.

## 🏗️ Architecture

Launchonomy uses a modular architecture with clear separation of concerns:

```
launchonomy/
├── launchonomy/                    # Main package
│   ├── cli.py                      # Command line interface
│   ├── core/                       # Core orchestration logic
│   │   ├── orchestrator.py         # Main orchestrator agent
│   │   ├── mission_manager.py      # Mission lifecycle management
│   │   ├── agent_manager.py        # Agent lifecycle management
│   │   └── communication.py       # Agent communication
│   ├── agents/                     # All agent implementations
│   │   ├── base/                   # Base classes
│   │   │   └── workflow_agent.py   # Base workflow agent
│   │   ├── workflow/               # Workflow agents
│   │   │   ├── scan.py             # Market scanning
│   │   │   ├── deploy.py           # Product deployment
│   │   │   ├── campaign.py         # Marketing campaigns
│   │   │   ├── analytics.py        # Analytics and metrics
│   │   │   ├── finance.py          # Financial management
│   │   │   └── growth.py           # Growth optimization
│   │   └── csuite/                 # C-Suite agents (future)
│   ├── registry/                   # Agent registry system
│   │   ├── registry.py             # Agent discovery and management
│   │   └── registry.json           # Agent specifications
│   ├── templates/                  # Agent templates and prompts
│   └── utils/                      # Utilities
│       ├── logging.py              # Mission logging
│       └── consensus.py            # Consensus voting
├── tools/                          # External tools
├── tests/                          # Test suite
├── mission_logs/                   # Mission execution logs
└── main.py                         # Entry point
```

## 🚀 Quick Start

### Prerequisites

1. Python 3.8+
2. OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd launchonomy
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
# Or create a .env file with: OPENAI_API_KEY=your-api-key-here
```

### Running Launchonomy

#### Option 1: Using the main entry point (recommended)
```bash
python main.py
```

#### Option 2: Direct module execution
```bash
python -m launchonomy.cli
```

#### Option 3: With specific mission
```bash
python main.py "Build a profitable SaaS application"
```

#### Option 4: Force new mission (skip resume menu)
```bash
python main.py --new "Create an AI-powered newsletter service"
```

## 🎯 How It Works

### C-Suite Orchestrated Approach

Launchonomy implements a unique **C-Suite orchestrated** approach where:

1. **Strategic Planning**: C-Suite agents (CEO, CRO, CTO, CFO) make high-level strategic decisions
2. **Workflow Execution**: Specialized workflow agents execute operational tasks
3. **Strategic Review**: C-Suite agents review results and adjust strategy
4. **Continuous Iteration**: The cycle repeats until mission objectives are achieved

### Workflow Agent Sequence

The system executes workflow agents in a logical business sequence:

1. **ScanAgent** - Identifies market opportunities
2. **DeployAgent** - Builds and deploys products/services  
3. **CampaignAgent** - Creates and manages marketing campaigns
4. **AnalyticsAgent** - Tracks performance and generates insights
5. **FinanceAgent** - Manages financial operations and compliance
6. **GrowthAgent** - Optimizes for growth and scaling

### Mission Logging

Every mission is comprehensively logged with:
- Strategic decisions from C-Suite agents
- Workflow agent execution results
- Financial tracking and guardrails
- Error handling and recovery
- Token usage and costs

Mission logs are saved as JSON files with parameterized names:
```
mission_logs/mission_20250526_005050_test_reorganized_codebase.json
```

## 🛠️ Configuration

### Environment Variables

- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `OPENAI_MODEL` - Model to use (default: gpt-4o-mini)

### Command Line Options

- `--debug` - Enable detailed debug logging
- `--new` - Skip resume menu and force new mission
- `--max-iterations N` - Maximum iterations for continuous mode (default: 10)

## 📊 Mission Management

### Resume Previous Missions

Launchonomy automatically detects resumable missions and presents a menu:

```
Found 3 resumable mission(s):
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ # ┃ Mission                     ┃ Status   ┃ Cyc ┃ Tokens ┃ Modified ┃ Last Activity                 ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1 │ Build SaaS App              │ running  │ 3  │ ~2k   │ 1h ago │ C-Suite planning session      │
│ 2 │ Newsletter Service          │ complete │ 5  │ ~4k   │ 2d ago │ Revenue: $150.00             │
└───┴─────────────────────────────┴──────────┴────┴───────┴────────┴───────────────────────────────┘

Options:
  1-2: Resume mission
  n: Start new mission
  q: Quit
```

### Mission Log Analysis

Use the mission log navigator to analyze completed missions:

```bash
python tools/mission_log_navigator.py
```

## 🧪 Development

### Project Structure

The codebase follows a clean, modular architecture:

- **Core**: Main orchestration logic and management systems
- **Agents**: All agent implementations with clear inheritance hierarchy
- **Registry**: Dynamic agent discovery and lifecycle management
- **Utils**: Shared utilities for logging, consensus, etc.
- **Templates**: Agent prompts and configuration templates

### Adding New Agents

1. Create agent class inheriting from `BaseWorkflowAgent`
2. Implement required methods (`execute`, `get_capabilities`, etc.)
3. Add to appropriate module (`workflow/`, `csuite/`, etc.)
4. Register in the agent registry

### Testing

Run the test suite:
```bash
python -m pytest tests/
```

## 📈 Features

### ✅ Implemented
- C-Suite strategic orchestration
- Complete workflow agent sequence
- Mission logging and resumability
- Financial guardrails and compliance
- Token usage tracking
- Error handling and recovery
- Parameterized mission naming
- JSON parsing fallbacks for natural language responses

### 🚧 In Development
- Dedicated C-Suite agent implementations
- Advanced tool integration
- Real-time monitoring dashboard
- Multi-mission coordination

### 🔮 Planned
- Web interface
- API endpoints
- Plugin system
- Advanced analytics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the existing architecture
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

[License information]

## 🆘 Support

For issues, questions, or contributions, please [create an issue](link-to-issues) or reach out to the development team.

---

**Launchonomy** - Where AI agents build businesses autonomously 🚀 