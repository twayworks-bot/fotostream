from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class BGMBase(BaseModel):
    title: str
    artist: Optional[str] = "Unknown"
    mood: Optional[str] = "General"
    source: Optional[str] = "Pixabay Music"
    license_info: Optional[str] = "Free for Commercial Use"

class BGMCreate(BGMBase):
    pass

class BGMResponse(BGMBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_size: int
    duration: float
    is_preset: bool
    created_at: datetime
    stream_url: Optional[str] = None

class BGMListResponse(BaseModel):
    tracks: List[BGMResponse]
    total: int
