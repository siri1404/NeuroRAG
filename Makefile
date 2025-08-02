# NeuroRAG Makefile
# Makefile
# Commands for development and deployment

.PHONY: help install build test clean deploy docker-build docker-push

# Default target
help:
	@echo "Development Commands"
	@echo "============================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install          Install all dependencies"
	@echo "  make setup-dev        Setup development environment"
	@echo "  make setup-prod       Setup production environment"
	@echo ""
	@echo "Development:"
	@echo "  make dev              Start development servers"
	@echo "  make build            Build all components"
	@echo "  make test             Run all tests"
	@echo "  make lint             Run code linting"
	@echo "  make format           Format code"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build     Build Docker images"
	@echo "  make docker-push      Push images to registry"
	@echo "  make docker-dev       Start development with Docker"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-staging   Deploy to staging"
	@echo "  make deploy-prod      Deploy to production"
	@echo "  make k8s-apply        Apply Kubernetes manifests"
	@echo ""
	@echo "Data & Cache:"
	@echo "  make ingest-data      Ingest sample data"
	@echo "  make warmup-cache     Warm up Redis cache"
	@echo "  make benchmark        Run performance benchmarks"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean            Clean build artifacts"
	@echo "  make logs             View application logs"
	@echo "  make health-check     Check system health"

# Variables
DOCKER_REGISTRY ?= neuroragacr.azurecr.io
IMAGE_TAG ?= latest
NAMESPACE ?= neurorag

# Setup & Installation
install:
	@echo "Installing dependencies..."
	npm install
	pip install -r requirements.txt
	@echo "Dependencies installed successfully!"

setup-dev:
	@echo "Setting up development environment..."
	cp .env.example .env
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	npm install
	@echo "Development environment ready!"

setup-prod:
	@echo "Setting up production environment..."
	@echo "Please ensure .env file is configured for production"
	pip install -r requirements.txt --no-dev
	npm ci --production

# Development
dev:
	@echo "Starting development servers..."
	docker-compose up -d redis
	npm run dev &
	cd src/api_gateway && python app.py &
	@echo "Development servers started!"

build: build-frontend build-cpp build-python

build-frontend:
	@echo "Building frontend..."
	npm run build

build-cpp:
	@echo "Building C++ vector service..."
	cd src/vector_service && \
	mkdir -p build && \
	cd build && \
	cmake .. -DCMAKE_BUILD_TYPE=Release && \
	make -j$$(nproc)

build-python:
	@echo "Building Python services..."
	pip install -e .

# Testing
test: test-frontend test-python test-cpp

test-frontend:
	@echo "Running frontend tests..."
	npm test

test-python:
	@echo "Running Python tests..."
	pytest src/tests/ -v --cov=src

test-cpp:
	@echo "Running C++ tests..."
	cd src/vector_service/build && make test

test-integration:
	@echo "Running integration tests..."
	docker-compose -f docker-compose.test.yml up -d
	sleep 10
	pytest src/tests/integration/ -v
	docker-compose -f docker-compose.test.yml down

# Code Quality
lint:
	@echo "Running linters..."
	flake8 src/ --max-line-length=100
	mypy src/ --ignore-missing-imports
	npm run lint

format:
	@echo "Formatting code..."
	black src/
	isort src/
	npm run format

# Docker
docker-build:
	@echo "Building Docker images..."
	docker build -t $(DOCKER_REGISTRY)/neurorag/api-gateway:$(IMAGE_TAG) -f src/api_gateway/Dockerfile .
	docker build -t $(DOCKER_REGISTRY)/neurorag/vector-service:$(IMAGE_TAG) -f src/vector_service/Dockerfile .
	docker build -t $(DOCKER_REGISTRY)/neurorag/frontend:$(IMAGE_TAG) -f Dockerfile.frontend .

docker-push:
	@echo "Pushing Docker images..."
	docker push $(DOCKER_REGISTRY)/neurorag/api-gateway:$(IMAGE_TAG)
	docker push $(DOCKER_REGISTRY)/neurorag/vector-service:$(IMAGE_TAG)
	docker push $(DOCKER_REGISTRY)/neurorag/frontend:$(IMAGE_TAG)

docker-dev:
	@echo "Starting development environment with Docker..."
	docker-compose up -d
	@echo "Services available at:"
	@echo "  Frontend: http://localhost:5173"
	@echo "  API Gateway: http://localhost:8000"
	@echo "  Vector Service: http://localhost:8001"

# Deployment
deploy-staging:
	@echo "Deploying to staging..."
	kubectl apply -f infra/k8s_deployments/ -n $(NAMESPACE)-staging
	kubectl rollout status deployment/neurorag-api-gateway -n $(NAMESPACE)-staging

deploy-prod:
	@echo "Deploying to production..."
	kubectl apply -f infra/k8s_deployments/ -n $(NAMESPACE)
	kubectl rollout status deployment/neurorag-api-gateway -n $(NAMESPACE)

k8s-apply:
	@echo "Applying Kubernetes manifests..."
	kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f infra/k8s_deployments/ -n $(NAMESPACE)

# Data & Cache
ingest-data:
	@echo "Ingesting sample data..."
	python scripts/ingest_data.py --input data/sample_docs/ --output data/

warmup-cache:
	@echo "Warming up cache..."
	bash scripts/cache_warmup.sh

benchmark:
	@echo "Running performance benchmarks..."
	python scripts/benchmark_vector_search.py \
		--index data/faiss_index.bin \
		--config data/config.json \
		--output benchmark_results/

# Utilities
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf src/vector_service/build/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf node_modules/.cache/
	docker system prune -f

logs:
	@echo "Viewing application logs..."
	docker-compose logs -f

health-check:
	@echo "Checking system health..."
	@curl -s http://localhost:8000/health | jq '.' || echo "API Gateway not responding"
	@curl -s http://localhost:8001/health | jq '.' || echo "Vector Service not responding"
	@redis-cli ping || echo "Redis not responding"

# Database operations
db-migrate:
	@echo "Running database migrations..."
	alembic upgrade head

db-seed:
	@echo "Seeding database with sample data..."
	python scripts/seed_database.py

# Monitoring
metrics:
	@echo "Viewing metrics..."
	curl -s http://localhost:9090/metrics

grafana-setup:
	@echo "Setting up Grafana dashboards..."
	curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
		-H "Content-Type: application/json\" \
		-d @config/grafana/neurorag-dashboard.json

# Security
security-scan:
	@echo "Running security scans..."
	bandit -r src/ -f json -o security-report.json
	safety check --json --output safety-report.json
	docker run --rm -v $$(pwd):/app clair-scanner:latest /app

# Performance
load-test:
	@echo "Running load tests..."
	ab -n 1000 -c 10 -H "Authorization: Bearer test-key\" \
		-T \"application/json\" \
		-p test_data/sample_query.json \
		http://localhost:8000/api/v1/query

stress-test:
	@echo "Running stress tests..."
	wrk -t12 -c400 -d30s --script=scripts/stress_test.lua http://localhost:8000/

# Backup & Recovery
backup:
	@echo "Creating backup..."
	kubectl create backup neurorag-backup-$$(date +%Y%m%d-%H%M%S) -n $(NAMESPACE)

restore:
	@echo "Restoring from backup..."
	@echo "Please specify backup name: make restore BACKUP_NAME=<name>"
	kubectl restore $(BACKUP_NAME) -n $(NAMESPACE)

# Development helpers
shell-api:
	@echo "Opening shell in API Gateway container..."
	docker-compose exec api-gateway bash

shell-vector:
	@echo "Opening shell in Vector Service container..."
	docker-compose exec vector-service bash

shell-redis:
	@echo "Opening Redis CLI..."
	docker-compose exec redis redis-cli

# Documentation
docs:
	@echo "Generating documentation..."
	cd docs && make html
	@echo "Documentation available at docs/_build/html/index.html"

docs-serve:
	@echo "Serving documentation..."
	cd docs/_build/html && python -m http.server 8080

# Release
release:
	@echo "Creating release..."
	@echo "Current version: $$(git describe --tags --abbrev=0)"
	@echo "Please run: git tag -a v<version> -m 'Release v<version>'"
	@echo "Then: git push origin v<version>"

# CI/CD helpers
ci-setup:
	@echo "Setting up CI/CD..."
	gh workflow run .github/workflows/ci.yml

cd-deploy:
	@echo "Triggering deployment..."
	gh workflow run .github/workflows/deploy.yml

# Quick start for new developers
quickstart:
	@echo "Quick Start"
	@echo "======================"
	@echo ""
	@echo "1. Setting up development environment..."
	make setup-dev
	@echo ""
	@echo "2. Starting services..."
	make docker-dev
	@echo ""
	@echo "3. Ingesting sample data..."
	make ingest-data
	@echo ""
	@echo "4. Warming up cache..."
	make warmup-cache
	@echo ""
	@echo "Setup complete! Access the application at:"
	@echo "   Frontend: http://localhost:5173"
	@echo "   API: http://localhost:8000"
	@echo ""
	@echo "Run 'make health-check' to verify all services are running."