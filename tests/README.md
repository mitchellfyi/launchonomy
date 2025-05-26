# Launchonomy Test Suite

This directory contains all test files for the Launchonomy autonomous AI agents business system.

## Test Files Overview

### Core Functionality Tests

#### `test_agent_loading.py`
Tests the agent loading and instantiation system (Task 5 implementation).
- **Purpose**: Verifies that all registered agents are loaded correctly at startup
- **Features Tested**:
  - Agent loading from registry
  - Registry persistence across restarts
  - Auto-provisioned agent integration
  - `registry.list_agent_names()` functionality
- **Run**: `python tests/test_agent_loading.py`

#### `test_mission_linking.py`
Tests mission logging, cycle linking, and resumable missions.
- **Purpose**: Verifies mission management and cycle linking functionality
- **Features Tested**:
  - Mission creation and management
  - Cycle linking with previous/next references
  - Mission resumption after restart
  - Context preservation across cycles
  - Key learnings extraction and propagation
- **Run**: `python tests/test_mission_linking.py`

#### `test_auto_provision.py`
Tests the auto-provisioning functionality for tools and agents.
- **Purpose**: Verifies that missing tools/agents can be auto-provisioned
- **Features Tested**:
  - Tool auto-provisioning
  - Agent auto-provisioning
  - Registry integration
- **Run**: `python tests/test_auto_provision.py`
- **Requirements**: OPENAI_API_KEY environment variable

#### `test_memory_integration.py`
Tests the mission-scoped RAG memory system integration.
- **Purpose**: Validates the ChromaDB vector memory system and RetrievalAgent functionality
- **Features Tested**:
  - ChromaDB vector memory creation and storage
  - Memory logging functionality across workflow steps
  - RetrievalAgent semantic search capabilities
  - Integration with the orchestrator system
  - Context-aware agent decision making
  - Cross-mission learning and pattern recognition
- **Run**: `python tests/test_memory_integration.py`
- **Requirements**: ChromaDB (automatically installed with requirements)

### Workflow and Integration Tests

#### `test_continuous_loop.py`
Tests the continuous launch and growth loop functionality.
- **Purpose**: Tests the main business automation loop
- **Features Tested**:
  - Continuous mode execution
  - Registry-based agent access
  - Workflow agent coordination
- **Run**: `python tests/test_continuous_loop.py`
- **Requirements**: OPENAI_API_KEY environment variable

#### `test_continuous_loop_mock.py`
Mock version of continuous loop tests (no API key required).
- **Purpose**: Tests continuous loop logic without external dependencies
- **Features Tested**:
  - Mock agent execution
  - Loop structure validation
  - Registry agent access patterns
- **Run**: `python tests/test_continuous_loop_mock.py`
- **Requirements**: None (uses mocks)

#### `test_workflow_agents_registration.py`
Tests workflow agent registration and specifications.
- **Purpose**: Verifies that workflow agents are properly registered
- **Features Tested**:
  - Agent registration validation
  - Specification compliance
  - Module/class loading
- **Run**: `python tests/test_workflow_agents_registration.py`

#### `test_workflow_auto_provision.py`
Tests auto-provisioning of workflow agents.
- **Purpose**: Tests dynamic creation of workflow agents
- **Features Tested**:
  - Workflow agent auto-provisioning
  - Registry integration
  - Agent specification generation
- **Run**: `python tests/test_workflow_auto_provision.py`

### Demo and Integration Tests

#### `test_repl_demo.py`
REPL-style demonstration of agent persistence and registry functionality.
- **Purpose**: Demonstrates registry functionality in REPL-like environment
- **Features Tested**:
  - Registry persistence simulation
  - Agent listing and details
  - Startup loading demonstration
- **Run**: `python tests/test_repl_demo.py`

#### `test_auto_provision_integration.py`
Integration tests for auto-provisioning across system restarts.
- **Purpose**: Tests auto-provisioning persistence and integration
- **Features Tested**:
  - Cross-restart persistence
  - Integration with main system
  - Registry consistency
- **Run**: `python tests/test_auto_provision_integration.py`

## Running Tests

### Prerequisites

1. **Python Environment**: Ensure you have Python 3.8+ with required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables** (for tests requiring API access):
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   export OPENAI_MODEL="gpt-4o-mini"  # Optional, defaults to gpt-4o-mini
   ```

### Running Individual Tests

From the project root directory:

```bash
# Core functionality tests
python tests/test_agent_loading.py
python tests/test_mission_linking.py
python tests/test_auto_provision.py
python tests/test_memory_integration.py

# Workflow tests
python tests/test_continuous_loop.py
python tests/test_continuous_loop_mock.py
python tests/test_workflow_agents_registration.py

# Demo and integration tests
python tests/test_repl_demo.py
python tests/test_auto_provision_integration.py
```

### Running All Tests

To run all tests that don't require API keys:
```bash
python tests/test_agent_loading.py
python tests/test_mission_linking.py
python tests/test_memory_integration.py
python tests/test_continuous_loop_mock.py
python tests/test_workflow_agents_registration.py
python tests/test_repl_demo.py
```

To run all tests (requires OPENAI_API_KEY):
```bash
for test in tests/test_*.py; do
    echo "Running $test..."
    python "$test"
    echo "---"
done
```

## Test Categories

### 🟢 No API Key Required
- `test_agent_loading.py`
- `test_mission_linking.py`
- `test_memory_integration.py`
- `test_continuous_loop_mock.py`
- `test_workflow_agents_registration.py`
- `test_repl_demo.py`
- `test_auto_provision_integration.py`

### 🟡 API Key Required
- `test_auto_provision.py`
- `test_continuous_loop.py`
- `test_workflow_auto_provision.py`

## Expected Output

All tests should output:
- ✅ Success indicators for passing tests
- ❌ Error indicators for failing tests
- Detailed logs of test execution
- Summary of results at the end

Example successful output:
```
Testing Agent Loading at Startup
============================================================
✅ Added test agents to registry
✅ Orchestrator created successfully
✅ TestLoadAgent loaded successfully
✅ Registry persistence verified
✅ All tests completed successfully!
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the project root directory
2. **API Key Errors**: Set OPENAI_API_KEY for tests that require it
3. **Module Not Found**: Install dependencies with `pip install -r requirements.txt`
4. **Registry Issues**: Delete `orchestrator/registry.json` if tests fail due to corrupted registry

### Test Data Cleanup

Some tests create temporary files in:
- `mission_logs/` - Mission and cycle log files
- `tools/stubs/` - Auto-provisioned tool stubs

These can be safely deleted between test runs if needed.

## Contributing

When adding new tests:

1. **Naming**: Use `test_<feature_name>.py` format
2. **Documentation**: Add description to this README
3. **Dependencies**: Clearly mark if API key is required
4. **Cleanup**: Ensure tests clean up after themselves
5. **Error Handling**: Include proper error handling and logging

## Test Architecture

The test suite is designed to:
- **Validate core functionality** without external dependencies where possible
- **Test integration points** between system components
- **Verify persistence** and resumability features
- **Demonstrate usage patterns** for developers
- **Ensure backward compatibility** during refactoring

Each test is self-contained and can be run independently, making it easy to debug specific functionality or run targeted test suites during development. 