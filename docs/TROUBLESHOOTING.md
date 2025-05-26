# Troubleshooting Guide

## 🚨 **Overview**

This guide provides solutions to common issues encountered when running Launchonomy, from setup problems to runtime errors and performance issues.

## 📋 **Table of Contents**

1. [Installation & Setup Issues](#installation--setup-issues)
2. [Runtime Errors](#runtime-errors)
3. [Mission Execution Problems](#mission-execution-problems)
4. [Performance Issues](#performance-issues)
5. [AutoGen Integration Issues](#autogen-integration-issues)
6. [Logging & Debugging](#logging--debugging)
7. [Recovery Procedures](#recovery-procedures)

---

## 🛠️ **Installation & Setup Issues**

### **Issue: Python Version Compatibility**
```bash
# Error
ERROR: Python 3.7 is not supported. Requires Python 3.8+

# Solution
# Install Python 3.8 or higher
pyenv install 3.8.10
pyenv global 3.8.10
# Or use conda
conda create -n launchonomy python=3.8
conda activate launchonomy
```

### **Issue: Missing Dependencies**
```bash
# Error
ModuleNotFoundError: No module named 'autogen'

# Solution
pip install -r requirements.txt
# If still failing, try upgrading pip
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### **Issue: OpenAI API Key Not Found**
```bash
# Error
openai.AuthenticationError: No API key provided

# Solution 1: Environment variable
export OPENAI_API_KEY="your-api-key-here"

# Solution 2: .env file
echo "OPENAI_API_KEY=your-api-key-here" > .env

# Solution 3: Verify key is loaded
python -c "import os; print('API Key:', os.getenv('OPENAI_API_KEY', 'NOT FOUND'))"
```

### **Issue: Permission Denied on Mission Workspaces**
```bash
# Error
PermissionError: [Errno 13] Permission denied: '.launchonomy/'

# Solution
# Create directory with proper permissions
mkdir -p .launchonomy
chmod 755 .launchonomy

# Note: Running with sudo is not recommended for security reasons
```

---

## ⚠️ **Runtime Errors**

### **Issue: JSON Parsing Errors**
```python
# Error
json.JSONDecodeError: Expecting ',' delimiter: line 1 column 45

# Symptoms
- Agent responses contain natural language instead of JSON
- Mission logs show parsing failures
- Workflow execution stops unexpectedly

# Solution
# The system has built-in fallback handling, but you can debug:
python -c "
from launchonomy.core.communication import AgentCommunicator
comm = AgentCommunicator()
# Test with problematic response
response = 'This is not JSON but natural language'
result = comm.parse_json_with_fallback(response)
print(result)
"

# Prevention
# Ensure prompts clearly request JSON format:
prompt = '''
Please respond in valid JSON format:
{
    "status": "success|error",
    "data": {...},
    "reasoning": "explanation"
}
'''
```

### **Issue: Agent Loading Failures**
```python
# Error
ImportError: cannot import name 'ScanAgent' from 'launchonomy.agents.workflow.scan'

# Diagnosis
python -c "
import sys
sys.path.append('.')
try:
    from launchonomy.agents.workflow.scan import ScanAgent
    print('✅ ScanAgent loaded successfully')
except ImportError as e:
    print(f'❌ Import failed: {e}')
"

# Solution 1: Check file exists
ls -la launchonomy/agents/workflow/scan.py

# Solution 2: Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Solution 3: Reinstall in development mode
pip install -e .
```

### **Issue: Async/Await Errors**
```python
# Error
RuntimeError: This event loop is already running

# Common cause
# Mixing sync and async code incorrectly

# Solution
# Use proper async patterns:
import asyncio

# ✅ Correct
async def main():
    result = await some_async_function()
    return result

if __name__ == "__main__":
    result = asyncio.run(main())

# ❌ Incorrect
def main():
    result = asyncio.run(some_async_function())  # Inside already running loop
    return result
```

### **Issue: Memory Leaks**
```python
# Symptoms
- Gradually increasing memory usage
- System becomes slow over time
- Out of memory errors

# Diagnosis
import psutil
import os

def check_memory_usage():
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"Memory usage: {memory_mb:.2f} MB")

# Solution
# Enable memory cleanup in orchestrator
from launchonomy.core.orchestrator import OrchestrationAgent

orchestrator = OrchestrationAgent()
orchestrator.enable_memory_cleanup = True
orchestrator.cleanup_interval = 50  # Every 50 operations
```

---

## 🎯 **Mission Execution Problems**

### **Issue: Mission Stuck in Loop**
```python
# Symptoms
- Same cycle repeating endlessly
- No progress toward mission goals
- High token usage without results

# Diagnosis
# Check mission workspace for patterns
python -m launchonomy.cli_workspace list

# Look for:
# - Repeated identical cycles
# - No revenue generation
# - Same errors recurring

# Solution 1: Set iteration limits
python main.py "Your mission" --max-iterations 5

# Solution 2: Add cycle detection
# The system automatically detects loops after 3 identical cycles
```

### **Issue: Budget Guardrail Violations**
```python
# Error
FinanceAgent: BUDGET_VIOLATION - Cost ratio 0.25 exceeds limit 0.20

# Diagnosis
# Check spending breakdown in mission log
{
    "total_mission_cost": 250.00,
    "revenue_generated": 100.00,
    "cost_ratio": 0.25,  # 25% > 20% limit
    "budget_status": "VIOLATION"
}

# Solution 1: Increase revenue focus
# Modify mission to emphasize quick revenue generation

# Solution 2: Adjust budget limits (temporary)
# In mission context:
mission_context = {
    "budget_constraints": {"max_cost_ratio": 0.30}  # Increase to 30%
}

# Solution 3: Review spending patterns
# Check which agents are consuming most budget
```

### **Issue: No Revenue Generation**
```python
# Symptoms
- Multiple cycles completed
- Products deployed
- Campaigns running
- Zero revenue

# Diagnosis
# Check analytics agent results
{
    "analytics_setup": "complete",
    "current_performance": {
        "signups": 150,
        "paying_customers": 0,  # ❌ Problem here
        "revenue": 0.00
    }
}

# Common causes
1. Payment integration not working
2. Pricing too high
3. Value proposition unclear
4. Technical issues preventing purchases

# Solution
# Force payment system check
python -c "
from launchonomy.tools.payment_processing import PaymentProcessingTool
tool = PaymentProcessingTool()
status = tool.check_integration_status()
print(f'Payment status: {status}')
"
```

### **Issue: Agent Execution Timeouts**
```python
# Error
asyncio.TimeoutError: Agent execution exceeded 60 seconds

# Diagnosis
# Check which agent is timing out
# Look for patterns in mission logs

# Solution 1: Increase timeout
from launchonomy.core.orchestrator import OrchestrationAgent

orchestrator = OrchestrationAgent()
orchestrator.agent_timeout = 120  # Increase to 2 minutes

# Solution 2: Optimize agent prompts
# Reduce complexity of agent tasks
# Break large tasks into smaller ones

# Solution 3: Check API rate limits
# OpenAI API might be rate limiting
```

---

## 🐌 **Performance Issues**

### **Issue: Slow Mission Execution**
```python
# Symptoms
- Each cycle takes > 5 minutes
- High latency between agent calls
- Excessive token usage

# Diagnosis
import time
from launchonomy.utils.logging import EnhancedLogger

logger = EnhancedLogger("performance")

# Profile agent execution
start_time = time.time()
result = await agent.execute(task, context)
execution_time = time.time() - start_time
logger.info(f"Agent execution time: {execution_time:.2f}s")

# Solution 1: Enable concurrent execution
# Modify orchestrator to run compatible agents in parallel

# Solution 2: Optimize prompts
# Reduce prompt length
# Use more specific instructions
# Cache common responses

# Solution 3: Use faster model
export OPENAI_MODEL="gpt-4o-mini"  # Faster than gpt-4
```

### **Issue: High Token Usage**
```python
# Symptoms
- Rapid API cost increase
- Token counts in hundreds of thousands
- Budget exceeded quickly

# Diagnosis
# Check token usage breakdown
{
    "total_input_tokens": 45000,
    "total_output_tokens": 25000,
    "estimated_cost": "$35.00"
}

# Solution 1: Optimize prompts
# Remove unnecessary context
# Use shorter, more focused prompts
# Implement prompt templates

# Solution 2: Enable response caching
from launchonomy.utils.caching import ResponseCache

cache = ResponseCache()
cache.enable_caching = True
cache.cache_duration = 3600  # 1 hour

# Solution 3: Use cheaper model for simple tasks
# Use gpt-4o-mini for routine operations
# Reserve gpt-4 for complex decisions
```

### **Issue: Database/File I/O Bottlenecks**
```python
# Symptoms
- Slow mission log writes
- File system errors
- Disk space issues

# Diagnosis
import os
import shutil

def check_disk_space():
    total, used, free = shutil.disk_usage(".")
    print(f"Free space: {free // (1024**3)} GB")

# Solution 1: Optimize logging
# Reduce log verbosity
# Implement log rotation
# Use async file writes

# Solution 2: Clean up old logs
find .launchonomy/ -name "*.json" -mtime +30 -delete

# Solution 3: Use database for large deployments
# Consider PostgreSQL for production use
```

---

## 🔧 **AutoGen Integration Issues**

### **Issue: AutoGen Version Conflicts**
```python
# Error
AttributeError: module 'autogen' has no attribute 'OpenAIChatCompletionClient'

# Diagnosis
python -c "import autogen; print(f'AutoGen version: {autogen.__version__}')"

# Solution
# Ensure AutoGen v0.4+ is installed
pip install "pyautogen>=0.4.0"
pip install --upgrade pyautogen

# Verify installation
python -c "
from autogen import OpenAIChatCompletionClient
print('✅ AutoGen v0.4 features available')
"
```

### **Issue: Model Client Configuration**
```python
# Error
openai.BadRequestError: Invalid model specified

# Diagnosis
# Check model availability
python -c "
from autogen import OpenAIChatCompletionClient
client = OpenAIChatCompletionClient(model='gpt-4o-mini')
print('✅ Model client created successfully')
"

# Solution
# Use supported models
SUPPORTED_MODELS = [
    "gpt-4o-mini",
    "gpt-4o", 
    "gpt-4-turbo",
    "gpt-3.5-turbo"
]

# Update configuration
export OPENAI_MODEL="gpt-4o-mini"
```

### **Issue: Message Format Errors**
```python
# Error
TypeError: Expected SystemMessage or UserMessage, got dict

# Diagnosis
# Check message format in agent communication

# Solution
from autogen import SystemMessage, UserMessage

# ✅ Correct format
messages = [
    SystemMessage(content="You are a helpful assistant"),
    UserMessage(content="Execute this task")
]

# ❌ Incorrect format
messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Execute this task"}
]
```

---

## 📊 **Logging & Debugging**

### **Enable Debug Logging**
```python
# Set environment variable
export LAUNCHONOMY_LOG_LEVEL=DEBUG

# Or in code
from launchonomy.utils.logging import EnhancedLogger

logger = EnhancedLogger("debug")
logger.set_level("DEBUG")

# Enable AutoGen debug logging
import logging
logging.getLogger("autogen").setLevel(logging.DEBUG)
```

### **Mission Log Analysis**
```python
# Analyze mission logs for issues
python launchonomy/utils/mission_log_navigator.py

# Or programmatically
import json

def analyze_mission_log(log_path):
    with open(log_path, 'r') as f:
        data = json.load(f)
    
    print(f"Mission: {data['overall_mission']}")
    print(f"Status: {data['final_status']}")
    print(f"Cycles: {len(data['decision_cycles_summary'])}")
    print(f"Cost: ${data['total_mission_cost']:.2f}")
    
    # Check for errors
    errors = []
    for cycle in data['decision_cycles_summary']:
        if 'error' in cycle.get('execution_output', {}):
            errors.append(cycle['execution_output']['error'])
    
    if errors:
        print(f"Errors found: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
```

### **Real-time Monitoring**
```python
# Monitor mission execution in real-time
import asyncio
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MissionLogMonitor(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.json'):
            print(f"Mission log updated: {event.src_path}")
            # Analyze latest changes

# Start monitoring
observer = Observer()
observer.schedule(MissionLogMonitor(), ".launchonomy/", recursive=False)
observer.start()
```

---

## 🔄 **Recovery Procedures**

### **Corrupted Mission Recovery**
```python
# If mission log is corrupted
def recover_mission_log(corrupted_log_path):
    """Attempt to recover corrupted mission log"""
    try:
        with open(corrupted_log_path, 'r') as f:
            content = f.read()
        
        # Try to fix common JSON issues
        content = content.replace('}{', '},{')  # Missing commas
        content = content.strip()
        if not content.endswith('}'):
            content += '}'
        
        # Validate JSON
        data = json.loads(content)
        
        # Save recovered version
        backup_path = corrupted_log_path + '.recovered'
        with open(backup_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Mission log recovered: {backup_path}")
        return data
        
    except Exception as e:
        print(f"❌ Recovery failed: {e}")
        return None
```

### **Reset Mission State**
```python
# If mission is stuck, reset to clean state
def reset_mission_state(mission_id):
    """Reset mission to clean state"""
    import os
    import glob
    
    # Backup current state
    backup_dir = f"backups/{mission_id}"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Find mission files
    mission_files = glob.glob(f".launchonomy/*{mission_id}*")
    
    for file_path in mission_files:
        # Create backup
        backup_path = os.path.join(backup_dir, os.path.basename(file_path))
        shutil.copy2(file_path, backup_path)
        
        # Reset mission status
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        data['final_status'] = 'started'
        data['decision_cycles_summary'] = []
        data['total_mission_cost'] = 0.0
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    print(f"✅ Mission {mission_id} reset to clean state")
    print(f"📁 Backup created in: {backup_dir}")
```

### **Emergency Stop Procedure**
```python
# Emergency stop for runaway missions
def emergency_stop():
    """Emergency stop procedure"""
    import signal
    import os
    
    # Create stop signal file
    with open('.emergency_stop', 'w') as f:
        f.write('STOP')
    
    # Kill any running processes
    os.system("pkill -f 'python.*main.py'")
    
    print("🚨 Emergency stop activated")
    print("Remove .emergency_stop file to resume operations")

# Check for emergency stop in main loop
def check_emergency_stop():
    if os.path.exists('.emergency_stop'):
        print("🚨 Emergency stop detected - halting execution")
        exit(1)
```

---

## 🆘 **Getting Help**

### **Diagnostic Information Collection**
```python
# Collect system information for support
def collect_diagnostic_info():
    """Collect diagnostic information"""
    import sys
    import platform
    import pkg_resources
    
    info = {
        "system": {
            "platform": platform.platform(),
            "python_version": sys.version,
            "architecture": platform.architecture()
        },
        "packages": {
            pkg.project_name: pkg.version 
            for pkg in pkg_resources.working_set
            if pkg.project_name in ['pyautogen', 'openai', 'aiohttp']
        },
        "environment": {
            "openai_api_key_set": bool(os.getenv('OPENAI_API_KEY')),
            "openai_model": os.getenv('OPENAI_MODEL', 'not_set')
        }
    }
    
    print("📋 Diagnostic Information:")
    print(json.dumps(info, indent=2))
    return info
```

### **Common Error Patterns**
```python
# Pattern: Rate limiting
if "rate_limit_exceeded" in error_message:
    print("💡 Solution: Reduce request frequency or upgrade API plan")

# Pattern: Token limit exceeded  
if "maximum context length" in error_message:
    print("💡 Solution: Reduce prompt length or use conversation summarization")

# Pattern: Network connectivity
if "connection" in error_message.lower():
    print("💡 Solution: Check internet connection and API endpoint availability")

# Pattern: Authentication
if "authentication" in error_message.lower():
    print("💡 Solution: Verify OpenAI API key is correct and has sufficient credits")
```

### **Support Checklist**
Before seeking help, ensure you have:

- ✅ **System Information**: Python version, OS, package versions
- ✅ **Error Messages**: Complete error traceback
- ✅ **Mission Context**: What mission was running when error occurred
- ✅ **Reproduction Steps**: How to reproduce the issue
- ✅ **Log Files**: Relevant mission logs and debug output
- ✅ **Configuration**: Environment variables and settings used

### **Self-Help Resources**
1. **Check Documentation**: README.md, AUTOGEN_ARCHITECTURE.md
2. **Search Logs**: Use mission log navigator for patterns
3. **Test Components**: Run individual agents/tools in isolation
4. **Check Dependencies**: Verify all packages are correctly installed
5. **Review Configuration**: Ensure environment variables are set correctly

This troubleshooting guide covers the most common issues encountered in Launchonomy. For issues not covered here, collect diagnostic information and follow the support checklist for the most effective assistance. 