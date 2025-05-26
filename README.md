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

## 🤖 Agents & Tools Reference

### Core Orchestration

#### OrchestrationAgent
**Role**: Main mission orchestrator and strategic coordinator  
**Description**: Manages the entire mission lifecycle, coordinates between agents, handles C-Suite orchestration, and makes high-level strategic decisions. Acts as the central hub for all mission activities.

#### AgentManager  
**Role**: Agent lifecycle management  
**Description**: Handles technical aspects of agent creation, loading, and initialization. Manages the agent registry and bootstraps specialized agents when needed.

#### MissionManager
**Role**: Mission persistence and logging  
**Description**: Manages mission logs, handles mission resumability, tracks decision cycles, and maintains comprehensive mission history.

#### AgentCommunicator
**Role**: Inter-agent communication  
**Description**: Handles communication between agents, manages JSON parsing with fallbacks, and facilitates peer review processes.

### C-Suite Strategic Agents

#### CEO-Agent
**Role**: Chief Executive Officer - Strategic oversight  
**Description**: Provides high-level strategic direction, makes final mission decisions, and ensures alignment with overall business objectives.

#### CRO-Agent  
**Role**: Chief Revenue Officer - Revenue strategy  
**Description**: Focuses on revenue generation strategies, customer acquisition planning, and sales optimization decisions.

#### CTO-Agent
**Role**: Chief Technology Officer - Technical strategy  
**Description**: Makes technology stack decisions, oversees product development strategy, and ensures technical feasibility of initiatives.

#### CFO-Agent
**Role**: Chief Financial Officer - Financial oversight  
**Description**: Manages budget allocation, enforces financial guardrails, approves expenditures, and ensures profitability targets.

### Workflow Agents

#### ScanAgent
**Role**: Market opportunity scanner  
**Description**: Identifies and researches potential business opportunities, analyzes market demand, assesses competition, and ranks opportunities based on Launchonomy criteria (speed to first customer, budget constraints, automation potential).

**Key Capabilities**:
- Market opportunity identification
- Competitive analysis  
- Feasibility assessment
- Opportunity ranking and scoring

#### DeployAgent
**Role**: MVP deployment specialist  
**Description**: Builds and deploys minimum viable products rapidly. Handles architecture planning, technology stack selection, infrastructure setup, and essential integrations for immediate customer acquisition.

**Key Capabilities**:
- MVP architecture design
- Rapid development & deployment
- Essential integrations (payments, analytics, email)
- Launch preparation and validation

#### CampaignAgent
**Role**: Customer acquisition and marketing specialist  
**Description**: Designs, executes, and optimizes customer acquisition campaigns across multiple channels. Focuses on getting the first paying customer quickly while maintaining cost efficiency.

**Key Capabilities**:
- Multi-channel campaign strategy
- Campaign execution and automation
- Performance optimization and A/B testing
- Cost management and ROI optimization

#### AnalyticsAgent
**Role**: Business metrics and insights specialist  
**Description**: Collects, analyzes, and reports on key business metrics including revenue, customer acquisition, conversion rates, and operational efficiency. Provides data-driven insights for decision making.

**Key Capabilities**:
- Comprehensive metrics collection
- KPI dashboard creation
- Trend analysis and predictions
- Performance threshold monitoring

#### FinanceAgent
**Role**: Financial guardrails and budget enforcement  
**Description**: Enforces financial constraints, monitors budget utilization, assesses financial risks, and ensures operations stay within the <20% cost ratio guardrail.

**Key Capabilities**:
- Budget limit enforcement
- Financial risk assessment
- Cost tracking and monitoring
- Approval/rejection decisions for expenditures

#### GrowthAgent
**Role**: Growth optimization and scaling specialist  
**Description**: Handles growth loop execution, designs and runs growth experiments, optimizes conversion funnels, and scales successful initiatives while maintaining profitability.

**Key Capabilities**:
- Growth opportunity analysis
- Experiment design and execution
- Growth loop optimization
- Scaling strategy development

### Utility Components

#### Registry
**Role**: Agent discovery and management system  
**Description**: Maintains a registry of available agents, their capabilities, and specifications. Enables dynamic agent discovery and loading.

#### AutoProvisionAgent
**Role**: Automatic tool and agent provisioning  
**Description**: Handles automatic provisioning of trivial tools and agents when specialized capabilities are needed but not available.

#### ReviewManager
**Role**: Peer review coordination  
**Description**: Manages peer review processes between agents, facilitates consensus building, and ensures quality control in agent decisions.

### Tools & Integrations

#### Required Tools
- **hosting**: Web hosting and infrastructure management
- **domain_registration**: Domain name registration and DNS management
- **email_marketing**: Email campaign management and automation
- **social_media**: Social media posting and engagement
- **analytics_platform**: Core analytics and tracking
- **financial_monitoring**: Budget and expense tracking
- **payment_processing**: Payment gateway integration

#### Optional Tools
- **market_research**: Market analysis and competitive intelligence
- **competitor_analysis**: Competitive landscape analysis
- **trend_analysis**: Market trend identification
- **code_generation**: Automated code generation
- **template_library**: Pre-built templates and components
- **a_b_testing**: Split testing and optimization
- **seo_tools**: Search engine optimization
- **content_management**: Content creation and management
- **user_tracking**: User behavior analytics
- **conversion_optimization**: Conversion rate optimization
- **viral_mechanics**: Viral growth features
- **referral_systems**: Customer referral programs

### Agent Communication Flow

```
OrchestrationAgent (Central Hub)
    ├── C-Suite Planning Session
    │   ├── CEO-Agent (Strategic direction)
    │   ├── CRO-Agent (Revenue strategy)  
    │   ├── CTO-Agent (Technical decisions)
    │   └── CFO-Agent (Financial approval)
    │
    ├── Workflow Execution Sequence
    │   ├── ScanAgent → Market opportunities
    │   ├── DeployAgent → MVP deployment
    │   ├── CampaignAgent → Customer acquisition
    │   ├── AnalyticsAgent → Performance tracking
    │   ├── FinanceAgent → Budget enforcement
    │   └── GrowthAgent → Scaling optimization
    │
    └── C-Suite Review Session
        └── Strategic adjustments and next iteration planning
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