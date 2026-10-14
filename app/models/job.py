import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="My Photo Slideshow")
    status = Column(String(30), nullable=False, default="QUEUED")  # QUEUED, PROCESSING, COMPLETED, FAILED, CANCELED
    progress = Column(Integer, default=0)
    resolution = Column(String(20), nullable=False, default="1080p")  # 720p, 1080p (standard), 1440p, 1920p
    image_count = Column(Integer, nullable=False, default=0)
    grid_rows = Column(Integer, nullable=True)
    grid_cols = Column(Integer, nullable=True)
    bgm_id = Column(String(36), nullable=True)
    bgm_filename = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    video = relationship("Video", back_populates="job", uselist=False, cascade="all, delete-orphan")
