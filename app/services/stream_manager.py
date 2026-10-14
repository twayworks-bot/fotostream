"""
Streaming Session Manager for FOTOSTREAM.
Controls concurrent streaming sessions with a maximum limit of M = 10.
Implements HTTP Range Requests (206 Partial Content) for efficient video seeking.
"""

import os
import re
import asyncio
import logging
from pathlib import Path
from typing import AsyncGenerator, Tuple, Optional
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from app.core.config import settings

logger = logging.getLogger("fotostream.streaming")

class ActiveStreamRegistry:
    def __init__(self, max_streams: int = 10):
        self.max_streams = max_streams
        self.current_streams = 0
        self._lock = asyncio.Lock()

    async def acquire_slot(self) -> bool:
        async with self._lock:
            if self.current_streams >= self.max_streams:
                return False
            self.current_streams += 1
            logger.info(f"Stream slot acquired. Active streams: {self.current_streams}/{self.max_streams}")
            return True

    async def release_slot(self):
        async with self._lock:
            if self.current_streams > 0:
                self.current_streams -= 1
            logger.info(f"Stream slot released. Active streams: {self.current_streams}/{self.max_streams}")

stream_registry = ActiveStreamRegistry(max_streams=settings.MAX_CONCURRENT_STREAMS)

RANGE_REGEX = re.compile(r"bytes=(\d+)-(\d*)")

def parse_range_header(range_header: Optional[str], file_size: int) -> Tuple[int, int]:
    """Parse HTTP Range header and return (start, end) byte offsets."""
    if not range_header:
        return 0, file_size - 1

    match = RANGE_REGEX.match(range_header.strip())
    if not match:
        return 0, file_size - 1

    start_str, end_str = match.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else file_size - 1

    if start >= file_size:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail=f"Requested range not satisfiable: start {start} >= size {file_size}"
        )

    end = min(end, file_size - 1)
    return start, end

async def create_video_range_response(
    file_path: Path,
    range_header: Optional[str],
    media_type: str = "video/mp4",
    chunk_size: int = 256 * 1024  # 256 KB
) -> StreamingResponse:
    """
    Builds a StreamingResponse supporting HTTP 206 Partial Content
    guarded by the 10-stream concurrency limit.
    """
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video file not found")

    file_size = file_path.stat().st_size
    start, end = parse_range_header(range_header, file_size)
    content_length = (end - start) + 1

    # Check concurrent stream slot
    slot_acquired = await stream_registry.acquire_slot()
    if not slot_acquired:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum concurrent streaming limit ({settings.MAX_CONCURRENT_STREAMS}) reached. Please try again shortly."
        )

    async def range_file_iterator() -> AsyncGenerator[bytes, None]:
        try:
            with open(file_path, "rb") as f:
                f.seek(start)
                bytes_left = content_length
                while bytes_left > 0:
                    read_bytes = min(chunk_size, bytes_left)
                    data = f.read(read_bytes)
                    if not data:
                        break
                    bytes_left -= len(data)
                    yield data
                    # Yield control to event loop
                    await asyncio.sleep(0.001)
        finally:
            await stream_registry.release_slot()

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": media_type
    }

    status_code = status.HTTP_206_PARTIAL_CONTENT if range_header else status.HTTP_200_OK
    return StreamingResponse(range_file_iterator(), status_code=status_code, headers=headers)
