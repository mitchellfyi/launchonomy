#!/usr/bin/env python3
"""
Test script for mission-scoped RAG memory integration.

This script tests:
1. ChromaDB vector memory creation
2. Memory logging functionality
3. RetrievalAgent functionality
4. Integration with orchestrator
"""

import asyncio
import os
import sys
import tempfile
import shutil
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from launchonomy.core.vector_memory import create_mission_memory, MemoryContent
from launchonomy.agents.retrieval_agent import RetrievalAgent
from launchonomy.utils.memory_helper import MemoryHelper

async def test_basic_memory_operations():
    """Test basic memory operations."""
    print("🧠 Testing basic memory operations...")
    
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    print(f"Using temporary directory: {temp_dir}")
    
    try:
        # Test 1: Create mission memory
        print("\n1. Creating mission memory...")
        mission_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_test_mission"
        memory_store = create_mission_memory(mission_id, temp_dir)
        print(f"✅ Created memory store for mission: {mission_id}")
        
        # Test 2: Store some test memories
        print("\n2. Storing test memories...")
        memory_helper = MemoryHelper(memory_store, mission_id)
        
        # Log a workflow event
        event_id = memory_helper.log_workflow_event(
            "scan", 
            "Successfully identified 5 business opportunities",
            {"opportunities_found": 5, "top_opportunity": "AI-powered newsletter service"}
        )
        print(f"✅ Logged workflow event: {event_id}")
        
        # Log an insight
        insight_id = memory_helper.log_insight(
            "Newsletter services have high demand and low competition in the AI space",
            "ScanAgent",
            0.9
        )
        print(f"✅ Logged insight: {insight_id}")
        
        # Log a decision
        decision_id = memory_helper.log_decision(
            "Selected AI newsletter service as primary opportunity",
            "High market demand, low competition, fits budget constraints",
            "OrchestrationAgent"
        )
        print(f"✅ Logged decision: {decision_id}")
        
        # Test 3: Retrieve memories
        print("\n3. Testing memory retrieval...")
        retrieval_agent = RetrievalAgent(memory_store)
        
        # Query for opportunities
        memories = await retrieval_agent.retrieve("business opportunities", k=3)
        print(f"✅ Retrieved {len(memories)} memories about opportunities:")
        for i, memory in enumerate(memories, 1):
            print(f"   {i}. {memory[:100]}...")
        
        # Query for decisions
        memories = await retrieval_agent.retrieve("decisions made", k=2)
        print(f"✅ Retrieved {len(memories)} memories about decisions:")
        for i, memory in enumerate(memories, 1):
            print(f"   {i}. {memory[:100]}...")
        
        # Test 4: Get memory stats
        print("\n4. Getting memory statistics...")
        stats = retrieval_agent.get_memory_stats()
        print(f"✅ Memory stats: {stats}")
        
        print("\n🎉 All basic memory operations completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error in basic memory operations: {str(e)}")
        return False
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"🧹 Cleaned up temporary directory: {temp_dir}")

async def test_memory_with_orchestrator():
    """Test memory integration with orchestrator."""
    print("\n🎭 Testing memory integration with orchestrator...")
    
    try:
        # Import orchestrator components
        from launchonomy.core.orchestrator import create_orchestrator
        from unittest.mock import Mock
        
        # Create a mock client for testing
        mock_client = Mock()
        
        # Create orchestrator
        print("1. Creating orchestrator...")
        orchestrator = create_orchestrator(mock_client)
        print("✅ Orchestrator created")
        
        # Create a test mission
        print("\n2. Creating test mission...")
        mission_log = orchestrator.create_or_load_mission(
            "test_memory_mission",
            "Test mission for memory integration",
            resume_existing=False
        )
        print(f"✅ Mission created: {mission_log.mission_id}")
        
        # Test memory system initialization
        print("\n3. Testing memory system...")
        if orchestrator.mission_memory:
            print("✅ Mission memory initialized")
        else:
            print("❌ Mission memory not initialized")
            return False
            
        if orchestrator.memory_helper:
            print("✅ Memory helper initialized")
        else:
            print("❌ Memory helper not initialized")
            return False
            
        if orchestrator.retrieval_agent:
            print("✅ Retrieval agent initialized")
        else:
            print("❌ Retrieval agent not initialized")
            return False
        
        # Test logging a workflow step
        print("\n4. Testing workflow step logging...")
        await orchestrator._log_workflow_step_to_memory(
            "TestAgent",
            {"status": "success", "revenue": 100.0, "customers": 5},
            "success"
        )
        print("✅ Workflow step logged to memory")
        
        # Test retrieving memories
        print("\n5. Testing memory retrieval...")
        memories = await orchestrator.retrieval_agent.retrieve("test workflow", k=2)
        print(f"✅ Retrieved {len(memories)} memories")
        for i, memory in enumerate(memories, 1):
            print(f"   {i}. {memory[:100]}...")
        
        print("\n🎉 Orchestrator memory integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error in orchestrator memory integration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_agent_memory_retrieval():
    """Test memory retrieval from workflow agents."""
    print("\n🤖 Testing agent memory retrieval...")
    
    try:
        # Import a workflow agent
        from launchonomy.agents.workflow.scan import ScanAgent
        from unittest.mock import Mock
        
        # Create mock orchestrator with memory system
        mock_orchestrator = Mock()
        mock_retrieval_agent = Mock()
        
        # Mock the retrieve method to return test memories
        mock_retrieval_agent.retrieve = Mock(return_value=[
            "[scan - 2024-01-15] Previous scan found 3 opportunities in AI space",
            "[deploy - 2024-01-14] Successfully deployed newsletter service MVP",
            "[campaign - 2024-01-13] Email campaign achieved 5% conversion rate"
        ])
        
        mock_orchestrator.retrieval_agent = mock_retrieval_agent
        
        # Create scan agent
        scan_agent = ScanAgent(registry=None, orchestrator=mock_orchestrator)
        
        # Test memory retrieval
        print("1. Testing memory retrieval from ScanAgent...")
        memories = await scan_agent._get_relevant_memories("scanning for business opportunities")
        print(f"✅ Retrieved memories: {len(memories)} characters")
        print(f"Memory content preview: {memories[:200]}...")
        
        print("\n🎉 Agent memory retrieval test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error in agent memory retrieval: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all memory integration tests."""
    print("🚀 Starting mission-scoped RAG memory integration tests...\n")
    
    tests = [
        ("Basic Memory Operations", test_basic_memory_operations),
        ("Orchestrator Integration", test_memory_with_orchestrator),
        ("Agent Memory Retrieval", test_agent_memory_retrieval),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Print summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Memory integration is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 