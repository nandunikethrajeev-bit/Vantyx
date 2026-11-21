export type NavigationSection =
  | 'overview'
  | 'discovery'
  | 'intelligence'
  | 'production'
  | 'distribution'
  | 'analytics'
  | 'settings';

export interface ComponentHealth {
  status: 'healthy' | 'degraded' | 'unreachable';
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
