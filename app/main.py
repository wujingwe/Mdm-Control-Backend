import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import router as v1_router
from app.infra.config.settings import settings
from app.dependencies import get_db
from app.lifecycle import Lifecycle
from app.infra.messaging.producer import rabbitmq_producer
from app.mock.seed import seed_database

APP_VERSION = "1.0.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_lifecycle = Lifecycle()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    if settings.mock_db:
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
    try:
        await db.execute(select(1))
        db_status = "ok"
    except Exception:
        db_status = "error"
    try:
        rabbitmq_status = "ok" if rabbitmq_producer.healthy else "disconnected"
    except Exception:
        rabbitmq_status = "error"

    overall = "ok" if db_status == "ok" else "error"
    return JSONResponse(
        content={"status": overall, "database": db_status, "rabbitmq": rabbitmq_status},
        status_code=200 if overall == "ok" else 503,
    )


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    return await readiness(db)
