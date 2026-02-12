"""
Lightweight Prometheus-compatible metrics collector.
Implements D9.1 Section 8.3.4 monitoring requirements.

Tracks: request counts, response times, error rates, storage utilization.
"""

import time
from collections import defaultdict
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class MetricsCollector:
    """
    In-process metrics collector.
    
    Collects request counts, response times, error rates,
    and exposes them in Prometheus text format.
    """
    
    def __init__(self) -> None:
        self._request_count: dict[str, int] = defaultdict(int)
        self._error_count: dict[str, int] = defaultdict(int)
        self._response_time_sum: dict[str, float] = defaultdict(float)
        self._response_time_count: dict[str, int] = defaultdict(int)
        self._status_counts: dict[int, int] = defaultdict(int)
        self._start_time: float = time.time()
    
    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
    ) -> None:
        """Record a completed request."""
        key = f"{method} {path}"
        self._request_count[key] += 1
        self._response_time_sum[key] += duration
        self._response_time_count[key] += 1
        self._status_counts[status_code] += 1
        
        if status_code >= 400:
            self._error_count[key] += 1
    
    def get_metrics(self) -> dict[str, Any]:
        """Get metrics as a structured dictionary."""
        total_requests = sum(self._request_count.values())
        total_errors = sum(self._error_count.values())
        uptime = time.time() - self._start_time
        
        return {
            "uptime_seconds": round(uptime, 2),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": round(total_errors / total_requests, 4) if total_requests > 0 else 0,
            "requests_by_endpoint": dict(self._request_count),
            "errors_by_endpoint": dict(self._error_count),
            "status_code_counts": {str(k): v for k, v in sorted(self._status_counts.items())},
            "avg_response_time_ms": {
                k: round((self._response_time_sum[k] / self._response_time_count[k]) * 1000, 2)
                for k in self._response_time_count
            },
        }
    
    def to_prometheus(self) -> str:
        """
        Export metrics in Prometheus text exposition format.
        See: https://prometheus.io/docs/instrumenting/exposition_formats/
        """
        lines: list[str] = []
        uptime = time.time() - self._start_time
        
        # Uptime
        lines.append("# HELP metro_uptime_seconds Time since service start in seconds")
        lines.append("# TYPE metro_uptime_seconds gauge")
        lines.append(f"metro_uptime_seconds {uptime:.2f}")
        lines.append("")
        
        # Total requests
        lines.append("# HELP metro_http_requests_total Total HTTP requests")
        lines.append("# TYPE metro_http_requests_total counter")
        for key, count in sorted(self._request_count.items()):
            method, path = key.split(" ", 1)
            lines.append(
                f'metro_http_requests_total{{method="{method}",path="{path}"}} {count}'
            )
        lines.append("")
        
        # Error counts
        lines.append("# HELP metro_http_errors_total Total HTTP errors (4xx/5xx)")
        lines.append("# TYPE metro_http_errors_total counter")
        for key, count in sorted(self._error_count.items()):
            method, path = key.split(" ", 1)
            lines.append(
                f'metro_http_errors_total{{method="{method}",path="{path}"}} {count}'
            )
        lines.append("")
        
        # Status code counts
        lines.append("# HELP metro_http_status_total HTTP responses by status code")
        lines.append("# TYPE metro_http_status_total counter")
        for code, count in sorted(self._status_counts.items()):
            lines.append(f'metro_http_status_total{{code="{code}"}} {count}')
        lines.append("")
        
        # Average response times
        lines.append("# HELP metro_http_response_time_seconds Average response time in seconds")
        lines.append("# TYPE metro_http_response_time_seconds gauge")
        for key in sorted(self._response_time_count.keys()):
            method, path = key.split(" ", 1)
            avg = self._response_time_sum[key] / self._response_time_count[key]
            lines.append(
                f'metro_http_response_time_seconds{{method="{method}",path="{path}"}} {avg:.6f}'
            )
        lines.append("")
        
        return "\n".join(lines) + "\n"


# Global singleton
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that records request metrics.
    
    Measures request duration and records status codes
    for all API requests.
    """
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip metrics endpoint itself to avoid recursion
        if request.url.path.endswith("/metrics"):
            return await call_next(request)
        
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        
        # Normalize path: replace UUIDs with {id} for aggregation
        path = request.url.path
        parts = path.split("/")
        normalized = []
        for part in parts:
            # Simple UUID detection (36 chars with hyphens)
            if len(part) == 36 and part.count("-") == 4:
                normalized.append("{id}")
            else:
                normalized.append(part)
        normalized_path = "/".join(normalized)
        
        collector = get_metrics_collector()
        collector.record_request(
            method=request.method,
            path=normalized_path,
            status_code=response.status_code,
            duration=duration,
        )
        
        return response
