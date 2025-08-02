# NeuroRAG Setup Guide

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Python 3.9+
- Git

### Required API Keys

#### OpenAI API (Required)
- Sign up: https://platform.openai.com/
- Create API key: https://platform.openai.com/api-keys
- Add to `.env`: `OPENAI_API_KEY=your_key_here`
- Cost: ~$0.01-0.03 per query

#### Supabase (Optional)
- Sign up: https://supabase.com/
- Create project and get URL + anon key
- Add to `.env`:
  ```
  VITE_SUPABASE_URL=your_project_url
  VITE_SUPABASE_ANON_KEY=your_anon_key
  ```

### Setup Steps

1. Clone and setup:
```bash
git clone <repository-url>
cd NeuroRAG
cp .env.example .env
```

2. Start services:
```bash
docker-compose up -d
docker-compose ps
docker-compose logs -f
```

3. Access application:
- Frontend: http://localhost:5173
- API Gateway: http://localhost:8000
- Vector Service: http://localhost:8001
- Metrics: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

4. Initialize data:
```bash
python scripts/ingest_data.py --input data/sample_docs/ --output data/
bash scripts/cache_warmup.sh
```

## Development Setup

### Frontend
```bash
npm install
npm run dev
npm test
```

### Python Services
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd src/api_gateway
python app.py
pytest src/tests/
```

### C++ Vector Service
```bash
sudo apt-get install -y build-essential cmake libblas-dev liblapack-dev libhiredis-dev
cd src/vector_service
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
./vector_service
```

## Production Deployment

### Azure Kubernetes Service

1. Prerequisites:
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az aks install-cli
curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
sudo mv linux-amd64/helm /usr/local/bin/
```

2. Azure setup:
```bash
az login
az group create --name neurorag-rg --location eastus
az aks create --resource-group neurorag-rg --name neurorag-aks --node-count 3
az aks get-credentials --resource-group neurorag-rg --name neurorag-aks
```

3. Deploy:
```bash
kubectl create namespace neurorag
kubectl apply -f infra/k8s_deployments/ -n neurorag
helm install neurorag ./infra/helm_charts/neurorag -n neurorag
```

4. Verify:
```bash
kubectl get pods -n neurorag
kubectl get services -n neurorag
kubectl logs -f deployment/neurorag-api-gateway -n neurorag
```

## Configuration

### Environment Variables
```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4-turbo-preview

# Vector Database
FAISS_INDEX_PATH=/data/faiss_index
VECTOR_DIMENSION=1536

# Redis
REDIS_URL=redis://localhost:6379

# API
API_HOST=0.0.0.0
API_PORT=8000

# Security
JWT_SECRET_KEY=your_jwt_secret_key
ADMIN_API_KEY=your_admin_api_key
```

## Monitoring

### Metrics
```bash
curl http://localhost:9090/metrics
open http://localhost:3000
```

### Health Checks
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8000/api/v1/status
```

### Logs
```bash
docker-compose logs api-gateway | jq '.'
docker-compose logs vector-service | grep "latency"
```

## Testing

### Unit Tests
```bash
pytest src/tests/ -v --cov=src
cd src/vector_service/build && make test
```

### Integration Tests
```bash
docker-compose -f docker-compose.test.yml up -d
sleep 10
pytest src/tests/integration/ -v
docker-compose -f docker-compose.test.yml down
```

### Performance Testing
```bash
python scripts/benchmark_vector_search.py \
  --index data/faiss_index.bin \
  --config data/config.json \
  --output benchmark_results/

ab -n 1000 -c 10 http://localhost:8000/api/v1/query
```

## Security

### API Authentication
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8000/api/v1/query
```

### SSL/TLS
```bash
# Development
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Production
certbot --nginx -d your-domain.com
```

## Troubleshooting

### Common Issues

#### Vector Service Won't Start
```bash
python -c "import faiss; print(faiss.__version__)"
ldd src/vector_service/build/vector_service
```

#### Redis Connection Issues
```bash
redis-cli ping
docker-compose logs redis
```

#### High Memory Usage
```bash
docker stats
# Adjust memory limits in docker-compose.yml
```

#### Slow Query Performance
```bash
python scripts/benchmark_vector_search.py --analyze
curl http://localhost:8000/metrics | grep cache_hit_rate
```

### Debug Mode
```bash
export LOG_LEVEL=DEBUG
python -m cProfile src/api_gateway/app.py
```

## Scaling

### Horizontal Scaling
```bash
kubectl scale deployment neurorag-api-gateway --replicas=5 -n neurorag
kubectl scale deployment neurorag-vector-service --replicas=3 -n neurorag
```

### Performance Tuning
```bash
python scripts/optimize_index.py --input data/faiss_index.bin
redis-cli config set maxmemory 4gb
redis-cli config set maxmemory-policy allkeys-lru
```

## CI/CD Pipeline

The GitHub Actions pipeline:
1. Runs code quality checks
2. Builds and tests components
3. Creates Docker images
4. Deploys to staging/production
5. Runs smoke tests

### Manual Deployment
```bash
docker build -t neurorag/api-gateway src/api_gateway/
docker build -t neurorag/vector-service src/vector_service/
docker push neurorag/api-gateway
docker push neurorag/vector-service
kubectl set image deployment/neurorag-api-gateway api-gateway=neurorag/api-gateway:latest -n neurorag
```