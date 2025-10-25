"""
Backend API for Ollama UI with Advanced RAG capabilities
FastAPI + ChromaDB (for all storage) - Vector DB for everything
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
import os
from pathlib import Path
import chromadb
import hashlib
import json
import uuid

# FastAPI app
app = FastAPI(title="Ollama RAG API - Vector DB Storage", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11435")
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Persistent ChromaDB client
chroma_client = chromadb.PersistentClient(path="./vector_db")

# Collections for different data types
documents_collection = chroma_client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine", "description": "Document chunks with embeddings"}
)

conversations_collection = chroma_client.get_or_create_collection(
    name="conversations",
    metadata={"hnsw:space": "cosine", "description": "Conversation metadata"}
)

messages_collection = chroma_client.get_or_create_collection(
    name="messages",
    metadata={"hnsw:space": "cosine", "description": "Chat messages with embeddings"}
)

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
    temperature: float = 0.7
    top_k: int = 3
    conversation_id: Optional[str] = None

class EmbeddingRequest(BaseModel):
    text: str
    model: str = "llama3"

# Helper functions
async def get_embedding(text: str, model: str = "llama3") -> List[float]:
    """Get embeddings from Ollama"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=30.0
        )
        return response.json()["embedding"]

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks"""
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
    
    return chunks

def generate_conversation_title(first_message: str) -> str:
    """Generate a title from the first message"""
    title = first_message[:50]
    if len(first_message) > 50:
        title += "..."
    return title

def get_timestamp() -> str:
    """Get ISO format timestamp"""
    return datetime.utcnow().isoformat()

# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
            
            # Get collection stats
            docs_count = documents_collection.count()
            convs_count = conversations_collection.count()
            msgs_count = messages_collection.count()
            
            return {
                "status": "healthy",
                "ollama": "connected",
                "vector_db": "connected",
                "collections": {
                    "documents": docs_count,
                    "conversations": convs_count,
                    "messages": msgs_count
                },
                "models": response.json().get("models", [])
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not available: {str(e)}")

# Conversation Management Routes
@app.post("/api/conversations")
async def create_conversation(conv: ConversationCreate):
    """Create a new conversation"""
    try:
        conversation_id = str(uuid.uuid4())
        timestamp = get_timestamp()
        
        # Create a dummy embedding for conversation metadata
        # We use a simple text representation for searchability
        conv_text = f"Conversation: {conv.title or 'New Chat'}"
        embedding = await get_embedding(conv_text, conv.model)
        
        conversations_collection.add(
            ids=[conversation_id],
            embeddings=[embedding],
            documents=[conv_text],
            metadatas=[{
                "conversation_id": conversation_id,
                "title": conv.title or "New Chat",
                "model": conv.model,
                "created_at": timestamp,
                "updated_at": timestamp,
                "message_count": "0"
            }]
        )
        
        return {
            "id": conversation_id,
            "title": conv.title or "New Chat",
            "model": conv.model,
            "created_at": timestamp,
            "message_count": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations")
async def list_conversations(limit: int = 50):
    """List all conversations"""
    try:
        # Get all conversations
        result = conversations_collection.get()
        
        if not result["ids"]:
            return {"conversations": [], "total": 0}
        
        # Sort by updated_at (most recent first)
        conversations = []
        for i, conv_id in enumerate(result["ids"]):
            metadata = result["metadatas"][i]
            conversations.append({
                "id": conv_id,
                "title": metadata.get("title", "New Chat"),
                "model": metadata.get("model", "llama3"),
                "created_at": metadata.get("created_at"),
                "updated_at": metadata.get("updated_at"),
                "message_count": int(metadata.get("message_count", 0))
            })
        
        # Sort by updated_at descending
        conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        
        return {
            "conversations": conversations[:limit],
            "total": len(conversations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all messages"""
    try:
        # Get conversation metadata
        conv_result = conversations_collection.get(
            ids=[conversation_id]
        )
        
        if not conv_result["ids"]:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conv_metadata = conv_result["metadatas"][0]
        
        # Get all messages for this conversation
        messages_result = messages_collection.get(
            where={"conversation_id": conversation_id}
        )
        
        # Sort messages by timestamp
        messages = []
        if messages_result["ids"]:
            for i, msg_id in enumerate(messages_result["ids"]):
                metadata = messages_result["metadatas"][i]
                messages.append({
                    "id": msg_id,
                    "role": metadata.get("role"),
                    "content": metadata.get("content"),
                    "timestamp": metadata.get("timestamp")
                })
            
            messages.sort(key=lambda x: x["timestamp"])
        
        return {
            "id": conversation_id,
            "title": conv_metadata.get("title"),
            "model": conv_metadata.get("model"),
            "created_at": conv_metadata.get("created_at"),
            "updated_at": conv_metadata.get("updated_at"),
            "messages": messages
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, update: ConversationUpdate):
    """Update conversation details"""
    try:
        # Get existing conversation
        conv_result = conversations_collection.get(ids=[conversation_id])
        
        if not conv_result["ids"]:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        old_metadata = conv_result["metadatas"][0]
        
        # Update metadata
        new_metadata = old_metadata.copy()
        if update.title:
            new_metadata["title"] = update.title
        new_metadata["updated_at"] = get_timestamp()
        
        # Update conversation text for embedding
        conv_text = f"Conversation: {new_metadata['title']}"
        embedding = await get_embedding(conv_text, old_metadata["model"])
        
        # Update in ChromaDB
        conversations_collection.update(
            ids=[conversation_id],
            embeddings=[embedding],
            documents=[conv_text],
            metadatas=[new_metadata]
        )
        
        return {
            "id": conversation_id,
            "title": new_metadata["title"],
            "updated_at": new_metadata["updated_at"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages"""
    try:
        # Check if conversation exists
        conv_result = conversations_collection.get(ids=[conversation_id])
        if not conv_result["ids"]:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Delete all messages in this conversation
        messages_result = messages_collection.get(
            where={"conversation_id": conversation_id}
        )
        
        if messages_result["ids"]:
            messages_collection.delete(ids=messages_result["ids"])
        
        # Delete conversation
        conversations_collection.delete(ids=[conversation_id])
        
        return {
            "status": "deleted",
            "conversation_id": conversation_id,
            "messages_deleted": len(messages_result["ids"]) if messages_result["ids"] else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint with conversation storage"""
    try:
        # If conversation_id is provided, update it; otherwise create new
        if not request.conversation_id:
            # Auto-create conversation
            first_user_msg = next((m.content for m in request.messages if m.role == "user"), "New Chat")
            title = generate_conversation_title(first_user_msg)
            
            conv_create = ConversationCreate(title=title, model=request.model)
            conv_response = await create_conversation(conv_create)
            conversation_id = conv_response["id"]
        else:
            conversation_id = request.conversation_id
        
        # Store user message
        user_message = request.messages[-1]  # Last message is typically the new user message
        if user_message.role == "user":
            message_id = str(uuid.uuid4())
            timestamp = get_timestamp()
            
            # Get embedding for semantic search
            msg_embedding = await get_embedding(user_message.content, request.model)
            
            messages_collection.add(
                ids=[message_id],
                embeddings=[msg_embedding],
                documents=[user_message.content],
                metadatas=[{
                    "conversation_id": conversation_id,
                    "role": "user",
                    "content": user_message.content,
                    "timestamp": timestamp
                }]
            )
        
        # Call Ollama
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": request.model,
                    "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
                    "stream": False,
                    "options": {"temperature": request.temperature}
                },
                timeout=120.0
            )
            result = response.json()
        
        # Store assistant message
        assistant_content = result["message"]["content"]
        assistant_msg_id = str(uuid.uuid4())
        timestamp = get_timestamp()
        
        assistant_embedding = await get_embedding(assistant_content, request.model)
        
        messages_collection.add(
            ids=[assistant_msg_id],
            embeddings=[assistant_embedding],
            documents=[assistant_content],
            metadatas=[{
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": assistant_content,
                "timestamp": timestamp
            }]
        )
        
        # Update conversation metadata
        conv_result = conversations_collection.get(ids=[conversation_id])
        if conv_result["ids"]:
            conv_metadata = conv_result["metadatas"][0]
            conv_metadata["updated_at"] = timestamp
            conv_metadata["message_count"] = str(int(conv_metadata.get("message_count", 0)) + 2)
            
            conv_text = f"Conversation: {conv_metadata['title']}"
            conv_embedding = await get_embedding(conv_text, request.model)
            
            conversations_collection.update(
                ids=[conversation_id],
                embeddings=[conv_embedding],
                documents=[conv_text],
                metadatas=[conv_metadata]
            )
        
        return {
            "message": result["message"],
            "conversation_id": conversation_id,
            "model": result.get("model"),
            "done": result.get("done")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# Continuation of main.py - Document and RAG endpoints

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process document for RAG - stored in vector DB"""
    try:
        # Read file content
        content = await file.read()
        text = content.decode('utf-8')
        
        # Generate unique file hash
        file_hash = hashlib.md5(file.filename.encode()).hexdigest()
        
        # Check if document already exists
        existing_docs = documents_collection.get(
            where={"file_hash": file_hash}
        )
        
        if existing_docs["ids"]:
            raise HTTPException(
                status_code=409,
                detail=f"Document '{file.filename}' already exists. Delete it first to re-upload."
            )
        
        # Create chunks
        chunks = chunk_text(text)
        timestamp = get_timestamp()
        
        # Store each chunk with embedding
        chunk_ids = []
        embeddings_list = []
        documents_list = []
        metadatas_list = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{file_hash}_{i}"
            chunk_ids.append(chunk_id)
            
            # Get embedding
            embedding = await get_embedding(chunk)
            embeddings_list.append(embedding)
            documents_list.append(chunk)
            
            # Metadata for each chunk
            metadatas_list.append({
                "filename": file.filename,
                "file_hash": file_hash,
                "chunk_index": str(i),
                "total_chunks": str(len(chunks)),
                "upload_date": timestamp,
                "file_size": str(len(content)),
                "content_type": "text/plain",
                "chunk_content": chunk  # Store full content in metadata too
            })
        
        # Add all chunks to collection
        documents_collection.add(
            ids=chunk_ids,
            embeddings=embeddings_list,
            documents=documents_list,
            metadatas=metadatas_list
        )
        
        return {
            "filename": file.filename,
            "file_hash": file_hash,
            "chunks": len(chunks),
            "file_size": len(content),
            "upload_date": timestamp,
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/query")
async def rag_query(request: RAGRequest):
    """RAG query endpoint - retrieves from vector DB and generates response"""
    try:
        # Get query embedding
        query_embedding = await get_embedding(request.query, request.model)
        
        # Search similar documents in vector DB
        results = documents_collection.query(
            query_embeddings=[query_embedding],
            n_results=request.top_k,
            where={"filename": {"$ne": ""}}  # Only get document chunks
        )
        
        # Extract context
        context_chunks = results['documents'][0] if results['documents'] else []
        context = "\n\n".join(context_chunks)
        
        if not context:
            return {
                "response": "I don't have any relevant documents to answer this question. Please upload documents first.",
                "context": [],
                "sources": [],
                "num_sources": 0
            }
        
        # Generate prompt with context
        prompt = f"""Context from documents:
{context}

Question: {request.query}

Answer the question based on the context provided above. If the context doesn't contain relevant information, say so."""
        
        # Generate response using Ollama
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": request.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": request.temperature}
                },
                timeout=120.0
            )
            
            result = response.json()
        
        # If conversation_id provided, store the RAG interaction
        if request.conversation_id:
            timestamp = get_timestamp()
            
            # Store user query
            query_msg_id = str(uuid.uuid4())
            query_embedding = await get_embedding(request.query, request.model)
            
            messages_collection.add(
                ids=[query_msg_id],
                embeddings=[query_embedding],
                documents=[request.query],
                metadatas=[{
                    "conversation_id": request.conversation_id,
                    "role": "user",
                    "content": request.query,
                    "timestamp": timestamp,
                    "type": "rag_query"
                }]
            )
            
            # Store assistant response
            response_msg_id = str(uuid.uuid4())
            response_embedding = await get_embedding(result["response"], request.model)
            
            messages_collection.add(
                ids=[response_msg_id],
                embeddings=[response_embedding],
                documents=[result["response"]],
                metadatas=[{
                    "conversation_id": request.conversation_id,
                    "role": "assistant",
                    "content": result["response"],
                    "timestamp": timestamp,
                    "type": "rag_response",
                    "sources_used": str(len(context_chunks))
                }]
            )
            
            # Update conversation
            conv_result = conversations_collection.get(ids=[request.conversation_id])
            if conv_result["ids"]:
                conv_metadata = conv_result["metadatas"][0]
                conv_metadata["updated_at"] = timestamp
                conv_metadata["message_count"] = str(int(conv_metadata.get("message_count", 0)) + 2)
                
                conv_text = f"Conversation: {conv_metadata['title']}"
                conv_embedding = await get_embedding(conv_text, request.model)
                
                conversations_collection.update(
                    ids=[request.conversation_id],
                    embeddings=[conv_embedding],
                    documents=[conv_text],
                    metadatas=[conv_metadata]
                )
        
        return {
            "response": result["response"],
            "context": context_chunks,
            "sources": results['metadatas'][0] if results['metadatas'] else [],
            "num_sources": len(context_chunks),
            "conversation_id": request.conversation_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents")
async def list_documents():
    """List all documents in the vector store"""
    try:
        # Get all document chunks
        all_docs = documents_collection.get()
        
        if not all_docs["ids"]:
            return {"documents": [], "total": 0}
        
        # Group by file_hash
        docs_by_hash = {}
        for metadata in all_docs['metadatas']:
            file_hash = metadata.get('file_hash')
            if not file_hash:
                continue
                
            if file_hash not in docs_by_hash:
                docs_by_hash[file_hash] = {
                    "filename": metadata['filename'],
                    "file_hash": file_hash,
                    "chunks": 0,
                    "file_size": int(metadata.get('file_size', 0)),
                    "upload_date": metadata.get('upload_date'),
                    "content_type": metadata.get('content_type', 'text/plain')
                }
            docs_by_hash[file_hash]["chunks"] += 1
        
        # Convert to list and sort by upload date
        documents_list = list(docs_by_hash.values())
        documents_list.sort(key=lambda x: x["upload_date"], reverse=True)
        
        return {
            "documents": documents_list,
            "total": len(documents_list)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents/{file_hash}")
async def get_document_details(file_hash: str):
    """Get detailed information about a specific document"""
    try:
        # Get all chunks for this document
        doc_chunks = documents_collection.get(
            where={"file_hash": file_hash}
        )
        
        if not doc_chunks["ids"]:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get metadata from first chunk
        first_metadata = doc_chunks['metadatas'][0]
        
        # Reconstruct full content from chunks
        chunks_data = []
        for i, chunk_id in enumerate(doc_chunks["ids"]):
            metadata = doc_chunks['metadatas'][i]
            chunks_data.append({
                "chunk_id": chunk_id,
                "chunk_index": int(metadata.get('chunk_index', 0)),
                "content": doc_chunks['documents'][i],
                "content_preview": doc_chunks['documents'][i][:200] + "..." if len(doc_chunks['documents'][i]) > 200 else doc_chunks['documents'][i]
            })
        
        # Sort by chunk index
        chunks_data.sort(key=lambda x: x["chunk_index"])
        
        return {
            "filename": first_metadata['filename'],
            "file_hash": file_hash,
            "total_chunks": len(chunks_data),
            "file_size": int(first_metadata.get('file_size', 0)),
            "upload_date": first_metadata.get('upload_date'),
            "content_type": first_metadata.get('content_type'),
            "chunks": chunks_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/{file_hash}")
async def delete_document(file_hash: str):
    """Delete a document from the vector store"""
    try:
        # Get all chunks with this file_hash
        doc_chunks = documents_collection.get(
            where={"file_hash": file_hash}
        )
        
        if not doc_chunks["ids"]:
            raise HTTPException(status_code=404, detail="Document not found")
        
        filename = doc_chunks['metadatas'][0]['filename']
        
        # Delete all chunks
        documents_collection.delete(ids=doc_chunks["ids"])
        
        return {
            "status": "deleted",
            "filename": filename,
            "file_hash": file_hash,
            "chunks_removed": len(doc_chunks["ids"])
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/embeddings")
async def create_embedding(request: EmbeddingRequest):
    """Generate embeddings for text"""
    try:
        embedding = await get_embedding(request.text, request.model)
        return {
            "embedding": embedding,
            "dimension": len(embedding),
            "model": request.model
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search/messages")
async def search_messages(query: str, conversation_id: Optional[str] = None, limit: int = 10):
    """Semantic search across all messages"""
    try:
        # Get query embedding
        query_embedding = await get_embedding(query)
        
        # Build where clause
        where_clause = {}
        if conversation_id:
            where_clause["conversation_id"] = conversation_id
        
        # Search messages
        results = messages_collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_clause if where_clause else None
        )
        
        # Format results
        messages = []
        if results["ids"]:
            for i, msg_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                messages.append({
                    "id": msg_id,
                    "conversation_id": metadata.get("conversation_id"),
                    "role": metadata.get("role"),
                    "content": metadata.get("content"),
                    "timestamp": metadata.get("timestamp"),
                    "relevance_score": 1 - results["distances"][0][i] if results.get("distances") else None
                })
        
        return {
            "query": query,
            "results": messages,
            "total": len(messages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_statistics():
    """Get overall statistics from vector DB"""
    try:
        docs_count = documents_collection.count()
        convs_count = conversations_collection.count()
        msgs_count = messages_collection.count()
        
        # Get unique document count
        all_docs = documents_collection.get()
        unique_files = set()
        if all_docs["metadatas"]:
            for metadata in all_docs["metadatas"]:
                if metadata.get("file_hash"):
                    unique_files.add(metadata["file_hash"])
        
        return {
            "total_document_chunks": docs_count,
            "unique_documents": len(unique_files),
            "total_conversations": convs_count,
            "total_messages": msgs_count,
            "storage_type": "chromadb_vector_store"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)