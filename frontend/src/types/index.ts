export type NavigationSection =
  | 'overview'
  | 'discovery'
  | 'intelligence'
  | 'selection'
  | 'production'
  | 'distribution'
  | 'orchestration'
  | 'analytics'
  | 'settings';

export interface ComponentHealth {
  status: 'healthy' | 'degraded' | 'unreachable' | 'mock_mode' | 'heuristic_fallback' | 'eager_development' | string;
  message: string;
  latency_ms?: number | null;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  app: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface ReadinessResponse {
  status: 'ready' | 'degraded';
  timestamp: string;
  components: {
    database: ComponentHealth;
    [key: string]: ComponentHealth;
  };
}

export type ConnectionState = 'connecting' | 'connected' | 'degraded' | 'offline';

// ---------------- Discovery & Rights Domain Types ----------------

export interface Creator {
  id: number;
  name: string;
  channel_id: string;
  channel_handle?: string | null;
  channel_url?: string | null;
  content_category: string;
  is_monitored: boolean;
  approval_status: 'pending' | 'approved' | 'rejected';
  permission_tier: 'own_content' | 'authorized_partner' | 'public_creative_commons' | 'unverified';
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RightsRecord {
  id: number;
  source_id: number;
  permission_status: 'pending' | 'authorized' | 'rejected' | 'revoked' | 'own_gameplay';
  commercial_use_allowed: boolean;
  allowed_editing_scope: 'full' | 'clip_only' | 'transformative_shorts' | 'restricted';
  attribution_required: boolean;
  attribution_text?: string | null;
  license_documentation?: string | null;
  verified_by?: string | null;
  verified_at?: string | null;
  expires_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface VideoSource {
  id: number;
  creator_id?: number | null;
  creator_name?: string | null;
  video_id: string;
  title: string;
  description?: string | null;
  duration_seconds: number;
  published_at?: string | null;
  thumbnail_url?: string | null;
  source_url: string;
  discovery_method: string;
  local_video_path?: string | null;
  rights?: RightsRecord | null;
  is_eligible: boolean;
  created_at: string;
  updated_at: string;
}

export interface DiscoveryRunResult {
  channels_polled: number;
  videos_discovered: number;
  duplicates_skipped: number;
  errors: string[];
  timestamp: string;
}

// ---------------- Intelligence & Scene Understanding ----------------

export interface VideoScene {
  id: number;
  job_id: number;
  source_id: number;
  start_time: number;
  end_time: number;
  duration_seconds: number;
  scene_label: string;
  description?: string | null;
  speech_transcript?: string | null;
  action_intensity: number;
  excitement_score: number;
  tags?: string[] | null;
  created_at: string;
}

export interface AnalysisJob {
  id: number;
  source_id: number;
  video_title?: string | null;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  provider: string;
  error_message?: string | null;
  scene_count: number;
  scenes: VideoScene[];
  created_at: string;
  updated_at: string;
}

// ---------------- Selection & Moment Ranking ----------------

export interface CandidateClip {
  id: number;
  source_id: number;
  scene_id?: number | null;
  start_time: number;
  end_time: number;
  duration_seconds: number;
  title_suggestion: string;
  hook_score: number;
  retention_score: number;
  context_score: number;
  audio_score: number;
  overall_score: number;
  status: 'candidate' | 'approved' | 'rejected' | 'produced';
  rationale?: string | null;
  video_title?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DailySelectionResponse {
  target_count: number;
  selected_count: number;
  has_sufficient_moments: boolean;
  candidates: CandidateClip[];
}

export interface RankingWeightsInput {
  hook_weight?: number;
  retention_weight?: number;
  context_weight?: number;
  audio_weight?: number;
}

// ---------------- Production & Video Rendering ----------------

export interface RenderSettingsInput {
  layout_style?: 'blurred_backdrop' | 'crop_center';
  has_burned_subtitles?: boolean;
  resolution?: string;
  normalize_audio?: boolean;
}

export interface RenderJob {
  id: number;
  candidate_id: number;
  source_id: number;
  status: 'queued' | 'rendering' | 'completed' | 'failed';
  progress_pct: number;
  output_file_path?: string | null;
  thumbnail_path?: string | null;
  resolution: string;
  format_aspect: string;
  layout_style: string;
  has_burned_subtitles: boolean;
  is_synthetic?: boolean;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

// ---------------- Distribution & Publishing Domain Types ----------------

export interface YouTubeAccount {
  id: number;
  channel_id: string;
  channel_title: string;
  channel_handle?: string | null;
  thumbnail_url?: string | null;
  is_active: boolean;
  connected_at: string;
}

export interface OAuthUrlResponse {
  configured: boolean;
  auth_url?: string | null;
  message?: string | null;
}

export interface UploadJob {
  id: number;
  schedule_id: number;
  attempt_number: number;
  status: 'uploading' | 'processing' | 'verified' | 'failed';
  bytes_uploaded: number;
  total_bytes: number;
  error_detail?: string | null;
  started_at: string;
  completed_at?: string | null;
}

export interface PublishSchedule {
  id: number;
  candidate_id: number;
  render_job_id: number;
  scheduled_time: string;
  slot_name: string;
  timezone: string;
  target_channel: string;
  title: string;
  description?: string | null;
  tags?: string | null;
  privacy_status: string;
  status: 'scheduled' | 'publishing' | 'published' | 'failed' | 'cancelled';
  youtube_video_id?: string | null;
  publish_url?: string | null;
  retry_count: number;
  is_mock: boolean;
  error_message?: string | null;
  upload_jobs?: UploadJob[];
  created_at: string;
  updated_at: string;
}

export interface SlotInfo {
  slot_name: string;
  scheduled_time_utc: string;
  scheduled_time_local: string;
  status: 'unfilled' | 'scheduled' | 'published' | 'expired';
  schedule?: PublishSchedule | null;
}

export interface DailySlotsResponse {
  target_date: string;
  timezone: string;
  slots: SlotInfo[];
}

export interface PublishTriggerResponse {
  schedule_id: number;
  status: string;
  youtube_video_id?: string | null;
  publish_url?: string | null;
  is_mock: boolean;
  message: string;
}

// ---------------- Orchestration & Autonomous Workflow ----------------

export interface WorkflowStep {
  id: number;
  step_name: string;
  step_order: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  started_at?: string | null;
  completed_at?: string | null;
  error_details?: string | null;
  output_data?: Record<string, any> | null;
}

export interface JobExecutionLog {
  id: number;
  workflow_run_id?: number | null;
  job_id?: number | null;
  level: string;
  message: string;
  context_data?: Record<string, any> | null;
  timestamp: string;
}

export interface WorkflowRun {
  id: number;
  run_id: string;
  workflow_type: string;
  target_date: string;
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'retrying' | 'cancelled' | 'paused';
  current_step: string;
  started_at: string;
  completed_at?: string | null;
  error_details?: string | null;
  retry_count: number;
  execution_metadata?: Record<string, any> | null;
  steps: WorkflowStep[];
  logs: JobExecutionLog[];
}

export interface DailyPublishingPlan {
  id: number;
  plan_date: string;
  timezone: string;
  status: 'planning' | 'ready' | 'in_progress' | 'fulfilled' | 'partial' | 'unfulfilled';
  target_count: number;
  filled_count: number;
  slot_assignments?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationStatus {
  automation_enabled: boolean;
  daily_run_time_ist: string;
  timezone: string;
  celery_mode: 'eager' | 'distributed';
  redis_connected: boolean;
  active_worker_count: number;
  max_concurrent_renders: number;
  current_workflow_id?: string | null;
  today_plan_status?: string | null;
  filled_slots_today: number;
  next_scheduled_run?: string | null;
  disk_free_gb: number;
}

// ---------------- Audience Analytics & Feedback Domain Types ----------------

export interface ChannelAnalyticsOverview {
  channel_id: string;
  channel_name: string;
  snapshot_date: string;
  total_views: number;
  total_subscribers: number;
  subscribers_gained: number;
  total_videos: number;
  estimated_minutes_watched: number;
  average_view_duration_seconds: number;
  average_view_percentage: number;
  collection_source: 'api' | 'mock';
  is_delayed_reporting: boolean;
  history_trend: Array<{
    date: string;
    views: number;
    subscribers: number;
    minutes_watched: number;
  }>;
}

export interface PublishedVideoPerformance {
  schedule_id: number;
  youtube_video_id?: string | null;
  title: string;
  slot_name: string;
  scheduled_time: string;
  age_days: number;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  subscribers_gained: number;
  average_view_duration_seconds: number;
  average_view_percentage: number;
  relative_retention_index: number;
  hook_retention_rate: number;
  category: string;
  duration_bucket: string;
  reporting_status: 'complete' | 'partial' | 'delayed' | 'inaccessible' | 'pending';
  is_delayed_reporting: boolean;
}

export interface InsightBucket {
  key: string;
  label: string;
  sample_size: number;
  avg_views: number;
  avg_retention_pct: number;
  confidence_level: 'low' | 'medium' | 'high';
  relative_multiplier: number;
  rationale: string;
}

export interface PerformanceIntelligence {
  top_clips: Array<{
    candidate_id: number;
    schedule_id?: number | null;
    relative_retention_index: number;
    hook_retention_rate: number;
    views: number;
    average_view_percentage: number;
    category: string;
    duration_bucket: string;
    publish_slot: string;
  }>;
  hook_insights: InsightBucket[];
  duration_insights: InsightBucket[];
  category_insights: InsightBucket[];
  slot_insights: InsightBucket[];
  correlation_vs_causation_notice: string;
  overall_confidence: 'low' | 'medium' | 'high';
  total_samples_analyzed: number;
}

export interface AnalyticsCollectionJob {
  id: number;
  job_id: string;
  job_type: 'scheduled' | 'manual' | 'initial_bootstrap';
  status: 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string | null;
  videos_probed: number;
  snapshots_created: number;
  errors_count: number;
  error_details?: string | null;
}

export interface FeedbackStatus {
  feedback_enabled: boolean;
  max_impact: number;
  min_sample_size: number;
  category_multipliers: Record<string, number>;
  duration_multipliers: Record<string, number>;
  hook_multipliers: Record<string, number>;
  active_profiles_count: number;
}



