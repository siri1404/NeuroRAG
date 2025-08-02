"""
Rate Limiting Middleware for NeuroRAG API Gateway
Implements sliding window rate limiting using Redis
"""

import time
import asyncio
from typing import Optional
import redis.asyncio as redis
import structlog

logger = structlog.get_logger(__name__)

class RateLimiter:
    """Redis-based sliding window rate limiter"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    async def check_rate_limit(
        self,
        key: str,
        window_seconds: int,
        max_requests: int
    ) -> bool:
        """
        Check if request is within rate limit using sliding window
        
        Args:
            key: Unique identifier for the client/user
            window_seconds: Time window in seconds
            max_requests: Maximum requests allowed in the window
            
        Returns:
            True if request is allowed, False if rate limited
        """
        try:
            current_time = time.time()
            pipeline = self.redis.pipeline()
            
            # Remove expired entries
            pipeline.zremrangebyscore(
                key,
                0,
                current_time - window_seconds
            )
            
            # Count current requests in window
            pipeline.zcard(key)
            
            # Add current request
            pipeline.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipeline.expire(key, window_seconds)
            
            results = await pipeline.execute()
            current_requests = results[1]
            
            if current_requests >= max_requests:
                # Remove the request we just added since it's rate limited
                await self.redis.zrem(key, str(current_time))
                
                logger.warning(
                    "Rate limit exceeded",
                    key=key,
                    current_requests=current_requests,
                    max_requests=max_requests,
                    window_seconds=window_seconds
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error("Rate limiting error", error=str(e), key=key)
            # Fail open - allow request if rate limiting fails
            return True
    
    async def get_rate_limit_info(
        self,
        key: str,
        window_seconds: int,
        max_requests: int
    ) -> dict:
        """
        Get current rate limit information for a key
        
        Returns:
            Dictionary with rate limit info
        """
        try:
            current_time = time.time()
            
            # Clean up expired entries
            await self.redis.zremrangebyscore(
                key,
                0,
                current_time - window_seconds
            )
            
            # Get current count
            current_requests = await self.redis.zcard(key)
            
            # Get oldest request time in current window
            oldest_requests = await self.redis.zrange(key, 0, 0, withscores=True)
            oldest_time = oldest_requests[0][1] if oldest_requests else current_time
            
            # Calculate reset time
            reset_time = oldest_time + window_seconds
            
            return {
                "limit": max_requests,
                "remaining": max(0, max_requests - current_requests),
                "reset": int(reset_time),
                "window": window_seconds
            }
            
        except Exception as e:
            logger.error("Error getting rate limit info", error=str(e), key=key)
            return {
                "limit": max_requests,
                "remaining": max_requests,
                "reset": int(time.time() + window_seconds),
                "window": window_seconds
            }
    
    async def reset_rate_limit(self, key: str) -> bool:
        """
        Reset rate limit for a specific key
        
        Args:
            key: The rate limit key to reset
            
        Returns:
            True if reset successful, False otherwise
        """
        try:
            await self.redis.delete(key)
            logger.info("Rate limit reset", key=key)
            return True
        except Exception as e:
            logger.error("Error resetting rate limit", error=str(e), key=key)
            return False

class AdaptiveRateLimiter(RateLimiter):
    """
    Adaptive rate limiter that adjusts limits based on system load
    """
    
    def __init__(self, redis_client: redis.Redis):
        super().__init__(redis_client)
        self.base_limits = {}
        self.load_factor = 1.0
        
    async def update_load_factor(self, cpu_usage: float, memory_usage: float):
        """
        Update load factor based on system metrics
        
        Args:
            cpu_usage: CPU usage percentage (0-100)
            memory_usage: Memory usage percentage (0-100)
        """
        # Simple load calculation - can be made more sophisticated
        system_load = max(cpu_usage, memory_usage) / 100.0
        
        if system_load > 0.9:
            self.load_factor = 0.5  # Reduce limits by 50%
        elif system_load > 0.7:
            self.load_factor = 0.75  # Reduce limits by 25%
        elif system_load > 0.5:
            self.load_factor = 0.9   # Reduce limits by 10%
        else:
            self.load_factor = 1.0   # Normal limits
            
        logger.info(
            "Load factor updated",
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            load_factor=self.load_factor
        )
    
    async def check_adaptive_rate_limit(
        self,
        key: str,
        window_seconds: int,
        base_max_requests: int
    ) -> bool:
        """
        Check rate limit with adaptive adjustment
        """
        # Adjust max requests based on current load
        adjusted_max_requests = int(base_max_requests * self.load_factor)
        
        return await self.check_rate_limit(
            key,
            window_seconds,
            adjusted_max_requests
        )

class HierarchicalRateLimiter:
    """
    Hierarchical rate limiter supporting multiple limit levels
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.base_limiter = RateLimiter(redis_client)
        
    async def check_hierarchical_limits(
        self,
        limits: list,
        base_key: str
    ) -> tuple[bool, Optional[dict]]:
        """
        Check multiple rate limits in hierarchy
        
        Args:
            limits: List of (window_seconds, max_requests) tuples
            base_key: Base key for rate limiting
            
        Returns:
            (allowed, violated_limit_info)
        """
        for window_seconds, max_requests in limits:
            key = f"{base_key}:{window_seconds}"
            
            if not await self.base_limiter.check_rate_limit(
                key, window_seconds, max_requests
            ):
                # Get info about the violated limit
                limit_info = await self.base_limiter.get_rate_limit_info(
                    key, window_seconds, max_requests
                )
                limit_info["window"] = window_seconds
                
                return False, limit_info
        
        return True, None

class TokenBucketRateLimiter:
    """
    Token bucket rate limiter implementation
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    async def check_token_bucket(
        self,
        key: str,
        capacity: int,
        refill_rate: float,
        tokens_requested: int = 1
    ) -> bool:
        """
        Check token bucket rate limit
        
        Args:
            key: Unique identifier
            capacity: Maximum tokens in bucket
            refill_rate: Tokens added per second
            tokens_requested: Number of tokens requested
            
        Returns:
            True if tokens available, False otherwise
        """
        try:
            current_time = time.time()
            
            # Get current bucket state
            bucket_data = await self.redis.hmget(
                key, "tokens", "last_refill"
            )
            
            current_tokens = float(bucket_data[0] or capacity)
            last_refill = float(bucket_data[1] or current_time)
            
            # Calculate tokens to add based on time elapsed
            time_elapsed = current_time - last_refill
            tokens_to_add = time_elapsed * refill_rate
            
            # Update token count (capped at capacity)
            new_tokens = min(capacity, current_tokens + tokens_to_add)
            
            if new_tokens >= tokens_requested:
                # Consume tokens
                remaining_tokens = new_tokens - tokens_requested
                
                # Update bucket state
                await self.redis.hmset(key, {
                    "tokens": remaining_tokens,
                    "last_refill": current_time
                })
                
                # Set expiration
                await self.redis.expire(key, int(capacity / refill_rate) + 60)
                
                return True
            else:
                # Not enough tokens, update state without consuming
                await self.redis.hmset(key, {
                    "tokens": new_tokens,
                    "last_refill": current_time
                })
                
                logger.warning(
                    "Token bucket limit exceeded",
                    key=key,
                    available_tokens=new_tokens,
                    requested_tokens=tokens_requested
                )
                
                return False
                
        except Exception as e:
            logger.error("Token bucket error", error=str(e), key=key)
            # Fail open
            return True