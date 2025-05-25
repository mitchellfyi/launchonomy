#!/usr/bin/env python3
"""
Test the enhanced status display with:
- Token usage tracking (input/output tokens)
- 3-line activity messages instead of 1
- Expanded status panel
"""

import sys
import os
import time
from rich.console import Console
from rich.live import Live

# Add orchestrator to path
sys.path.append('orchestrator')

from orchestrator.cli import MissionMonitor

def test_enhanced_status():
    console = Console()
    
    console.print("[bold green]🧪 Testing Enhanced Status Display[/bold green]")
    console.print()
    
    # Create monitor
    monitor = MissionMonitor()
    
    # Add some test agents
    test_agents = ["OrchestrationAgent", "CEO-Agent", "CTO-Agent", "CMO-Agent"]
    for agent in test_agents:
        monitor.add_agent(agent)
    
    console.print("[bold yellow]New Status Features:[/bold yellow]")
    console.print("• Token usage tracking: ↑input tokens ↓output tokens")
    console.print("• Activity messages can span up to 3 lines")
    console.print("• Expanded status panel (7 lines instead of 5)")
    console.print("• Smart line breaking for long messages")
    console.print()
    
    # Test scenarios with different message lengths and token usage
    test_scenarios = [
        {
            "status": "Initializing Mission...",
            "activity": "Setting up environment and loading configuration files",
            "tokens": (150, 75),
            "running": True
        },
        {
            "status": "Orchestrator: Consulting specialists...",
            "activity": "The orchestrator is currently consulting with multiple specialist agents to determine the best approach for this complex business mission. This involves analyzing market conditions, evaluating technical requirements, and assessing resource constraints to develop an optimal strategy.",
            "tokens": (450, 220),
            "running": True
        },
        {
            "status": "CEO-Agent: Strategic planning...",
            "activity": "Conducting comprehensive market analysis including competitor research, customer segmentation, pricing strategy evaluation, and risk assessment to inform strategic decision-making processes.",
            "tokens": (680, 340),
            "running": True
        },
        {
            "status": "Mission Complete!",
            "activity": "All objectives achieved successfully with optimal resource utilization",
            "tokens": (1250, 890),
            "running": False
        }
    ]
    
    console.print("[bold cyan]🎬 Live Status Demo (3 seconds each scenario):[/bold cyan]")
    console.print()
    
    with Live(monitor.layout, refresh_per_second=2, console=console) as live:
        for i, scenario in enumerate(test_scenarios, 1):
            console.print(f"Scenario {i}: {scenario['status']}")
            
            # Add tokens for this scenario
            monitor.add_tokens(scenario['tokens'][0], scenario['tokens'][1])
            
            # Set status and activity
            monitor.set_overall_status(scenario['status'], scenario['running'])
            monitor.set_detail_activity(scenario['activity'])
            monitor.update("Test Mission: Enhanced Status Display with Token Tracking")
            
            # Let it run for 3 seconds
            for _ in range(6):  # 3 seconds at 2 fps
                time.sleep(0.5)
                live.refresh()
    
    console.print()
    console.print("[bold green]✅ Enhanced Status Test Complete![/bold green]")
    console.print()
    console.print("[bold blue]Key Improvements:[/bold blue]")
    console.print("1. [green]Token Tracking[/green]: Shows input (↑) and output (↓) token usage")
    console.print("2. [cyan]Multi-line Activity[/cyan]: Activity messages can span up to 3 lines")
    console.print("3. [yellow]Smart Breaking[/yellow]: Long messages break at natural points")
    console.print("4. [magenta]Expanded Panel[/magenta]: More space for detailed status information")
    console.print()
    console.print(f"[dim]Final token count: ↑{monitor.total_input_tokens:,} input, ↓{monitor.total_output_tokens:,} output[/dim]")

if __name__ == "__main__":
    test_enhanced_status() 