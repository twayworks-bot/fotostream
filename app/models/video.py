import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Video(Base):
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False, default=0)
    duration = Column(Float, nullable=False, default=0.0)
    resolution = Column(String(20), nullable=False, default="1280x720")
    thumbnail_path = Column(String(500), nullable=True)
    stream_url = Column(String(500), nullable=False)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="video")
