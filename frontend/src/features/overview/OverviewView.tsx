import React from 'react';
import { Server, Database, ShieldCheck, Layers, Cpu, Cloud, HardDrive } from 'lucide-react';
import { ConnectionState, HealthResponse, ReadinessResponse } from '@/types';

interface OverviewViewProps {
  connectionState: ConnectionState;
  liveness: HealthResponse | null;
  readiness: ReadinessResponse | null;
  errorMessage: string | null;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  connectionState,
  liveness,
  readiness,
  errorMessage,
}) => {
  const redisHealth = readiness?.components?.redis;
  const workerHealth = readiness?.components?.celery_worker;
  const oauthHealth = readiness?.components?.youtube_oauth;
  const aiHealth = readiness?.components?.ai_provider;
  const storageHealth = readiness?.components?.storage;

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      {/* Brand Hero & Architectural Statement */}
      <section className="border-b border-vantyx-border pb-8">
        <div className="flex items-center gap-2 text-xs font-mono tracking-widest text-vantyx-accent uppercase mb-2">
          <span>Milestone 09</span>
          <span>•</span>
          <span>Production Hardening & Deployment</span>
        </div>
        <h2 className="text-2xl font-light tracking-tight text-vantyx-textPrimary">
          VANTYX System Architecture & Production Operations
        </h2>
        <p className="mt-1 text-sm text-vantyx-textSecondary max-w-2xl leading-relaxed">
          The intelligence behind every moment. Fully verified autonomous media intelligence pipeline
          with strict database validation, encrypted credentials at rest, distributed task coordination,
          and production containerization.
        </p>

        {/* Operational Integration Status Badges */}
        <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono">
          <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-2.5">
            <div className="text-[10px] text-vantyx-textMuted uppercase">YouTube Publishing</div>
            <div className="mt-1 flex items-center gap-1.5 font-medium text-vantyx-textPrimary">
              <span className={`h-1.5 w-1.5 rounded-full ${oauthHealth?.status === 'healthy' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
              {oauthHealth?.status === 'healthy' ? 'Official OAuth Live' : 'Verified Mock Mode'}
            </div>
          </div>

          <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-2.5">
            <div className="text-[10px] text-vantyx-textMuted uppercase">AI Intelligence</div>
            <div className="mt-1 flex items-center gap-1.5 font-medium text-vantyx-textPrimary">
              <span className={`h-1.5 w-1.5 rounded-full ${aiHealth?.status === 'healthy' ? 'bg-emerald-400' : 'bg-vantyx-accent'}`} />
              {aiHealth?.status === 'healthy' ? 'Gemini 2.5 Flash' : 'Heuristic Engine'}
            </div>
          </div>

          <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-2.5">
            <div className="text-[10px] text-vantyx-textMuted uppercase">Task Execution</div>
            <div className="mt-1 flex items-center gap-1.5 font-medium text-vantyx-textPrimary">
              <span className={`h-1.5 w-1.5 rounded-full ${readiness?.execution_mode === 'LOCAL IN-PROCESS' ? 'bg-amber-400' : workerHealth?.status === 'healthy' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
              {readiness?.execution_mode || (workerHealth?.status === 'healthy' ? 'DISTRIBUTED CELERY' : 'LOCAL IN-PROCESS')}
            </div>
          </div>

          <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-2.5">
            <div className="text-[10px] text-vantyx-textMuted uppercase">Token Security</div>
            <div className="mt-1 flex items-center gap-1.5 font-medium text-emerald-400">
              <ShieldCheck size={12} />
              AES-256 Encrypted
            </div>
          </div>
        </div>
      </section>

      {/* Live System Telemetry / Diagnostic Probes */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono font-semibold tracking-wider text-vantyx-textMuted uppercase">
            Live Subsystem Verification
          </h3>
          <span className="text-[11px] font-mono text-vantyx-textMuted">
            Probing: <code className="text-vantyx-textSecondary">/api/v1/health</code> &{' '}
            <code className="text-vantyx-textSecondary">/api/v1/health/ready</code>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Card 1: Backend API Service */}
          <div className="rounded border border-vantyx-border bg-vantyx-surface p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="flex items-center gap-2 text-xs font-medium text-vantyx-textSecondary">
                  <Server size={14} className="text-vantyx-accent" /> Backend Core API
                </span>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border ${connectionState !== 'offline'
                    ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10'
                    : 'border-rose-500/30 text-rose-400 bg-rose-500/10'
                    }`}
                >
                  {connectionState !== 'offline' ? 'ACTIVE' : 'UNREACHABLE'}
                </span>
              </div>

              {liveness ? (
                <div className="space-y-1.5 font-mono text-xs text-vantyx-textSecondary">
                  <div className="flex justify-between">
                    <span className="text-vantyx-textMuted">Platform:</span>
                    <span>{liveness.app} v{liveness.version}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-vantyx-textMuted">Environment:</span>
                    <span className="uppercase text-vantyx-accent">{liveness.environment}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-vantyx-textMuted">Execution Mode:</span>
                    <span className="text-vantyx-accent">{liveness.execution_mode || readiness?.execution_mode || 'LOCAL IN-PROCESS'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-vantyx-textMuted">Probe Sync:</span>
                    <span className="text-[11px]">{new Date(liveness.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-rose-400 font-mono space-y-1">
                  <p>Backend service not detected at 127.0.0.1:8000</p>
                  {errorMessage && <p className="text-[11px] text-vantyx-textMuted">{errorMessage}</p>}
                </div>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-vantyx-borderSubtle text-[11px] text-vantyx-textMuted flex items-center justify-between">
              <span>Routing prefix: <code className="text-vantyx-textSecondary">/api/v1</code></span>
              <span>FastAPI 0.115+</span>
            </div>
          </div>

          {/* Card 2: Database Layer (PostgreSQL) */}
          <div className="rounded border border-vantyx-border bg-vantyx-surface p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="flex items-center gap-2 text-xs font-medium text-vantyx-textSecondary">
                  <Database size={14} className="text-vantyx-accent" /> PostgreSQL Connectivity
                </span>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border ${readiness?.components.database.status === 'healthy'
                    ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10'
                    : 'border-vantyx-accent/30 text-vantyx-accent bg-vantyx-accent/10'
                    }`}
                >
                  {readiness?.components.database.status === 'healthy' ? 'CONNECTED' : 'STANDBY / RESILIENT'}
                </span>
              </div>

              <div className="space-y-1.5 font-mono text-xs text-vantyx-textSecondary">
                <div className="flex justify-between">
                  <span className="text-vantyx-textMuted">Driver:</span>
                  <span>SQLAlchemy 2.0 (asyncpg)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-vantyx-textMuted">Migrations:</span>
                  <span>Alembic 1.13+ (Head Synced)</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-vantyx-textMuted">Readiness State:</span>
                  <span className="text-[11px]">
                    {readiness?.components.database.message || 'Probing connection...'}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-vantyx-borderSubtle text-[11px] text-vantyx-textMuted flex items-center justify-between">
              <span>Strict Postgres in Production</span>
              <span>Pool Size: 10</span>
            </div>
          </div>

          {/* Card 3: Redis & Celery Background Queue */}
          <div className="rounded border border-vantyx-border bg-vantyx-surface p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="flex items-center gap-2 text-xs font-medium text-vantyx-textSecondary">
                  <Cpu size={14} className="text-vantyx-accent" /> Worker & Queue Broker
                </span>
                <div className="flex items-center gap-1.5">
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                      redisHealth?.status === 'healthy'
                        ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10'
                        : 'border-rose-500/30 text-rose-400 bg-rose-500/10'
                    }`}
                  >
                    {redisHealth?.status === 'healthy' ? 'REDIS ONLINE' : 'REDIS OFFLINE'}
                  </span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                      readiness?.execution_mode === 'LOCAL IN-PROCESS' || workerHealth?.status === 'eager_development'
                        ? 'border-amber-500/30 text-amber-400 bg-amber-500/10'
                        : workerHealth?.status === 'healthy'
                        ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10'
                        : 'border-rose-500/30 text-rose-400 bg-rose-500/10'
                    }`}
                  >
                    {readiness?.execution_mode === 'LOCAL IN-PROCESS' || workerHealth?.status === 'eager_development'
                      ? 'LOCAL IN-PROCESS'
                      : workerHealth?.status === 'healthy'
                      ? 'DISTRIBUTED'
                      : 'STANDBY'}
                  </span>
                </div>
              </div>

              <div className="space-y-1.5 font-mono text-xs text-vantyx-textSecondary">
                <div className="flex justify-between">
                  <span className="text-vantyx-textMuted">Execution Mode:</span>
                  <span className="text-vantyx-accent font-semibold">{readiness?.execution_mode || 'LOCAL IN-PROCESS'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-vantyx-textMuted">Redis Broker:</span>
                  <span className="truncate max-w-[200px]">{redisHealth?.message || 'Probing...'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-vantyx-textMuted">Worker State:</span>
                  <span className="text-[11px] truncate max-w-[200px]">{workerHealth?.message || 'Inspecting workers...'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-vantyx-textMuted">Beat Schedule:</span>
                  <span>{readiness?.execution_mode === 'LOCAL IN-PROCESS' ? 'In-Process (API / Manual Trigger)' : '06:00 IST (Celery Beat Daemon)'}</span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-vantyx-borderSubtle text-[11px] text-vantyx-textMuted flex items-center justify-between">
              <span>{readiness?.execution_mode === 'LOCAL IN-PROCESS' ? 'In-Process Task Dispatch' : 'Celery 5.4+ (Distributed Pool)'}</span>
              <span>Concurrency: {readiness?.execution_mode === 'LOCAL IN-PROCESS' ? '1 (In-Process)' : '2'}</span>
            </div>
          </div>

          {/* Card 4: External Services & Storage Health */}
          <div className="rounded border border-vantyx-border bg-vantyx-surface p-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="flex items-center gap-2 text-xs font-medium text-vantyx-textSecondary">
                  <Cloud size={14} className="text-vantyx-accent" /> External Integration Boundaries
                </span>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border ${readiness?.status === 'ready'
                    ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10'
                    : 'border-amber-500/30 text-amber-400 bg-amber-500/10'
                    }`}
                >
                  {readiness?.status === 'ready' ? 'READY' : 'DEVELOPMENT MODE'}
                </span>
              </div>

              <div className="space-y-1.5 font-mono text-xs text-vantyx-textSecondary">
                <div className="flex justify-between">
                  <span className="text-vantyx-textMuted">OAuth Status:</span>
                  <span className="truncate max-w-[200px]">{oauthHealth?.message || 'Evaluating...'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-vantyx-textMuted">AI Provider:</span>
                  <span className="truncate max-w-[200px]">{aiHealth?.message || 'Evaluating...'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-vantyx-textMuted flex items-center gap-1">
                    <HardDrive size={10} /> Storage:
                  </span>
                  <span className="text-[11px]">{storageHealth?.message || 'Checking disk...'}</span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-vantyx-borderSubtle text-[11px] text-vantyx-textMuted flex items-center justify-between">
              <span>Target: Astro Rebel</span>
              <span>Timezone: Asia/Kolkata</span>
            </div>
          </div>
        </div>
      </section>

      {/* Modular Pipeline Architecture Matrix */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-mono font-semibold tracking-wider text-vantyx-textMuted uppercase">
            Domain Module Boundaries
          </h3>
          <span className="text-[11px] text-vantyx-textMuted font-mono">Milestone Execution Matrix</span>
        </div>

        <div className="divide-y divide-vantyx-border rounded border border-vantyx-border bg-vantyx-surface">
          {[
            {
              module: 'Discovery',
              domain: 'GTA 6 Gameplay ingestion & creator permission rights validation',
              milestone: 'Milestone 02',
              status: 'VERIFIED',
            },
            {
              module: 'Intelligence',
              domain: 'Multimodal scene understanding, transcript indexing & audio signal scoring',
              milestone: 'Milestone 03',
              status: 'VERIFIED',
            },
            {
              module: 'Selection',
              domain: 'Hook detection, retention scoring, and clip boundary ranking',
              milestone: 'Milestone 04',
              status: 'VERIFIED',
            },
            {
              module: 'Production',
              domain: 'Vertical 9:16 synthesis, dynamic aspect ratios (16:9, 21:9, 4:3), audio normalization',
              milestone: 'Milestone 05',
              status: 'VERIFIED',
            },
            {
              module: 'Distribution',
              domain: 'YouTube channel authorization, token encryption, release schedule (09:00, 13:00, 17:00, 21:00)',
              milestone: 'Milestone 06',
              status: 'VERIFIED',
            },
            {
              module: 'Orchestration',
              domain: 'Persistent state machines, Redis/Celery queue coordination & Celery Beat scheduler',
              milestone: 'Milestone 07',
              status: 'VERIFIED',
            },
            {
              module: 'Analytics',
              domain: 'Audience retention tracking, performance metrics & bounded closed-loop feedback engine',
              milestone: 'Milestone 08',
              status: 'VERIFIED',
            },
            {
              module: 'Hardening & Deployment',
              domain: 'PostgreSQL validation, token encryption, multi-aspect FFmpeg, multi-service Docker containerization',
              milestone: 'Milestone 09',
              status: 'COMPLETE',
            },
          ].map((item, idx) => (
            <div key={idx} className="flex items-center justify-between p-3.5 text-xs">
              <div className="flex items-center gap-3">
                <Layers size={14} className="text-vantyx-textMuted" />
                <div>
                  <span className="font-medium text-vantyx-textPrimary font-mono">{item.module}</span>
                  <p className="text-[11px] text-vantyx-textMuted mt-0.5">{item.domain}</p>
                </div>
              </div>
              <div className="text-right shrink-0 ml-4 font-mono flex items-center gap-2">
                <span className="text-[10px] text-vantyx-accent border border-vantyx-border px-2 py-0.5 rounded">
                  {item.milestone}
                </span>
                <span className="text-[9px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-1.5 py-0.5 rounded">
                  {item.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Security & Safeguards Summary */}
      <section className="rounded border border-vantyx-border bg-vantyx-surface/30 p-4">
        <div className="flex items-center gap-2 mb-2 text-xs font-mono text-vantyx-textSecondary">
          <ShieldCheck size={14} className="text-vantyx-accent" /> Security Safeguards & Operational Integrity
        </div>
        <p className="text-xs text-vantyx-textMuted leading-relaxed">
          Zero external credentials committed. OAuth tokens are encrypted at rest using AES/Fernet encryption.
          Log redaction filters all authorization headers, cookies, and tokens. Path traversal protection enforces
          strict boundary containment for all media streaming endpoints. Production environment strictly rejects SQLite.
        </p>
      </section>
    </div>
  );
};
