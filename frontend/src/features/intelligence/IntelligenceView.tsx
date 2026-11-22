import React, { useEffect, useState } from 'react';
import {
  Cpu,
  Sparkles,
  Flame,
  Activity,
  Tag,
  Clock,
  ShieldCheck,
  Film,
  CheckCircle2,
} from 'lucide-react';
import { fetchAnalysisJobs, fetchVideoSources, triggerVideoAnalysis } from '@/lib/api';
import { AnalysisJob, VideoScene, VideoSource } from '@/types';

export const IntelligenceView: React.FC = () => {
  const [sources, setSources] = useState<VideoSource[]>([]);
  const [selectedSource, setSelectedSource] = useState<VideoSource | null>(null);
  const [activeJob, setActiveJob] = useState<AnalysisJob | null>(null);
  const [jobsHistory, setJobsHistory] = useState<AnalysisJob[]>([]);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadData = async () => {
    try {
      const [srcData, jData] = await Promise.all([
        fetchVideoSources(undefined, true), // Only legally eligible sources
        fetchAnalysisJobs(),
      ]);
      setSources(srcData);
      setJobsHistory(jData);

      if (srcData.length > 0 && !selectedSource) {
        setSelectedSource(srcData[0]);
        // Find if job exists for this source
        const existingJob = jData.find((j) => j.source_id === srcData[0].id && j.status === 'completed');
        if (existingJob) {
          setActiveJob(existingJob);
        }
      }
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to load intelligence data',
      });
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSelectSource = (src: VideoSource) => {
    setSelectedSource(src);
    const existingJob = jobsHistory.find((j) => j.source_id === src.id && j.status === 'completed');
    setActiveJob(existingJob || null);
    setMessage(null);
  };

  const handleAnalyze = async (force = false) => {
    if (!selectedSource) return;
    setAnalyzing(true);
    setMessage(null);
    try {
      const job = await triggerVideoAnalysis(selectedSource.id, force);
      setActiveJob(job);
      setMessage({
        type: 'success',
        text: `Analysis complete: ${job.scenes.length} high-interest moments identified via ${job.provider.toUpperCase()} provider.`,
      });
      // Refresh jobs history
      const updatedJobs = await fetchAnalysisJobs();
      setJobsHistory(updatedJobs);
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'AI analysis failed',
      });
    } finally {
      setAnalyzing(false);
    }
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-vantyx-border pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono tracking-widest text-vantyx-accent uppercase mb-1">
            <span>Milestone 03</span>
            <span>•</span>
            <span>AI Multimodal Intelligence Engine</span>
          </div>
          <h2 className="text-xl font-light text-vantyx-textPrimary">
            Semantic Scene Segmentation & Engaging Moment Detection
          </h2>
          <p className="text-xs text-vantyx-textSecondary mt-1">
            Deep multimodal analysis on verified long-form sources: transcript extraction, narrative arc
            tagging, and hook excitement scoring.
          </p>
        </div>

        {selectedSource && (
          <div className="flex items-center gap-2.5">
            <button
              onClick={() => handleAnalyze(true)}
              disabled={analyzing}
              className="flex items-center gap-2 rounded border border-vantyx-accent bg-vantyx-accent/10 px-4 py-2 text-xs font-mono font-medium text-vantyx-accent hover:bg-vantyx-accent hover:text-black transition-all disabled:opacity-40"
            >
              <Sparkles size={14} className={analyzing ? 'animate-spin' : ''} />
              {analyzing ? 'Analyzing Scenes...' : activeJob ? 'Re-Analyze Media' : 'Run AI Analysis'}
            </button>
          </div>
        )}
      </div>

      {/* Notifications */}
      {message && (
        <div
          className={`flex items-center justify-between rounded border p-3 text-xs font-mono ${
            message.type === 'success'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
              : 'border-rose-500/30 bg-rose-500/10 text-rose-400'
          }`}
        >
          <span>{message.text}</span>
          <button onClick={() => setMessage(null)} className="text-vantyx-textMuted hover:text-white">
            ✕
          </button>
        </div>
      )}

      {/* Split Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Eligible Sources List */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-[11px] font-mono uppercase text-vantyx-textMuted">
              Eligible Sources ({sources.length})
            </span>
            <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
              <ShieldCheck size={12} /> Rights Verified
            </span>
          </div>

          {sources.length === 0 ? (
            <div className="rounded border border-vantyx-border bg-vantyx-surface/40 p-6 text-center text-xs font-mono text-vantyx-textMuted">
              No eligible video sources found. Ingest media in Milestone 02 Discovery workspace.
            </div>
          ) : (
            <div className="space-y-2 max-h-[700px] overflow-y-auto pr-1">
              {sources.map((src) => {
                const isSelected = selectedSource?.id === src.id;
                const hasAnalysis = jobsHistory.some((j) => j.source_id === src.id && j.status === 'completed');

                return (
                  <button
                    key={src.id}
                    onClick={() => handleSelectSource(src)}
                    className={`w-full text-left rounded border p-3 transition-all ${
                      isSelected
                        ? 'border-vantyx-accent bg-vantyx-surfaceElevated shadow-lg'
                        : 'border-vantyx-border bg-vantyx-surface hover:bg-vantyx-surfaceElevated/60'
                    }`}
                  >
                    <div className="flex gap-3">
                      {src.thumbnail_url ? (
                        <img
                          src={src.thumbnail_url}
                          alt=""
                          className="h-12 w-20 object-cover rounded border border-vantyx-border shrink-0"
                        />
                      ) : (
                        <div className="h-12 w-20 bg-vantyx-bg border border-vantyx-border rounded flex items-center justify-center shrink-0">
                          <Film size={14} className="text-vantyx-textMuted" />
                        </div>
                      )}

                      <div className="min-w-0 flex-1">
                        <h4 className="font-sans text-xs font-medium text-vantyx-textPrimary truncate">
                          {src.title}
                        </h4>
                        <div className="mt-1 flex items-center gap-2 text-[10px] font-mono text-vantyx-textMuted">
                          <span>{src.creator_name || 'Astro Rebel'}</span>
                          <span>•</span>
                          <span>{formatTime(src.duration_seconds)}</span>
                        </div>
                        <div className="mt-2 flex items-center justify-between">
                          <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                            <ShieldCheck size={11} /> Eligible
                          </span>
                          {hasAnalysis && (
                            <span className="text-[10px] font-mono text-vantyx-accent flex items-center gap-1">
                              <CheckCircle2 size={11} /> Indexed
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: AI Scene Inspector */}
        <div className="lg:col-span-8 space-y-4">
          {selectedSource ? (
            <div className="rounded border border-vantyx-border bg-vantyx-surface p-5 space-y-5">
              {/* Selected Source Header */}
              <div className="flex items-start justify-between border-b border-vantyx-border pb-4">
                <div>
                  <h3 className="text-sm font-medium text-vantyx-textPrimary">{selectedSource.title}</h3>
                  <div className="mt-1 flex items-center gap-3 text-xs font-mono text-vantyx-textMuted">
                    <span>ID: {selectedSource.video_id}</span>
                    <span>•</span>
                    <span>Duration: {formatTime(selectedSource.duration_seconds)}</span>
                    <span>•</span>
                    <a
                      href={selectedSource.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-vantyx-accent hover:underline"
                    >
                      View Source
                    </a>
                  </div>
                </div>

                {activeJob && (
                  <div className="text-right font-mono">
                    <span className={`inline-block border text-[11px] px-2.5 py-0.5 rounded uppercase ${
                      activeJob.provider === 'gemini'
                        ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                        : 'border-vantyx-accent/40 bg-vantyx-accent/10 text-vantyx-accent'
                    }`}>
                      {activeJob.provider === 'gemini'
                        ? 'Engine: Gemini 2.5 Flash'
                        : activeJob.provider === 'heuristic_fallback'
                        ? 'Engine: Heuristic (Fallback)'
                        : 'Engine: Heuristic Rule Engine'}
                    </span>
                    <span className="block text-[10px] text-vantyx-textMuted mt-1">
                      {activeJob.scenes.length} Scenes Identified
                    </span>
                  </div>
                )}
              </div>

              {/* Analysis Status / Empty State */}
              {!activeJob ? (
                <div className="py-16 text-center space-y-3 font-mono">
                  <Cpu size={32} className="mx-auto text-vantyx-textMuted" />
                  <p className="text-xs text-vantyx-textSecondary">
                    No intelligence analysis recorded for this source.
                  </p>
                  <button
                    onClick={() => handleAnalyze(false)}
                    disabled={analyzing}
                    className="inline-flex items-center gap-2 rounded border border-vantyx-accent bg-vantyx-accent px-4 py-2 text-xs font-semibold text-black hover:bg-vantyx-accentHover transition-all"
                  >
                    <Sparkles size={14} />
                    {analyzing ? 'Extracting Moments...' : 'Execute Multimodal Analysis'}
                  </button>
                </div>
              ) : activeJob.scenes.length === 0 ? (
                <div className="py-12 text-center text-xs font-mono text-vantyx-textMuted">
                  Analysis completed, but no high-scoring scenes exceeded the minimum threshold.
                </div>
              ) : (
                /* Scene Cards Timeline */
                <div className="space-y-3">
                  {/* Provider Transparency Disclosure */}
                  {activeJob.provider !== 'gemini' && (
                    <div className="rounded border border-amber-500/30 bg-amber-500/10 p-3 text-xs font-mono text-amber-300 flex items-start gap-2.5">
                      <Sparkles size={16} className="text-amber-400 shrink-0 mt-0.5" />
                      <div>
                        <div className="font-semibold text-amber-200 uppercase text-[11px]">
                          Heuristic Metadata Segmentation Active (Visual Frame AI Disabled)
                        </div>
                        <div className="mt-0.5 text-[11px] text-amber-300/80 leading-relaxed">
                          Scene boundaries, pacing metrics, and GTA narrative tags are estimated from video metadata, keyword analysis, and duration pacing rules. Real visual frame-level understanding requires configuring <code className="text-white bg-black/40 px-1 py-0.5 rounded">GEMINI_API_KEY</code>.
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between text-xs font-mono text-vantyx-textMuted">
                    <span>SEGMENTED SCENE BREAKDOWN</span>
                    <span>ACTION & EXCITEMENT METRICS</span>
                  </div>

                  <div className="space-y-3">
                    {activeJob.scenes.map((scene: VideoScene, idx: number) => {
                      const excitementPct = Math.round(scene.excitement_score * 100);
                      const intensityPct = Math.round(scene.action_intensity * 100);

                      return (
                        <div
                          key={scene.id}
                          className="rounded border border-vantyx-border bg-vantyx-bg/60 p-4 space-y-3 hover:border-vantyx-accent/40 transition-all"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-2.5">
                              <span className="font-mono text-xs font-semibold text-vantyx-accent border border-vantyx-accent/30 bg-vantyx-accent/10 px-2 py-0.5 rounded">
                                #{idx + 1}
                              </span>
                              <div>
                                <h4 className="text-xs font-semibold text-vantyx-textPrimary">
                                  {scene.scene_label}
                                </h4>
                                <div className="mt-0.5 flex items-center gap-2 text-[11px] font-mono text-vantyx-textMuted">
                                  <Clock size={12} />
                                  <span>
                                    {formatTime(scene.start_time)} - {formatTime(scene.end_time)}
                                  </span>
                                  <span>({scene.duration_seconds}s)</span>
                                </div>
                              </div>
                            </div>

                            {/* Excitement Badge */}
                            <div className="flex items-center gap-3 font-mono text-xs">
                              <div className="text-right">
                                <span className="text-[10px] text-vantyx-textMuted block">Excitement</span>
                                <span className="text-xs font-bold text-vantyx-accent flex items-center gap-1 justify-end">
                                  <Flame size={12} /> {excitementPct}%
                                </span>
                              </div>
                              <div className="text-right">
                                <span className="text-[10px] text-vantyx-textMuted block">Intensity</span>
                                <span className="text-xs font-bold text-emerald-400 flex items-center gap-1 justify-end">
                                  <Activity size={12} /> {intensityPct}%
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Speech Transcript Extraction */}
                          {scene.speech_transcript && (
                            <div className="rounded border border-vantyx-borderSubtle bg-vantyx-surface/50 p-2.5 text-xs text-vantyx-textSecondary font-mono italic">
                              "{scene.speech_transcript}"
                            </div>
                          )}

                          {/* Measured Physical Audio Metrics */}
                          {scene.audio_metrics && (
                            <div className="flex flex-wrap items-center gap-3 rounded border border-vantyx-borderSubtle bg-vantyx-surface/30 px-2.5 py-1.5 text-[11px] font-mono text-vantyx-textSecondary">
                              <span className="text-vantyx-accent uppercase text-[10px] font-semibold tracking-wider">
                                Measured Audio:
                              </span>
                              {scene.audio_metrics.rms_db !== null && scene.audio_metrics.rms_db !== undefined && (
                                <span>RMS: {scene.audio_metrics.rms_db} dB</span>
                              )}
                              {scene.audio_metrics.peak_db !== null && scene.audio_metrics.peak_db !== undefined && (
                                <span>Peak: {scene.audio_metrics.peak_db} dB</span>
                              )}
                              {scene.audio_metrics.loudness_range_lu !== null && scene.audio_metrics.loudness_range_lu !== undefined && (
                                <span>LRA: {scene.audio_metrics.loudness_range_lu} LU</span>
                              )}
                              {scene.audio_metrics.audio_score !== null && scene.audio_metrics.audio_score !== undefined && (
                                <span className="text-emerald-400 font-medium">
                                  Track Score: {scene.audio_metrics.audio_score}/100
                                </span>
                              )}
                            </div>
                          )}

                          {/* Semantic Tags */}
                          {scene.tags && scene.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 pt-1">
                              {scene.tags.map((tag: string, tIdx: number) => (
                                <span
                                  key={tIdx}
                                  className="inline-flex items-center gap-1 rounded bg-vantyx-surfaceElevated px-2 py-0.5 text-[10px] font-mono text-vantyx-textMuted border border-vantyx-borderSubtle"
                                >
                                  <Tag size={10} className="text-vantyx-accent" />
                                  #{tag}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded border border-vantyx-border bg-vantyx-surface p-12 text-center text-xs font-mono text-vantyx-textMuted">
              Select an eligible video source from the catalog to view intelligence data.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
