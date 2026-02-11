import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from maviriq.api.auth_routes import router as auth_router
from maviriq.api.routes import router
from maviriq.api.stripe_routes import router as stripe_router
from maviriq.config import settings
from maviriq.storage import DatabaseError

_MAX_BODY_SIZE = 1_048_576  # 1 MB


class LimitRequestBodyMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds _MAX_BODY_SIZE."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"},
            )
        return await call_next(request)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Maviriq backend starting...")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Maviriq API",
    description="Idea validation pipeline — 4-agent research system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware (configure via CORS_ORIGINS env var)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Reject oversized request bodies (runs before route handlers)
app.add_middleware(LimitRequestBodyMiddleware)

app.include_router(router)
app.include_router(auth_router)
app.include_router(stripe_router)


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    logger.error("Database error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=503,
        content={"detail": "Service temporarily unavailable"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("maviriq.main:app", host="0.0.0.0", port=8000, reload=True)
