from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Pydantic Models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "llama3"
    temperature: float = 0.7
    conversation_id: Optional[str] = None

class ConversationCreate(BaseModel):
    title: Optional[str] = None
    model: str = "llama3"

class ConversationUpdate(BaseModel):
    title: Optional[str] = None

class RAGRequest(BaseModel):
    query: str
    model: str = "llama3"
    stream: bool = False
    temperature: float = 0.7
    top_k: int = 3
    conversation_id: Optional[str] = None


class EmbeddingRequest(BaseModel):
    text: str
    model: str = "llama3"
    
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    role: MessageRole
    content: str
    metadata: Optional[Dict[str, Any]] = None


class QueryRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: str
    context: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    response: str
    conversation_id: str
    metadata: Dict[str, Any]
    sources: List[Dict[str, Any]]