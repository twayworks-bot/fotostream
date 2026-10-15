"""
Task Queue & Background Worker Pool for FOTOSTREAM.
Controls concurrent video synthesis with a strict maximum limit of N <= 3.
Manages queue ordering (FIFO), progress tracking, and database synchronization.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.job import Job
from app.models.video import Video
from app.models.bgm import BGMTrack
from app.services.video_synthesizer import synthesize_video

logger = logging.getLogger("fotostream.queue")

class TaskQueueManager:
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._queue: Optional[asyncio.Queue[str]] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self.active_workers: int = 0
        self.is_running = False
        self._worker_tasks: List[asyncio.Task] = []

    @property
    def queue(self) -> asyncio.Queue[str]:
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue

    @property
    def semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    def start_workers(self):
        """Start worker loop tasks in the current running event loop."""
        if self.is_running:
            return
        self._queue = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self.is_running = True
        for i in range(self.max_concurrent):
            task = asyncio.create_task(self._worker_loop(i + 1))
            self._worker_tasks.append(task)
        logger.info(f"TaskQueueManager started with {self.max_concurrent} worker slots.")

    async def stop_workers(self):
        """Gracefully stop worker tasks."""
        self.is_running = False
        for task in self._worker_tasks:
            task.cancel()
        self._worker_tasks.clear()
        self._queue = None
        self._semaphore = None

    async def enqueue_job(self, job_id: str):
        """Add job ID to processing queue."""
        await self.queue.put(job_id)
        logger.info(f"Job {job_id} enqueued. Queue size: {self.queue.qsize()}")

    async def _worker_loop(self, worker_id: int):
        while self.is_running:
            try:
                job_id = await self.queue.get()
                async with self.semaphore:
                    self.active_workers += 1
                    try:
                        await self._process_job(job_id, worker_id)
                    except Exception as e:
                        logger.error(f"[Worker {worker_id}] Unhandled error processing job {job_id}: {e}", exc_info=True)
                    finally:
                        self.active_workers -= 1
                        self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Worker {worker_id}] Loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _process_job(self, job_id: str, worker_id: int):
        logger.info(f"[Worker {worker_id}] Starting synthesis for Job {job_id}")
        db: Session = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job or job.status == "CANCELED":
                return

            job.status = "PROCESSING"
            job.started_at = datetime.utcnow()
            job.progress = 5
            db.commit()

            # Locate upload directory for this job
            job_upload_dir = settings.abs_upload_dir / job_id
            if not job_upload_dir.exists():
                raise FileNotFoundError(f"Upload directory for job {job_id} not found: {job_upload_dir}")

            # Collect image files in sorted order
            valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
            image_files = sorted([
                p for p in job_upload_dir.iterdir()
                if p.is_file() and p.suffix.lower() in valid_exts and not p.name.startswith("bgm_")
            ])

            if not image_files:
                raise ValueError("No valid image files found to synthesize")

            # Determine BGM path
            bgm_path: Optional[Path] = None
            if job.bgm_id:
                bgm_track = db.query(BGMTrack).filter(BGMTrack.id == job.bgm_id).first()
                if bgm_track and Path(bgm_track.file_path).exists():
                    bgm_path = Path(bgm_track.file_path)

            if not bgm_path and job.bgm_filename:
                uploaded_bgm = job_upload_dir / job.bgm_filename
                if uploaded_bgm.exists():
                    bgm_path = uploaded_bgm

            # Target output paths
            output_video_filename = f"{job_id}.mp4"
            output_mp4_path = settings.abs_transcode_dir / output_video_filename
            thumb_filename = f"{job_id}_thumb.jpg"
            thumb_path = settings.abs_transcode_dir / thumb_filename

            def progress_callback(pct: int):
                # Update progress in DB periodically
                nonlocal db, job_id
                try:
                    j = db.query(Job).filter(Job.id == job_id).first()
                    if j:
                        j.progress = pct
                        db.commit()
                except Exception:
                    pass

            from app.services.video_synthesizer import get_resolution_spec
            default_w, default_h, _, _ = get_resolution_spec(job.resolution or "1080p")

            # Run CPU-bound synthesis in thread pool to avoid blocking asyncio event loop
            loop = asyncio.get_running_loop()
            synth_res = await loop.run_in_executor(
                None,
                synthesize_video,
                image_files,
                bgm_path,
                output_mp4_path,
                thumb_path,
                progress_callback,
                job.resolution or "1080p"
            )

            duration = float(synth_res)
            res_w = getattr(synth_res, "width", default_w)
            res_h = getattr(synth_res, "height", default_h)

            file_size = output_mp4_path.stat().st_size if output_mp4_path.exists() else 0
            stream_url = f"{settings.url_prefix}/api/v1/videos/{job_id}/stream"

            # Immediately convert synthesized MP4 to HLS for high real-time responsiveness
            from app.services.hls_manager import generate_hls_stream
            hls_dir = settings.abs_hls_dir / job_id
            hls_url = f"{settings.url_prefix}/api/v1/videos/{job_id}/hls/playlist.m3u8"
            hls_path = None
            try:
                playlist_p, _ = generate_hls_stream(output_mp4_path, hls_dir)
                hls_path = str(playlist_p)
                logger.info(f"[Worker {worker_id}] Converted Job {job_id} to HLS stream immediately.")
            except Exception as hls_err:
                logger.warning(f"[Worker {worker_id}] Immediate HLS generation warning for Job {job_id}: {hls_err}")

            # Create video record
            video = Video(
                id=job_id,
                job_id=job_id,
                title=job.title,
                filename=output_video_filename,
                file_path=str(output_mp4_path),
                file_size=file_size,
                duration=duration,
                resolution=f"{res_w}x{res_h}",
                thumbnail_path=str(thumb_path) if thumb_path.exists() else None,
                stream_url=stream_url,
                hls_url=hls_url,
                hls_path=hls_path
            )
            db.add(video)

            job.status = "COMPLETED"
            job.progress = 100
            job.completed_at = datetime.utcnow()
            db.commit()
            logger.info(f"[Worker {worker_id}] Successfully synthesized Job {job_id} ({duration:.1f}s, {file_size / 1024 / 1024:.2f}MB)")

        except Exception as e:
            logger.error(f"[Worker {worker_id}] Job {job_id} failed: {e}", exc_info=True)
            db.rollback()
            try:
                failed_job = db.query(Job).filter(Job.id == job_id).first()
                if failed_job:
                    failed_job.status = "FAILED"
                    failed_job.error_message = str(e)
                    failed_job.completed_at = datetime.utcnow()
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()

task_queue = TaskQueueManager(max_concurrent=settings.MAX_CONCURRENT_JOBS)
