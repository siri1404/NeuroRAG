#!/usr/bin/env python3
"""
Vector Search Service
Vector similarity search with FAISS
"""

import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np
import faiss
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from sentence_transformers import SentenceTransformer
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    k: int = 5
    threshold: float = 0.7
    filters: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    documents: List[Dict[str, Any]]
    latency_ms: float
    total_results: int

class Document(BaseModel):
    id: str
    title: str
    content: str
    metadata: Dict[str, Any]

class VectorSearchService:
    def __init__(self):
        self.app = FastAPI(title="Vector Service", version="1.0.0")
        self.redis_client = None
        self.db_connection = None
        self.embedding_model = None
        self.faiss_index = None
        self.documents = []
        
        # Setup middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self.setup_routes()
    
    async def startup(self):
        logger.info("Starting Vector Service...")
        
        # Initialize Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(redis_url)
        
        # Initialize database connection
        db_url = os.getenv("DATABASE_URL", "postgresql://neurorag:neurorag_password@localhost:5432/neurorag")
        try:
            self.db_connection = psycopg2.connect(db_url)
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
        
        # Initialize FAISS index
        self.initialize_faiss_index()
        
        logger.info("Vector Search Service started successfully")
        logger.info("Vector Service started")
    
    def initialize_faiss_index(self):
        """Initialize FAISS index"""
        try:
            dimension = 384  # all-MiniLM-L6-v2 dimension
            self.faiss_index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            logger.info(f"FAISS index initialized with dimension {dimension}")
        except Exception as e:
            logger.error(f"Failed to initialize FAISS index: {e}")
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.on_event("startup")
        async def startup_event():
            await self.startup()
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "components": {
                    "redis": "connected" if self.redis_client else "disconnected",
                    "database": "connected" if self.db_connection else "disconnected",
                    "faiss": "initialized" if self.faiss_index else "not_initialized",
                    "embedding_model": "loaded" if self.embedding_model else "not_loaded"
                }
            }
        
        @self.app.post("/search", response_model=SearchResponse)
        async def search_vectors(request: SearchRequest):
            start_time = asyncio.get_event_loop().time()
            
            try:
                # Generate query embedding
                if not self.embedding_model:
                    raise HTTPException(status_code=503, detail="Embedding model not available")
                
                query_embedding = self.embedding_model.encode([request.query])
                query_embedding = query_embedding.astype(np.float32)
                
                # Normalize for cosine similarity
                faiss.normalize_L2(query_embedding)
                
                # Search in FAISS index
                if self.faiss_index.ntotal == 0:
                    # No documents indexed yet
                    return SearchResponse(
                        documents=[],
                        latency_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
                        total_results=0
                    )
                
                scores, indices = self.faiss_index.search(query_embedding, min(request.k, self.faiss_index.ntotal))
                
                # Filter by threshold and prepare results
                results = []
                for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                    if score >= request.threshold and idx < len(self.documents):
                        doc = self.documents[idx]
                        results.append({
                            "id": doc["id"],
                            "title": doc["title"],
                            "content": doc["content"],
                            "metadata": doc["metadata"],
                            "score": float(score),
                            "relevance_reason": f"Semantic similarity score: {score:.3f}"
                        })
                
                latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                return SearchResponse(
                    documents=results,
                    latency_ms=latency_ms,
                    total_results=len(results)
                )
                
            except Exception as e:
                logger.error(f"Search error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/documents")
        async def add_document(document: Document):
            try:
                if not self.embedding_model:
                    raise HTTPException(status_code=503, detail="Embedding model not available")
                
                # Generate embedding
                embedding = self.embedding_model.encode([document.content])
                embedding = embedding.astype(np.float32)
                
                # Normalize for cosine similarity
                faiss.normalize_L2(embedding)
                
                # Add to FAISS index
                self.faiss_index.add(embedding)
                
                # Store document
                doc_dict = {
                    "id": document.id,
                    "title": document.title,
                    "content": document.content,
                    "metadata": document.metadata
                }
                self.documents.append(doc_dict)
                
                # Cache in Redis
                if self.redis_client:
                    await self.redis_client.setex(
                        f"doc:{document.id}",
                        3600,  # 1 hour TTL
                        json.dumps(doc_dict)
                    )
                
                logger.info(f"Document {document.id} added successfully")
                return {"status": "success", "document_id": document.id}
                
            except Exception as e:
                logger.error(f"Error adding document: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/documents")
        async def list_documents():
            return {
                "documents": self.documents,
                "total_count": len(self.documents),
                "index_size": self.faiss_index.ntotal if self.faiss_index else 0
            }
        
        @self.app.delete("/documents/{document_id}")
        async def delete_document(document_id: str):
            try:
                # Find document index
                doc_index = None
                for i, doc in enumerate(self.documents):
                    if doc["id"] == document_id:
                        doc_index = i
                        break
                
                if doc_index is None:
                    raise HTTPException(status_code=404, detail="Document not found")
                
                # Remove from documents list
                self.documents.pop(doc_index)
                
                # Note: FAISS doesn't support individual vector removal easily
                # In production, you'd rebuild the index or use a different approach
                
                # Remove from Redis cache
                if self.redis_client:
                    await self.redis_client.delete(f"doc:{document_id}")
                
                logger.info(f"Document {document_id} deleted successfully")
                return {"status": "success", "document_id": document_id}
                
            except Exception as e:
                logger.error(f"Error deleting document: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/metrics")
        async def get_metrics():
            return {
                "total_documents": len(self.documents),
                "index_size": self.faiss_index.ntotal if self.faiss_index else 0,
                "embedding_dimension": 384,
                "cache_status": "connected" if self.redis_client else "disconnected"
            }

def main():
    service = VectorSearchService()
    
    # Run the service
    uvicorn.run(
        service.app,
        host=os.getenv("VECTOR_SERVICE_HOST", "0.0.0.0"),
        port=int(os.getenv("VECTOR_SERVICE_PORT", 8001)),
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )

if __name__ == "__main__":
    main()