"""
Schema validation utilities for Launchonomy workflow agents.

This module provides schema validation using pydantic for input/output validation
in workflow agents and tools.
"""

import logging
from typing import Dict, Any, Optional, Type, Union
from pydantic import BaseModel, ValidationError, Field
from datetime import datetime

logger = logging.getLogger(__name__)

class ValidationResult:
    """Result of schema validation."""
    
    def __init__(self, is_valid: bool, errors: Optional[list] = None, validated_data: Optional[Dict[str, Any]] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.validated_data = validated_data

class BaseWorkflowInput(BaseModel):
    """Base schema for workflow agent inputs."""
    
    task_description: str = Field(..., description="Description of the task to perform")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context for the task")
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp of the request")

class BaseWorkflowOutput(BaseModel):
    """Base schema for workflow agent outputs."""
    
    status: str = Field(..., description="Status of the execution (success, failed, partial)")
    execution_type: str = Field(..., description="Type of execution performed")
    description: str = Field(..., description="Human-readable description of what was done")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Structured output data")
    errors: Optional[list] = Field(default=None, description="List of errors if any occurred")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp of completion")

class ScanAgentInput(BaseWorkflowInput):
    """Schema for ScanAgent input."""
    
    market_focus: Optional[str] = Field(default=None, description="Specific market or niche to focus on")
    budget_limit: Optional[float] = Field(default=1000.0, description="Budget limit for scanning activities")
    time_horizon: Optional[str] = Field(default="30_days", description="Time horizon for opportunities")

class ScanAgentOutput(BaseWorkflowOutput):
    """Schema for ScanAgent output."""
    
    opportunities: list = Field(..., description="List of identified opportunities")
    market_analysis: Dict[str, Any] = Field(..., description="Market analysis results")
    recommendations: list = Field(..., description="Recommended next steps")

class DeployAgentInput(BaseWorkflowInput):
    """Schema for DeployAgent input."""
    
    opportunity: Dict[str, Any] = Field(..., description="Selected opportunity to deploy")
    requirements: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Deployment requirements")
    budget_limit: Optional[float] = Field(default=500.0, description="Budget limit for deployment")

class DeployAgentOutput(BaseWorkflowOutput):
    """Schema for DeployAgent output."""
    
    deployment_url: Optional[str] = Field(default=None, description="URL of deployed application")
    architecture: Dict[str, Any] = Field(..., description="Architecture details")
    integrations: Dict[str, Any] = Field(..., description="Configured integrations")
    costs: Dict[str, Any] = Field(..., description="Deployment costs breakdown")

class CampaignAgentInput(BaseWorkflowInput):
    """Schema for CampaignAgent input."""
    
    product_info: Dict[str, Any] = Field(..., description="Product information for campaign")
    target_audience: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Target audience details")
    budget_limit: Optional[float] = Field(default=200.0, description="Campaign budget limit")
    campaign_type: Optional[str] = Field(default="launch", description="Type of campaign to run")

class CampaignAgentOutput(BaseWorkflowOutput):
    """Schema for CampaignAgent output."""
    
    campaigns: list = Field(..., description="List of created campaigns")
    performance_metrics: Dict[str, Any] = Field(..., description="Campaign performance data")
    optimization_suggestions: list = Field(..., description="Suggestions for optimization")

class AnalyticsAgentInput(BaseWorkflowInput):
    """Schema for AnalyticsAgent input."""
    
    analysis_type: str = Field(..., description="Type of analysis to perform")
    time_period: Optional[str] = Field(default="last_30_days", description="Time period for analysis")
    metrics_focus: Optional[list] = Field(default_factory=list, description="Specific metrics to focus on")

class AnalyticsAgentOutput(BaseWorkflowOutput):
    """Schema for AnalyticsAgent output."""
    
    metrics: Dict[str, Any] = Field(..., description="Collected metrics data")
    insights: list = Field(..., description="Generated insights")
    recommendations: list = Field(..., description="Data-driven recommendations")
    alerts: Optional[list] = Field(default=None, description="Any alerts or warnings")

class FinanceAgentInput(BaseWorkflowInput):
    """Schema for FinanceAgent input."""
    
    analysis_type: str = Field(..., description="Type of financial analysis")
    time_period: Optional[str] = Field(default="current_month", description="Time period for analysis")
    include_projections: Optional[bool] = Field(default=True, description="Whether to include projections")

class FinanceAgentOutput(BaseWorkflowOutput):
    """Schema for FinanceAgent output."""
    
    financial_data: Dict[str, Any] = Field(..., description="Financial data and metrics")
    analysis_results: Dict[str, Any] = Field(..., description="Analysis results")
    recommendations: list = Field(..., description="Financial recommendations")
    projections: Optional[Dict[str, Any]] = Field(default=None, description="Financial projections")

class GrowthAgentInput(BaseWorkflowInput):
    """Schema for GrowthAgent input."""
    
    current_metrics: Dict[str, Any] = Field(..., description="Current growth metrics")
    growth_targets: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Growth targets")
    experiment_budget: Optional[float] = Field(default=100.0, description="Budget for growth experiments")

class GrowthAgentOutput(BaseWorkflowOutput):
    """Schema for GrowthAgent output."""
    
    experiments: list = Field(..., description="Growth experiments conducted")
    results: Dict[str, Any] = Field(..., description="Growth experiment results")
    optimizations: list = Field(..., description="Optimization recommendations")
    next_experiments: list = Field(..., description="Suggested next experiments")

# Schema registry for easy lookup
AGENT_SCHEMAS = {
    "ScanAgent": {
        "input": ScanAgentInput,
        "output": ScanAgentOutput
    },
    "DeployAgent": {
        "input": DeployAgentInput,
        "output": DeployAgentOutput
    },
    "CampaignAgent": {
        "input": CampaignAgentInput,
        "output": CampaignAgentOutput
    },
    "AnalyticsAgent": {
        "input": AnalyticsAgentInput,
        "output": AnalyticsAgentOutput
    },
    "FinanceAgent": {
        "input": FinanceAgentInput,
        "output": FinanceAgentOutput
    },
    "GrowthAgent": {
        "input": GrowthAgentInput,
        "output": GrowthAgentOutput
    }
}

def validate_input(agent_name: str, data: Dict[str, Any]) -> ValidationResult:
    """Validate input data for a specific agent."""
    
    if agent_name not in AGENT_SCHEMAS:
        logger.warning(f"No schema defined for agent: {agent_name}")
        return ValidationResult(is_valid=True, validated_data=data)
    
    schema_class = AGENT_SCHEMAS[agent_name]["input"]
    
    try:
        validated_model = schema_class(**data)
        return ValidationResult(
            is_valid=True,
            validated_data=validated_model.model_dump()
        )
    except ValidationError as e:
        errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
        logger.error(f"Input validation failed for {agent_name}: {errors}")
        return ValidationResult(
            is_valid=False,
            errors=errors
        )

def validate_output(agent_name: str, data: Dict[str, Any]) -> ValidationResult:
    """Validate output data for a specific agent."""
    
    if agent_name not in AGENT_SCHEMAS:
        logger.warning(f"No schema defined for agent: {agent_name}")
        return ValidationResult(is_valid=True, validated_data=data)
    
    schema_class = AGENT_SCHEMAS[agent_name]["output"]
    
    try:
        validated_model = schema_class(**data)
        return ValidationResult(
            is_valid=True,
            validated_data=validated_model.model_dump()
        )
    except ValidationError as e:
        errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
        logger.error(f"Output validation failed for {agent_name}: {errors}")
        return ValidationResult(
            is_valid=False,
            errors=errors
        )

def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> ValidationResult:
    """Validate data against a JSON schema."""
    
    try:
        # Create a dynamic pydantic model from JSON schema
        # This is a simplified implementation - could be enhanced with jsonschema library
        required_fields = schema.get("required", [])
        properties = schema.get("properties", {})
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return ValidationResult(
                is_valid=False,
                errors=[f"Missing required field: {field}" for field in missing_fields]
            )
        
        # Basic type checking
        errors = []
        for field, field_schema in properties.items():
            if field in data:
                expected_type = field_schema.get("type")
                actual_value = data[field]
                
                if expected_type == "string" and not isinstance(actual_value, str):
                    errors.append(f"Field '{field}' should be string, got {type(actual_value).__name__}")
                elif expected_type == "number" and not isinstance(actual_value, (int, float)):
                    errors.append(f"Field '{field}' should be number, got {type(actual_value).__name__}")
                elif expected_type == "boolean" and not isinstance(actual_value, bool):
                    errors.append(f"Field '{field}' should be boolean, got {type(actual_value).__name__}")
                elif expected_type == "array" and not isinstance(actual_value, list):
                    errors.append(f"Field '{field}' should be array, got {type(actual_value).__name__}")
                elif expected_type == "object" and not isinstance(actual_value, dict):
                    errors.append(f"Field '{field}' should be object, got {type(actual_value).__name__}")
        
        if errors:
            return ValidationResult(is_valid=False, errors=errors)
        
        return ValidationResult(is_valid=True, validated_data=data)
        
    except Exception as e:
        logger.error(f"Schema validation error: {e}")
        return ValidationResult(
            is_valid=False,
            errors=[f"Schema validation error: {str(e)}"]
        )

def get_agent_input_schema(agent_name: str) -> Optional[Type[BaseModel]]:
    """Get the input schema class for an agent."""
    return AGENT_SCHEMAS.get(agent_name, {}).get("input")

def get_agent_output_schema(agent_name: str) -> Optional[Type[BaseModel]]:
    """Get the output schema class for an agent."""
    return AGENT_SCHEMAS.get(agent_name, {}).get("output")

def create_example_input(agent_name: str) -> Dict[str, Any]:
    """Create an example input for an agent based on its schema."""
    
    schema_class = get_agent_input_schema(agent_name)
    if not schema_class:
        return {"task_description": f"Example task for {agent_name}"}
    
    try:
        # Create an instance with default values
        example = schema_class(task_description=f"Example task for {agent_name}")
        return example.model_dump()
    except Exception as e:
        logger.error(f"Error creating example input for {agent_name}: {e}")
        return {"task_description": f"Example task for {agent_name}"}

def create_example_output(agent_name: str) -> Dict[str, Any]:
    """Create an example output for an agent based on its schema."""
    
    schema_class = get_agent_output_schema(agent_name)
    if not schema_class:
        return {
            "status": "success",
            "execution_type": "example",
            "description": f"Example output from {agent_name}",
            "output_data": {}
        }
    
    try:
        # Create an instance with minimal required values
        example = schema_class(
            status="success",
            execution_type="example",
            description=f"Example output from {agent_name}",
            output_data={}
        )
        return example.model_dump()
    except Exception as e:
        logger.error(f"Error creating example output for {agent_name}: {e}")
        return {
            "status": "success",
            "execution_type": "example",
            "description": f"Example output from {agent_name}",
            "output_data": {}
        } 