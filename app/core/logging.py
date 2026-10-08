"""
Structured JSON logging configuration for NomadOS with trace correlation support.
"""
import logging
import sys
import contextvars
from typing import Optional

# Context variable to hold the correlation ID per request trace
correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("correlation_id", default=None)


class StructuredFormatter(logging.Formatter):
    """Formats log records as structured strings with correlation IDs and timestamps."""
    def format(self, record: logging.LogRecord) -> str:
        trace_id = correlation_id_ctx.get() or "N/A"
        timestamp = self.formatTime(record, self.datefmt)
        log_data = {
            "timestamp": timestamp,
            "level": record.levelname,
            "trace_id": trace_id,
            "logger": record.name,
            "message": record.getMessage()
        }
        if hasattr(record, "agent"):
            log_data["agent"] = record.agent
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms
        if hasattr(record, "model_id"):
            log_data["model_id"] = record.model_id
        if hasattr(record, "cost_usd"):
            log_data["cost_usd"] = record.cost_usd
            
        import json
        return json.dumps(log_data)


def setup_logger(name: str = "nomados", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter(datefmt="%Y-%m-%dT%H:%M:%SZ"))
        logger.addHandler(handler)
        
    logger.propagate = False
    return logger


logger = setup_logger()
