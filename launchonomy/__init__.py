"""
Launchonomy - Autonomous AI Business Orchestration System

A comprehensive system for orchestrating AI agents to build and grow autonomous businesses.
"""

__version__ = "1.0.0"
__author__ = "Launchonomy Team"

from .core.orchestrator import OrchestrationAgent, create_orchestrator
from .cli import main as cli_main

__all__ = [
    "OrchestrationAgent",
    "create_orchestrator", 
    "cli_main"
] 