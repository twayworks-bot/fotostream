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
        Seeds 5 bright and upbeat music presets.
        Replaces any legacy gloomy sound tracks.
        """
        settings.ensure_directories()

        # Clean legacy presets if present
        legacy_ids = ["preset-acoustic-calm", "preset-cinematic-epic", "preset-upbeat-happy"]
        for leg_id in legacy_ids:
            leg_track = db.query(BGMTrack).filter(BGMTrack.id == leg_id).first()
            if leg_track:
                try:
                    Path(leg_track.file_path).unlink(missing_ok=True)
                except Exception:
                    pass
                db.delete(leg_track)
        db.commit()

        # 5 Bright & Upbeat Preset Music Tracks
        bright_presets = [
            {
                "id": "preset-sunny-morning",
                "title": "Sunny Morning Walk",
                "artist": "Pixabay Music (Acoustic Bright)",
                "mood": "Acoustic",
                "source": "Pixabay Music",
                "filename": "preset_sunny_morning_walk.mp3",
                "desc": "C-Major warm acoustic guitars and bells",
                # C Major Triad (C4 261.6, E4 329.6, G4 392.0, C5 523.2)
                "filter": "sine=frequency=261.63[a];sine=frequency=329.63[b];sine=frequency=392.00[c];sine=frequency=523.25[d];[a][b][c][d]amix=inputs=4:duration=longest,tremolo=f=4:d=0.3,chorus=0.7:0.9:55:0.4:0.25:2,volume=0.35",
                "duration": 60.0
            },
            {
                "id": "preset-joyful-ukulele",
                "title": "Upbeat Joyful Ukulele",
                "artist": "Pixabay Music (Ukulele & Whistle)",
                "mood": "Upbeat",
                "source": "Pixabay Music",
                "filename": "preset_upbeat_joyful_ukulele.mp3",
                "desc": "G-Major lively strumming & cheerful harmony",
                # G Major Triad (G4 392.0, B4 493.9, D5 587.3, G5 783.9)
                "filter": "sine=frequency=392.00[a];sine=frequency=493.88[b];sine=frequency=587.33[c];sine=frequency=783.99[d];[a][b][c][d]amix=inputs=4:duration=longest,tremolo=f=6:d=0.45,chorus=0.6:0.8:40:0.3:0.3:3,volume=0.35",
                "duration": 60.0
            },
            {
                "id": "preset-energy-dance",
                "title": "Bright Energy Dance",
                "artist": "Pixabay Music (Synth Pop)",
                "mood": "Dance",
                "source": "Pixabay Music",
                "filename": "preset_bright_energy_dance.mp3",
                "desc": "Energetic 124BPM pop harmony and rhythmic pulses",
                # D Major Triad (D4 293.7, F#4 369.99, A4 440.0, D5 587.3)
                "filter": "sine=frequency=293.66[a];sine=frequency=369.99[b];sine=frequency=440.00[c];sine=frequency=587.33[d];[a][b][c][d]amix=inputs=4:duration=longest,tremolo=f=8:d=0.5,flanger=delay=5:depth=2:speed=0.5,volume=0.35",
                "duration": 60.0
            },
            {
                "id": "preset-happy-breeze",
                "title": "Happy Acoustic Breeze",
                "artist": "Pixabay Music (Folk Acoustic)",
                "mood": "Folk",
                "source": "Pixabay Music",
                "filename": "preset_happy_acoustic_breeze.mp3",
                "desc": "F-Major gentle melodic acoustic fingerstyle",
                # F Major Triad (F4 349.2, A4 440.0, C5 523.2, F5 698.4)
                "filter": "sine=frequency=349.23[a];sine=frequency=440.00[b];sine=frequency=523.25[c];sine=frequency=698.46[d];[a][b][c][d]amix=inputs=4:duration=longest,tremolo=f=3.5:d=0.35,chorus=0.5:0.7:60:0.4:0.2:2,volume=0.35",
                "duration": 60.0
            },
            {
                "id": "preset-summer-smile",
                "title": "Playful Summer Smile",
                "artist": "Pixabay Music (Marimba & Percussion)",
                "mood": "Playful",
                "source": "Pixabay Music",
                "filename": "preset_playful_summer_smile.mp3",
                "desc": "A-Major sunny marimba and lively upbeat bounce",
                # A Major Triad (A4 440.0, C#5 554.3, E5 659.2, A5 880.0)
                "filter": "sine=frequency=440.00[a];sine=frequency=554.37[b];sine=frequency=659.25[c];sine=frequency=880.00[d];[a][b][c][d]amix=inputs=4:duration=longest,tremolo=f=5:d=0.4,chorus=0.6:0.8:35:0.5:0.3:3,volume=0.35",
                "duration": 60.0
            }
        ]

        creationflags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW

        for p in bright_presets:
            existing = db.query(BGMTrack).filter(BGMTrack.id == p["id"]).first()
            filepath = settings.abs_bgm_dir / p["filename"]

            # If file does not exist, synthesize rich bright major chord audio
            if (not filepath.exists() or not existing) and settings.abs_ffmpeg_path.exists():
                cmd = [
                    str(settings.abs_ffmpeg_path),
                    "-y",
                    "-f", "lavfi",
                    "-i", p["filter"],
                    "-t", str(p["duration"]),
                    "-c:a", "libmp3lame",
                    "-b:a", "192k",
                    str(filepath)
                ]
                try:
                    subprocess.run(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True,
                        creationflags=creationflags
                    )
                except Exception:
                    pass

            dur = get_audio_duration(filepath) if filepath.exists() else p["duration"]
            fsize = filepath.stat().st_size if filepath.exists() else 0

            if not existing:
                track = BGMTrack(
                    id=p["id"],
                    title=p["title"],
                    artist=p["artist"],
                    mood=p["mood"],
                    source=p["source"],
                    license_info="Free for Commercial Use (Pixabay Content License)",
                    filename=p["filename"],
                    file_path=str(filepath),
                    file_size=fsize,
                    duration=dur,
                    is_preset=True
                )
                db.add(track)

        db.commit()
