import {
  AnalysisJob,
  AutomationStatus,
  CandidateClip,
  Creator,
  DailyPublishingPlan,
  DailySelectionResponse,
  DailySlotsResponse,
  DiscoveryRunResult,
  HealthResponse,
  OAuthUrlResponse,
  PublishSchedule,
  PublishTriggerResponse,
  ReadinessResponse,
  RankingWeightsInput,
  RenderJob,
  RenderSettingsInput,
  RightsRecord,
  VideoScene,
  VideoSource,
  WorkflowRun,
  YouTubeAccount,
  ChannelAnalyticsOverview,
  PublishedVideoPerformance,
  PerformanceIntelligence,
  AnalyticsCollectionJob,
  FeedbackStatus,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`;
    try {
      const errorJson = await response.json();
      if (errorJson.error?.message) {
        errorDetail = errorJson.error.message;
      } else if (errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return await response.json();
}

// ---------------- System Health ----------------

export async function checkBackendLiveness(timeoutMs = 4000): Promise<HealthResponse> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await request<HealthResponse>('/api/v1/health', { signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

export async function checkBackendReadiness(timeoutMs = 4000): Promise<ReadinessResponse> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await request<ReadinessResponse>('/api/v1/health/ready', { signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

// ---------------- Discovery & Creators API ----------------

export async function fetchCreators(): Promise<Creator[]> {
  return await request<Creator[]>('/api/v1/discovery/creators');
}

export async function createCreator(data: {
  name: string;
  channel_id: string;
  channel_handle?: string;
  channel_url?: string;
  content_category?: string;
  is_monitored?: boolean;
  approval_status?: string;
  permission_tier?: string;
  notes?: string;
}): Promise<Creator> {
  return await request<Creator>('/api/v1/discovery/creators', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateCreator(
  creatorId: number,
  data: Partial<Creator>
): Promise<Creator> {
  return await request<Creator>(`/api/v1/discovery/creators/${creatorId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteCreator(creatorId: number): Promise<void> {
  await request<void>(`/api/v1/discovery/creators/${creatorId}`, {
    method: 'DELETE',
  });
}

export async function discoverCreatorVideos(creatorId: number): Promise<VideoSource[]> {
  return await request<VideoSource[]>(`/api/v1/discovery/creators/${creatorId}/discover`, {
    method: 'POST',
  });
}

export async function runGlobalDiscovery(): Promise<DiscoveryRunResult> {
  return await request<DiscoveryRunResult>('/api/v1/discovery/run', {
    method: 'POST',
  });
}

// ---------------- Video Sources & Rights API ----------------

export async function fetchVideoSources(creatorId?: number, eligibleOnly = false): Promise<VideoSource[]> {
  let url = '/api/v1/discovery/sources';
  const params = new URLSearchParams();
  if (creatorId) params.append('creator_id', creatorId.toString());
  if (eligibleOnly) params.append('eligible_only', 'true');
  if (params.toString()) url += `?${params.toString()}`;
  return await request<VideoSource[]>(url);
}

export async function importManualSource(data: {
  video_id: string;
  title: string;
  source_url: string;
  description?: string;
  duration_seconds?: number;
  creator_id?: number;
  is_own_gameplay?: boolean;
  attribution_text?: string;
}): Promise<VideoSource> {
  return await request<VideoSource>('/api/v1/discovery/sources', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateSourceRights(
  sourceId: number,
  data: {
    permission_status?: string;
    commercial_use_allowed?: boolean;
    allowed_editing_scope?: string;
    attribution_required?: boolean;
    attribution_text?: string;
    license_documentation?: string;
    verified_by?: string;
  }
): Promise<RightsRecord> {
  return await request<RightsRecord>(`/api/v1/discovery/sources/${sourceId}/rights`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// ---------------- AI Intelligence API ----------------

export async function triggerVideoAnalysis(
  sourceId: number,
  force = false,
  provider?: string
): Promise<AnalysisJob> {
  return await request<AnalysisJob>(`/api/v1/intelligence/analyze/${sourceId}`, {
    method: 'POST',
    body: JSON.stringify({
      force_reanalysis: force,
      provider_override: provider,
    }),
  });
}

export async function fetchAnalysisJobs(sourceId?: number): Promise<AnalysisJob[]> {
  let url = '/api/v1/intelligence/jobs';
  if (sourceId) url += `?source_id=${sourceId}`;
  return await request<AnalysisJob[]>(url);
}

export async function fetchSourceScenes(sourceId: number): Promise<VideoScene[]> {
  return await request<VideoScene[]>(`/api/v1/intelligence/sources/${sourceId}/scenes`);
}

// ---------------- Selection & Candidate Ranking API ----------------

export async function generateCandidates(
  sourceId: number,
  options: {
    min_score_threshold?: number;
    max_candidates?: number;
    weights?: RankingWeightsInput;
  } = {}
): Promise<CandidateClip[]> {
  return await request<CandidateClip[]>(`/api/v1/selection/generate/${sourceId}`, {
    method: 'POST',
    body: JSON.stringify(options),
  });
}

export async function fetchCandidates(
  sourceId?: number,
  status?: string
): Promise<CandidateClip[]> {
  let url = '/api/v1/selection/candidates';
  const params = new URLSearchParams();
  if (sourceId) params.append('source_id', sourceId.toString());
  if (status) params.append('status', status);
  if (params.toString()) url += `?${params.toString()}`;
  return await request<CandidateClip[]>(url);
}

export async function getCandidate(candidateId: number): Promise<CandidateClip> {
  return await request<CandidateClip>(`/api/v1/selection/candidates/${candidateId}`);
}

export async function updateCandidate(
  candidateId: number,
  data: {
    status?: string;
    title_suggestion?: string;
    start_time?: number;
    end_time?: number;
  }
): Promise<CandidateClip> {
  return await request<CandidateClip>(`/api/v1/selection/candidates/${candidateId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function fetchDailyQueue(targetCount = 4): Promise<DailySelectionResponse> {
  return await request<DailySelectionResponse>(`/api/v1/selection/daily-queue?target_count=${targetCount}`);
}

// ---------------- Production & Video Rendering API ----------------

export async function triggerRender(
  candidateId: number,
  settings: RenderSettingsInput = {}
): Promise<RenderJob> {
  return await request<RenderJob>(`/api/v1/production/render/${candidateId}`, {
    method: 'POST',
    body: JSON.stringify(settings),
  });
}

export async function fetchRenderJobs(status?: string, limit = 50): Promise<RenderJob[]> {
  let url = `/api/v1/production/jobs?limit=${limit}`;
  if (status) url += `&status=${status}`;
  return await request<RenderJob[]>(url);
}

export async function getRenderJob(jobId: number): Promise<RenderJob> {
  return await request<RenderJob>(`/api/v1/production/jobs/${jobId}`);
}

export function getRenderStreamUrl(jobId: number): string {
  return `${API_BASE_URL}/api/v1/production/jobs/${jobId}/stream`;
}

export function getRenderThumbnailUrl(jobId: number): string {
  return `${API_BASE_URL}/api/v1/production/jobs/${jobId}/thumbnail`;
}

// ---------------- Distribution & Publishing API ----------------

export async function fetchOAuthUrl(): Promise<OAuthUrlResponse> {
  return await request<OAuthUrlResponse>('/api/v1/distribution/oauth/url');
}

export async function fetchChannelStatus(): Promise<YouTubeAccount | null> {
  return await request<YouTubeAccount | null>('/api/v1/distribution/channel');
}

export async function disconnectChannel(): Promise<{ message: string }> {
  return await request<{ message: string }>('/api/v1/distribution/disconnect', {
    method: 'POST',
  });
}

export async function fetchDailySlots(targetDate?: string): Promise<DailySlotsResponse> {
  let url = '/api/v1/distribution/slots';
  if (targetDate) url += `?target_date=${targetDate}`;
  return await request<DailySlotsResponse>(url);
}

export async function createSchedule(data: {
  candidate_id: number;
  render_job_id: number;
  target_date: string;
  slot_name: string;
  title?: string;
  custom_description?: string;
}): Promise<PublishSchedule> {
  return await request<PublishSchedule>('/api/v1/distribution/schedule', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function fetchSchedules(status?: string, limit = 50): Promise<PublishSchedule[]> {
  let url = `/api/v1/distribution/schedules?limit=${limit}`;
  if (status) url += `&status=${status}`;
  return await request<PublishSchedule[]>(url);
}

export async function cancelSchedule(scheduleId: number): Promise<{ message: string }> {
  return await request<{ message: string }>(`/api/v1/distribution/schedule/${scheduleId}`, {
    method: 'DELETE',
  });
}

export async function triggerPublish(
  scheduleId: number,
  forceMock = false
): Promise<PublishTriggerResponse> {
  return await request<PublishTriggerResponse>(
    `/api/v1/distribution/publish/${scheduleId}?force_mock=${forceMock}`,
    {
      method: 'POST',
    }
  );
}

// ---------------- Orchestration & Automation API ----------------

export async function fetchAutomationStatus(): Promise<AutomationStatus> {
  return await request<AutomationStatus>('/api/v1/orchestration/status');
}

export async function updateAutomationConfig(data: {
  automation_enabled?: boolean;
  daily_run_time_ist?: string;
  max_concurrent_renders?: number;
}): Promise<AutomationStatus> {
  return await request<AutomationStatus>('/api/v1/orchestration/config', {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function startWorkflow(data: {
  target_date?: string;
  force?: boolean;
  execute_sync?: boolean;
} = {}): Promise<WorkflowRun> {
  return await request<WorkflowRun>('/api/v1/orchestration/start', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function fetchCurrentWorkflow(): Promise<WorkflowRun | null> {
  return await request<WorkflowRun | null>('/api/v1/orchestration/workflows/current');
}

export async function fetchWorkflowHistory(limit = 20, status?: string): Promise<WorkflowRun[]> {
  let url = `/api/v1/orchestration/workflows?limit=${limit}`;
  if (status) url += `&status=${status}`;
  return await request<WorkflowRun[]>(url);
}

export async function getWorkflowDetails(runId: string): Promise<WorkflowRun> {
  return await request<WorkflowRun>(`/api/v1/orchestration/workflows/${runId}`);
}

export async function pauseWorkflow(runId: string): Promise<WorkflowRun> {
  return await request<WorkflowRun>(`/api/v1/orchestration/workflows/${runId}/pause`, {
    method: 'POST',
  });
}

export async function resumeWorkflow(runId: string): Promise<WorkflowRun> {
  return await request<WorkflowRun>(`/api/v1/orchestration/workflows/${runId}/resume`, {
    method: 'POST',
  });
}

export async function cancelWorkflow(runId: string): Promise<WorkflowRun> {
  return await request<WorkflowRun>(`/api/v1/orchestration/workflows/${runId}/cancel`, {
    method: 'POST',
  });
}

export async function fetchDailyPublishingPlan(targetDate?: string): Promise<DailyPublishingPlan> {
  let url = '/api/v1/orchestration/plan';
  if (targetDate) url += `?target_date=${targetDate}`;
  return await request<DailyPublishingPlan>(url);
}

export async function triggerWorkflowRecovery(): Promise<{ recovered_count: number; message: string }> {
  return await request<{ recovered_count: number; message: string }>('/api/v1/orchestration/recover', {
    method: 'POST',
  });
}

// ---------------- Audience Analytics & Performance Feedback API ----------------

export async function fetchAnalyticsOverview(): Promise<ChannelAnalyticsOverview> {
  return await request<ChannelAnalyticsOverview>('/api/v1/analytics/overview');
}

export async function fetchPublishedVideosPerformance(): Promise<PublishedVideoPerformance[]> {
  return await request<PublishedVideoPerformance[]>('/api/v1/analytics/videos');
}

export async function fetchPerformanceInsights(): Promise<PerformanceIntelligence> {
  return await request<PerformanceIntelligence>('/api/v1/analytics/insights');
}

export async function triggerAnalyticsCollection(): Promise<AnalyticsCollectionJob> {
  return await request<AnalyticsCollectionJob>('/api/v1/analytics/collect', {
    method: 'POST',
  });
}

export async function fetchAnalyticsJobs(limit = 20): Promise<AnalyticsCollectionJob[]> {
  return await request<AnalyticsCollectionJob[]>(`/api/v1/analytics/jobs?limit=${limit}`);
}

export async function fetchFeedbackStatus(): Promise<FeedbackStatus> {
  return await request<FeedbackStatus>('/api/v1/analytics/feedback/status');
}

export async function updateFeedbackConfig(data: {
  feedback_enabled?: boolean;
  max_impact?: number;
  min_sample_size?: number;
}): Promise<{ feedback_enabled: boolean; max_impact: number; min_sample_size: number }> {
  return await request<{ feedback_enabled: boolean; max_impact: number; min_sample_size: number }>(
    '/api/v1/analytics/feedback/config',
    {
      method: 'PATCH',
      body: JSON.stringify(data),
    }
  );
}



