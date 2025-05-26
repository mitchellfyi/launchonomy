import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..core.vector_memory import ChromaDBVectorMemory, MemoryContent

logger = logging.getLogger(__name__)

class MemoryHelper:
    """
    Helper class for logging key events and information to the mission's vector memory.
    
    This class provides convenient methods for storing workflow events, insights,
    and other important information that agents can later retrieve for context.
    """
    
    def __init__(self, memory_store: ChromaDBVectorMemory, mission_id: str):
        """
        Initialize the MemoryHelper.
        
        Args:
            memory_store: ChromaDBVectorMemory instance for the mission
            mission_id: Unique identifier for the current mission
        """
        self.memory_store = memory_store
        self.mission_id = mission_id
    
    def log_workflow_event(self, step_name: str, summary: str, details: Optional[Dict[str, Any]] = None) -> str:
        """
        Log a workflow step event to memory.
        
        Args:
            step_name: Name of the workflow step (e.g., "scan", "deploy", "campaign")
            summary: Brief summary of what happened
            details: Optional additional details to include
            
        Returns:
            str: ID of the stored memory
        """
        try:
            # Create detailed content
            content_parts = [f"Workflow Step: {step_name}", f"Summary: {summary}"]
            
            if details:
                content_parts.append("Details:")
                for key, value in details.items():
                    content_parts.append(f"  - {key}: {value}")
            
            content = "\n".join(content_parts)
            
            # Create memory content
            memory_content = MemoryContent(
                content=content,
                mime_type="TEXT",
                metadata={
                    "mission": self.mission_id,
                    "type": "event",
                    "step": step_name,
                    "timestamp": datetime.now().isoformat(),
                    "category": "workflow_event"
                }
            )
            
            # Store in memory
            memory_id = self.memory_store.upsert(memory_content)
            logger.debug(f"Logged workflow event for {step_name}: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error logging workflow event: {str(e)}")
            return ""
    
    def log_insight(self, insight: str, source: str, confidence: float = 1.0) -> str:
        """
        Log an insight or learning to memory.
        
        Args:
            insight: The insight or learning
            source: Source of the insight (e.g., agent name, analysis type)
            confidence: Confidence level in the insight (0.0 to 1.0)
            
        Returns:
            str: ID of the stored memory
        """
        try:
            content = f"Insight: {insight}\nSource: {source}\nConfidence: {confidence:.2f}"
            
            memory_content = MemoryContent(
                content=content,
                mime_type="TEXT",
                metadata={
                    "mission": self.mission_id,
                    "type": "insight",
                    "source": source,
                    "confidence": confidence,
                    "timestamp": datetime.now().isoformat(),
                    "category": "learning"
                }
            )
            
            memory_id = self.memory_store.upsert(memory_content)
            logger.debug(f"Logged insight from {source}: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error logging insight: {str(e)}")
            return ""
    
    def log_decision(self, decision: str, rationale: str, agent_name: str) -> str:
        """
        Log a decision made by an agent.
        
        Args:
            decision: The decision that was made
            rationale: Reasoning behind the decision
            agent_name: Name of the agent that made the decision
            
        Returns:
            str: ID of the stored memory
        """
        try:
            content = f"Decision: {decision}\nRationale: {rationale}\nDecision Maker: {agent_name}"
            
            memory_content = MemoryContent(
                content=content,
                mime_type="TEXT",
                metadata={
                    "mission": self.mission_id,
                    "type": "decision",
                    "agent": agent_name,
                    "timestamp": datetime.now().isoformat(),
                    "category": "decision_making"
                }
            )
            
            memory_id = self.memory_store.upsert(memory_content)
            logger.debug(f"Logged decision by {agent_name}: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error logging decision: {str(e)}")
            return ""
    
    def log_performance_metrics(self, step_name: str, metrics: Dict[str, Any]) -> str:
        """
        Log performance metrics for a workflow step.
        
        Args:
            step_name: Name of the workflow step
            metrics: Dictionary of metrics and their values
            
        Returns:
            str: ID of the stored memory
        """
        try:
            content_parts = [f"Performance Metrics for {step_name}:"]
            
            for metric, value in metrics.items():
                if isinstance(value, (int, float)):
                    content_parts.append(f"  - {metric}: {value:.2f}")
                else:
                    content_parts.append(f"  - {metric}: {value}")
            
            content = "\n".join(content_parts)
            
            memory_content = MemoryContent(
                content=content,
                mime_type="TEXT",
                metadata={
                    "mission": self.mission_id,
                    "type": "metrics",
                    "step": step_name,
                    "timestamp": datetime.now().isoformat(),
                    "category": "performance"
                }
            )
            
            memory_id = self.memory_store.upsert(memory_content)
            logger.debug(f"Logged metrics for {step_name}: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error logging metrics: {str(e)}")
            return ""
    
    def log_error_or_failure(self, step_name: str, error_description: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Log an error or failure for future learning.
        
        Args:
            step_name: Name of the workflow step where error occurred
            error_description: Description of the error
            context: Optional context information
            
        Returns:
            str: ID of the stored memory
        """
        try:
            content_parts = [
                f"Error in {step_name}:",
                f"Description: {error_description}"
            ]
            
            if context:
                content_parts.append("Context:")
                for key, value in context.items():
                    content_parts.append(f"  - {key}: {value}")
            
            content = "\n".join(content_parts)
            
            memory_content = MemoryContent(
                content=content,
                mime_type="TEXT",
                metadata={
                    "mission": self.mission_id,
                    "type": "error",
                    "step": step_name,
                    "timestamp": datetime.now().isoformat(),
                    "category": "failure_learning"
                }
            )
            
            memory_id = self.memory_store.upsert(memory_content)
            logger.debug(f"Logged error for {step_name}: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error logging error: {str(e)}")
            return ""
    
    def log_success_pattern(self, step_name: str, success_description: str, key_factors: List[str]) -> str:
        """
        Log a successful pattern for future replication.
        
        Args:
            step_name: Name of the workflow step
            success_description: Description of what succeeded
            key_factors: List of key factors that contributed to success
            
        Returns:
            str: ID of the stored memory
        """
        try:
            content_parts = [
                f"Success in {step_name}:",
                f"Description: {success_description}",
                "Key Success Factors:"
            ]
            
            for factor in key_factors:
                content_parts.append(f"  - {factor}")
            
            content = "\n".join(content_parts)
            
            memory_content = MemoryContent(
                content=content,
                mime_type="TEXT",
                metadata={
                    "mission": self.mission_id,
                    "type": "success",
                    "step": step_name,
                    "timestamp": datetime.now().isoformat(),
                    "category": "success_pattern"
                }
            )
            
            memory_id = self.memory_store.upsert(memory_content)
            logger.debug(f"Logged success pattern for {step_name}: {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error logging success pattern: {str(e)}")
            return "" 