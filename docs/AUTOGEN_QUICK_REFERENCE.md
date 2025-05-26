# AutoGen Integration Quick Reference

## 🚀 **Quick Start**

### **What We Use vs. What We Built**

| Component | AutoGen | Custom | Why |
|-----------|---------|--------|-----|
| **Model Client** | ✅ `OpenAIChatCompletionClient` | Enhanced wrapper | Reliability + monitoring |
| **Message Types** | ✅ `SystemMessage`, `UserMessage` | - | Standardization |
| **Base Agents** | ✅ `RoutedAgent` | Business logic on top | Foundation + custom behavior |
| **Orchestration** | ❌ Teams/Selector | C-Suite consensus | Business domain expertise |
| **State Management** | ❌ Built-in state | Mission logs | Business continuity |
| **Workflows** | ❌ GraphFlow | Workflow agents | Business operations |

## 🔧 **Common Patterns**

### **Creating an Enhanced Client**
```python
from launchonomy.cli import EnhancedOpenAIClient

enhanced_client = EnhancedOpenAIClient(
    monitor=monitor,
    api_key=api_key,
    model="gpt-4o-mini",
    timeout=60.0,
    max_retries=3,
    retry_delay=1.0
)
```

### **Agent Communication with History**
```python
from launchonomy.core.communication import EnhancedAgentCommunicator

communicator = EnhancedAgentCommunicator()

# Basic communication
response, cost = await communicator.ask_agent(agent, "Hello")

# With conversation history
response, cost = await communicator.ask_agent(
    agent, 
    "Continue our discussion", 
    include_history=True
)
```

### **Structured Logging**
```python
from launchonomy.utils.logging import EnhancedLogger, ErrorCategory

logger = EnhancedLogger("MyComponent")

# Basic logging
logger.info("Processing request", agent_id="agent_1", cost=0.05)

# Error with context
logger.log_error_with_context(
    error=exception,
    context={"agent": "agent_1", "operation": "decision"},
    category=ErrorCategory.COMMUNICATION
)

# Get analytics
summary = logger.get_error_summary()
```

### **Creating Custom Agents**
```python
from autogen_core import RoutedAgent

class MyBusinessAgent(RoutedAgent):
    def __init__(self, client, business_context):
        super().__init__("You are a business specialist...")
        self._client = client
        self.business_context = business_context
    
    async def make_business_decision(self, scenario):
        # Use AutoGen foundation with business logic
        response = await self._client.create([
            SystemMessage(content=self.system_prompt, source="system"),
            UserMessage(content=scenario, source="user")
        ])
        return self.process_business_response(response)
```

## 📋 **Integration Checklist**

### **When Adding New Features**

- [ ] **Use AutoGen for infrastructure** (clients, messages, base agents)
- [ ] **Build custom for business logic** (workflows, state, orchestration)
- [ ] **Maintain backward compatibility** (use aliases if needed)
- [ ] **Add structured logging** (with cost and error tracking)
- [ ] **Include conversation history** (for complex interactions)
- [ ] **Handle errors gracefully** (with categorization)
- [ ] **Track costs and tokens** (for business analytics)

### **When Upgrading AutoGen**

- [ ] **Test enhanced client** (verify timeout/retry behavior)
- [ ] **Check message compatibility** (SystemMessage/UserMessage)
- [ ] **Validate token tracking** (ensure cost monitoring works)
- [ ] **Test error handling** (verify categorization still works)
- [ ] **Run integration tests** (full workflow validation)

## 🎯 **Best Practices**

### **DO Use AutoGen For:**
- ✅ Model client management
- ✅ Message standardization
- ✅ Base agent functionality
- ✅ Connection pooling
- ✅ Retry logic
- ✅ Token tracking

### **DON'T Use AutoGen For:**
- ❌ Business orchestration
- ❌ State management
- ❌ Workflow definition
- ❌ Business logic
- ❌ Cost management
- ❌ Approval processes

### **Always Custom Build For:**
- 🎯 C-Suite consensus
- 🎯 Mission management
- 🎯 Business workflows
- 🎯 Peer reviews
- 🎯 Cost tracking
- 🎯 Human-in-loop

## 🔍 **Troubleshooting**

### **Common Issues**

| Issue | AutoGen Related? | Solution |
|-------|------------------|----------|
| Connection timeouts | ✅ Yes | Check `EnhancedOpenAIClient` timeout settings |
| Rate limiting | ✅ Yes | AutoGen retry logic should handle automatically |
| Token tracking missing | ✅ Yes | Verify `enhanced_client` is being used |
| Agent creation fails | ❌ No | Check `AgentManager` business logic |
| Mission resume fails | ❌ No | Check `OverallMissionLog` state management |
| Workflow execution fails | ❌ No | Check workflow agent implementation |

### **Debug Commands**
```python
# Test AutoGen integration
from launchonomy.cli import EnhancedOpenAIClient
client = EnhancedOpenAIClient(monitor=mock_monitor, api_key="test")

# Test communication
from launchonomy.core.communication import EnhancedAgentCommunicator
comm = EnhancedAgentCommunicator()

# Test logging
from launchonomy.utils.logging import EnhancedLogger
logger = EnhancedLogger("Debug")
logger.info("Testing integration")
```

## 📚 **Key Files**

| File | Purpose | AutoGen Usage |
|------|---------|---------------|
| `launchonomy/cli.py` | Enhanced client wrapper | Heavy AutoGen usage |
| `launchonomy/core/communication.py` | Message handling | Medium AutoGen usage |
| `launchonomy/core/orchestrator.py` | Business orchestration | Light AutoGen usage |
| `launchonomy/utils/logging.py` | Structured logging | No AutoGen usage |
| `launchonomy/agents/workflow/` | Business workflows | No AutoGen usage |

## 🔄 **Migration Path**

### **From Pure AutoGen → Hybrid**
1. Keep AutoGen for infrastructure
2. Add custom business layer on top
3. Maintain clear separation of concerns

### **From Custom → Hybrid**
1. Replace low-level client code with AutoGen
2. Standardize message types
3. Keep business logic custom

### **Future AutoGen Adoption**
1. Evaluate new features against business needs
2. Adopt infrastructure improvements
3. Keep business logic proprietary 