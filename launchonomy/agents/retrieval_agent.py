import logging
from typing import List, Dict, Any, Optional
from ..core.vector_memory import ChromaDBVectorMemory

logger = logging.getLogger(__name__)

class RetrievalAgent:
    """
    Agent responsible for retrieving relevant memories from the mission's vector store.
    
    This agent provides a simple interface for other agents to query the mission's
    long-term memory and retrieve contextually relevant information from past cycles.
    """
    
    def __init__(self, memory_store: ChromaDBVectorMemory):
        """
        Initialize the RetrievalAgent with a memory store.
        
        Args:
            memory_store: ChromaDBVectorMemory instance for the current mission
        """
        self.memory_store = memory_store
        self.name = "RetrievalAgent"
        
    async def retrieve(self, query: str, k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Retrieve relevant memories based on a query.
        
        Args:
            query: Text query to search for relevant memories
            k: Number of results to return (default: 5)
            filters: Optional metadata filters to apply
            
        Returns:
            List of relevant memory content strings
        """
        try:
            # Query the memory store
            results = self.memory_store.query(query_text=query, k=k, where=filters)
            
            # Extract just the content strings
            memory_contents = []
            for result in results:
                content = result.get("content", "")
                if content:
                    # Add metadata context if available
                    metadata = result.get("metadata", {})
                    step = metadata.get("step", "")
                    timestamp = metadata.get("timestamp", "")
                    
                    # Format with context
                    if step and timestamp:
                        formatted_content = f"[{step} - {timestamp[:10]}] {content}"
                    elif step:
                        formatted_content = f"[{step}] {content}"
                    else:
                        formatted_content = content
                    
                    memory_contents.append(formatted_content)
            
            logger.debug(f"Retrieved {len(memory_contents)} memories for query: {query[:50]}...")
            return memory_contents
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
            return []
    
    async def retrieve_by_step(self, step_name: str, k: int = 3) -> List[str]:
        """
        Retrieve memories from a specific workflow step.
        
        Args:
            step_name: Name of the workflow step (e.g., "scan", "deploy", "campaign")
            k: Number of results to return
            
        Returns:
            List of memory content strings from the specified step
        """
        filters = {"step": step_name}
        return await self.retrieve("", k=k, filters=filters)
    
    async def retrieve_recent(self, k: int = 5) -> List[str]:
        """
        Retrieve the most recent memories.
        
        Args:
            k: Number of recent memories to return
            
        Returns:
            List of recent memory content strings
        """
        # Query with a generic term to get all results, then sort by timestamp
        try:
            results = self.memory_store.query(query_text="mission", k=k*2)  # Get more to sort
            
            # Sort by timestamp (most recent first)
            sorted_results = sorted(
                results,
                key=lambda x: x.get("metadata", {}).get("timestamp", ""),
                reverse=True
            )
            
            # Extract content from top k results
            memory_contents = []
            for result in sorted_results[:k]:
                content = result.get("content", "")
                if content:
                    metadata = result.get("metadata", {})
                    step = metadata.get("step", "")
                    timestamp = metadata.get("timestamp", "")
                    
                    if step and timestamp:
                        formatted_content = f"[{step} - {timestamp[:10]}] {content}"
                    else:
                        formatted_content = content
                    
                    memory_contents.append(formatted_content)
            
            return memory_contents
            
        except Exception as e:
            logger.error(f"Error retrieving recent memories: {str(e)}")
            return []
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the memory store.
        
        Returns:
            Dictionary with memory store statistics
        """
        return self.memory_store.get_collection_stats() 