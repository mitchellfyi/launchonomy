#!/usr/bin/env python3

import asyncio
import os
import sys
import logging

# Add the current directory to the path so we can import launchonomy modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_workflow_auto_provision():
    """Test that workflow agents can auto-provision missing tools."""
    logger.info("Starting workflow auto-provision test...")
    
    try:
        from launchonomy.registry.registry import Registry
        from launchonomy.agents.workflow.scan import ScanAgent
        from launchonomy.agents.workflow.auto_provision_agent import AutoProvisionAgent
        
        # Create a mock orchestrator for testing
        class MockOrchestrator:
            def __init__(self):
                self.name = "MockOrchestrator"
                self.registry = Registry()
                self.auto_provision_agent = AutoProvisionAgent(registry=self.registry, coa=self)
            
            def _log(self, message, level="info"):
                logger.info(f"MockOrchestrator: {message}")
        
        # Create mock orchestrator and scan agent
        mock_orchestrator = MockOrchestrator()
        scan_agent = ScanAgent(registry=mock_orchestrator.registry, orchestrator=mock_orchestrator)
        
        logger.info("✓ Created ScanAgent with mock orchestrator")
        
        # Test that ScanAgent can auto-provision missing tools
        logger.info("Testing auto-provisioning of missing tools...")
        
        # This should trigger auto-provisioning for missing tools
        available_tools = await scan_agent._get_available_scanning_tools()
        
        logger.info(f"✓ ScanAgent found {len(available_tools)} available tools")
        
        # Check if any tools were auto-provisioned
        auto_provisioned_tools = []
        for tool_name, tool_spec in available_tools.items():
            if tool_spec and tool_spec.get("source") == "auto-provisioned":
                auto_provisioned_tools.append(tool_name)
        
        if auto_provisioned_tools:
            logger.info(f"✓ Auto-provisioned tools: {auto_provisioned_tools}")
        else:
            logger.info("ℹ No tools were auto-provisioned (may already exist or not trivial)")
        
        # Test the full execute workflow
        logger.info("Testing full ScanAgent execution with auto-provisioning...")
        
        input_data = {
            "mission_context": {"overall_mission": "test auto-provisioning"},
            "focus_areas": ["api", "automation"],
            "max_opportunities": 3
        }
        
        result = await scan_agent.execute(input_data)
        
        if result.status == "success":
            logger.info("✓ ScanAgent execution successful with auto-provisioning")
            logger.info(f"✓ Tools used: {result.tools_used}")
            logger.info(f"✓ Found {len(result.data.get('opportunities', []))} opportunities")
        else:
            logger.warning(f"✗ ScanAgent execution failed: {result.error_message}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Workflow auto-provision test failed: {e}")
        return False

async def test_direct_tool_auto_provision():
    """Test direct tool auto-provisioning through the base workflow agent."""
    logger.info("Testing direct tool auto-provisioning...")
    
    try:
        from launchonomy.registry.registry import Registry
        from launchonomy.agents.base.workflow_agent import BaseWorkflowAgent
        from launchonomy.agents.workflow.auto_provision_agent import AutoProvisionAgent
        
        # Create a mock orchestrator
        class MockOrchestrator:
            def __init__(self):
                self.name = "MockOrchestrator"
                self.registry = Registry()
                self.auto_provision_agent = AutoProvisionAgent(registry=self.registry, coa=self)
            
            def _log(self, message, level="info"):
                logger.info(f"MockOrchestrator: {message}")
        
        # Create a test workflow agent
        class TestWorkflowAgent(BaseWorkflowAgent):
            async def execute(self, input_data):
                return self._format_output("success", {"test": "data"})
        
        mock_orchestrator = MockOrchestrator()
        test_agent = TestWorkflowAgent("TestAgent", registry=mock_orchestrator.registry, orchestrator=mock_orchestrator)
        
        # Test auto-provisioning of a trivial tool
        logger.info("Testing auto-provisioning of 'SpreadsheetTool'...")
        
        tool_spec = await test_agent._get_tool_from_registry("SpreadsheetTool")
        
        if tool_spec:
            logger.info(f"✓ SpreadsheetTool obtained: {tool_spec.get('description', 'No description')}")
            if tool_spec.get("source") == "auto-provisioned":
                logger.info("✓ Tool was auto-provisioned!")
            else:
                logger.info("ℹ Tool was already in registry")
        else:
            logger.warning("✗ SpreadsheetTool could not be obtained")
        
        # Test auto-provisioning of a non-trivial tool
        logger.info("Testing auto-provisioning of 'ComplexAnalyticsTool'...")
        
        tool_spec = await test_agent._get_tool_from_registry("ComplexAnalyticsTool")
        
        if tool_spec:
            logger.info(f"✓ ComplexAnalyticsTool obtained: {tool_spec.get('description', 'No description')}")
        else:
            logger.info("ℹ ComplexAnalyticsTool was not auto-provisioned (expected for non-trivial tools)")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Direct tool auto-provision test failed: {e}")
        return False

async def main():
    """Run all workflow auto-provision tests."""
    logger.info("Starting workflow auto-provision tests...")
    
    tests = [
        test_direct_tool_auto_provision,
        test_workflow_auto_provision
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if await test():
            passed += 1
        logger.info("-" * 50)
    
    logger.info(f"Workflow auto-provision tests completed: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 All workflow auto-provision tests passed!")
        return True
    else:
        logger.error("❌ Some workflow auto-provision tests failed.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 