"""Monitoring and metrics utilities for future enhancement."""
import time
from functools import wraps
from typing import Callable, Any

from logger import setup_logger

logger = setup_logger(__name__)


class PerformanceMonitor:
    """Simple performance monitoring for API calls."""

    @staticmethod
    def time_function(func: Callable) -> Callable:
        """Decorator to time function execution."""

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"{func.__name__} completed in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"{func.__name__} failed after {elapsed:.2f}s: {e}")
                raise

        return wrapper

    @staticmethod
    def log_request(endpoint: str, **metadata):
        """Log an API request with metadata."""
        logger.info(f"Request to {endpoint}", extra=metadata)


class MetricsCollector:
    """Collect metrics for monitoring (placeholder for future enhancement)."""

    def __init__(self):
        self.requests_total = 0
        self.requests_success = 0
        self.requests_failed = 0
        self.total_processing_time = 0.0

    def record_request(self, success: bool, processing_time: float):
        """Record a request metric."""
        self.requests_total += 1
        if success:
            self.requests_success += 1
        else:
            self.requests_failed += 1
        self.total_processing_time += processing_time

    def get_stats(self) -> dict:
        """Get current metrics."""
        avg_time = (
            self.total_processing_time / self.requests_total
            if self.requests_total > 0
            else 0
        )

        return {
            "total_requests": self.requests_total,
            "successful_requests": self.requests_success,
            "failed_requests": self.requests_failed,
            "average_processing_time": avg_time,
            "success_rate": (
                self.requests_success / self.requests_total * 100
                if self.requests_total > 0
                else 0
            )
        }


# Global metrics collector
metrics = MetricsCollector()
