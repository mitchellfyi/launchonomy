#!/usr/bin/env python3
"""
Mission Log Navigator - Utility for exploring mission logs and cycle relationships
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional

def load_mission_logs() -> Dict[str, dict]:
    """Load all mission logs from the mission_logs directory."""
    mission_logs = {}
    mission_log_dir = "mission_logs"
    
    if not os.path.exists(mission_log_dir):
        print(f"Mission logs directory '{mission_log_dir}' not found.")
        return mission_logs
    
    for filename in os.listdir(mission_log_dir):
        if filename.startswith("mission_") and filename.endswith(".json"):
            try:
                with open(os.path.join(mission_log_dir, filename), 'r') as f:
                    data = json.load(f)
                    mission_logs[data.get('mission_id', filename)] = data
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    
    return mission_logs

def load_cycle_logs() -> Dict[str, dict]:
    """Load all cycle logs from the mission_logs directory."""
    cycle_logs = {}
    mission_log_dir = "mission_logs"
    
    if not os.path.exists(mission_log_dir):
        return cycle_logs
    
    for filename in os.listdir(mission_log_dir):
        if filename.startswith("cycle_") and filename.endswith(".json"):
            try:
                with open(os.path.join(mission_log_dir, filename), 'r') as f:
                    data = json.load(f)
                    cycle_logs[data.get('mission_id', filename)] = data
            except Exception as e:
                print(f"Error loading {filename}: {e}")
    
    return cycle_logs

def list_missions():
    """List all available missions with summary information."""
    print("=" * 60)
    print("AVAILABLE MISSIONS")
    print("=" * 60)
    
    mission_logs = load_mission_logs()
    
    if not mission_logs:
        print("No mission logs found.")
        return
    
    for mission_id, mission_data in mission_logs.items():
        print(f"\n📋 Mission: {mission_data.get('mission_name', 'Unknown')}")
        print(f"   ID: {mission_id}")
        print(f"   Status: {mission_data.get('status', 'Unknown')}")
        print(f"   Cycles: {len(mission_data.get('cycle_ids', []))}")
        print(f"   Completed: {mission_data.get('completed_cycles', 0)}")
        print(f"   Failed: {mission_data.get('failed_cycles', 0)}")
        print(f"   Total Cost: ${mission_data.get('total_mission_cost', 0):.2f}")
        print(f"   Total Time: {mission_data.get('total_mission_time_minutes', 0):.1f} minutes")
        print(f"   Started: {mission_data.get('start_timestamp', 'Unknown')}")
        print(f"   Last Updated: {mission_data.get('last_updated', 'Unknown')}")

def show_mission_details(mission_id: str):
    """Show detailed information about a specific mission."""
    mission_logs = load_mission_logs()
    
    if mission_id not in mission_logs:
        print(f"Mission '{mission_id}' not found.")
        return
    
    mission = mission_logs[mission_id]
    
    print("=" * 60)
    print(f"MISSION DETAILS: {mission.get('mission_name', 'Unknown')}")
    print("=" * 60)
    
    print(f"Mission ID: {mission_id}")
    print(f"Overall Mission: {mission.get('overall_mission', 'Unknown')}")
    print(f"Status: {mission.get('status', 'Unknown')}")
    print(f"Created By: {mission.get('created_by', 'Unknown')}")
    print(f"Started: {mission.get('start_timestamp', 'Unknown')}")
    print(f"Last Updated: {mission.get('last_updated', 'Unknown')}")
    
    print(f"\n📊 METRICS:")
    print(f"   Total Cycles: {len(mission.get('cycle_ids', []))}")
    print(f"   Completed: {mission.get('completed_cycles', 0)}")
    print(f"   Failed: {mission.get('failed_cycles', 0)}")
    print(f"   Total Cost: ${mission.get('total_mission_cost', 0):.2f}")
    print(f"   Total Time: {mission.get('total_mission_time_minutes', 0):.1f} minutes")
    
    print(f"\n🤖 PERSISTENT AGENTS:")
    agents = mission.get('persistent_agents', [])
    if agents:
        for agent in agents:
            print(f"   • {agent}")
    else:
        print("   None")
    
    print(f"\n🧠 KEY LEARNINGS:")
    learnings = mission.get('key_learnings', [])
    if learnings:
        for i, learning in enumerate(learnings, 1):
            print(f"   {i}. {learning[:100]}{'...' if len(learning) > 100 else ''}")
    else:
        print("   None")
    
    print(f"\n🔄 CYCLE HISTORY:")
    cycle_summaries = mission.get('cycle_summaries', [])
    if cycle_summaries:
        for i, cycle in enumerate(cycle_summaries, 1):
            print(f"   {i}. {cycle.get('cycle_id', 'Unknown')}")
            print(f"      Focus: {cycle.get('decision_focus', 'Unknown')}")
            print(f"      Status: {cycle.get('status', 'Unknown')}")
            print(f"      Cost: ${cycle.get('cost', 0):.2f}")
            print(f"      Duration: {cycle.get('duration_minutes', 0):.1f} min")
            print(f"      Agents: {', '.join(cycle.get('agents_used', []))}")
    else:
        print("   No cycles found")

def show_cycle_details(cycle_id: str):
    """Show detailed information about a specific cycle."""
    cycle_logs = load_cycle_logs()
    
    if cycle_id not in cycle_logs:
        print(f"Cycle '{cycle_id}' not found.")
        return
    
    cycle = cycle_logs[cycle_id]
    
    print("=" * 60)
    print(f"CYCLE DETAILS: {cycle_id}")
    print("=" * 60)
    
    print(f"Decision Focus: {cycle.get('current_decision_focus', 'Unknown')}")
    print(f"Status: {cycle.get('status', 'Unknown')}")
    print(f"Timestamp: {cycle.get('timestamp', 'Unknown')}")
    print(f"Duration: {cycle.get('cycle_duration_minutes', 0):.2f} minutes")
    print(f"Cost: ${cycle.get('total_cycle_cost', 0):.2f}")
    
    print(f"\n🔗 LINKING:")
    print(f"   Parent Mission: {cycle.get('parent_mission_id', 'None')}")
    print(f"   Sequence Number: {cycle.get('cycle_sequence_number', 0)}")
    print(f"   Previous Cycle: {cycle.get('previous_cycle_id', 'None')}")
    print(f"   Next Cycle: {cycle.get('next_cycle_id', 'None')}")
    
    print(f"\n🤖 AGENTS USED:")
    agents = cycle.get('agents_used', [])
    if agents:
        for agent in agents:
            print(f"   • {agent}")
    else:
        print("   None")
    
    print(f"\n📝 INTERACTIONS:")
    interactions = [
        ("Specialist", cycle.get('specialist_interactions', [])),
        ("Review", cycle.get('review_interactions', [])),
        ("Orchestrator", cycle.get('orchestrator_interactions', [])),
        ("Execution", cycle.get('execution_attempts', []))
    ]
    
    for interaction_type, interaction_list in interactions:
        print(f"   {interaction_type}: {len(interaction_list)} interactions")
    
    print(f"\n🧠 CONTEXT FROM PREVIOUS CYCLES:")
    prev_context = cycle.get('previous_cycles_context', [])
    if prev_context:
        for i, context in enumerate(prev_context, 1):
            print(f"   {i}. {context.get('cycle_id', 'Unknown')}: {context.get('decision_focus', 'Unknown')[:50]}...")
    else:
        print("   None")
    
    print(f"\n💡 KEY INSIGHTS FROM PREVIOUS:")
    insights = cycle.get('key_insights_from_previous', [])
    if insights:
        for i, insight in enumerate(insights, 1):
            print(f"   {i}. {insight[:100]}{'...' if len(insight) > 100 else ''}")
    else:
        print("   None")

def trace_cycle_chain(start_cycle_id: str):
    """Trace the chain of cycles from a starting cycle."""
    cycle_logs = load_cycle_logs()
    
    if start_cycle_id not in cycle_logs:
        print(f"Cycle '{start_cycle_id}' not found.")
        return
    
    print("=" * 60)
    print(f"CYCLE CHAIN STARTING FROM: {start_cycle_id}")
    print("=" * 60)
    
    # Find the first cycle in the chain
    current_cycle_id = start_cycle_id
    while current_cycle_id and current_cycle_id in cycle_logs:
        cycle = cycle_logs[current_cycle_id]
        prev_id = cycle.get('previous_cycle_id')
        if not prev_id or prev_id not in cycle_logs:
            break
        current_cycle_id = prev_id
    
    # Trace forward through the chain
    sequence = 1
    while current_cycle_id and current_cycle_id in cycle_logs:
        cycle = cycle_logs[current_cycle_id]
        
        print(f"\n{sequence}. {current_cycle_id}")
        print(f"   Focus: {cycle.get('current_decision_focus', 'Unknown')}")
        print(f"   Status: {cycle.get('status', 'Unknown')}")
        print(f"   Duration: {cycle.get('cycle_duration_minutes', 0):.1f} min")
        print(f"   Cost: ${cycle.get('total_cycle_cost', 0):.2f}")
        
        # Show linking
        prev_id = cycle.get('previous_cycle_id')
        next_id = cycle.get('next_cycle_id')
        print(f"   Links: {prev_id or 'START'} → THIS → {next_id or 'END'}")
        
        current_cycle_id = next_id
        sequence += 1

def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("Mission Log Navigator")
        print("\nUsage:")
        print("  python mission_log_navigator.py list                    # List all missions")
        print("  python mission_log_navigator.py mission <mission_id>    # Show mission details")
        print("  python mission_log_navigator.py cycle <cycle_id>        # Show cycle details")
        print("  python mission_log_navigator.py trace <cycle_id>        # Trace cycle chain")
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_missions()
    
    elif command == "mission":
        if len(sys.argv) < 3:
            print("Please provide a mission ID")
            return
        mission_id = sys.argv[2]
        show_mission_details(mission_id)
    
    elif command == "cycle":
        if len(sys.argv) < 3:
            print("Please provide a cycle ID")
            return
        cycle_id = sys.argv[2]
        show_cycle_details(cycle_id)
    
    elif command == "trace":
        if len(sys.argv) < 3:
            print("Please provide a cycle ID to start tracing from")
            return
        cycle_id = sys.argv[2]
        trace_cycle_chain(cycle_id)
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: list, mission, cycle, trace")

if __name__ == "__main__":
    main() 