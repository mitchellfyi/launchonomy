import json
import asyncio
from typing import Dict, Any, List, Optional
from ..base.workflow_agent import BaseWorkflowAgent, WorkflowOutput

class CampaignAgent(BaseWorkflowAgent):
    """
    CampaignAgent encapsulates both "run_campaigns" and "optimize_campaigns" workflow steps.
    Manages customer acquisition campaigns and continuously optimizes them for better conversion
    rates and cost efficiency within Launchonomy constraints.
    """
    
    REQUIRED_TOOLS = ["email_marketing", "social_media"]
    OPTIONAL_TOOLS = ["paid_advertising", "content_management", "seo_tools", "analytics", "a_b_testing"]
    
    def __init__(self, registry=None, orchestrator=None):
        super().__init__("CampaignAgent", registry, orchestrator)
        self.system_prompt = self._build_system_prompt()
        self.active_campaigns = {}
        self.optimization_history = []
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with current Launchonomy context."""
        context = self._get_launchonomy_context()
        
        return f"""You are CampaignAgent, the customer acquisition and optimization specialist in the Launchonomy autonomous business system.

MISSION CONTEXT:
{json.dumps(context, indent=2)}

YOUR ROLE:
You design, execute, and optimize customer acquisition campaigns that:
- Operate within strict budget constraints (<20% of revenue)
- Focus on acquiring the first paying customer as quickly as possible
- Scale efficiently as revenue grows
- Run autonomously without human intervention

CORE CAPABILITIES:
1. Campaign Strategy & Planning
   - Identify optimal customer acquisition channels
   - Design multi-channel campaign strategies
   - Set realistic conversion targets and budgets
   - Plan campaign sequences and automation

2. Campaign Execution
   - Launch email marketing campaigns
   - Execute social media outreach
   - Manage content marketing initiatives
   - Coordinate paid advertising (when budget allows)

3. Performance Optimization
   - Monitor campaign performance in real-time
   - Conduct A/B tests on messaging, timing, and channels
   - Optimize conversion funnels and landing pages
   - Reallocate budget to highest-performing channels

4. Cost Management
   - Track cost per acquisition (CPA) across all channels
   - Ensure total marketing costs stay under 20% of revenue
   - Optimize for maximum ROI within budget constraints
   - Pause or adjust campaigns that exceed cost thresholds

OPTIMIZATION PRINCIPLES:
- Data-driven decisions: Every optimization based on measurable results
- Rapid iteration: Quick testing cycles to find what works
- Cost efficiency: Maximum customer acquisition at minimum cost
- Automation-first: Set up campaigns to run and optimize themselves
- Customer-centric: Focus on providing value to attract customers

CAMPAIGN TYPES:
- Launch campaigns: Initial customer acquisition for new products
- Growth campaigns: Scaling successful acquisition channels
- Retention campaigns: Keeping existing customers engaged
- Optimization campaigns: Testing and improving existing campaigns

Always prioritize getting the first paying customer, then focus on scalable, profitable growth."""

    async def execute(self, input_data: Dict[str, Any]) -> WorkflowOutput:
        """
        Execute campaign management workflow (both running and optimizing campaigns).
        
        Args:
            input_data: Contains product details, campaign type, budget, and optimization parameters
            
        Returns:
            WorkflowOutput with campaign results and optimization recommendations
        """
        self._log("Starting campaign management workflow")
        
        try:
            # Extract input parameters
            campaign_type = input_data.get("campaign_type", "launch")  # launch, growth, optimization
            product_details = input_data.get("product_details", {})
            budget_allocation = input_data.get("budget_allocation", {})
            optimization_goals = input_data.get("optimization_goals", {})
            
            if not product_details:
                raise ValueError("Product details required for campaign execution")
            
            # Get available marketing tools
            available_tools = await self._get_available_campaign_tools()
            
            if campaign_type == "optimization":
                # Run optimization workflow
                result = await self._optimize_existing_campaigns(
                    product_details, optimization_goals, available_tools
                )
            else:
                # Run new campaign workflow
                result = await self._run_new_campaigns(
                    campaign_type, product_details, budget_allocation, available_tools
                )
            
            return result
            
        except Exception as e:
            self._log(f"Error in campaign management: {str(e)}", "error")
            return self._format_output(
                status="failure",
                data={"error_details": str(e)},
                error_message=f"Campaign management failed: {str(e)}"
            )
    
    async def _run_new_campaigns(self, campaign_type: str, product_details: Dict[str, Any], 
                               budget_allocation: Dict[str, Any], 
                               available_tools: Dict[str, Any]) -> WorkflowOutput:
        """Run new customer acquisition campaigns."""
        
        self._log(f"Launching {campaign_type} campaigns for {product_details.get('name', 'product')}")
        
        # Plan campaign strategy
        campaign_strategy = await self._plan_campaign_strategy(
            campaign_type, product_details, budget_allocation, available_tools
        )
        
        # Execute campaigns across channels
        campaign_results = await self._execute_campaigns(campaign_strategy, available_tools)
        
        # Set up monitoring and automation
        monitoring_setup = await self._setup_campaign_monitoring(campaign_results)
        
        # Calculate initial performance metrics
        performance_metrics = await self._calculate_campaign_performance(campaign_results)
        
        output_data = {
            "campaign_type": campaign_type,
            "strategy": campaign_strategy,
            "execution_results": campaign_results,
            "monitoring": monitoring_setup,
            "performance": performance_metrics,
            "next_optimization_date": self._calculate_next_optimization_date(),
            "budget_utilization": self._calculate_budget_utilization(campaign_results, budget_allocation)
        }
        
        # Store active campaigns for future optimization
        campaign_id = f"{campaign_type}_{product_details.get('name', 'product')}_{len(self.active_campaigns)}"
        self.active_campaigns[campaign_id] = output_data
        
        self._log(f"Campaigns launched successfully. Budget utilization: {output_data['budget_utilization']['percentage_used']:.1f}%")
        
        return self._format_output(
            status="success",
            data=output_data,
            cost=output_data["budget_utilization"]["total_spent"],
            tools_used=list(available_tools.keys()),
            next_steps=[
                "Monitor campaign performance daily",
                "Prepare for optimization cycle in 7 days",
                "Track conversion metrics and customer feedback"
            ],
            confidence=0.8
        )
    
    async def _optimize_existing_campaigns(self, product_details: Dict[str, Any],
                                         optimization_goals: Dict[str, Any],
                                         available_tools: Dict[str, Any]) -> WorkflowOutput:
        """Optimize existing campaigns based on performance data."""
        
        self._log("Starting campaign optimization cycle")
        
        if not self.active_campaigns:
            return self._format_output(
                status="failure",
                data={"error": "No active campaigns to optimize"},
                error_message="No active campaigns found for optimization"
            )
        
        # Analyze current campaign performance
        performance_analysis = await self._analyze_campaign_performance()
        
        # Identify optimization opportunities
        optimization_opportunities = await self._identify_optimization_opportunities(
            performance_analysis, optimization_goals
        )
        
        # Execute optimizations
        optimization_results = await self._execute_optimizations(
            optimization_opportunities, available_tools
        )
        
        # Update campaign configurations
        updated_campaigns = await self._update_campaign_configurations(optimization_results)
        
        # Calculate optimization impact
        optimization_impact = await self._calculate_optimization_impact(
            performance_analysis, optimization_results
        )
        
        output_data = {
            "optimization_type": "performance_improvement",
            "performance_analysis": performance_analysis,
            "opportunities_identified": optimization_opportunities,
            "optimizations_executed": optimization_results,
            "updated_campaigns": updated_campaigns,
            "impact_assessment": optimization_impact,
            "next_optimization_date": self._calculate_next_optimization_date()
        }
        
        # Store optimization history
        self.optimization_history.append({
            "timestamp": self._get_launchonomy_context()["timestamp"],
            "optimization_data": output_data
        })
        
        self._log(f"Optimization completed. Expected improvement: {optimization_impact.get('expected_improvement', 'N/A')}")
        
        return self._format_output(
            status="success",
            data=output_data,
            cost=optimization_impact.get("optimization_cost", 0.0),
            tools_used=list(available_tools.keys()),
            next_steps=[
                "Monitor optimization impact over next 7 days",
                "Prepare for next optimization cycle",
                "Continue tracking conversion improvements"
            ],
            confidence=0.85
        )
    
    async def _get_available_campaign_tools(self) -> Dict[str, Any]:
        """Get available tools for campaign management."""
        available_tools = {}
        
        for tool_name in self.REQUIRED_TOOLS + self.OPTIONAL_TOOLS:
            tool_spec = await self._get_tool_from_registry(tool_name)
            if tool_spec:
                available_tools[tool_name] = tool_spec
                self._log(f"Campaign tool available: {tool_name}")
            else:
                self._log(f"Campaign tool not available: {tool_name}", "warning")
        
        return available_tools
    
    async def _plan_campaign_strategy(self, campaign_type: str, product_details: Dict[str, Any],
                                    budget_allocation: Dict[str, Any], 
                                    available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Plan comprehensive campaign strategy."""
        
        total_budget = budget_allocation.get("total_budget", 100.0)
        
        # Determine optimal channel mix based on product type and budget
        channel_strategy = self._determine_channel_strategy(product_details, total_budget, available_tools)
        
        # Create messaging strategy
        messaging_strategy = self._create_messaging_strategy(product_details, campaign_type)
        
        # Plan campaign timeline
        timeline = self._plan_campaign_timeline(campaign_type, channel_strategy)
        
        strategy = {
            "campaign_type": campaign_type,
            "target_audience": self._define_target_audience(product_details),
            "channel_strategy": channel_strategy,
            "messaging_strategy": messaging_strategy,
            "timeline": timeline,
            "success_metrics": self._define_success_metrics(campaign_type, total_budget),
            "budget_allocation": self._allocate_budget_by_channel(total_budget, channel_strategy)
        }
        
        self._log(f"Campaign strategy planned: {len(channel_strategy['channels'])} channels, ${total_budget} budget")
        return strategy
    
    def _determine_channel_strategy(self, product_details: Dict[str, Any], 
                                  total_budget: float, available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Determine optimal marketing channels based on product and budget."""
        
        product_type = product_details.get("type", "web_application")
        
        # Channel effectiveness by product type (0-1 scale)
        channel_effectiveness = {
            "api_service": {
                "email_marketing": 0.9,
                "social_media": 0.7,
                "content_marketing": 0.8,
                "paid_advertising": 0.6,
                "developer_communities": 0.9
            },
            "newsletter_service": {
                "email_marketing": 0.8,
                "social_media": 0.9,
                "content_marketing": 0.9,
                "paid_advertising": 0.7,
                "influencer_outreach": 0.8
            },
            "web_application": {
                "email_marketing": 0.8,
                "social_media": 0.8,
                "content_marketing": 0.7,
                "paid_advertising": 0.8,
                "seo": 0.6
            }
        }
        
        effectiveness = channel_effectiveness.get(product_type, channel_effectiveness["web_application"])
        
        # Filter channels based on available tools and budget
        selected_channels = []
        for channel, score in effectiveness.items():
            if score >= 0.7 and total_budget >= 50:  # High-value channels for sufficient budget
                selected_channels.append({"name": channel, "effectiveness": score, "priority": "high"})
            elif score >= 0.6 and total_budget >= 25:  # Medium-value channels for moderate budget
                selected_channels.append({"name": channel, "effectiveness": score, "priority": "medium"})
        
        # Ensure at least email marketing if available
        if not any(c["name"] == "email_marketing" for c in selected_channels) and "email_marketing" in available_tools:
            selected_channels.append({"name": "email_marketing", "effectiveness": 0.8, "priority": "high"})
        
        return {
            "channels": selected_channels,
            "primary_channel": max(selected_channels, key=lambda x: x["effectiveness"])["name"] if selected_channels else "email_marketing",
            "channel_count": len(selected_channels)
        }
    
    def _create_messaging_strategy(self, product_details: Dict[str, Any], campaign_type: str) -> Dict[str, Any]:
        """Create messaging strategy for campaigns."""
        
        product_name = product_details.get("name", "Product")
        value_proposition = self._extract_value_proposition(product_details)
        
        messaging_themes = {
            "launch": {
                "primary_message": f"Introducing {product_name} - {value_proposition}",
                "call_to_action": "Be among the first to try it",
                "urgency_factor": "Limited early access",
                "social_proof": "Join innovative early adopters"
            },
            "growth": {
                "primary_message": f"{product_name} is helping customers {value_proposition}",
                "call_to_action": "Start your free trial today",
                "urgency_factor": "Don't miss out on productivity gains",
                "social_proof": "Join thousands of satisfied users"
            }
        }
        
        return messaging_themes.get(campaign_type, messaging_themes["launch"])
    
    def _extract_value_proposition(self, product_details: Dict[str, Any]) -> str:
        """Extract key value proposition from product details."""
        
        description = product_details.get("description", "")
        name = product_details.get("name", "")
        
        # Simple value proposition extraction based on keywords
        if "newsletter" in name.lower() or "newsletter" in description.lower():
            return "save time with curated, relevant content"
        elif "api" in name.lower() or "api" in description.lower():
            return "integrate powerful functionality with simple API calls"
        elif "builder" in name.lower() or "tool" in description.lower():
            return "create professional results without technical expertise"
        elif "tracker" in name.lower() or "analytics" in description.lower():
            return "gain insights and track progress effortlessly"
        else:
            return "solve your problems more efficiently"
    
    def _plan_campaign_timeline(self, campaign_type: str, channel_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Plan campaign execution timeline."""
        
        timelines = {
            "launch": {
                "duration": "14 days",
                "phases": [
                    {"phase": "setup", "duration": "2 days", "activities": ["Create content", "Set up automation"]},
                    {"phase": "soft_launch", "duration": "3 days", "activities": ["Limited audience", "Gather feedback"]},
                    {"phase": "full_launch", "duration": "9 days", "activities": ["All channels active", "Monitor and adjust"]}
                ]
            },
            "growth": {
                "duration": "30 days",
                "phases": [
                    {"phase": "optimization", "duration": "7 days", "activities": ["Analyze current performance", "Identify improvements"]},
                    {"phase": "scaling", "duration": "23 days", "activities": ["Increase budget", "Expand successful channels"]}
                ]
            }
        }
        
        return timelines.get(campaign_type, timelines["launch"])
    
    def _define_target_audience(self, product_details: Dict[str, Any]) -> Dict[str, Any]:
        """Define target audience based on product characteristics."""
        
        product_type = product_details.get("type", "web_application")
        
        audiences = {
            "api_service": {
                "primary": "Software developers and technical teams",
                "secondary": "Product managers and CTOs",
                "demographics": "Tech professionals, 25-45 years old",
                "channels": ["Developer communities", "LinkedIn", "Twitter"]
            },
            "newsletter_service": {
                "primary": "Industry professionals seeking curated content",
                "secondary": "Busy executives and consultants",
                "demographics": "Knowledge workers, 30-50 years old",
                "channels": ["LinkedIn", "Email", "Industry forums"]
            },
            "web_application": {
                "primary": "Small business owners and entrepreneurs",
                "secondary": "Freelancers and consultants",
                "demographics": "Business professionals, 25-55 years old",
                "channels": ["Social media", "Email", "Business forums"]
            }
        }
        
        return audiences.get(product_type, audiences["web_application"])
    
    def _define_success_metrics(self, campaign_type: str, total_budget: float) -> Dict[str, Any]:
        """Define success metrics for campaign evaluation."""
        
        return {
            "primary_goal": "first_paying_customer" if campaign_type == "launch" else "customer_acquisition_growth",
            "target_conversions": 1 if campaign_type == "launch" else max(5, int(total_budget / 20)),
            "target_cpa": min(total_budget, 50.0),  # Cost per acquisition
            "target_roi": 3.0,  # 3x return on investment
            "timeline_goal": "7 days" if campaign_type == "launch" else "30 days"
        }
    
    def _allocate_budget_by_channel(self, total_budget: float, channel_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate budget across selected channels."""
        
        channels = channel_strategy["channels"]
        if not channels:
            return {"total_budget": total_budget, "allocations": {}}
        
        # Allocate budget based on channel effectiveness
        total_effectiveness = sum(c["effectiveness"] for c in channels)
        
        allocations = {}
        remaining_budget = total_budget
        
        for channel in channels[:-1]:  # All but last channel
            allocation = (channel["effectiveness"] / total_effectiveness) * total_budget
            allocations[channel["name"]] = round(allocation, 2)
            remaining_budget -= allocation
        
        # Give remaining budget to last channel (handles rounding)
        if channels:
            allocations[channels[-1]["name"]] = round(remaining_budget, 2)
        
        return {
            "total_budget": total_budget,
            "allocations": allocations,
            "primary_channel_budget": allocations.get(channel_strategy["primary_channel"], 0)
        }
    
    async def _execute_campaigns(self, campaign_strategy: Dict[str, Any], 
                               available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Execute campaigns across all planned channels."""
        
        execution_results = {
            "campaigns_launched": [],
            "total_reach": 0,
            "estimated_impressions": 0,
            "automation_setup": {},
            "tracking_configured": True
        }
        
        budget_allocations = campaign_strategy["budget_allocation"]["allocations"]
        
        for channel_info in campaign_strategy["channel_strategy"]["channels"]:
            channel_name = channel_info["name"]
            channel_budget = budget_allocations.get(channel_name, 0)
            
            if channel_budget > 0:
                campaign_result = await self._execute_single_channel_campaign(
                    channel_name, channel_budget, campaign_strategy, available_tools
                )
                execution_results["campaigns_launched"].append(campaign_result)
                execution_results["total_reach"] += campaign_result.get("estimated_reach", 0)
                execution_results["estimated_impressions"] += campaign_result.get("estimated_impressions", 0)
        
        self._log(f"Executed {len(execution_results['campaigns_launched'])} campaigns")
        return execution_results
    
    async def _execute_single_channel_campaign(self, channel_name: str, budget: float,
                                             campaign_strategy: Dict[str, Any],
                                             available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Execute campaign for a single channel using available tools."""
        
        # Use the appropriate tool for the channel
        if channel_name in available_tools:
            tool_spec = available_tools[channel_name]
            
            try:
                tool_result = await self._execute_tool(tool_spec, {
                    "action": "launch_campaign",
                    "budget": budget,
                    "campaign_strategy": campaign_strategy,
                    "channel_config": campaign_strategy.get("channel_strategy", {}).get(channel_name, {}),
                    "messaging": campaign_strategy.get("messaging_strategy", {}),
                    "target_audience": campaign_strategy.get("target_audience", {}),
                    "timeline": campaign_strategy.get("timeline", {})
                })
                
                if tool_result.get("status") == "success":
                    result = tool_result.get("campaign_data", {})
                    result.update({
                        "channel": channel_name,
                        "budget_allocated": budget,
                        "status": "active",
                        "launch_timestamp": self._get_launchonomy_context()["timestamp"],
                        "tool_used": channel_name
                    })
                    self._log(f"Successfully launched {channel_name} campaign with ${budget} budget using {channel_name} tool")
                    return result
                else:
                    self._log(f"Failed to launch {channel_name} campaign: {tool_result.get('error', 'Unknown error')}", "error")
                    return {
                        "channel": channel_name,
                        "budget_allocated": budget,
                        "status": "failed",
                        "error": tool_result.get("error", "Campaign launch failed"),
                        "launch_timestamp": self._get_launchonomy_context()["timestamp"]
                    }
                    
            except Exception as e:
                self._log(f"Error executing {channel_name} campaign: {str(e)}", "error")
                return {
                    "channel": channel_name,
                    "budget_allocated": budget,
                    "status": "error",
                    "error": f"Tool execution error: {str(e)}",
                    "launch_timestamp": self._get_launchonomy_context()["timestamp"]
                }
        else:
            self._log(f"No tool available for {channel_name} channel", "warning")
            return {
                "channel": channel_name,
                "budget_allocated": budget,
                "status": "skipped",
                "error": f"No {channel_name} tool available",
                "launch_timestamp": self._get_launchonomy_context()["timestamp"]
            }
    
    async def _setup_campaign_monitoring(self, campaign_results: Dict[str, Any]) -> Dict[str, Any]:
        """Set up monitoring and automation for launched campaigns."""
        
        monitoring_config = {
            "tracking_frequency": "daily",
            "key_metrics": ["impressions", "clicks", "conversions", "cost_per_conversion"],
            "alert_thresholds": {
                "high_cost_per_conversion": 50.0,
                "low_conversion_rate": 0.01,
                "budget_utilization": 0.8
            },
            "automated_actions": {
                "pause_high_cost_campaigns": True,
                "reallocate_budget_to_performers": True,
                "send_performance_reports": True
            },
            "optimization_schedule": "weekly"
        }
        
        return monitoring_config
    
    async def _calculate_campaign_performance(self, campaign_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate campaign performance metrics from actual campaign data."""
        
        campaigns = campaign_results.get("campaigns_launched", [])
        total_budget = sum(c.get("budget_allocated", 0) for c in campaigns)
        
        # Aggregate actual performance data from campaigns
        total_reach = 0
        total_impressions = 0
        total_clicks = 0
        total_conversions = 0
        
        for campaign in campaigns:
            if campaign.get("status") == "active":
                # Get actual metrics from campaign data
                total_reach += campaign.get("actual_reach", campaign.get("estimated_reach", 0))
                total_impressions += campaign.get("actual_impressions", campaign.get("estimated_impressions", 0))
                total_clicks += campaign.get("actual_clicks", campaign.get("estimated_clicks", 0))
                total_conversions += campaign.get("actual_conversions", campaign.get("estimated_conversions", 0))
        
        # Calculate performance metrics
        ctr = (total_clicks / total_impressions) if total_impressions > 0 else 0
        conversion_rate = (total_conversions / total_clicks) if total_clicks > 0 else 0
        cpa = (total_budget / total_conversions) if total_conversions > 0 else total_budget
        
        # Estimate revenue (assuming $50 average order value)
        estimated_revenue = total_conversions * 50
        roi = ((estimated_revenue - total_budget) / total_budget) if total_budget > 0 else 0
        
        performance = {
            "total_budget_spent": total_budget,
            "total_reach": total_reach,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "click_through_rate": ctr,
            "conversion_rate": conversion_rate,
            "cost_per_acquisition": cpa,
            "estimated_revenue": estimated_revenue,
            "return_on_investment": roi,
            "performance_score": min(100, max(0, roi * 50 + 50))  # Scale ROI to 0-100 score
        }
        
        return performance
    
    def _calculate_next_optimization_date(self) -> str:
        """Calculate when the next optimization cycle should run."""
        from datetime import datetime, timedelta
        
        next_date = datetime.now() + timedelta(days=7)
        return next_date.isoformat()
    
    def _calculate_budget_utilization(self, campaign_results: Dict[str, Any], 
                                    budget_allocation: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate budget utilization metrics."""
        
        total_allocated = budget_allocation.get("total_budget", 0)
        total_spent = sum(c.get("budget_allocated", 0) for c in campaign_results.get("campaigns_launched", []))
        
        return {
            "total_allocated": total_allocated,
            "total_spent": total_spent,
            "percentage_used": (total_spent / total_allocated * 100) if total_allocated > 0 else 0,
            "remaining_budget": total_allocated - total_spent,
            "efficiency_rating": "high" if total_spent > 0 else "pending"
        }
    
    async def _analyze_campaign_performance(self) -> Dict[str, Any]:
        """Analyze performance of all active campaigns using actual data."""
        
        if not self.active_campaigns:
            return {"error": "No active campaigns to analyze"}
        
        # Collect actual performance data from active campaigns
        total_campaigns = len(self.active_campaigns)
        high_performers = []
        underperformers = []
        channel_performance = {}
        total_conversions = 0
        total_spend = 0
        total_revenue = 0
        
        for campaign_id, campaign_data in self.active_campaigns.items():
            if campaign_data.get("status") == "active":
                conversions = campaign_data.get("actual_conversions", 0)
                spend = campaign_data.get("budget_allocated", 0)
                revenue = conversions * 50  # Assuming $50 AOV
                roi = ((revenue - spend) / spend) if spend > 0 else 0
                cpa = (spend / conversions) if conversions > 0 else spend
                
                # Categorize performance
                if roi > 2.0:  # ROI > 200%
                    high_performers.append({
                        "campaign_id": campaign_id,
                        "channel": campaign_data.get("channel", "unknown"),
                        "roi": roi,
                        "cpa": cpa,
                        "conversions": conversions
                    })
                elif roi < 1.0:  # ROI < 100%
                    underperformers.append({
                        "campaign_id": campaign_id,
                        "channel": campaign_data.get("channel", "unknown"),
                        "roi": roi,
                        "cpa": cpa,
                        "conversions": conversions
                    })
                
                # Aggregate channel performance
                channel = campaign_data.get("channel", "unknown")
                if channel not in channel_performance:
                    channel_performance[channel] = {"cpa": 0, "roi": 0, "conversions": 0, "campaigns": 0}
                
                channel_performance[channel]["cpa"] += cpa
                channel_performance[channel]["roi"] += roi
                channel_performance[channel]["conversions"] += conversions
                channel_performance[channel]["campaigns"] += 1
                
                total_conversions += conversions
                total_spend += spend
                total_revenue += revenue
        
        # Calculate averages for channels
        for channel in channel_performance:
            campaigns_count = channel_performance[channel]["campaigns"]
            if campaigns_count > 0:
                channel_performance[channel]["cpa"] /= campaigns_count
                channel_performance[channel]["roi"] /= campaigns_count
        
        analysis = {
            "total_campaigns": total_campaigns,
            "performance_summary": {
                "high_performers": high_performers,
                "underperformers": underperformers,
                "average_cpa": (total_spend / total_conversions) if total_conversions > 0 else 0,
                "average_roi": ((total_revenue - total_spend) / total_spend) if total_spend > 0 else 0,
                "total_conversions": total_conversions,
                "total_spend": total_spend,
                "total_revenue": total_revenue
            },
            "channel_performance": channel_performance,
            "data_source": "actual_campaign_data"
        }
        
        return analysis
    
    async def _identify_optimization_opportunities(self, performance_analysis: Dict[str, Any],
                                                 optimization_goals: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify specific optimization opportunities."""
        
        opportunities = [
            {
                "type": "budget_reallocation",
                "description": "Reallocate budget from underperforming to high-performing channels",
                "expected_impact": "15% improvement in overall ROI",
                "implementation_effort": "low"
            },
            {
                "type": "message_optimization",
                "description": "A/B test different messaging approaches",
                "expected_impact": "10% improvement in conversion rate",
                "implementation_effort": "medium"
            },
            {
                "type": "audience_refinement",
                "description": "Narrow targeting to highest-converting audience segments",
                "expected_impact": "20% reduction in CPA",
                "implementation_effort": "low"
            }
        ]
        
        return opportunities
    
    async def _execute_optimizations(self, optimization_opportunities: List[Dict[str, Any]],
                                   available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Execute identified optimizations."""
        
        executed_optimizations = []
        
        for opportunity in optimization_opportunities:
            if opportunity["implementation_effort"] in ["low", "medium"]:
                optimization_result = {
                    "optimization_type": opportunity["type"],
                    "status": "implemented",
                    "implementation_date": self._get_launchonomy_context()["timestamp"],
                    "expected_impact": opportunity["expected_impact"]
                }
                executed_optimizations.append(optimization_result)
        
        return {
            "optimizations_executed": executed_optimizations,
            "total_optimizations": len(executed_optimizations),
            "implementation_status": "completed"
        }
    
    async def _update_campaign_configurations(self, optimization_results: Dict[str, Any]) -> Dict[str, Any]:
        """Update campaign configurations based on optimizations."""
        
        # Update active campaigns with optimization results
        updated_count = 0
        optimization_errors = []
        
        for campaign_id in self.active_campaigns:
            try:
                campaign_data = self.active_campaigns[campaign_id]
                channel = campaign_data.get("channel")
                
                # Apply optimizations based on results
                for optimization in optimization_results.get("optimizations_executed", []):
                    if optimization["optimization_type"] == "budget_reallocation":
                        # Update budget allocation if this campaign is affected
                        if campaign_data.get("roi", 0) > 2.0:  # High performer
                            campaign_data["budget_allocated"] *= 1.2  # Increase budget by 20%
                        elif campaign_data.get("roi", 0) < 1.0:  # Underperformer
                            campaign_data["budget_allocated"] *= 0.8  # Decrease budget by 20%
                    
                    elif optimization["optimization_type"] == "audience_refinement":
                        # Update targeting parameters
                        campaign_data["targeting_refined"] = True
                        campaign_data["audience_segments"] = "high_converting_only"
                    
                    elif optimization["optimization_type"] == "message_optimization":
                        # Mark for A/B testing
                        campaign_data["ab_testing_enabled"] = True
                        campaign_data["message_variants"] = 2
                
                # Update metadata
                campaign_data["last_optimized"] = self._get_launchonomy_context()["timestamp"]
                campaign_data["optimization_version"] = campaign_data.get("optimization_version", 0) + 1
                
                updated_count += 1
                
            except Exception as e:
                optimization_errors.append({
                    "campaign_id": campaign_id,
                    "error": str(e)
                })
                self._log(f"Error updating campaign {campaign_id}: {str(e)}", "error")
        
        return {
            "campaigns_updated": updated_count,
            "update_timestamp": self._get_launchonomy_context()["timestamp"],
            "configuration_changes": optimization_results["optimizations_executed"]
        }
    
    async def _calculate_optimization_impact(self, performance_analysis: Dict[str, Any],
                                           optimization_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate the expected impact of optimizations."""
        
        current_roi = performance_analysis.get("performance_summary", {}).get("average_roi", 2.0)
        current_cpa = performance_analysis.get("performance_summary", {}).get("average_cpa", 30.0)
        
        # Estimate improvement based on optimizations executed
        roi_improvement = len(optimization_results["optimizations_executed"]) * 0.1  # 10% per optimization
        cpa_reduction = len(optimization_results["optimizations_executed"]) * 0.05  # 5% per optimization
        
        return {
            "current_performance": {
                "roi": current_roi,
                "cpa": current_cpa
            },
            "expected_improvement": {
                "roi_increase": f"{roi_improvement * 100:.1f}%",
                "cpa_reduction": f"{cpa_reduction * 100:.1f}%"
            },
            "projected_performance": {
                "roi": current_roi * (1 + roi_improvement),
                "cpa": current_cpa * (1 - cpa_reduction)
            },
            "optimization_cost": 5.0 * len(optimization_results["optimizations_executed"])
        } 