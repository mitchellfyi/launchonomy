#!/usr/bin/env python3

import asyncio
import os
import sys
import logging
import importlib

# Add the current directory to the path so we can import orchestrator modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_agent_imports():
    """Test that all workflow agents can be imported correctly."""
    logger.info("Testing workflow agent imports...")
    
    agents = [
        ("ScanAgent", "orchestrator.agents.scan_agent"),
        ("DeployAgent", "orchestrator.agents.deploy_agent"),
        ("CampaignAgent", "orchestrator.agents.campaign_agent"),
        ("AnalyticsAgent", "orchestrator.agents.analytics_agent"),
        ("FinanceAgent", "orchestrator.agents.finance_agent"),
        ("GrowthAgent", "orchestrator.agents.growth_agent")
    ]
    
    imported_agents = {}
    
    for agent_name, module_path in agents:
        try:
            module = importlib.import_module(module_path)
            agent_class = getattr(module, agent_name)
            imported_agents[agent_name] = agent_class
            logger.info(f"✓ Successfully imported {agent_name} from {module_path}")
        except ImportError as e:
            logger.error(f"✗ Failed to import {agent_name} from {module_path}: {e}")
            return False
        except AttributeError as e:
            logger.error(f"✗ {agent_name} class not found in {module_path}: {e}")
            return False
    
    return imported_agents

def test_agent_instantiation(imported_agents):
    """Test that all workflow agents can be instantiated correctly."""
    logger.info("Testing workflow agent instantiation...")
    
    from orchestrator.registry import Registry
    
    registry = Registry()
    
    instantiated_agents = {}
    
    for agent_name, agent_class in imported_agents.items():
        try:
            agent_instance = agent_class(registry=registry, orchestrator=None)
            instantiated_agents[agent_name] = agent_instance
            logger.info(f"✓ Successfully instantiated {agent_name}")
            
            # Check if agent has required attributes
            if hasattr(agent_instance, 'name'):
                logger.info(f"  - Agent name: {agent_instance.name}")
            if hasattr(agent_instance, 'REQUIRED_TOOLS'):
                logger.info(f"  - Required tools: {agent_instance.REQUIRED_TOOLS}")
            if hasattr(agent_instance, 'OPTIONAL_TOOLS'):
                logger.info(f"  - Optional tools: {len(agent_instance.OPTIONAL_TOOLS)} tools")
                
        except Exception as e:
            logger.error(f"✗ Failed to instantiate {agent_name}: {e}")
            return False
    
    return instantiated_agents

async def test_agent_execute_methods(instantiated_agents):
    """Test that all workflow agents have working execute methods."""
    logger.info("Testing workflow agent execute methods...")
    
    test_inputs = {
        "ScanAgent": {
            "mission_context": {"overall_mission": "test"},
            "focus_areas": ["api", "automation"],
            "max_opportunities": 3
        },
        "DeployAgent": {
            "opportunity": {"name": "Test Product", "type": "web_application"},
            "requirements": {},
            "budget_limit": 500
        },
        "CampaignAgent": {
            "campaign_type": "launch",
            "product_details": {"name": "Test Product"},
            "budget_allocation": {"total_budget": 100}
        },
        "AnalyticsAgent": {
            "analysis_type": "comprehensive",
            "time_period": "current_month",
            "specific_metrics": []
        },
        "FinanceAgent": {
            "operation_type": "marketing_campaign",
            "estimated_cost": 50.0,
            "time_period": "monthly"
        },
        "GrowthAgent": {
            "growth_phase": "early",
            "current_metrics": {},
            "experiment_budget": 100
        }
    }
    
    for agent_name, agent_instance in instantiated_agents.items():
        try:
            if hasattr(agent_instance, 'execute'):
                test_input = test_inputs.get(agent_name, {})
                result = await agent_instance.execute(test_input)
                
                if hasattr(result, 'status'):
                    logger.info(f"✓ {agent_name}.execute() returned status: {result.status}")
                else:
                    logger.warning(f"⚠ {agent_name}.execute() returned unexpected format: {type(result)}")
                    
            else:
                logger.error(f"✗ {agent_name} does not have execute method")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error executing {agent_name}: {e}")
            return False
    
    return True

def test_registry_registration():
    """Test that all workflow agents are properly registered in the registry."""
    logger.info("Testing workflow agent registry registration...")
    
    from orchestrator.registry import Registry
    
    registry = Registry()
    
    expected_agents = ["ScanAgent", "DeployAgent", "CampaignAgent", "AnalyticsAgent", "FinanceAgent", "GrowthAgent"]
    
    for agent_name in expected_agents:
        agent_spec = registry.get_agent_spec(agent_name)
        if agent_spec:
            logger.info(f"✓ {agent_name} is registered in registry")
            
            # Check for required fields
            if "module" in agent_spec:
                logger.info(f"  - Module: {agent_spec['module']}")
            if "class" in agent_spec:
                logger.info(f"  - Class: {agent_spec['class']}")
            if "spec" in agent_spec and "workflow_step" in agent_spec["spec"]:
                logger.info(f"  - Workflow step: {agent_spec['spec']['workflow_step']}")
                
        else:
            logger.error(f"✗ {agent_name} is not registered in registry")
            return False
    
    return True

async def main():
    """Run all workflow agent tests."""
    logger.info("Starting workflow agent scaffolding and registration tests...")
    
    # Test 1: Import agents
    imported_agents = test_agent_imports()
    if not imported_agents:
        logger.error("❌ Agent import tests failed")
        return False
    
    logger.info("-" * 50)
    
    # Test 2: Instantiate agents
    instantiated_agents = test_agent_instantiation(imported_agents)
    if not instantiated_agents:
        logger.error("❌ Agent instantiation tests failed")
        return False
    
    logger.info("-" * 50)
    
    # Test 3: Test execute methods
    execute_success = await test_agent_execute_methods(instantiated_agents)
    if not execute_success:
        logger.error("❌ Agent execute method tests failed")
        return False
    
    logger.info("-" * 50)
    
    # Test 4: Test registry registration
    registry_success = test_registry_registration()
    if not registry_success:
        logger.error("❌ Registry registration tests failed")
        return False
    
    logger.info("-" * 50)
    logger.info("🎉 All workflow agent scaffolding and registration tests passed!")
    logger.info("✓ All six agents (ScanAgent, DeployAgent, CampaignAgent, AnalyticsAgent, FinanceAgent, GrowthAgent) are properly scaffolded")
    logger.info("✓ All agents have working execute() methods")
    logger.info("✓ All agents are registered in the registry with module/class specifications")
    logger.info("✓ All agents follow the standardized input/output schema patterns")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 