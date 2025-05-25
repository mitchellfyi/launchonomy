"""
FinanceAgent - Handles financial guardrails and budget enforcement for Launchonomy.

This agent encapsulates the enforce_guardrail workflow, providing:
- Budget monitoring and enforcement
- Financial risk assessment
- Cost optimization recommendations
- Revenue tracking and forecasting
- Automated financial controls
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from ..base.workflow_agent import BaseWorkflowAgent, WorkflowOutput

logger = logging.getLogger(__name__)


class FinanceAgent(BaseWorkflowAgent):
    """
    FinanceAgent encapsulates the "enforce_guardrail" workflow step.
    Handles financial guardrails and budget enforcement for Launchonomy.
    """
    
    REQUIRED_TOOLS = ["financial_monitoring", "budget_tracking"]
    OPTIONAL_TOOLS = [
        "stripe_analytics", "expense_tracking", "revenue_forecasting", 
        "cost_optimization", "risk_assessment", "automated_billing",
        "financial_reporting", "tax_calculation"
    ]
    
    def __init__(self, registry=None, orchestrator=None):
        super().__init__("FinanceAgent", registry, orchestrator)
        self.system_prompt = self._build_system_prompt()
        
        # Financial thresholds and limits
        self.budget_limits = {}
        self.risk_tolerance = 'conservative'
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with current Launchonomy context."""
        context = self._get_launchonomy_context()
        
        return f"""You are FinanceAgent, the financial guardrails and budget enforcement specialist in the Launchonomy autonomous business system.

MISSION CONTEXT:
{context}

YOUR ROLE:
You enforce financial guardrails and budget constraints to ensure:
- Total costs never exceed 20% of revenue
- Operations stay within allocated budgets
- Financial risks are properly assessed and mitigated
- Cash flow remains positive and sustainable

CORE CAPABILITIES:
1. Budget Monitoring & Enforcement
2. Financial Risk Assessment
3. Cost Optimization Recommendations
4. Revenue Tracking and Forecasting
5. Automated Financial Controls

Always prioritize financial sustainability and the 20% cost constraint."""
        
    async def execute(self, input_data: Dict[str, Any]) -> WorkflowOutput:
        """
        Execute financial guardrail enforcement workflow.
        
        Args:
            input_data: Dictionary containing:
                - operation_type: Type of operation to check (required)
                - estimated_cost: Estimated cost of operation (required)
                - time_period: Time period for budget check (optional, defaults to 'monthly')
                - project_id: Project identifier (optional)
                - force_approval: Override guardrails if True (optional)
        
        Returns:
            WorkflowOutput with financial approval/rejection and recommendations
        """
        try:
            self._log(f"Starting financial guardrail enforcement for {input_data.get('operation_type', 'unknown')}")
            
            # Validate required inputs
            operation_type = input_data.get('operation_type')
            estimated_cost = input_data.get('estimated_cost', 0)
            
            if not operation_type:
                return self._format_output(
                    status="failure",
                    data={},
                    error_message="Operation type is required for financial guardrail check"
                )
            
            # Get current financial status
            financial_status = await self._get_financial_status(input_data.get('time_period', 'monthly'))
            
            # Perform budget check
            budget_check = self._check_budget_limits(operation_type, estimated_cost, financial_status)
            
            # Assess financial risk
            risk_assessment = self._assess_financial_risk(operation_type, estimated_cost, financial_status)
            
            # Generate recommendations
            recommendations = self._generate_financial_recommendations(
                budget_check, risk_assessment, financial_status
            )
            
            # Make approval decision
            approval_decision = self._make_approval_decision(
                budget_check, risk_assessment, input_data.get('force_approval', False)
            )
            
            # Calculate total cost estimate for this operation
            total_cost = self._calculate_operation_cost(operation_type, estimated_cost)
            
            result_data = {
                'approval_status': approval_decision['status'],
                'approved_amount': approval_decision['approved_amount'],
                'budget_status': budget_check,
                'risk_assessment': risk_assessment,
                'financial_status': financial_status,
                'recommendations': recommendations,
                'operation_details': {
                    'type': operation_type,
                    'estimated_cost': estimated_cost,
                    'total_cost': total_cost
                },
                'guardrails_applied': approval_decision['guardrails'],
                'next_review_date': (datetime.now() + timedelta(days=7)).isoformat()
            }
            
            success = approval_decision['status'] in ['approved', 'conditionally_approved']
            status = "success" if success else "failure"
            
            self._log(f"Financial guardrail check completed: {approval_decision['status']}")
            
            return self._format_output(
                status=status,
                data=result_data,
                cost=total_cost,
                next_steps=[
                    "Monitor budget utilization",
                    "Review financial performance",
                    "Optimize cost efficiency"
                ],
                confidence=0.9
            )
            
        except Exception as e:
            self._log(f"Error in financial guardrail enforcement: {str(e)}", "error")
            return self._format_output(
                status="failure",
                data={"error_details": str(e)},
                error_message=f"Financial guardrail check failed: {str(e)}"
            )
    
    async def _get_financial_status(self, time_period: str) -> Dict[str, Any]:
        """Get current financial status and spending."""
        try:
            # Use financial monitoring tool if available
            financial_tool = await self._get_tool_from_registry('financial_monitoring')
            if financial_tool:
                # Simulate financial status (in real implementation, this would call the actual tool)
                status = {
                    'current_spending': 250.0,
                    'revenue': 1250.0,
                    'profit_margin': 0.8,
                    'cash_flow': 1000.0
                }
            else:
                # Fallback to basic status
                status = {
                    'current_spending': 0.0,
                    'revenue': 0.0,
                    'profit_margin': 0.0,
                    'cash_flow': 0.0
                }
            
            # Add budget tracking if available
            budget_tool = await self._get_tool_from_registry('budget_tracking')
            if budget_tool:
                # Simulate budget data
                budget_data = {
                    'budget_utilization': 0.5,
                    'monthly_limit': 500.0,
                    'remaining_budget': 250.0
                }
                status.update(budget_data)
            
            return status
            
        except Exception as e:
            self.logger.warning(f"Could not get financial status: {str(e)}")
            return {
                'current_spending': 0.0,
                'revenue': 0.0,
                'profit_margin': 0.0,
                'cash_flow': 0.0,
                'budget_utilization': 0.0
            }
    
    def _check_budget_limits(self, operation_type: str, estimated_cost: float, 
                           financial_status: Dict[str, Any]) -> Dict[str, Any]:
        """Check if operation fits within budget limits."""
        try:
            # Get budget limits from mission context
            monthly_limit = self.budget_limits.get('monthly_limit', 1000.0)
            operation_limit = self.budget_limits.get(f'{operation_type}_limit', monthly_limit * 0.3)
            
            current_spending = financial_status.get('current_spending', 0.0)
            remaining_budget = monthly_limit - current_spending
            
            # Calculate budget utilization
            new_spending = current_spending + estimated_cost
            utilization_after = (new_spending / monthly_limit) * 100
            
            # Determine budget status
            if estimated_cost > operation_limit:
                status = 'exceeds_operation_limit'
            elif estimated_cost > remaining_budget:
                status = 'exceeds_remaining_budget'
            elif utilization_after > 90:
                status = 'high_utilization'
            elif utilization_after > 70:
                status = 'moderate_utilization'
            else:
                status = 'within_limits'
            
            return {
                'status': status,
                'monthly_limit': monthly_limit,
                'operation_limit': operation_limit,
                'current_spending': current_spending,
                'remaining_budget': remaining_budget,
                'estimated_cost': estimated_cost,
                'utilization_after': utilization_after,
                'fits_in_budget': status in ['within_limits', 'moderate_utilization']
            }
            
        except Exception as e:
            self.logger.error(f"Error checking budget limits: {str(e)}")
            return {
                'status': 'error',
                'fits_in_budget': False,
                'error': str(e)
            }
    
    def _assess_financial_risk(self, operation_type: str, estimated_cost: float,
                             financial_status: Dict[str, Any]) -> Dict[str, Any]:
        """Assess financial risk of the operation."""
        try:
            risk_factors = []
            risk_score = 0
            
            # Revenue risk assessment
            revenue = financial_status.get('revenue', 0.0)
            if revenue == 0:
                risk_factors.append("No current revenue stream")
                risk_score += 30
            elif estimated_cost > revenue * 0.5:
                risk_factors.append("Cost exceeds 50% of current revenue")
                risk_score += 20
            
            # Cash flow risk
            cash_flow = financial_status.get('cash_flow', 0.0)
            if cash_flow < 0:
                risk_factors.append("Negative cash flow")
                risk_score += 25
            elif cash_flow < estimated_cost:
                risk_factors.append("Insufficient cash flow to cover cost")
                risk_score += 15
            
            # Operation type risk
            high_risk_operations = ['paid_advertising', 'infrastructure_scaling', 'new_market_entry']
            if operation_type in high_risk_operations:
                risk_factors.append(f"High-risk operation type: {operation_type}")
                risk_score += 15
            
            # Budget utilization risk
            utilization = financial_status.get('budget_utilization', 0.0)
            if utilization > 80:
                risk_factors.append("High budget utilization")
                risk_score += 10
            
            # Determine risk level
            if risk_score >= 50:
                risk_level = 'high'
            elif risk_score >= 25:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'risk_factors': risk_factors,
                'mitigation_required': risk_level in ['high', 'medium']
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing financial risk: {str(e)}")
            return {
                'risk_level': 'unknown',
                'risk_score': 100,
                'risk_factors': [f"Risk assessment error: {str(e)}"],
                'mitigation_required': True
            }
    
    def _generate_financial_recommendations(self, budget_check: Dict[str, Any],
                                          risk_assessment: Dict[str, Any],
                                          financial_status: Dict[str, Any]) -> List[str]:
        """Generate financial recommendations based on analysis."""
        recommendations = []
        
        # Budget recommendations
        if not budget_check.get('fits_in_budget', False):
            recommendations.append("Consider reducing operation scope to fit within budget")
            recommendations.append("Explore cost optimization opportunities")
        
        if budget_check.get('utilization_after', 0) > 80:
            recommendations.append("Monitor spending closely for remainder of period")
        
        # Risk mitigation recommendations
        risk_level = risk_assessment.get('risk_level', 'unknown')
        if risk_level == 'high':
            recommendations.append("Implement additional risk controls before proceeding")
            recommendations.append("Consider phased approach to reduce financial exposure")
        elif risk_level == 'medium':
            recommendations.append("Monitor operation closely for cost overruns")
        
        # Revenue recommendations
        if financial_status.get('revenue', 0) == 0:
            recommendations.append("Prioritize revenue-generating activities")
        
        # Cash flow recommendations
        if financial_status.get('cash_flow', 0) < 0:
            recommendations.append("Focus on improving cash flow before major expenditures")
        
        # Cost optimization recommendations
        recommendations.append("Run cost optimization analysis for potential savings")
        
        return recommendations
    
    def _make_approval_decision(self, budget_check: Dict[str, Any],
                              risk_assessment: Dict[str, Any],
                              force_approval: bool) -> Dict[str, Any]:
        """Make final approval decision based on all factors."""
        try:
            if force_approval:
                return {
                    'status': 'approved',
                    'approved_amount': budget_check.get('estimated_cost', 0),
                    'message': 'Operation approved with force override',
                    'guardrails': ['force_override_applied']
                }
            
            fits_budget = budget_check.get('fits_in_budget', False)
            risk_level = risk_assessment.get('risk_level', 'high')
            
            guardrails = []
            
            # Decision logic
            if not fits_budget and risk_level == 'high':
                status = 'rejected'
                approved_amount = 0
                message = 'Operation rejected: exceeds budget and high risk'
            elif not fits_budget:
                # Offer reduced amount
                remaining_budget = budget_check.get('remaining_budget', 0)
                status = 'conditionally_approved'
                approved_amount = max(0, remaining_budget * 0.8)  # 80% of remaining
                message = f'Conditionally approved for reduced amount: ${approved_amount:.2f}'
                guardrails.append('reduced_amount')
            elif risk_level == 'high':
                status = 'conditionally_approved'
                approved_amount = budget_check.get('estimated_cost', 0)
                message = 'Conditionally approved with enhanced monitoring'
                guardrails.extend(['enhanced_monitoring', 'milestone_reviews'])
            else:
                status = 'approved'
                approved_amount = budget_check.get('estimated_cost', 0)
                message = 'Operation approved within financial guardrails'
            
            # Add standard guardrails based on amount
            if approved_amount > 500:
                guardrails.append('executive_notification')
            if approved_amount > 1000:
                guardrails.append('board_notification')
            
            return {
                'status': status,
                'approved_amount': approved_amount,
                'message': message,
                'guardrails': guardrails
            }
            
        except Exception as e:
            self.logger.error(f"Error making approval decision: {str(e)}")
            return {
                'status': 'rejected',
                'approved_amount': 0,
                'message': f'Approval decision failed: {str(e)}',
                'guardrails': ['error_fallback']
            }
    
    def _calculate_operation_cost(self, operation_type: str, estimated_cost: float) -> float:
        """Calculate total cost including overhead and fees."""
        try:
            # Base cost
            total_cost = estimated_cost
            
            # Add operation-specific overhead
            overhead_rates = {
                'marketing': 0.15,  # 15% overhead for marketing operations
                'infrastructure': 0.10,  # 10% for infrastructure
                'development': 0.20,  # 20% for development
                'default': 0.12  # 12% default overhead
            }
            
            overhead_rate = overhead_rates.get(operation_type, overhead_rates['default'])
            total_cost += estimated_cost * overhead_rate
            
            # Add platform fees if using external tools
            if estimated_cost > 0:
                total_cost += 2.50  # Base platform fee
            
            return round(total_cost, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating operation cost: {str(e)}")
            return estimated_cost 