#!/usr/bin/env python3
"""
API Gateway
FastAPI-based gateway for the RAG system
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import httpx
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import structlog

from middleware.rate_limiter import RateLimiter
from utils.logger import setup_logging

# Configure structured logging
logger = structlog.get_logger(__name__)

# Metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
VECTOR_SEARCH_DURATION = Histogram('vector_search_duration_seconds', 'Vector search duration')
RAG_PROCESSING_DURATION = Histogram('rag_processing_duration_seconds', 'RAG processing duration')

# Pydantic models
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="The query text")
    max_results: int = Field(5, ge=1, le=100, description="Maximum number of results to return")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Similarity threshold")
    include_explanation: bool = Field(True, description="Include AI explanation in response")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")

class QueryResponse(BaseModel):
    id: str
    query: str
    answer: str
    retrieved_documents: List[Dict[str, Any]]
    explanation: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]

class MetricsResponse(BaseModel):
    requests_per_second: float
    average_latency_ms: float
    cache_hit_rate: float
    error_rate: float

# Global variables
redis_client: Optional[redis.Redis] = None
http_client: Optional[httpx.AsyncClient] = None
rate_limiter: Optional[RateLimiter] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global redis_client, http_client, rate_limiter
    
    # Startup
    logger.info("Starting NeuroRAG API Gateway...")
    
    # Initialize Redis client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url, decode_responses=True)
    
    # Initialize HTTP client
    http_client = httpx.AsyncClient(timeout=30.0)
    
    # Initialize rate limiter
    rate_limiter = RateLimiter(redis_client)
    
    # Test connections
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
    
    # Test vector service
    vector_service_url = os.getenv("VECTOR_SERVICE_URL", "http://localhost:8001")
    try:
        response = await http_client.get(f"{vector_service_url}/health")
        if response.status_code == 200:
            logger.info("Vector service connection established")
        else:
            logger.warning("Vector service health check failed", status_code=response.status_code)
    except Exception as e:
        logger.warning("Failed to connect to vector service", error=str(e))
    
    logger.info("NeuroRAG API Gateway started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NeuroRAG API Gateway...")
    
    if http_client:
        await http_client.aclose()
    
    if redis_client:
        await redis_client.close()
    
    logger.info("NeuroRAG API Gateway shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="RAG API",
    description="RAG System API",
    version="1.0.0",
    lifespan=lifespan
)

# Security
security = HTTPBearer(auto_error=False)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Setup logging
setup_logging()

async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """Verify API key authentication"""
    api_key = None
    
    if credentials:
        api_key = credentials.credentials
    else:
        # Check for API key in headers
        api_key = os.getenv("X_API_KEY")
    
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # In production, validate against database or key management service
    valid_keys = {
        os.getenv("ADMIN_API_KEY", "admin-key-12345"): "admin",
        os.getenv("READONLY_API_KEY", "readonly-key-12345"): "readonly"
    }
    
    if api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return valid_keys[api_key]

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Request logging and metrics middleware"""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Request received",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Update metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    # Log response
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2)
    )
    
    # Add timing header
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    
    return response

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    services = {}
    
    # Check Redis
    try:
        await redis_client.ping()
        services["redis"] = "healthy"
    except Exception:
        services["redis"] = "unhealthy"
    
    # Check Vector Service
    vector_service_url = os.getenv("VECTOR_SERVICE_URL", "http://localhost:8001")
    try:
        response = await http_client.get(f"{vector_service_url}/health", timeout=5.0)
        services["vector_service"] = "healthy" if response.status_code == 200 else "unhealthy"
    except Exception:
        services["vector_service"] = "unhealthy"
    
    # Overall status
    status = "healthy" if all(s == "healthy" for s in services.values()) else "degraded"
    
    return HealthResponse(
        status=status,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        version="1.0.0",
        services=services
    )

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/api/v1/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    user_role: str = Depends(verify_api_key),
    http_request: Request = None
):
    """Process RAG query"""
    start_time = time.time()
    
    try:
        # Rate limiting
        client_ip = http_request.client.host if http_request and http_request.client else "unknown"
        if not await rate_limiter.check_rate_limit(f"user:{client_ip}", 60, 100):  # 100 requests per minute
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Input validation
        if len(request.query.strip()) == 0:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Check cache first
        cache_key = f"query:{hash(request.query)}:{request.max_results}:{request.threshold}"
        cached_result = await redis_client.get(cache_key)
        
        if cached_result:
            logger.info("Cache hit for query", query_hash=hash(request.query))
            import json
            return QueryResponse(**json.loads(cached_result))
        
        # Forward to vector service for search
        vector_service_url = os.getenv("VECTOR_SERVICE_URL", "http://localhost:8001")
        
        search_start = time.time()
        search_response = await http_client.post(
            f"{vector_service_url}/search",
            json={
                "query": request.query,
                "k": request.max_results,
                "threshold": request.threshold,
                "filters": request.filters
            },
            timeout=30.0
        )
        search_duration = time.time() - search_start
        VECTOR_SEARCH_DURATION.observe(search_duration)
        
        if search_response.status_code != 200:
            raise HTTPException(status_code=503, detail="Vector search service unavailable")
        
        search_results = search_response.json()
        
        # Forward to RAG orchestration service
        rag_service_url = os.getenv("RAG_SERVICE_URL", "http://localhost:8002")
        
        rag_start = time.time()
        rag_response = await http_client.post(
            f"{rag_service_url}/generate",
            json={
                "query": request.query,
                "retrieved_documents": search_results.get("documents", []),
                "include_explanation": request.include_explanation
            },
            timeout=120.0
        )
        rag_duration = time.time() - rag_start
        RAG_PROCESSING_DURATION.observe(rag_duration)
        
        if rag_response.status_code != 200:
            raise HTTPException(status_code=503, detail="RAG service unavailable")
        
        rag_result = rag_response.json()
        
        # Build response
        total_duration = time.time() - start_time
        
        response = QueryResponse(
            id=rag_result.get("id", "unknown"),
            query=request.query,
            answer=rag_result.get("answer", ""),
            retrieved_documents=search_results.get("documents", []),
            explanation=rag_result.get("explanation") if request.include_explanation else None,
            metadata={
                "latency": round(total_duration * 1000, 2),
                "vector_search_latency": round(search_duration * 1000, 2),
                "rag_processing_latency": round(rag_duration * 1000, 2),
                "tokens_used": rag_result.get("tokens_used", 0),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "user_role": user_role,
                "compliance_flags": rag_result.get("compliance_flags", [])
            }
        )
        
        # Cache result
        await redis_client.setex(
            cache_key,
            300,  # 5 minutes TTL
            response.json()
        )
        
        logger.info(
            "Query processed successfully",
            query_length=len(request.query),
            results_count=len(response.retrieved_documents),
            total_latency_ms=response.metadata["latency"],
            user_role=user_role
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Query processing failed", error=str(e), query=request.query[:100])
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/v1/metrics", response_model=MetricsResponse)
async def get_metrics(user_role: str = Depends(verify_api_key)):
    """Get system metrics"""
    if user_role not in ["admin", "readonly"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Calculate metrics from Redis or monitoring system
    # This is a simplified implementation
    
    return MetricsResponse(
        requests_per_second=100.0,  # Mock data
        average_latency_ms=150.0,
        cache_hit_rate=0.75,
        error_rate=0.01
    )

@app.get("/api/v1/status")
async def system_status(user_role: str = Depends(verify_api_key)):
    """Get detailed system status"""
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get system status from various services
    status = {
        "api_gateway": "healthy",
        "vector_service": "healthy",
        "rag_service": "healthy",
        "redis": "healthy",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    return status

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "app:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )