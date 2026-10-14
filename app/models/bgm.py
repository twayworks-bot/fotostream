import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from app.core.database import Base

class BGMTrack(Base):
    __tablename__ = "bgm_tracks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    artist = Column(String(255), default="Unknown")
    mood = Column(String(100), default="General")
    source = Column(String(255), default="Pixabay Music")
    license_info = Column(String(255), default="Free for Commercial Use")
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    duration = Column(Float, nullable=False, default=0.0)
    is_preset = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
