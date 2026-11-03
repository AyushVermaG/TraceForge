"""TraceForge FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database.neo4j_client import neo4j_client
from app.database.schema import init_schema
from app.routers import health, repositories, upload, graph, evidence

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TraceForge.Main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info("TraceForge backend starting up...")
    # Initialize Neo4j schema constraints if reachable
    try:
        init_schema()
    except Exception as e:
        logger.warning(f"Neo4j schema init skipped on startup: {str(e)}")
    
    yield

    logger.info("TraceForge backend shutting down...")
    neo4j_client.close()

app = FastAPI(
    title="TraceForge API",
    description="Evidence-first codebase intelligence platform backed by Neo4j graph database",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(repositories.router, prefix="/api/v1")
app.include_router(upload.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(evidence.router, prefix="/api/v1")

# Mount frontend production build if available
from pathlib import Path
from fastapi.staticfiles import StaticFiles

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "service": "TraceForge Backend",
            "version": "1.0.0",
            "status": "ONLINE",
            "docs_url": "/docs"
        }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "message": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    from pathlib import Path

    backend_dir = Path(__file__).resolve().parent
    watch_dir = str(backend_dir / "app")

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        reload_dirs=[watch_dir] if settings.RELOAD else None,
        reload_excludes=[
            "*/data/*",
            "data/*",
            "*/repos/*",
            "repos/*",
            "*.zip",
            "*.pyc",
            "__pycache__/*",
            "*/__pycache__/*",
        ] if settings.RELOAD else None,
    )
