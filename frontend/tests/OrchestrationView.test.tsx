import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { OrchestrationView } from '@/features/orchestration/OrchestrationView';
import * as api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  fetchAutomationStatus: vi.fn(),
  fetchCurrentWorkflow: vi.fn(),
  fetchWorkflowHistory: vi.fn(),
  fetchDailyPublishingPlan: vi.fn(),
  updateAutomationConfig: vi.fn(),
  startWorkflow: vi.fn(),
  pauseWorkflow: vi.fn(),
  resumeWorkflow: vi.fn(),
  cancelWorkflow: vi.fn(),
  triggerWorkflowRecovery: vi.fn(),
}));

describe('OrchestrationView', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.fetchAutomationStatus).mockResolvedValue({
      automation_enabled: false,
      daily_run_time_ist: '06:00',
      timezone: 'Asia/Kolkata',
      celery_mode: 'eager',
      redis_connected: false,
      active_worker_count: 0,
      max_concurrent_renders: 2,
      current_workflow_id: 'wf_test_101',
      today_plan_status: 'planning',
      filled_slots_today: 0,
      next_scheduled_run: '2027-03-01 06:00 IST',
      disk_free_gb: 45.2,
    });

    vi.mocked(api.fetchCurrentWorkflow).mockResolvedValue({
      id: 1,
      run_id: 'wf_test_101',
      workflow_type: 'daily_autonomous_publishing',
      target_date: '2027-03-01',
      status: 'completed',
      current_step: 'completed',
      started_at: '2027-03-01T06:00:00Z',
      completed_at: '2027-03-01T06:01:30Z',
      error_details: null,
      retry_count: 0,
      execution_metadata: {
        sources_discovered: 3,
        eligible_sources: 2,
        scenes_indexed: 12,
        candidates_selected: 4,
        shorts_rendered: 2,
        slots_scheduled: 2,
      },
      steps: [
        { id: 1, step_name: 'discovery', step_order: 1, status: 'completed' },
        { id: 2, step_name: 'rights_validation', step_order: 2, status: 'completed' },
        { id: 3, step_name: 'intelligence', step_order: 3, status: 'completed' },
        { id: 4, step_name: 'selection', step_order: 4, status: 'completed' },
        { id: 5, step_name: 'production', step_order: 5, status: 'completed' },
        { id: 6, step_name: 'distribution', step_order: 6, status: 'completed' },
        { id: 7, step_name: 'monitoring', step_order: 7, status: 'completed' },
      ],
      logs: [
        {
          id: 1,
          workflow_run_id: 1,
          job_id: null,
          level: 'INFO',
          message: 'Initialized workflow run wf_test_101',
          timestamp: '2027-03-01T06:00:00Z',
        },
      ],
    });

    vi.mocked(api.fetchWorkflowHistory).mockResolvedValue([]);

    vi.mocked(api.fetchDailyPublishingPlan).mockResolvedValue({
      id: 1,
      plan_date: '2027-03-01',
      timezone: 'Asia/Kolkata',
      status: 'partial',
      target_count: 4,
      filled_count: 2,
      slot_assignments: {
        '09:00': { slot_name: '09:00', status: 'published', candidate_id: 10, youtube_video_id: 'mock_yt_1' },
        '13:00': { slot_name: '13:00', status: 'scheduled', candidate_id: 11, youtube_video_id: null },
        '17:00': { slot_name: '17:00', status: 'unfilled' },
        '21:00': { slot_name: '21:00', status: 'unfilled' },
      },
      created_at: '2027-03-01T00:00:00Z',
      updated_at: '2027-03-01T06:01:00Z',
    });
  });

  it('renders orchestration workspace with status card and 7 pipeline stages', async () => {
    render(<OrchestrationView />);

    expect(screen.getByText('Autonomous Orchestration Engine')).toBeInTheDocument();
    expect(screen.getByText('M07 ACTIVE')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Automation Scheduler:')).toBeInTheDocument();
      expect(screen.getByText('DISABLED')).toBeInTheDocument();
    });

    // Check 7 pipeline stages
    expect(screen.getByText('1. Discovery')).toBeInTheDocument();
    expect(screen.getByText('2. Rights Gate')).toBeInTheDocument();
    expect(screen.getByText('3. Intelligence')).toBeInTheDocument();
    expect(screen.getByText('4. Selection')).toBeInTheDocument();
    expect(screen.getByText('5. Production')).toBeInTheDocument();
    expect(screen.getByText('6. Distribution')).toBeInTheDocument();
    expect(screen.getByText('7. Monitoring')).toBeInTheDocument();

    // Check daily plan slots
    expect(screen.getByText('09:00 IST')).toBeInTheDocument();
    expect(screen.getByText('13:00 IST')).toBeInTheDocument();
    expect(screen.getByText('17:00 IST')).toBeInTheDocument();
    expect(screen.getByText('21:00 IST')).toBeInTheDocument();
  });

  it('toggles automation enabled state when Enable Automation is clicked', async () => {
    vi.mocked(api.updateAutomationConfig).mockResolvedValue({
      automation_enabled: true,
      daily_run_time_ist: '06:00',
      timezone: 'Asia/Kolkata',
      celery_mode: 'eager',
      redis_connected: false,
      active_worker_count: 0,
      max_concurrent_renders: 2,
      filled_slots_today: 0,
      disk_free_gb: 45.2,
    });

    render(<OrchestrationView />);

    await waitFor(() => {
      expect(screen.getByText('Enable Automation')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Enable Automation'));

    await waitFor(() => {
      expect(api.updateAutomationConfig).toHaveBeenCalledWith({ automation_enabled: true });
    });
  });

  it('triggers pipeline execution when Run Pipeline Now is clicked', async () => {
    vi.mocked(api.startWorkflow).mockResolvedValue({
      id: 2,
      run_id: 'wf_manual_102',
      workflow_type: 'daily_autonomous_publishing',
      target_date: '2027-03-01',
      status: 'completed',
      current_step: 'completed',
      started_at: '2027-03-01T07:00:00Z',
      retry_count: 0,
      steps: [],
      logs: [],
    });

    render(<OrchestrationView />);

    await waitFor(() => {
      expect(screen.getByText('Run Pipeline Now')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Run Pipeline Now'));

    await waitFor(() => {
      expect(api.startWorkflow).toHaveBeenCalledWith({ force: true, execute_sync: true });
    });
  });
});
