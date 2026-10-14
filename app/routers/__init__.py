from app.routers.system import router as system_router
from app.routers.bgm import router as bgm_router
from app.routers.jobs import router as jobs_router
from app.routers.videos import router as videos_router
from app.routers.ui import router as ui_router

__all__ = ["system_router", "bgm_router", "jobs_router", "videos_router", "ui_router"]
