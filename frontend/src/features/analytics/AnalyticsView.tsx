import React, { useEffect, useState } from 'react';
import {
  TrendingUp,
  Clock,
  Users,
  Eye,
  RefreshCw,
  AlertTriangle,
  Sparkles,
  Info,
  History,
  XCircle,
} from 'lucide-react';
import {
  fetchAnalyticsOverview,
  fetchPublishedVideosPerformance,
  fetchPerformanceInsights,
  triggerAnalyticsCollection,
  fetchAnalyticsJobs,
  fetchFeedbackStatus,
  updateFeedbackConfig,
} from '@/lib/api';
import {
  ChannelAnalyticsOverview,
  PublishedVideoPerformance,
  PerformanceIntelligence,
  AnalyticsCollectionJob,
  FeedbackStatus,
} from '@/types';

export const AnalyticsView: React.FC = () => {
  const [overview, setOverview] = useState<ChannelAnalyticsOverview | null>(null);
  const [videos, setVideos] = useState<PublishedVideoPerformance[]>([]);
  const [insights, setInsights] = useState<PerformanceIntelligence | null>(null);
  const [feedback, setFeedback] = useState<FeedbackStatus | null>(null);
  const [jobs, setJobs] = useState<AnalyticsCollectionJob[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [collecting, setCollecting] = useState<boolean>(false);
  const [updatingFeedback, setUpdatingFeedback] = useState<boolean>(false);
  const [showJobsModal, setShowJobsModal] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [ovData, vidData, insData, fbData] = await Promise.all([
        fetchAnalyticsOverview(),
        fetchPublishedVideosPerformance(),
        fetchPerformanceInsights(),
        fetchFeedbackStatus(),
      ]);
      setOverview(ovData);
      setVideos(vidData);
      setInsights(insData);
      setFeedback(fbData);
    } catch (err: any) {
      console.error('Failed to load analytics data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleTriggerCollection = async () => {
    try {
      setCollecting(true);
      setActionMessage('Collecting performance telemetry from YouTube Analytics...');
      const job = await triggerAnalyticsCollection();
      setActionMessage(`Collection completed: ${job.snapshots_created} snapshots saved.`);
      await loadData();
    } catch (err: any) {
      setActionMessage(`Collection failed: ${err.message || 'Network error'}`);
    } finally {
      setCollecting(false);
      setTimeout(() => setActionMessage(null), 4000);
    }
  };

  const handleToggleFeedback = async () => {
    if (!feedback) return;
    try {
      setUpdatingFeedback(true);
      const newEnabled = !feedback.feedback_enabled;
      await updateFeedbackConfig({ feedback_enabled: newEnabled });
      setFeedback({ ...feedback, feedback_enabled: newEnabled });
      setActionMessage(
        newEnabled
          ? 'Closed-loop feedback engine activated: calibrated multipliers applied to Selection.'
          : 'Closed-loop feedback disabled: baseline deterministic scoring active.'
      );
      await loadData();
    } catch (err: any) {
      setActionMessage(`Failed to update feedback engine: ${err.message}`);
    } finally {
      setUpdatingFeedback(false);
      setTimeout(() => setActionMessage(null), 4000);
    }
  };

  const handleOpenJobsModal = async () => {
    try {
      const jobList = await fetchAnalyticsJobs(15);
      setJobs(jobList);
      setShowJobsModal(true);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
    }
  };

  if (loading && !overview) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="h-6 w-6 animate-spin text-vantyx-accent" />
          <span className="text-xs uppercase tracking-widest text-vantyx-textMuted">
            Loading Audience Telemetry...
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Action Notification Banner */}
      {actionMessage && (
        <div className="flex items-center justify-between rounded border border-vantyx-accent/30 bg-vantyx-accent/10 px-4 py-3 text-xs text-vantyx-accent">
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4 shrink-0" />
            <span>{actionMessage}</span>
          </div>
          <button
            onClick={() => setActionMessage(null)}
            className="text-vantyx-textMuted hover:text-vantyx-textPrimary"
          >
            <XCircle className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Top Controls Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-semibold tracking-wide text-vantyx-textPrimary">
              Audience Performance & Feedback Engine
            </h2>
            <span className="rounded border border-vantyx-accent/30 bg-vantyx-accent/10 px-2 py-0.5 font-mono text-[10px] text-vantyx-accent">
              {overview?.channel_name || 'Astro Rebel'}
            </span>
            {overview?.is_delayed_reporting && (
              <span className="rounded border border-yellow-500/30 bg-yellow-500/10 px-2 py-0.5 font-mono text-[10px] text-yellow-400">
                24-48h YouTube Lag Active
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-vantyx-textSecondary">
            Snapshot Date: <span className="font-mono text-vantyx-textPrimary">{overview?.snapshot_date}</span> • Source:{' '}
            <span className="font-mono capitalize text-vantyx-textPrimary">{overview?.collection_source}</span>
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleOpenJobsModal}
            className="flex items-center gap-1.5 rounded border border-vantyx-border bg-vantyx-surface px-3 py-1.5 text-xs font-medium text-vantyx-textSecondary transition-colors hover:bg-vantyx-surfaceElevated hover:text-vantyx-textPrimary"
          >
            <History className="h-3.5 w-3.5" />
            <span>Audit Jobs</span>
          </button>
          <button
            onClick={handleTriggerCollection}
            disabled={collecting}
            className="flex items-center gap-1.5 rounded bg-vantyx-accent px-3.5 py-1.5 text-xs font-medium text-vantyx-bg transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${collecting ? 'animate-spin' : ''}`} />
            <span>{collecting ? 'Collecting...' : 'Collect Analytics'}</span>
          </button>
        </div>
      </div>

      {/* Channel KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-4">
          <div className="flex items-center justify-between text-vantyx-textMuted">
            <span className="text-[11px] uppercase tracking-wider">Total Views</span>
            <Eye className="h-4 w-4 text-vantyx-accent" />
          </div>
          <div className="mt-2 text-2xl font-semibold tracking-tight text-vantyx-textPrimary">
            {(overview?.total_views || 0).toLocaleString()}
          </div>
          <div className="mt-1 flex items-center gap-1 text-[11px] text-emerald-400">
            <TrendingUp className="h-3 w-3" />
            <span>Across {overview?.total_videos || 0} published Shorts</span>
          </div>
        </div>

        <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-4">
          <div className="flex items-center justify-between text-vantyx-textMuted">
            <span className="text-[11px] uppercase tracking-wider">Avg Retention (AVP)</span>
            <TrendingUp className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-semibold tracking-tight text-emerald-400">
            {(overview?.average_view_percentage || 0).toFixed(1)}%
          </div>
          <div className="mt-1 text-[11px] text-vantyx-textMuted">
            Mean AVD: <span className="font-mono text-vantyx-textPrimary">{overview?.average_view_duration_seconds}s</span>
          </div>
        </div>

        <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-4">
          <div className="flex items-center justify-between text-vantyx-textMuted">
            <span className="text-[11px] uppercase tracking-wider">Estimated Watch Time</span>
            <Clock className="h-4 w-4 text-blue-400" />
          </div>
          <div className="mt-2 text-2xl font-semibold tracking-tight text-vantyx-textPrimary">
            {((overview?.estimated_minutes_watched || 0) / 60.0).toFixed(1)} hrs
          </div>
          <div className="mt-1 text-[11px] text-vantyx-textMuted">
            <span className="font-mono">{(overview?.estimated_minutes_watched || 0).toLocaleString()}</span> total minutes
          </div>
        </div>

        <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-4">
          <div className="flex items-center justify-between text-vantyx-textMuted">
            <span className="text-[11px] uppercase tracking-wider">Subscribers Gained</span>
            <Users className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2 text-2xl font-semibold tracking-tight text-vantyx-textPrimary">
            +{(overview?.subscribers_gained || 0).toLocaleString()}
          </div>
          <div className="mt-1 text-[11px] text-vantyx-textMuted">
            Channel Total: <span className="font-mono text-vantyx-textPrimary">{(overview?.total_subscribers || 0).toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Closed-Loop Selection Feedback Engine Banner */}
      <div className="rounded border border-vantyx-border bg-vantyx-surfaceElevated/60 p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded border ${
              feedback?.feedback_enabled
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                : 'border-vantyx-border bg-vantyx-surface text-vantyx-textMuted'
            }`}>
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium text-vantyx-textPrimary">
                  Closed-Loop Selection Feedback Engine
                </h3>
                <span className={`rounded px-2 py-0.5 font-mono text-[10px] ${
                  feedback?.feedback_enabled
                    ? 'border border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                    : 'border border-vantyx-border bg-vantyx-surface text-vantyx-textMuted'
                }`}>
                  {feedback?.feedback_enabled ? 'ACTIVE' : 'DISABLED'}
                </span>
              </div>
              <p className="mt-1 text-xs text-vantyx-textSecondary">
                Feeds empirical retention benchmarks back into candidate clip scoring. Multipliers are bounded to{' '}
                <span className="font-mono text-vantyx-textPrimary">±{(feedback?.max_impact || 0.15) * 100}%</span> and require{' '}
                <span className="font-mono text-vantyx-textPrimary">N ≥ {feedback?.min_sample_size || 3}</span> samples.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleToggleFeedback}
              disabled={updatingFeedback}
              className={`rounded px-4 py-2 text-xs font-medium transition-all ${
                feedback?.feedback_enabled
                  ? 'border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20'
                  : 'bg-emerald-500 text-vantyx-bg hover:bg-emerald-400'
              }`}
            >
              {feedback?.feedback_enabled ? 'Disable Feedback Engine' : 'Enable Feedback Engine'}
            </button>
          </div>
        </div>

        {/* Multiplier Chips */}
        {feedback?.feedback_enabled && (
          <div className="mt-4 border-t border-vantyx-border/60 pt-3">
            <div className="text-[11px] font-medium uppercase tracking-wider text-vantyx-textMuted">
              Current Calibrated Category & Duration Multipliers:
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(feedback.category_multipliers).map(([cat, mult]) => (
                <div
                  key={cat}
                  className="flex items-center gap-1.5 rounded border border-vantyx-border bg-vantyx-surface px-2.5 py-1 text-xs"
                >
                  <span className="capitalize text-vantyx-textSecondary">{cat}:</span>
                  <span className={`font-mono font-medium ${
                    mult > 1.0 ? 'text-emerald-400' : mult < 1.0 ? 'text-amber-400' : 'text-vantyx-textMuted'
                  }`}>
                    {mult.toFixed(2)}x
                  </span>
                </div>
              ))}
              {Object.entries(feedback.duration_multipliers).map(([dur, mult]) => (
                <div
                  key={dur}
                  className="flex items-center gap-1.5 rounded border border-vantyx-border bg-vantyx-surface px-2.5 py-1 text-xs"
                >
                  <span className="text-vantyx-textSecondary">{dur}:</span>
                  <span className={`font-mono font-medium ${
                    mult > 1.0 ? 'text-emerald-400' : mult < 1.0 ? 'text-amber-400' : 'text-vantyx-textMuted'
                  }`}>
                    {mult.toFixed(2)}x
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Statistical Intelligence Insights Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold tracking-wide text-vantyx-textPrimary">
            Statistical Performance Intelligence
          </h3>
          <span className="text-xs text-vantyx-textMuted">
            Samples Analyzed: <span className="font-mono text-vantyx-textPrimary">{insights?.total_samples_analyzed || 0}</span> • Overall Confidence:{' '}
            <span className={`font-mono uppercase ${
              insights?.overall_confidence === 'high'
                ? 'text-emerald-400'
                : insights?.overall_confidence === 'medium'
                ? 'text-yellow-400'
                : 'text-zinc-500'
            }`}>
              {insights?.overall_confidence || 'low'}
            </span>
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {/* Duration Bucket Insights */}
          <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-4">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-2.5">
              <span className="text-xs font-medium text-vantyx-textPrimary">Optimal Duration Breakdown</span>
              <span className="text-[10px] text-vantyx-textMuted">15-60s Shorts Pacing</span>
            </div>
            <div className="mt-3 space-y-2.5">
              {insights?.duration_insights.map((b) => (
                <div key={b.key} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-16 font-mono text-vantyx-textSecondary">{b.key}</span>
                    <span className="rounded border border-vantyx-border px-1.5 py-0.2 font-mono text-[9px] text-vantyx-textMuted">
                      N={b.sample_size}
                    </span>
                    <span className={`text-[10px] uppercase font-mono ${
                      b.confidence_level === 'high' ? 'text-emerald-400' : b.confidence_level === 'medium' ? 'text-yellow-400' : 'text-zinc-500'
                    }`}>
                      {b.confidence_level}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-vantyx-textPrimary">{b.avg_retention_pct}% AVP</span>
                    <span className="w-14 text-right font-mono text-vantyx-textMuted">{b.avg_views.toFixed(0)} views</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Content Category Insights */}
          <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-4">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-2.5">
              <span className="text-xs font-medium text-vantyx-textPrimary">GTA 6 Content Category Affinity</span>
              <span className="text-[10px] text-vantyx-textMuted">Relative to Baseline</span>
            </div>
            <div className="mt-3 space-y-2.5">
              {insights?.category_insights.map((b) => (
                <div key={b.key} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-16 capitalize font-mono text-vantyx-textSecondary">{b.key}</span>
                    <span className="rounded border border-vantyx-border px-1.5 py-0.2 font-mono text-[9px] text-vantyx-textMuted">
                      N={b.sample_size}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-vantyx-textPrimary">{b.avg_retention_pct}% AVP</span>
                    <span className={`w-14 text-right font-mono font-medium ${
                      b.relative_multiplier > 1.0 ? 'text-emerald-400' : b.relative_multiplier < 1.0 ? 'text-amber-400' : 'text-vantyx-textMuted'
                    }`}>
                      {b.relative_multiplier.toFixed(2)}x
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Publishing Slot Performance */}
          <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-4">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-2.5">
              <span className="text-xs font-medium text-vantyx-textPrimary">Release Cadence (Asia/Kolkata IST)</span>
              <span className="text-[10px] text-vantyx-textMuted">4 Slots Daily Target</span>
            </div>
            <div className="mt-3 space-y-2.5">
              {insights?.slot_insights.map((b) => (
                <div key={b.key} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-16 font-mono text-vantyx-textSecondary">{b.key}</span>
                    <span className="rounded border border-vantyx-border px-1.5 py-0.2 font-mono text-[9px] text-vantyx-textMuted">
                      N={b.sample_size}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-vantyx-textPrimary">{b.avg_views.toFixed(0)} views</span>
                    <span className="w-14 text-right font-mono text-vantyx-textMuted">{b.avg_retention_pct}% AVP</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Hook Efficacy */}
          <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-4">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-2.5">
              <span className="text-xs font-medium text-vantyx-textPrimary">Opening Hook Impact (0-3s)</span>
              <span className="text-[10px] text-vantyx-textMuted">Dropoff Resistance</span>
            </div>
            <div className="mt-3 space-y-2.5">
              {insights?.hook_insights.map((b) => (
                <div key={b.key} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-vantyx-textSecondary">{b.label}</span>
                    <span className="rounded border border-vantyx-border px-1.5 py-0.2 font-mono text-[9px] text-vantyx-textMuted">
                      N={b.sample_size}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-emerald-400">{b.avg_retention_pct}% AVP</span>
                    <span className="w-14 text-right font-mono text-vantyx-textPrimary">{b.avg_views.toFixed(0)} views</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Correlation vs Causation Notice Banner */}
        <div className="flex items-start gap-3 rounded border border-amber-500/20 bg-amber-500/5 p-4 text-xs text-amber-300">
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
          <div className="leading-relaxed">
            <span className="font-semibold text-amber-200">Correlation vs Causation Guardrail:</span>{' '}
            {insights?.correlation_vs_causation_notice}
          </div>
        </div>
      </div>

      {/* Published Shorts Performance Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold tracking-wide text-vantyx-textPrimary">
            Published Shorts Telemetry & Profiles
          </h3>
          <span className="text-xs text-vantyx-textMuted">
            Total Videos: <span className="font-mono text-vantyx-textPrimary">{videos.length}</span>
          </span>
        </div>

        <div className="overflow-x-auto rounded border border-vantyx-border bg-vantyx-surface/40">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-vantyx-border bg-vantyx-surface/80 text-[11px] uppercase tracking-wider text-vantyx-textMuted">
              <tr>
                <th className="px-4 py-3">Short Title</th>
                <th className="px-4 py-3">Slot (IST)</th>
                <th className="px-4 py-3">Age</th>
                <th className="px-4 py-3">Views</th>
                <th className="px-4 py-3">Retention %</th>
                <th className="px-4 py-3">RRI Index</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-vantyx-border/60">
              {videos.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-vantyx-textMuted">
                    No published Shorts telemetry available yet. Run a collection sweep or schedule publications.
                  </td>
                </tr>
              ) : (
                videos.map((v) => (
                  <tr key={v.schedule_id} className="transition-colors hover:bg-vantyx-surfaceElevated/40">
                    <td className="px-4 py-3 font-medium text-vantyx-textPrimary">
                      <div className="max-w-xs truncate" title={v.title}>
                        {v.title}
                      </div>
                      <div className="font-mono text-[10px] text-vantyx-textMuted">
                        YT ID: {v.youtube_video_id || 'pending'}
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-vantyx-textSecondary">
                      {v.slot_name}
                    </td>
                    <td className="px-4 py-3 font-mono text-vantyx-textMuted">
                      {v.age_days}d ago
                    </td>
                    <td className="px-4 py-3 font-mono text-vantyx-textPrimary">
                      {v.views.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 font-mono text-emerald-400">
                      {v.average_view_percentage.toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 font-mono">
                      <span className="rounded bg-vantyx-accent/10 px-2 py-0.5 font-medium text-vantyx-accent">
                        {v.relative_retention_index.toFixed(0)}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono capitalize text-vantyx-textSecondary">
                      {v.category}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded px-2 py-0.5 font-mono text-[10px] capitalize ${
                        v.reporting_status === 'complete'
                          ? 'border border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                          : v.reporting_status === 'delayed'
                          ? 'border border-yellow-500/30 bg-yellow-500/10 text-yellow-400'
                          : 'border border-vantyx-border bg-vantyx-surface text-vantyx-textMuted'
                      }`}>
                        {v.reporting_status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Historical Audit Jobs Modal */}
      {showJobsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded border border-vantyx-border bg-vantyx-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-3">
              <h3 className="text-sm font-semibold text-vantyx-textPrimary">
                Analytics Collection Audit History
              </h3>
              <button
                onClick={() => setShowJobsModal(false)}
                className="text-vantyx-textMuted hover:text-vantyx-textPrimary"
              >
                <XCircle className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-4 max-h-96 space-y-2.5 overflow-y-auto">
              {jobs.length === 0 ? (
                <div className="py-6 text-center text-xs text-vantyx-textMuted">
                  No collection jobs recorded yet.
                </div>
              ) : (
                jobs.map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between rounded border border-vantyx-border bg-vantyx-surfaceElevated/50 p-3 text-xs"
                  >
                    <div>
                      <div className="font-mono text-vantyx-textPrimary">{job.job_id}</div>
                      <div className="mt-0.5 text-[11px] text-vantyx-textMuted">
                        Type: <span className="capitalize">{job.job_type}</span> • Started:{' '}
                        {new Date(job.started_at).toLocaleTimeString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right text-[11px]">
                        <span className="font-mono text-vantyx-textPrimary">{job.snapshots_created}</span> snapshots
                      </div>
                      <span className={`rounded px-2 py-0.5 font-mono text-[10px] uppercase ${
                        job.status === 'completed'
                          ? 'border border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                          : 'border border-red-500/30 bg-red-500/10 text-red-400'
                      }`}>
                        {job.status}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="mt-5 flex justify-end">
              <button
                onClick={() => setShowJobsModal(false)}
                className="rounded border border-vantyx-border bg-vantyx-surface px-4 py-2 text-xs font-medium text-vantyx-textSecondary hover:bg-vantyx-surfaceElevated hover:text-vantyx-textPrimary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
