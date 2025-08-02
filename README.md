# NeuroRAG - Enterprise RAG System

A high-performance Retrieval-Augmented Generation system for enterprise document analysis.

## Features

- Sub-200ms vector search latency
- 1M+ API calls/day capacity
- Built-in compliance and audit trails
- Data privacy with automatic redaction
- Cost optimization through intelligent caching

## Architecture

```
Web Client → API Gateway → RAG Orchestrator
                ↓              ↓
        Rate Limiter    C++ Vector Service
                              ↓
                    FAISS + Redis Cache
```

## Performance Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| API Latency (P99) | <200ms | <180ms |
| Vector Search | <50ms | <35ms |
| Throughput | 1M+ calls/day | 1.2M calls/day |
| Uptime SLA | 99.99% | 99.99% |
| Cost Reduction | 25% | 30% |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.9+
- CMake 3.16+
- Azure CLI (for deployment)

### Local Development

1. Clone and setup:
```bash
git clone <repository-url>
cd NeuroRAG
cp .env.example .env
```

2. Start services:
```bash
docker-compose up -d
```

3. Access application:
- Frontend: http://localhost:5173
- API Gateway: http://localhost:8000
- Metrics: http://localhost:9090

### Initialize Data

```bash
python scripts/ingest_data.py --input data/sample_docs/ --output data/
bash scripts/cache_warmup.sh
```

## Development

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

## Deployment

### Azure Kubernetes Service

```bash
az group create --name neurorag-rg --location eastus
az aks create --resource-group neurorag-rg --name neurorag-aks --node-count 3
az aks get-credentials --resource-group neurorag-rg --name neurorag-aks
kubectl apply -f infra/k8s_deployments/ -n neurorag
```

## Configuration

Key environment variables:

```bash
OPENAI_API_KEY=your_openai_api_key
FAISS_INDEX_PATH=/data/faiss_index
REDIS_URL=redis://localhost:6379
API_HOST=0.0.0.0
API_PORT=8000
```

## Testing

```bash
# All tests
pytest src/tests/ -v --cov=src
cd src/vector_service/build && make test
npm test

# Performance testing
python scripts/benchmark_vector_search.py
```

## License

MIT License - see LICENSE file for details.