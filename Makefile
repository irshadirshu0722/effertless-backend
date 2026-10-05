.PHONY: help infra-up infra-down infra-clean up down rebuild logs dev test lint format migrate migration

COMPOSE_FILE = docker-compose.yml

help: ## Display available backend commands
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

infra-up: ## Start PostgreSQL and Redis
	docker compose -f $(COMPOSE_FILE) up -d postgres redis

infra-down: ## Stop backend infrastructure
	docker compose -f $(COMPOSE_FILE) down

infra-clean: ## Stop infrastructure and remove local volumes
	docker compose -f $(COMPOSE_FILE) down -v

up: ## Start the backend stack
	docker compose -f $(COMPOSE_FILE) up -d

down: ## Stop the backend stack
	docker compose -f $(COMPOSE_FILE) down

rebuild: ## Rebuild and restart the backend stack
	docker compose -f $(COMPOSE_FILE) down
	docker compose -f $(COMPOSE_FILE) up -d --build

logs: ## Follow backend stack logs
	docker compose -f $(COMPOSE_FILE) logs -f

dev:
	poetry run uvicorn --app-dir src main:app --reload --port 8000

test: 
	poetry run pytest

lint: 
	poetry run ruff check .

format: 
	poetry run ruff check --fix .
	poetry run ruff format .

migrate:
	poetry run alembic upgrade head

migration:
	poetry run alembic revision --autogenerate -m "$(message)"
