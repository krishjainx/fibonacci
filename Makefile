# Image name (change if desired)
IMAGE_NAME := fibonacci-service
# Container name
CONTAINER_NAME := fibonacci-container
# Redis container name
REDIS_NAME := redis-cache
# Redis image and config
REDIS_IMAGE := cgr.dev/chainguard/redis:latest
REDIS_PORT := 6379

# Default shell
SHELL := /bin/bash

.PHONY: build run stop test-local test-container clean load-test integration-test redis wait-for-app create-network

## Build Docker image
build:
	docker build -t $(IMAGE_NAME) .

## Run Redis container and wait for it to be ready
redis:
	docker run -d --name $(REDIS_NAME) \
		-p $(REDIS_PORT):6379 \
		$(REDIS_IMAGE) \
		--port 6379
	@echo "Waiting for Redis to be ready..."
	@sleep 3
	@docker exec $(REDIS_NAME) redis-cli ping || (docker logs $(REDIS_NAME) && exit 1)

## Wait for application to be ready
wait-for-app:
	@echo "Waiting for application to be ready..."
	@for i in $$(seq 1 30); do \
		if curl -s http://localhost:5000/health > /dev/null; then \
			echo "Application is ready!"; \
			exit 0; \
		fi; \
		echo "Waiting... ($$i/30)"; \
		sleep 1; \
	done; \
	echo "Application failed to start"; \
	docker logs $(CONTAINER_NAME); \
	exit 1

## Run the container in detached mode, mapping port 5000
run: create-network
	docker run -d --name $(CONTAINER_NAME) \
		-p 5000:5000 \
		--network fibonacci-network \
		$(IMAGE_NAME)
	$(MAKE) redis
	docker network connect fibonacci-network $(REDIS_NAME)
	$(MAKE) wait-for-app

## Stop and remove container
stop:
	docker stop $(CONTAINER_NAME) $(REDIS_NAME) || true
	docker rm $(CONTAINER_NAME) $(REDIS_NAME) || true

## Run unit tests locally (outside Docker)
test-local: run
	PYTHONPATH=. REDIS_HOST=localhost pip install -r requirements.txt
	PYTHONPATH=. REDIS_HOST=localhost pytest tests/test_app.py -v  # Run unit tests only

## Run tests inside the running container
test-container:
	docker exec $(CONTAINER_NAME) python -m pytest -v $(ARGS)

## Run integration tests
integration-test: run
	$(MAKE) wait-for-app
	PYTHONPATH=. pytest tests/test_integration.py -v
	$(MAKE) stop

## Run load tests
load-test: run
	locust -f tests/test_load.py --headless -u 100 -r 10 --run-time 1m
	$(MAKE) stop

## Clean up Docker image (and stop/remove container if it's running)
clean: stop
	docker rm -vf $(docker ps -a -q)

## Check Redis connection
check-redis:
	@docker exec $(REDIS_NAME) redis-cli ping || echo "Redis is not responding"

## Create network
create-network:
	docker network inspect fibonacci-network >/dev/null 2>&1 || docker network create fibonacci-network
