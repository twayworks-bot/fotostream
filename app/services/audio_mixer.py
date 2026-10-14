"""
Audio Mixer Service for FOTOSTREAM.
Handles BGM duration extraction via FFprobe, audio looping, volume adjustment,
and smooth fade-out filter configuration for FFmpeg encoding.
"""

import subprocess
import json
from pathlib import Path
from typing import Optional, Tuple
from app.core.config import settings

def get_audio_duration(audio_path: Path) -> float:
    """Extract audio duration in seconds using ffprobe."""
    if not audio_path.exists():
        return 0.0

    cmd = [
        str(settings.abs_ffprobe_path),
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(audio_path)
    ]
    try:
        creationflags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            creationflags=creationflags
        )
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0.0))
    except Exception:
        return 0.0

def build_audio_ffmpeg_args(
    audio_path: Optional[Path],
    video_duration: float,
    fade_duration: float = 2.0
) -> Tuple[list, list]:
    """
    Returns (input_args, filter_args) for FFmpeg command.
    If audio_path is valid:
      - loops audio indefinitely
      - cuts at video_duration
      - applies fade-out at (video_duration - fade_duration)
    If audio_path is None or missing:
      - generates silent audio matching video_duration
    """
    if audio_path and audio_path.exists():
        input_args = [
            "-stream_loop", "-1",
            "-i", str(audio_path)
        ]
        start_fade = max(0.0, video_duration - fade_duration)
        filter_args = [
            "-af", f"afade=t=out:st={start_fade:.2f}:d={fade_duration:.2f}",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest"
        ]
        return input_args, filter_args
    else:
        # Generate silent audio track
        input_args = [
            "-f", "lavfi",
            "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100"
        ]
        filter_args = [
            "-c:a", "aac",
            "-b:a", "128k",
            "-t", f"{video_duration:.2f}"
        ]
        return input_args, filter_args
