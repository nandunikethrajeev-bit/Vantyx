import React from 'react';
import { Server, Database, ShieldCheck, Terminal, Layers } from 'lucide-react';
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
  return (
    <div className="mx-auto max-w-5xl space-y-8">
      {/* Brand Hero & Architectural Statement */}
      <section className="border-b border-vantyx-border pb-8">
        <div className="flex items-center gap-2 text-xs font-mono tracking-widest text-vantyx-accent uppercase mb-2">
          <span>Milestone 01</span>
          <span>•</span>
          <span>Engineering Foundation</span>
        </div>
        <h2 className="text-2xl font-light tracking-tight text-vantyx-textPrimary">
          VANTYX System Architecture
        </h2>
        <p className="mt-1 text-sm text-vantyx-textSecondary max-w-2xl leading-relaxed">
          The intelligence behind every moment. Modular monolith foundation initialized with
          isolated domain boundaries, strict configuration validation, and structured observability.
        </p>

        {/* Notice: Engines Inactive */}
        <div className="mt-5 flex items-start gap-3 rounded border border-vantyx-border bg-vantyx-surface/40 p-3.5 text-xs">
          <Terminal size={16} className="text-vantyx-accent mt-0.5 shrink-0" />
          <div className="space-y-0.5">
            <span className="font-mono font-medium text-vantyx-textPrimary">
              Operational Status: Engine Automation Inactive
            </span>
            <p className="text-vantyx-textMuted leading-relaxed">
              This milestone establishes the engineering foundation. Content discovery, AI multimodal
              intelligence, clip extraction, video rendering, and channel publishing engines are scheduled
              for progressive activation in Milestones 02 through 07.
            </p>
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
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                    connectionState !== 'offline'
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
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                    readiness?.components.database.status === 'healthy'
                      ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10'
                      : 'border-vantyx-accent/30 text-vantyx-accent bg-vantyx-accent/10'
                  }`}
                >
                  {readiness?.components.database.status === 'healthy' ? 'CONNECTED' : 'STANDBY / DEGRADED'}
                </span>
              </div>

              <div className="space-y-1.5 font-mono text-xs text-vantyx-textSecondary">
                <div className="flex justify-between">
                  <span className="text-vantyx-textMuted">Driver:</span>
                  <span>SQLAlchemy 2.0 (asyncpg)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-vantyx-textMuted">Migrations:</span>
                  <span>Alembic 1.13+</span>
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
              <span>Docker Compose config: <code className="text-vantyx-textSecondary">infrastructure/</code></span>
              <span>Port: 5432</span>
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
          <span className="text-[11px] text-vantyx-textMuted">Milestone Sequence</span>
        </div>

        <div className="divide-y divide-vantyx-border rounded border border-vantyx-border bg-vantyx-surface">
          {[
            {
              module: 'Discovery',
              domain: 'GTA 6 Gameplay ingestion & creator permission rights validation',
              milestone: 'Milestone 02',
            },
            {
              module: 'Intelligence',
              domain: 'Multimodal scene understanding, transcript indexing & audio signal scoring',
              milestone: 'Milestone 03',
            },
            {
              module: 'Selection',
              domain: 'Hook detection, retention scoring, and clip boundary ranking',
              milestone: 'Milestone 04',
            },
            {
              module: 'Production',
              domain: 'Vertical 9:16 synthesis, subtitle rendering, motion styling & encoding',
              milestone: 'Milestone 05',
            },
            {
              module: 'Distribution',
              domain: 'YouTube channel authorization, release queue orchestration & publishing',
              milestone: 'Milestone 06',
            },
            {
              module: 'Analytics',
              domain: 'Audience retention tracking and continuous feedback loop optimization',
              milestone: 'Milestone 07',
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
              <div className="text-right shrink-0 ml-4 font-mono">
                <span className="text-[10px] text-vantyx-accent border border-vantyx-border px-2 py-0.5 rounded">
                  {item.milestone}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Security & Safeguards Summary */}
      <section className="rounded border border-vantyx-border bg-vantyx-surface/30 p-4">
        <div className="flex items-center gap-2 mb-2 text-xs font-mono text-vantyx-textSecondary">
          <ShieldCheck size={14} className="text-vantyx-accent" /> Security Safeguards
        </div>
        <p className="text-xs text-vantyx-textMuted leading-relaxed">
          Zero external credentials committed. Log redaction filters all authorization headers, cookies,
          and tokens. Database connection parameters are validated strictly via Pydantic Settings.
        </p>
      </section>
    </div>
  );
};
