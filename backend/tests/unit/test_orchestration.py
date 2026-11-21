"""Unit tests for VANTYX Autonomous Orchestration Service."""

import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.orchestration import WorkflowRun, WorkflowStep, DailyPublishingPlan
from app.modules.orchestration.service import OrchestrationService, PIPELINE_STEPS


@pytest.mark.asyncio
async def test_daily_plan_initialization_four_slots(async_db_session: AsyncSession):
    """Verify that get_or_create_daily_plan initializes 4 slots in Asia/Kolkata."""
    test_date = f"2027-05-{uuid.uuid4().hex[:6]}"
    plan = await OrchestrationService.get_or_create_daily_plan(async_db_session, test_date)

    assert plan.plan_date == test_date
    assert plan.target_count == 4
    assert plan.filled_count == 0
    assert plan.timezone == "Asia/Kolkata"
    assert plan.status == "planning"

    slots = plan.slot_assignments
    assert "09:00" in slots
    assert "13:00" in slots
    assert "17:00" in slots
    assert "21:00" in slots
    assert slots["09:00"]["status"] == "unfilled"


@pytest.mark.asyncio
async def test_workflow_run_initializes_seven_steps(async_db_session: AsyncSession):
    """Verify that create_workflow_run initializes all 7 pipeline steps."""
    test_date = f"2027-05-{uuid.uuid4().hex[:6]}"
    run = await OrchestrationService.create_workflow_run(
        async_db_session, target_date=test_date, force=True
    )

    assert run.target_date == test_date
    assert run.status == "pending"
    assert run.current_step == "discovery"
    assert run.run_id.startswith("wf_")

    assert len(run.steps) == 7
    step_names = [s.step_name for s in run.steps]
    expected_steps = [s[0] for s in PIPELINE_STEPS]
    assert step_names == expected_steps

    for step in run.steps:
        assert step.status == "pending"


@pytest.mark.asyncio
async def test_duplicate_workflow_prevention(async_db_session: AsyncSession):
    """Verify that create_workflow_run returns existing active run unless forced."""
    test_date = f"2027-05-{uuid.uuid4().hex[:6]}"
    run1 = await OrchestrationService.create_workflow_run(
        async_db_session, target_date=test_date, force=True
    )
    # Attempt to create duplicate without force
    run2 = await OrchestrationService.create_workflow_run(
        async_db_session, target_date=test_date, force=False
    )

    assert run1.id == run2.id
    assert run1.run_id == run2.run_id


@pytest.mark.asyncio
async def test_workflow_pause_and_cancel_lifecycle(async_db_session: AsyncSession):
    """Verify state transitions for pausing and cancelling workflows."""
    test_date = f"2027-05-{uuid.uuid4().hex[:6]}"
    run = await OrchestrationService.create_workflow_run(
        async_db_session, target_date=test_date, force=True
    )

    # Pause
    paused = await OrchestrationService.pause_workflow(async_db_session, run.run_id)
    assert paused.status == "paused"

    # Cancel
    cancelled = await OrchestrationService.cancel_workflow(async_db_session, run.run_id)
    assert cancelled.status == "cancelled"
    assert cancelled.completed_at is not None


@pytest.mark.asyncio
async def test_stalled_workflow_recovery(async_db_session: AsyncSession):
    """Verify that recover_stalled_workflows recovers in-flight workflows after restart."""
    test_date = f"2027-05-{uuid.uuid4().hex[:6]}"
    run = await OrchestrationService.create_workflow_run(
        async_db_session, target_date=test_date, force=True
    )
    run.status = "running"
    await async_db_session.commit()

    recovered_count = await OrchestrationService.recover_stalled_workflows(async_db_session)
    assert recovered_count >= 1

    await async_db_session.refresh(run)
    assert run.status == "failed"
    assert "Worker restart" in run.error_details
