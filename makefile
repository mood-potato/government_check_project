PROJECT_NAME := government_project
include .env
export $(shell sed 's/=.*//' .env)

up:
	docker-compose -p $(PROJECT_NAME) up -d

down:
	docker-compose -p $(PROJECT_NAME) down

restart:
	docker-compose -p $(PROJECT_NAME) down
	docker-compose -p $(PROJECT_NAME) up -d

logs:
	docker-compose -p $(PROJECT_NAME) logs -f

ps:
	docker-compose -p $(PROJECT_NAME) ps

build:
	docker-compose -p $(PROJECT_NAME) build

deploy:
	docker-compose -p $(PROJECT_NAME) build webapp
	docker-compose -p $(PROJECT_NAME) up -d

webapp-logs:
	docker-compose -p $(PROJECT_NAME) logs -f webapp
