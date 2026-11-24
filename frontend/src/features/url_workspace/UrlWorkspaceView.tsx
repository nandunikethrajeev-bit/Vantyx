import React, { useState, useEffect, useMemo } from 'react';
import {
  Sparkles,
  Play,
  RotateCcw,
  CheckCircle2,
  Clock,
  AlertCircle,
  ExternalLink,
  Film,
  HardDrive,
  Link as LinkIcon,
  RefreshCw,
  FolderOpen,
} from 'lucide-react';
import {
  submitBatchIntake,
  fetchIntakeBatches,
  fetchIntakeBatch,
  triggerBatchProcess,
  retryBatchItem,
  linkSourceLocalMedia,
  uploadSourceMedia,
} from '@/lib/api';
import { BatchIntakeResponse, BatchItemResponse, NavigationSection } from '@/types';

interface UrlWorkspaceViewProps {
  onNavigate?: (section: NavigationSection) => void;
}

const YOUTUBE_REGEX =
  /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/i;

export const UrlWorkspaceView: React.FC<UrlWorkspaceViewProps> = ({ onNavigate }) => {
  const [urlInput, setUrlInput] = useState<string>('');
  const [batchNotes, setBatchNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [batches, setBatches] = useState<BatchIntakeResponse[]>([]);
  const [activeBatch, setActiveBatch] = useState<BatchIntakeResponse | null>(null);
  const [loadingBatches, setLoadingBatches] = useState<boolean>(true);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(
    null
  );

  // Attach Media Modal
  const [mediaModalItem, setMediaModalItem] = useState<BatchItemResponse | null>(null);
  const [mediaModalMode, setMediaModalMode] = useState<'link' | 'upload'>('link');
  const [localMediaPath, setLocalMediaPath] = useState<string>('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [isAttaching, setIsAttaching] = useState<boolean>(false);

  // Parse lines and compute real-time validation stats
  const validationStats = useMemo(() => {
    const rawLines = urlInput
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0);

    const validUrls: string[] = [];
    const seenIds = new Set<string>();
    let duplicates = 0;
    let invalid = 0;

    for (const line of rawLines) {
      const match = line.match(YOUTUBE_REGEX);
      if (match && match[1]) {
        const vid = match[1];
        if (seenIds.has(vid)) {
          duplicates += 1;
        } else {
          seenIds.add(vid);
          validUrls.push(line);
        }
      } else {
        invalid += 1;
      }
    }

    return {
      total: rawLines.length,
      validCount: validUrls.length,
      duplicates,
      invalid,
      validUrls,
    };
  }, [urlInput]);

  const loadBatches = async (silent = false) => {
    if (!silent) setLoadingBatches(true);
    try {
      const list = await fetchIntakeBatches(15);
      setBatches(list);
      if (list.length > 0 && !activeBatch) {
        setActiveBatch(list[0]);
      } else if (activeBatch) {
        const updated = list.find((b) => b.batch_id === activeBatch.batch_id);
        if (updated) setActiveBatch(updated);
      }
    } catch (err: any) {
      if (!silent) {
        setStatusMessage({ type: 'error', text: `Failed to load batches: ${err.message || 'Network error'}` });
      }
    } finally {
      if (!silent) setLoadingBatches(false);
    }
  };

  useEffect(() => {
    loadBatches();
  }, []);

  // Poll active batch if any item is actively in progress
  useEffect(() => {
    if (!activeBatch) return;
    const hasActiveItems = activeBatch.items.some((item) =>
      [
        'url_submitted',
        'url_validated',
        'metadata_resolved',
        'rights_verified',
        'media_resolving',
        'analyzing',
        'candidates_ready',
        'rendering',
      ].includes(item.status)
    );

    if (hasActiveItems) {
      const timer = setInterval(async () => {
        try {
          const fresh = await fetchIntakeBatch(activeBatch.batch_id);
          setActiveBatch(fresh);
        } catch {
          // ignore transient poll error
        }
      }, 3000);
      return () => clearInterval(timer);
    }
  }, [activeBatch]);

  const handleSubmitBatch = async () => {
    if (validationStats.validCount === 0) {
      setStatusMessage({ type: 'error', text: 'Please enter at least one valid YouTube URL.' });
      return;
    }

    setIsSubmitting(true);
    setStatusMessage(null);
    try {
      const res = await submitBatchIntake(validationStats.validUrls, batchNotes, true);
      setActiveBatch(res);
      setUrlInput('');
      setBatchNotes('');
      setStatusMessage({
        type: 'success',
        text: `Submitted batch ${res.batch_id} with ${res.total_valid} valid URLs. Autonomous pipeline initiated.`,
      });
      loadBatches(true);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: `Submission failed: ${err.message || 'Server error'}` });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTriggerProcess = async (batchId: string) => {
    setIsProcessing(true);
    setStatusMessage(null);
    try {
      const res = await triggerBatchProcess(batchId);
      setActiveBatch(res);
      setStatusMessage({
        type: 'success',
        text: `Autonomous pipeline triggered for batch ${batchId}.`,
      });
      loadBatches(true);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: `Process trigger failed: ${err.message || 'Server error'}` });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRetryItem = async (itemId: number) => {
    setStatusMessage(null);
    try {
      const updated = await retryBatchItem(itemId);
      if (activeBatch) {
        const fresh = await fetchIntakeBatch(activeBatch.batch_id);
        setActiveBatch(fresh);
      }
      setStatusMessage({
        type: 'info',
        text: `Retried URL ${updated.video_id}: status is now ${updated.status}.`,
      });
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: `Retry failed: ${err.message || 'Server error'}` });
    }
  };

  const handleAttachMedia = async () => {
    if (!mediaModalItem || !mediaModalItem.source_id) return;
    setIsAttaching(true);
    setStatusMessage(null);
    try {
      if (mediaModalMode === 'link') {
        if (!localMediaPath.trim()) {
          alert('Please enter a valid local media file path.');
          setIsAttaching(false);
          return;
        }
        await linkSourceLocalMedia(mediaModalItem.source_id, localMediaPath.trim());
      } else {
        if (!uploadFile) {
          alert('Please select a video file to upload.');
          setIsAttaching(false);
          return;
        }
        await uploadSourceMedia(mediaModalItem.source_id, uploadFile);
      }

      setMediaModalItem(null);
      setLocalMediaPath('');
      setUploadFile(null);
      setStatusMessage({
        type: 'success',
        text: 'Media attached successfully. Autonomous pipeline has resumed automatically.',
      });

      // Refresh active batch
      if (activeBatch) {
        const fresh = await fetchIntakeBatch(activeBatch.batch_id);
        setActiveBatch(fresh);
      }
      loadBatches(true);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: `Failed to attach media: ${err.message || 'Error'}` });
    } finally {
      setIsAttaching(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Short Completed
          </span>
        );
      case 'awaiting_authorized_media':
      case 'awaiting_media':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="w-3.5 h-3.5" />
            Awaiting Media
          </span>
        );
      case 'rights_pending':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="w-3.5 h-3.5" />
            Rights Pending
          </span>
        );
      case 'rights_rejected':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle className="w-3.5 h-3.5" />
            Rights Rejected
          </span>
        );
      case 'metadata_ready':
      case 'metadata_resolved':
      case 'rights_verified':
      case 'media_ready':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {status.replace('_', ' ').toUpperCase()}
          </span>
        );
      case 'media_resolving':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            Resolving Media
          </span>
        );
      case 'analyzing':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 animate-pulse">
            <Sparkles className="w-3.5 h-3.5" />
            Analyzing Audio/Video
          </span>
        );
      case 'candidates_ready':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Candidates Ready
          </span>
        );
      case 'rendering':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20 animate-pulse">
            <Film className="w-3.5 h-3.5" />
            Rendering 9:16 Short
          </span>
        );
      case 'failed':
      case 'rejected':
      case 'invalid_url':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle className="w-3.5 h-3.5" />
            {status.toUpperCase()}
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-neutral-800 text-neutral-400 border border-neutral-700">
            {status}
          </span>
        );
    }
  };

  const getCategoryBadge = (category?: string) => {
    switch (category) {
      case 'creator_owned':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            Creator-Owned
          </span>
        );
      case 'authorized_partner':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-blue-500/15 text-blue-400 border border-blue-500/30">
            Authorized Partner
          </span>
        );
      case 'licensed_third_party':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-purple-500/15 text-purple-400 border border-purple-500/30">
            Licensed Third-Party
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-neutral-800 text-neutral-400 border border-neutral-700">
            Unresolved
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Banner / Editorial Header */}
      <div className="border-b border-neutral-800 pb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
                <Sparkles className="w-4 h-4" />
              </span>
              <h1 className="text-2xl font-semibold tracking-tight text-white font-serif">
                Autonomous URL Studio
              </h1>
            </div>
            <p className="mt-1 text-sm text-neutral-400">
              Submit YouTube source URLs to automatically resolve metadata, verify rights, analyze visual cuts & audio
              transients, rank candidates, and produce ready-to-publish 9:16 HD Shorts.
            </p>
          </div>
          {onNavigate && (
            <button
              onClick={() => onNavigate('outputs')}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded-lg transition-colors"
            >
              <Film className="w-4 h-4" />
              View Outputs Studio →
            </button>
          )}
        </div>
      </div>

      {/* Status Notifications */}
      {statusMessage && (
        <div
          className={`p-4 rounded-xl border text-sm flex items-start justify-between gap-3 ${
            statusMessage.type === 'success'
              ? 'bg-emerald-950/30 border-emerald-800/40 text-emerald-300'
              : statusMessage.type === 'error'
              ? 'bg-rose-950/30 border-rose-800/40 text-rose-300'
              : 'bg-neutral-900 border-neutral-700 text-neutral-300'
          }`}
        >
          <span>{statusMessage.text}</span>
          <button
            onClick={() => setStatusMessage(null)}
            className="text-xs text-neutral-400 hover:text-white"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Intake Card */}
      <div className="bg-neutral-900/60 border border-neutral-800 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-neutral-200 flex items-center gap-2">
              <LinkIcon className="w-4 h-4 text-amber-400" />
              YouTube Video URLs (1–20 URLs, one per line)
            </label>
            <div className="flex items-center gap-2 text-xs">
              <span className="px-2 py-0.5 rounded bg-neutral-800 text-neutral-300">
                Total: <strong className="text-white">{validationStats.total}</strong>
              </span>
              <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Valid: <strong>{validationStats.validCount}</strong>
              </span>
              {validationStats.duplicates > 0 && (
                <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  Duplicates: <strong>{validationStats.duplicates}</strong>
                </span>
              )}
              {validationStats.invalid > 0 && (
                <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  Invalid: <strong>{validationStats.invalid}</strong>
                </span>
              )}
            </div>
          </div>

          <textarea
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder={`https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://youtu.be/kxyP_8bV0_0
https://www.youtube.com/shorts/5v5v5v5v5v5`}
            rows={5}
            className="w-full bg-neutral-950/80 border border-neutral-800 rounded-xl px-4 py-3 text-sm text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/50 font-mono transition-all"
          />

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
            <input
              type="text"
              value={batchNotes}
              onChange={(e) => setBatchNotes(e.target.value)}
              placeholder="Optional batch label (e.g. 'Morning GTA Stunts Batch')"
              className="w-full sm:w-1/2 bg-neutral-950/60 border border-neutral-800 rounded-lg px-3 py-2 text-xs text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-neutral-700"
            />

            <button
              onClick={handleSubmitBatch}
              disabled={isSubmitting || validationStats.validCount === 0}
              className="w-full sm:w-auto px-6 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:bg-neutral-800 disabled:text-neutral-500 text-neutral-950 font-medium text-sm rounded-xl shadow-lg transition-all flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Initiating Pipeline...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  Run Autonomous Pipeline ({validationStats.validCount})
                </>
              )}
            </button>
          </div>
        </div>

        {/* Visual Pipeline Progression Roadmap */}
        <div className="mt-8 pt-6 border-t border-neutral-800/80">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-4">
            Autonomous Pipeline Stages
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 text-center text-xs">
            {[
              { num: '01', title: 'URL Intake', desc: 'Syntax & Deduplication' },
              { num: '02', title: 'Metadata', desc: 'Compliant oEmbed' },
              { num: '03', title: 'Rights Gate', desc: 'Legal Authorization' },
              { num: '04', title: 'Media Staging', desc: 'Local Storage / Link' },
              { num: '05', title: 'Intelligence', desc: 'Audio & Visual Cuts' },
              { num: '06', title: 'Moment Rank', desc: 'Hook & Retention PTS' },
              { num: '07', title: '9:16 Render', desc: 'FFmpeg 1080x1920' },
              { num: '08', title: 'Verified Short', desc: 'Output Ready' },
            ].map((step) => (
              <div
                key={step.num}
                className="bg-neutral-950/40 border border-neutral-800/60 rounded-lg p-2.5 flex flex-col items-center justify-between"
              >
                <span className="text-[10px] font-mono text-amber-500/80">{step.num}</span>
                <span className="font-medium text-neutral-200 mt-1">{step.title}</span>
                <span className="text-[10px] text-neutral-500 mt-0.5">{step.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Active Batch & Inspection Section */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-amber-400" />
              {activeBatch ? `Batch: ${activeBatch.batch_id}` : 'Recent Batches'}
            </h2>
            {activeBatch && (
              <p className="text-xs text-neutral-400 mt-0.5">
                Submitted {new Date(activeBatch.created_at).toLocaleString()} • {activeBatch.total_submitted} submitted
                ({activeBatch.total_valid} valid, {activeBatch.total_duplicates} duplicates)
              </p>
            )}
          </div>

          <div className="flex items-center gap-2">
            {batches.length > 1 && (
              <select
                value={activeBatch?.batch_id || ''}
                onChange={(e) => {
                  const found = batches.find((b) => b.batch_id === e.target.value);
                  if (found) setActiveBatch(found);
                }}
                className="bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-1.5 text-xs text-neutral-200 focus:outline-none"
              >
                {batches.map((b) => (
                  <option key={b.batch_id} value={b.batch_id}>
                    Batch {b.batch_id.slice(0, 8)}... ({b.total_valid} items)
                  </option>
                ))}
              </select>
            )}

            {activeBatch && (
              <button
                onClick={() => handleTriggerProcess(activeBatch.batch_id)}
                disabled={isProcessing}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 disabled:opacity-50 text-neutral-200 text-xs font-medium rounded-lg border border-neutral-700 transition-colors"
                title="Re-run pipeline for all pending/unresolved items in this batch"
              >
                <RotateCcw className={`w-3.5 h-3.5 ${isProcessing ? 'animate-spin' : ''}`} />
                Process All Items
              </button>
            )}

            <button
              onClick={() => loadBatches(false)}
              disabled={loadingBatches}
              className="p-1.5 bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 rounded-lg text-neutral-400 hover:text-white transition-colors"
              title="Refresh Batches"
            >
              <RefreshCw className={`w-4 h-4 ${loadingBatches ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Batch Items Table */}
        {activeBatch ? (
          <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl overflow-hidden shadow-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-neutral-800 bg-neutral-950/50 text-xs font-semibold uppercase tracking-wider text-neutral-400">
                    <th className="px-5 py-3.5">Video & Channel</th>
                    <th className="px-5 py-3.5">Category & Rights</th>
                    <th className="px-5 py-3.5">Pipeline Stage</th>
                    <th className="px-5 py-3.5">Diagnostic / Blocker</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/60">
                  {activeBatch.items.map((item) => (
                    <tr key={item.id} className="hover:bg-neutral-800/30 transition-colors">
                      <td className="px-5 py-4">
                        <div className="flex flex-col gap-0.5">
                          <span className="font-medium text-white truncate max-w-sm" title={item.source_title || item.video_id}>
                            {item.source_title || `Video ${item.video_id || item.raw_url}`}
                          </span>
                          <div className="flex items-center gap-2 text-xs text-neutral-400">
                            {item.creator_name ? (
                              <span className="text-amber-400/90 font-medium">{item.creator_name}</span>
                            ) : (
                              <span className="text-neutral-500">Unlinked Channel</span>
                            )}
                            <span>•</span>
                            <span className="font-mono text-[11px] text-neutral-400">{item.video_id || 'N/A'}</span>
                            <span>•</span>
                            <a
                              href={item.canonical_url || item.raw_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-amber-400 hover:underline inline-flex items-center gap-0.5 text-[11px]"
                            >
                              URL
                              <ExternalLink className="w-2.5 h-2.5" />
                            </a>
                          </div>
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <div className="flex flex-col gap-1 items-start">
                          {getCategoryBadge(item.source_category)}
                          <div className="flex items-center gap-1.5 text-[11px]">
                            <span
                              className={
                                item.commercial_use_allowed
                                  ? 'text-emerald-400 font-medium'
                                  : 'text-neutral-400'
                              }
                            >
                              {item.commercial_use_allowed ? 'Commercial: Allowed' : 'Commercial: Restricted'}
                            </span>
                          </div>
                        </div>
                      </td>

                      <td className="px-5 py-4">{getStatusBadge(item.status)}</td>

                      <td className="px-5 py-4">
                        {item.status === 'completed' ? (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-emerald-400 font-medium">
                              9:16 Short Rendered
                            </span>
                            {onNavigate && (
                              <button
                                onClick={() => onNavigate('outputs')}
                                className="text-xs text-amber-400 hover:underline font-medium"
                              >
                                View Output →
                              </button>
                            )}
                          </div>
                        ) : item.error_message ? (
                          <span
                            className="text-xs text-rose-300 font-mono line-clamp-2 max-w-xs"
                            title={item.error_message}
                          >
                            {item.error_message.includes('mismatch') || item.error_message.includes('Ownership') ? (
                              <span className="font-semibold text-rose-400 flex items-center gap-1">
                                <AlertCircle className="w-3 h-3 inline shrink-0" />
                                {item.error_message}
                              </span>
                            ) : (
                              item.error_message
                            )}
                          </span>
                        ) : ['awaiting_media', 'awaiting_authorized_media'].includes(item.status) ? (
                          <span className="text-xs text-amber-300/90 font-mono">
                            Awaiting master video file in connected vault or asset mapping
                          </span>
                        ) : (
                          <span className="text-xs text-neutral-400 font-mono">In pipeline</span>
                        )}
                      </td>

                      <td className="px-5 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {['awaiting_media', 'awaiting_authorized_media'].includes(item.status) && item.source_id && (
                            <button
                              onClick={() => {
                                setMediaModalItem(item);
                                setLocalMediaPath('');
                                setUploadFile(null);
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-lg text-xs font-medium transition-colors"
                            >
                              <HardDrive className="w-3.5 h-3.5" />
                              Attach Media
                            </button>
                          )}

                          {['failed', 'rejected', 'rights_rejected', 'rights_pending', 'awaiting_media', 'awaiting_authorized_media'].includes(item.status) && (
                            <button
                              onClick={() => handleRetryItem(item.id)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded-lg text-xs transition-colors"
                              title="Retry processing this URL"
                            >
                              <RotateCcw className="w-3 h-3" />
                              Retry
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="bg-neutral-900/40 border border-neutral-800/80 rounded-2xl p-12 text-center">
            <Film className="w-10 h-10 text-neutral-600 mx-auto mb-3" />
            <h3 className="text-sm font-medium text-neutral-300">No batches submitted yet</h3>
            <p className="text-xs text-neutral-500 mt-1">
              Enter YouTube URLs in the studio above to run your first autonomous Shorts generation batch.
            </p>
          </div>
        )}
      </div>

      {/* Attach Media Modal */}
      {mediaModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-neutral-800">
              <div className="flex items-center gap-2 text-white font-semibold">
                <HardDrive className="w-5 h-5 text-amber-400" />
                Attach Authorized Source Media
              </div>
              <button
                onClick={() => setMediaModalItem(null)}
                className="text-neutral-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="py-4 space-y-4">
              <p className="text-xs text-neutral-300">
                To analyze video and audio without third-party stream scraping, attach the authorized original video
                file for:
              </p>
              <div className="p-3 bg-neutral-950 rounded-lg border border-neutral-800 text-xs font-mono text-neutral-300">
                {mediaModalItem.source_title || mediaModalItem.video_id} (Source #{mediaModalItem.source_id})
              </div>

              {/* Mode Toggle */}
              <div className="flex rounded-lg bg-neutral-950 p-1 border border-neutral-800">
                <button
                  type="button"
                  onClick={() => setMediaModalMode('link')}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    mediaModalMode === 'link'
                      ? 'bg-amber-500 text-neutral-950'
                      : 'text-neutral-400 hover:text-white'
                  }`}
                >
                  Link Local Staged File
                </button>
                <button
                  type="button"
                  onClick={() => setMediaModalMode('upload')}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${
                    mediaModalMode === 'upload'
                      ? 'bg-amber-500 text-neutral-950'
                      : 'text-neutral-400 hover:text-white'
                  }`}
                >
                  Direct File Upload
                </button>
              </div>

              {mediaModalMode === 'link' ? (
                <div className="space-y-2">
                  <label className="text-xs font-medium text-neutral-300">
                    Absolute or Workspace-relative Video Path (.mp4, .mov, etc.)
                  </label>
                  <input
                    type="text"
                    value={localMediaPath}
                    onChange={(e) => setLocalMediaPath(e.target.value)}
                    placeholder="e.g. data/media/stunt_raw.mp4 or C:\Footage\video.mp4"
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-3 py-2 text-xs text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-amber-500/50 font-mono"
                  />
                  <p className="text-[11px] text-neutral-500">
                    File must exist and have non-zero size. Once linked, the autonomous pipeline resumes automatically.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <label className="text-xs font-medium text-neutral-300">
                    Select Local Video File (.mp4, .mov)
                  </label>
                  <input
                    type="file"
                    accept="video/mp4,video/quicktime,video/x-matroska,video/webm"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    className="w-full text-xs text-neutral-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-neutral-800 file:text-neutral-200 hover:file:bg-neutral-700 cursor-pointer"
                  />
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-neutral-800">
              <button
                onClick={() => setMediaModalItem(null)}
                className="px-4 py-2 text-xs font-medium text-neutral-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleAttachMedia}
                disabled={isAttaching}
                className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-neutral-950 text-xs font-medium rounded-lg disabled:opacity-50 transition-colors flex items-center gap-1.5"
              >
                {isAttaching ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Attaching & Resuming...
                  </>
                ) : (
                  'Confirm & Resume Pipeline'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
