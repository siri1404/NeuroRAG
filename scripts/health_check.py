#!/usr/bin/env python3
"""
Health Check Script
Health monitoring for system components
"""

import asyncio
import json
import sys
import time
from typing import Dict, List, Optional
import aiohttp
import redis
import psycopg2
from dataclasses import dataclass
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ServiceHealth:
    name: str
    status: HealthStatus
    response_time_ms: float
    details: Dict[str, any]
    error: Optional[str] = None

class HealthChecker:
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.results: List[ServiceHealth] = []
    
    async def check_http_service(self, name: str, url: str, timeout: int = 5) -> ServiceHealth:
        """Check HTTP service health"""
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(f"{url}/health") as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        return ServiceHealth(
                            name=name,
                            status=HealthStatus.HEALTHY,
                            response_time_ms=response_time,
                            details=data
                        )
                    else:
                        return ServiceHealth(
                            name=name,
                            status=HealthStatus.UNHEALTHY,
                            response_time_ms=response_time,
                            details={"status_code": response.status},
                            error=f"HTTP {response.status}"
                        )
        
        except asyncio.TimeoutError:
            return ServiceHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details={},
                error="Timeout"
            )
        except Exception as e:
            return ServiceHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details={},
                error=str(e)
            )
    
    def check_redis(self) -> ServiceHealth:
        """Check Redis health"""
        start_time = time.time()
        
        try:
            redis_client = redis.from_url(self.config.get("REDIS_URL", "redis://localhost:6379"))
            
            # Test basic operations
            redis_client.ping()
            redis_client.set("health_check", "test", ex=10)
            value = redis_client.get("health_check")
            redis_client.delete("health_check")
            
            response_time = (time.time() - start_time) * 1000
            
            info = redis_client.info()
            
            return ServiceHealth(
                name="Redis",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={
                    "version": info.get("redis_version"),
                    "connected_clients": info.get("connected_clients"),
                    "used_memory_human": info.get("used_memory_human"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                }
            )
        
        except Exception as e:
            return ServiceHealth(
                name="Redis",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details={},
                error=str(e)
            )
    
    def check_database(self) -> ServiceHealth:
        """Check PostgreSQL database health"""
        start_time = time.time()
        
        try:
            conn = psycopg2.connect(
                self.config.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/neurorag")
            )
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
                table_count = cursor.fetchone()[0]
            
            conn.close()
            response_time = (time.time() - start_time) * 1000
            
            return ServiceHealth(
                name="PostgreSQL",
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={
                    "version": version,
                    "table_count": table_count
                }
            )
        
        except Exception as e:
            return ServiceHealth(
                name="PostgreSQL",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details={},
                error=str(e)
            )
    
    async def check_all_services(self) -> List[ServiceHealth]:
        """Check all services"""
        tasks = []
        
        # HTTP services
        services = [
            ("API Gateway", self.config.get("API_GATEWAY_URL", "http://localhost:8000")),
            ("Vector Service", self.config.get("VECTOR_SERVICE_URL", "http://localhost:8001")),
            ("RAG Orchestrator", self.config.get("RAG_SERVICE_URL", "http://localhost:8002")),
        ]
        
        for name, url in services:
            tasks.append(self.check_http_service(name, url))
        
        # Run HTTP checks concurrently
        http_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Add HTTP results
        for result in http_results:
            if isinstance(result, ServiceHealth):
                self.results.append(result)
            else:
                self.results.append(ServiceHealth(
                    name="Unknown Service",
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=0,
                    details={},
                    error=str(result)
                ))
        
        # Check databases
        self.results.append(self.check_redis())
        self.results.append(self.check_database())
        
        return self.results
    
    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status"""
        if not self.results:
            return HealthStatus.UNKNOWN
        
        unhealthy_count = sum(1 for r in self.results if r.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for r in self.results if r.status == HealthStatus.DEGRADED)
        
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def print_results(self, format_type: str = "table"):
        """Print health check results"""
        if format_type == "json":
            output = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "overall_status": self.get_overall_status().value,
                "services": [
                    {
                        "name": r.name,
                        "status": r.status.value,
                        "response_time_ms": r.response_time_ms,
                        "details": r.details,
                        "error": r.error
                    }
                    for r in self.results
                ]
            }
            print(json.dumps(output, indent=2))
        
        else:  # table format
            print("\nHealth Check Results")
            print("=" * 50)
            print(f"Overall Status: {self.get_overall_status().value.upper()}")
            print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
            print()
            
            # Print service status table
            print(f"{'Service':<20} {'Status':<12} {'Response Time':<15} {'Details'}")
            print("-" * 70)
            
            for result in self.results:
                status_icon = {
                    HealthStatus.HEALTHY: "✅",
                    HealthStatus.DEGRADED: "⚠️",
                    HealthStatus.UNHEALTHY: "❌",
                    HealthStatus.UNKNOWN: "❓"
                }.get(result.status, "❓")
                
                details_str = ""
                if result.error:
                    details_str = f"Error: {result.error}"
                elif result.details:
                    key_details = []
                    for key, value in list(result.details.items())[:2]:
                        key_details.append(f"{key}: {value}")
                    details_str = ", ".join(key_details)
                
                print(f"{result.name:<20} {status_icon} {result.status.value:<10} {result.response_time_ms:>6.1f}ms      {details_str}")
            
            print()
            
            # Print recommendations
            unhealthy_services = [r for r in self.results if r.status == HealthStatus.UNHEALTHY]
            if unhealthy_services:
                print("Issues Detected:")
                for service in unhealthy_services:
                    print(f"  - {service.name}: {service.error or 'Service unavailable'}")
                print()
                
                print("Troubleshooting Steps:")
                print("  1. Check if all services are running: docker-compose ps")
                print("  2. View service logs: docker-compose logs <service-name>")
                print("  3. Restart unhealthy services: docker-compose restart <service-name>")
                print("  4. Check network connectivity and firewall settings")
                print()

async def main():
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Health Check")
    parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--continuous", action="store_true", help="Run continuous health checks")
    parser.add_argument("--interval", type=int, default=30, help="Interval for continuous checks (seconds)")
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)
    else:
        # Load from environment variables
        config = {
            "API_GATEWAY_URL": os.getenv("API_GATEWAY_URL", "http://localhost:8000"),
            "VECTOR_SERVICE_URL": os.getenv("VECTOR_SERVICE_URL", "http://localhost:8001"),
            "RAG_SERVICE_URL": os.getenv("RAG_SERVICE_URL", "http://localhost:8002"),
            "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "DATABASE_URL": os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/neurorag")
        }
    
    checker = HealthChecker(config)
    
    if args.continuous:
        print(f"Starting continuous health monitoring (interval: {args.interval}s)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                checker.results = []  # Reset results
                await checker.check_all_services()
                checker.print_results(args.format)
                
                if args.format == "table":
                    print(f"\nNext check in {args.interval} seconds...\n")
                
                await asyncio.sleep(args.interval)
        
        except KeyboardInterrupt:
            print("\nHealth monitoring stopped")
    
    else:
        # Single health check
        await checker.check_all_services()
        checker.print_results(args.format)
        
        # Exit with appropriate code
        overall_status = checker.get_overall_status()
        if overall_status == HealthStatus.UNHEALTHY:
            sys.exit(1)
        elif overall_status == HealthStatus.DEGRADED:
            sys.exit(2)
        else:
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())