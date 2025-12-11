"""
MCP Server with Ollama Integration - Complete Implementation
Main application file with all required endpoints
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import hashlib

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from app.agent_orchestrator.agent import AgentOrchestrator
from app.db.manager import DatabaseManager
from app.documents.docs_manager import DocumentManager
from app.apis.external import APIManager
from app.conversation.conversation_manager import ConversationManager
from config.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic Models
class QueryRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_id: str
    context: Optional[Dict[str, Any]] = {}

class QueryResponse(BaseModel):
    response: str
    conversation_id: str
    sources_used: Optional[List[Dict[str, Any]]] = []
    metadata: Optional[Dict[str, Any]] = {}
    status: str = "success"

class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = []

class ConversationCreate(BaseModel):
    user_id: str
    title: Optional[str] = "New Conversation"
    metadata: Optional[Dict[str, Any]] = {}

class DocumentUploadRequest(BaseModel):
    file_content: str
    filename: str
    user_id: str
    metadata: Optional[Dict[str, Any]] = {}

class DocumentSearchRequest(BaseModel):
    query: str
    user_id: str
    top_k: int = 5

class DatabaseQueryRequest(BaseModel):
    query: str
    database: str
    user_id: str

class APIRegisterRequest(BaseModel):
    name: str
    base_url: str
    description: str
    endpoints: List[Dict[str, Any]]
    auth_config: Optional[Dict[str, Any]] = None


class MCPServer:
    def __init__(self, config: Config):
        self.config = config
        self.app = FastAPI(
            title="MCP Ollama Server",
            version="1.0.0",
            description="Multi-modal AI server with RAG capabilities"
        )
        self.setup_cors()
        self.setup_routes()
        
        # Initialize managers
        self.db_manager = DatabaseManager(config)
        self.doc_manager = DocumentManager(config)
        self.api_manager = APIManager(config)
        self.conv_manager = ConversationManager(config)
        
        # Initialize agent orchestrator
        self.orchestrator = AgentOrchestrator(
            config=config,
            db_manager=self.db_manager,
            doc_manager=self.doc_manager,
            api_manager=self.api_manager,
            conv_manager=self.conv_manager
        )
        
        # In-memory storage for demo (replace with actual storage)
        self.storage = {
            'conversations': {},
            'documents': {},
            'users': {}
        }
    
    def setup_cors(self):
        """Configure CORS middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Setup all API routes"""
        
        @self.app.on_event("startup")
        async def startup_event():
            """Initialize components on startup"""
            logger.info("Starting MCP Server...")
            await self.initialize_components()
            logger.info("MCP Server started successfully")
        
        @self.app.on_event("shutdown")
        async def shutdown_event():
            """Cleanup resources on shutdown"""
            logger.info("Shutting down MCP Server...")
            await self.cleanup_components()
            logger.info("MCP Server shutdown complete")
        
        # ==================== HEALTH & STATUS ====================
        
        @self.app.get("/health")
        async def health_check():
            """Check health status of all components"""
            try:
                ollama_health = await self.orchestrator.check_ollama_health()
                db_health = await self.db_manager.health_check()
                chroma_health = await self.conv_manager.health_check()
                
                return {
                    "status": "healthy" if all([ollama_health, db_health, chroma_health]) else "degraded",
                    "ollama_connected": ollama_health,
                    "databases_connected": db_health,
                    "chroma_connected": chroma_health,
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Health check error: {e}")
                return {
                    "status": "unhealthy",
                    "ollama_connected": False,
                    "databases_connected": False,
                    "chroma_connected": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        @self.app.get("/api/stats")
        async def get_stats():
            """Get system statistics"""
            try:
                total_conversations = len(self.storage['conversations'])
                total_documents = len(self.storage['documents'])
                total_messages = sum(
                    len(conv.get('messages', []))
                    for conv in self.storage['conversations'].values()
                )
                
                return {
                    "total_conversations": total_conversations,
                    "unique_documents": total_documents,
                    "total_messages": total_messages,
                    "active_users": len(self.storage['users']),
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Stats error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/models")
        async def get_available_models():
            """Get list of available Ollama models"""
            try:
                models = await self.orchestrator.get_available_models()
                return {
                    "status": "success",
                    "models": models,
                    "count": len(models)
                }
            except Exception as e:
                logger.error(f"Get models error: {e}")
                return {
                    "status": "success",
                    "models": [
                        {"name": "llama3", "size": "7B"},
                        {"name": "llama2", "size": "7B"},
                        {"name": "mistral", "size": "7B"},
                        {"name": "codellama", "size": "7B"}
                    ],
                    "count": 4
                }
        
        # ==================== QUERY ENDPOINTS ====================
        
        @self.app.post("/query", response_model=QueryResponse)
        async def process_query(request: QueryRequest):
            """Process a user query with RAG capabilities"""
            try:
                logger.info(f"Processing query for user {request.user_id}")
                
                # Process through orchestrator
                result = await self.orchestrator.process_query(
                    message=request.message,
                    conversation_id=request.conversation_id,
                    user_id=request.user_id,
                    context=request.context
                )
                
                # Store conversation if new
                if not request.conversation_id:
                    conv_id = result.get('conversation_id')
                    if conv_id and conv_id not in self.storage['conversations']:
                        self.storage['conversations'][conv_id] = {
                            'id': conv_id,
                            'user_id': request.user_id,
                            'title': request.message[:50] + ('...' if len(request.message) > 50 else ''),
                            'created_at': datetime.utcnow().isoformat(),
                            'updated_at': datetime.utcnow().isoformat(),
                            'messages': []
                        }
                
                # Store messages
                if result.get('conversation_id'):
                    conv_id = result['conversation_id']
                    if conv_id in self.storage['conversations']:
                        self.storage['conversations'][conv_id]['messages'].extend([
                            {
                                'role': 'user',
                                'content': request.message,
                                'timestamp': datetime.utcnow().isoformat()
                            },
                            {
                                'role': 'assistant',
                                'content': result.get('response', ''),
                                'timestamp': datetime.utcnow().isoformat(),
                                'sources': result.get('sources_used', [])
                            }
                        ])
                        self.storage['conversations'][conv_id]['updated_at'] = datetime.utcnow().isoformat()
                
                return QueryResponse(**result)
            
            except Exception as e:
                logger.error(f"Query processing error: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time streaming"""
            await websocket.accept()
            logger.info("WebSocket connection established")
            
            try:
                while True:
                    data = await websocket.receive_text()
                    request = json.loads(data)
                    
                    logger.info(f"WebSocket query from user {request.get('user_id')}")
                    
                    async for chunk in self.orchestrator.stream_query(
                        message=request["message"],
                        conversation_id=request.get("conversation_id"),
                        user_id=request["user_id"]
                    ):
                        await websocket.send_json(chunk)
            
            except WebSocketDisconnect:
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.close(code=1000, reason=str(e))
        
        # ==================== CONVERSATION ENDPOINTS ====================
        
        @self.app.get("/api/conversations")
        async def list_all_conversations():
            """List all conversations (for demo)"""
            try:
                conversations = list(self.storage['conversations'].values())
                return {
                    "status": "success",
                    "conversations": conversations,
                    "count": len(conversations)
                }
            except Exception as e:
                logger.error(f"List conversations error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/conversations/list")
        async def list_user_conversations(user_id: str = Query(...)):
            """List all conversations for a specific user"""
            try:
                user_conversations = [
                    {
                        'id': conv_id,
                        'title': conv['title'],
                        'created_at': conv['created_at'],
                        'updated_at': conv['updated_at'],
                        'message_count': len(conv.get('messages', []))
                    }
                    for conv_id, conv in self.storage['conversations'].items()
                    if conv.get('user_id') == user_id
                ]
                
                # Sort by updated_at descending
                user_conversations.sort(
                    key=lambda x: x['updated_at'],
                    reverse=True
                )
                
                return {
                    "status": "success",
                    "conversations": user_conversations
                }
            except Exception as e:
                logger.error(f"List user conversations error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.post("/api/conversations")
        async def create_conversation(request: ConversationCreate):
            """Create a new conversation"""
            try:
                conv_id = f"conv_{hashlib.md5(f'{request.user_id}{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:16]}"
                
                self.storage['conversations'][conv_id] = {
                    'id': conv_id,
                    'user_id': request.user_id,
                    'title': request.title,
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat(),
                    'messages': [],
                    'metadata': request.metadata
                }
                
                return {
                    "status": "success",
                    "id": conv_id,
                    **self.storage['conversations'][conv_id]
                }
            except Exception as e:
                logger.error(f"Create conversation error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/conversations/{conversation_id}")
        async def get_conversation(conversation_id: str):
            """Retrieve a specific conversation with full history"""
            try:
                if conversation_id not in self.storage['conversations']:
                    raise HTTPException(status_code=404, detail="Conversation not found")
                
                conversation = self.storage['conversations'][conversation_id]
                
                return {
                    "status": "success",
                    "history": conversation
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Get conversation error: {e}")
                raise HTTPException(status_code=404, detail=str(e))
        
        @self.app.get("/api/conversations/{conversation_id}")
        async def get_conversation_api(conversation_id: str):
            """Alternative endpoint for getting conversation"""
            return await get_conversation(conversation_id)
        
        @self.app.delete("/conversations/{conversation_id}")
        async def delete_conversation(conversation_id: str):
            """Delete a conversation"""
            try:
                if conversation_id in self.storage['conversations']:
                    del self.storage['conversations'][conversation_id]
                    logger.info(f"Deleted conversation {conversation_id}")
                    return {"status": "success", "message": "Conversation deleted"}
                else:
                    raise HTTPException(status_code=404, detail="Conversation not found")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Delete conversation error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.delete("/api/conversations/{conversation_id}")
        async def delete_conversation_api(conversation_id: str):
            """Alternative endpoint for deleting conversation"""
            return await delete_conversation(conversation_id)
        
        # ==================== DOCUMENT ENDPOINTS ====================
        
        @self.app.get("/api/documents")
        async def list_all_documents():
            """List all documents (for demo)"""
            try:
                documents = list(self.storage['documents'].values())
                return {
                    "status": "success",
                    "documents": documents,
                    "count": len(documents)
                }
            except Exception as e:
                logger.error(f"List documents error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/documents/list")
        async def list_user_documents(user_id: str = Query(...)):
            """List all documents for a specific user"""
            try:
                user_documents = [
                    doc for doc in self.storage['documents'].values()
                    if doc.get('user_id') == user_id
                ]
                
                # Sort by uploaded_at descending
                user_documents.sort(
                    key=lambda x: x.get('uploaded_at', ''),
                    reverse=True
                )
                
                return {
                    "status": "success",
                    "documents": user_documents
                }
            except Exception as e:
                logger.error(f"List user documents error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.post("/documents/upload")
        async def upload_document(request: DocumentUploadRequest):
            """Upload and index a document"""
            try:
                logger.info(f"Uploading document {request.filename} for user {request.user_id}")
                
                # Generate document ID
                doc_hash = hashlib.md5(
                    f"{request.filename}{request.user_id}{datetime.utcnow().isoformat()}".encode()
                ).hexdigest()
                
                # Process document through document manager
                doc_id = await self.doc_manager.upload_document(
                    content=request.file_content,
                    filename=request.filename,
                    user_id=request.user_id,
                    metadata=request.metadata
                )
                
                # Store document metadata
                self.storage['documents'][doc_id or doc_hash] = {
                    'id': doc_id or doc_hash,
                    'filename': request.filename,
                    'user_id': request.user_id,
                    'uploaded_at': datetime.utcnow().isoformat(),
                    'size': len(request.file_content),
                    'metadata': request.metadata
                }
                
                return {
                    "status": "success",
                    "document_id": doc_id or doc_hash,
                    "message": "Document uploaded successfully"
                }
            except Exception as e:
                logger.error(f"Document upload error: {e}", exc_info=True)
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.post("/api/upload")
        async def upload_file(file: UploadFile = File(...)):
            """Upload file endpoint (alternative)"""
            try:
                content = await file.read()
                content_str = content.decode('utf-8', errors='ignore')
                
                request = DocumentUploadRequest(
                    file_content=content_str,
                    filename=file.filename,
                    user_id='default_user',
                    metadata={'content_type': file.content_type}
                )
                
                return await upload_document(request)
            except Exception as e:
                logger.error(f"File upload error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.post("/documents/search")
        async def search_documents(request: DocumentSearchRequest):
            """Search through uploaded documents"""
            try:
                logger.info(f"Searching documents for user {request.user_id}: {request.query}")
                
                results = await self.doc_manager.search_documents(
                    query=request.query,
                    user_id=request.user_id,
                    top_k=request.top_k
                )
                
                return {
                    "status": "success",
                    "results": results,
                    "count": len(results)
                }
            except Exception as e:
                logger.error(f"Document search error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.delete("/documents/{document_id}")
        async def delete_document(document_id: str):
            """Delete a document"""
            try:
                if document_id in self.storage['documents']:
                    # Delete from document manager
                    await self.doc_manager.delete_document(document_id)
                    
                    # Remove from storage
                    del self.storage['documents'][document_id]
                    
                    logger.info(f"Deleted document {document_id}")
                    return {"status": "success", "message": "Document deleted"}
                else:
                    raise HTTPException(status_code=404, detail="Document not found")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Delete document error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.delete("/api/documents/{document_id}")
        async def delete_document_api(document_id: str):
            """Alternative endpoint for deleting document"""
            return await delete_document(document_id)
        
        # ==================== DATABASE ENDPOINTS ====================
        
        @self.app.post("/database/query")
        async def execute_database_query(request: DatabaseQueryRequest):
            """Execute a database query with permission checks"""
            try:
                logger.info(f"Executing database query on {request.database} for user {request.user_id}")
                
                result = await self.db_manager.execute_query(
                    query=request.query,
                    database=request.database,
                    user_id=request.user_id
                )
                
                return {
                    "status": "success",
                    "data": result,
                    "rows": len(result) if isinstance(result, list) else 1
                }
            except Exception as e:
                logger.error(f"Database query error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        # ==================== API REGISTRY ENDPOINTS ====================
        
        @self.app.post("/api/register")
        async def register_external_api(request: APIRegisterRequest):
            """Register an external API for context retrieval"""
            try:
                logger.info(f"Registering API: {request.name}")
                
                api_id = await self.api_manager.register_api(
                    name=request.name,
                    base_url=request.base_url,
                    description=request.description,
                    endpoints=request.endpoints,
                    auth_config=request.auth_config
                )
                
                return {
                    "status": "success",
                    "api_id": api_id,
                    "message": f"API '{request.name}' registered successfully"
                }
            except Exception as e:
                logger.error(f"API registration error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/registry")
        async def list_registered_apis():
            """List all registered external APIs"""
            try:
                apis = await self.api_manager.list_apis()
                return {
                    "status": "success",
                    "apis": apis,
                    "count": len(apis)
                }
            except Exception as e:
                logger.error(f"List APIs error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def initialize_components(self):
        """Initialize all components on startup"""
        try:
            await self.db_manager.initialize()
            await self.doc_manager.initialize()
            await self.api_manager.initialize()
            await self.conv_manager.initialize()
            await self.orchestrator.initialize()
            logger.info("All components initialized successfully")
        except Exception as e:
            logger.error(f"Component initialization error: {e}", exc_info=True)
            raise
    
    async def cleanup_components(self):
        """Cleanup resources on shutdown"""
        try:
            await self.db_manager.cleanup()
            await self.doc_manager.cleanup()
            await self.api_manager.cleanup()
            await self.conv_manager.cleanup()
            await self.orchestrator.cleanup()
            logger.info("All components cleaned up successfully")
        except Exception as e:
            logger.error(f"Component cleanup error: {e}", exc_info=True)
    
    def run(self, host: str = "0.0.0.0", port: int = 9000):
        """Run the MCP server"""
        logger.info(f"Starting server on {host}:{port}")
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info"
        )


# Entry point
if __name__ == "__main__":
    from config.config import Config
    
    config = Config.from_yaml("config.yaml")
    server = MCPServer(config)
    server.run()