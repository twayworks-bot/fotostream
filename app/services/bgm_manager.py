"""
BGM Manager Service for FOTOSTREAM.
Manages BGM tracks, seeding 5 bright & upbeat preset tracks, and audio streaming operations.
"""

import os
import uuid
import subprocess
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.bgm import BGMTrack
from app.services.audio_mixer import get_audio_duration

class BGMManager:
    @staticmethod
    def list_tracks(db: Session, mood: Optional[str] = None) -> List[BGMTrack]:
        query = db.query(BGMTrack)
        if mood and mood.lower() != "all":
            query = query.filter(BGMTrack.mood.ilike(f"%{mood}%"))
        return query.order_by(BGMTrack.is_preset.desc(), BGMTrack.created_at.desc()).all()

    @staticmethod
    def get_track(db: Session, track_id: str) -> Optional[BGMTrack]:
        return db.query(BGMTrack).filter(BGMTrack.id == track_id).first()

    @staticmethod
    def register_track(
        db: Session,
        title: str,
        artist: str,
        mood: str,
        source: str,
        license_info: str,
        file_bytes: bytes,
        original_filename: str
    ) -> BGMTrack:
        settings.ensure_directories()
        track_id = str(uuid.uuid4())
        ext = Path(original_filename).suffix.lower()
        if not ext or ext not in [".mp3", ".wav", ".aac", ".ogg", ".m4a"]:
            ext = ".mp3"

        saved_filename = f"{track_id}{ext}"
        saved_path = settings.abs_bgm_dir / saved_filename

        with open(saved_path, "wb") as f:
            f.write(file_bytes)

        duration = get_audio_duration(saved_path)
        file_size = len(file_bytes)

        track = BGMTrack(
            id=track_id,
            title=title or Path(original_filename).stem,
            artist=artist or "Unknown Artist",
            mood=mood or "General",
            source=source or "Pixabay Music",
            license_info=license_info or "Free for Commercial Use",
            filename=saved_filename,
            file_path=str(saved_path),
            file_size=file_size,
            duration=duration,
            is_preset=False
        )
        db.add(track)
        db.commit()
        db.refresh(track)
        return track

    @staticmethod
    def delete_track(db: Session, track_id: str) -> bool:
        track = db.query(BGMTrack).filter(BGMTrack.id == track_id).first()
        if not track:
            return False

        file_p = Path(track.file_path)
        if file_p.exists():
            try:
                file_p.unlink()
            except OSError:
                pass

        db.delete(track)
        db.commit()
        return True

    @staticmethod
    def seed_default_presets(db: Session) -> None:
        """
        Automatic seeding is disabled.
        Background music tracks are registered manually by the administrator.
        """
        pass

    @staticmethod
    def clean_default_presets(db: Session) -> int:
        """
        Removes any default preset tracks from the database and storage directory.
        """
        preset_ids = [
            "preset-sunny-morning", "preset-joyful-ukulele", "preset-energy-dance",
            "preset-happy-breeze", "preset-summer-smile", "preset-acoustic-calm",
            "preset-cinematic-epic", "preset-upbeat-happy"
        ]
        removed_count = 0
        preset_tracks = db.query(BGMTrack).filter(
            (BGMTrack.is_preset == True) | (BGMTrack.id.in_(preset_ids))
        ).all()
        for track in preset_tracks:
            try:
                Path(track.file_path).unlink(missing_ok=True)
            except Exception:
                pass
            db.delete(track)
            removed_count += 1
        db.commit()

        # Clean preset audio files from storage/bgm
        for p in settings.abs_bgm_dir.glob("preset_*.mp3"):
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        flag = settings.abs_bgm_dir / ".presets_seeded"
        try:
            flag.unlink(missing_ok=True)
        except Exception:
            pass

        return removed_count
