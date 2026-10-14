"""
Root entrypoint for FOTOSTREAM FastAPI application.
Re-exports `app` from `app.main` to support:
- `uvicorn main:app --host 0.0.0.0 --port 5000`
- `gunicorn --bind 0.0.0.0:5000 main:app`
"""

import sys
from pathlib import Path

# Ensure root directory is on Python search path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app
from app.core.config import settings

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
