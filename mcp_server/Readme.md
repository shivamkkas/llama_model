# MCP Server with Ollama Integration

A comprehensive Model Context Protocol (MCP) server that integrates Ollama for local LLM inference, with support for database querying, document search, external API calling, and conversation history management.

## Features

- 🤖 **Ollama Integration**: Run local LLMs (Llama2, Llama3, Mistral, etc.) in Docker
- 🗄️ **Multi-Database Support**: SQLite and PostgreSQL with table-level permissions
- 📄 **Document Management**: Upload, index, and semantically search documents (PDF, DOCX, TXT, MD, JSON, CSV)
- 🌐 **External API Integration**: Register and call external APIs with caching
- 💬 **Conversation History**: Store and retrieve conversation history using ChromaDB
- 🧠 **Intelligent Routing**: LangGraph-based agent orchestrator that decides which handler to use
- 🔒 **Permission Management**: Fine-grained table and document access control
- 🐳 **Fully Dockerized**: Complete Docker Compose setup with all dependencies

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Server (FastAPI)                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Agent Orchestrator (LangGraph)                │  │
│  │  - Intent Classification                              │  │
│  │  - Query Routing                                      │  │
│  │  - Response Generation                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│      ┌──────────────┬───┴────┬──────────────┬─────────┐    │
│      │              │        │              │         │    │
│  ┌───▼───┐     ┌───▼───┐ ┌──▼──┐     ┌────▼───┐  ┌──▼──┐ │
│  │  DB   │     │  Doc  │ │ API │     │  Conv  │  │Ollama│ │
│  │Manager│     │Manager│ │Mgr  │     │Manager │  │ LLM  │ │
│  └───┬───┘     └───┬───┘ └──┬──┘     └────┬───┘  └─────┘ │
└──────┼─────────────┼────────┼─────────────┼──────────────┘
       │             │        │             │
   ┌───▼───┐    ┌───▼────┐   │        ┌────▼─────┐
   │SQLite │    │ChromaDB│   │        │ChromaDB  │
   │Postgres    │(Docs)  │   │        │(Convs)   │
   └───────┘    └────────┘   │        └──────────┘
                          ┌───▼────┐
                          │External│
                          │  APIs  │
                          └────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- At least 8GB RAM (for Ollama models)
- 10GB free disk space

### Installation

1. **Clone or create the project structure:**

```bash
mkdir mcp-server && cd mcp-server
```

2. **Copy all the provided files to the project directory:**

- `server.py` - Main server application
- `config.py` - Configuration management
- `agent_orchestrator.py` - LangGraph-based routing
- `database_manager.py` - Database operations
- `document_manager.py` - Document handling
- `api_manager.py` - External API management
- `conversation_manager.py` - Conversation history
- `docker-compose.yml` - Docker setup
- `Dockerfile` - Container definition
- `requirements.txt` - Python dependencies
- `config.yaml` - Server configuration
- `init_postgres.sql` - PostgreSQL initialization
- `setup.sh` - Setup script

3. **Run the setup script:**

```bash
chmod +x setup.sh
./setup.sh
```

This will:
- Create necessary directories
- Build Docker images
- Start all services
- Pull the Ollama model
- Initialize databases

4. **Verify installation:**

```bash
curl http://localhost:8000/health
```

## Usage

### 1. Query Database

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me all customers who made transactions over $100",
    "user_id": "user_1"
  }'
```

### 2. Upload and Search Documents

```bash
# Upload a document
curl -X POST http://localhost:8000/documents/upload \
  -H "Content-Type: application/json" \
  -d '{
    "file_content": "This is my document content...",
    "filename": "mydoc.txt",
    "user_id": "user_1",
    "metadata": {"category": "research"}
  }'

# Search documents
curl -X POST http://localhost:8000/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find information about machine learning",
    "user_id": "user_1",
    "top_k": 5
  }'
```

### 3. Register and Call External APIs

```bash
# Register an API
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "weather_api",
    "base_url": "https://api.weather.com",
    "description": "Weather data API",
    "endpoints": [
      {
        "path": "/current",
        "method": "GET",
        "description": "Get current weather"
      }
    ],
    "auth_config": {
      "type": "api_key",
      "header_name": "X-API-Key",
      "api_key": "your-api-key"
    }
  }'

# Call the API through MCP
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the current weather in New York?",
    "user_id": "user_1"
  }'
```

### 4. Manage Conversations

```bash
# Get conversation history
curl http://localhost:8000/conversations/{conversation_id}

# List all conversations for a user
curl http://localhost:8000/conversations/list?user_id=user_1
```

### 5. WebSocket Streaming

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    message: "Tell me about the latest transactions",
    user_id: "user_1"
  }));
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log(response);
};
```

## Configuration

Edit `config.yaml` to customize:

### Ollama Settings

```yaml
ollama:
  host: "http://ollama:11434"
  model: "llama2"  # Options: llama2, llama3, mistral, codellama, etc.
  temperature: 0.7
  max_tokens: 4096
```

### Database Permissions

```yaml
databases:
  postgresql:
    table_permissions:
      customers: []  # Empty = all users
      transactions: ["user_1", "admin"]  # Restricted
      sensitive_data: ["admin"]  # Admin only
```

### Document Settings

```yaml
documents:
  chunk_size: 1000
  chunk_overlap: 200
  supported_formats: ["txt", "pdf", "docx", "md", "json", "csv"]
```

## API Endpoints

### Core Endpoints

- `POST /query` - Main query endpoint (auto-routes to appropriate handler)
- `GET /health` - Health check for all services

### Database Endpoints

- `POST /database/query` - Direct database query execution
- `GET /database/tables` - List accessible tables

### Document Endpoints

- `POST /documents/upload` - Upload and index a document
- `POST /documents/search` - Semantic search through documents
- `GET /documents/{doc_id}` - Retrieve a specific document
- `DELETE /documents/{doc_id}` - Delete a document

### API Management

- `POST /api/register` - Register an external API
- `GET /api/list` - List registered APIs
- `DELETE /api/{api_id}` - Remove an API

### Conversation Endpoints

- `GET /conversations/{conversation_id}` - Get conversation history
- `DELETE /conversations/{conversation_id}` - Delete a conversation
- `GET /conversations/search` - Search across conversations

## Development

### Running Locally (without Docker)

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set environment variables:

```bash
export OLLAMA_HOST=http://localhost:11434
export POSTGRES_CONNECTION=postgresql://user:pass@localhost:5432/db
```

3. Run the server:

```bash
python server.py
```

### Pulling Different Ollama Models

```bash
# Access Ollama container
docker-compose exec ollama bash

# Pull models
ollama pull llama2
ollama pull llama3
ollama pull mistral
ollama pull codellama
ollama pull neural-chat

# List installed models
ollama list
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mcp-server
docker-compose logs -f ollama
docker-compose logs -f postgres
```

## Advanced Features

### Custom Intent Classification

Modify `agent_orchestrator.py` to add custom intents:

```python
class IntentType(str, Enum):
    DATABASE_QUERY = "database_query"
    DOCUMENT_SEARCH = "document_search"
    API_CALL = "api_call"
    CUSTOM_INTENT = "custom_intent"  # Add your intent
```

### Complex Multi-Step Queries

The orchestrator can handle queries that require multiple operations:

```
"Find all customers who made purchases in the last month, 
then search our documentation for their feedback"
```

This will:
1. Query the database for customers
2. Search documents for feedback
3. Combine results in a comprehensive response

### Table-Level Access Control

Define permissions in `config.yaml`:

```yaml
table_permissions:
  public_data: []  # Everyone
  user_data: ["user_1", "user_2"]  # Specific users
  admin_data: ["admin"]  # Admin only
```

## Troubleshooting

### Ollama Not Responding

```bash
docker-compose restart ollama
docker-compose exec ollama ollama pull llama2
```

### Database Connection Issues

```bash
# Check PostgreSQL
docker-compose exec postgres pg_isready -U mcp_user

# Recreate database
docker-compose down -v
docker-compose up -d
```

### ChromaDB Issues

```bash
# Clear ChromaDB data
rm -rf chroma_data/*
docker-compose restart mcp-server
```

### Out of Memory

Increase Docker memory limit or use smaller models:

```yaml
ollama:
  model: "tinyllama"  # Smaller, faster model
```

## Performance Tips

1. **Use caching**: API calls are cached for 1 hour by default
2. **Optimize chunk size**: Adjust `chunk_size` in config for your documents
3. **Use connection pooling**: Already configured for PostgreSQL
4. **Monitor resources**: Check `docker stats` for resource usage

## Security Considerations

- Set `api_key` in config for authentication
- Use environment variables for sensitive data
- Configure `allowed_origins` for CORS
- Review table permissions before deployment
- Use HTTPS in production (add reverse proxy)

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- Check logs: `docker-compose logs`
- Review configuration: `config.yaml`
- Health check: `curl http://localhost:8000/health`