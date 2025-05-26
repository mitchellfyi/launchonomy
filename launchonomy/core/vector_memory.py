import os
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

@dataclass
class MemoryContent:
    """Represents a piece of content to be stored in vector memory."""
    content: str
    mime_type: str = "TEXT"
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class PersistentChromaDBVectorMemoryConfig:
    """Configuration for persistent ChromaDB vector memory."""
    persist_directory: str
    collection_name: str
    embedding_function: Optional[str] = None
    
class ChromaDBVectorMemory:
    """
    ChromaDB-based vector memory for storing and retrieving mission context.
    
    This class provides persistent vector storage for agent memories, allowing
    agents to store and retrieve contextual information across mission cycles.
    """
    
    def __init__(self, config: PersistentChromaDBVectorMemoryConfig):
        self.config = config
        self.persist_directory = config.persist_directory
        self.collection_name = config.collection_name
        
        # Ensure persist directory exists
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing ChromaDB collection: {self.collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": f"Mission memory for {self.collection_name}"}
            )
            logger.info(f"Created new ChromaDB collection: {self.collection_name}")
    
    def upsert(self, content: MemoryContent) -> str:
        """
        Store or update content in the vector memory.
        
        Args:
            content: MemoryContent object to store
            
        Returns:
            str: Unique ID of the stored content
        """
        # Generate unique ID if not provided in metadata
        content_id = content.metadata.get("id", str(uuid.uuid4()))
        
        # Prepare metadata
        metadata = content.metadata.copy()
        metadata.update({
            "mime_type": content.mime_type,
            "timestamp": datetime.now().isoformat(),
            "id": content_id
        })
        
        try:
            # Add to collection
            self.collection.upsert(
                documents=[content.content],
                metadatas=[metadata],
                ids=[content_id]
            )
            
            logger.debug(f"Upserted content to ChromaDB: {content_id}")
            return content_id
            
        except Exception as e:
            logger.error(f"Error upserting content to ChromaDB: {str(e)}")
            raise
    
    def query(self, query_text: str, k: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query the vector memory for relevant content.
        
        Args:
            query_text: Text to search for
            k: Number of results to return
            where: Optional metadata filters
            
        Returns:
            List of dictionaries containing content and metadata
        """
        try:
            # Query the collection
            results = self.collection.query(
                query_texts=[query_text],
                n_results=k,
                where=where
            )
            
            # Format results
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    result = {
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {},
                        "distance": results["distances"][0][i] if results["distances"] and results["distances"][0] else 0.0,
                        "id": results["ids"][0][i] if results["ids"] and results["ids"][0] else None
                    }
                    formatted_results.append(result)
            
            logger.debug(f"ChromaDB query returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {str(e)}")
            return []
    
    def delete(self, content_id: str) -> bool:
        """
        Delete content from vector memory.
        
        Args:
            content_id: ID of content to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.collection.delete(ids=[content_id])
            logger.debug(f"Deleted content from ChromaDB: {content_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting content from ChromaDB: {str(e)}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {"error": str(e)}
    
    def clear_collection(self) -> bool:
        """
        Clear all documents from the collection.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": f"Mission memory for {self.collection_name}"}
            )
            logger.info(f"Cleared ChromaDB collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Error clearing collection: {str(e)}")
            return False

def create_mission_memory(mission_id: str, base_directory: Optional[str] = None) -> ChromaDBVectorMemory:
    """
    Factory function to create a ChromaDB vector memory for a specific mission.
    
    Args:
        mission_id: Unique identifier for the mission
        base_directory: Base directory for ChromaDB storage (defaults to ~/.chromadb_launchonomy)
        
    Returns:
        ChromaDBVectorMemory instance configured for the mission
    """
    if base_directory is None:
        base_directory = os.path.expanduser("~/.chromadb_launchonomy")
    
    config = PersistentChromaDBVectorMemoryConfig(
        persist_directory=base_directory,
        collection_name=f"mission_{mission_id}"
    )
    
    return ChromaDBVectorMemory(config) 