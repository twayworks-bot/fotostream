import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.core.database import init_db, SessionLocal
from app.services.bgm_manager import BGMManager
from app.services.task_queue import task_queue
from app.routers import system_router, bgm_router, jobs_router, videos_router, ui_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("fotostream")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Initializing FOTOSTREAM Database and Storage...")
    init_db()

    # Seed default BGM presets
    db = SessionLocal()
    try:
        BGMManager.seed_default_presets(db)
    except Exception as e:
        logger.warning(f"Could not seed default presets: {e}")
    finally:
        db.close()

    # Start task worker pool (max N=3)
    task_queue.start_workers()
    logger.info("FOTOSTREAM Background Worker Pool is active.")

    yield

    # Shutdown actions
    logger.info("Stopping FOTOSTREAM Worker Pool...")
    await task_queue.stop_workers()
    logger.info("FOTOSTREAM Shutdown complete.")

url_prefix = settings.url_prefix
docs_url = f"{url_prefix}/docs" if url_prefix else "/docs"
redoc_url = f"{url_prefix}/redoc" if url_prefix else "/redoc"
openapi_url = f"{url_prefix}/openapi.json" if url_prefix else "/openapi.json"

app = FastAPI(
    title="FOTOSTREAM API",
    description="Multi-Photo to Video Synthesizer with NxM Zoom-in Matrix Transition and BGM Streaming",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url
)

# Static files mounting
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
static_mount = f"{url_prefix}/static" if url_prefix else "/static"
app.mount(static_mount, StaticFiles(directory=str(static_dir)), name="static")

# Mount Routers under url_prefix
app.include_router(ui_router, prefix=url_prefix)
app.include_router(system_router, prefix=f"{url_prefix}/api/v1")
app.include_router(bgm_router, prefix=f"{url_prefix}/api/v1")
app.include_router(jobs_router, prefix=f"{url_prefix}/api/v1")
app.include_router(videos_router, prefix=f"{url_prefix}/api/v1")

# Dedicated healthcheck endpoint matching Dockerfile HEALTHCHECK:
# requests.get(f'http://localhost:5000{prefix}/api/status')
if url_prefix:
    @app.get(f"{url_prefix}/api/status", tags=["System"])
    def prefix_api_status():
        """Health check endpoint with prefix."""
        return {"status": "healthy", "app": "fotostream", "prefix": url_prefix}

@app.get("/api/status", tags=["System"])
def root_api_status():
    """Health check endpoint without prefix."""
    return {"status": "healthy", "app": "fotostream", "prefix": url_prefix}

@app.get("/", include_in_schema=False)
def root_redirect():
    """Redirect root access to base prefix dashboard."""
    if url_prefix:
        return RedirectResponse(url=url_prefix)
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
