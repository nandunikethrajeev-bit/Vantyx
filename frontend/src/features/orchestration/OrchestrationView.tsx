import React, { useEffect, useState } from 'react';
import {
  Activity,
  Play,
  Pause,
  RotateCcw,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  HardDrive,
  Cpu,
  Layers,
  ShieldCheck,
  Terminal,
  XCircle,
  Radio,
  Share2,
  Film,
  Sparkles,
  Sliders,
} from 'lucide-react';
import {
  cancelWorkflow,
  fetchAutomationStatus,
  fetchCurrentWorkflow,
  fetchDailyPublishingPlan,
  fetchWorkflowHistory,
  pauseWorkflow,
  resumeWorkflow,
  startWorkflow,
  triggerWorkflowRecovery,
  updateAutomationConfig,
} from '@/lib/api';
import {
  AutomationStatus,
  DailyPublishingPlan,
  WorkflowRun,
} from '@/types';

const PIPELINE_STAGES = [
  { key: 'discovery', label: '1. Discovery', icon: Radio },
  { key: 'rights_validation', label: '2. Rights Gate', icon: ShieldCheck },
  { key: 'intelligence', label: '3. Intelligence', icon: Cpu },
  { key: 'selection', label: '4. Selection', icon: Sparkles },
  { key: 'production', label: '5. Production', icon: Film },
  { key: 'distribution', label: '6. Distribution', icon: Share2 },
  { key: 'monitoring', label: '7. Monitoring', icon: Activity },
];

export const OrchestrationView: React.FC = () => {
  const [statusData, setStatusData] = useState<AutomationStatus | null>(null);
  const [currentWorkflow, setCurrentWorkflow] = useState<WorkflowRun | null>(null);
  const [history, setHistory] = useState<WorkflowRun[]>([]);
  const [dailyPlan, setDailyPlan] = useState<DailyPublishingPlan | null>(null);
  const [activeTab, setActiveTab] = useState<'current' | 'history' | 'logs'>('current');
  const [loading, setLoading] = useState<boolean>(true);
  const [actionInFlight, setActionInFlight] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setErrorMessage(null);
      const [statusRes, currentRes, historyRes, planRes] = await Promise.all([
        fetchAutomationStatus(),
        fetchCurrentWorkflow(),
        fetchWorkflowHistory(15),
        fetchDailyPublishingPlan(),
      ]);
      setStatusData(statusRes);
      setCurrentWorkflow(currentRes);
      setHistory(historyRes);
      setDailyPlan(planRes);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load orchestration data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Non-aggressive polling every 12 seconds
    const interval = setInterval(loadData, 12000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleAutomation = async () => {
    if (!statusData) return;
    try {
      setActionInFlight(true);
      const newStatus = !statusData.automation_enabled;
      const res = await updateAutomationConfig({ automation_enabled: newStatus });
      setStatusData(res);
      setSuccessMessage(
        newStatus
          ? 'Autonomous scheduler ENABLED. Daily workflows will execute at 06:00 IST.'
          : 'Autonomous scheduler PAUSED. Workflows will only run on manual trigger.'
      );
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to toggle automation');
    } finally {
      setActionInFlight(false);
    }
  };

  const handleStartWorkflow = async () => {
    try {
      setActionInFlight(true);
      setErrorMessage(null);
      const run = await startWorkflow({ force: true, execute_sync: true });
      setCurrentWorkflow(run);
      setSuccessMessage(`Workflow #${run.id} (${run.run_id}) executed successfully.`);
      await loadData();
    } catch (err: any) {
      setErrorMessage(err.message || 'Workflow execution failed');
    } finally {
      setActionInFlight(false);
    }
  };

  const handlePauseWorkflow = async () => {
    if (!currentWorkflow) return;
    try {
      setActionInFlight(true);
      const updated = await pauseWorkflow(currentWorkflow.run_id);
      setCurrentWorkflow(updated);
      setSuccessMessage(`Workflow #${updated.id} paused.`);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to pause workflow');
    } finally {
      setActionInFlight(false);
    }
  };

  const handleResumeWorkflow = async () => {
    if (!currentWorkflow) return;
    try {
      setActionInFlight(true);
      const updated = await resumeWorkflow(currentWorkflow.run_id);
      setCurrentWorkflow(updated);
      setSuccessMessage(`Workflow #${updated.id} resumed.`);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to resume workflow');
    } finally {
      setActionInFlight(false);
    }
  };

  const handleCancelWorkflow = async () => {
    if (!currentWorkflow) return;
    if (!confirm('Are you sure you want to cancel the active workflow?')) return;
    try {
      setActionInFlight(true);
      const updated = await cancelWorkflow(currentWorkflow.run_id);
      setCurrentWorkflow(updated);
      setSuccessMessage(`Workflow #${updated.id} cancelled.`);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to cancel workflow');
    } finally {
      setActionInFlight(false);
    }
  };

  const handleRecoverStalled = async () => {
    try {
      setActionInFlight(true);
      const res = await triggerWorkflowRecovery();
      setSuccessMessage(res.message);
      await loadData();
    } catch (err: any) {
      setErrorMessage(err.message || 'Recovery failed');
    } finally {
      setActionInFlight(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-light tracking-wide text-vantyx-textPrimary">
              Autonomous Orchestration Engine
            </h1>
            <span className="rounded border border-vantyx-accent/40 bg-vantyx-accent/10 px-2 py-0.5 text-xs font-mono font-medium text-vantyx-accent">
              M07 ACTIVE
            </span>
          </div>
          <p className="mt-1 text-sm text-vantyx-textSecondary">
            Persistent 7-stage publishing pipeline • Redis/Celery queue • 4 daily Shorts in Asia/Kolkata.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRecoverStalled}
            disabled={actionInFlight}
            className="flex items-center gap-1.5 rounded border border-vantyx-border bg-vantyx-surface/60 px-3 py-1.5 text-xs text-vantyx-textSecondary hover:border-vantyx-accent/50 hover:text-white transition disabled:opacity-50"
            title="Scan and recover workflows interrupted by server restarts"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Recover Stalled
          </button>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 rounded border border-vantyx-border bg-vantyx-surface/80 px-3 py-1.5 text-xs text-vantyx-textSecondary hover:border-vantyx-accent/50 hover:text-white transition disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Notifications */}
      {errorMessage && (
        <div className="flex items-center justify-between rounded border border-red-500/30 bg-red-950/20 p-4 text-sm text-red-400">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 shrink-0 text-red-400" />
            <span>{errorMessage}</span>
          </div>
          <button onClick={() => setErrorMessage(null)} className="text-red-400 hover:text-white">
            &times;
          </button>
        </div>
      )}

      {successMessage && (
        <div className="flex items-center justify-between rounded border border-emerald-500/30 bg-emerald-950/20 p-4 text-sm text-emerald-400">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-400 hover:text-white">
            &times;
          </button>
        </div>
      )}

      {/* Master Control & Health Card */}
      <div className="rounded-lg border border-vantyx-border bg-vantyx-surface/40 p-6 backdrop-blur-sm">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <div
              className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border shadow-inner ${statusData?.automation_enabled
                ? 'border-emerald-500/30 bg-emerald-950/30 text-emerald-400'
                : 'border-slate-700 bg-slate-800/40 text-slate-400'
                }`}
            >
              <Activity className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-lg font-medium text-white">
                  Automation Scheduler:{' '}
                  <span
                    className={
                      statusData?.automation_enabled ? 'text-emerald-400 font-semibold' : 'text-slate-400'
                    }
                  >
                    {statusData?.automation_enabled ? 'ACTIVE' : 'DISABLED'}
                  </span>
                </h2>
                <span className="rounded bg-black/40 px-2 py-0.5 text-xs font-mono text-vantyx-textSecondary border border-vantyx-border">
                  Daily Run: {statusData?.daily_run_time_ist || '06:00'} IST
                </span>
              </div>
              <p className="mt-1 text-xs text-vantyx-textSecondary leading-relaxed">
                {statusData?.automation_enabled
                  ? 'Autonomous scheduler active. Discovers gameplay, generates 9:16 vertical shorts, and fills 4 daily slots in Asia/Kolkata.'
                  : 'Safety mode: Automation is disabled. Workflows must be explicitly initiated by the operator.'}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleToggleAutomation}
              disabled={actionInFlight}
              className={`rounded px-4 py-2 text-xs font-medium transition ${statusData?.automation_enabled
                ? 'border border-amber-500/40 bg-amber-950/20 text-amber-300 hover:bg-amber-900/30'
                : 'border border-emerald-500/40 bg-emerald-950/20 text-emerald-300 hover:bg-emerald-900/30'
                }`}
            >
              {statusData?.automation_enabled ? 'Disable Automation' : 'Enable Automation'}
            </button>

            <button
              onClick={handleStartWorkflow}
              disabled={actionInFlight || currentWorkflow?.status === 'running'}
              className="flex items-center gap-2 rounded bg-vantyx-accent px-5 py-2 text-xs font-medium text-vantyx-bg hover:bg-vantyx-accent/90 transition shadow-lg disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              Run Pipeline Now
            </button>
          </div>
        </div>

        {/* System Resource Telemetry Grid */}
        <div className="mt-6 grid grid-cols-2 gap-4 border-t border-vantyx-border/60 pt-4 sm:grid-cols-4">
          <div className="rounded bg-black/30 p-3 border border-vantyx-border/40">
            <div className="flex items-center gap-2 text-xs text-vantyx-textSecondary">
              <Cpu className="h-3.5 w-3.5 text-vantyx-accent" />
              Queue Engine
            </div>
            <p className="mt-1 text-sm font-mono text-white capitalize">
              {statusData?.celery_mode || 'Eager'} (Celery)
            </p>
            <span className="text-[10px] text-slate-500">
              Redis: {statusData?.redis_connected ? 'Connected' : 'In-Process Fallback'}
            </span>
          </div>

          <div className="rounded bg-black/30 p-3 border border-vantyx-border/40">
            <div className="flex items-center gap-2 text-xs text-vantyx-textSecondary">
              <Sliders className="h-3.5 w-3.5 text-vantyx-accent" />
              Concurrency Limit
            </div>
            <p className="mt-1 text-sm font-mono text-white">
              {statusData?.max_concurrent_renders || 2} Active Renders
            </p>
            <span className="text-[10px] text-slate-500">CPU-aware throttle</span>
          </div>

          <div className="rounded bg-black/30 p-3 border border-vantyx-border/40">
            <div className="flex items-center gap-2 text-xs text-vantyx-textSecondary">
              <HardDrive className="h-3.5 w-3.5 text-vantyx-accent" />
              Storage Free
            </div>
            <p className="mt-1 text-sm font-mono text-white">
              {statusData?.disk_free_gb || 0} GB
            </p>
            <span className="text-[10px] text-slate-500">Data & Media Drive</span>
          </div>

          <div className="rounded bg-black/30 p-3 border border-vantyx-border/40">
            <div className="flex items-center gap-2 text-xs text-vantyx-textSecondary">
              <Clock className="h-3.5 w-3.5 text-vantyx-accent" />
              Today's Plan
            </div>
            <p className="mt-1 text-sm font-mono text-white capitalize">
              {dailyPlan?.status || 'Planning'} ({dailyPlan?.filled_count || 0}/4 Slots)
            </p>
            <span className="text-[10px] text-slate-500">Asia/Kolkata Cadence</span>
          </div>
        </div>
      </div>

      {/* Daily 4-Slot Publishing Plan Matrix */}
      {dailyPlan && (
        <div className="rounded-lg border border-vantyx-border bg-vantyx-surface/30 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-medium text-white flex items-center gap-2">
                <Clock className="h-4 w-4 text-vantyx-accent" />
                Daily Publishing Plan: {dailyPlan.plan_date} (Asia/Kolkata)
              </h3>
              <p className="text-xs text-vantyx-textSecondary">
                Target: 4 Shorts/day • 09:00, 13:00, 17:00, 21:00 IST
              </p>
            </div>
            <span
              className={`rounded px-2.5 py-1 text-xs font-mono uppercase font-medium border ${dailyPlan.status === 'fulfilled'
                ? 'border-emerald-500/40 bg-emerald-950/30 text-emerald-400'
                : dailyPlan.status === 'partial'
                  ? 'border-amber-500/40 bg-amber-950/30 text-amber-400'
                  : 'border-slate-700 bg-slate-800 text-slate-400'
                }`}
            >
              {dailyPlan.status} ({dailyPlan.filled_count}/4)
            </span>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {['09:00', '13:00', '17:00', '21:00'].map((slotTime) => {
              const slot = dailyPlan.slot_assignments?.[slotTime] || {};
              const isFilled = slot.status === 'scheduled' || slot.status === 'published';

              return (
                <div
                  key={slotTime}
                  className={`rounded border p-4 transition ${isFilled
                    ? 'border-vantyx-accent/40 bg-vantyx-accent/5'
                    : 'border-vantyx-border/60 bg-black/20'
                    }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm font-semibold text-white">
                      {slotTime} IST
                    </span>
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-mono uppercase border ${slot.status === 'published'
                        ? 'border-emerald-500/30 bg-emerald-950/40 text-emerald-400'
                        : slot.status === 'scheduled'
                          ? 'border-vantyx-accent/40 bg-vantyx-accent/20 text-vantyx-accent'
                          : 'border-slate-700 bg-slate-800/40 text-slate-400'
                        }`}
                    >
                      {slot.status || 'unfilled'}
                    </span>
                  </div>

                  <div className="mt-3 text-xs">
                    {isFilled ? (
                      <div>
                        <p className="font-medium text-white truncate">
                          Candidate #{slot.candidate_id}
                        </p>
                        <p className="text-[11px] font-mono text-vantyx-textSecondary mt-1">
                          {slot.youtube_video_id ? `Video: ${slot.youtube_video_id}` : 'Queued'}
                        </p>
                      </div>
                    ) : (
                      <p className="text-slate-500 italic">Slot open</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Active Workflow Progression Tracker */}
      {currentWorkflow && (
        <div className="rounded-lg border border-vantyx-border bg-vantyx-surface/30 p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-vantyx-border pb-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-medium text-white">
                  Active Workflow: <span className="font-mono text-vantyx-accent">{currentWorkflow.run_id}</span>
                </h3>
                <span
                  className={`rounded px-2 py-0.5 font-mono text-[10px] uppercase border ${currentWorkflow.status === 'completed'
                    ? 'border-emerald-500/40 bg-emerald-950/30 text-emerald-400'
                    : currentWorkflow.status === 'running'
                      ? 'border-vantyx-accent/40 bg-vantyx-accent/20 text-vantyx-accent animate-pulse'
                      : currentWorkflow.status === 'paused'
                        ? 'border-amber-500/40 bg-amber-950/30 text-amber-400'
                        : 'border-red-500/40 bg-red-950/30 text-red-400'
                    }`}
                >
                  {currentWorkflow.status}
                </span>
              </div>
              <p className="text-xs text-vantyx-textSecondary mt-1">
                Started: {new Date(currentWorkflow.started_at).toLocaleString()} • Current Stage:{' '}
                <span className="font-mono text-white capitalize">{currentWorkflow.current_step}</span>
              </p>
            </div>

            <div className="flex items-center gap-2">
              {currentWorkflow.status === 'running' && (
                <button
                  onClick={handlePauseWorkflow}
                  disabled={actionInFlight}
                  className="flex items-center gap-1.5 rounded border border-amber-500/40 bg-amber-950/20 px-3 py-1.5 text-xs text-amber-300 hover:bg-amber-900/40 transition disabled:opacity-50"
                >
                  <Pause className="h-3 w-3" />
                  Pause
                </button>
              )}
              {currentWorkflow.status === 'paused' && (
                <button
                  onClick={handleResumeWorkflow}
                  disabled={actionInFlight}
                  className="flex items-center gap-1.5 rounded border border-emerald-500/40 bg-emerald-950/20 px-3 py-1.5 text-xs text-emerald-300 hover:bg-emerald-900/40 transition disabled:opacity-50"
                >
                  <Play className="h-3 w-3 fill-current" />
                  Resume
                </button>
              )}
              {['running', 'paused', 'pending', 'queued'].includes(currentWorkflow.status) && (
                <button
                  onClick={handleCancelWorkflow}
                  disabled={actionInFlight}
                  className="flex items-center gap-1.5 rounded border border-red-500/40 bg-red-950/20 px-3 py-1.5 text-xs text-red-300 hover:bg-red-900/40 transition disabled:opacity-50"
                >
                  <XCircle className="h-3 w-3" />
                  Cancel
                </button>
              )}
            </div>
          </div>

          {/* 7 Pipeline Stages Horizontal Bar */}
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
            {PIPELINE_STAGES.map((stage) => {
              const matchedStep = currentWorkflow.steps?.find((s) => s.step_name === stage.key);
              const isCompleted = matchedStep?.status === 'completed';
              const isRunning = matchedStep?.status === 'running';
              const isFailed = matchedStep?.status === 'failed';
              const Icon = stage.icon;

              return (
                <div
                  key={stage.key}
                  className={`rounded-lg border p-3 flex flex-col justify-between transition ${isCompleted
                    ? 'border-emerald-500/40 bg-emerald-950/20'
                    : isRunning
                      ? 'border-vantyx-accent bg-vantyx-accent/10 shadow-lg'
                      : isFailed
                        ? 'border-red-500/40 bg-red-950/20'
                        : 'border-vantyx-border/40 bg-black/20 opacity-70'
                    }`}
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <Icon
                        className={`h-4 w-4 ${isCompleted
                          ? 'text-emerald-400'
                          : isRunning
                            ? 'text-vantyx-accent animate-pulse'
                            : isFailed
                              ? 'text-red-400'
                              : 'text-slate-500'
                          }`}
                      />
                      {isCompleted && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />}
                      {isRunning && <RefreshCw className="h-3.5 w-3.5 text-vantyx-accent animate-spin" />}
                      {isFailed && <AlertCircle className="h-3.5 w-3.5 text-red-400" />}
                    </div>
                    <p className="mt-2 text-xs font-medium text-white">{stage.label}</p>
                  </div>
                  <span
                    className={`mt-3 text-[10px] font-mono uppercase ${isCompleted
                      ? 'text-emerald-400'
                      : isRunning
                        ? 'text-vantyx-accent font-semibold'
                        : isFailed
                          ? 'text-red-400'
                          : 'text-slate-500'
                      }`}
                  >
                    {matchedStep?.status || 'pending'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tabs: Execution History & Logs */}
      <div className="space-y-4">
        <div className="flex items-center gap-4 border-b border-vantyx-border">
          <button
            onClick={() => setActiveTab('current')}
            className={`flex items-center gap-2 border-b-2 pb-3 text-xs font-medium transition ${activeTab === 'current'
              ? 'border-vantyx-accent text-vantyx-accent'
              : 'border-transparent text-vantyx-textSecondary hover:text-white'
              }`}
          >
            <Activity className="h-4 w-4" />
            Workflow Telemetry
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-2 border-b-2 pb-3 text-xs font-medium transition ${activeTab === 'history'
              ? 'border-vantyx-accent text-vantyx-accent'
              : 'border-transparent text-vantyx-textSecondary hover:text-white'
              }`}
          >
            <Layers className="h-4 w-4" />
            Execution History ({history.length})
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`flex items-center gap-2 border-b-2 pb-3 text-xs font-medium transition ${activeTab === 'logs'
              ? 'border-vantyx-accent text-vantyx-accent'
              : 'border-transparent text-vantyx-textSecondary hover:text-white'
              }`}
          >
            <Terminal className="h-4 w-4" />
            Live Execution Logs
          </button>
        </div>

        {/* Tab 1: Current Workflow Telemetry */}
        {activeTab === 'current' && (
          <div className="rounded-lg border border-vantyx-border bg-vantyx-surface/30 p-6">
            <h4 className="text-sm font-medium text-white mb-4">Pipeline Execution Metadata</h4>
            {currentWorkflow?.execution_metadata ? (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6 text-xs">
                {Object.entries(currentWorkflow.execution_metadata).map(([key, value]) => (
                  <div key={key} className="rounded bg-black/40 p-3 border border-vantyx-border/40">
                    <p className="text-[11px] text-slate-400 capitalize">{key.replace(/_/g, ' ')}</p>
                    <p className="mt-1 font-mono text-base font-semibold text-white">{String(value)}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-vantyx-textSecondary italic">No active workflow telemetry.</p>
            )}
          </div>
        )}

        {/* Tab 2: Execution History Table */}
        {activeTab === 'history' && (
          <div className="rounded-lg border border-vantyx-border bg-vantyx-surface/30 p-6">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-vantyx-border text-vantyx-textSecondary font-mono">
                  <tr>
                    <th className="pb-3">Run ID</th>
                    <th className="pb-3">Target Date</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3">Final Step</th>
                    <th className="pb-3">Started</th>
                    <th className="pb-3">Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-vantyx-border/40 text-vantyx-textPrimary">
                  {history.map((run) => (
                    <tr key={run.id} className="hover:bg-vantyx-surface/40">
                      <td className="py-3 font-mono font-medium text-vantyx-accent">{run.run_id}</td>
                      <td className="py-3 font-mono">{run.target_date}</td>
                      <td className="py-3">
                        <span
                          className={`rounded px-2 py-0.5 font-mono text-[10px] uppercase border ${run.status === 'completed'
                            ? 'border-emerald-500/30 bg-emerald-950/40 text-emerald-400'
                            : run.status === 'running'
                              ? 'border-vantyx-accent/40 bg-vantyx-accent/20 text-vantyx-accent'
                              : 'border-red-500/30 bg-red-950/40 text-red-400'
                            }`}
                        >
                          {run.status}
                        </span>
                      </td>
                      <td className="py-3 font-mono capitalize">{run.current_step}</td>
                      <td className="py-3 text-slate-400">
                        {new Date(run.started_at).toLocaleTimeString()}
                      </td>
                      <td className="py-3 text-slate-400">
                        {run.completed_at
                          ? `${Math.round(
                            (new Date(run.completed_at).getTime() -
                              new Date(run.started_at).getTime()) /
                            1000
                          )}s`
                          : 'In flight'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: Structured Logs Feed */}
        {activeTab === 'logs' && (
          <div className="rounded-lg border border-vantyx-border bg-black/60 p-4 font-mono text-xs max-h-96 overflow-y-auto space-y-2">
            {currentWorkflow?.logs && currentWorkflow.logs.length > 0 ? (
              currentWorkflow.logs.map((log) => (
                <div key={log.id} className="flex items-start gap-2 text-[11px] leading-relaxed">
                  <span className="text-slate-500 shrink-0">
                    [{new Date(log.timestamp).toLocaleTimeString()}]
                  </span>
                  <span
                    className={`font-semibold shrink-0 ${log.level === 'ERROR'
                      ? 'text-red-400'
                      : log.level === 'WARNING'
                        ? 'text-amber-400'
                        : 'text-vantyx-accent'
                      }`}
                  >
                    [{log.level}]
                  </span>
                  <span className="text-slate-300">{log.message}</span>
                </div>
              ))
            ) : (
              <p className="text-slate-500 italic">No log entries available.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default OrchestrationView;

