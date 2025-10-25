# Configuration
SERVICE_NAME := ollama
DOCKER_HUB_USERNAME := infinityshiv
VERSION := latest
COMPOSE_FILE := docker-compose.yml

# Colors for output
RED := \033[0;31m]
GREEN := \033[0;32m]
YELLOW := \033[0;33m]
BLUE := \033[0;34m]
NC := \033[0m]

.PHONY: help run stop restart logs logs-follow clean purge ps status pull-model build push pull-hub recreate

help:
	@echo "Available commands:"
	@echo "  $(GREEN)run$(NC)        - Build and start services in detached mode"
	@echo "  $(GREEN)stop$(NC)       - Stop all services"
	@echo "  $(GREEN)restart$(NC)    - Restart all services"
	@echo "  $(GREEN)logs$(NC)       - Show logs for all services"
	@echo "  $(GREEN)logs-follow$(NC) - Follow logs for all services"
	@echo "  $(GREEN)logs-service$(NC) - Show logs for specific service (make logs-service SERVICE=backend)"
	@echo "  $(GREEN)clean$(NC)      - Stop services and remove containers"
	@echo "  $(GREEN)purge$(NC)      - Stop services and remove containers, images, volumes"
	@echo "  $(GREEN)ps$(NC)         - Show running services"
	@echo "  $(GREEN)status$(NC)     - Show detailed service status"
	@echo "  $(GREEN)build$(NC)      - Build services without starting"
	@echo "  $(GREEN)recreate$(NC)   - Recreate services with force"
	@echo ""
	@echo "Model Management:"
	@echo "  $(GREEN)pull-model$(NC) - Pull Llama3 model"
	@echo "  $(GREEN)pull-model-custom$(NC) - Pull custom model (make pull-model-custom MODEL=model-name)"
	@echo "  $(GREEN)list-models$(NC) - List available models"
	@echo ""
	@echo "Docker Hub:"
	@echo "  $(GREEN)push$(NC)       - Push images to Docker Hub"
	@echo "  $(GREEN)pull-hub$(NC)   - Pull images from Docker Hub"
	@echo "  $(GREEN)tag$(NC)        - Tag images for Docker Hub"

run:
	@echo "$(BLUE)Building and starting $(SERVICE_NAME)...$(NC)"
	docker compose -f $(COMPOSE_FILE) up --build -d
	@echo "$(GREEN)Services started successfully!$(NC)"
	@make status

stop:
	@echo "$(YELLOW)Stopping $(SERVICE_NAME)...$(NC)"
	docker compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN)Services stopped successfully!$(NC)"

restart: stop run

logs:
	@echo "$(BLUE)Showing logs for $(SERVICE_NAME)...$(NC)"
	docker compose -f $(COMPOSE_FILE) logs

logs-follow:
	@echo "$(BLUE)Following logs for $(SERVICE_NAME)...$(NC)"
	docker compose -f $(COMPOSE_FILE) logs -f

logs-service:
ifndef SERVICE
	$(error SERVICE variable is required. Usage: make logs-service SERVICE=service-name)
endif
	@echo "$(BLUE)Showing logs for $(SERVICE)...$(NC)"
	docker compose -f $(COMPOSE_FILE) logs $(SERVICE)

clean:
	@echo "$(YELLOW)Cleaning up $(SERVICE_NAME)...$(NC)"
	docker compose -f $(COMPOSE_FILE) down -v
	@echo "$(GREEN)Cleanup completed!$(NC)"

purge:
	@echo "$(RED)Purging $(SERVICE_NAME)...$(NC)"
	docker compose -f $(COMPOSE_FILE) down -v --rmi all --remove-orphans
	@echo "$(GREEN)Purge completed!$(NC)"

ps:
	@echo "$(BLUE)Running services:$(NC)"
	docker compose -f $(COMPOSE_FILE) ps

status:
	@echo "$(BLUE)Service Status:$(NC)"
	@docker compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "$(BLUE)Recent logs:$(NC)"
	@docker compose -f $(COMPOSE_FILE) logs --tail=5

build:
	@echo "$(BLUE)Building $(SERVICE_NAME)...$(NC)"
	docker compose -f $(COMPOSE_FILE) build
	@echo "$(GREEN)Build completed!$(NC)"

recreate:
	@echo "$(BLUE)Recreating $(SERVICE_NAME)...$(NC)"
	docker compose -f $(COMPOSE_FILE) up --build -d --force-recreate
	@echo "$(GREEN)Recreation completed!$(NC)"
	@make status

# Model Management
pull-model:
	@echo "$(BLUE)Pulling Llama3 model...$(NC)"
	docker exec -it $(SERVICE_NAME) ollama pull llama3
	@echo "$(GREEN)Llama3 model pulled successfully!$(NC)"

pull-model-custom:
ifndef MODEL
	$(error MODEL variable is required. Usage: make pull-model-custom MODEL=model-name)
endif
	@echo "$(BLUE)Pulling $(MODEL) model...$(NC)"
	docker exec -it $(SERVICE_NAME)-ollama-1 ollama pull $(MODEL)
	@echo "$(GREEN)$(MODEL) model pulled successfully!$(NC)"

list-models:
	@echo "$(BLUE)Available models:$(NC)"
	docker exec -it $(SERVICE_NAME)-ollama-1 ollama list

# Docker Hub Operations
tag:
	@echo "$(BLUE)Tagging images for Docker Hub...$(NC)"
	docker tag $(SERVICE_NAME)-backend $(DOCKER_HUB_USERNAME)/$(SERVICE_NAME)-backend:$(VERSION)
	docker tag $(SERVICE_NAME)-frontend $(DOCKER_HUB_USERNAME)/$(SERVICE_NAME)-frontend:$(VERSION)
	@echo "$(GREEN)Images tagged successfully!$(NC)"

push: tag
	@echo "$(BLUE)Pushing images to Docker Hub...$(NC)"
	docker push $(DOCKER_HUB_USERNAME)/$(SERVICE_NAME)-backend:$(VERSION)
	docker push $(DOCKER_HUB_USERNAME)/$(SERVICE_NAME)-frontend:$(VERSION)
	@echo "$(GREEN)Images pushed to Docker Hub successfully!$(NC)"

pull-hub:
	@echo "$(BLUE)Pulling images from Docker Hub...$(NC)"
	docker pull $(DOCKER_HUB_USERNAME)/$(SERVICE_NAME)-backend:$(VERSION)
	docker pull $(DOCKER_HUB_USERNAME)/$(SERVICE_NAME)-frontend:$(VERSION)
	@echo "$(GREEN)Images pulled from Docker Hub successfully!$(NC)"

# Service-specific commands
backend-logs:
	@make logs-service SERVICE=backend

frontend-logs:
	@make logs-service SERVICE=frontend

ollama-logs:
	@make logs-service SERVICE=ollama

# Database operations
db-backup:
	@echo "$(BLUE)Backing up database...$(NC)"
	docker exec -t $(SERVICE_NAME)-db-1 pg_dump -U postgres ragdb > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Database backup completed!$(NC)"

db-restore:
ifndef FILE
	$(error FILE variable is required. Usage: make db-restore FILE=backup_file.sql)
endif
	@echo "$(BLUE)Restoring database from $(FILE)...$(NC)"
	docker exec -i $(SERVICE_NAME)-db-1 psql -U postgres ragdb < $(FILE)
	@echo "$(GREEN)Database restore completed!$(NC)"

# Monitoring
stats:
	@echo "$(BLUE)Container statistics:$(NC)"
	docker stats --no-stream

resources:
	@echo "$(BLUE)System resources:$(NC)"
	@echo "Containers:"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "Images:"
	@docker images $(SERVICE_NAME)* --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Quick setup
setup: pull-hub run pull-model
	@echo "$(GREEN)Setup completed!$(NC)"
	@make status

# Health check
health:
	@echo "$(BLUE)Checking service health...$(NC)"
	@curl -f http://localhost:8000/health || echo "$(RED)Backend is not healthy$(NC)"
	@curl -f http://localhost:3005 || echo "$(RED)Frontend is not healthy$(NC)"
	@curl -f http://localhost:11435/api/tags || echo "$(RED)Ollama is not healthy$(NC)"
	@echo "$(GREEN)Health check completed!$(NC)"