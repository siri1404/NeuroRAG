#!/usr/bin/env python3
"""
RAG Orchestration Service
GPT-4 Pipeline for RAG processing
"""

import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class RAGRequest(BaseModel):
    query: str
    retrieved_documents: List[Dict[str, Any]]
    include_explanation: bool = True

class RAGResponse(BaseModel):
    id: str
    answer: str
    explanation: Optional[Dict[str, Any]] = None
    tokens_used: int
    compliance_flags: List[str]

class RAGOrchestrationService:
    def __init__(self):
        self.app = FastAPI(title="RAG Orchestration Service", version="1.0.0")
        self.redis_client = None
        self.openai_client = None
        self.vector_service_url = os.getenv("VECTOR_SERVICE_URL", "http://localhost:8001")
        
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
        logger.info("Starting RAG Service...")
        
        # Initialize Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(redis_url)
        
        # Initialize OpenAI client
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
            logger.info("OpenAI client initialized")
        else:
            logger.warning("OpenAI API key not provided")
        
        logger.info("RAG Orchestration Service started successfully")
        logger.info("RAG Service started")
    
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
                    "openai": "configured" if self.openai_client else "not_configured",
                    "vector_service": await self.check_vector_service()
                }
            }
        
        @self.app.post("/generate", response_model=RAGResponse)
        async def generate_response(request: RAGRequest):
            try:
                # Generate unique ID for this request
                request_id = f"rag_{int(datetime.utcnow().timestamp() * 1000)}"
                
                # Prepare context from retrieved documents
                context = self.prepare_context(request.retrieved_documents)
                
                # Generate response
                if self.openai_client:
                    answer, tokens_used = await self.generate_with_openai(request.query, context)
                else:
                    answer, tokens_used = self.generate_fallback_response(request.query, request.retrieved_documents)
                
                # Check compliance
                compliance_flags = self.check_compliance(request.retrieved_documents, answer)
                
                # Generate explanation if requested
                explanation = None
                if request.include_explanation:
                    explanation = self.generate_explanation(request.query, answer, request.retrieved_documents)
                
                # Cache the response
                if self.redis_client:
                    cache_key = f"rag_response:{hash(request.query)}"
                    await self.redis_client.setex(
                        cache_key,
                        1800,  # 30 minutes TTL
                        json.dumps({
                            "answer": answer,
                            "tokens_used": tokens_used,
                            "compliance_flags": compliance_flags
                        })
                    )
                
                return RAGResponse(
                    id=request_id,
                    answer=answer,
                    explanation=explanation,
                    tokens_used=tokens_used,
                    compliance_flags=compliance_flags
                )
                
            except Exception as e:
                logger.error(f"RAG generation error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def check_vector_service(self) -> str:
        """Check if vector service is available"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.vector_service_url}/health", timeout=5.0)
                return "connected" if response.status_code == 200 else "error"
        except:
            return "disconnected"
    
    def prepare_context(self, documents: List[Dict[str, Any]]) -> str:
        context_parts = []
        max_context_length = 4000
        current_length = 0
        
        for doc in documents:
            doc_context = f"Title: {doc.get('title', 'Unknown')}\n"
            doc_context += f"Content: {doc.get('content', '')}\n"
            doc_context += f"Relevance: {doc.get('relevance_reason', 'N/A')}\n\n"
            
            if current_length + len(doc_context) <= max_context_length:
                context_parts.append(doc_context)
                current_length += len(doc_context)
            else:
                remaining_space = max_context_length - current_length - 50
                if remaining_space > 100:
                    truncated_content = doc.get('content', '')[:remaining_space] + "..."
                    context_parts.append(f"Title: {doc.get('title', 'Unknown')}\nContent: {truncated_content}\n\n")
                break
        
        return "".join(context_parts)
    
    async def generate_with_openai(self, query: str, context: str) -> tuple[str, int]:
        try:
            system_prompt = """You are an AI assistant for document analysis. 
            Provide accurate responses based on the provided context. 
            If the context doesn't contain sufficient information, clearly state this limitation.
            Be concise but comprehensive."""
            
            user_prompt = f"""Context from retrieved documents:
{context}

Question: {query}

Please provide a comprehensive answer based on the context above."""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.1
            )
            
            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            return answer, tokens_used
            
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            return self.generate_fallback_response(query, [])
    
    def generate_fallback_response(self, query: str, documents: List[Dict[str, Any]]) -> tuple[str, int]:
        if not documents:
            return ("I couldn't find relevant documents to answer your question. "
                   "Please try rephrasing your query or ensure documents are properly indexed."), 50
        
        # Simple keyword-based response
        doc_count = len(documents)
        avg_score = sum(doc.get('score', 0) for doc in documents) / doc_count if doc_count > 0 else 0
        
        response = f"""Based on {doc_count} retrieved document(s) with an average relevance score of {avg_score:.2f}, 
I found information related to your query. However, I need an OpenAI API key to provide detailed analysis.

Key documents found:
"""
        
        for i, doc in enumerate(documents[:3], 1):
            response += f"{i}. {doc.get('title', 'Unknown Document')} (Score: {doc.get('score', 0):.2f})\n"
        
        response += "\nPlease configure your OpenAI API key to enable AI-powered detailed responses."
        response += "\nPlease configure your OpenAI API key to enable detailed responses."
        
        return response, 100
    
    def check_compliance(self, documents: List[Dict[str, Any]], answer: str) -> List[str]:
        flags = []
        
        for doc in documents:
            classification = doc.get('metadata', {}).get('classification', 'public')
            if classification == 'restricted':
                flags.append('RESTRICTED_DATA_ACCESS')
        
        if '[REDACTED]' in answer:
            flags.append('SENSITIVE_DATA_REDACTED')
        
        import re
        if re.search(r'\b\d{3}-\d{2}-\d{4}\b', answer):
            flags.append('POTENTIAL_PII_IN_RESPONSE')
        
        return flags
    
    def generate_explanation(self, query: str, answer: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "reasoning": "Response generated by analyzing retrieved documents using semantic similarity.",
            "confidence_score": min(0.95, max(0.7, sum(doc.get('score', 0) for doc in documents) / len(documents) if documents else 0.7)),
            "source_influence": [
                {
                    "document_id": doc.get('id', 'unknown'),
                    "influence": doc.get('score', 0),
                    "reason": f"{doc.get('score', 0):.1%} relevance based on semantic similarity"
                }
                for doc in documents[:5]
            ]
        }

def main():
    service = RAGOrchestrationService()
    
    # Run the service
    uvicorn.run(
        service.app,
        host=os.getenv("RAG_SERVICE_HOST", "0.0.0.0"),
        port=int(os.getenv("RAG_SERVICE_PORT", 8002)),
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )

if __name__ == "__main__":
    main()