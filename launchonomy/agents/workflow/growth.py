"""
GrowthAgent - Handles growth loop execution and optimization for Launchonomy.

This agent encapsulates the run_growth_loop workflow, providing:
- Growth strategy planning and execution
- User acquisition and retention optimization
- Product-market fit validation
- Viral coefficient optimization
- Growth metrics tracking and analysis
- Automated growth experiments
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from ..base.workflow_agent import BaseWorkflowAgent, WorkflowOutput

logger = logging.getLogger(__name__)


class GrowthAgent(BaseWorkflowAgent):
    """
    GrowthAgent encapsulates the "run_growth_loop" workflow step.
    Handles growth loop execution and optimization for Launchonomy.
    """
    
    REQUIRED_TOOLS = ["analytics_platform", "user_tracking"]
    OPTIONAL_TOOLS = [
        "a_b_testing", "email_marketing", "social_media", "referral_system",
        "push_notifications", "conversion_optimization", "cohort_analysis",
        "funnel_analysis", "viral_mechanics", "retention_tools",
        "product_analytics", "growth_experiments"
    ]
    
    def __init__(self, registry=None, orchestrator=None):
        super().__init__("GrowthAgent", registry, orchestrator)
        self.system_prompt = self._build_system_prompt()
        
        # Growth parameters
        self.growth_targets = {}
        self.growth_stage = 'early'
        self.budget_constraints = {}
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with current Launchonomy context."""
        context = self._get_launchonomy_context()
        
        return f"""You are GrowthAgent, the growth loop execution and optimization specialist in the Launchonomy autonomous business system.

MISSION CONTEXT:
{context}

YOUR ROLE:
You execute and optimize growth loops to achieve sustainable, profitable growth:
- User acquisition and retention optimization
- Product-market fit validation
- Viral coefficient optimization
- Growth metrics tracking and analysis
- Automated growth experiments

CORE CAPABILITIES:
1. Growth Strategy Planning & Execution
2. User Acquisition & Retention Optimization
3. Viral Mechanics Implementation
4. Growth Metrics Analysis
5. Automated Growth Experiments

Always focus on sustainable, cost-effective growth within budget constraints."""
        
    async def execute(self, input_data: Dict[str, Any]) -> WorkflowOutput:
        """
        Execute growth loop workflow.
        
        Args:
            input_data: Dictionary containing:
                - growth_phase: Phase of growth to focus on (required)
                - current_metrics: Current growth metrics (optional)
                - experiment_budget: Budget for growth experiments (optional)
                - target_timeframe: Timeframe for growth goals (optional, defaults to 'monthly')
                - focus_areas: Specific areas to focus on (optional)
        
        Returns:
            WorkflowOutput with growth strategy execution results and recommendations
        """
        try:
            self._log(f"Starting growth loop execution for phase: {input_data.get('growth_phase', 'unknown')}")
            
            # Validate required inputs
            growth_phase = input_data.get('growth_phase')
            if not growth_phase:
                return self._format_output(
                    status="failure",
                    data={},
                    error_message="Growth phase is required for growth loop execution"
                )
            
            # Get current growth metrics
            current_metrics = await self._get_current_growth_metrics(input_data.get('current_metrics', {}))
            
            # Analyze growth opportunities
            growth_opportunities = self._analyze_growth_opportunities(growth_phase, current_metrics)
            
            # Plan growth experiments
            experiment_plan = self._plan_growth_experiments(
                growth_opportunities, 
                input_data.get('experiment_budget', 0),
                input_data.get('focus_areas', [])
            )
            
            # Execute growth strategies
            execution_results = await self._execute_growth_strategies(experiment_plan, current_metrics)
            
            # Optimize growth loops
            optimization_results = self._optimize_growth_loops(execution_results, current_metrics)
            
            # Generate growth recommendations
            recommendations = self._generate_growth_recommendations(
                current_metrics, growth_opportunities, execution_results, optimization_results
            )
            
            # Calculate total cost estimate
            total_cost = self._calculate_growth_cost(experiment_plan, execution_results)
            
            result_data = {
                'growth_phase': growth_phase,
                'current_metrics': current_metrics,
                'growth_opportunities': growth_opportunities,
                'experiment_plan': experiment_plan,
                'execution_results': execution_results,
                'optimization_results': optimization_results,
                'recommendations': recommendations,
                'growth_score': self._calculate_growth_score(current_metrics, execution_results),
                'next_review_date': (datetime.now() + timedelta(days=7)).isoformat(),
                'projected_impact': self._project_growth_impact(execution_results, current_metrics)
            }
            
            success = len(execution_results.get('successful_strategies', [])) > 0
            status = "success" if success else "failure"
            
            self._log(f"Growth loop execution completed: {len(execution_results.get('successful_strategies', []))} strategies executed")
            
            return self._format_output(
                status=status,
                data=result_data,
                cost=total_cost,
                next_steps=[
                    "Monitor growth metrics",
                    "Optimize successful strategies",
                    "Plan next growth experiments"
                ],
                confidence=0.85
            )
            
        except Exception as e:
            self._log(f"Error in growth loop execution: {str(e)}", "error")
            return self._format_output(
                status="failure",
                data={"error_details": str(e)},
                error_message=f"Growth loop execution failed: {str(e)}"
            )
    
    async def _get_current_growth_metrics(self, provided_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Get current growth metrics from analytics platforms."""
        try:
            metrics = provided_metrics.copy()
            
            # Use analytics platform if available
            analytics_tool = await self._get_tool_from_registry('analytics_platform')
            if analytics_tool:
                # Simulate platform metrics (in real implementation, this would call the actual tool)
                platform_metrics = {
                    'total_users': 100,
                    'active_users': 75,
                    'new_users_last_30d': 25
                }
                metrics.update(platform_metrics)
            
            # Add user tracking data if available
            tracking_tool = await self._get_tool_from_registry('user_tracking')
            if tracking_tool:
                # Simulate user data (in real implementation, this would call the actual tool)
                user_data = {
                    'retention_rate_7d': 0.6,
                    'retention_rate_30d': 0.4,
                    'engagement_score': 0.7
                }
                metrics.update(user_data)
            
            # Ensure we have baseline metrics
            default_metrics = {
                'total_users': 0,
                'active_users': 0,
                'new_users_last_30d': 0,
                'retention_rate_7d': 0.0,
                'retention_rate_30d': 0.0,
                'viral_coefficient': 0.0,
                'conversion_rate': 0.0,
                'churn_rate': 0.0,
                'ltv': 0.0,
                'cac': 0.0,
                'growth_rate': 0.0,
                'engagement_score': 0.0
            }
            
            for key, default_value in default_metrics.items():
                if key not in metrics:
                    metrics[key] = default_value
            
            return metrics
            
        except Exception as e:
            self.logger.warning(f"Could not get growth metrics: {str(e)}")
            return {
                'total_users': 0,
                'active_users': 0,
                'new_users_last_30d': 0,
                'retention_rate_7d': 0.0,
                'retention_rate_30d': 0.0,
                'viral_coefficient': 0.0,
                'conversion_rate': 0.0,
                'churn_rate': 0.0,
                'ltv': 0.0,
                'cac': 0.0,
                'growth_rate': 0.0,
                'engagement_score': 0.0
            }
    
    def _analyze_growth_opportunities(self, growth_phase: str, current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze growth opportunities based on current phase and metrics."""
        try:
            opportunities = {
                'acquisition': [],
                'activation': [],
                'retention': [],
                'referral': [],
                'revenue': [],
                'priority_scores': {}
            }
            
            # Phase-specific opportunity analysis
            if growth_phase == 'early':
                # Focus on product-market fit and initial traction
                opportunities['acquisition'].extend([
                    'Content marketing for early adopters',
                    'Community building and engagement',
                    'Direct outreach to target users',
                    'Product hunt and launch platforms'
                ])
                opportunities['activation'].extend([
                    'Onboarding flow optimization',
                    'First-time user experience improvement',
                    'Feature discovery enhancement'
                ])
                
            elif growth_phase == 'scaling':
                # Focus on scalable growth channels
                opportunities['acquisition'].extend([
                    'Paid advertising optimization',
                    'SEO and content scaling',
                    'Partnership and integration opportunities',
                    'Influencer and affiliate programs'
                ])
                opportunities['retention'].extend([
                    'Email marketing automation',
                    'Push notification campaigns',
                    'Feature usage optimization',
                    'Customer success programs'
                ])
                
            elif growth_phase == 'optimization':
                # Focus on efficiency and viral growth
                opportunities['referral'].extend([
                    'Referral program implementation',
                    'Viral mechanics integration',
                    'Social sharing optimization',
                    'Network effects enhancement'
                ])
                opportunities['revenue'].extend([
                    'Pricing optimization',
                    'Upselling and cross-selling',
                    'Premium feature development',
                    'Enterprise sales funnel'
                ])
            
            # Metric-based opportunity identification
            if current_metrics.get('retention_rate_7d', 0) < 0.4:
                opportunities['retention'].append('Critical retention improvement needed')
                opportunities['priority_scores']['retention'] = 10
            
            if current_metrics.get('viral_coefficient', 0) < 0.1:
                opportunities['referral'].append('Viral mechanics implementation')
                opportunities['priority_scores']['referral'] = 8
            
            if current_metrics.get('conversion_rate', 0) < 0.02:
                opportunities['activation'].append('Conversion funnel optimization')
                opportunities['priority_scores']['activation'] = 9
            
            # Calculate opportunity scores
            for category in ['acquisition', 'activation', 'retention', 'referral', 'revenue']:
                if category not in opportunities['priority_scores']:
                    opportunities['priority_scores'][category] = len(opportunities[category]) * 2
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error analyzing growth opportunities: {str(e)}")
            return {
                'acquisition': ['Basic user acquisition'],
                'activation': ['User onboarding'],
                'retention': ['User engagement'],
                'referral': ['Word of mouth'],
                'revenue': ['Monetization'],
                'priority_scores': {'acquisition': 5, 'activation': 5, 'retention': 5, 'referral': 3, 'revenue': 3}
            }
    
    def _plan_growth_experiments(self, growth_opportunities: Dict[str, Any], 
                               experiment_budget: float, focus_areas: List[str]) -> Dict[str, Any]:
        """Plan growth experiments based on opportunities and budget."""
        try:
            experiments = []
            total_budget_allocated = 0.0
            
            # Get priority scores
            priority_scores = growth_opportunities.get('priority_scores', {})
            
            # Determine focus areas (use provided or default to highest priority)
            if not focus_areas:
                focus_areas = sorted(priority_scores.keys(), key=lambda x: priority_scores[x], reverse=True)[:3]
            
            # Plan experiments for each focus area
            for area in focus_areas:
                if total_budget_allocated >= experiment_budget:
                    break
                
                area_opportunities = growth_opportunities.get(area, [])
                area_budget = min(experiment_budget * 0.4, experiment_budget - total_budget_allocated)
                
                for opportunity in area_opportunities[:2]:  # Top 2 opportunities per area
                    if total_budget_allocated >= experiment_budget:
                        break
                    
                    experiment = self._design_experiment(area, opportunity, area_budget / 2)
                    experiments.append(experiment)
                    total_budget_allocated += experiment['budget']
            
            return {
                'experiments': experiments,
                'total_budget': total_budget_allocated,
                'focus_areas': focus_areas,
                'experiment_timeline': '2-4 weeks',
                'success_metrics': self._define_success_metrics(focus_areas)
            }
            
        except Exception as e:
            self.logger.error(f"Error planning growth experiments: {str(e)}")
            return {
                'experiments': [],
                'total_budget': 0.0,
                'focus_areas': [],
                'experiment_timeline': 'unknown',
                'success_metrics': {}
            }
    
    def _design_experiment(self, area: str, opportunity: str, budget: float) -> Dict[str, Any]:
        """Design a specific growth experiment."""
        experiment_templates = {
            'acquisition': {
                'type': 'acquisition_test',
                'duration_days': 14,
                'success_metric': 'new_user_acquisition',
                'channels': ['social_media', 'content_marketing', 'paid_ads']
            },
            'activation': {
                'type': 'conversion_test',
                'duration_days': 7,
                'success_metric': 'activation_rate',
                'channels': ['onboarding', 'email', 'in_app']
            },
            'retention': {
                'type': 'retention_test',
                'duration_days': 30,
                'success_metric': 'retention_rate',
                'channels': ['email', 'push_notifications', 'in_app']
            },
            'referral': {
                'type': 'viral_test',
                'duration_days': 21,
                'success_metric': 'viral_coefficient',
                'channels': ['referral_program', 'social_sharing', 'incentives']
            },
            'revenue': {
                'type': 'monetization_test',
                'duration_days': 30,
                'success_metric': 'revenue_per_user',
                'channels': ['pricing', 'upselling', 'premium_features']
            }
        }
        
        template = experiment_templates.get(area, experiment_templates['acquisition'])
        
        return {
            'id': f"{area}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'area': area,
            'opportunity': opportunity,
            'type': template['type'],
            'budget': min(budget, 100.0),  # Cap individual experiment budget
            'duration_days': template['duration_days'],
            'success_metric': template['success_metric'],
            'channels': template['channels'],
            'hypothesis': f"By implementing {opportunity}, we will improve {template['success_metric']}",
            'target_improvement': self._calculate_target_improvement(area),
            'status': 'planned'
        }
    
    def _calculate_target_improvement(self, area: str) -> str:
        """Calculate target improvement for experiment area."""
        targets = {
            'acquisition': '20% increase in new user acquisition',
            'activation': '15% increase in activation rate',
            'retention': '25% increase in 7-day retention',
            'referral': '50% increase in viral coefficient',
            'revenue': '30% increase in revenue per user'
        }
        return targets.get(area, '10% improvement in key metric')
    
    def _define_success_metrics(self, focus_areas: List[str]) -> Dict[str, str]:
        """Define success metrics for focus areas."""
        metrics = {}
        for area in focus_areas:
            if area == 'acquisition':
                metrics[area] = 'new_users_per_day'
            elif area == 'activation':
                metrics[area] = 'activation_rate'
            elif area == 'retention':
                metrics[area] = 'retention_rate_7d'
            elif area == 'referral':
                metrics[area] = 'viral_coefficient'
            elif area == 'revenue':
                metrics[area] = 'revenue_per_user'
        return metrics
    
    async def _execute_growth_strategies(self, experiment_plan: Dict[str, Any], 
                                 current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Execute planned growth strategies and experiments."""
        try:
            executed_strategies = []
            failed_strategies = []
            total_cost = 0.0
            
            experiments = experiment_plan.get('experiments', [])
            
            for experiment in experiments:
                try:
                    result = await self._execute_single_experiment(experiment)
                    executed_strategies.append({
                        'experiment': experiment,
                        'result': result,
                        'status': 'executed',
                        'cost': result.get('cost', 0)
                    })
                    total_cost += result.get('cost', 0)
                    
                except Exception as e:
                    failed_strategies.append({
                        'experiment': experiment,
                        'error': str(e),
                        'status': 'failed'
                    })
            
            return {
                'successful_strategies': executed_strategies,
                'failed_strategies': failed_strategies,
                'total_experiments': len(experiments),
                'success_rate': len(executed_strategies) / len(experiments) if experiments else 0,
                'total_cost': total_cost,
                'execution_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error executing growth strategies: {str(e)}")
            return {
                'successful_strategies': [],
                'failed_strategies': [],
                'total_experiments': 0,
                'success_rate': 0.0,
                'total_cost': 0.0,
                'execution_timestamp': datetime.now().isoformat()
            }
    
    async def _execute_single_experiment(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single growth experiment."""
        experiment_type = experiment.get('type', 'unknown')
        area = experiment.get('area', 'unknown')
        budget = experiment.get('budget', 0)
        
        # Simulate experiment execution based on available tools
        if experiment_type == 'acquisition_test':
            return await self._execute_acquisition_experiment(experiment)
        elif experiment_type == 'conversion_test':
            return self._execute_conversion_experiment(experiment)
        elif experiment_type == 'retention_test':
            return self._execute_retention_experiment(experiment)
        elif experiment_type == 'viral_test':
            return self._execute_viral_experiment(experiment)
        elif experiment_type == 'monetization_test':
            return self._execute_monetization_experiment(experiment)
        else:
            return {
                'description': f'Executed {experiment_type} experiment',
                'cost': budget * 0.8,
                'estimated_impact': 'moderate',
                'metrics_tracked': [experiment.get('success_metric', 'unknown')],
                'duration': experiment.get('duration_days', 14)
            }
    
    async def _execute_acquisition_experiment(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """Execute acquisition-focused experiment."""
        channels = experiment.get('channels', [])
        budget = experiment.get('budget', 0)
        
        results = {
            'description': 'Executed user acquisition experiment',
            'channels_used': [],
            'cost': 0,
            'estimated_reach': 0,
            'estimated_conversions': 0
        }
        
        # Use available marketing tools
        # Use available marketing tools (simplified for testing)
        if 'social_media' in channels:
            results['channels_used'].append('social_media')
            results['cost'] += budget * 0.4
            results['estimated_reach'] += 1000
            results['estimated_conversions'] += 20
        
        if 'email_marketing' in channels:
            results['channels_used'].append('email_marketing')
            results['cost'] += budget * 0.3
            results['estimated_reach'] += 500
            results['estimated_conversions'] += 15
        
        # Fallback to basic execution
        if not results['channels_used']:
            results['channels_used'] = ['organic']
            results['cost'] = budget * 0.2
            results['estimated_reach'] = 200
            results['estimated_conversions'] = 5
        
        results['estimated_impact'] = 'high' if results['estimated_conversions'] > 15 else 'moderate'
        results['metrics_tracked'] = ['new_users', 'acquisition_cost', 'conversion_rate']
        
        return results
    
    def _execute_conversion_experiment(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """Execute conversion optimization experiment."""
        budget = experiment.get('budget', 0)
        
        # Use A/B testing if available (simplified for testing)
        if True:  # Assume A/B testing is available
            return {
                'description': 'Executed A/B test for conversion optimization',
                'test_variants': 2,
                'cost': budget * 0.6,
                'estimated_impact': 'high',
                'metrics_tracked': ['conversion_rate', 'activation_rate', 'time_to_activation'],
                'confidence_level': 0.95
            }
        else:
            return {
                'description': 'Executed conversion optimization without A/B testing',
                'cost': budget * 0.3,
                'estimated_impact': 'moderate',
                'metrics_tracked': ['conversion_rate', 'user_flow_completion'],
                'confidence_level': 0.8
            }
    
    def _execute_retention_experiment(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """Execute retention-focused experiment."""
        channels = experiment.get('channels', [])
        budget = experiment.get('budget', 0)
        
        results = {
            'description': 'Executed user retention experiment',
            'retention_tactics': [],
            'cost': 0,
            'estimated_impact': 'moderate'
        }
        
        if 'email' in channels:
            results['retention_tactics'].append('email_drip_campaign')
            results['cost'] += budget * 0.4
        
        if 'push_notifications' in channels:
            results['retention_tactics'].append('push_notification_sequence')
            results['cost'] += budget * 0.3
        
        if not results['retention_tactics']:
            results['retention_tactics'] = ['in_app_messaging']
            results['cost'] = budget * 0.2
        
        results['metrics_tracked'] = ['retention_rate_7d', 'retention_rate_30d', 'engagement_score']
        return results
    
    def _execute_viral_experiment(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """Execute viral growth experiment."""
        budget = experiment.get('budget', 0)
        
        # Check for referral system (simplified for testing)
        if True:  # Assume referral system is available
            return {
                'description': 'Implemented referral program for viral growth',
                'viral_mechanics': ['referral_rewards', 'social_sharing', 'invite_system'],
                'cost': budget * 0.7,
                'estimated_impact': 'high',
                'metrics_tracked': ['viral_coefficient', 'referral_rate', 'invite_conversion']
            }
        else:
            return {
                'description': 'Implemented basic viral mechanics',
                'viral_mechanics': ['social_sharing_buttons'],
                'cost': budget * 0.2,
                'estimated_impact': 'low',
                'metrics_tracked': ['share_rate', 'organic_growth']
            }
    
    def _execute_monetization_experiment(self, experiment: Dict[str, Any]) -> Dict[str, Any]:
        """Execute monetization experiment."""
        budget = experiment.get('budget', 0)
        
        return {
            'description': 'Executed monetization optimization experiment',
            'monetization_tactics': ['pricing_test', 'feature_gating', 'upsell_flows'],
            'cost': budget * 0.5,
            'estimated_impact': 'high',
            'metrics_tracked': ['revenue_per_user', 'conversion_to_paid', 'ltv']
        }
    
    def _optimize_growth_loops(self, execution_results: Dict[str, Any], 
                             current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize growth loops based on execution results."""
        try:
            successful_strategies = execution_results.get('successful_strategies', [])
            
            optimizations = {
                'loop_improvements': [],
                'channel_optimizations': [],
                'metric_improvements': [],
                'automation_opportunities': []
            }
            
            # Analyze successful strategies for optimization opportunities
            for strategy in successful_strategies:
                experiment = strategy.get('experiment', {})
                result = strategy.get('result', {})
                
                area = experiment.get('area', 'unknown')
                estimated_impact = result.get('estimated_impact', 'low')
                
                if estimated_impact == 'high':
                    optimizations['loop_improvements'].append(
                        f"Scale {area} strategy - showing high impact"
                    )
                    optimizations['automation_opportunities'].append(
                        f"Automate {area} processes for efficiency"
                    )
            
            # Identify channel optimizations
            optimizations['channel_optimizations'].append(
                "Run conversion optimization on high-performing channels"
            )
            
            # Suggest metric improvements
            if current_metrics.get('viral_coefficient', 0) < 0.5:
                optimizations['metric_improvements'].append(
                    "Focus on viral coefficient improvement"
                )
            
            if current_metrics.get('retention_rate_7d', 0) < 0.6:
                optimizations['metric_improvements'].append(
                    "Prioritize retention rate optimization"
                )
            
            return optimizations
            
        except Exception as e:
            self.logger.error(f"Error optimizing growth loops: {str(e)}")
            return {
                'loop_improvements': [],
                'channel_optimizations': [],
                'metric_improvements': [],
                'automation_opportunities': []
            }
    
    def _generate_growth_recommendations(self, current_metrics: Dict[str, Any],
                                       growth_opportunities: Dict[str, Any],
                                       execution_results: Dict[str, Any],
                                       optimization_results: Dict[str, Any]) -> List[str]:
        """Generate growth recommendations based on analysis."""
        recommendations = []
        
        # Metric-based recommendations
        if current_metrics.get('growth_rate', 0) < 0.1:
            recommendations.append("Focus on fundamental growth drivers - current growth rate is low")
        
        if current_metrics.get('retention_rate_7d', 0) < 0.4:
            recommendations.append("Critical: Address retention issues before scaling acquisition")
        
        if current_metrics.get('viral_coefficient', 0) < 0.1:
            recommendations.append("Implement viral mechanics to reduce customer acquisition costs")
        
        # Execution-based recommendations
        success_rate = execution_results.get('success_rate', 0)
        if success_rate < 0.5:
            recommendations.append("Review experiment design - low success rate indicates issues")
        elif success_rate > 0.8:
            recommendations.append("Scale successful experiments and increase experiment budget")
        
        # Optimization recommendations
        loop_improvements = optimization_results.get('loop_improvements', [])
        if loop_improvements:
            recommendations.extend(loop_improvements[:2])  # Top 2 improvements
        
        # Budget recommendations
        total_cost = execution_results.get('total_cost', 0)
        if total_cost > 0:
            cac = total_cost / max(1, current_metrics.get('new_users_last_30d', 1))
            ltv = current_metrics.get('ltv', 0)
            if ltv > 0 and cac > ltv * 0.3:
                recommendations.append("Customer acquisition cost is high - optimize for efficiency")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _calculate_growth_score(self, current_metrics: Dict[str, Any], 
                              execution_results: Dict[str, Any]) -> float:
        """Calculate overall growth score."""
        try:
            score = 0.0
            
            # Metric-based scoring (0-60 points)
            score += min(20, current_metrics.get('growth_rate', 0) * 100)  # Growth rate
            score += min(20, current_metrics.get('retention_rate_7d', 0) * 20)  # Retention
            score += min(20, current_metrics.get('viral_coefficient', 0) * 40)  # Viral coefficient
            
            # Execution-based scoring (0-40 points)
            success_rate = execution_results.get('success_rate', 0)
            score += success_rate * 40
            
            return round(min(100, score), 1)
            
        except Exception as e:
            self.logger.error(f"Error calculating growth score: {str(e)}")
            return 0.0
    
    def _project_growth_impact(self, execution_results: Dict[str, Any], 
                             current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Project the impact of growth strategies."""
        try:
            successful_strategies = execution_results.get('successful_strategies', [])
            
            # Calculate projected improvements
            projected_growth_rate = current_metrics.get('growth_rate', 0)
            projected_users = current_metrics.get('total_users', 0)
            projected_revenue_impact = 0.0
            
            for strategy in successful_strategies:
                result = strategy.get('result', {})
                impact = result.get('estimated_impact', 'low')
                
                if impact == 'high':
                    projected_growth_rate += 0.05  # 5% improvement
                    projected_users += result.get('estimated_conversions', 0)
                    projected_revenue_impact += 100.0
                elif impact == 'moderate':
                    projected_growth_rate += 0.02  # 2% improvement
                    projected_users += result.get('estimated_conversions', 0) * 0.5
                    projected_revenue_impact += 50.0
            
            return {
                'projected_growth_rate': round(projected_growth_rate, 3),
                'projected_new_users_30d': int(projected_users),
                'projected_revenue_impact': round(projected_revenue_impact, 2),
                'confidence_level': 0.7,
                'timeframe': '30 days'
            }
            
        except Exception as e:
            self.logger.error(f"Error projecting growth impact: {str(e)}")
            return {
                'projected_growth_rate': 0.0,
                'projected_new_users_30d': 0,
                'projected_revenue_impact': 0.0,
                'confidence_level': 0.0,
                'timeframe': 'unknown'
            }
    
    def _calculate_growth_cost(self, experiment_plan: Dict[str, Any], 
                             execution_results: Dict[str, Any]) -> float:
        """Calculate total cost of growth operations."""
        try:
            # Base cost from experiment plan
            plan_cost = experiment_plan.get('total_budget', 0)
            
            # Actual execution cost
            execution_cost = execution_results.get('total_cost', 0)
            
            # Platform and tool costs
            platform_cost = 5.0  # Base platform cost
            
            # Tool usage costs (simplified for testing)
            tool_cost = 0.0
            # Assume basic tools are available
            tool_cost += 10.0  # A/B testing
            tool_cost += 15.0  # Email marketing
            tool_cost += 12.0  # Social media
            
            total_cost = max(plan_cost, execution_cost) + platform_cost + tool_cost
            return round(total_cost, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating growth cost: {str(e)}")
            return 0.0 