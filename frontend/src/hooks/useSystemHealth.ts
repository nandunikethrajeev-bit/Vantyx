import { useEffect, useState, useCallback } from 'react';
import { checkBackendLiveness, checkBackendReadiness } from '@/lib/api';
import { ConnectionState, HealthResponse, ReadinessResponse } from '@/types';

export interface SystemHealthState {
  connectionState: ConnectionState;
  liveness: HealthResponse | null;
  readiness: ReadinessResponse | null;
  lastChecked: Date | null;
  errorMessage: string | null;
  isChecking: boolean;
  refresh: () => Promise<void>;
}

export function useSystemHealth(pollIntervalMs = 15000): SystemHealthState {
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');
  const [liveness, setLiveness] = useState<HealthResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isChecking, setIsChecking] = useState<boolean>(false);

  const checkHealth = useCallback(async () => {
    setIsChecking(true);
    try {
      // 1. Probe basic liveness
      const live = await checkBackendLiveness();
      setLiveness(live);

      // 2. Probe readiness (includes database connectivity)
      try {
        const ready = await checkBackendReadiness();
        setReadiness(ready);
        if (ready.status === 'ready') {
          setConnectionState('connected');
        } else {
          setConnectionState('degraded');
        }
      } catch {
        setReadiness(null);
        setConnectionState('degraded');
      }

      setErrorMessage(null);
    } catch (err) {
      setConnectionState('offline');
      setLiveness(null);
      setReadiness(null);
      setErrorMessage(
        err instanceof Error ? err.message : 'Unable to establish connection to backend service'
      );
    } finally {
      setLastChecked(new Date());
      setIsChecking(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    if (pollIntervalMs > 0) {
      const interval = setInterval(checkHealth, pollIntervalMs);
      return () => clearInterval(interval);
    }
  }, [checkHealth, pollIntervalMs]);

  return {
    connectionState,
    liveness,
    readiness,
    lastChecked,
    errorMessage,
    isChecking,
    refresh: checkHealth,
  };
}
