import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import router as v1_router
from app.config.settings import settings
from app.dependencies import get_db
from app.lifecycle import Lifecycle
from app.messaging.producer import rabbitmq_producer

APP_VERSION = "1.0.0"
_start_time = time.monotonic()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_lifecycle = Lifecycle()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    if settings.mock_db:
        from app.mock.seed import seed_database
        await seed_database()
    await _lifecycle.start()
    yield
    await _lifecycle.stop()


app = FastAPI(
    title="MdM Control Backend",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api")


@app.get("/health/live")
async def liveness() -> JSONResponse:
    return JSONResponse(content={"status": "ok"})


@app.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    db_latency_ms: float | None = None
    # noinspection PyBroadException
    try:
        start = time.monotonic()
        await db.execute(select(1))
        db_latency_ms = round((time.monotonic() - start) * 1000, 2)
        db_status = "ok"
    except Exception:  # noqa: BLE001 — healthcheck should survive any DB error
        db_status = "error"
    # noinspection PyBroadException
    try:
        rabbitmq_status = "ok" if rabbitmq_producer.healthy else "disconnected"
    except Exception:  # noqa: BLE001
        rabbitmq_status = "error"

    overall = "ok" if db_status == "ok" else "error"
    return JSONResponse(
        content={
            "status": overall,
            "version": APP_VERSION,
            "uptime_seconds": int(time.monotonic() - _start_time),
            "database": {"status": db_status, "latency_ms": db_latency_ms},
            "rabbitmq": rabbitmq_status,
        },
        status_code=200 if overall == "ok" else 503,
    )


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    return await readiness(db)
