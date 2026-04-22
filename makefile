PROJECT_NAME := government_project
DOCKER_COMPOSE ?= docker compose
include .env
export $(shell sed 's/=.*//' .env)

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

pipeline:
	$(DOCKER_COMPOSE) -p $(PROJECT_NAME) --profile pipeline run --rm pipeline
