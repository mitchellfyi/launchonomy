import json
import asyncio
from typing import Dict, Any, List, Optional
from ..base.workflow_agent import BaseWorkflowAgent, WorkflowOutput

class ScanAgent(BaseWorkflowAgent):
    """
    ScanAgent encapsulates the "scan_opportunities" workflow step.
    Identifies, researches, and ranks potential business opportunities based on market demand,
    competition analysis, and alignment with Launchonomy constraints.
    """
    
    REQUIRED_TOOLS = ["market_research", "competitor_analysis"]
    OPTIONAL_TOOLS = ["trend_analysis", "keyword_research", "social_media_monitoring"]
    
    def __init__(self, registry=None, orchestrator=None):
        super().__init__("ScanAgent", registry, orchestrator)
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with current Launchonomy context."""
        context = self._get_launchonomy_context()
        
        return f"""You are ScanAgent, the opportunity scanning specialist in the Launchonomy autonomous business system.

MISSION CONTEXT:
{json.dumps(context, indent=2)}

YOUR ROLE:
You identify, research, and rank potential business opportunities that align with Launchonomy's constraints:
- Can be launched with $500 initial budget
- Can achieve first paying customer quickly (ideally within 30 days)
- Has clear path to profitability with <20% cost ratio
- Suitable for autonomous operation without human intervention

CORE CAPABILITIES:
1. Market Opportunity Identification
   - Scan trending topics, pain points, and emerging needs
   - Identify underserved niches with high demand/low competition
   - Evaluate market size and accessibility

2. Competitive Analysis
   - Research existing solutions and their weaknesses
   - Identify market gaps and differentiation opportunities
   - Assess competitive barriers and entry points

3. Feasibility Assessment
   - Evaluate technical complexity and resource requirements
   - Assess time-to-market and customer acquisition potential
   - Calculate estimated costs and revenue projections

4. Opportunity Ranking
   - Score opportunities based on multiple criteria
   - Prioritize based on speed-to-first-customer potential
   - Consider automation-friendliness and scalability

DECISION FRAMEWORK:
- Speed: How quickly can we get first paying customer?
- Budget: Can we launch within $500 constraint?
- Automation: Can this run autonomously without human intervention?
- Profitability: Clear path to <20% cost ratio?
- Market: Sufficient demand with accessible customers?

Always provide data-driven recommendations with clear reasoning and risk assessment."""

    async def execute(self, input_data: Dict[str, Any]) -> WorkflowOutput:
        """
        Execute opportunity scanning workflow.
        
        Args:
            input_data: Contains mission context, focus areas, and scanning parameters
            
        Returns:
            WorkflowOutput with ranked opportunities and analysis
        """
        self._log("Starting opportunity scanning workflow")
        
        try:
            # Extract input parameters
            mission_context = input_data.get("mission_context", {})
            focus_areas = input_data.get("focus_areas", [])
            max_opportunities = input_data.get("max_opportunities", 5)
            
            # Get available tools for market research
            available_tools = await self._get_available_scanning_tools()
            
            # Execute scanning process
            opportunities = await self._scan_opportunities(
                mission_context, focus_areas, max_opportunities, available_tools
            )
            
            # Rank and filter opportunities
            ranked_opportunities = await self._rank_opportunities(opportunities)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(ranked_opportunities)
            
            output_data = {
                "opportunities": ranked_opportunities,
                "recommendations": recommendations,
                "scan_metadata": {
                    "total_opportunities_found": len(opportunities),
                    "focus_areas_scanned": focus_areas,
                    "tools_used": list(available_tools.keys()),
                    "scan_timestamp": self._get_launchonomy_context()["timestamp"]
                }
            }
            
            self._log(f"Scan completed: {len(ranked_opportunities)} opportunities identified")
            
            return self._format_output(
                status="success",
                data=output_data,
                cost=self._estimate_scanning_cost(len(opportunities)),
                tools_used=list(available_tools.keys()),
                next_steps=[
                    "Review top-ranked opportunities",
                    "Select opportunity for MVP deployment",
                    "Initiate consensus voting on selected opportunity"
                ],
                confidence=0.85
            )
            
        except Exception as e:
            self._log(f"Error in opportunity scanning: {str(e)}", "error")
            return self._format_output(
                status="failure",
                data={"error_details": str(e)},
                error_message=f"Opportunity scanning failed: {str(e)}"
            )
    
    async def _get_available_scanning_tools(self) -> Dict[str, Any]:
        """Get available tools for market research and scanning."""
        available_tools = {}
        
        for tool_name in self.REQUIRED_TOOLS + self.OPTIONAL_TOOLS:
            tool_spec = await self._get_tool_from_registry(tool_name)
            if tool_spec:
                available_tools[tool_name] = tool_spec
                self._log(f"Tool available: {tool_name}")
            else:
                self._log(f"Tool not available: {tool_name}", "warning")
        
        return available_tools
    
    async def _scan_opportunities(self, mission_context: Dict[str, Any], 
                                focus_areas: List[str], max_opportunities: int,
                                available_tools: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scan for business opportunities using available tools."""
        opportunities = []
        
        # Use market research tools to find real opportunities
        if "market_research" in available_tools:
            market_data = await self._scan_with_market_research(
                mission_context, focus_areas, max_opportunities, available_tools["market_research"]
            )
            opportunities.extend(market_data)
        
        # Use trend analysis tools
        if "trend_analysis" in available_tools:
            trend_data = await self._scan_with_trend_analysis(
                mission_context, focus_areas, available_tools["trend_analysis"]
            )
            opportunities.extend(trend_data)
        
        # Use competitor analysis tools
        if "competitor_analysis" in available_tools:
            competitor_data = await self._scan_with_competitor_analysis(
                mission_context, focus_areas, available_tools["competitor_analysis"]
            )
            opportunities.extend(competitor_data)
        
        # Use keyword research tools
        if "keyword_research" in available_tools:
            keyword_data = await self._scan_with_keyword_research(
                mission_context, focus_areas, available_tools["keyword_research"]
            )
            opportunities.extend(keyword_data)
        
        # If no tools available, return empty list with error
        if not opportunities and not available_tools:
            self._log("No market scanning tools available - cannot identify opportunities", "error")
            return [{
                "name": "No Opportunities Found",
                "description": "No market scanning tools available",
                "error": "No scanning tools available",
                "market_size": "Unknown",
                "competition_level": "Unknown",
                "estimated_launch_cost": 0,
                "time_to_first_customer": "Unknown",
                "revenue_model": "Unknown",
                "automation_potential": "Unknown"
            }]
        
        # Remove duplicates and limit to max_opportunities
        unique_opportunities = []
        seen_names = set()
        for opp in opportunities:
            if opp["name"] not in seen_names:
                unique_opportunities.append(opp)
                seen_names.add(opp["name"])
                if len(unique_opportunities) >= max_opportunities:
                    break
        
        return unique_opportunities
    
    async def _rank_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank opportunities based on Launchonomy criteria."""
        for opp in opportunities:
            score = 0
            
            # Speed to first customer (40% weight)
            days = int(opp.get("time_to_first_customer", "30").split()[0])
            speed_score = max(0, (30 - days) / 30 * 40)
            
            # Budget constraint (30% weight)
            cost = opp.get("estimated_launch_cost", 500)
            budget_score = max(0, (500 - cost) / 500 * 30) if cost <= 500 else 0
            
            # Automation potential (20% weight)
            automation_map = {"Very High": 20, "High": 15, "Medium": 10, "Low": 5}
            automation_score = automation_map.get(opp.get("automation_potential", "Medium"), 10)
            
            # Competition level (10% weight) - lower competition is better
            competition_map = {"Low": 10, "Medium": 7, "High": 3}
            competition_score = competition_map.get(opp.get("competition_level", "Medium"), 7)
            
            total_score = speed_score + budget_score + automation_score + competition_score
            opp["launchonomy_score"] = round(total_score, 2)
        
        # Sort by score (highest first)
        return sorted(opportunities, key=lambda x: x["launchonomy_score"], reverse=True)
    
    async def _generate_recommendations(self, ranked_opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate strategic recommendations based on scan results."""
        if not ranked_opportunities:
            return {
                "primary_recommendation": "No viable opportunities found",
                "reasoning": "Scan did not identify opportunities meeting Launchonomy criteria",
                "suggested_actions": ["Expand search criteria", "Consider different market segments"]
            }
        
        top_opportunity = ranked_opportunities[0]
        
        return {
            "primary_recommendation": f"Pursue '{top_opportunity['name']}' as primary opportunity",
            "reasoning": f"Highest Launchonomy score ({top_opportunity['launchonomy_score']}) with {top_opportunity['time_to_first_customer']} to first customer",
            "risk_factors": self._assess_risks(top_opportunity),
            "success_factors": self._identify_success_factors(top_opportunity),
            "suggested_actions": [
                f"Begin MVP development for {top_opportunity['name']}",
                "Validate market demand through quick prototype",
                "Set up basic infrastructure and tools"
            ]
        }
    
    def _assess_risks(self, opportunity: Dict[str, Any]) -> List[str]:
        """Assess risks for the given opportunity."""
        risks = []
        
        if opportunity.get("competition_level") == "High":
            risks.append("High competition may make customer acquisition difficult")
        
        if opportunity.get("estimated_launch_cost", 0) > 400:
            risks.append("High launch cost leaves little budget for marketing")
        
        if "API" in opportunity.get("name", ""):
            risks.append("Developer market may have longer sales cycles")
        
        return risks
    
    def _identify_success_factors(self, opportunity: Dict[str, Any]) -> List[str]:
        """Identify key success factors for the opportunity."""
        factors = []
        
        if opportunity.get("automation_potential") in ["High", "Very High"]:
            factors.append("High automation potential enables scalable operations")
        
        if opportunity.get("estimated_launch_cost", 500) < 300:
            factors.append("Low launch cost provides budget flexibility")
        
        if "subscription" in opportunity.get("revenue_model", "").lower():
            factors.append("Recurring revenue model provides predictable income")
        
        return factors
    
    def _estimate_scanning_cost(self, num_opportunities: int) -> float:
        """Estimate the cost of the scanning operation."""
        # Base cost for scanning tools and analysis
        base_cost = 5.0
        # Additional cost per opportunity researched
        per_opportunity_cost = 2.0
        
        return base_cost + (num_opportunities * per_opportunity_cost)
    
    async def _scan_with_market_research(self, mission_context: Dict[str, Any], 
                                       focus_areas: List[str], max_opportunities: int,
                                       tool_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use market research tool to find opportunities."""
        try:
            tool_result = await self._execute_tool(tool_spec, {
                "action": "find_opportunities",
                "mission_context": mission_context,
                "focus_areas": focus_areas,
                "max_results": max_opportunities,
                "criteria": {
                    "max_launch_cost": 500,
                    "target_time_to_customer": "30 days",
                    "automation_potential": "medium_or_higher"
                }
            })
            
            if tool_result.get("status") == "success":
                return tool_result.get("opportunities", [])
            else:
                self._log(f"Market research tool failed: {tool_result.get('error', 'Unknown error')}", "error")
                return []
                
        except Exception as e:
            self._log(f"Error using market research tool: {str(e)}", "error")
            return []
    
    async def _scan_with_trend_analysis(self, mission_context: Dict[str, Any], 
                                      focus_areas: List[str], tool_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use trend analysis tool to identify trending opportunities."""
        try:
            tool_result = await self._execute_tool(tool_spec, {
                "action": "analyze_trends",
                "focus_areas": focus_areas,
                "time_period": "last_30_days",
                "trend_types": ["emerging_markets", "growing_demand", "technology_trends"]
            })
            
            if tool_result.get("status") == "success":
                return tool_result.get("trending_opportunities", [])
            else:
                self._log(f"Trend analysis tool failed: {tool_result.get('error', 'Unknown error')}", "error")
                return []
                
        except Exception as e:
            self._log(f"Error using trend analysis tool: {str(e)}", "error")
            return []
    
    async def _scan_with_competitor_analysis(self, mission_context: Dict[str, Any], 
                                           focus_areas: List[str], tool_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use competitor analysis tool to find market gaps."""
        try:
            tool_result = await self._execute_tool(tool_spec, {
                "action": "find_market_gaps",
                "focus_areas": focus_areas,
                "analysis_depth": "competitive_landscape",
                "include": ["underserved_segments", "pricing_gaps", "feature_gaps"]
            })
            
            if tool_result.get("status") == "success":
                return tool_result.get("market_gaps", [])
            else:
                self._log(f"Competitor analysis tool failed: {tool_result.get('error', 'Unknown error')}", "error")
                return []
                
        except Exception as e:
            self._log(f"Error using competitor analysis tool: {str(e)}", "error")
            return []
    
    async def _scan_with_keyword_research(self, mission_context: Dict[str, Any], 
                                        focus_areas: List[str], tool_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use keyword research tool to identify demand-driven opportunities."""
        try:
            tool_result = await self._execute_tool(tool_spec, {
                "action": "research_demand",
                "focus_areas": focus_areas,
                "metrics": ["search_volume", "competition_level", "commercial_intent"],
                "filters": {
                    "min_search_volume": 1000,
                    "max_competition": "medium"
                }
            })
            
            if tool_result.get("status") == "success":
                return tool_result.get("demand_opportunities", [])
            else:
                self._log(f"Keyword research tool failed: {tool_result.get('error', 'Unknown error')}", "error")
                return []
                
        except Exception as e:
            self._log(f"Error using keyword research tool: {str(e)}", "error")
            return [] 