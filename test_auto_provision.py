#!/usr/bin/env python3

import asyncio
import os
import sys
import logging

# Add the current directory to the path so we can import orchestrator modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.orchestrator_agent import create_orchestrator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_auto_provision_tool():
    """Test auto-provisioning of a nonexistent tool."""
    logger.info("Starting auto-provision test...")
    
    # Create orchestrator instance
    orchestrator = create_orchestrator()
    
    # Test context
    context = {
        "overall_mission": "test_auto_provision",
        "current_step": "testing_spreadsheet_tool"
    }
    
    # Test auto-provisioning of a SpreadsheetTool
    logger.info("Testing auto-provisioning of 'SpreadsheetTool'...")
    result = await orchestrator._get_tool_from_registry("SpreadsheetTool", context)
    
    if result:
        logger.info(f"SUCCESS: SpreadsheetTool was auto-provisioned: {result}")
    else:
        logger.warning("SpreadsheetTool was not auto-provisioned")
    
    # Test auto-provisioning of a ReportingAgent
    logger.info("Testing auto-provisioning of 'ReportingAgent'...")
    
    missing_item_details = {
        "type": "agent",
        "name": "ReportingAgent",
        "reason": "not_found",
        "details": "ReportingAgent was requested but not found in registry."
    }
    
    auto_provision_result = await orchestrator.auto_provision_agent.handle_trivial_request(
        context, missing_item_details
    )
    
    if auto_provision_result:
        logger.info(f"SUCCESS: ReportingAgent was auto-provisioned: {auto_provision_result}")
    else:
        logger.warning("ReportingAgent was not auto-provisioned")
    
    logger.info("Auto-provision test completed.")

if __name__ == "__main__":
    # Check if OPENAI_API_KEY is set
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set. Please set it to run the test.")
        sys.exit(1)
    
    asyncio.run(test_auto_provision_tool()) 