"""Prometheus metrics: request counts, latency and a few business numbers.

Prometheus scrapes GET /metrics. Routes are labelled by their *template*
(e.g. /deadlines/{deadline_id}), never the real path, so IDs and the secret
calendar tokens never end up in metrics, and the number of label values stays small.
"""

import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS = Counter("http_requests_total", "HTTP requests handled", ["method", "route", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Time spent handling a request",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
USERS_REGISTERED = Counter("deadline_users_registered_total", "Accounts created")
DEADLINES_CREATED = Counter("deadline_deadlines_created_total", "Deadlines created")
LOGIN_FAILURES = Counter("deadline_login_failures_total", "Failed login attempts")

SKIP = {"/metrics", "/health", "/health/live"}  # probes would drown out real traffic


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def record(request: Request, call_next):
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            template = getattr(route, "path", "unmatched")
            if template not in SKIP:
                REQUESTS.labels(request.method, template, str(status)).inc()
                LATENCY.labels(request.method, template).observe(time.perf_counter() - start)

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
