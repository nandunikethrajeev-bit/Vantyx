"""VANTYX Video Production & Rendering Engine.

Generates 9:16 vertical YouTube Shorts from selected candidate clips using FFmpeg.
Applies blurred background side-fill or center crop, EBU R128 audio normalization,
and thumbnail extraction.
"""

import os
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.models.intelligence import VideoScene
from app.db.models.production import RenderJob
from app.db.models.selection import CandidateClip
from app.db.models.source import VideoSource
from app.schemas.production import RenderSettingsInput


class ProductionServiceInterface(ABC):
    """Abstract interface defining the video production domain boundary."""

    @abstractmethod
    async def render_short(self, segment_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger render task for a vertical short video."""
        pass


class ProductionService(ProductionServiceInterface):
    """Production service implementing vertical video synthesis and audio processing."""

    def __init__(self) -> None:
        self.is_active = False

    async def render_short(self, segment_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy interface helper."""
        return {
            "segment_id": segment_id,
            "status": "idle",
            "output_path": None,
        }

    # ---------------- Vertical Synthesis Filtergraphs ----------------

    @staticmethod
    def build_video_filtergraph(
        layout_style: str = "blurred_backdrop",
        src_width: Optional[int] = None,
        src_height: Optional[int] = None,
    ) -> str:
        """Construct universal aspect-ratio agnostic video filtergraph for 9:16 vertical framing.
        
        Seamlessly handles 16:9 widescreen, 21:9 ultra-wide, 4:3 legacy, and native 9:16 vertical
        without distortion or letterboxing defects.
        """
        # If input is already native vertical (9:16 within 5% tolerance), direct scale to 1080x1920
        if src_width and src_height and abs((src_width / src_height) - (9 / 16)) < 0.05:
            return "[0:v]scale=1080:1920,setsar=1[v]"

        if layout_style == "crop_center":
            # Crop 9:16 strip from center and scale to 1080x1920
            return "[0:v]crop=in_h*(9/16):in_h,scale=1080:1920,setsar=1[v]"

        # Default: blurred backdrop fill with crisp aspect-preserved center foreground
        return (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[bg];"
            "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
        )

    # ---------------- Core Render Execution ----------------

    @classmethod
    async def execute_render(
        cls,
        db: AsyncSession,
        candidate_id: int,
        render_settings: Optional[RenderSettingsInput] = None,
    ) -> RenderJob:
        """Execute FFmpeg render workflow for a candidate clip."""
        config = render_settings or RenderSettingsInput()

        # 1. Fetch Candidate and Source
        candidate = await db.get(CandidateClip, candidate_id)
        if not candidate:
            raise ValueError(f"Candidate clip ID {candidate_id} not found")

        source = await db.get(VideoSource, candidate.source_id)
        if not source:
            raise ValueError(f"Source video ID {candidate.source_id} not found")

        # 2. Prepare Storage Directories
        export_dir = Path(settings.EXPORT_DIR).resolve()
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = int(time.time())
        output_filename = f"vantyx_short_{candidate_id}_{timestamp_str}.mp4"
        thumb_filename = f"vantyx_thumb_{candidate_id}_{timestamp_str}.jpg"
        output_path = export_dir / output_filename
        thumb_path = export_dir / thumb_filename

        # 3. Create RenderJob Record
        job = RenderJob(
            candidate_id=candidate_id,
            source_id=source.id,
            status="rendering",
            progress_pct=15.0,
            resolution=config.resolution,
            format_aspect="9:16",
            layout_style=config.layout_style,
            has_burned_subtitles=config.has_burned_subtitles,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        ffmpeg_exe = settings.get_ffmpeg_executable()
        duration = max(1.0, round(candidate.end_time - candidate.start_time, 2))

        try:
            # 4. Determine Input Stream Source
            local_file = source.local_video_path
            has_local_file = local_file and os.path.exists(local_file)
            job.is_synthetic = bool(source.is_synthetic) or (not has_local_file)

            filtergraph = cls.build_video_filtergraph(
                layout_style=config.layout_style,
                src_width=getattr(source, "width", None),
                src_height=getattr(source, "height", None),
            )
            audio_filter = "loudnorm=I=-14:LRA=11:TP=-1.5" if config.normalize_audio else "anull"

            if has_local_file:
                # Real source video trimming
                cmd = [
                    ffmpeg_exe, "-y",
                    "-ss", str(candidate.start_time),
                    "-to", str(candidate.end_time),
                    "-i", str(local_file),
                    "-filter_complex", f"{filtergraph};[0:a]{audio_filter}[a]",
                    "-map", "[v]",
                    "-map", "[a]",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    str(output_path),
                ]
            else:
                # Synthetic realistic test generator for standalone/un-downloaded gameplay
                # Generates 1080x1920 vertical pattern with test tone and normalization
                cmd = [
                    ffmpeg_exe, "-y",
                    "-f", "lavfi",
                    "-i", f"testsrc=size=1920x1080:rate=30:duration={duration}",
                    "-f", "lavfi",
                    "-i", f"sine=frequency=800:duration={duration}",
                    "-filter_complex", f"{filtergraph};[1:a]{audio_filter}[a]",
                    "-map", "[v]",
                    "-map", "[a]",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    str(output_path),
                ]

            logger.info(f"Starting video render job {job.id} for candidate {candidate_id}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                err_detail = result.stderr[-500:] if result.stderr else "FFmpeg failed with unknown error"
                raise RuntimeError(f"FFmpeg render error: {err_detail}")

            # 5. Extract Thumbnail Frame
            thumb_cmd = [
                ffmpeg_exe, "-y",
                "-ss", "0.5",
                "-i", str(output_path),
                "-vframes", "1",
                "-q:v", "2",
                str(thumb_path),
            ]
            subprocess.run(thumb_cmd, capture_output=True, text=True, timeout=15)

            # 6. Validate output file existence and integrity
            if not output_path.exists() or output_path.stat().st_size < 1024:
                raise RuntimeError(
                    f"FFmpeg render produced an invalid or empty file at {output_path} "
                    f"(size: {output_path.stat().st_size if output_path.exists() else 0} bytes)"
                )

            # 7. Mark Job Completed & Candidate Produced
            job.status = "completed"
            job.progress_pct = 100.0
            job.output_file_path = str(output_path)
            if thumb_path.exists() and thumb_path.stat().st_size > 0:
                job.thumbnail_path = str(thumb_path)

            candidate.status = "produced"
            await db.commit()
            await db.refresh(job)

            logger.info(f"Render job {job.id} finished successfully: {output_path.name}")
            return job

        except Exception as exc:
            logger.error(f"Render job {job.id} failed: {exc}")
            job.status = "failed"
            job.error_message = str(exc)
            await db.commit()
            await db.refresh(job)
            return job

    # ---------------- Query Helpers & Integrity ----------------

    @classmethod
    async def quarantine_orphaned_jobs(cls, db: AsyncSession) -> int:
        """Scan completed jobs and mark any with missing or empty media files as failed.
        
        Prevents ghost records where previous tests or manual file deletions leave
        completed jobs in the DB with non-existent files.
        """
        stmt = select(RenderJob).where(RenderJob.status == "completed")
        result = await db.execute(stmt)
        completed_jobs = list(result.scalars().all())
        quarantined_count = 0

        for job in completed_jobs:
            is_corrupt = False
            if not job.output_file_path:
                is_corrupt = True
            else:
                p = Path(job.output_file_path)
                if not p.is_absolute():
                    p = Path(os.getcwd()) / p
                if not p.exists() or p.stat().st_size < 1024:
                    is_corrupt = True

            if is_corrupt:
                job.status = "failed"
                job.error_message = "Rendered media file is missing on disk or corrupted (quarantined)"
                db.add(job)
                quarantined_count += 1

        if quarantined_count > 0:
            await db.commit()
            logger.info(f"Quarantined {quarantined_count} orphaned/missing render jobs.")
        return quarantined_count

    @classmethod
    async def list_jobs(
        cls,
        db: AsyncSession,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[RenderJob]:
        """List render jobs ordered by creation date descending with integrity verification."""
        await cls.quarantine_orphaned_jobs(db)
        stmt = select(RenderJob).order_by(RenderJob.created_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(RenderJob.status == status)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_job(db: AsyncSession, job_id: int) -> Optional[RenderJob]:
        """Retrieve render job by ID."""
        return await db.get(RenderJob, job_id)

    @classmethod
    async def cleanup_expired_storage(
        cls,
        max_age_days: int = 30,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Purge rendered video and thumbnail exports older than max_age_days.
        
        Preserves active render jobs and raw downloaded source assets.
        """
        export_dir = Path(settings.EXPORT_DIR).resolve()
        if not export_dir.exists():
            return {"deleted_files": 0, "freed_bytes": 0, "freed_mb": 0.0}

        cutoff_time = time.time() - (max_age_days * 86400)
        deleted_count = 0
        freed_bytes = 0

        for file_path in export_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in (".mp4", ".jpg", ".png"):
                try:
                    stat = file_path.stat()
                    if stat.st_mtime < cutoff_time:
                        file_size = stat.st_size
                        if not dry_run:
                            file_path.unlink()
                        deleted_count += 1
                        freed_bytes += file_size
                except Exception as exc:
                    logger.warning(f"Error inspecting or removing storage file {file_path}: {exc}")

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        logger.info(
            f"Storage cleanup completed: {deleted_count} files ({freed_mb} MB) "
            f"{'identified (dry run)' if dry_run else 'deleted'}."
        )
        return {
            "deleted_files": deleted_count,
            "freed_bytes": freed_bytes,
            "freed_mb": freed_mb,
            "cutoff_days": max_age_days,
            "dry_run": dry_run,
        }
