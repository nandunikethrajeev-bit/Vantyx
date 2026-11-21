"""VANTYX Autonomous Orchestration & End-to-End Workflow Engine.

Ties together Discovery, Rights Intelligence, AI Understanding, Moment Selection,
Video Production, Distribution, and Channel Monitoring into a resilient, persistent
autonomous pipeline targeting 4 daily Shorts in Asia/Kolkata timezone.
"""

import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import logger
from app.db.models.creator import Creator
from app.db.models.distribution import PublishSchedule
from app.db.models.orchestration import (
    BackgroundJob,
    DailyPublishingPlan,
    JobAttempt,
    JobExecutionLog,
    WorkflowRun,
    WorkflowStep,
)
from app.db.models.intelligence import VideoScene
from app.db.models.production import RenderJob
from app.db.models.rights import RightsRecord
from app.db.models.selection import CandidateClip
from app.db.models.source import VideoSource
from app.modules.discovery.service import DiscoveryService
from app.modules.distribution.service import DistributionService, PublishingEligibilityError, TimezoneHelper
from app.modules.intelligence.service import IntelligenceService
from app.modules.production.service import ProductionService
from app.modules.selection.service import SelectionService
from app.schemas.distribution import PublishScheduleCreate
from app.schemas.production import RenderSettingsInput


PIPELINE_STEPS = [
    ("discovery", 1),
    ("rights_validation", 2),
    ("intelligence", 3),
    ("selection", 4),
    ("production", 5),
    ("distribution", 6),
    ("monitoring", 7),
]


class OrchestrationService:
    """Core autonomous workflow controller and job recovery engine."""

    # ---------------- Persistent Plan & Workflow Initialization ----------------

    @classmethod
    async def get_or_create_daily_plan(
        cls, db: AsyncSession, plan_date: str
    ) -> DailyPublishingPlan:
        """Retrieve or initialize the persistent daily publishing plan for Asia/Kolkata."""
        stmt = select(DailyPublishingPlan).where(DailyPublishingPlan.plan_date == plan_date)
        res = await db.execute(stmt)
        plan = res.scalar_one_or_none()

        if not plan:
            # Initialize empty 4-slot grid
            default_slots = {
                slot: {
                    "slot_name": slot,
                    "status": "unfilled",
                    "candidate_id": None,
                    "render_job_id": None,
                    "schedule_id": None,
                    "youtube_video_id": None,
                }
                for slot in settings.DEFAULT_PUBLISH_SLOTS
            }
            plan = DailyPublishingPlan(
                plan_date=plan_date,
                timezone=settings.TIMEZONE,
                status="planning",
                target_count=settings.TARGET_SHORTS_PER_DAY,
                filled_count=0,
                slot_assignments=default_slots,
            )
            db.add(plan)
            await db.commit()
            await db.refresh(plan)

        return plan

    @classmethod
    async def create_workflow_run(
        cls, db: AsyncSession, target_date: Optional[str] = None, force: bool = False
    ) -> WorkflowRun:
        """Create a persistent WorkflowRun instance with 7 initialized steps."""
        if not target_date:
            target_date = datetime.now(TimezoneHelper.KOLKATA_TZ).strftime("%Y-%m-%d")

        # Duplicate run prevention: check if an active run already exists for this date
        if not force:
            existing_stmt = select(WorkflowRun).where(
                WorkflowRun.target_date == target_date,
                WorkflowRun.status.in_(["pending", "queued", "running"]),
            )
            existing_res = await db.execute(existing_stmt)
            active_run = existing_res.scalar_one_or_none()
            if active_run:
                logger.warning(
                    f"Active workflow run #{active_run.id} ({active_run.run_id}) already exists for {target_date}"
                )
                return active_run

        run_id = f"wf_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        workflow_run = WorkflowRun(
            run_id=run_id,
            workflow_type="daily_autonomous_publishing",
            target_date=target_date,
            status="pending",
            current_step="discovery",
            started_at=datetime.now(timezone.utc),
            retry_count=0,
            execution_metadata={
                "target_date": target_date,
                "sources_discovered": 0,
                "eligible_sources": 0,
                "scenes_indexed": 0,
                "candidates_selected": 0,
                "shorts_rendered": 0,
                "slots_scheduled": 0,
            },
        )
        db.add(workflow_run)
        await db.flush()

        # Initialize the 7 pipeline steps
        for step_name, order in PIPELINE_STEPS:
            step = WorkflowStep(
                workflow_run_id=workflow_run.id,
                step_name=step_name,
                step_order=order,
                status="pending",
                output_data={},
            )
            db.add(step)

        await cls.log_event(
            db,
            workflow_run_id=workflow_run.id,
            level="INFO",
            message=f"Initialized workflow run {run_id} for target date {target_date}",
        )

        await db.commit()
        await db.refresh(workflow_run)

        # Ensure daily publishing plan exists
        await cls.get_or_create_daily_plan(db, target_date)

        return workflow_run

    # ---------------- Logging & Telemetry ----------------

    @classmethod
    async def log_event(
        cls,
        db: AsyncSession,
        workflow_run_id: Optional[int],
        level: str,
        message: str,
        context_data: Optional[Dict[str, Any]] = None,
        job_id: Optional[int] = None,
    ) -> JobExecutionLog:
        """Write persistent log entry for operational transparency."""
        entry = JobExecutionLog(
            workflow_run_id=workflow_run_id,
            job_id=job_id,
            level=level,
            message=message,
            context_data=context_data or {},
            timestamp=datetime.now(timezone.utc),
        )
        db.add(entry)
        if level in ["WARNING", "ERROR"]:
            logger.warning(f"Workflow [{workflow_run_id}]: {message}")
        else:
            logger.info(f"Workflow [{workflow_run_id}]: {message}")
        return entry

    # ---------------- Step-By-Step Workflow Execution ----------------

    @classmethod
    async def execute_step_1_discovery(
        cls, db: AsyncSession, run: WorkflowRun, step: WorkflowStep
    ) -> Dict[str, Any]:
        """Step 1: Discover newly available videos from monitored GTA creators."""
        step.status = "running"
        step.started_at = datetime.now(timezone.utc)
        await db.commit()

        # 1. Run autonomous discovery sweep across approved monitored channels
        res = await DiscoveryService.run_discovery_cycle(db)
        discovered_count = res.get("videos_discovered", 0)

        # 2. Count existing eligible sources in catalog
        sources_stmt = select(VideoSource).order_by(VideoSource.id.desc()).limit(20)
        all_sources = list((await db.execute(sources_stmt)).scalars().all())

        output = {
            "channels_polled": res.get("channels_polled", 0),
            "videos_discovered": discovered_count,
            "catalog_sources_checked": len(all_sources),
            "duplicates_skipped": res.get("duplicates_skipped", 0),
        }

        step.output_data = output
        step.status = "completed"
        step.completed_at = datetime.now(timezone.utc)

        metadata = dict(run.execution_metadata or {})
        metadata["sources_discovered"] = discovered_count
        run.execution_metadata = metadata

        await cls.log_event(
            db,
            run.id,
            "INFO",
            f"Discovery complete: {discovered_count} new videos found across {res.get('channels_polled', 0)} creators",
            output,
        )
        await db.commit()
        return output

    @classmethod
    async def execute_step_2_rights_validation(
        cls, db: AsyncSession, run: WorkflowRun, step: WorkflowStep
    ) -> Dict[str, Any]:
        """Step 2: Verify commercial use permissions and legal eligibility."""
        step.status = "running"
        step.started_at = datetime.now(timezone.utc)
        await db.commit()

        # Check all un-evaluated sources
        stmt = (
            select(VideoSource)
            .options(selectinload(VideoSource.rights), selectinload(VideoSource.creator))
            .order_by(VideoSource.id.desc())
            .limit(30)
        )
        sources = list((await db.execute(stmt)).scalars().all())

        eligible_ids = []
        rejected_ids = []

        for src in sources:
            is_eligible, reason, _ = await DiscoveryService.check_source_eligibility(db, src.id)
            if is_eligible:
                eligible_ids.append(src.id)
            else:
                rejected_ids.append({"source_id": src.id, "title": src.title, "reason": reason})

        output = {
            "sources_evaluated": len(sources),
            "eligible_count": len(eligible_ids),
            "rejected_count": len(rejected_ids),
            "eligible_source_ids": eligible_ids,
        }

        step.output_data = output
        step.status = "completed"
        step.completed_at = datetime.now(timezone.utc)

        metadata = dict(run.execution_metadata or {})
        metadata["eligible_sources"] = len(eligible_ids)
        run.execution_metadata = metadata

        await cls.log_event(
            db,
            run.id,
            "INFO",
            f"Rights validation complete: {len(eligible_ids)} sources verified for commercial use, {len(rejected_ids)} rejected",
            output,
        )
        await db.commit()
        return output

    @classmethod
    async def execute_step_3_intelligence(
        cls, db: AsyncSession, run: WorkflowRun, step: WorkflowStep
    ) -> Dict[str, Any]:
        """Step 3: Multimodal scene analysis and engaging moment discovery."""
        step.status = "running"
        step.started_at = datetime.now(timezone.utc)
        await db.commit()

        # Find eligible sources by inspecting rights
        stmt = (
            select(VideoSource)
            .options(selectinload(VideoSource.rights))
            .order_by(VideoSource.id.desc())
            .limit(10)
        )
        sources = list((await db.execute(stmt)).scalars().all())
        eligible_sources = [s for s in sources if DiscoveryService.evaluate_eligibility(s)[0]][:5]

        analyzed_count = 0
        for src in eligible_sources:
            # Check if scenes already indexed (cached analysis)
            existing_scenes = await IntelligenceService.list_source_scenes(db, src.id)
            if existing_scenes and len(existing_scenes) > 0:
                continue

            try:
                job = await IntelligenceService.start_video_analysis(db, src.id, force=True)
                analyzed_count += 1
                await cls.log_event(
                    db,
                    run.id,
                    "INFO",
                    f"Analyzed source #{src.id} '{src.title}'",
                )
            except Exception as e:
                await cls.log_event(
                    db, run.id, "WARNING", f"Scene analysis failed for source #{src.id}: {str(e)}"
                )

        # Count total scenes across eligible sources
        scene_count_stmt = select(VideoScene).where(
            VideoScene.source_id.in_([s.id for s in eligible_sources])
        )
        total_scenes = len(list((await db.execute(scene_count_stmt)).scalars().all()))

        output = {
            "sources_analyzed": analyzed_count,
            "total_scenes_available": total_scenes,
        }

        step.output_data = output
        step.status = "completed"
        step.completed_at = datetime.now(timezone.utc)

        metadata = dict(run.execution_metadata or {})
        metadata["scenes_indexed"] = total_scenes
        run.execution_metadata = metadata

        await db.commit()
        return output

    @classmethod
    async def execute_step_4_selection(
        cls, db: AsyncSession, run: WorkflowRun, step: WorkflowStep
    ) -> Dict[str, Any]:
        """Step 4: Rank candidate clips and select top non-overlapping moments."""
        step.status = "running"
        step.started_at = datetime.now(timezone.utc)
        await db.commit()

        # Prefer selecting multiple distinct moments from eligible source videos
        stmt = (
            select(VideoSource)
            .options(selectinload(VideoSource.rights))
            .order_by(VideoSource.id.desc())
            .limit(10)
        )
        sources = list((await db.execute(stmt)).scalars().all())
        eligible_sources = [s for s in sources if DiscoveryService.evaluate_eligibility(s)[0]][:5]

        selected_candidates: List[CandidateClip] = []

        for src in eligible_sources:
            # Generate candidates with scoring
            candidates = await SelectionService.generate_candidates_for_source(
                db, src.id, min_score_threshold=30.0, max_candidates=4
            )
            for c in candidates:
                if c.status == "candidate":
                    # Approve top candidate moments
                    c.status = "approved"
                    selected_candidates.append(c)

            if len(selected_candidates) >= settings.TARGET_SHORTS_PER_DAY:
                break

        await db.commit()

        # Check total approved candidates ready for production
        approved_stmt = select(CandidateClip).where(CandidateClip.status == "approved")
        all_approved = list((await db.execute(approved_stmt)).scalars().all())

        candidates_count = len(all_approved) if all_approved else len(selected_candidates)

        output = {
            "new_candidates_selected": len(selected_candidates),
            "total_approved_candidates": candidates_count,
            "target_daily_quota": settings.TARGET_SHORTS_PER_DAY,
            "has_sufficient_moments": candidates_count >= settings.TARGET_SHORTS_PER_DAY,
        }

        step.output_data = output
        step.status = "completed"
        step.completed_at = datetime.now(timezone.utc)

        metadata = dict(run.execution_metadata or {})
        metadata["candidates_selected"] = candidates_count
        run.execution_metadata = metadata

        await cls.log_event(
            db,
            run.id,
            "INFO",
            f"Moment selection complete: {len(all_approved)} approved moments ready for production (Target: {settings.TARGET_SHORTS_PER_DAY}/day)",
            output,
        )
        await db.commit()
        return output

    @classmethod
    async def execute_step_5_production(
        cls, db: AsyncSession, run: WorkflowRun, step: WorkflowStep
    ) -> Dict[str, Any]:
        """Step 5: Synthesize 9:16 vertical video with blurred backdrop and audio normalization."""
        step.status = "running"
        step.started_at = datetime.now(timezone.utc)
        await db.commit()

        # Check free disk space before processing renders
        try:
            total, used, free = shutil.disk_usage(settings.DATA_DIR)
            free_gb = free / (1024**3)
            if free_gb < 1.0:
                raise RuntimeError(
                    f"Insufficient disk space ({free_gb:.2f} GB available). Minimum 1.0 GB required."
                )
        except Exception as e:
            if "Insufficient" in str(e):
                raise

        # Find approved candidates needing rendering (respecting concurrency limit)
        stmt = (
            select(CandidateClip)
            .where(CandidateClip.status == "approved")
            .order_by(CandidateClip.overall_score.desc())
            .limit(settings.MAX_CONCURRENT_RENDERS)
        )
        approved_candidates = list((await db.execute(stmt)).scalars().all())

        rendered_jobs: List[RenderJob] = []

        for candidate in approved_candidates:
            # Check if already has a completed render
            existing_job_stmt = select(RenderJob).where(
                RenderJob.candidate_id == candidate.id, RenderJob.status == "completed"
            )
            existing_job = (await db.execute(existing_job_stmt)).scalars().first()

            if existing_job:
                rendered_jobs.append(existing_job)
                continue

            # Respect concurrency and execute render
            try:
                job = await ProductionService.execute_render(
                    db,
                    candidate.id,
                    render_settings=RenderSettingsInput(
                        layout_style="blurred_backdrop",
                        normalize_audio=True,
                        resolution="1080x1920",
                    ),
                )
                rendered_jobs.append(job)
                await cls.log_event(
                    db,
                    run.id,
                    "INFO",
                    f"Rendered Short for Candidate #{candidate.id}: Job #{job.id} (Output: {job.output_file_path}, is_synthetic={job.is_synthetic})",
                )
            except Exception as e:
                await cls.log_event(
                    db,
                    run.id,
                    "ERROR",
                    f"Failed to render Short for Candidate #{candidate.id}: {str(e)}",
                )

        output = {
            "rendered_count": len(rendered_jobs),
            "completed_job_ids": [j.id for j in rendered_jobs],
        }

        step.output_data = output
        step.status = "completed"
        step.completed_at = datetime.now(timezone.utc)

        metadata = dict(run.execution_metadata or {})
        metadata["shorts_rendered"] = len(rendered_jobs)
        run.execution_metadata = metadata

        await db.commit()
        return output

    @classmethod
    async def execute_step_6_distribution(
        cls, db: AsyncSession, run: WorkflowRun, step: WorkflowStep
    ) -> Dict[str, Any]:
        """Step 6: Allocate daily publishing slots (Asia/Kolkata) and schedule Shorts."""
        step.status = "running"
        step.started_at = datetime.now(timezone.utc)
        await db.commit()

        plan = await cls.get_or_create_daily_plan(db, run.target_date)
        slots_dict = dict(plan.slot_assignments or {})

        # Find completed render jobs
        render_stmt = (
            select(RenderJob)
            .where(RenderJob.status == "completed")
            .order_by(RenderJob.id.desc())
            .limit(10)
        )
        completed_renders = list((await db.execute(render_stmt)).scalars().all())

        scheduled_count = 0
        scheduled_schedules = []

        for job in completed_renders:
            # 1. Check if candidate or job is already scheduled
            sched_check = select(PublishSchedule).where(
                PublishSchedule.candidate_id == job.candidate_id,
                PublishSchedule.status.in_(["scheduled", "published"]),
            )
            if (await db.execute(sched_check)).scalars().first():
                continue

            # 2. Find first unfilled slot in the daily plan
            target_slot = None
            for slot_name in settings.DEFAULT_PUBLISH_SLOTS:
                slot_data = slots_dict.get(slot_name, {})
                if slot_data.get("status") in ["unfilled", None]:
                    target_slot = slot_name
                    break

            if not target_slot:
                # All 4 slots filled for today
                break

            # 3. Check Publishing Eligibility (Strict Gate - blocks synthetic media)
            try:
                await DistributionService.verify_publishing_eligibility(
                    db, job.candidate_id, job.id
                )
            except PublishingEligibilityError as pe:
                await cls.log_event(
                    db,
                    run.id,
                    "WARNING",
                    f"Candidate #{job.candidate_id} rejected at publishing gate: {str(pe)}",
                )
                continue

            # 4. Schedule short for slot
            candidate = await db.get(CandidateClip, job.candidate_id)
            title = (
                f"GTA 6: {candidate.title_suggestion} #Shorts"
                if candidate and candidate.title_suggestion
                else "GTA 6 Epic Moment #Shorts"
            )

            try:
                schedule = await DistributionService.create_schedule(
                    db,
                    PublishScheduleCreate(
                        candidate_id=job.candidate_id,
                        render_job_id=job.id,
                        target_date=run.target_date,
                        slot_name=target_slot,
                        title=title[:100],
                    ),
                )
                scheduled_count += 1
                scheduled_schedules.append(schedule.id)

                # Update slot in daily plan
                slots_dict[target_slot] = {
                    "slot_name": target_slot,
                    "status": "scheduled",
                    "candidate_id": job.candidate_id,
                    "render_job_id": job.id,
                    "schedule_id": schedule.id,
                    "youtube_video_id": schedule.youtube_video_id,
                }

                await cls.log_event(
                    db,
                    run.id,
                    "INFO",
                    f"Scheduled Short #{schedule.id} for slot {target_slot} IST on {run.target_date}",
                )

                # Execute mock publish if mock publishing enabled
                if settings.MOCK_YOUTUBE_PUBLISHING:
                    pub_res = await DistributionService.execute_publishing_upload(
                        db, schedule.id, force_mock=True
                    )
                    slots_dict[target_slot]["status"] = "published"
                    slots_dict[target_slot]["youtube_video_id"] = pub_res.get("youtube_video_id")
                    await cls.log_event(
                        db,
                        run.id,
                        "INFO",
                        f"Mock published slot {target_slot}: {pub_res.get('youtube_video_id')}",
                    )

            except Exception as se:
                await cls.log_event(
                    db,
                    run.id,
                    "ERROR",
                    f"Failed to schedule slot {target_slot}: {str(se)}",
                )

        # Update Daily Plan
        plan.slot_assignments = slots_dict
        filled_slots = sum(
            1 for s in slots_dict.values() if s.get("status") in ["scheduled", "published"]
        )
        plan.filled_count = filled_slots
        if filled_slots >= plan.target_count:
            plan.status = "fulfilled"
        elif filled_slots > 0:
            plan.status = "partial"
        else:
            plan.status = "unfulfilled"

        output = {
            "slots_scheduled": scheduled_count,
            "total_slots_filled": filled_slots,
            "target_count": plan.target_count,
            "plan_status": plan.status,
            "scheduled_schedule_ids": scheduled_schedules,
        }

        step.output_data = output
        step.status = "completed"
        step.completed_at = datetime.now(timezone.utc)

        metadata = dict(run.execution_metadata or {})
        metadata["slots_scheduled"] = filled_slots
        run.execution_metadata = metadata

        await db.commit()
        return output

    @classmethod
    async def execute_step_7_monitoring(
        cls, db: AsyncSession, run: WorkflowRun, step: WorkflowStep
    ) -> Dict[str, Any]:
        """Step 7: Verify quota fulfillment, report unfilled slots, and log telemetry."""
        step.status = "running"
        step.started_at = datetime.now(timezone.utc)
        await db.commit()

        plan = await cls.get_or_create_daily_plan(db, run.target_date)
        slots_dict = dict(plan.slot_assignments or {})

        unfilled = [
            slot
            for slot, data in slots_dict.items()
            if data.get("status") not in ["scheduled", "published"]
        ]

        if unfilled:
            await cls.log_event(
                db,
                run.id,
                "WARNING",
                f"Daily publishing plan has unfilled slots for {run.target_date}: {', '.join(unfilled)} (Fulfilled: {plan.filled_count}/4)",
            )
        else:
            await cls.log_event(
                db,
                run.id,
                "INFO",
                f"Daily publishing plan 100% fulfilled for {run.target_date} (4/4 slots assigned)",
            )

        output = {
            "plan_date": run.target_date,
            "plan_status": plan.status,
            "filled_slots": plan.filled_count,
            "target_slots": plan.target_count,
            "unfilled_slots": unfilled,
        }

        step.output_data = output
        step.status = "completed"
        step.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return output

    # ---------------- Full Pipeline Execution Engine ----------------

    @classmethod
    async def run_full_pipeline(
        cls, db: AsyncSession, run_id: str
    ) -> WorkflowRun:
        """Execute all 7 stages of the autonomous workflow sequentially with failure isolation."""
        stmt = (
            select(WorkflowRun)
            .options(selectinload(WorkflowRun.steps))
            .where(WorkflowRun.run_id == run_id)
        )
        res = await db.execute(stmt)
        run = res.scalar_one_or_none()
        if not run:
            raise ValueError(f"Workflow run '{run_id}' not found")

        run.status = "running"
        await db.commit()

        step_map = {s.step_name: s for s in run.steps}

        try:
            # Step 1: Discovery
            run.current_step = "discovery"
            await db.commit()
            if "discovery" in step_map and step_map["discovery"].status != "completed":
                await cls.execute_step_1_discovery(db, run, step_map["discovery"])

            # Step 2: Rights Validation
            run.current_step = "rights_validation"
            await db.commit()
            if "rights_validation" in step_map and step_map["rights_validation"].status != "completed":
                await cls.execute_step_2_rights_validation(db, run, step_map["rights_validation"])

            # Step 3: Intelligence
            run.current_step = "intelligence"
            await db.commit()
            if "intelligence" in step_map and step_map["intelligence"].status != "completed":
                await cls.execute_step_3_intelligence(db, run, step_map["intelligence"])

            # Step 4: Selection
            run.current_step = "selection"
            await db.commit()
            if "selection" in step_map and step_map["selection"].status != "completed":
                await cls.execute_step_4_selection(db, run, step_map["selection"])

            # Step 5: Production
            run.current_step = "production"
            await db.commit()
            if "production" in step_map and step_map["production"].status != "completed":
                await cls.execute_step_5_production(db, run, step_map["production"])

            # Step 6: Distribution
            run.current_step = "distribution"
            await db.commit()
            if "distribution" in step_map and step_map["distribution"].status != "completed":
                await cls.execute_step_6_distribution(db, run, step_map["distribution"])

            # Step 7: Monitoring
            run.current_step = "monitoring"
            await db.commit()
            if "monitoring" in step_map and step_map["monitoring"].status != "completed":
                await cls.execute_step_7_monitoring(db, run, step_map["monitoring"])

            run.status = "completed"
            run.current_step = "completed"
            run.completed_at = datetime.now(timezone.utc)
            await cls.log_event(
                db, run.id, "INFO", f"Workflow {run_id} completed successfully"
            )

        except Exception as e:
            run.status = "failed"
            run.error_details = str(e)
            run.completed_at = datetime.now(timezone.utc)
            await cls.log_event(
                db, run.id, "ERROR", f"Workflow {run_id} failed at step '{run.current_step}': {str(e)}"
            )

        await db.commit()
        await db.refresh(run)
        return run

    # ---------------- Workflow Control & Recovery ----------------

    @classmethod
    async def pause_workflow(cls, db: AsyncSession, run_id: str) -> WorkflowRun:
        """Pause an active workflow."""
        stmt = select(WorkflowRun).where(WorkflowRun.run_id == run_id)
        run = (await db.execute(stmt)).scalar_one_or_none()
        if not run:
            raise ValueError(f"Workflow '{run_id}' not found")
        if run.status not in ["running", "pending", "queued"]:
            raise ValueError(f"Cannot pause workflow in '{run.status}' state")
        run.status = "paused"
        await cls.log_event(db, run.id, "WARNING", f"Workflow {run_id} paused by operator")
        await db.commit()
        await db.refresh(run)
        return run

    @classmethod
    async def resume_workflow(cls, db: AsyncSession, run_id: str) -> WorkflowRun:
        """Resume a paused workflow."""
        stmt = select(WorkflowRun).where(WorkflowRun.run_id == run_id)
        run = (await db.execute(stmt)).scalar_one_or_none()
        if not run:
            raise ValueError(f"Workflow '{run_id}' not found")
        if run.status != "paused":
            raise ValueError(f"Workflow is '{run.status}', not paused")
        run.status = "queued"
        await cls.log_event(db, run.id, "INFO", f"Workflow {run_id} resumed by operator")
        await db.commit()
        # Trigger execution
        return await cls.run_full_pipeline(db, run_id)

    @classmethod
    async def cancel_workflow(cls, db: AsyncSession, run_id: str) -> WorkflowRun:
        """Safely cancel an active workflow."""
        stmt = select(WorkflowRun).where(WorkflowRun.run_id == run_id)
        run = (await db.execute(stmt)).scalar_one_or_none()
        if not run:
            raise ValueError(f"Workflow '{run_id}' not found")
        run.status = "cancelled"
        run.completed_at = datetime.now(timezone.utc)
        await cls.log_event(db, run.id, "WARNING", f"Workflow {run_id} cancelled by operator")
        await db.commit()
        await db.refresh(run)
        return run

    @classmethod
    async def get_current_workflow(cls, db: AsyncSession) -> Optional[WorkflowRun]:
        """Retrieve the currently active or most recent workflow run."""
        stmt = (
            select(WorkflowRun)
            .options(selectinload(WorkflowRun.steps), selectinload(WorkflowRun.logs))
            .order_by(WorkflowRun.id.desc())
            .limit(1)
        )
        return (await db.execute(stmt)).scalars().first()

    @classmethod
    async def list_workflows(
        cls, db: AsyncSession, limit: int = 20, status: Optional[str] = None
    ) -> List[WorkflowRun]:
        """List workflow history."""
        stmt = (
            select(WorkflowRun)
            .options(selectinload(WorkflowRun.steps))
            .order_by(WorkflowRun.id.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(WorkflowRun.status == status)
        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def get_workflow_by_id(cls, db: AsyncSession, run_id: str) -> Optional[WorkflowRun]:
        """Retrieve full workflow run by run_id string."""
        stmt = (
            select(WorkflowRun)
            .options(selectinload(WorkflowRun.steps), selectinload(WorkflowRun.logs))
            .where(WorkflowRun.run_id == run_id)
        )
        return (await db.execute(stmt)).scalars().first()

    @classmethod
    async def recover_stalled_workflows(cls, db: AsyncSession) -> int:
        """Detect workflows stuck in 'running' state after application restart and recover."""
        cutoff = datetime.now(timezone.utc)
        stmt = select(WorkflowRun).where(WorkflowRun.status == "running")
        stalled = list((await db.execute(stmt)).scalars().all())
        recovered_count = 0

        for run in stalled:
            # Mark stalled workflow as retrying or failed with recovery log
            run.status = "failed"
            run.error_details = "Worker restart or process interrupted while workflow was in-flight."
            run.completed_at = datetime.now(timezone.utc)
            await cls.log_event(
                db,
                run.id,
                "WARNING",
                f"Recovered stalled workflow #{run.id} after worker restart",
            )
            recovered_count += 1

        if recovered_count > 0:
            await db.commit()
        return recovered_count
