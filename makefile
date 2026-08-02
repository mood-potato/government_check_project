PROJECT_NAME := government_project
DOCKER_COMPOSE ?= docker compose
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 3000
include .env
export $(shell sed 's/=.*//' .env)

.PHONY: up down restart logs ps build deploy backend-logs frontend-logs pipeline pipeline-services pipeline-bootstrap airflow airflow-build backend-local frontend-local dev-local

up:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) up -d

down:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) down

restart:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) down
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) up -d

logs:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) logs -f

ps:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) ps

build:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) build

deploy:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) build backend frontend
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) up -d

backend-logs:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) logs -f backend

frontend-logs:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) logs -f frontend

pipeline-services:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) up -d postgres elasticsearch

pipeline:
	PROJECT_NAME=$(PROJECT_NAME) DOCKER_COMPOSE="$(DOCKER_COMPOSE)" scripts/run_pipeline.sh

pipeline-bootstrap:
	PROJECT_NAME=$(PROJECT_NAME) DOCKER_COMPOSE="$(DOCKER_COMPOSE)" scripts/run_pipeline.sh --build

airflow-build:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) build airflow

airflow:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) up -d airflow

backend-local:
	uv run uvicorn backend.api.main:app --host 127.0.0.1 --port $(BACKEND_PORT) --reload

frontend-local:
	cd frontend && BACKEND_URL=http://localhost:$(BACKEND_PORT) PORT=$(FRONTEND_PORT) bun run dev

dev-local:
	$(MAKE) -j2 backend-local frontend-local
