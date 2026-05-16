"""
FastAPI application entry point.
Logging is configured at module level, before any other imports, so that
submodule loggers (created at import time via logging.getLogger) inherit
the handlers set up here.
"""
import logging
import logging.handlers
import os
import socket
import subprocess
import sys
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

_LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter(_LOG_FORMAT))

# Rotating file handler — 5 MB per file, keep 5 backups
_file = logging.handlers.RotatingFileHandler(
    filename=os.path.join(_LOG_DIR, "app.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
_file.setFormatter(logging.Formatter(_LOG_FORMAT))

logging.basicConfig(level=logging.INFO, handlers=[_console, _file])
logger = logging.getLogger(__name__)
logger.info("Logging to %s", os.path.join(_LOG_DIR, "app.log"))

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

_SERVER_START = time.perf_counter()

from backend.database import engine, run_migrations
from backend import models
from backend.limiter import limiter
from backend.routers import auth, families, fridge, meal_plans, shopping, audit, recipes, export

# Create tables on cold start; run_migrations() adds columns to existing DBs
# without dropping data (SQLite has no ALTER TABLE MODIFY COLUMN).
models.Base.metadata.create_all(bind=engine)
run_migrations()

MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
_MCP_SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp", "recipe_mcp_server.py")
_mcp_process: subprocess.Popen | None = None


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mcp_process
    if not _port_in_use(MCP_PORT):
        logger.info("Starting Recipe MCP Server on port %d...", MCP_PORT)
        _mcp_process = subprocess.Popen(
            [sys.executable, _MCP_SERVER_SCRIPT],
            env={**os.environ},
        )
        # Wait up to 5s for the server to be ready
        for _ in range(10):
            if _port_in_use(MCP_PORT):
                logger.info("Recipe MCP Server ready on port %d.", MCP_PORT)
                break
            time.sleep(0.5)
        else:
            logger.warning("MCP server did not start in time — will use SQL fallback.")
    else:
        logger.info("Recipe MCP Server already running on port %d.", MCP_PORT)

    yield

    if _mcp_process:
        logger.info("Shutting down Recipe MCP Server...")
        _mcp_process.terminate()
        _mcp_process = None


app = FastAPI(
    title="🍽️ Multi-Agent Meal Planner API",
    description="AI-powered meal planning with multi-agent architecture and RAG",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "REQUEST %s %s → %d | %.1fms",
            request.method, request.url.path, response.status_code, duration_ms,
        )
        return response


app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(families.router)
app.include_router(fridge.router)
app.include_router(meal_plans.router)
app.include_router(shopping.router)
app.include_router(audit.router)
app.include_router(recipes.router)
app.include_router(export.router)


@app.get("/")
def root():
    return {
        "message": "🍽️ Multi-Agent Meal Planner API",
        "docs": "/docs",
        "agents": [
            "PreferenceAgent — aggregates dietary constraints",
            "RecipeAgent (MCP client) — queries Recipe MCP Server via HTTP/SSE",
            "PlannerAgent — generates daily meal plan with calorie validation",
            "ConversationalAgent (GPT-4o) — natural language meal adjustments",
        ],
    }


@app.get("/health")
def health():
    from backend.rag import vector_store
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        recipe_total  = db.query(models.Recipe).count()
        recipe_local  = db.query(models.Recipe).filter(models.Recipe.source == "local").count()
        recipe_spoon  = db.query(models.Recipe).filter(models.Recipe.source == "spoonacular").count()
        family_count  = db.query(models.Family).count()
        user_count    = db.query(models.User).count()
        latest_plan   = db.query(models.MealPlan).order_by(models.MealPlan.id.desc()).first()
    finally:
        db.close()

    return {
        "status": "ok",
        "uptime_seconds": round(time.perf_counter() - _SERVER_START),
        "vector_store_ready": vector_store.is_ready(),
        "mcp_server_running": _port_in_use(MCP_PORT),
        "database": {
            "users": user_count,
            "families": family_count,
            "recipes_total": recipe_total,
            "recipes_local_epub": recipe_local,
            "recipes_spoonacular": recipe_spoon,
            "latest_plan_date": latest_plan.date if latest_plan else None,
        },
    }
