"""VANTYX Autonomous Batch-to-Publish Pipeline Engine.

Orchestrates the autonomous multi-stage workflow:
URL_SUBMITTED
→ URL_VALIDATED
→ METADATA_RESOLVED
→ RIGHTS_VERIFIED (or RIGHTS_PENDING)
→ MEDIA_RESOLVING (or AWAITING_MEDIA)
→ MEDIA_READY
→ ANALYZING
→ CANDIDATES_READY
→ RENDERING
→ OUTPUT_VALIDATION
→ COMPLETED

Safety & Compliance Guarantees:
1. Strict legal gate: A source without verified commercial rights never enters production.
2. Strict media gate: A source without authorized media on disk never enters video analysis.
3. Fault-isolation: Failures on individual URLs do not block adjacent batch items.
4. Idempotency: Processing a previously completed item returns the completed record without duplication.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.db.models.intake import IntakeBatch, IntakeBatchItem
from app.db.models.intelligence import AnalysisJob
from app.db.models.production import RenderJob
from app.db.models.selection import CandidateClip
from app.db.models.source import VideoSource
from app.modules.discovery.service import DiscoveryService
from app.modules.intelligence.service import IntelligenceService
from app.modules.media_resolution.creator_provider import get_creator_provider
from app.modules.media_resolution.media_resolver import get_media_resolver
from app.modules.media_resolution.metadata_provider import get_metadata_provider
from app.modules.media_resolution.rights_evaluator import RightsEvaluator, SourceEligibilityCategory
from app.modules.production.service import ProductionService
from app.modules.selection.service import SelectionService


class AutonomousPipelineService:
    """Autonomous coordinator driving YouTube URLs through discovery, analysis, selection, and rendering."""

    @classmethod
    async def process_item(
        cls,
        db: AsyncSession,
        item_id: int,
        auto_render_top: bool = True,
    ) -> Dict[str, Any]:
        """Execute the autonomous pipeline on a single batch item."""
        stmt = (
            select(IntakeBatchItem)
            .where(IntakeBatchItem.id == item_id)
            .options(
                selectinload(IntakeBatchItem.source).selectinload(VideoSource.rights),
                selectinload(IntakeBatchItem.source).selectinload(VideoSource.creator),
            )
        )
        item = (await db.execute(stmt)).scalars().first()
        if not item:
            raise ValueError(f"Batch item ID {item_id} not found")

        source = item.source
        if not source:
            item.status = "failed"
            item.error_message = "No associated VideoSource record found"
            await db.commit()
            return {"status": "failed", "item_id": item_id, "stage": "SOURCE_MISSING"}

        # Idempotency check: if already completed and rendered, don't re-render
        if item.status == "completed":
            return {"status": "completed", "item_id": item_id, "stage": "COMPLETED", "cached": True}

        try:
            # ---------------- Stage 1: METADATA_RESOLVED ----------------
            metadata_provider = get_metadata_provider()
            meta = await metadata_provider.resolve_metadata(source.video_id, source.source_url)
            if meta.get("resolved"):
                if meta.get("title") and (not source.title or source.title.startswith("YouTube Source")):
                    source.title = meta["title"]
                if meta.get("thumbnail_url"):
                    source.thumbnail_url = meta["thumbnail_url"]
                if meta.get("raw_data"):
                    source.raw_metadata = meta["raw_data"]
                if meta.get("channel_id"):
                    if not source.raw_metadata:
                        source.raw_metadata = {}
                    source.raw_metadata["channel_id"] = meta["channel_id"]

                # Attempt automatic creator corroboration if not linked
                if not source.creator_id and meta.get("author_name"):
                    creator_prov = get_creator_provider()
                    creator = await creator_prov.resolve_creator(
                        db,
                        author_name=meta.get("author_name"),
                        author_url=meta.get("author_url"),
                        channel_id=meta.get("channel_id"),
                    )
                    if creator:
                        source.creator_id = creator.id
                        source.creator = creator

            item.status = "metadata_ready"
            await db.commit()

            # ---------------- Stage 2: RIGHTS_VERIFICATION ----------------
            auth_eval = RightsEvaluator.evaluate(source)
            if not auth_eval.is_eligible and not source.is_synthetic:
                if auth_eval.permission_status == "rejected" or "expired" in auth_eval.reason.lower():
                    item.status = "rights_rejected"
                else:
                    item.status = "rights_pending"
                item.error_message = f"Commercial rights verification blocked: {auth_eval.blocker_detail or auth_eval.reason}"
                await db.commit()
                return {
                    "status": item.status,
                    "item_id": item_id,
                    "stage": item.status.upper(),
                    "category": auth_eval.category.value,
                    "reason": auth_eval.reason,
                    "blocker_detail": auth_eval.blocker_detail,
                }

            item.status = "rights_verified"
            await db.commit()

            # ---------------- Stage 3: MEDIA_RESOLVING ----------------
            item.status = "media_resolving"
            await db.commit()

            media_resolver = get_media_resolver()
            media_res = await media_resolver.resolve_media(db, source)

            if not media_res.resolved:
                if media_res.status in ("invalid_mapping", "corrupted"):
                    item.status = "failed"
                else:
                    item.status = "awaiting_authorized_media"
                item.error_message = media_res.message
                await db.commit()
                return {
                    "status": item.status,
                    "item_id": item_id,
                    "stage": item.status.upper(),
                    "provider": media_res.provider,
                    "message": media_res.message,
                    "blocker_detail": media_res.blocker_detail,
                }

            # Valid media asset confirmed on disk
            source.local_video_path = media_res.local_path
            if media_res.duration_seconds > 0 and source.duration_seconds == 0:
                source.duration_seconds = int(media_res.duration_seconds)

            item.status = "media_ready"
            item.error_message = None
            await db.commit()

            # ---------------- Stage 4: ANALYZING ----------------
            item.status = "analyzing"
            await db.commit()

            analysis_job = await IntelligenceService.start_video_analysis(
                db, source_id=source.id, force=False
            )

            # ---------------- Stage 5: CANDIDATES_READY ----------------
            candidates = await SelectionService.generate_candidates_for_source(
                db, source_id=source.id, min_score_threshold=50.0, max_candidates=6
            )

            if not candidates:
                item.status = "completed"
                item.error_message = "Analysis finished but no moments met Shorts engagement threshold"
                await db.commit()
                return {
                    "status": "completed",
                    "item_id": item_id,
                    "stage": "CANDIDATES_EMPTY",
                    "candidates_count": 0,
                }

            item.status = "candidates_ready"
            await db.commit()

            # ---------------- Stage 6: RENDERING ----------------
            rendered_job: Optional[RenderJob] = None
            if auto_render_top and candidates:
                top_candidate = max(candidates, key=lambda c: c.overall_score)
                top_candidate.status = "approved"
                await db.commit()

                item.status = "rendering"
                await db.commit()

                rendered_job = await ProductionService.execute_render(
                    db, candidate_id=top_candidate.id
                )

                # ---------------- Stage 7: OUTPUT_VALIDATION ----------------
                if rendered_job.status != "completed" or not rendered_job.output_file_path:
                    item.status = "failed"
                    item.error_message = f"Render failed: {rendered_job.error_message or 'Output file missing'}"
                    await db.commit()
                    return {
                        "status": "failed",
                        "item_id": item_id,
                        "stage": "RENDER_FAILED",
                        "error": item.error_message,
                    }

                out_p = Path(rendered_job.output_file_path)
                if not out_p.exists() or out_p.stat().st_size < 1024:
                    item.status = "failed"
                    item.error_message = "Render output validation failed: file size < 1024 bytes"
                    await db.commit()
                    return {
                        "status": "failed",
                        "item_id": item_id,
                        "stage": "OUTPUT_VALIDATION_FAILED",
                    }

            # ---------------- Stage 8: COMPLETED ----------------
            item.status = "completed"
            item.error_message = None
            await db.commit()

            return {
                "status": "completed",
                "item_id": item_id,
                "stage": "COMPLETED",
                "source_id": source.id,
                "source_title": source.title,
                "candidates_count": len(candidates),
                "rendered_job_id": rendered_job.id if rendered_job else None,
                "output_file": rendered_job.output_file_path if rendered_job else None,
            }

        except Exception as exc:
            logger.error(f"Autonomous pipeline error on item #{item_id}: {exc}", exc_info=True)
            item.status = "failed"
            item.error_message = str(exc)
            await db.commit()
            return {"status": "failed", "item_id": item_id, "stage": "FAILED", "error": str(exc)}

    @classmethod
    async def process_batch(
        cls,
        db: AsyncSession,
        batch_id: str,
        auto_render_top: bool = True,
    ) -> Dict[str, Any]:
        """Execute autonomous pipeline sequentially across all items in a batch with fault-isolation."""
        batch = await DiscoveryService.get_batch(db, batch_id)
        if not batch:
            raise ValueError(f"Batch '{batch_id}' not found")

        batch.status = "processing"
        await db.commit()

        results: List[Dict[str, Any]] = []
        completed_count = 0
        awaiting_media_count = 0
        failed_count = 0

        for item in batch.items:
            # Skip items already rejected during URL syntax validation or duplicate checking
            if item.status in ("rejected", "duplicate") and not item.source_id:
                results.append({"item_id": item.id, "status": item.status, "skipped": True})
                continue

            res = await cls.process_item(db, item.id, auto_render_top=auto_render_top)
            results.append(res)

            if res.get("status") == "completed":
                completed_count += 1
            elif res.get("status") in ("awaiting_media", "rights_pending"):
                awaiting_media_count += 1
            elif res.get("status") == "failed":
                failed_count += 1

        # Re-evaluate batch overall status
        if completed_count == len(batch.items):
            batch.status = "completed"
        elif completed_count > 0 or awaiting_media_count > 0:
            batch.status = "partially_completed"
        elif failed_count > 0:
            batch.status = "failed"
        else:
            batch.status = "completed"

        await db.commit()
        await db.refresh(batch)

        logger.info(
            f"Autonomous batch {batch_id} execution finished: "
            f"{completed_count} completed, {awaiting_media_count} awaiting media, {failed_count} failed."
        )

        return {
            "batch_id": batch_id,
            "status": batch.status,
            "total_items": len(batch.items),
            "completed": completed_count,
            "awaiting_media": awaiting_media_count,
            "failed": failed_count,
            "results": results,
        }

    @classmethod
    async def list_outputs(
        cls,
        db: AsyncSession,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve unified list of completed render outputs with rich context for the Outputs Studio."""
        # Clean up any phantom files first
        await ProductionService.quarantine_orphaned_jobs(db)

        stmt = (
            select(RenderJob)
            .options(
                selectinload(RenderJob.candidate_id),  # handled via candidate
            )
            .order_by(RenderJob.created_at.desc())
            .limit(limit)
        )
        jobs = await ProductionService.list_jobs(db, limit=limit)

        outputs: List[Dict[str, Any]] = []
        for job in jobs:
            candidate = await db.get(CandidateClip, job.candidate_id)
            source = await db.get(VideoSource, job.source_id)

            file_exists = False
            file_size_mb = 0.0
            if job.output_file_path:
                p = Path(job.output_file_path)
                if not p.is_absolute():
                    p = Path(os.getcwd()) / p
                if p.exists() and p.is_file():
                    file_exists = True
                    file_size_mb = round(p.stat().st_size / (1024 * 1024), 2)

            outputs.append(
                {
                    "job_id": job.id,
                    "candidate_id": job.candidate_id,
                    "source_id": job.source_id,
                    "status": job.status,
                    "progress_pct": job.progress_pct,
                    "resolution": job.resolution,
                    "layout_style": job.layout_style,
                    "format_aspect": job.format_aspect,
                    "has_burned_subtitles": job.has_burned_subtitles,
                    "is_synthetic": job.is_synthetic,
                    "created_at": job.created_at,
                    "output_file_path": job.output_file_path,
                    "file_exists": file_exists,
                    "file_size_mb": file_size_mb,
                    "source_title": source.title if source else f"Source #{job.source_id}",
                    "source_url": source.source_url if source else "",
                    "video_id": source.video_id if source else "",
                    "clip_title": candidate.title_suggestion if candidate else f"Short #{job.id}",
                    "duration_seconds": candidate.duration_seconds if candidate else 0.0,
                    "overall_score": candidate.overall_score if candidate else 0.0,
                    "hook_score": candidate.hook_score if candidate else 0.0,
                    "retention_score": candidate.retention_score if candidate else 0.0,
                    "context_score": candidate.context_score if candidate else 0.0,
                    "audio_score": candidate.audio_score if candidate else 0.0,
                    "approval_status": candidate.status if candidate else "unknown",
                    "error_message": job.error_message,
                }
            )

        return outputs
