import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base_workflow_agent import BaseWorkflowAgent, WorkflowOutput

class AnalyticsAgent(BaseWorkflowAgent):
    """
    AnalyticsAgent encapsulates the "fetch_metrics" workflow step.
    Collects, analyzes, and reports on key business metrics including revenue,
    customer acquisition, conversion rates, and operational efficiency.
    """
    
    REQUIRED_TOOLS = ["analytics_platform"]
    OPTIONAL_TOOLS = ["google_analytics", "stripe_analytics", "email_analytics", "social_media_analytics", "database_analytics"]
    
    def __init__(self, registry=None, orchestrator=None):
        super().__init__("AnalyticsAgent", registry, orchestrator)
        self.system_prompt = self._build_system_prompt()
        self.metrics_history = []
        self.kpi_thresholds = self._initialize_kpi_thresholds()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with current Launchonomy context."""
        context = self._get_launchonomy_context()
        
        return f"""You are AnalyticsAgent, the business intelligence and metrics specialist in the Launchonomy autonomous business system.

MISSION CONTEXT:
{json.dumps(context, indent=2)}

YOUR ROLE:
You collect, analyze, and report on critical business metrics that drive autonomous decision-making:
- Revenue and profitability tracking
- Customer acquisition and conversion metrics
- Cost efficiency and budget utilization
- Product performance and user engagement
- Operational health and system performance

CORE CAPABILITIES:
1. Data Collection & Integration
   - Aggregate data from multiple sources (analytics, payments, email, social)
   - Ensure data quality and consistency
   - Handle real-time and batch data processing
   - Maintain historical data for trend analysis

2. Key Performance Indicators (KPIs)
   - Revenue: Total revenue, MRR, ARR, revenue growth rate
   - Customer Metrics: CAC, LTV, churn rate, conversion rates
   - Cost Metrics: Cost ratio (<20% constraint), CPA, operational costs
   - Product Metrics: User engagement, feature adoption, retention
   - Marketing Metrics: Campaign ROI, channel performance, attribution

3. Analysis & Insights
   - Identify trends and patterns in business performance
   - Detect anomalies and potential issues early
   - Calculate growth rates and projections
   - Perform cohort analysis and segmentation

4. Automated Reporting
   - Generate real-time dashboards for key stakeholders
   - Send automated alerts for threshold breaches
   - Create executive summaries and recommendations
   - Track progress toward business objectives

CRITICAL CONSTRAINTS:
- Cost Ratio Monitoring: Ensure total costs never exceed 20% of revenue
- First Customer Focus: Prioritize metrics that track progress to first paying customer
- Profitability Tracking: Monitor path to sustainable profitability
- Autonomous Operation: All metrics collection and analysis must be automated

DECISION SUPPORT:
Your metrics directly inform autonomous business decisions:
- Budget allocation and reallocation
- Campaign optimization and scaling
- Product development priorities
- Growth strategy adjustments

Always provide actionable insights that enable data-driven autonomous decisions."""

    def _initialize_kpi_thresholds(self) -> Dict[str, Any]:
        """Initialize KPI thresholds for automated monitoring."""
        return {
            "cost_ratio": {"max": 0.20, "warning": 0.15, "critical": 0.18},
            "customer_acquisition_cost": {"max": 50.0, "warning": 40.0, "critical": 45.0},
            "conversion_rate": {"min": 0.01, "warning": 0.015, "target": 0.05},
            "revenue_growth": {"min": 0.0, "warning": 0.10, "target": 0.50},
            "churn_rate": {"max": 0.10, "warning": 0.05, "critical": 0.08}
        }

    async def execute(self, input_data: Dict[str, Any]) -> WorkflowOutput:
        """
        Execute metrics collection and analysis workflow.
        
        Args:
            input_data: Contains analysis type, time period, and specific metrics to fetch
            
        Returns:
            WorkflowOutput with comprehensive metrics analysis and insights
        """
        self._log("Starting metrics collection and analysis workflow")
        
        try:
            # Extract input parameters
            analysis_type = input_data.get("analysis_type", "comprehensive")  # comprehensive, financial, marketing, product
            time_period = input_data.get("time_period", "current_month")
            specific_metrics = input_data.get("specific_metrics", [])
            include_predictions = input_data.get("include_predictions", True)
            
            # Get available analytics tools
            available_tools = self._get_available_analytics_tools()
            
            # Collect raw metrics data
            raw_metrics = await self._collect_raw_metrics(
                analysis_type, time_period, specific_metrics, available_tools
            )
            
            # Process and analyze metrics
            processed_metrics = await self._process_metrics(raw_metrics, analysis_type)
            
            # Generate insights and recommendations
            insights = await self._generate_insights(processed_metrics, analysis_type)
            
            # Check for threshold violations and alerts
            alerts = await self._check_thresholds(processed_metrics)
            
            # Generate predictions if requested
            predictions = {}
            if include_predictions:
                predictions = await self._generate_predictions(processed_metrics)
            
            output_data = {
                "analysis_type": analysis_type,
                "time_period": time_period,
                "collection_timestamp": self._get_launchonomy_context()["timestamp"],
                "raw_metrics": raw_metrics,
                "processed_metrics": processed_metrics,
                "insights": insights,
                "alerts": alerts,
                "predictions": predictions,
                "data_quality": self._assess_data_quality(raw_metrics),
                "next_analysis_recommended": self._calculate_next_analysis_time()
            }
            
            # Store metrics in history
            self.metrics_history.append({
                "timestamp": output_data["collection_timestamp"],
                "metrics": processed_metrics,
                "analysis_type": analysis_type
            })
            
            # Keep only last 30 entries to manage memory
            if len(self.metrics_history) > 30:
                self.metrics_history = self.metrics_history[-30:]
            
            self._log(f"Metrics analysis completed. {len(alerts)} alerts generated.")
            
            return self._format_output(
                status="success",
                data=output_data,
                cost=self._estimate_analytics_cost(len(available_tools), analysis_type),
                tools_used=list(available_tools.keys()),
                next_steps=self._generate_next_steps(insights, alerts),
                confidence=0.95
            )
            
        except Exception as e:
            self._log(f"Error in metrics analysis: {str(e)}", "error")
            return self._format_output(
                status="failure",
                data={"error_details": str(e)},
                error_message=f"Metrics analysis failed: {str(e)}"
            )
    
    def _get_available_analytics_tools(self) -> Dict[str, Any]:
        """Get available tools for analytics and data collection."""
        available_tools = {}
        
        for tool_name in self.REQUIRED_TOOLS + self.OPTIONAL_TOOLS:
            tool_spec = self._get_tool_from_registry(tool_name)
            if tool_spec:
                available_tools[tool_name] = tool_spec
                self._log(f"Analytics tool available: {tool_name}")
            else:
                self._log(f"Analytics tool not available: {tool_name}", "warning")
        
        return available_tools
    
    async def _collect_raw_metrics(self, analysis_type: str, time_period: str,
                                 specific_metrics: List[str], 
                                 available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Collect raw metrics data from various sources."""
        
        # Simulate data collection from various sources
        # In real implementation, this would call actual analytics APIs
        
        raw_data = {
            "revenue_data": await self._collect_revenue_metrics(time_period, available_tools),
            "customer_data": await self._collect_customer_metrics(time_period, available_tools),
            "marketing_data": await self._collect_marketing_metrics(time_period, available_tools),
            "product_data": await self._collect_product_metrics(time_period, available_tools),
            "operational_data": await self._collect_operational_metrics(time_period, available_tools)
        }
        
        # Filter based on analysis type and specific metrics
        if analysis_type == "financial":
            raw_data = {k: v for k, v in raw_data.items() if k in ["revenue_data", "operational_data"]}
        elif analysis_type == "marketing":
            raw_data = {k: v for k, v in raw_data.items() if k in ["marketing_data", "customer_data"]}
        elif analysis_type == "product":
            raw_data = {k: v for k, v in raw_data.items() if k in ["product_data", "customer_data"]}
        
        return raw_data
    
    async def _collect_revenue_metrics(self, time_period: str, available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Collect revenue and financial metrics."""
        
        # Simulate revenue data collection
        base_revenue = 1250.0  # Simulated current revenue
        
        return {
            "total_revenue": base_revenue,
            "monthly_recurring_revenue": base_revenue * 0.8,  # 80% is recurring
            "one_time_revenue": base_revenue * 0.2,
            "revenue_growth_rate": 0.15,  # 15% growth
            "average_order_value": 49.99,
            "total_transactions": int(base_revenue / 49.99),
            "refunds": base_revenue * 0.02,  # 2% refund rate
            "net_revenue": base_revenue * 0.98,
            "payment_processing_fees": base_revenue * 0.029,  # 2.9% Stripe fees
            "collection_source": "stripe_analytics" if "stripe_analytics" in available_tools else "simulated"
        }
    
    async def _collect_customer_metrics(self, time_period: str, available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Collect customer acquisition and behavior metrics."""
        
        return {
            "total_customers": 47,
            "new_customers": 12,
            "returning_customers": 35,
            "customer_acquisition_cost": 28.50,
            "customer_lifetime_value": 149.97,
            "churn_rate": 0.04,  # 4% monthly churn
            "retention_rate": 0.96,
            "conversion_rate": 0.032,  # 3.2% conversion rate
            "signup_to_paid_conversion": 0.15,  # 15% of signups become paid
            "trial_to_paid_conversion": 0.25,  # 25% of trials convert
            "collection_source": "analytics_platform"
        }
    
    async def _collect_marketing_metrics(self, time_period: str, available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Collect marketing campaign and channel performance metrics."""
        
        return {
            "total_marketing_spend": 180.0,
            "cost_per_acquisition": 15.0,
            "return_on_ad_spend": 6.94,  # $6.94 revenue per $1 spent
            "channel_performance": {
                "email_marketing": {"spend": 50.0, "conversions": 8, "cpa": 6.25},
                "social_media": {"spend": 80.0, "conversions": 3, "cpa": 26.67},
                "paid_advertising": {"spend": 50.0, "conversions": 1, "cpa": 50.0}
            },
            "campaign_metrics": {
                "total_impressions": 45000,
                "total_clicks": 900,
                "click_through_rate": 0.02,
                "cost_per_click": 0.20
            },
            "organic_metrics": {
                "organic_traffic": 1200,
                "organic_conversions": 5,
                "organic_conversion_rate": 0.0042
            },
            "collection_source": "multiple_platforms"
        }
    
    async def _collect_product_metrics(self, time_period: str, available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Collect product usage and engagement metrics."""
        
        return {
            "total_users": 156,
            "active_users": 89,
            "daily_active_users": 23,
            "weekly_active_users": 67,
            "monthly_active_users": 89,
            "user_engagement": {
                "average_session_duration": 8.5,  # minutes
                "pages_per_session": 4.2,
                "bounce_rate": 0.35
            },
            "feature_adoption": {
                "core_feature_usage": 0.78,  # 78% of users use core features
                "advanced_feature_usage": 0.23,
                "feature_completion_rate": 0.65
            },
            "user_satisfaction": {
                "nps_score": 42,
                "satisfaction_rating": 4.1,
                "support_tickets": 3
            },
            "collection_source": "google_analytics" if "google_analytics" in available_tools else "simulated"
        }
    
    async def _collect_operational_metrics(self, time_period: str, available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Collect operational and cost metrics."""
        
        total_revenue = 1250.0  # From revenue metrics
        
        operational_costs = {
            "hosting_costs": 25.0,
            "software_subscriptions": 89.0,
            "payment_processing": 36.25,  # 2.9% of revenue
            "marketing_spend": 180.0,
            "domain_and_ssl": 1.0,
            "email_service": 15.0,
            "analytics_tools": 0.0,  # Free tier
            "other_operational": 12.0
        }
        
        total_costs = sum(operational_costs.values())
        cost_ratio = total_costs / total_revenue if total_revenue > 0 else 1.0
        
        return {
            "total_operational_costs": total_costs,
            "cost_breakdown": operational_costs,
            "cost_ratio": cost_ratio,
            "cost_ratio_percentage": cost_ratio * 100,
            "profit_margin": (total_revenue - total_costs) / total_revenue if total_revenue > 0 else -1.0,
            "net_profit": total_revenue - total_costs,
            "burn_rate": total_costs,  # Monthly burn rate
            "runway_months": 500 / total_costs if total_costs > 0 else float('inf'),  # Based on $500 initial budget
            "collection_source": "internal_tracking"
        }
    
    async def _process_metrics(self, raw_metrics: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Process raw metrics into actionable insights."""
        
        processed = {
            "summary": self._create_metrics_summary(raw_metrics),
            "kpi_dashboard": self._create_kpi_dashboard(raw_metrics),
            "trend_analysis": self._analyze_trends(raw_metrics),
            "performance_scores": self._calculate_performance_scores(raw_metrics),
            "comparative_analysis": self._compare_with_history(raw_metrics)
        }
        
        return processed
    
    def _create_metrics_summary(self, raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Create high-level metrics summary."""
        
        revenue_data = raw_metrics.get("revenue_data", {})
        customer_data = raw_metrics.get("customer_data", {})
        operational_data = raw_metrics.get("operational_data", {})
        
        return {
            "business_health": "healthy" if operational_data.get("cost_ratio", 1.0) < 0.20 else "at_risk",
            "revenue_status": revenue_data.get("total_revenue", 0),
            "customer_count": customer_data.get("total_customers", 0),
            "profitability": operational_data.get("net_profit", 0),
            "cost_efficiency": operational_data.get("cost_ratio_percentage", 100),
            "growth_trajectory": "positive" if revenue_data.get("revenue_growth_rate", 0) > 0 else "flat"
        }
    
    def _create_kpi_dashboard(self, raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Create KPI dashboard with key metrics."""
        
        revenue_data = raw_metrics.get("revenue_data", {})
        customer_data = raw_metrics.get("customer_data", {})
        marketing_data = raw_metrics.get("marketing_data", {})
        operational_data = raw_metrics.get("operational_data", {})
        
        return {
            "financial_kpis": {
                "total_revenue": revenue_data.get("total_revenue", 0),
                "mrr": revenue_data.get("monthly_recurring_revenue", 0),
                "net_profit": operational_data.get("net_profit", 0),
                "cost_ratio": operational_data.get("cost_ratio", 0),
                "profit_margin": operational_data.get("profit_margin", 0)
            },
            "customer_kpis": {
                "total_customers": customer_data.get("total_customers", 0),
                "new_customers": customer_data.get("new_customers", 0),
                "cac": customer_data.get("customer_acquisition_cost", 0),
                "ltv": customer_data.get("customer_lifetime_value", 0),
                "churn_rate": customer_data.get("churn_rate", 0),
                "conversion_rate": customer_data.get("conversion_rate", 0)
            },
            "marketing_kpis": {
                "marketing_spend": marketing_data.get("total_marketing_spend", 0),
                "roas": marketing_data.get("return_on_ad_spend", 0),
                "cpa": marketing_data.get("cost_per_acquisition", 0),
                "ctr": marketing_data.get("campaign_metrics", {}).get("click_through_rate", 0)
            },
            "operational_kpis": {
                "total_costs": operational_data.get("total_operational_costs", 0),
                "burn_rate": operational_data.get("burn_rate", 0),
                "runway_months": operational_data.get("runway_months", 0)
            }
        }
    
    def _analyze_trends(self, raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends based on historical data."""
        
        if len(self.metrics_history) < 2:
            return {"status": "insufficient_data", "message": "Need more historical data for trend analysis"}
        
        # Compare with previous period
        current_revenue = raw_metrics.get("revenue_data", {}).get("total_revenue", 0)
        current_customers = raw_metrics.get("customer_data", {}).get("total_customers", 0)
        current_cost_ratio = raw_metrics.get("operational_data", {}).get("cost_ratio", 0)
        
        # Get previous metrics (simplified for demo)
        prev_metrics = self.metrics_history[-1]["metrics"] if self.metrics_history else {}
        prev_revenue = prev_metrics.get("kpi_dashboard", {}).get("financial_kpis", {}).get("total_revenue", current_revenue)
        prev_customers = prev_metrics.get("kpi_dashboard", {}).get("customer_kpis", {}).get("total_customers", current_customers)
        prev_cost_ratio = prev_metrics.get("kpi_dashboard", {}).get("financial_kpis", {}).get("cost_ratio", current_cost_ratio)
        
        return {
            "revenue_trend": {
                "direction": "up" if current_revenue > prev_revenue else "down" if current_revenue < prev_revenue else "flat",
                "change_percentage": ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0,
                "change_amount": current_revenue - prev_revenue
            },
            "customer_trend": {
                "direction": "up" if current_customers > prev_customers else "down" if current_customers < prev_customers else "flat",
                "change_count": current_customers - prev_customers,
                "growth_rate": ((current_customers - prev_customers) / prev_customers * 100) if prev_customers > 0 else 0
            },
            "cost_efficiency_trend": {
                "direction": "improving" if current_cost_ratio < prev_cost_ratio else "worsening" if current_cost_ratio > prev_cost_ratio else "stable",
                "change_percentage": ((current_cost_ratio - prev_cost_ratio) / prev_cost_ratio * 100) if prev_cost_ratio > 0 else 0
            }
        }
    
    def _calculate_performance_scores(self, raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance scores for different business areas."""
        
        operational_data = raw_metrics.get("operational_data", {})
        customer_data = raw_metrics.get("customer_data", {})
        marketing_data = raw_metrics.get("marketing_data", {})
        revenue_data = raw_metrics.get("revenue_data", {})
        
        # Financial health score (0-100)
        cost_ratio = operational_data.get("cost_ratio", 1.0)
        financial_score = max(0, min(100, (0.20 - cost_ratio) / 0.20 * 100)) if cost_ratio <= 0.20 else 0
        
        # Customer acquisition score (0-100)
        conversion_rate = customer_data.get("conversion_rate", 0)
        customer_score = min(100, conversion_rate / 0.05 * 100)  # 5% is excellent
        
        # Marketing efficiency score (0-100)
        roas = marketing_data.get("return_on_ad_spend", 0)
        marketing_score = min(100, roas / 5.0 * 100)  # 5x ROAS is excellent
        
        # Overall business score
        overall_score = (financial_score * 0.4 + customer_score * 0.3 + marketing_score * 0.3)
        
        return {
            "financial_health_score": round(financial_score, 1),
            "customer_acquisition_score": round(customer_score, 1),
            "marketing_efficiency_score": round(marketing_score, 1),
            "overall_business_score": round(overall_score, 1),
            "score_interpretation": {
                "90-100": "Excellent",
                "70-89": "Good",
                "50-69": "Fair",
                "30-49": "Poor",
                "0-29": "Critical"
            }[
                "90-100" if overall_score >= 90 else
                "70-89" if overall_score >= 70 else
                "50-69" if overall_score >= 50 else
                "30-49" if overall_score >= 30 else
                "0-29"
            ]
        }
    
    def _compare_with_history(self, raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current metrics with historical performance."""
        
        if not self.metrics_history:
            return {"status": "no_history", "message": "No historical data available for comparison"}
        
        # Simple comparison with averages (in real implementation, this would be more sophisticated)
        return {
            "comparison_period": f"Last {len(self.metrics_history)} periods",
            "performance_vs_average": "above_average",  # Simplified
            "best_performing_period": self.metrics_history[-1]["timestamp"] if self.metrics_history else None,
            "improvement_areas": ["cost_efficiency", "conversion_rate"],
            "declining_areas": []
        }
    
    async def _generate_insights(self, processed_metrics: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Generate actionable insights from processed metrics."""
        
        kpi_dashboard = processed_metrics.get("kpi_dashboard", {})
        performance_scores = processed_metrics.get("performance_scores", {})
        trend_analysis = processed_metrics.get("trend_analysis", {})
        
        insights = {
            "key_findings": [],
            "opportunities": [],
            "risks": [],
            "recommendations": []
        }
        
        # Analyze cost ratio
        cost_ratio = kpi_dashboard.get("financial_kpis", {}).get("cost_ratio", 0)
        if cost_ratio > 0.18:
            insights["risks"].append("Cost ratio approaching 20% limit - immediate cost optimization needed")
            insights["recommendations"].append("Review and reduce operational costs, especially marketing spend")
        elif cost_ratio < 0.10:
            insights["opportunities"].append("Low cost ratio provides opportunity for increased marketing investment")
        
        # Analyze customer acquisition
        new_customers = kpi_dashboard.get("customer_kpis", {}).get("new_customers", 0)
        if new_customers == 0:
            insights["risks"].append("No new customers acquired - urgent need for marketing optimization")
            insights["recommendations"].append("Increase marketing budget and optimize conversion funnel")
        elif new_customers > 10:
            insights["key_findings"].append("Strong customer acquisition momentum")
            insights["opportunities"].append("Scale successful acquisition channels")
        
        # Analyze profitability
        net_profit = kpi_dashboard.get("financial_kpis", {}).get("net_profit", 0)
        if net_profit > 0:
            insights["key_findings"].append("Business is profitable - ready for growth investment")
        else:
            insights["risks"].append("Business not yet profitable - focus on revenue optimization")
        
        return insights
    
    async def _check_thresholds(self, processed_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check metrics against defined thresholds and generate alerts."""
        
        alerts = []
        kpi_dashboard = processed_metrics.get("kpi_dashboard", {})
        
        # Check cost ratio threshold
        cost_ratio = kpi_dashboard.get("financial_kpis", {}).get("cost_ratio", 0)
        cost_thresholds = self.kpi_thresholds["cost_ratio"]
        
        if cost_ratio >= cost_thresholds["critical"]:
            alerts.append({
                "type": "critical",
                "metric": "cost_ratio",
                "current_value": cost_ratio,
                "threshold": cost_thresholds["critical"],
                "message": "Cost ratio critically high - immediate action required",
                "recommended_action": "Pause non-essential spending and optimize costs"
            })
        elif cost_ratio >= cost_thresholds["warning"]:
            alerts.append({
                "type": "warning",
                "metric": "cost_ratio",
                "current_value": cost_ratio,
                "threshold": cost_thresholds["warning"],
                "message": "Cost ratio approaching limit",
                "recommended_action": "Review and optimize operational costs"
            })
        
        # Check customer acquisition cost
        cac = kpi_dashboard.get("customer_kpis", {}).get("cac", 0)
        cac_thresholds = self.kpi_thresholds["customer_acquisition_cost"]
        
        if cac >= cac_thresholds["critical"]:
            alerts.append({
                "type": "critical",
                "metric": "customer_acquisition_cost",
                "current_value": cac,
                "threshold": cac_thresholds["critical"],
                "message": "Customer acquisition cost too high",
                "recommended_action": "Optimize marketing campaigns and improve conversion rates"
            })
        
        # Check conversion rate
        conversion_rate = kpi_dashboard.get("customer_kpis", {}).get("conversion_rate", 0)
        conversion_thresholds = self.kpi_thresholds["conversion_rate"]
        
        if conversion_rate < conversion_thresholds["min"]:
            alerts.append({
                "type": "warning",
                "metric": "conversion_rate",
                "current_value": conversion_rate,
                "threshold": conversion_thresholds["min"],
                "message": "Conversion rate below minimum threshold",
                "recommended_action": "Optimize landing pages and user experience"
            })
        
        return alerts
    
    async def _generate_predictions(self, processed_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate predictions based on current trends."""
        
        kpi_dashboard = processed_metrics.get("kpi_dashboard", {})
        trend_analysis = processed_metrics.get("trend_analysis", {})
        
        # Simple linear projections (in real implementation, this would use more sophisticated models)
        current_revenue = kpi_dashboard.get("financial_kpis", {}).get("total_revenue", 0)
        revenue_growth = trend_analysis.get("revenue_trend", {}).get("change_percentage", 0) / 100
        
        predictions = {
            "next_month_revenue": current_revenue * (1 + revenue_growth),
            "time_to_profitability": "already_profitable" if kpi_dashboard.get("financial_kpis", {}).get("net_profit", 0) > 0 else "2-3_months",
            "customer_growth_projection": {
                "next_month": kpi_dashboard.get("customer_kpis", {}).get("total_customers", 0) + 
                             max(1, trend_analysis.get("customer_trend", {}).get("change_count", 0)),
                "confidence": "medium"
            },
            "cost_ratio_projection": {
                "next_month": min(0.25, kpi_dashboard.get("financial_kpis", {}).get("cost_ratio", 0) * 1.05),
                "trend": "stable"
            }
        }
        
        return predictions
    
    def _assess_data_quality(self, raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality and completeness of collected data."""
        
        total_sources = len(raw_metrics)
        complete_sources = sum(1 for source_data in raw_metrics.values() if source_data and len(source_data) > 3)
        
        return {
            "overall_quality": "high" if complete_sources / total_sources > 0.8 else "medium" if complete_sources / total_sources > 0.5 else "low",
            "completeness_percentage": (complete_sources / total_sources * 100) if total_sources > 0 else 0,
            "missing_sources": [k for k, v in raw_metrics.items() if not v or len(v) <= 3],
            "data_freshness": "real_time",
            "reliability_score": 0.9
        }
    
    def _calculate_next_analysis_time(self) -> str:
        """Calculate when the next analysis should be performed."""
        from datetime import datetime, timedelta
        
        # Daily analysis for active businesses
        next_time = datetime.now() + timedelta(days=1)
        return next_time.isoformat()
    
    def _generate_next_steps(self, insights: Dict[str, Any], alerts: List[Dict[str, Any]]) -> List[str]:
        """Generate recommended next steps based on insights and alerts."""
        
        next_steps = []
        
        # Add steps based on critical alerts
        critical_alerts = [a for a in alerts if a.get("type") == "critical"]
        for alert in critical_alerts:
            next_steps.append(alert.get("recommended_action", "Address critical alert"))
        
        # Add steps based on recommendations
        recommendations = insights.get("recommendations", [])
        next_steps.extend(recommendations[:3])  # Top 3 recommendations
        
        # Default steps if none generated
        if not next_steps:
            next_steps = [
                "Continue monitoring key metrics daily",
                "Review marketing campaign performance",
                "Optimize cost efficiency where possible"
            ]
        
        return next_steps[:5]  # Limit to 5 steps
    
    def _estimate_analytics_cost(self, num_tools: int, analysis_type: str) -> float:
        """Estimate the cost of analytics operations."""
        
        base_cost = 2.0  # Base cost for analysis
        tool_cost = num_tools * 0.5  # Cost per tool used
        
        type_multiplier = {
            "comprehensive": 1.5,
            "financial": 1.0,
            "marketing": 1.2,
            "product": 1.1
        }.get(analysis_type, 1.0)
        
        return base_cost + tool_cost * type_multiplier 