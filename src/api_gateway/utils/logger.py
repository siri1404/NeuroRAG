"""
Structured Logging Configuration for NeuroRAG
"""

import os
import sys
import logging
import structlog
from typing import Any, Dict
import json
from datetime import datetime

def setup_logging():
    """Configure structured logging for the application"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            # Add log level
            structlog.stdlib.add_log_level,
            
            # Add timestamp
            add_timestamp,
            
            # Add request ID if available
            add_request_id,
            
            # Filter sensitive data
            filter_sensitive_data,
            
            # Format for console or JSON
            structlog.dev.ConsoleRenderer() if os.getenv("LOG_FORMAT") != "json" 
            else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

def add_timestamp(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add timestamp to log entries"""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict

def add_request_id(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add request ID to log entries if available"""
    # This would typically get the request ID from context
    # For now, we'll skip if not available
    return event_dict

def filter_sensitive_data(logger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Filter sensitive data from log entries"""
    sensitive_fields = {
        "password", "api_key", "authorization", "x-api-key", 
        "token", "secret", "private_key", "ssn", "credit_card"
    }
    
    def _filter_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        filtered = {}
        for key, value in data.items():
            if isinstance(key, str) and key.lower() in sensitive_fields:
                filtered[key] = "[REDACTED]"
            elif isinstance(value, dict):
                filtered[key] = _filter_dict(value)
            elif isinstance(value, str) and len(value) > 50:
                # Truncate very long strings that might contain sensitive data
                filtered[key] = value[:50] + "..."
            else:
                filtered[key] = value
        return filtered
    
    # Filter the event dict
    for key, value in list(event_dict.items()):
        if isinstance(value, dict):
            event_dict[key] = _filter_dict(value)
        elif isinstance(key, str) and key.lower() in sensitive_fields:
            event_dict[key] = "[REDACTED]"
    
    return event_dict

class StructuredLogger:
    """Wrapper for structured logging with additional context"""
    
    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)
        self.context = {}
    
    def bind(self, **kwargs) -> 'StructuredLogger':
        """Bind additional context to logger"""
        new_logger = StructuredLogger(self.logger.name)
        new_logger.logger = self.logger.bind(**kwargs)
        new_logger.context = {**self.context, **kwargs}
        return new_logger
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, **kwargs)

class AuditLogger:
    """Specialized logger for audit events"""
    
    def __init__(self):
        self.logger = structlog.get_logger("audit")
    
    def log_query(
        self,
        user_id: str,
        query: str,
        results_count: int,
        latency_ms: float,
        compliance_flags: list = None
    ):
        """Log query audit event"""
        self.logger.info(
            "Query executed",
            event_type="query",
            user_id=user_id,
            query_length=len(query),
            query_hash=hash(query),
            results_count=results_count,
            latency_ms=latency_ms,
            compliance_flags=compliance_flags or [],
            sensitive_data_detected=bool(compliance_flags)
        )
    
    def log_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        success: bool,
        reason: str = None
    ):
        """Log access audit event"""
        self.logger.info(
            "Resource access",
            event_type="access",
            user_id=user_id,
            resource=resource,
            action=action,
            success=success,
            reason=reason
        )
    
    def log_data_export(
        self,
        user_id: str,
        data_type: str,
        record_count: int,
        export_format: str
    ):
        """Log data export audit event"""
        self.logger.info(
            "Data exported",
            event_type="export",
            user_id=user_id,
            data_type=data_type,
            record_count=record_count,
            export_format=export_format
        )
    
    def log_compliance_violation(
        self,
        user_id: str,
        violation_type: str,
        severity: str,
        details: dict
    ):
        """Log compliance violation"""
        self.logger.warning(
            "Compliance violation detected",
            event_type="compliance_violation",
            user_id=user_id,
            violation_type=violation_type,
            severity=severity,
            details=details
        )

class PerformanceLogger:
    """Logger for performance metrics and monitoring"""
    
    def __init__(self):
        self.logger = structlog.get_logger("performance")
    
    def log_latency(
        self,
        operation: str,
        latency_ms: float,
        success: bool,
        metadata: dict = None
    ):
        """Log operation latency"""
        self.logger.info(
            "Operation completed",
            event_type="latency",
            operation=operation,
            latency_ms=latency_ms,
            success=success,
            metadata=metadata or {}
        )
    
    def log_throughput(
        self,
        operation: str,
        requests_per_second: float,
        time_window_seconds: int
    ):
        """Log throughput metrics"""
        self.logger.info(
            "Throughput measured",
            event_type="throughput",
            operation=operation,
            requests_per_second=requests_per_second,
            time_window_seconds=time_window_seconds
        )
    
    def log_resource_usage(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_usage_percent: float = None
    ):
        """Log system resource usage"""
        self.logger.info(
            "Resource usage",
            event_type="resource_usage",
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_usage_percent=disk_usage_percent
        )

# Global logger instances
audit_logger = AuditLogger()
performance_logger = PerformanceLogger()

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)