"""FastAPI application entry point for PageIndex RAG backend.

Provides an OpenAI-compatible API that exposes workspaces as selectable
models and implements chat completions backed by the hierarchical RAG
pipeline.  Designed to be called by Open WebUI or any OpenAI-compatible
client.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: initialise the database on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — runs once at startup and shutdown."""
    # Startup
    from backend.db.database import init_db
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown (nothing to clean up)


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Vectorless RAG Backend",
    description="Hierarchical tree-based document RAG with OpenAI-compatible API",
    version="1.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow Open WebUI (or any front-end) to call us
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Bearer-token authentication middleware
# ---------------------------------------------------------------------------

RAG_API_KEY = os.getenv("RAG_API_KEY", "pageindex-secret-key")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Validate Bearer token on every request except health/root and /api/."""
    # Skip auth for health check and root
    if request.url.path in ("/health", "/"):
        return await call_next(request)

    # Validate Bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        if token == RAG_API_KEY:
            return await call_next(request)

    # Also allow /api/ endpoints without auth for internal Docker calls
    if request.url.path.startswith("/api/"):
        return await call_next(request)

    raise HTTPException(status_code=401, detail="Invalid API key")


# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

from backend.api.chat import router as chat_router            # noqa: E402
from backend.api.models_list import router as models_router    # noqa: E402
from backend.api.documents import router as documents_router    # noqa: E402
from backend.api.rich_chat import router as rich_chat_router    # noqa: E402

app.include_router(chat_router)
app.include_router(models_router)
app.include_router(documents_router)
app.include_router(rich_chat_router)


# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Simple health-check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint returning service metadata."""
    return {"name": "Vectorless RAG Backend", "version": "1.1.0"}
