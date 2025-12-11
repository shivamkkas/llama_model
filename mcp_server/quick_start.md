# Quick Start Guide

Get your MCP Server up and running in 5 minutes!

## Prerequisites

- Docker Desktop installed and running
- At least 8GB RAM available
- 10GB free disk space

## Step 1: Setup

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup (pulls images, starts services, initializes databases)
./setup.sh
```

This will take 5-10 minutes on the first run as it downloads Docker images and Ollama models.

## Step 2: Verify Installation

```bash
# Check server health
curl http://localhost:8000/health
```

You should see:
```json
{
  "status": "healthy",
  "ollama_connected": true,
  "databases_connected": true,
  "chroma_connected": true
}
```

## Step 3: Your First Query

### Option A: Using curl

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me all customers in the database",
    "user_id": "user_1"
  }'
```

### Option B: Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/query",
    json={
        "message": "Show me all customers in the database",
        "user_id": "user_1"
    }
)

print(response.json()["response"])
```

### Option C: Using the API Docs

Open your browser to: `http://localhost:8000/docs`

This interactive Swagger UI lets you test all endpoints!

## Step 4: Try More Features

### Upload a Document

```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "Content-Type: application/json" \
  -d '{
    "file_content": "Machine learning is a subset of artificial intelligence...",
    "filename": "ml_notes.txt",
    "user_id": "user_1"
  }'
```

### Search Documents

```bash
curl -X POST http://localhost:8000/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "user_id": "user_1",
    "top_k": 3
  }'
```

### Run Examples

```bash
# Install Python dependencies locally
pip install requests websockets

# Run all example scenarios
python examples.py
```

## Step 5: Customize

### Change Ollama Model

```bash
# List available models
docker-compose exec ollama ollama list

# Pull a different model
docker-compose exec ollama ollama pull llama3

# Update config.yaml
# Change: model: "llama2" to model: "llama3"

# Restart server
docker-compose restart mcp-server
```

### Configure Database Permissions

Edit `config.yaml`:

```yaml
databases:
  postgresql:
    table_permissions:
      customers: []  # Everyone can access
      transactions: ["user_1", "admin"]  # Only these users
      sensitive_data: ["admin"]  # Admin only
```

Then restart:

```bash
docker-compose restart mcp-server
```

## Common Commands

```bash
# View logs
docker-compose logs -f mcp-server

# Stop all services
docker-compose down

# Start services
docker-compose up -d

# Rebuild after code changes
docker-compose up -d --build

# Reset everything
docker-compose down -v
./setup.sh
```

## Troubleshooting

### Server Not Starting

```bash
# Check logs
docker-compose logs mcp-server

# Common issue: Port already in use
# Change port in docker-compose.yml:
# ports: - "8001:8000"  # Use 8001 instead
```

### Ollama Out of Memory

```bash
# Use a smaller model
docker-compose exec ollama ollama pull tinyllama

# Update config.yaml: model: "tinyllama"
docker-compose restart mcp-server
```

### Database Connection Failed

```bash
# Restart PostgreSQL
docker-compose restart postgres

# Check if it's running
docker-compose exec postgres pg_isready -U mcp_user
```

### ChromaDB Issues

```bash
# Clear ChromaDB data
rm -rf chroma_data/*
docker-compose restart mcp-server
```

## Next Steps

1. **Read the full README**: `README.md` for detailed documentation
2. **Explore API docs**: `http://localhost:8000/docs`
3. **Check examples**: Run `python examples.py` to see all features
4. **Customize config**: Edit `config.yaml` for your needs
5. **Add your data**: Upload your documents and connect your databases

## Architecture Overview

```
You → FastAPI Server → LangGraph Router → Chooses:
                                         ├─ Database Query
                                         ├─ Document Search
                                         ├─ API Call
                                         └─ General Chat
                                         
All powered by Ollama (local LLM) in Docker!
```

## Support

- Check `docker-compose logs` for errors
- Visit `http://localhost:8000/health` to diagnose issues
- Review `config.yaml` for configuration
- See `README.md` for detailed documentation

## Production Deployment

For production use:

1. Set a strong `api_key` in `config.yaml`
2. Use environment variables for secrets
3. Configure HTTPS (use nginx reverse proxy)
4. Set up proper backup for data volumes
5. Monitor resource usage with `docker stats`
6. Use a production-grade PostgreSQL setup

Happy building! 🚀