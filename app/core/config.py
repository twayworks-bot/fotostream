import os
import shutil
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_PIN: str = "1234"
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    DEFAULT_PREFIX: str = "fotostream"

    # Concurrency and limits
    MAX_CONCURRENT_JOBS: int = 3
    MAX_CONCURRENT_STREAMS: int = 10
    MAX_IMAGES_COUNT: int = 49
    MAX_VIDEO_SIZE_MB: int = 100
    MAX_VIDEO_DURATION_SEC: int = 600

    # Paths
    RETENTION_DAYS: int = 365
    CLEANUP_INTERVAL_HOURS: int = 24
    DOWNLOAD_DIR: str = "./downloads"
    STORAGE_DIR: str = "./storage"
    UPLOAD_DIR: str = "./storage/uploads"
    BGM_DIR: str = "./storage/bgm"
    TRANSCODE_DIR: str = "./storage/transcoded"
    HLS_DIR: str = "./storage/hls"
    DB_PATH: Optional[str] = None
    DB_URL: str = "sqlite:///./storage/fotostream.db"

    # FFmpeg executables
    FFMPEG_PATH: str = "./bin/ffmpeg.exe"
    FFPROBE_PATH: str = "./bin/ffprobe.exe"

    @property
    def clean_prefix(self) -> str:
        """Normalized prefix without leading/trailing slashes. E.g. 'fotostream' or ''."""
        if not self.DEFAULT_PREFIX:
            return ""
        return self.DEFAULT_PREFIX.strip().strip("/")

    @property
    def url_prefix(self) -> str:
        """Normalized URL prefix with single leading slash, no trailing slash. E.g. '/fotostream' or ''."""
        clean = self.clean_prefix
        return f"/{clean}" if clean else ""

    @property
    def effective_db_url(self) -> str:
        """Returns database connection URL, respecting persistent volume DB_PATH if set."""
        if self.DB_PATH:
            p = Path(self.DB_PATH)
            resolved = p if p.is_absolute() else (BASE_DIR / p).resolve()
            resolved.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{resolved.as_posix()}"
        return self.DB_URL

    @property
    def abs_ffmpeg_path(self) -> Path:
        which_path = shutil.which(self.FFMPEG_PATH)
        if which_path:
            return Path(which_path)
        p = Path(self.FFMPEG_PATH)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    @property
    def abs_ffprobe_path(self) -> Path:
        which_path = shutil.which(self.FFPROBE_PATH)
        if which_path:
            return Path(which_path)
        p = Path(self.FFPROBE_PATH)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    @property
    def abs_storage_dir(self) -> Path:
        p = Path(self.STORAGE_DIR)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    @property
    def abs_upload_dir(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    @property
    def abs_bgm_dir(self) -> Path:
        p = Path(self.BGM_DIR)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    @property
    def abs_transcode_dir(self) -> Path:
        p = Path(self.TRANSCODE_DIR)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    @property
    def abs_download_dir(self) -> Path:
        p = Path(self.DOWNLOAD_DIR)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    @property
    def abs_hls_dir(self) -> Path:
        p = Path(self.HLS_DIR)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    def ensure_directories(self) -> None:
        """Ensure all required runtime directories exist."""
        for d in [
            self.abs_storage_dir,
            self.abs_upload_dir,
            self.abs_bgm_dir,
            self.abs_transcode_dir,
            self.abs_download_dir,
            self.abs_hls_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)
        if self.DB_PATH:
            p = Path(self.DB_PATH)
            resolved = p if p.is_absolute() else (BASE_DIR / p).resolve()
            resolved.parent.mkdir(parents=True, exist_ok=True)

settings = Settings()
