#!/bin/bash

# MCP Server Setup Script
# This script sets up the complete MCP server environment

set -e

echo "=========================================="
echo "MCP Server Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi
print_success "Docker is installed"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
print_success "Docker Compose is installed"

# Create necessary directories
print_info "Creating directory structure..."
mkdir -p data
mkdir -p chroma_data
mkdir -p documents
mkdir -p logs
print_success "Directories created"

# Create config.yaml if it doesn't exist
if [ ! -f config.yaml ]; then
    print_info "Creating default config.yaml..."
    cat > config.yaml << 'EOF'
ollama:
  host: "http://ollama:11434"
  model: "llama2"
  temperature: 0.7
  timeout: 300
  max_tokens: 4096

databases:
  sqlite:
    type: "sqlite"
    connection_string: "sqlite:///./data/mcp_data.db"
    pool_size: 1
    table_permissions: {}
  
  postgresql:
    type: "postgresql"
    connection_string: "postgresql://mcp_user:mcp_password@postgres:5432/mcp_db"
    pool_size: 10
    max_overflow: 20
    table_permissions: {}

chroma:
  host: "localhost"
  port: 8000
  collection_name: "mcp_conversations"
  persist_directory: "./chroma_data"
  distance_metric: "cosine"

documents:
  storage_path: "./documents"
  chroma_collection: "documents"
  chunk_size: 1000
  chunk_overlap: 200
  supported_formats: ["txt", "pdf", "docx", "md", "json", "csv"]

apis:
  registry_path: "./api_registry.json"
  timeout: 30
  max_retries: 3
  cache_ttl: 3600

log_level: "INFO"
log_file: "./logs/mcp_server.log"
EOF
    print_success "config.yaml created"
else
    print_info "config.yaml already exists, skipping..."
fi

# Create api_registry.json if it doesn't exist
if [ ! -f api_registry.json ]; then
    print_info "Creating empty api_registry.json..."
    echo "{}" > api_registry.json
    print_success "api_registry.json created"
fi

# Build and start containers
print_info "Building Docker images..."
docker-compose build

print_info "Starting containers..."
docker-compose up -d

# Wait for services to be healthy
print_info "Waiting for services to be ready..."
sleep 10

# Check if Ollama is running
print_info "Checking Ollama service..."
if docker-compose exec -T ollama curl -f http://localhost:11434/api/tags &> /dev/null; then
    print_success "Ollama is running"
else
    print_error "Ollama is not responding"
fi

# Pull Ollama model
print_info "Pulling Ollama model (this may take a while)..."
docker-compose exec -T ollama ollama pull llama2
print_success "Ollama model pulled"

# Check PostgreSQL
print_info "Checking PostgreSQL service..."
if docker-compose exec -T postgres pg_isready -U mcp_user &> /dev/null; then
    print_success "PostgreSQL is running"
else
    print_error "PostgreSQL is not responding"
fi

# Check MCP Server
print_info "Checking MCP Server..."
sleep 5
if curl -f http://localhost:8000/health &> /dev/null; then
    print_success "MCP Server is running"
else
    print_error "MCP Server is not responding"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Services running:"
echo "  - MCP Server: http://localhost:8000"
echo "  - Ollama: http://localhost:11434"
echo "  - PostgreSQL: localhost:5432"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart services: docker-compose restart"
echo "  - View health: curl http://localhost:8000/health"
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo ""