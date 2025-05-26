# Development Guide

## 🛠️ **Overview**

This guide provides comprehensive information for developers contributing to Launchonomy, including architecture patterns, coding standards, testing practices, and development workflows.

## 📋 **Table of Contents**

1. [Development Environment Setup](#development-environment-setup)
2. [Architecture Patterns](#architecture-patterns)
3. [Agent Development](#agent-development)
4. [Tool Development](#tool-development)
5. [Testing Guidelines](#testing-guidelines)
6. [Code Standards](#code-standards)
7. [Debugging & Troubleshooting](#debugging--troubleshooting)
8. [Performance Optimization](#performance-optimization)

---

## 🚀 **Development Environment Setup**

### **Prerequisites**
```bash
# Required software
- Python 3.8+
- Git
- OpenAI API key
- Code editor (VS Code recommended)

# Optional but recommended
- Docker (for containerized development)
- PostgreSQL (for advanced logging)
- Redis (for caching)
```

### **Local Setup**
```bash
# 1. Clone repository
git clone <repository-url>
cd launchonomy

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# 4. Environment configuration
cp .env.example .env
# Edit .env with your API keys

# 5. Run tests to verify setup
python -m pytest tests/

# 6. Run the system
python main.py
```

### **Development Dependencies**
```txt
# requirements-dev.txt
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.0.0
pre-commit>=3.0.0
```

---

## 🏗️ **Architecture Patterns**

### **Core Design Principles**

#### **1. Separation of Concerns**
```python
# ✅ Good: Clear separation
class OrchestrationAgent:
    """Handles strategic coordination only"""
    
class WorkflowAgent:
    """Handles specific operational tasks only"""
    
class MissionManager:
    """Handles persistence and logging only"""

# ❌ Bad: Mixed responsibilities
class SuperAgent:
    """Handles everything - orchestration, execution, logging"""
```

#### **2. Dependency Injection**
```python
# ✅ Good: Inject dependencies
class OrchestrationAgent:
    def __init__(self, mission_manager: MissionManager, 
                 agent_manager: AgentManager,
                 communicator: AgentCommunicator):
        self.mission_manager = mission_manager
        self.agent_manager = agent_manager
        self.communicator = communicator

# ❌ Bad: Hard-coded dependencies
class OrchestrationAgent:
    def __init__(self):
        self.mission_manager = MissionManager()  # Hard-coded
```

#### **3. Async/Await Patterns**
```python
# ✅ Good: Proper async patterns
async def execute_workflow_sequence(self, agents: List[BaseWorkflowAgent]):
    results = []
    for agent in agents:
        try:
            result = await agent.execute(task_description, context)
            results.append(result)
        except Exception as e:
            await self.handle_agent_error(agent, e)
    return results

# ❌ Bad: Blocking operations
def execute_workflow_sequence(self, agents):
    results = []
    for agent in agents:
        result = agent.execute_sync(task_description, context)  # Blocking
        results.append(result)
    return results
```

### **Agent Hierarchy**
```python
# Base agent classes
BaseAgent                    # Core agent interface
├── BaseWorkflowAgent       # Workflow execution agents
│   ├── ScanAgent
│   ├── DeployAgent
│   ├── CampaignAgent
│   ├── AnalyticsAgent
│   ├── FinanceAgent
│   └── GrowthAgent
├── BaseCSuiteAgent         # Strategic decision agents
│   ├── CEOAgent
│   ├── CROAgent
│   ├── CTOAgent
│   └── CFOAgent
└── BaseOrchestrationAgent  # Coordination agents
    └── OrchestrationAgent
```

### **Communication Patterns**
```python
# Agent-to-Agent Communication
class AgentCommunicator:
    async def send_message(self, from_agent: str, to_agent: str, 
                          message: Dict[str, Any]) -> Dict[str, Any]:
        """Send structured message between agents"""
        
    async def broadcast_message(self, from_agent: str, 
                               message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Broadcast message to all agents"""
        
    async def request_peer_review(self, agent: str, 
                                 decision: Dict[str, Any]) -> Dict[str, Any]:
        """Request peer review of decision"""
```

---

## 🤖 **Agent Development**

### **Creating a New Workflow Agent**

#### **1. Agent Class Structure**
```python
# launchonomy/agents/workflow/my_new_agent.py
from typing import Dict, Any, List
from launchonomy.agents.base.workflow_agent import BaseWorkflowAgent

class MyNewAgent(BaseWorkflowAgent):
    """
    Agent for handling [specific business function]
    
    Responsibilities:
    - [Primary responsibility]
    - [Secondary responsibility]
    - [Tertiary responsibility]
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = "MyNewAgent"
        self.agent_description = "Handles [specific function]"
    
    async def execute(self, task_description: str, 
                     context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's primary function
        
        Args:
            task_description: Specific task to execute
            context: Mission context and previous results
            
        Returns:
            Dict containing execution results
        """
        try:
            # 1. Validate inputs
            self._validate_inputs(task_description, context)
            
            # 2. Execute core logic
            result = await self._execute_core_logic(task_description, context)
            
            # 3. Validate outputs
            self._validate_outputs(result)
            
            # 4. Return standardized response
            return {
                "status": "success",
                "data": result,
                "agent": self.agent_name,
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            return await self._handle_error(e, task_description, context)
    
    async def _execute_core_logic(self, task_description: str, 
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Implement the agent's core business logic"""
        # Your implementation here
        pass
    
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities"""
        return [
            "capability_1",
            "capability_2", 
            "capability_3"
        ]
    
    def get_required_tools(self) -> List[str]:
        """Return list of required tools"""
        return [
            "tool_1",
            "tool_2"
        ]
    
    def _validate_inputs(self, task_description: str, context: Dict[str, Any]):
        """Validate input parameters"""
        if not task_description:
            raise ValueError("Task description is required")
        if not context:
            raise ValueError("Context is required")
    
    def _validate_outputs(self, result: Dict[str, Any]):
        """Validate output format"""
        required_fields = ["key_field_1", "key_field_2"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required output field: {field}")
```

#### **2. Agent Registration**
```python
# launchonomy/registry/registry.json
{
    "agents": {
        "MyNewAgent": {
            "class_path": "launchonomy.agents.workflow.my_new_agent.MyNewAgent",
            "description": "Handles [specific function]",
            "capabilities": ["capability_1", "capability_2"],
            "required_tools": ["tool_1", "tool_2"],
            "status": "active",
            "version": "1.0.0"
        }
    }
}
```

#### **3. Agent Testing**
```python
# tests/agents/workflow/test_my_new_agent.py
import pytest
from launchonomy.agents.workflow.my_new_agent import MyNewAgent

class TestMyNewAgent:
    
    @pytest.fixture
    def agent(self):
        return MyNewAgent()
    
    @pytest.fixture
    def sample_context(self):
        return {
            "overall_mission": "Test mission",
            "budget_constraints": {"max_cost_ratio": 0.20},
            "previous_results": []
        }
    
    @pytest.mark.asyncio
    async def test_execute_success(self, agent, sample_context):
        """Test successful execution"""
        task_description = "Test task"
        result = await agent.execute(task_description, sample_context)
        
        assert result["status"] == "success"
        assert "data" in result
        assert result["agent"] == "MyNewAgent"
    
    @pytest.mark.asyncio
    async def test_execute_invalid_input(self, agent, sample_context):
        """Test handling of invalid inputs"""
        result = await agent.execute("", sample_context)
        assert result["status"] == "error"
    
    def test_get_capabilities(self, agent):
        """Test capabilities reporting"""
        capabilities = agent.get_capabilities()
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
    
    def test_get_required_tools(self, agent):
        """Test required tools reporting"""
        tools = agent.get_required_tools()
        assert isinstance(tools, list)
```

### **C-Suite Agent Development**

#### **C-Suite Agent Pattern**
```python
# launchonomy/agents/csuite/ceo_agent.py
from launchonomy.agents.base.csuite_agent import BaseCSuiteAgent

class CEOAgent(BaseCSuiteAgent):
    """
    Chief Executive Officer Agent
    
    Responsibilities:
    - Strategic oversight and direction
    - Final decision authority
    - Mission alignment and vision
    """
    
    def __init__(self):
        super().__init__()
        self.agent_name = "CEO-Agent"
        self.role = "Chief Executive Officer"
        self.decision_authority = "final"
    
    async def provide_strategic_input(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Provide CEO-level strategic input"""
        prompt = f"""
        As the CEO, analyze the current mission context and provide strategic guidance:
        
        Mission Context: {json.dumps(context, indent=2)}
        
        Please provide:
        1. Strategic priorities for this cycle
        2. Key risks and mitigation strategies
        3. Success metrics and KPIs
        4. Resource allocation recommendations
        5. Go/no-go decision with rationale
        """
        
        response = await self._get_llm_response(prompt)
        return self._parse_strategic_response(response)
    
    async def review_cycle_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Review and evaluate cycle results"""
        prompt = f"""
        As the CEO, review the cycle results and provide executive assessment:
        
        Cycle Results: {json.dumps(results, indent=2)}
        
        Please evaluate:
        1. Did we achieve our strategic objectives?
        2. What worked well and what didn't?
        3. What adjustments should we make?
        4. Should we continue or pivot?
        5. Next cycle priorities
        """
        
        response = await self._get_llm_response(prompt)
        return self._parse_review_response(response)
```

---

## 🔧 **Tool Development**

### **Tool Interface Pattern**
```python
# launchonomy/tools/base_tool.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseTool(ABC):
    """Base class for all tools"""
    
    def __init__(self):
        self.tool_name = ""
        self.tool_description = ""
        self.required_config = []
    
    @abstractmethod
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool action with parameters"""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate tool configuration"""
        pass
    
    @abstractmethod
    def get_available_actions(self) -> List[str]:
        """Get list of available actions"""
        pass
```

### **Example Tool Implementation**
```python
# launchonomy/tools/email_marketing.py
import aiohttp
from typing import Dict, Any, List
from launchonomy.tools.base_tool import BaseTool

class EmailMarketingTool(BaseTool):
    """Email marketing automation tool"""
    
    def __init__(self):
        super().__init__()
        self.tool_name = "email_marketing"
        self.tool_description = "Email campaign management and automation"
        self.required_config = ["api_key", "sender_email"]
        self.base_url = "https://api.emailservice.com/v1"
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute email marketing action"""
        if action not in self.get_available_actions():
            raise ValueError(f"Unknown action: {action}")
        
        if action == "send_campaign":
            return await self._send_campaign(parameters)
        elif action == "create_list":
            return await self._create_list(parameters)
        elif action == "add_subscriber":
            return await self._add_subscriber(parameters)
        elif action == "get_analytics":
            return await self._get_analytics(parameters)
    
    async def _send_campaign(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Send email campaign"""
        required_params = ["subject", "content", "recipient_list"]
        self._validate_parameters(parameters, required_params)
        
        payload = {
            "subject": parameters["subject"],
            "html_content": parameters["content"],
            "recipient_list_id": parameters["recipient_list"],
            "sender_email": self.config["sender_email"]
        }
        
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.config['api_key']}"}
            async with session.post(
                f"{self.base_url}/campaigns",
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "status": "success",
                        "campaign_id": result["id"],
                        "sent_count": result["sent_count"],
                        "cost": result["cost"]
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Email campaign failed: {error_text}")
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate tool configuration"""
        for key in self.required_config:
            if key not in config:
                return False
        return True
    
    def get_available_actions(self) -> List[str]:
        """Get available actions"""
        return [
            "send_campaign",
            "create_list", 
            "add_subscriber",
            "get_analytics"
        ]
    
    def _validate_parameters(self, parameters: Dict[str, Any], required: List[str]):
        """Validate required parameters"""
        for param in required:
            if param not in parameters:
                raise ValueError(f"Missing required parameter: {param}")
```

### **Tool Registration**
```python
# launchonomy/tools/__init__.py
from .email_marketing import EmailMarketingTool
from .hosting import HostingTool
from .analytics_platform import AnalyticsPlatformTool

AVAILABLE_TOOLS = {
    "email_marketing": EmailMarketingTool,
    "hosting": HostingTool,
    "analytics_platform": AnalyticsPlatformTool
}

def get_tool(tool_name: str) -> BaseTool:
    """Get tool instance by name"""
    if tool_name not in AVAILABLE_TOOLS:
        raise ValueError(f"Unknown tool: {tool_name}")
    return AVAILABLE_TOOLS[tool_name]()
```

---

## 🧪 **Testing Guidelines**

### **Test Structure**
```
tests/
├── unit/                   # Unit tests
│   ├── agents/
│   ├── core/
│   ├── tools/
│   └── utils/
├── integration/            # Integration tests
│   ├── test_workflow_sequence.py
│   ├── test_csuite_orchestration.py
│   └── test_mission_lifecycle.py
├── e2e/                   # End-to-end tests
│   └── test_complete_mission.py
└── fixtures/              # Test data and fixtures
    ├── sample_missions.json
    └── mock_responses.json
```

### **Testing Patterns**

#### **Unit Testing**
```python
# tests/unit/agents/test_scan_agent.py
import pytest
from unittest.mock import AsyncMock, patch
from launchonomy.agents.workflow.scan import ScanAgent

class TestScanAgent:
    
    @pytest.fixture
    def agent(self):
        return ScanAgent()
    
    @pytest.fixture
    def mock_context(self):
        return {
            "overall_mission": "Build AI newsletter service",
            "budget_constraints": {"max_cost_ratio": 0.20}
        }
    
    @pytest.mark.asyncio
    async def test_execute_success(self, agent, mock_context):
        """Test successful market scan execution"""
        with patch.object(agent, '_analyze_market_opportunities') as mock_analyze:
            mock_analyze.return_value = {
                "opportunities": [
                    {
                        "market": "AI newsletters",
                        "demand_score": 8.5,
                        "competition": "medium"
                    }
                ]
            }
            
            result = await agent.execute("Scan market opportunities", mock_context)
            
            assert result["status"] == "success"
            assert "opportunities" in result["data"]
            mock_analyze.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_with_invalid_context(self, agent):
        """Test handling of invalid context"""
        result = await agent.execute("Scan market", {})
        assert result["status"] == "error"
        assert "error_message" in result
```

#### **Integration Testing**
```python
# tests/integration/test_workflow_sequence.py
import pytest
from launchonomy.core.orchestrator import OrchestrationAgent
from launchonomy.core.mission_manager import MissionManager

class TestWorkflowSequence:
    
    @pytest.fixture
    async def orchestrator(self):
        mission_manager = MissionManager()
        orchestrator = OrchestrationAgent(mission_manager)
        await orchestrator.initialize()
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_complete_workflow_sequence(self, orchestrator):
        """Test complete workflow agent sequence"""
        mission = "Build simple SaaS application"
        
        # Execute workflow sequence
        result = await orchestrator.execute_workflow_sequence(mission)
        
        # Verify all agents executed
        assert len(result["workflow_results"]) == 6  # All 6 workflow agents
        
        # Verify sequence order
        agent_names = [r["agent"] for r in result["workflow_results"]]
        expected_order = ["ScanAgent", "DeployAgent", "CampaignAgent", 
                         "AnalyticsAgent", "FinanceAgent", "GrowthAgent"]
        assert agent_names == expected_order
        
        # Verify budget compliance
        total_cost = sum(r.get("cost", 0) for r in result["workflow_results"])
        assert total_cost > 0
        assert result["budget_status"] == "within_limits"
```

#### **End-to-End Testing**
```python
# tests/e2e/test_complete_mission.py
import pytest
import tempfile
import os
from launchonomy.cli import main

class TestCompleteMission:
    
    @pytest.mark.asyncio
    async def test_complete_mission_lifecycle(self):
        """Test complete mission from start to finish"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up test environment
            os.environ["MISSION_LOGS_DIR"] = temp_dir
            os.environ["OPENAI_API_KEY"] = "test-key"
            
            # Run mission
            mission = "Build test application"
            result = await main(mission, max_iterations=2)
            
            # Verify mission completion
            assert result["status"] == "completed"
            assert result["total_cycles"] >= 1
            assert result["total_cost"] > 0
            
            # Verify mission log created
            log_files = os.listdir(temp_dir)
            assert len(log_files) == 1
            assert log_files[0].startswith("mission_")
```

### **Test Configuration**
```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --cov=launchonomy
    --cov-report=html
    --cov-report=term-missing
    --asyncio-mode=auto
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
```

---

## 📏 **Code Standards**

### **Python Style Guide**

#### **Formatting**
```python
# Use Black for code formatting
black launchonomy/ tests/

# Configuration in pyproject.toml
[tool.black]
line-length = 88
target-version = ['py38']
include = '\.pyi?$'
```

#### **Linting**
```python
# Use flake8 for linting
flake8 launchonomy/ tests/

# Configuration in .flake8
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .git,__pycache__,venv
```

#### **Type Hints**
```python
# Use mypy for type checking
mypy launchonomy/

# Always use type hints
from typing import Dict, List, Optional, Any, Union

async def execute_agent(
    agent_name: str,
    task_description: str,
    context: Dict[str, Any],
    timeout: Optional[float] = None
) -> Dict[str, Any]:
    """Execute agent with proper type hints"""
    pass
```

### **Documentation Standards**

#### **Docstring Format**
```python
def complex_function(param1: str, param2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Brief description of what the function does.
    
    Longer description if needed, explaining the purpose,
    behavior, and any important details.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter
        
    Returns:
        Dict containing the result with keys:
        - status: Success/error status
        - data: Main result data
        - metadata: Additional information
        
    Raises:
        ValueError: When param1 is empty
        RuntimeError: When operation fails
        
    Example:
        >>> result = complex_function("test", {"key": "value"})
        >>> print(result["status"])
        "success"
    """
    pass
```

#### **Code Comments**
```python
# ✅ Good: Explain why, not what
def calculate_budget_ratio(spent: float, revenue: float) -> float:
    # Use 20% threshold to ensure profitability while allowing growth investment
    if revenue == 0:
        return float('inf')  # Prevent division by zero
    return spent / revenue

# ❌ Bad: Explain what (obvious from code)
def calculate_budget_ratio(spent: float, revenue: float) -> float:
    # Check if revenue is zero
    if revenue == 0:
        # Return infinity
        return float('inf')
    # Divide spent by revenue
    return spent / revenue
```

### **Error Handling Standards**

#### **Exception Hierarchy**
```python
# launchonomy/exceptions.py
class LaunchonomyError(Exception):
    """Base exception for all Launchonomy errors"""
    pass

class AgentError(LaunchonomyError):
    """Agent-related errors"""
    pass

class MissionError(LaunchonomyError):
    """Mission-related errors"""
    pass

class ToolError(LaunchonomyError):
    """Tool-related errors"""
    pass

class ConfigurationError(LaunchonomyError):
    """Configuration-related errors"""
    pass
```

#### **Error Handling Pattern**
```python
async def execute_with_error_handling(self, operation: str) -> Dict[str, Any]:
    """Standard error handling pattern"""
    try:
        result = await self._execute_operation(operation)
        return {
            "status": "success",
            "data": result
        }
    except AgentError as e:
        logger.error(f"Agent error in {operation}: {e}")
        return {
            "status": "error",
            "error_type": "agent_error",
            "error_message": str(e),
            "recoverable": True
        }
    except Exception as e:
        logger.exception(f"Unexpected error in {operation}")
        return {
            "status": "error",
            "error_type": "unexpected_error",
            "error_message": str(e),
            "recoverable": False
        }
```

---

## 🐛 **Debugging & Troubleshooting**

### **Logging Configuration**
```python
# Enhanced logging for debugging
import logging
from launchonomy.utils.logging import EnhancedLogger

# Set up debug logging
logger = EnhancedLogger("debug_session")
logger.set_level("DEBUG")

# Enable detailed AutoGen logging
logging.getLogger("autogen").setLevel(logging.DEBUG)
```

### **Common Issues & Solutions**

#### **Agent Execution Failures**
```python
# Debug agent execution
async def debug_agent_execution(agent_name: str, task: str, context: Dict[str, Any]):
    """Debug agent execution with detailed logging"""
    logger.info(f"Starting debug execution for {agent_name}")
    logger.debug(f"Task: {task}")
    logger.debug(f"Context: {json.dumps(context, indent=2)}")
    
    try:
        agent = await self.agent_manager.get_agent(agent_name)
        logger.debug(f"Agent loaded: {agent.__class__.__name__}")
        
        result = await agent.execute(task, context)
        logger.debug(f"Execution result: {json.dumps(result, indent=2)}")
        
        return result
    except Exception as e:
        logger.exception(f"Agent execution failed: {e}")
        # Add breakpoint for interactive debugging
        import pdb; pdb.set_trace()
        raise
```

#### **Mission Resume Issues**
```python
# Debug mission resume
def debug_mission_resume(mission_log_path: str):
    """Debug mission resume process"""
    with open(mission_log_path, 'r') as f:
        mission_data = json.load(f)
    
    print(f"Mission ID: {mission_data['mission_id']}")
    print(f"Status: {mission_data['final_status']}")
    print(f"Cycles: {len(mission_data['decision_cycles_summary'])}")
    
    # Check for corruption
    for i, cycle in enumerate(mission_data['decision_cycles_summary']):
        if 'status' not in cycle:
            print(f"WARNING: Cycle {i} missing status")
        if 'execution_output' not in cycle:
            print(f"WARNING: Cycle {i} missing execution_output")
```

### **Performance Profiling**
```python
# Profile mission execution
import cProfile
import pstats

def profile_mission_execution(mission: str):
    """Profile mission execution for performance analysis"""
    profiler = cProfile.Profile()
    
    profiler.enable()
    # Run mission
    result = asyncio.run(main(mission))
    profiler.disable()
    
    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions
    
    return result
```

---

## ⚡ **Performance Optimization**

### **Async Optimization**
```python
# ✅ Good: Concurrent execution
async def execute_agents_concurrently(self, agents: List[BaseAgent], 
                                    tasks: List[str]) -> List[Dict[str, Any]]:
    """Execute multiple agents concurrently"""
    tasks_coroutines = [
        agent.execute(task, self.context) 
        for agent, task in zip(agents, tasks)
    ]
    results = await asyncio.gather(*tasks_coroutines, return_exceptions=True)
    return self._process_concurrent_results(results)

# ❌ Bad: Sequential execution
async def execute_agents_sequentially(self, agents: List[BaseAgent], 
                                    tasks: List[str]) -> List[Dict[str, Any]]:
    """Execute agents one by one (slower)"""
    results = []
    for agent, task in zip(agents, tasks):
        result = await agent.execute(task, self.context)
        results.append(result)
    return results
```

### **Caching Strategies**
```python
# Cache expensive operations
from functools import lru_cache
import asyncio

class CachedAgentManager:
    def __init__(self):
        self._agent_cache = {}
        self._response_cache = {}
    
    @lru_cache(maxsize=128)
    def get_agent_capabilities(self, agent_name: str) -> List[str]:
        """Cache agent capabilities"""
        agent = self._load_agent(agent_name)
        return agent.get_capabilities()
    
    async def get_cached_response(self, prompt_hash: str) -> Optional[str]:
        """Get cached LLM response"""
        return self._response_cache.get(prompt_hash)
    
    async def cache_response(self, prompt_hash: str, response: str):
        """Cache LLM response"""
        self._response_cache[prompt_hash] = response
```

### **Memory Management**
```python
# Efficient memory usage
import gc
import weakref

class MemoryEfficientOrchestrator:
    def __init__(self):
        self._agent_refs = weakref.WeakValueDictionary()
        self._cleanup_interval = 100  # Cleanup every 100 operations
        self._operation_count = 0
    
    async def execute_with_cleanup(self, operation):
        """Execute operation with periodic cleanup"""
        try:
            result = await operation()
            return result
        finally:
            self._operation_count += 1
            if self._operation_count % self._cleanup_interval == 0:
                await self._cleanup_memory()
    
    async def _cleanup_memory(self):
        """Cleanup unused objects"""
        # Clear caches
        self._response_cache.clear()
        
        # Force garbage collection
        gc.collect()
        
        logger.debug("Memory cleanup completed")
```

---

## 🚀 **Development Workflow**

### **Git Workflow**
```bash
# Feature development workflow
git checkout -b feature/new-agent-type
git add .
git commit -m "feat: add new agent type with capabilities X, Y, Z"
git push origin feature/new-agent-type

# Create pull request
# After review and approval:
git checkout main
git pull origin main
git merge feature/new-agent-type
git push origin main
```

### **Pre-commit Hooks**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3.8
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
  
  - repo: local
    hooks:
      - id: tests
        name: tests
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

### **Release Process**
```bash
# Version bump and release
1. Update version in __init__.py
2. Update CHANGELOG.md
3. Run full test suite: pytest
4. Create release branch: git checkout -b release/v1.2.0
5. Tag release: git tag v1.2.0
6. Push: git push origin v1.2.0
7. Create GitHub release with changelog
```

This comprehensive development guide provides the foundation for contributing to Launchonomy while maintaining code quality, performance, and architectural consistency. 