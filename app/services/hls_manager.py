"""
HLS (HTTP Live Streaming) Manager for FOTOSTREAM.
Converts synthesized MP4 videos into HLS format (.m3u8 playlist and .ts segments)
using fast stream copying for ultra-low latency, and manages HLS serving and lifecycle.
"""

import os
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Tuple, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger("fotostream.hls")


def generate_hls_stream(
    input_mp4_path: Path,
    output_hls_dir: Path,
    segment_duration: float = 2.0
) -> Tuple[Path, List[Path]]:
    """
    Converts an MP4 video file to HLS (.m3u8 playlist and .ts segment files).
    Uses fast stream copying (-c copy) so remuxing takes less than 0.3s.
    
    Args:
        input_mp4_path: Path to existing source MP4 file.
        output_hls_dir: Directory where playlist.m3u8 and segment_*.ts files will be saved.
        segment_duration: Target duration of each .ts segment in seconds (default: 2.0s).

    Returns:
        Tuple of (playlist_path, list_of_segment_paths)
    """
    if not input_mp4_path.exists():
        raise FileNotFoundError(f"Source MP4 file not found: {input_mp4_path}")

    output_hls_dir.mkdir(parents=True, exist_ok=True)
    playlist_path = output_hls_dir / "playlist.m3u8"
    segment_pattern = output_hls_dir / "segment_%03d.ts"

    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW

    # Fast remuxing via stream copy
    cmd = [
        str(settings.abs_ffmpeg_path),
        "-y",
        "-i", str(input_mp4_path),
        "-c", "copy",
        "-bsf:v", "h264_mp4toannexb",
        "-hls_time", str(segment_duration),
        "-hls_list_size", "0",
        "-hls_segment_type", "mpegts",
        "-hls_flags", "independent_segments",
        "-hls_segment_filename", str(segment_pattern),
        str(playlist_path)
    ]

    logger.info(f"Running HLS conversion: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags
    )

    if result.returncode != 0:
        logger.warning(
            f"Fast stream copy HLS failed (code {result.returncode}), trying transcode fallback: {result.stderr.decode(errors='ignore')[:300]}"
        )
        # Fallback with transcode if stream copy fails
        fallback_cmd = [
            str(settings.abs_ffmpeg_path),
            "-y",
            "-i", str(input_mp4_path),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-hls_time", str(segment_duration),
            "-hls_list_size", "0",
            "-hls_segment_type", "mpegts",
            "-hls_flags", "independent_segments",
            "-hls_segment_filename", str(segment_pattern),
            str(playlist_path)
        ]
        fb_res = subprocess.run(
            fallback_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags
        )
        if fb_res.returncode != 0:
            raise RuntimeError(
                f"FFmpeg HLS conversion failed: {fb_res.stderr.decode(errors='ignore')}"
            )

    if not playlist_path.exists():
        raise RuntimeError(f"HLS playlist was not generated at: {playlist_path}")

    segments = sorted(output_hls_dir.glob("*.ts"))
    logger.info(
        f"HLS generation completed: {playlist_path.name} with {len(segments)} segments in {output_hls_dir}"
    )
    return playlist_path, segments


def ensure_video_hls(video, db: Optional[Session] = None) -> Optional[Path]:
    """
    Ensures HLS playlist and segments exist for a Video instance.
    If not already generated, converts the existing MP4 on-the-fly and persists paths.
    """
    expected_hls_dir = settings.abs_hls_dir / video.id
    playlist_path = expected_hls_dir / "playlist.m3u8"

    if playlist_path.exists() and playlist_path.stat().st_size > 0:
        # Existing playlist verified
        if not video.hls_path or not video.hls_url:
            video.hls_path = str(playlist_path)
            video.hls_url = f"{settings.url_prefix}/api/v1/videos/{video.id}/hls/playlist.m3u8"
            if db:
                db.commit()
        return playlist_path

    mp4_path = Path(video.file_path)
    if not mp4_path.exists():
        logger.error(f"Cannot generate HLS: source MP4 missing for video {video.id} at {mp4_path}")
        return None

    try:
        playlist_path, segments = generate_hls_stream(mp4_path, expected_hls_dir)
        video.hls_path = str(playlist_path)
        video.hls_url = f"{settings.url_prefix}/api/v1/videos/{video.id}/hls/playlist.m3u8"
        if db:
            db.commit()
        return playlist_path
    except Exception as e:
        logger.error(f"On-demand HLS generation failed for video {video.id}: {e}", exc_info=True)
        return None


def delete_video_hls(video_id: str) -> bool:
    """Removes all HLS artifacts for a given video ID."""
    hls_dir = settings.abs_hls_dir / video_id
    if hls_dir.exists():
        try:
            shutil.rmtree(hls_dir, ignore_errors=True)
            logger.info(f"Deleted HLS directory: {hls_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete HLS directory {hls_dir}: {e}")
            return False
    return False
