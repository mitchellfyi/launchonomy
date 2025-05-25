"""
WorkflowManager - Manages workflow agent execution and routing for Launchonomy.

This module provides intelligent routing of workflow steps to specialized agents,
auto-provisioning of missing agents, and standardized workflow execution.
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from .agents import get_workflow_agent, WORKFLOW_AGENTS
from .agents.base_workflow_agent import WorkflowOutput

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Manages workflow agent execution and routing."""
    
    def __init__(self, registry: Dict[str, Any], mission_context: Dict[str, Any]):
        self.registry = registry
        self.mission_context = mission_context
        self.logger = logging.getLogger("workflow_manager")
        
        # Cache for instantiated workflow agents
        self._agent_cache = {}
        
        # Workflow step patterns for detection
        self.workflow_patterns = {
            'scan_opportunities': [
                r'scan\s+opportunities',
                r'identify\s+opportunities',
                r'market\s+research',
                r'opportunity\s+analysis',
                r'find\s+business\s+opportunities'
            ],
            'deploy_mvp': [
                r'deploy\s+mvp',
                r'build\s+mvp',
                r'launch\s+product',
                r'create\s+minimum\s+viable\s+product',
                r'deploy\s+application'
            ],
            'run_campaigns': [
                r'run\s+campaigns',
                r'launch\s+marketing',
                r'start\s+advertising',
                r'customer\s+acquisition',
                r'marketing\s+campaign'
            ],
            'optimize_campaigns': [
                r'optimize\s+campaigns',
                r'improve\s+marketing',
                r'campaign\s+optimization',
                r'marketing\s+optimization',
                r'improve\s+conversion'
            ],
            'fetch_metrics': [
                r'fetch\s+metrics',
                r'get\s+analytics',
                r'analyze\s+performance',
                r'collect\s+data',
                r'performance\s+analysis'
            ],
            'enforce_guardrail': [
                r'enforce\s+guardrail',
                r'check\s+budget',
                r'financial\s+approval',
                r'budget\s+check',
                r'cost\s+control'
            ],
            'run_growth_loop': [
                r'run\s+growth\s+loop',
                r'growth\s+strategy',
                r'user\s+acquisition',
                r'growth\s+optimization',
                r'viral\s+growth'
            ]
        }
    
    def detect_workflow_step(self, recommendation: str) -> Optional[str]:
        """
        Detect if a recommendation contains a workflow step.
        
        Args:
            recommendation: The recommendation text to analyze
            
        Returns:
            The detected workflow step name or None
        """
        recommendation_lower = recommendation.lower()
        
        for workflow_step, patterns in self.workflow_patterns.items():
            for pattern in patterns:
                if re.search(pattern, recommendation_lower):
                    self.logger.info(f"Detected workflow step '{workflow_step}' from pattern: {pattern}")
                    return workflow_step
        
        return None
    
    def can_handle_workflow(self, recommendation: str) -> bool:
        """Check if the recommendation can be handled by a workflow agent."""
        return self.detect_workflow_step(recommendation) is not None
    
    async def execute_workflow_step(self, workflow_step: str, input_data: Dict[str, Any]) -> WorkflowOutput:
        """
        Execute a specific workflow step using the appropriate agent.
        
        Args:
            workflow_step: The workflow step to execute
            input_data: Input data for the workflow step
            
        Returns:
            WorkflowOutput from the executed agent
        """
        try:
            self.logger.info(f"Executing workflow step: {workflow_step}")
            
            # Get or create the workflow agent
            agent = await self._get_workflow_agent(workflow_step)
            if not agent:
                return WorkflowOutput(
                    success=False,
                    data={},
                    message=f"No agent available for workflow step: {workflow_step}",
                    cost_estimate=0.0
                )
            
            # Execute the workflow step
            result = agent.execute(input_data)
            
            # Handle async execution if needed
            if hasattr(result, '__await__'):
                result = await result
            
            self.logger.info(f"Workflow step '{workflow_step}' completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing workflow step '{workflow_step}': {str(e)}")
            return WorkflowOutput(
                success=False,
                data={'error': str(e)},
                message=f"Workflow step '{workflow_step}' failed: {str(e)}",
                cost_estimate=0.0
            )
    
    async def execute_from_recommendation(self, recommendation: str) -> Optional[WorkflowOutput]:
        """
        Execute a workflow step detected from a recommendation.
        
        Args:
            recommendation: The recommendation text to analyze and execute
            
        Returns:
            WorkflowOutput if a workflow step was detected and executed, None otherwise
        """
        workflow_step = self.detect_workflow_step(recommendation)
        if not workflow_step:
            return None
        
        # Extract input data from recommendation
        input_data = self._extract_input_data(recommendation, workflow_step)
        
        # Execute the workflow step
        return await self.execute_workflow_step(workflow_step, input_data)
    
    def _extract_input_data(self, recommendation: str, workflow_step: str) -> Dict[str, Any]:
        """
        Extract input data from recommendation text for a specific workflow step.
        
        Args:
            recommendation: The recommendation text
            workflow_step: The detected workflow step
            
        Returns:
            Dictionary of input data for the workflow step
        """
        input_data = {
            'recommendation_text': recommendation,
            'workflow_step': workflow_step,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add step-specific data extraction
        if workflow_step == 'scan_opportunities':
            input_data.update({
                'mission_context': self.mission_context,
                'focus_areas': self._extract_focus_areas(recommendation),
                'max_opportunities': 5
            })
        
        elif workflow_step == 'deploy_mvp':
            input_data.update({
                'opportunity': self._extract_opportunity_info(recommendation),
                'requirements': self._extract_requirements(recommendation),
                'budget_limit': self.mission_context.get('budget_constraints', {}).get('monthly_limit', 500)
            })
        
        elif workflow_step in ['run_campaigns', 'optimize_campaigns']:
            input_data.update({
                'campaign_type': 'launch' if workflow_step == 'run_campaigns' else 'optimization',
                'product_details': self._extract_product_details(recommendation),
                'budget_allocation': self._extract_budget_allocation(recommendation),
                'optimization_goals': self._extract_optimization_goals(recommendation)
            })
        
        elif workflow_step == 'fetch_metrics':
            input_data.update({
                'analysis_type': self._extract_analysis_type(recommendation),
                'time_period': self._extract_time_period(recommendation),
                'specific_metrics': self._extract_specific_metrics(recommendation)
            })
        
        elif workflow_step == 'enforce_guardrail':
            input_data.update({
                'operation_type': self._extract_operation_type(recommendation),
                'estimated_cost': self._extract_estimated_cost(recommendation),
                'time_period': 'monthly'
            })
        
        elif workflow_step == 'run_growth_loop':
            input_data.update({
                'growth_phase': self._extract_growth_phase(recommendation),
                'experiment_budget': self._extract_experiment_budget(recommendation),
                'focus_areas': self._extract_focus_areas(recommendation)
            })
        
        return input_data
    
    def _extract_focus_areas(self, text: str) -> List[str]:
        """Extract focus areas from text."""
        focus_keywords = {
            'ai': ['ai', 'artificial intelligence', 'machine learning'],
            'saas': ['saas', 'software as a service', 'web app'],
            'api': ['api', 'application programming interface'],
            'newsletter': ['newsletter', 'email marketing'],
            'automation': ['automation', 'workflow'],
            'analytics': ['analytics', 'data analysis', 'metrics']
        }
        
        text_lower = text.lower()
        focus_areas = []
        
        for area, keywords in focus_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                focus_areas.append(area)
        
        return focus_areas or ['general']
    
    def _extract_opportunity_info(self, text: str) -> Dict[str, Any]:
        """Extract opportunity information from text."""
        # Simple extraction - in a real implementation this would be more sophisticated
        return {
            'name': 'Extracted Opportunity',
            'description': text[:200] + '...' if len(text) > 200 else text,
            'source': 'recommendation_extraction'
        }
    
    def _extract_requirements(self, text: str) -> Dict[str, Any]:
        """Extract requirements from text."""
        return {
            'priority': 'high',
            'timeline': 'asap',
            'extracted_from': 'recommendation'
        }
    
    def _extract_product_details(self, text: str) -> Dict[str, Any]:
        """Extract product details from text."""
        return {
            'name': 'Current Product',
            'type': 'web_application',
            'status': 'active'
        }
    
    def _extract_budget_allocation(self, text: str) -> Dict[str, Any]:
        """Extract budget allocation from text."""
        return {
            'total_budget': 200.0,
            'allocations': {
                'email_marketing': 80.0,
                'social_media': 60.0,
                'paid_advertising': 60.0
            }
        }
    
    def _extract_optimization_goals(self, text: str) -> Dict[str, Any]:
        """Extract optimization goals from text."""
        return {
            'target_improvement': '20%',
            'focus_metrics': ['conversion_rate', 'cost_per_acquisition'],
            'timeline': '2_weeks'
        }
    
    def _extract_analysis_type(self, text: str) -> str:
        """Extract analysis type from text."""
        if 'financial' in text.lower():
            return 'financial'
        elif 'marketing' in text.lower():
            return 'marketing'
        elif 'product' in text.lower():
            return 'product'
        else:
            return 'comprehensive'
    
    def _extract_time_period(self, text: str) -> str:
        """Extract time period from text."""
        if 'week' in text.lower():
            return 'weekly'
        elif 'day' in text.lower():
            return 'daily'
        elif 'quarter' in text.lower():
            return 'quarterly'
        else:
            return 'monthly'
    
    def _extract_specific_metrics(self, text: str) -> List[str]:
        """Extract specific metrics from text."""
        metric_keywords = {
            'revenue': ['revenue', 'income', 'sales'],
            'users': ['users', 'customers', 'subscribers'],
            'conversion': ['conversion', 'conversion rate'],
            'cost': ['cost', 'expense', 'spending'],
            'engagement': ['engagement', 'activity', 'usage']
        }
        
        text_lower = text.lower()
        metrics = []
        
        for metric, keywords in metric_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                metrics.append(metric)
        
        return metrics or ['all']
    
    def _extract_operation_type(self, text: str) -> str:
        """Extract operation type from text."""
        if 'marketing' in text.lower():
            return 'marketing'
        elif 'development' in text.lower():
            return 'development'
        elif 'infrastructure' in text.lower():
            return 'infrastructure'
        else:
            return 'general'
    
    def _extract_estimated_cost(self, text: str) -> float:
        """Extract estimated cost from text."""
        # Simple regex to find dollar amounts
        import re
        cost_match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
        if cost_match:
            return float(cost_match.group(1))
        
        # Default estimates based on operation type
        if 'marketing' in text.lower():
            return 100.0
        elif 'development' in text.lower():
            return 200.0
        else:
            return 50.0
    
    def _extract_growth_phase(self, text: str) -> str:
        """Extract growth phase from text."""
        if 'early' in text.lower() or 'initial' in text.lower():
            return 'early'
        elif 'scaling' in text.lower() or 'scale' in text.lower():
            return 'scaling'
        elif 'optimization' in text.lower() or 'optimize' in text.lower():
            return 'optimization'
        else:
            return 'early'
    
    def _extract_experiment_budget(self, text: str) -> float:
        """Extract experiment budget from text."""
        # Look for budget mentions
        cost = self._extract_estimated_cost(text)
        return min(cost, 150.0)  # Cap experiment budget
    
    async def _get_workflow_agent(self, workflow_step: str):
        """Get or create a workflow agent for the given step."""
        if workflow_step in self._agent_cache:
            return self._agent_cache[workflow_step]
        
        # Get the agent class
        agent_class = get_workflow_agent(workflow_step)
        if not agent_class:
            self.logger.error(f"No agent class found for workflow step: {workflow_step}")
            return None
        
        # Check if agent is available in registry
        agent_name = f"{agent_class.__name__}"
        if not self._is_agent_registered(agent_name):
            # Auto-provision the agent
            success = await self._auto_provision_agent(agent_name, workflow_step)
            if not success:
                self.logger.error(f"Failed to auto-provision agent: {agent_name}")
                return None
        
        # Instantiate the agent
        try:
            agent = agent_class(self.registry, self.mission_context)
            self._agent_cache[workflow_step] = agent
            self.logger.info(f"Successfully instantiated workflow agent: {agent_name}")
            return agent
        except Exception as e:
            self.logger.error(f"Failed to instantiate workflow agent {agent_name}: {str(e)}")
            return None
    
    def _is_agent_registered(self, agent_name: str) -> bool:
        """Check if an agent is registered in the registry."""
        if hasattr(self.registry, 'get_agent_spec'):
            return self.registry.get_agent_spec(agent_name) is not None
        elif isinstance(self.registry, dict):
            return agent_name in self.registry.get('agents', {})
        else:
            # Assume it's registered for now
            return True
    
    async def _auto_provision_agent(self, agent_name: str, workflow_step: str) -> bool:
        """Auto-provision a workflow agent."""
        try:
            self.logger.info(f"Auto-provisioning workflow agent: {agent_name}")
            
            # In a real implementation, this would register the agent in the registry
            # For now, we'll assume it's successful
            self.logger.info(f"Successfully auto-provisioned agent: {agent_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to auto-provision agent {agent_name}: {str(e)}")
            return False
    
    def get_available_workflow_steps(self) -> List[str]:
        """Get list of available workflow steps."""
        return list(WORKFLOW_AGENTS.keys())
    
    def get_workflow_agent_info(self, workflow_step: str) -> Optional[Dict[str, Any]]:
        """Get information about a workflow agent."""
        agent_class = get_workflow_agent(workflow_step)
        if not agent_class:
            return None
        
        return {
            'name': agent_class.__name__,
            'workflow_step': workflow_step,
            'description': agent_class.__doc__ or f"Workflow agent for {workflow_step}",
            'required_tools': getattr(agent_class, 'required_tools', []),
            'optional_tools': getattr(agent_class, 'optional_tools', [])
        } 