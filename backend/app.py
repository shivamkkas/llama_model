"""
Backend API for Ollama UI with Advanced RAG capabilities
FastAPI + ChromaDB + LangChain
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import os
from pathlib import Path
import chromadb
from chromadb.config import Settings
import hashlib
import json

app = FastAPI(title="Ollama RAG API", version="1.0.0")

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

# Persistent client
chroma_client = chromadb.PersistentClient(path="./vector_db")

# Get or create collection
collection = chroma_client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"}
)

# Models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "llama3"
    temperature: float = 0.7

class RAGRequest(BaseModel):
    query: str
    model: str = "llama3"
    temperature: float = 0.7
    top_k: int = 3

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

# Routes
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
            return {
                "status": "healthy",
                "ollama": "connected",
                "models": response.json().get("models", [])
            }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Ollama not available: {str(e)}")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat endpoint"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": request.model,
                    "messages": [msg.dict() for msg in request.messages],
                    "stream": False,
                    "options": {"temperature": request.temperature}
                },
                timeout=120.0
            )
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process document for RAG"""
    try:
        # Read file content
        content = await file.read()
        text = content.decode('utf-8')
        
        # Create chunks
        chunks = chunk_text(text)
        
        # Generate unique IDs
        file_hash = hashlib.md5(file.filename.encode()).hexdigest()
        
        # Get embeddings and store in ChromaDB
        for i, chunk in enumerate(chunks):
            embedding = await get_embedding(chunk)
            chunk_id = f"{file_hash}_{i}"
            
            collection.add(
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "filename": file.filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }],
                ids=[chunk_id]
            )
        
        return {
            "filename": file.filename,
            "chunks": len(chunks),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/query")
async def rag_query(request: RAGRequest):
    """RAG query endpoint"""
    try:
        # Get query embedding
        query_embedding = await get_embedding(request.query)
        
        # Search similar documents
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.top_k
        )
        
        # Extract context
        context_chunks = results['documents'][0] if results['documents'] else []
        context = "\n\n".join(context_chunks)
        
        # Generate prompt with context
        prompt = f"""Context from documents:
{context}

Question: {request.query}

Answer the question based on the context provided above. If the context doesn't contain relevant information, say o."""
        
        # Generate response
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
            
            return {
                "response": result["response"],
                "context": context_chunks,
                "sources": results['metadatas'][0] if results['metadatas'] else [],
                "num_sources": len(context_chunks)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents")
async def list_documents():
    """List all documents in the vector store"""
    try:
        all_docs = collection.get()
        
        # Group by filename
        docs_by_file = {}
        for metadata in all_docs['metadatas']:
            filename = metadata['filename']
            if filename not in docs_by_file:
                docs_by_file[filename] = {
                    "filename": filename,
                    "chunks": 0
                }
            docs_by_file[filename]["chunks"] += 1
        
        return {"documents": list(docs_by_file.values())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    """Delete a document from the vector store"""
    try:
        # Get all documents with this filename
        all_docs = collection.get()
        ids_to_delete = []
        
        for i, metadata in enumerate(all_docs['metadatas']):
            if metadata['filename'] == filename:
                ids_to_delete.append(all_docs['ids'][i])
        
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            return {"status": "deleted", "chunks_removed": len(ids_to_delete)}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/embeddings")
async def create_embedding(request: EmbeddingRequest):
    """Generate embeddings for text"""
    try:
        embedding = await get_embedding(request.text, request.model)
        return {
            "embedding": embedding,
            "dimension": len(embedding)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)