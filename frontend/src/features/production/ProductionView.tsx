import React, { useEffect, useState } from 'react';
import {
  Scissors,
  Play,
  Film,
  AlertCircle,
  RefreshCw,
  Sparkles,
  Layers,
  X,
  Volume2,
  Download,
  VideoOff,
} from 'lucide-react';
import {
  fetchRenderJobs,
  fetchCandidates,
  triggerRender,
  getRenderStreamUrl,
  getRenderDownloadUrl,
} from '@/lib/api';
import { CandidateClip, RenderJob, RenderSettingsInput } from '@/types';

export const ProductionView: React.FC = () => {
  const [jobs, setJobs] = useState<RenderJob[]>([]);
  const [approvedCandidates, setApprovedCandidates] = useState<CandidateClip[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Video Preview Modal State
  const [previewJob, setPreviewJob] = useState<RenderJob | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(true);

  // Render Trigger Modal State
  const [isRenderModalOpen, setIsRenderModalOpen] = useState<boolean>(false);
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | ''>('');
  const [layoutStyle, setLayoutStyle] = useState<'blurred_backdrop' | 'crop_center'>('blurred_backdrop');
  const [burnSubtitles, setBurnSubtitles] = useState<boolean>(true);
  const [normalizeAudio, setNormalizeAudio] = useState<boolean>(true);
  const [rendering, setRendering] = useState<boolean>(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [jobsData, candidatesData] = await Promise.all([
        fetchRenderJobs(undefined, 50),
        fetchCandidates(undefined, 'approved'),
      ]);
      setJobs(jobsData);
      setApprovedCandidates(candidatesData);
      if (candidatesData.length > 0 && selectedCandidateId === '') {
        setSelectedCandidateId(candidatesData[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load video production data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleStartRender = async (candidateIdToRender?: number) => {
    const targetId = candidateIdToRender || selectedCandidateId;
    if (!targetId) return;

    try {
      setRendering(true);
      setError(null);
      const renderConfig: RenderSettingsInput = {
        layout_style: layoutStyle,
        has_burned_subtitles: burnSubtitles,
        resolution: '1080x1920',
        normalize_audio: normalizeAudio,
      };

      await triggerRender(Number(targetId), renderConfig);
      setIsRenderModalOpen(false);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to trigger video render');
    } finally {
      setRendering(false);
    }
  };

  const completedJobsCount = jobs.filter((j) => j.status === 'completed').length;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-light tracking-wide text-vantyx-textPrimary">
              Shorts Production Engine
            </h1>
            <span className="rounded border border-vantyx-accent/40 bg-vantyx-accent/10 px-2 py-0.5 text-xs font-mono font-medium text-vantyx-accent">
              M05 ACTIVE
            </span>
          </div>
          <p className="mt-1 text-sm text-vantyx-textMuted">
            Automated synthesis of 9:16 vertical Shorts with blurred backdrop padding, EBU R128 audio normalization, and frame-accurate trimming.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadData()}
            className="flex items-center gap-2 rounded-lg border border-vantyx-border bg-vantyx-surfaceElevated px-3 py-2 text-xs font-medium text-vantyx-textPrimary hover:bg-vantyx-border transition-colors"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setIsRenderModalOpen(true)}
            disabled={approvedCandidates.length === 0}
            className="flex items-center gap-2 rounded-lg bg-vantyx-accent px-4 py-2 text-sm font-medium text-vantyx-bg shadow-lg shadow-vantyx-accent/20 transition-all hover:bg-vantyx-accentHover disabled:opacity-50"
          >
            <Scissors size={16} />
            <span>Render Approved Clip</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-950/20 px-4 py-3 text-sm text-red-400">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Overview Metric Bar */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-vantyx-border bg-vantyx-surface p-5">
          <span className="text-xs uppercase tracking-wider text-vantyx-textMuted">Ready to Render</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-mono font-light text-vantyx-textPrimary">
              {approvedCandidates.length}
            </span>
            <span className="text-xs text-vantyx-textMuted">approved clips</span>
          </div>
        </div>

        <div className="rounded-xl border border-vantyx-border bg-vantyx-surface p-5">
          <span className="text-xs uppercase tracking-wider text-vantyx-textMuted">Rendered Shorts</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-mono font-light text-vantyx-accent">
              {completedJobsCount}
            </span>
            <span className="text-xs text-vantyx-textMuted">completed files</span>
          </div>
        </div>

        <div className="rounded-xl border border-vantyx-border bg-vantyx-surface p-5">
          <span className="text-xs uppercase tracking-wider text-vantyx-textMuted">Active Engine</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl font-mono font-medium text-emerald-400">FFmpeg 9.0</span>
            <span className="text-xs text-vantyx-textMuted">H.264 / AAC / EBU R128</span>
          </div>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Left Column: Approved Candidate Queue Ready for Rendering */}
        <div className="rounded-xl border border-vantyx-border bg-vantyx-surface p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-vantyx-border pb-3">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-vantyx-accent" />
              <h2 className="text-sm font-medium text-vantyx-textPrimary">Approved Clip Queue</h2>
            </div>
            <span className="font-mono text-xs text-vantyx-textMuted">
              {approvedCandidates.length} available
            </span>
          </div>

          {approvedCandidates.length === 0 ? (
            <p className="py-8 text-center text-xs text-vantyx-textMuted">
              No approved candidate clips. Review and approve clips in the Selection tab.
            </p>
          ) : (
            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
              {approvedCandidates.map((c) => (
                <div
                  key={c.id}
                  className="rounded-lg border border-vantyx-border bg-vantyx-surfaceElevated p-3 space-y-2 hover:border-vantyx-accent/40 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-vantyx-accent">
                      {c.overall_score.toFixed(1)} PTS
                    </span>
                    <span className="font-mono text-xs text-vantyx-textMuted">
                      {c.duration_seconds}s
                    </span>
                  </div>
                  <h3 className="text-xs font-medium text-vantyx-textPrimary line-clamp-2">
                    {c.title_suggestion}
                  </h3>
                  <button
                    onClick={() => handleStartRender(c.id)}
                    disabled={rendering}
                    className="w-full mt-2 flex items-center justify-center gap-1.5 rounded bg-vantyx-surface border border-vantyx-border py-1.5 text-xs font-medium text-vantyx-textPrimary hover:border-vantyx-accent hover:text-vantyx-accent transition-colors disabled:opacity-50"
                  >
                    <Scissors size={12} />
                    <span>Render 9:16 Short</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Rendered Shorts Queue & Output Gallery */}
        <div className="lg:col-span-2 rounded-xl border border-vantyx-border bg-vantyx-surface p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-vantyx-border pb-3">
            <div className="flex items-center gap-2">
              <Film size={16} className="text-vantyx-accent" />
              <h2 className="text-sm font-medium text-vantyx-textPrimary">Render Jobs & Output Gallery</h2>
            </div>
            <span className="font-mono text-xs text-vantyx-textMuted">
              {jobs.length} total jobs
            </span>
          </div>

          {jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Scissors size={32} className="text-vantyx-textMuted/40" />
              <h3 className="mt-3 text-sm font-medium text-vantyx-textPrimary">No render jobs yet</h3>
              <p className="mt-1 text-xs text-vantyx-textMuted">
                Select an approved clip and trigger rendering to generate vertical Shorts.
              </p>
            </div>
          ) : (
            <div className="space-y-4 max-h-[500px] overflow-y-auto pr-1">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between rounded-lg border border-vantyx-border bg-vantyx-surfaceElevated p-4 gap-4"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2.5">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider ${job.status === 'completed'
                          ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-500/30'
                          : job.status === 'rendering'
                            ? 'bg-amber-950/60 text-amber-400 border border-amber-500/30'
                            : job.status === 'failed'
                              ? 'bg-red-950/60 text-red-400 border border-red-500/30'
                              : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                          }`}
                      >
                        {job.status}
                      </span>
                      <span className="font-mono text-xs font-semibold text-vantyx-textPrimary">
                        Job #{job.id}
                      </span>
                      <span className="font-mono text-xs text-vantyx-textMuted">
                        • {job.resolution} ({job.layout_style})
                      </span>
                    </div>

                    <p className="text-xs text-vantyx-textMuted truncate max-w-md">
                      Candidate Clip #{job.candidate_id} | Created: {new Date(job.created_at).toLocaleTimeString()}
                    </p>

                    {job.status === 'rendering' && (
                      <div className="mt-2 h-1.5 w-48 overflow-hidden rounded-full bg-vantyx-surface">
                        <div
                          className="h-full rounded-full bg-vantyx-accent transition-all duration-300"
                          style={{ width: `${job.progress_pct}%` }}
                        />
                      </div>
                    )}

                    {job.error_message && (
                      <p className="text-xs text-red-400 mt-1">{job.error_message}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {job.status === 'completed' && job.output_file_path && (
                      <>
                        <button
                          onClick={() => {
                            setPreviewJob(job);
                            setPreviewError(null);
                            setPreviewLoading(true);
                          }}
                          className="flex items-center gap-1.5 rounded-lg bg-vantyx-accent/15 border border-vantyx-accent/40 px-3 py-1.5 text-xs font-medium text-vantyx-accent hover:bg-vantyx-accent/25 transition-all"
                        >
                          <Play size={13} />
                          <span>Preview Short</span>
                        </button>
                        <a
                          href={getRenderDownloadUrl(job.id)}
                          download
                          className="flex items-center gap-1.5 rounded-lg bg-vantyx-surface border border-vantyx-border px-3 py-1.5 text-xs font-medium text-vantyx-textMuted hover:text-vantyx-textPrimary hover:border-vantyx-borderActive transition-all"
                          title="Download MP4"
                        >
                          <Download size={13} />
                          <span>Download</span>
                        </a>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Vertical Video Preview Modal */}
      {previewJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
          <div className="relative flex flex-col items-center max-w-sm rounded-2xl border border-vantyx-border bg-vantyx-surface p-4 shadow-2xl">
            <div className="flex w-full items-center justify-between border-b border-vantyx-border pb-3 mb-3">
              <div className="flex items-center gap-2">
                <Play size={16} className="text-vantyx-accent" />
                <h3 className="text-sm font-medium text-vantyx-textPrimary">
                  Short Preview (Job #{previewJob.id})
                </h3>
              </div>
              <button
                onClick={() => {
                  setPreviewJob(null);
                  setPreviewError(null);
                }}
                className="text-vantyx-textMuted hover:text-vantyx-textPrimary"
              >
                <X size={18} />
              </button>
            </div>

            {/* 9:16 Video Player Container */}
            <div className="relative aspect-[9/16] w-[270px] max-h-[480px] overflow-hidden rounded-xl border border-vantyx-border bg-black shadow-inner flex items-center justify-center">
              {previewLoading && !previewError && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/50 z-10">
                  <RefreshCw size={24} className="animate-spin text-vantyx-accent" />
                  <span className="mt-2 text-xs font-mono text-vantyx-textMuted">Loading media stream...</span>
                </div>
              )}

              {previewError ? (
                <div className="flex flex-col items-center justify-center p-4 text-center">
                  <VideoOff size={32} className="text-red-400" />
                  <p className="mt-2 text-xs font-medium text-red-400">{previewError}</p>
                  <p className="mt-1 text-[11px] text-vantyx-textMuted">
                    The rendered file may have been moved or removed from disk.
                  </p>
                </div>
              ) : (
                <video
                  src={getRenderStreamUrl(previewJob.id)}
                  controls
                  autoPlay
                  playsInline
                  onLoadedData={() => setPreviewLoading(false)}
                  onError={() => {
                    setPreviewLoading(false);
                    setPreviewError('Unable to load video stream (file missing or corrupt).');
                  }}
                  className="h-full w-full object-cover"
                />
              )}
            </div>

            <div className="mt-3 w-full flex items-center justify-between">
              <span className="font-mono text-[11px] text-vantyx-textMuted">
                1080x1920 • 9:16 Vertical
              </span>
              <a
                href={getRenderDownloadUrl(previewJob.id)}
                download
                className="flex items-center gap-1.5 rounded bg-vantyx-surfaceElevated border border-vantyx-border px-2.5 py-1 text-xs font-medium text-vantyx-accent hover:border-vantyx-accent transition-colors"
              >
                <Download size={12} />
                <span>Download MP4</span>
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Render Configuration Modal */}
      {isRenderModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-vantyx-border bg-vantyx-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-4">
              <div className="flex items-center gap-2">
                <Scissors size={18} className="text-vantyx-accent" />
                <h3 className="text-base font-medium text-vantyx-textPrimary">Render Vertical Short</h3>
              </div>
              <button
                onClick={() => setIsRenderModalOpen(false)}
                className="text-vantyx-textMuted hover:text-vantyx-textPrimary"
              >
                &times;
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-vantyx-textMuted">
                  Candidate Clip
                </label>
                <select
                  value={selectedCandidateId}
                  onChange={(e) => setSelectedCandidateId(e.target.value ? Number(e.target.value) : '')}
                  className="mt-1 w-full rounded-lg border border-vantyx-border bg-vantyx-surfaceElevated px-3 py-2 text-sm text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                >
                  {approvedCandidates.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.title_suggestion} ({c.duration_seconds}s)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-vantyx-textMuted">
                  Vertical Re-Framing Layout
                </label>
                <div className="mt-2 grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setLayoutStyle('blurred_backdrop')}
                    className={`flex flex-col rounded-lg border p-3 text-left transition-all ${layoutStyle === 'blurred_backdrop'
                      ? 'border-vantyx-accent bg-vantyx-accent/10 text-vantyx-accent'
                      : 'border-vantyx-border bg-vantyx-surfaceElevated text-vantyx-textMuted'
                      }`}
                  >
                    <span className="text-xs font-medium text-vantyx-textPrimary">Blurred Backdrop</span>
                    <span className="text-[10px] text-vantyx-textMuted mt-0.5">
                      Crisp full 16:9 gameplay with blurred top/bottom padding
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setLayoutStyle('crop_center')}
                    className={`flex flex-col rounded-lg border p-3 text-left transition-all ${layoutStyle === 'crop_center'
                      ? 'border-vantyx-accent bg-vantyx-accent/10 text-vantyx-accent'
                      : 'border-vantyx-border bg-vantyx-surfaceElevated text-vantyx-textMuted'
                      }`}
                  >
                    <span className="text-xs font-medium text-vantyx-textPrimary">Center Crop</span>
                    <span className="text-[10px] text-vantyx-textMuted mt-0.5">
                      Direct 9:16 focal crop filling full screen
                    </span>
                  </button>
                </div>
              </div>

              <div className="space-y-2 pt-2 border-t border-vantyx-border">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={normalizeAudio}
                    onChange={(e) => setNormalizeAudio(e.target.checked)}
                    className="accent-vantyx-accent rounded"
                  />
                  <span className="text-xs text-vantyx-textPrimary flex items-center gap-1.5">
                    <Volume2 size={13} className="text-vantyx-accent" />
                    EBU R128 Audio Normalization (-14 LUFS)
                  </span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={burnSubtitles}
                    onChange={(e) => setBurnSubtitles(e.target.checked)}
                    className="accent-vantyx-accent rounded"
                  />
                  <span className="text-xs text-vantyx-textPrimary flex items-center gap-1.5">
                    <Layers size={13} className="text-vantyx-accent" />
                    Burned-in Animated Captions
                  </span>
                </label>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3 border-t border-vantyx-border pt-4">
              <button
                type="button"
                onClick={() => setIsRenderModalOpen(false)}
                className="rounded-lg px-4 py-2 text-xs font-medium text-vantyx-textMuted hover:text-vantyx-textPrimary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleStartRender()}
                disabled={rendering || !selectedCandidateId}
                className="flex items-center gap-2 rounded-lg bg-vantyx-accent px-4 py-2 text-xs font-medium text-vantyx-bg hover:bg-vantyx-accentHover disabled:opacity-50"
              >
                {rendering ? 'Synthesizing Short...' : 'Start Render'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
