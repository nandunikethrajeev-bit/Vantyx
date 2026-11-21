import React, { useEffect, useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Filter,
  Flame,
  Clock,
  Volume2,
  BookOpen,
  AlertCircle,
  Play,
} from 'lucide-react';
import {
  fetchCandidates,
  updateCandidate,
  generateCandidates,
  fetchDailyQueue,
  fetchVideoSources,
} from '@/lib/api';
import { CandidateClip, DailySelectionResponse, VideoSource } from '@/types';

export const SelectionView: React.FC = () => {
  const [candidates, setCandidates] = useState<CandidateClip[]>([]);
  const [dailyQueue, setDailyQueue] = useState<DailySelectionResponse | null>(null);
  const [sources, setSources] = useState<VideoSource[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [error, setError] = useState<string | null>(null);

  // Generation Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [selectedSourceId, setSelectedSourceId] = useState<number | ''>('');
  const [minScore, setMinScore] = useState<number>(60);
  const [weightPreset, setWeightPreset] = useState<'balanced' | 'hook' | 'retention'>('balanced');
  const [generating, setGenerating] = useState<boolean>(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [candList, queue, srcList] = await Promise.all([
        fetchCandidates(undefined, statusFilter === 'all' ? undefined : statusFilter),
        fetchDailyQueue(4),
        fetchVideoSources(undefined, true),
      ]);
      setCandidates(candList);
      setDailyQueue(queue);
      setSources(srcList);
      if (srcList.length > 0 && selectedSourceId === '') {
        setSelectedSourceId(srcList[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load selection data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const handleUpdateStatus = async (
    candidateId: number,
    status: 'approved' | 'rejected' | 'candidate'
  ) => {
    try {
      await updateCandidate(candidateId, { status });
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to update candidate clip');
    }
  };

  const handleGenerate = async () => {
    if (!selectedSourceId) return;
    try {
      setGenerating(true);
      setError(null);

      let weights;
      if (weightPreset === 'hook') {
        weights = { hook_weight: 0.55, retention_weight: 0.25, context_weight: 0.1, audio_weight: 0.1 };
      } else if (weightPreset === 'retention') {
        weights = { hook_weight: 0.25, retention_weight: 0.50, context_weight: 0.15, audio_weight: 0.1 };
      } else {
        weights = { hook_weight: 0.35, retention_weight: 0.35, context_weight: 0.15, audio_weight: 0.15 };
      }

      await generateCandidates(Number(selectedSourceId), {
        min_score_threshold: minScore,
        max_candidates: 8,
        weights,
      });

      setIsModalOpen(false);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to generate candidates');
    } finally {
      setGenerating(false);
    }
  };

  const formatTimestamp = (sec: number): string => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const approvedCount = candidates.filter((c) => c.status === 'approved').length;

  return (
    <div className="space-y-8">
      {/* View Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-light tracking-wide text-vantyx-textPrimary">
              Intelligent Clip Selection
            </h1>
            <span className="rounded border border-vantyx-accent/40 bg-vantyx-accent/10 px-2 py-0.5 text-xs font-mono font-medium text-vantyx-accent">
              M04 ACTIVE
            </span>
          </div>
          <p className="mt-1 text-sm text-vantyx-textMuted">
            Algorithmic ranking of hook impact, retention curves, narrative context, and audio quality targeting 4 daily Shorts.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 rounded-lg bg-vantyx-accent px-4 py-2 text-sm font-medium text-vantyx-bg shadow-lg shadow-vantyx-accent/20 transition-all hover:bg-vantyx-accentHover"
          >
            <Sparkles size={16} />
            <span>Generate Candidates</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-950/20 px-4 py-3 text-sm text-red-400">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Daily Pipeline Target Banner */}
      <div className="rounded-xl border border-vantyx-border bg-vantyx-surface p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Flame size={18} className="text-vantyx-accent" />
              <h2 className="text-base font-medium text-vantyx-textPrimary">
                Daily YouTube Shorts Quota
              </h2>
            </div>
            <p className="text-xs text-vantyx-textMuted">
              Production quota for channel <span className="font-semibold text-vantyx-textPrimary">Astro Rebel</span> (Target: 4 Shorts/day)
            </p>
          </div>

          <div className="flex items-center gap-6">
            <div className="text-right">
              <span className="text-2xl font-mono font-bold text-vantyx-accent">
                {dailyQueue ? dailyQueue.selected_count : approvedCount} / 4
              </span>
              <span className="block text-xs text-vantyx-textMuted">Ready / Target</span>
            </div>
            <div className="h-10 w-px bg-vantyx-border" />
            <div className="min-w-[140px]">
              {dailyQueue?.has_sufficient_moments ? (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-950/20 px-3 py-1 text-xs font-medium text-emerald-400">
                  <CheckCircle2 size={13} />
                  <span>Quota Ready</span>
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-950/20 px-3 py-1 text-xs font-medium text-amber-400">
                  <AlertCircle size={13} />
                  <span>Need More Clips</span>
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-vantyx-surfaceElevated">
          <div
            className="h-full rounded-full bg-gradient-to-r from-vantyx-accent to-amber-300 transition-all duration-500"
            style={{
              width: `${Math.min(100, (((dailyQueue ? dailyQueue.selected_count : approvedCount) / 4) * 100))}%`,
            }}
          />
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between border-b border-vantyx-border pb-3">
        <div className="flex items-center gap-2">
          <Filter size={15} className="text-vantyx-textMuted" />
          <span className="text-xs uppercase tracking-wider text-vantyx-textMuted">Status:</span>
          {(['all', 'candidate', 'approved', 'rejected'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`rounded px-3 py-1 text-xs capitalize transition-colors ${
                statusFilter === s
                  ? 'bg-vantyx-accent/20 font-medium text-vantyx-accent'
                  : 'text-vantyx-textMuted hover:text-vantyx-textPrimary'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <span className="font-mono text-xs text-vantyx-textMuted">
          {candidates.length} moment{candidates.length === 1 ? '' : 's'} indexed
        </span>
      </div>

      {/* Candidate Clips Grid */}
      {loading ? (
        <div className="flex h-48 items-center justify-center text-sm text-vantyx-textMuted">
          Loading candidate moments...
        </div>
      ) : candidates.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-vantyx-border py-16 text-center">
          <Sparkles size={36} className="text-vantyx-textMuted/40" />
          <h3 className="mt-4 text-base font-medium text-vantyx-textPrimary">No candidate clips found</h3>
          <p className="mt-1 max-w-sm text-xs text-vantyx-textMuted">
            Run intelligence analysis on an eligible video source and click "Generate Candidates" to rank moments.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="mt-5 rounded-lg border border-vantyx-border bg-vantyx-surfaceElevated px-4 py-2 text-xs font-medium text-vantyx-textPrimary hover:bg-vantyx-border"
          >
            Generate Candidates Now
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          {candidates.map((clip) => (
            <div
              key={clip.id}
              className={`relative flex flex-col justify-between rounded-xl border p-5 transition-all ${
                clip.status === 'approved'
                  ? 'border-vantyx-accent/50 bg-vantyx-surface/90 shadow-md shadow-vantyx-accent/5'
                  : clip.status === 'rejected'
                  ? 'border-vantyx-border/40 bg-vantyx-surface/40 opacity-60'
                  : 'border-vantyx-border bg-vantyx-surface hover:border-vantyx-border/80'
              }`}
            >
              <div className="space-y-3">
                {/* Top Bar: Timestamps & Score Badge */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1 rounded bg-vantyx-surfaceElevated px-2 py-0.5 font-mono text-xs text-vantyx-textPrimary">
                      <Clock size={12} className="text-vantyx-textMuted" />
                      {formatTimestamp(clip.start_time)} - {formatTimestamp(clip.end_time)}
                    </span>
                    <span className="font-mono text-xs text-vantyx-textMuted">
                      ({clip.duration_seconds}s)
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded px-2.5 py-0.5 font-mono text-xs font-bold ${
                        clip.overall_score >= 80
                          ? 'border border-amber-400/40 bg-amber-400/10 text-amber-300'
                          : clip.overall_score >= 65
                          ? 'border border-blue-400/40 bg-blue-400/10 text-blue-300'
                          : 'border border-zinc-700 bg-zinc-800 text-zinc-400'
                      }`}
                    >
                      {clip.overall_score.toFixed(1)} PTS
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider ${
                        clip.status === 'approved'
                          ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-500/30'
                          : clip.status === 'rejected'
                          ? 'bg-red-950/60 text-red-400 border border-red-500/30'
                          : 'bg-zinc-800 text-zinc-300 border border-zinc-700'
                      }`}
                    >
                      {clip.status}
                    </span>
                  </div>
                </div>

                {/* Title */}
                <div>
                  <h3 className="text-base font-medium text-vantyx-textPrimary">
                    {clip.title_suggestion}
                  </h3>
                  {clip.video_title && (
                    <p className="mt-0.5 text-xs text-vantyx-textMuted truncate">
                      Source: {clip.video_title}
                    </p>
                  )}
                </div>

                {/* Score Breakdown Bars */}
                <div className="grid grid-cols-4 gap-2 rounded-lg bg-vantyx-surfaceElevated/60 p-2.5">
                  <div>
                    <span className="flex items-center gap-1 text-[11px] text-vantyx-textMuted">
                      <Flame size={11} className="text-amber-400" /> Hook
                    </span>
                    <span className="font-mono text-xs font-semibold text-vantyx-textPrimary">
                      {clip.hook_score.toFixed(0)}
                    </span>
                  </div>
                  <div>
                    <span className="flex items-center gap-1 text-[11px] text-vantyx-textMuted">
                      <Play size={11} className="text-emerald-400" /> Retention
                    </span>
                    <span className="font-mono text-xs font-semibold text-vantyx-textPrimary">
                      {clip.retention_score.toFixed(0)}
                    </span>
                  </div>
                  <div>
                    <span className="flex items-center gap-1 text-[11px] text-vantyx-textMuted">
                      <BookOpen size={11} className="text-blue-400" /> Context
                    </span>
                    <span className="font-mono text-xs font-semibold text-vantyx-textPrimary">
                      {clip.context_score.toFixed(0)}
                    </span>
                  </div>
                  <div>
                    <span className="flex items-center gap-1 text-[11px] text-vantyx-textMuted">
                      <Volume2 size={11} className="text-purple-400" /> Audio
                    </span>
                    <span className="font-mono text-xs font-semibold text-vantyx-textPrimary">
                      {clip.audio_score.toFixed(0)}
                    </span>
                  </div>
                </div>

                {/* Explainable Rationale */}
                {clip.rationale && (
                  <p className="text-xs leading-relaxed text-vantyx-textMuted italic">
                    "{clip.rationale}"
                  </p>
                )}
              </div>

              {/* Action Buttons */}
              <div className="mt-5 flex items-center justify-end gap-2 border-t border-vantyx-border/60 pt-3">
                {clip.status !== 'approved' && (
                  <button
                    onClick={() => handleUpdateStatus(clip.id, 'approved')}
                    className="flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-950/20 px-3 py-1.5 text-xs font-medium text-emerald-400 transition-colors hover:bg-emerald-900/30"
                  >
                    <CheckCircle2 size={13} />
                    <span>Approve</span>
                  </button>
                )}
                {clip.status !== 'rejected' && (
                  <button
                    onClick={() => handleUpdateStatus(clip.id, 'rejected')}
                    className="flex items-center gap-1.5 rounded-lg border border-red-500/30 bg-red-950/20 px-3 py-1.5 text-xs font-medium text-red-400 transition-colors hover:bg-red-900/30"
                  >
                    <XCircle size={13} />
                    <span>Reject</span>
                  </button>
                )}
                {clip.status !== 'candidate' && (
                  <button
                    onClick={() => handleUpdateStatus(clip.id, 'candidate')}
                    className="flex items-center gap-1.5 rounded-lg border border-vantyx-border bg-vantyx-surfaceElevated px-3 py-1.5 text-xs font-medium text-vantyx-textMuted transition-colors hover:text-vantyx-textPrimary"
                  >
                    <RotateCcw size={13} />
                    <span>Reset</span>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Generation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-vantyx-border bg-vantyx-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-4">
              <div className="flex items-center gap-2">
                <Sparkles size={18} className="text-vantyx-accent" />
                <h3 className="text-base font-medium text-vantyx-textPrimary">Generate Candidate Clips</h3>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-vantyx-textMuted hover:text-vantyx-textPrimary"
              >
                &times;
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-vantyx-textMuted">
                  Eligible Video Source
                </label>
                <select
                  value={selectedSourceId}
                  onChange={(e) => setSelectedSourceId(e.target.value ? Number(e.target.value) : '')}
                  className="mt-1 w-full rounded-lg border border-vantyx-border bg-vantyx-surfaceElevated px-3 py-2 text-sm text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                >
                  {sources.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title} ({s.duration_seconds}s)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex justify-between text-xs text-vantyx-textMuted">
                  <span>Minimum Overall Score</span>
                  <span className="font-mono font-semibold text-vantyx-textPrimary">{minScore} pts</span>
                </div>
                <input
                  type="range"
                  min="30"
                  max="80"
                  value={minScore}
                  onChange={(e) => setMinScore(Number(e.target.value))}
                  className="mt-2 w-full accent-vantyx-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-vantyx-textMuted">
                  Ranking Weight Preset
                </label>
                <div className="mt-2 grid grid-cols-3 gap-2">
                  {[
                    { id: 'balanced', label: 'Balanced', desc: 'Equal Hook & Retention' },
                    { id: 'hook', label: 'Hook Heavy', desc: 'Aggressive 3s impact' },
                    { id: 'retention', label: 'Story Pacing', desc: 'Sustained climax' },
                  ].map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setWeightPreset(p.id as any)}
                      className={`flex flex-col rounded-lg border p-2 text-left transition-all ${
                        weightPreset === p.id
                          ? 'border-vantyx-accent bg-vantyx-accent/10 text-vantyx-accent'
                          : 'border-vantyx-border bg-vantyx-surfaceElevated text-vantyx-textMuted'
                      }`}
                    >
                      <span className="text-xs font-medium text-vantyx-textPrimary">{p.label}</span>
                      <span className="text-[10px] text-vantyx-textMuted mt-0.5">{p.desc}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3 border-t border-vantyx-border pt-4">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="rounded-lg px-4 py-2 text-xs font-medium text-vantyx-textMuted hover:text-vantyx-textPrimary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleGenerate}
                disabled={generating || !selectedSourceId}
                className="flex items-center gap-2 rounded-lg bg-vantyx-accent px-4 py-2 text-xs font-medium text-vantyx-bg hover:bg-vantyx-accentHover disabled:opacity-50"
              >
                {generating ? 'Ranking Scenes...' : 'Run Ranking'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
