"""
Launchonomy Workflow Agents Package

This package contains specialized workflow agents that encapsulate core business workflow steps:
- ScanAgent: Opportunity scanning and market research
- DeployAgent: MVP deployment and product launch
- CampaignAgent: Marketing campaign execution and optimization
- AnalyticsAgent: Metrics collection and performance analysis
- FinanceAgent: Financial guardrails and budget enforcement
- GrowthAgent: Growth loop execution and optimization
"""

from .base_workflow_agent import BaseWorkflowAgent, WorkflowOutput
from .scan_agent import ScanAgent
from .deploy_agent import DeployAgent
from .campaign_agent import CampaignAgent
from .analytics_agent import AnalyticsAgent
from .finance_agent import FinanceAgent
from .growth_agent import GrowthAgent

__all__ = [
    'BaseWorkflowAgent',
    'WorkflowOutput',
    'ScanAgent',
    'DeployAgent',
    'CampaignAgent',
    'AnalyticsAgent',
    'FinanceAgent',
    'GrowthAgent'
]

# Workflow agent registry mapping
WORKFLOW_AGENTS = {
    'scan_opportunities': ScanAgent,
    'deploy_mvp': DeployAgent,
    'run_campaigns': CampaignAgent,
    'optimize_campaigns': CampaignAgent,
    'fetch_metrics': AnalyticsAgent,
    'enforce_guardrail': FinanceAgent,
    'run_growth_loop': GrowthAgent
}

def get_workflow_agent(workflow_step: str):
    """Get the appropriate workflow agent class for a given workflow step."""
    return WORKFLOW_AGENTS.get(workflow_step)
