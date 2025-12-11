#!/bin/bash

# MCP Server Setup Script
# This script sets up the MCP server with Ollama and PostgreSQL integration

set -e  # Exit on error

echo "🚀 MCP Server Setup Starting..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python installation
echo "📦 Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3 found: $(python3 --version)${NC}"
echo ""

# Check pip installation
echo "📦 Checking pip installation..."
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 is not installed. Installing pip...${NC}"
    python3 -m ensurepip --default-pip
fi
echo -e "${GREEN}✅ pip3 found${NC}"
echo ""

# Create project directory
PROJECT_DIR="mcp_ollama_server"
echo "📁 Creating project directory: $PROJECT_DIR"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install mcp chromadb requests psycopg2-binary

echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
echo ""

# Create the MCP server file
echo "📝 Creating MCP server file..."
cat > mcp_server.py << 'EOF'
"""
MCP Server with Ollama Integration and ChromaDB Storage
Backend server that interacts with Ollama and PostgreSQL
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
import requests
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
import chromadb
from chromadb.config import Settings
import psycopg2
from psycopg2.extras import RealDictCursor


class MCPOllamaServer:
    def __init__(self):
        self.server = Server("ollama-docs-server")
        self.ollama_url = "http://localhost:11436"
        self.ollama_model = "llama3.2"
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create collections
        self.api_docs_collection = self.chroma_client.get_or_create_collection(
            name="api_docs",
            metadata={"description": "API documentation storage"}
        )
        
        self.workflows_collection = self.chroma_client.get_or_create_collection(
            name="workflows",
            metadata={"description": "Query workflows and responses"}
        )
        
        self.db_schema_collection = self.chroma_client.get_or_create_collection(
            name="database_schemas",
            metadata={"description": "Database schema information"}
        )
        
        self.setup_handlers()
    
    def get_db_connection(self):
        """Create PostgreSQL connection"""
        try:
            conn = psycopg2.connect(
                host="192.168.1.11",
                port=5432,
                database="postgres",
                user="postgres",
                password="shivam@123"
            )
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    
    def setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="query_ollama",
                    description="Query Ollama model with context from API docs and database schema",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "User query to process"},
                            "model": {"type": "string", "description": "Ollama model to use", "default": "llama3.2"},
                            "include_context": {"type": "boolean", "description": "Include context", "default": True}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="add_api_doc",
                    description="Add API documentation to ChromaDB",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                            "endpoint": {"type": "string"},
                            "method": {"type": "string"}
                        },
                        "required": ["title", "content"]
                    }
                ),
                Tool(
                    name="extract_postgres_schema",
                    description="Extract PostgreSQL database schema",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schema_name": {"type": "string", "default": "public"}
                        }
                    }
                ),
                Tool(
                    name="query_postgres",
                    description="Execute SQL query on PostgreSQL",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "limit": {"type": "integer", "default": 50}
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="list_postgres_tables",
                    description="List all tables in PostgreSQL",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schema_name": {"type": "string", "default": "public"}
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> List[TextContent]:
            handlers = {
                "query_ollama": self.handle_query_ollama,
                "add_api_doc": self.handle_add_api_doc,
                "extract_postgres_schema": self.handle_extract_postgres_schema,
                "query_postgres": self.handle_query_postgres,
                "list_postgres_tables": self.handle_list_postgres_tables
            }
            if name in handlers:
                return await handlers[name](arguments)
            raise ValueError(f"Unknown tool: {name}")
    
    async def handle_query_ollama(self, args: Dict) -> List[TextContent]:
        query = args["query"]
        model = args.get("model", self.ollama_model)
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": model, "prompt": query, "stream": False},
                timeout=120
            )
            response.raise_for_status()
            result = response.json()["response"]
            
            # Save to ChromaDB
            workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.workflows_collection.add(
                documents=[json.dumps({"query": query, "response": result, "model": model})],
                ids=[workflow_id]
            )
            
            return [TextContent(type="text", text=f"✅ Response:\n{result}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error: {str(e)}")]
    
    async def handle_add_api_doc(self, args: Dict) -> List[TextContent]:
        doc_id = f"api_{int(datetime.now().timestamp())}"
        self.api_docs_collection.add(
            documents=[args["content"]],
            ids=[doc_id],
            metadatas=[{"title": args["title"]}]
        )
        return [TextContent(type="text", text=f"✅ Added: {doc_id}")]
    
    async def handle_extract_postgres_schema(self, args: Dict) -> List[TextContent]:
        conn = self.get_db_connection()
        if not conn:
            return [TextContent(type="text", text="❌ DB connection failed")]
        
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
            """, (args.get("schema_name", "public"),))
            tables = cursor.fetchall()
            conn.close()
            
            result = f"✅ Found {len(tables)} tables:\n"
            result += "\n".join([f"  - {t['table_name']}" for t in tables])
            return [TextContent(type="text", text=result)]
        except Exception as e:
            conn.close()
            return [TextContent(type="text", text=f"❌ Error: {str(e)}")]
    
    async def handle_query_postgres(self, args: Dict) -> List[TextContent]:
        if not args["query"].strip().upper().startswith("SELECT"):
            return [TextContent(type="text", text="❌ Only SELECT queries allowed")]
        
        conn = self.get_db_connection()
        if not conn:
            return [TextContent(type="text", text="❌ DB connection failed")]
        
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(args["query"])
            results = cursor.fetchall()
            conn.close()
            
            return [TextContent(type="text", text=f"✅ Returned {len(results)} rows:\n{json.dumps(results, indent=2, default=str)}")]
        except Exception as e:
            conn.close()
            return [TextContent(type="text", text=f"❌ Error: {str(e)}")]
    
    async def handle_list_postgres_tables(self, args: Dict) -> List[TextContent]:
        conn = self.get_db_connection()
        if not conn:
            return [TextContent(type="text", text="❌ DB connection failed")]
        
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
            """, (args.get("schema_name", "public"),))
            tables = cursor.fetchall()
            conn.close()
            
            result = "\n".join([f"  - {t['table_name']}" for t in tables])
            return [TextContent(type="text", text=f"✅ Tables:\n{result}")]
        except Exception as e:
            conn.close()
            return [TextContent(type="text", text=f"❌ Error: {str(e)}")]
    
    async def run(self):
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())


async def main():
    server = MCPOllamaServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
EOF

echo -e "${GREEN}✅ MCP server file created${NC}"
echo ""

# Create start script
echo "📝 Creating start script..."
cat > start_server.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python mcp_server.py
EOF

chmod +x start_server.sh

echo -e "${GREEN}✅ Start script created${NC}"
echo ""

# Create config file template
echo "📝 Creating Claude Desktop config template..."
cat > claude_config_template.json << EOF
{
  "mcpServers": {
    "ollama-postgres-server": {
      "command": "bash",
      "args": ["$(pwd)/start_server.sh"]
    }
  }
}
EOF

echo -e "${GREEN}✅ Config template created${NC}"
echo ""

# Create README
cat > README.md << 'EOF'
# MCP Ollama PostgreSQL Server

## Setup Complete! 🎉

### Configuration Files:
- `mcp_server.py` - Main MCP server
- `start_server.sh` - Server startup script
- `claude_config_template.json` - Claude Desktop config template

### Next Steps:

1. **Test the server:**
   ```bash
   ./start_server.sh
   ```

2. **Configure Claude Desktop:**
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`
   
   Copy content from `claude_config_template.json` to your Claude config file.

3. **Restart Claude Desktop**

### Requirements:
- Ollama running on http://localhost:11436
- PostgreSQL at 192.168.1.11:5432

### Available Tools:
- query_ollama - Query Ollama with context
- add_api_doc - Add API documentation
- extract_postgres_schema - Extract DB schema
- query_postgres - Run SQL queries
- list_postgres_tables - List all tables

### Troubleshooting:
- Check Ollama is running: `curl http://localhost:11436/api/tags`
- Test PostgreSQL connection: `psql postgresql://postgres:shivam@123@192.168.1.11:5432/postgres`
EOF

echo -e "${GREEN}✅ README created${NC}"
echo ""

# Final instructions
echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "📂 Project location: $(pwd)"
echo ""
echo "🚀 To start the server:"
echo "   ./start_server.sh"
echo ""
echo "⚙️  To configure Claude Desktop:"
echo "   1. Copy config from: claude_config_template.json"
echo "   2. Paste to Claude Desktop config file"
echo "   3. Restart Claude Desktop"
echo ""
echo "📖 Read README.md for more details"
echo ""

# Deactivate virtual environment
deactivate

echo -e "${YELLOW}Note: Make sure Ollama is running on port 11436!${NC}"
echo ""
