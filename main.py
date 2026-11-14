import time
from contextlib import asynccontextmanager
from typing import Any

import psycopg
import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field

from config import settings

# Structured JSON logging setup
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

# Prometheus RED metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total count of HTTP requests",
    ["method", "endpoint", "status"],
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)


def connect(timeout: int = 2):
    return psycopg.connect(settings.database_url, connect_timeout=timeout)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            "id SERIAL PRIMARY KEY, author TEXT, text TEXT)"
        )
    yield


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    endpoint = request.url.path
    method = request.method
    client_ip = request.client.host if request.client else "unknown"

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        duration = time.perf_counter() - start_time
        status_code = 500
        http_requests_total.labels(
            method=method, endpoint=endpoint, status=str(status_code)
        ).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
            duration
        )
        logger.error(
            "http_request_error",
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            client_ip=client_ip,
            error=str(exc),
        )
        raise exc

    duration = time.perf_counter() - start_time
    http_requests_total.labels(
        method=method, endpoint=endpoint, status=str(status_code)
    ).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
        duration
    )

    logger.info(
        "http_request",
        method=method,
        endpoint=endpoint,
        status_code=status_code,
        duration_ms=round(duration * 1000, 2),
        client_ip=client_ip,
    )
    return response


class Message(BaseModel):
    author: str
    text: str


class AlertItem(BaseModel):
    status: str | None = None
    labels: dict[str, Any] = Field(default_factory=dict)
    annotations: dict[str, Any] = Field(default_factory=dict)
    startsAt: str | None = None
    endsAt: str | None = None
    generatorURL: str | None = None
    fingerprint: str | None = None


class AlertmanagerPayload(BaseModel):
    version: str | None = None
    groupKey: str | None = None
    truncatedAlerts: int | None = 0
    status: str | None = None
    receiver: str | None = None
    groupLabels: dict[str, Any] = Field(default_factory=dict)
    commonLabels: dict[str, Any] = Field(default_factory=dict)
    commonAnnotations: dict[str, Any] = Field(default_factory=dict)
    externalURL: str | None = None
    alerts: list[AlertItem] = Field(default_factory=list)


@app.get("/")
def index():
    return {"message": settings.greeting}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    try:
        with connect(timeout=2) as conn:
            conn.execute("SELECT 1")
        return {"status": "ok"}
    except Exception:
        logger.error("readiness_check_failed", error="Database connection failed")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "detail": "Database connection failed"},
        )


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/alerts/webhook")
def alert_webhook(payload: AlertmanagerPayload):
    logger.info(
        "alert_received",
        status=payload.status,
        receiver=payload.receiver,
        alerts_count=len(payload.alerts),
        alerts=[alert.model_dump() for alert in payload.alerts],
    )
    return {"ok": True, "received": len(payload.alerts)}


@app.get("/messages")
def list_messages():
    with connect() as conn:
        rows = conn.execute(
            "SELECT author, text FROM messages ORDER BY id DESC"
        ).fetchall()
    return [{"author": author, "text": text} for author, text in rows]


@app.post("/messages")
def add_message(message: Message):
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages (author, text) VALUES (%s, %s)",
            (message.author, message.text),
        )
    return {"ok": True}
