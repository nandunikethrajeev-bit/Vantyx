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
