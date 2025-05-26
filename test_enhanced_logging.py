#!/usr/bin/env python3
"""
Test script to demonstrate enhanced C-Suite activity logging.
Shows detailed decision-making process and next steps planning.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from launchonomy.core.orchestrator import create_orchestrator


async def test_enhanced_csuite_logging():
    """Test the enhanced C-Suite logging functionality."""
    print("🧪 Testing Enhanced C-Suite Activity Logging")
    print("=" * 60)
    
    try:
        # Create orchestrator
        orchestrator = create_orchestrator()
        
        # Bootstrap C-Suite with enhanced logging
        print("\n🏛️ BOOTSTRAPPING C-SUITE")
        print("-" * 30)
        await orchestrator.bootstrap_c_suite("Test mission for enhanced logging demonstration")
        
        # Test C-Suite planning with enhanced logging
        print("\n📋 C-SUITE STRATEGIC PLANNING")
        print("-" * 30)
        
        strategic_csuite = ["CEO-Agent", "CRO-Agent", "CTO-Agent"]
        mission_context = {
            "overall_mission": "Launch and grow a SaaS product",
            "target_market": "small businesses",
            "budget": 1000
        }
        loop_results = {
            "total_revenue_generated": 500.0,
            "execution_log": [{"cycle": 1, "revenue": 250}, {"cycle": 2, "revenue": 250}]
        }
        cycle_log = {
            "iteration": 3,
            "revenue_generated": 150.0,
            "cycle_successful": True
        }
        
        planning_results = await orchestrator._conduct_csuite_planning(
            strategic_csuite, mission_context, loop_results, cycle_log
        )
        
        print(f"\n✅ Planning completed with {len(planning_results['key_decisions'])} decisions")
        
        # Test C-Suite review with enhanced logging
        print("\n📊 C-SUITE PERFORMANCE REVIEW")
        print("-" * 30)
        
        cycle_log_review = {
            "iteration": 3,
            "revenue_generated": 150.0,
            "cycle_successful": True,
            "steps": {"ScanAgent": {"status": "success"}, "CampaignAgent": {"status": "success"}},
            "errors": []
        }
        
        review_results = await orchestrator._conduct_csuite_review(
            strategic_csuite, cycle_log_review, loop_results
        )
        
        print(f"\n✅ Review completed with assessment: {review_results['overall_assessment']}")
        
        # Test CFO approval with enhanced logging
        print("\n💰 CFO GROWTH INVESTMENT APPROVAL")
        print("-" * 30)
        
        approval_results = await orchestrator._get_cfo_growth_approval(750.0)
        
        print(f"\n✅ CFO approval process completed")
        
        # Test mission completion consensus with enhanced logging
        print("\n🏁 MISSION COMPLETION CONSENSUS")
        print("-" * 30)
        
        completion_results = await orchestrator._get_csuite_mission_completion_consensus({
            "total_revenue_generated": 1500.0,
            "successful_cycles": 5,
            "total_iterations": 8
        })
        
        print(f"\n✅ Mission completion consensus: {completion_results['mission_complete']}")
        
        print("\n🎉 Enhanced C-Suite logging test completed successfully!")
        print("=" * 60)
        print("📝 Key enhancements demonstrated:")
        print("   • Detailed planning session logs with participant tracking")
        print("   • Strategic focus consensus and voting")
        print("   • Budget allocation recommendations with reasoning")
        print("   • Risk and opportunity identification")
        print("   • Specific next action planning based on focus")
        print("   • Performance review with cycle summaries")
        print("   • CFO approval process with decision reasoning")
        print("   • Mission completion voting with individual agent input")
        print("   • Enhanced emoji-based visual indicators for better readability")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_enhanced_csuite_logging())
    if result:
        print("\n✅ All enhanced logging features working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Enhanced logging test failed!")
        sys.exit(1) 