# Autonomous Business Creator

An AI-powered system that autonomously creates and launches online businesses with zero or minimal upfront investment. The system uses a team of specialized AI agents to handle different aspects of business creation, from market validation to execution.

## Features

- 🤖 Fully autonomous business creation and operation
- 💰 Zero/minimal investment focus
- 📊 KPI-driven decision making
- 🔄 Collaborative decision loops with peer review
- 📝 Comprehensive mission logging
- 🎯 Customizable constraints and KPIs through system prompts

## Prerequisites

- Python 3.9+
- pip package manager
- A local LLM server or OpenAI API access

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd autogen
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your environment:
Create a `.env` file in the root directory:
```env
# For local LLM
OPENAI_API_BASE=http://localhost:1234/v1
OPENAI_API_KEY=123

# For OpenAI
# OPENAI_API_KEY=your-api-key-here
```

## Usage

### Command Line Interface

1. Run with default mission:
```bash
python orchestrator/cli.py
```

2. Run with specific mission:
```bash
python orchestrator/cli.py "Build a profitable online course business in the tech niche"
```

The system will automatically determine the best approach based on the mission description, using built-in constraints and KPIs defined in the orchestrator's primer.

### Example Session

```bash
$ python orchestrator/cli.py
What business mission would you like to run? [Build a fully autonomous online business...]: Build a profitable newsletter business focused on AI trends
```

## Mission Monitoring

The CLI provides a real-time mission monitor with:

1. Mission Status Panel
   - Current mission description
   - Execution status
   - Active agents

2. Activity Log
   - Agent decisions and actions
   - Progress updates
   - Error messages

3. Results Display
   - Mission outcomes
   - KPI achievements
   - Next steps

## Directory Structure

```
autogen/
├── backend/           # FastAPI backend service
├── mission_logs/      # Mission execution logs
├── orchestrator/      # Core orchestration logic
│   ├── agents/       # Specialist agent implementations
│   ├── templates/    # Agent system prompts
│   ├── cli.py        # Command line interface
│   └── orchestrator_agent.py  # Main orchestrator
├── .env              # Environment configuration
└── requirements.txt  # Python dependencies
```

## Logging and Analysis

Mission logs are stored in `mission_logs/` with:
- JSON execution logs
- Retrospective analysis
- KPI tracking
- Decision history

## Error Handling

The system includes:
- Budget guard rails
- Execution validation
- Error recovery loops
- Graceful failure handling

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