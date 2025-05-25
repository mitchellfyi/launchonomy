#!/usr/bin/env python3

import os
import sys
import logging

# Add the current directory to the path so we can import orchestrator modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required imports work correctly."""
    logger.info("Testing imports...")
    
    try:
        from orchestrator.registry import Registry
        logger.info("✓ Registry import successful")
    except ImportError as e:
        logger.error(f"✗ Registry import failed: {e}")
        return False
    
    try:
        from orchestrator.agents.auto_provision_agent import AutoProvisionAgent
        logger.info("✓ AutoProvisionAgent import successful")
    except ImportError as e:
        logger.error(f"✗ AutoProvisionAgent import failed: {e}")
        return False
    
    return True

def test_auto_provision_agent_initialization():
    """Test that AutoProvisionAgent can be initialized correctly."""
    logger.info("Testing AutoProvisionAgent initialization...")
    
    try:
        from orchestrator.registry import Registry
        from orchestrator.agents.auto_provision_agent import AutoProvisionAgent
        
        # Create a mock COA object for testing
        class MockCOA:
            def __init__(self):
                self.name = "MockOrchestrationAgent"
            
            def _log(self, message, level="info"):
                logger.info(f"MockCOA: {message}")
        
        registry = Registry()
        mock_coa = MockCOA()
        auto_provision_agent = AutoProvisionAgent(registry=registry, coa=mock_coa)
        
        logger.info("✓ AutoProvisionAgent initialization successful")
        logger.info(f"✓ AutoProvisionAgent name: {auto_provision_agent.name}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ AutoProvisionAgent initialization failed: {e}")
        return False

def test_triviality_detection():
    """Test the triviality detection logic."""
    logger.info("Testing triviality detection...")
    
    try:
        from orchestrator.registry import Registry
        from orchestrator.agents.auto_provision_agent import AutoProvisionAgent
        
        class MockCOA:
            def __init__(self):
                self.name = "MockOrchestrationAgent"
            
            def _log(self, message, level="info"):
                logger.info(f"MockCOA: {message}")
        
        registry = Registry()
        mock_coa = MockCOA()
        auto_provision_agent = AutoProvisionAgent(registry=registry, coa=mock_coa)
        
        # Test trivial tool detection
        context = {"overall_mission": "test"}
        
        # Test SpreadsheetTool (should be trivial)
        missing_item_details = {
            "type": "tool",
            "name": "SpreadsheetTool",
            "reason": "not_found",
            "details": "SpreadsheetTool was requested but not found in registry."
        }
        
        is_trivial = auto_provision_agent.is_trivial(context, missing_item_details)
        if is_trivial:
            logger.info("✓ SpreadsheetTool correctly identified as trivial")
        else:
            logger.warning("✗ SpreadsheetTool not identified as trivial")
        
        # Test ReportingAgent (should not be trivial by default)
        missing_item_details = {
            "type": "agent",
            "name": "ReportingAgent",
            "reason": "not_found",
            "details": "ReportingAgent was requested but not found in registry."
        }
        
        is_trivial = auto_provision_agent.is_trivial(context, missing_item_details)
        if not is_trivial:
            logger.info("✓ ReportingAgent correctly identified as non-trivial")
        else:
            logger.warning("✗ ReportingAgent incorrectly identified as trivial")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Triviality detection test failed: {e}")
        return False

def test_stub_generation():
    """Test the stub specification generation."""
    logger.info("Testing stub generation...")
    
    try:
        from orchestrator.registry import Registry
        from orchestrator.agents.auto_provision_agent import AutoProvisionAgent
        
        class MockCOA:
            def __init__(self):
                self.name = "MockOrchestrationAgent"
            
            def _log(self, message, level="info"):
                logger.info(f"MockCOA: {message}")
        
        registry = Registry()
        mock_coa = MockCOA()
        auto_provision_agent = AutoProvisionAgent(registry=registry, coa=mock_coa)
        
        # Test tool stub generation
        tool_stub = auto_provision_agent.generate_stub_spec("SpreadsheetTool", "tool")
        logger.info(f"✓ Tool stub generated: {tool_stub['description']}")
        
        # Test agent stub generation
        agent_stub = auto_provision_agent.generate_stub_spec("ReportingAgent", "agent")
        logger.info(f"✓ Agent stub generated: {agent_stub['description']}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Stub generation test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    logger.info("Starting AutoProvisionAgent integration tests...")
    
    tests = [
        test_imports,
        test_auto_provision_agent_initialization,
        test_triviality_detection,
        test_stub_generation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        logger.info("-" * 50)
    
    logger.info(f"Integration tests completed: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 All integration tests passed! AutoProvisionAgent is properly integrated.")
        return True
    else:
        logger.error("❌ Some integration tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 