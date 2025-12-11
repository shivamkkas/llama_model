"""
Conversation Manager for storing conversation history in ChromaDB
"""
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime
import json

import chromadb
from chromadb.config import Settings

from config.config import Config


class ConversationManager:
    def __init__(self, config: Config):
        self.config = config
        self.chroma_client = None
        self.collection = None
    
    async def initialize(self):
        """Initialize ChromaDB client for conversations"""
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(
            path=self.config.chroma.persist_directory
        )
        
        # Get or create collection for conversations
        try:
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.config.chroma.collection_name,
                metadata={"description": "Conversation history for MCP server"}
            )
            print(f"✓ Initialized ChromaDB conversation collection")
        except Exception as e:
            print(f"✗ Failed to initialize conversation collection: {str(e)}")
            raise
    
    async def create_conversation(
        self,
        user_id: str,
        initial_message: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new conversation"""
        
        conversation_id = str(uuid.uuid4())
        
        # Add initial messages
        await self.add_message(
            conversation_id=conversation_id,
            role="user",
            content=initial_message,
            metadata={"user_id": user_id, **(metadata or {})}
        )
        
        await self.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response,
            metadata={"user_id": user_id, **(metadata or {})}
        )
        
        return conversation_id
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a message to a conversation"""
        
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        message_metadata = {
            "conversation_id": conversation_id,
            "role": role,
            "timestamp": timestamp,
            **(metadata or {})
        }
        
        # Store in ChromaDB
        self.collection.add(
            documents=[content],
            metadatas=[message_metadata],
            ids=[message_id]
        )
    
    async def get_conversation(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve conversation history"""
        
        results = self.collection.get(
            where={"conversation_id": conversation_id}
        )
        
        if not results['ids']:
            return []
        
        # Format messages
        messages = []
        for i, doc in enumerate(results['documents']):
            messages.append({
                "id": results['ids'][i],
                "role": results['metadatas'][i].get('role'),
                "content": doc,
                "timestamp": results['metadatas'][i].get('timestamp'),
                "metadata": {
                    k: v for k, v in results['metadatas'][i].items()
                    if k not in ['conversation_id', 'role', 'timestamp']
                }
            })
        
        # Sort by timestamp
        messages.sort(key=lambda x: x['timestamp'])
        
        # Apply limit if specified
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    async def search_conversations(
        self,
        query: str,
        user_id: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search across all conversations for a user"""
        
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"user_id": user_id}
        )
        
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    "conversation_id": results['metadatas'][0][i].get('conversation_id'),
                    "content": doc,
                    "role": results['metadatas'][0][i].get('role'),
                    "timestamp": results['metadatas'][0][i].get('timestamp'),
                    "score": results['distances'][0][i] if results.get('distances') else None
                })
        
        return formatted_results
    
    async def list_conversations(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """List all conversations for a user"""
        
        results = self.collection.get(
            where={"user_id": user_id}
        )
        
        # Group by conversation_id
        conversations = {}
        for i, metadata in enumerate(results['metadatas']):
            conv_id = metadata.get('conversation_id')
            if conv_id:
                if conv_id not in conversations:
                    conversations[conv_id] = {
                        "conversation_id": conv_id,
                        "user_id": user_id,
                        "message_count": 0,
                        "first_message": None,
                        "last_message": None,
                        "created_at": None,
                        "updated_at": None
                    }
                
                timestamp = metadata.get('timestamp')
                conversations[conv_id]["message_count"] += 1
                
                if not conversations[conv_id]["created_at"] or timestamp < conversations[conv_id]["created_at"]:
                    conversations[conv_id]["created_at"] = timestamp
                    conversations[conv_id]["first_message"] = results['documents'][i][:100]
                
                if not conversations[conv_id]["updated_at"] or timestamp > conversations[conv_id]["updated_at"]:
                    conversations[conv_id]["updated_at"] = timestamp
                    conversations[conv_id]["last_message"] = results['documents'][i][:100]
        
        # Sort by last updated
        sorted_conversations = sorted(
            conversations.values(),
            key=lambda x: x["updated_at"] or "",
            reverse=True
        )
        
        return sorted_conversations
    
    async def delete_conversation(self, conversation_id: str):
        """Delete a conversation and all its messages"""
        
        results = self.collection.get(
            where={"conversation_id": conversation_id}
        )
        
        if results['ids']:
            self.collection.delete(ids=results['ids'])
            print(f"✓ Deleted conversation {conversation_id}")
    
    async def delete_user_conversations(self, user_id: str):
        """Delete all conversations for a user"""
        
        results = self.collection.get(
            where={"user_id": user_id}
        )
        
        if results['ids']:
            self.collection.delete(ids=results['ids'])
            print(f"✓ Deleted all conversations for user {user_id}")
    
    async def get_conversation_summary(
        self,
        conversation_id: str
    ) -> Dict[str, Any]:
        """Get summary statistics for a conversation"""
        
        messages = await self.get_conversation(conversation_id)
        
        if not messages:
            return None
        
        user_messages = [m for m in messages if m['role'] == 'user']
        assistant_messages = [m for m in messages if m['role'] == 'assistant']
        
        return {
            "conversation_id": conversation_id,
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "started_at": messages[0]['timestamp'] if messages else None,
            "last_updated": messages[-1]['timestamp'] if messages else None,
            "duration_minutes": self._calculate_duration(
                messages[0]['timestamp'],
                messages[-1]['timestamp']
            ) if len(messages) > 1 else 0
        }
    
    def _calculate_duration(self, start: str, end: str) -> float:
        """Calculate duration between two timestamps in minutes"""
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            return (end_dt - start_dt).total_seconds() / 60
        except:
            return 0.0
    
    async def health_check(self) -> bool:
        """Check if ChromaDB is accessible"""
        try:
            if self.collection:
                self.collection.count()
                return True
            return False
        except Exception as e:
            print(f"Conversation manager health check failed: {str(e)}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.chroma_client:
            print("✓ Conversation manager cleanup complete")