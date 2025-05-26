"""
Cost calculation utilities for Launchonomy missions.

This module provides functions to calculate costs from various sources:
- Workflow agent executions
- C-Suite agent interactions
- API calls and token usage
- Tool executions
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# OpenAI pricing (as of 2024) - update as needed
OPENAI_PRICING = {
    "gpt-4": {
        "input": 0.03 / 1000,   # $0.03 per 1K input tokens
        "output": 0.06 / 1000   # $0.06 per 1K output tokens
    },
    "gpt-4-turbo": {
        "input": 0.01 / 1000,   # $0.01 per 1K input tokens
        "output": 0.03 / 1000   # $0.03 per 1K output tokens
    },
    "gpt-4o": {
        "input": 0.005 / 1000,  # $0.005 per 1K input tokens
        "output": 0.015 / 1000  # $0.015 per 1K output tokens
    },
    "gpt-4o-mini": {
        "input": 0.00015 / 1000,  # $0.00015 per 1K input tokens
        "output": 0.0006 / 1000   # $0.0006 per 1K output tokens
    },
    "gpt-3.5-turbo": {
        "input": 0.0015 / 1000, # $0.0015 per 1K input tokens
        "output": 0.002 / 1000  # $0.002 per 1K output tokens
    }
}

# Real-world third-party service costs (monthly estimates)
THIRD_PARTY_COSTS = {
    "hosting": {
        "vercel_pro": 20.0,
        "railway_starter": 5.0,
        "heroku_basic": 7.0,
        "netlify_pro": 19.0,
        "aws_lightsail": 10.0
    },
    "domains": {
        "namecheap_com": 12.98,  # Annual
        "godaddy_com": 14.99,    # Annual
        "google_domains": 12.0   # Annual
    },
    "payment_processing": {
        "stripe_rate": 0.029,    # 2.9% + $0.30 per transaction
        "stripe_fixed": 0.30,
        "paypal_rate": 0.0349,   # 3.49% for online payments
        "square_rate": 0.029     # 2.9% + $0.30
    },
    "email_services": {
        "convertkit_creator": 29.0,    # Up to 1,000 subscribers
        "mailchimp_essentials": 13.0,  # Up to 500 contacts
        "sendgrid_essentials": 19.95,  # Up to 50,000 emails
        "postmark_starter": 10.0       # Up to 10,000 emails
    },
    "analytics": {
        "google_analytics": 0.0,       # Free
        "mixpanel_growth": 25.0,       # Up to 100M events
        "amplitude_plus": 61.0,        # Up to 10M events
        "hotjar_plus": 39.0            # Up to 100 sessions/day
    },
    "monitoring": {
        "uptimerobot_pro": 7.0,        # Up to 50 monitors
        "pingdom_starter": 10.0,       # Up to 10 checks
        "datadog_pro": 15.0,           # Per host
        "newrelic_standard": 25.0      # Per host
    },
    "cdn": {
        "cloudflare_pro": 20.0,
        "aws_cloudfront": 8.50,        # Estimated for small site
        "bunnycdn": 1.0                # Pay as you go, very low
    },
    "database": {
        "planetscale_scaler": 29.0,    # 10GB storage
        "supabase_pro": 25.0,          # 8GB database
        "mongodb_atlas": 9.0,          # M2 cluster
        "postgresql_heroku": 9.0       # Standard-0 plan
    }
}

def calculate_token_cost(input_tokens: int, output_tokens: int, model: str = "gpt-4o-mini") -> float:
    """Calculate cost based on token usage and model."""
    if model not in OPENAI_PRICING:
        logger.warning(f"Unknown model {model}, using gpt-4o-mini pricing")
        model = "gpt-4o-mini"
    
    pricing = OPENAI_PRICING[model]
    input_cost = input_tokens * pricing["input"]
    output_cost = output_tokens * pricing["output"]
    
    return input_cost + output_cost

def calculate_third_party_service_cost(service_type: str, service_name: str, usage_data: Dict[str, Any] = None) -> float:
    """Calculate cost for third-party services based on actual usage."""
    if service_type not in THIRD_PARTY_COSTS:
        logger.warning(f"Unknown service type: {service_type}")
        return 0.0
    
    service_costs = THIRD_PARTY_COSTS[service_type]
    
    if service_name not in service_costs:
        logger.warning(f"Unknown service {service_name} in {service_type}")
        return 0.0
    
    base_cost = service_costs[service_name]
    
    # Handle usage-based pricing
    if service_type == "payment_processing" and usage_data:
        transaction_amount = usage_data.get("transaction_amount", 0.0)
        transaction_count = usage_data.get("transaction_count", 0)
        
        if service_name == "stripe_rate":
            return (transaction_amount * THIRD_PARTY_COSTS["payment_processing"]["stripe_rate"] + 
                   transaction_count * THIRD_PARTY_COSTS["payment_processing"]["stripe_fixed"])
        elif service_name == "paypal_rate":
            return transaction_amount * THIRD_PARTY_COSTS["payment_processing"]["paypal_rate"]
        elif service_name == "square_rate":
            return (transaction_amount * THIRD_PARTY_COSTS["payment_processing"]["square_rate"] + 
                   transaction_count * THIRD_PARTY_COSTS["payment_processing"]["stripe_fixed"])
    
    # For domain costs, convert annual to monthly
    if service_type == "domains":
        return base_cost / 12.0  # Convert annual to monthly
    
    return base_cost

def calculate_deployment_infrastructure_cost(deployment_config: Dict[str, Any]) -> Dict[str, float]:
    """Calculate real infrastructure costs for a deployment."""
    costs = {}
    
    # Hosting costs
    hosting_provider = deployment_config.get("hosting_provider", "vercel_pro")
    if hosting_provider in THIRD_PARTY_COSTS["hosting"]:
        costs["hosting"] = THIRD_PARTY_COSTS["hosting"][hosting_provider]
    else:
        costs["hosting"] = 15.0  # Default estimate
    
    # Domain costs (monthly)
    domain_provider = deployment_config.get("domain_provider", "namecheap_com")
    costs["domain"] = calculate_third_party_service_cost("domains", domain_provider)
    
    # Email service costs
    email_service = deployment_config.get("email_service", "convertkit_creator")
    costs["email"] = calculate_third_party_service_cost("email_services", email_service)
    
    # Analytics costs
    analytics_service = deployment_config.get("analytics_service", "google_analytics")
    costs["analytics"] = calculate_third_party_service_cost("analytics", analytics_service)
    
    # Monitoring costs
    monitoring_service = deployment_config.get("monitoring_service", "uptimerobot_pro")
    costs["monitoring"] = calculate_third_party_service_cost("monitoring", monitoring_service)
    
    # Payment processing (base monthly fee, usage calculated separately)
    costs["payment_processing_base"] = 0.0  # Most have no monthly fee
    
    # Database costs
    database_service = deployment_config.get("database_service", "postgresql_heroku")
    costs["database"] = calculate_third_party_service_cost("database", database_service)
    
    return costs

def calculate_marketing_campaign_cost(campaign_config: Dict[str, Any]) -> Dict[str, float]:
    """Calculate real marketing campaign costs."""
    costs = {}
    
    # Social media advertising
    social_budget = campaign_config.get("social_media_budget", 0.0)
    costs["social_media_ads"] = social_budget
    
    # Google Ads
    google_ads_budget = campaign_config.get("google_ads_budget", 0.0)
    costs["google_ads"] = google_ads_budget
    
    # Content creation tools
    content_tools = campaign_config.get("content_tools", [])
    content_cost = 0.0
    for tool in content_tools:
        if tool == "canva_pro":
            content_cost += 12.99  # Monthly
        elif tool == "adobe_creative":
            content_cost += 52.99  # Monthly
        elif tool == "figma_professional":
            content_cost += 12.0   # Monthly
    costs["content_creation"] = content_cost
    
    # Email marketing (additional to base email service)
    email_marketing_budget = campaign_config.get("email_marketing_budget", 0.0)
    costs["email_marketing"] = email_marketing_budget
    
    # Influencer marketing
    influencer_budget = campaign_config.get("influencer_budget", 0.0)
    costs["influencer_marketing"] = influencer_budget
    
    return costs

def calculate_workflow_step_cost(step_data: Dict[str, Any]) -> float:
    """Calculate cost for a single workflow step."""
    total_cost = 0.0
    
    # Extract token usage if available
    if "token_usage" in step_data:
        token_data = step_data["token_usage"]
        input_tokens = token_data.get("input_tokens", 0)
        output_tokens = token_data.get("output_tokens", 0)
        model = token_data.get("model", "gpt-4")
        total_cost += calculate_token_cost(input_tokens, output_tokens, model)
    
    # Extract direct cost if specified
    if "cost" in step_data:
        total_cost += step_data["cost"]
    
    # Extract costs from sub-operations
    if "operations" in step_data:
        for operation in step_data["operations"]:
            if isinstance(operation, dict):
                total_cost += calculate_workflow_step_cost(operation)
    
    return total_cost

def calculate_csuite_planning_cost(planning_data: Dict[str, Any]) -> float:
    """Calculate cost for C-Suite planning phase."""
    total_cost = 0.0
    
    # Cost from individual agent inputs
    for agent_name, agent_data in planning_data.items():
        if isinstance(agent_data, dict):
            if "token_usage" in agent_data:
                token_data = agent_data["token_usage"]
                input_tokens = token_data.get("input_tokens", 0)
                output_tokens = token_data.get("output_tokens", 0)
                model = token_data.get("model", "gpt-4")
                total_cost += calculate_token_cost(input_tokens, output_tokens, model)
            
            if "cost" in agent_data:
                total_cost += agent_data["cost"]
    
    return total_cost

def calculate_csuite_review_cost(review_data: Dict[str, Any]) -> float:
    """Calculate cost for C-Suite review phase."""
    total_cost = 0.0
    
    # Similar to planning cost calculation
    for agent_name, agent_data in review_data.items():
        if isinstance(agent_data, dict):
            if "token_usage" in agent_data:
                token_data = agent_data["token_usage"]
                input_tokens = token_data.get("input_tokens", 0)
                output_tokens = token_data.get("output_tokens", 0)
                model = token_data.get("model", "gpt-4")
                total_cost += calculate_token_cost(input_tokens, output_tokens, model)
            
            if "cost" in agent_data:
                total_cost += agent_data["cost"]
    
    return total_cost

def calculate_cycle_cost(cycle_log: Dict[str, Any]) -> float:
    """Calculate total cost for a complete cycle."""
    total_cost = 0.0
    
    # C-Suite planning cost
    if "csuite_planning" in cycle_log:
        total_cost += calculate_csuite_planning_cost(cycle_log["csuite_planning"])
    
    # Workflow steps cost
    if "steps" in cycle_log:
        for step_name, step_data in cycle_log["steps"].items():
            if isinstance(step_data, dict):
                total_cost += calculate_workflow_step_cost(step_data)
    
    # C-Suite review cost
    if "csuite_review" in cycle_log:
        total_cost += calculate_csuite_review_cost(cycle_log["csuite_review"])
    
    # Add any direct cycle costs
    if "direct_costs" in cycle_log:
        total_cost += cycle_log["direct_costs"]
    
    return total_cost

def calculate_mission_total_cost(execution_log: List[Dict[str, Any]]) -> float:
    """Calculate total cost for an entire mission from execution log."""
    total_cost = 0.0
    
    for cycle_log in execution_log:
        if isinstance(cycle_log, dict):
            total_cost += calculate_cycle_cost(cycle_log)
    
    return total_cost

def estimate_cost_breakdown(cycle_log: Dict[str, Any]) -> Dict[str, float]:
    """Provide detailed cost breakdown for a cycle."""
    breakdown = {
        "csuite_planning": 0.0,
        "workflow_execution": 0.0,
        "csuite_review": 0.0,
        "other": 0.0
    }
    
    # C-Suite planning cost
    if "csuite_planning" in cycle_log:
        breakdown["csuite_planning"] = calculate_csuite_planning_cost(cycle_log["csuite_planning"])
    
    # Workflow steps cost
    if "steps" in cycle_log:
        for step_name, step_data in cycle_log["steps"].items():
            if isinstance(step_data, dict):
                breakdown["workflow_execution"] += calculate_workflow_step_cost(step_data)
    
    # C-Suite review cost
    if "csuite_review" in cycle_log:
        breakdown["csuite_review"] = calculate_csuite_review_cost(cycle_log["csuite_review"])
    
    # Other costs
    if "direct_costs" in cycle_log:
        breakdown["other"] = cycle_log["direct_costs"]
    
    return breakdown

def format_cost_summary(cost: float, breakdown: Optional[Dict[str, float]] = None) -> str:
    """Format cost information for display."""
    summary = f"${cost:.4f}"
    
    if breakdown:
        details = []
        for category, amount in breakdown.items():
            if amount > 0:
                details.append(f"{category}: ${amount:.4f}")
        
        if details:
            summary += f" ({', '.join(details)})"
    
    return summary 