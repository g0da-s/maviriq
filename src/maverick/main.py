import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from maverick.api.auth_routes import router as auth_router
from maverick.api.routes import router
from maverick.api.stripe_routes import router as stripe_router
from maverick.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Maverick backend starting...")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Maverick API",
    description="Idea validation pipeline — 4-agent research system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware (configure via CORS_ORIGINS env var)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router)
app.include_router(stripe_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("maverick.main:app", host="0.0.0.0", port=8000, reload=True)
