import React, { useEffect, useState } from 'react';
import {
  Radio,
  Plus,
  Play,
  ShieldCheck,
  ShieldAlert,
  Trash2,
  RefreshCw,
  ExternalLink,
  Upload,
  CheckCircle2,
  XCircle,
  Clock,
  HardDrive,
  AlertTriangle,
  ListPlus,
  Key,
} from 'lucide-react';
import {
  createCreator,
  deleteCreator,
  discoverCreatorVideos,
  fetchCreators,
  fetchVideoSources,
  importManualSource,
  runGlobalDiscovery,
  updateCreator,
  updateSourceRights,
  fetchIntakeBatches,
  submitBatchIntake,
  uploadSourceMedia,
  linkSourceLocalMedia,
} from '@/lib/api';
import { Creator, VideoSource, BatchIntakeResponse } from '@/types';
import { CreatorOAuthVaultModal } from './CreatorOAuthVaultModal';

export const DiscoveryView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'sources' | 'creators' | 'batches'>('sources');
  const [creators, setCreators] = useState<Creator[]>([]);
  const [sources, setSources] = useState<VideoSource[]>([]);
  const [batches, setBatches] = useState<BatchIntakeResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [discovering, setDiscovering] = useState<boolean>(false);
  const [filterEligible, setFilterEligible] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modals
  const [showCreatorModal, setShowCreatorModal] = useState<boolean>(false);
  const [showImportModal, setShowImportModal] = useState<boolean>(false);
  const [editingRightsSource, setEditingRightsSource] = useState<VideoSource | null>(null);
  const [attachMediaSource, setAttachMediaSource] = useState<VideoSource | null>(null);
  const [selectedManageCreator, setSelectedManageCreator] = useState<Creator | null>(null);

  // Batch Intake State
  const [batchInput, setBatchInput] = useState<string>('');
  const [batchNotes, setBatchNotes] = useState<string>('');
  const [submittingBatch, setSubmittingBatch] = useState<boolean>(false);
  const [activeBatchResult, setActiveBatchResult] = useState<BatchIntakeResponse | null>(null);

  // Attach Media State
  const [attachMode, setAttachMode] = useState<'upload' | 'link'>('upload');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localPathInput, setLocalPathInput] = useState<string>('');
  const [attachingMedia, setAttachingMedia] = useState<boolean>(false);

  // Creator form state
  const [newCreator, setNewCreator] = useState({
    name: '',
    channel_id: '',
    channel_handle: '',
    content_category: 'GTA 6 Gameplay',
    permission_tier: 'authorized_partner',
    notes: '',
  });

  // Manual import form state
  const [newSource, setNewSource] = useState({
    video_id: '',
    title: '',
    source_url: '',
    description: '',
    duration_seconds: 300,
    is_own_gameplay: true,
    attribution_text: 'Astro Rebel Gameplay Recording',
  });

  // Rights form state
  const [rightsForm, setRightsForm] = useState({
    permission_status: 'authorized',
    commercial_use_allowed: true,
    allowed_editing_scope: 'transformative_shorts',
    attribution_required: true,
    attribution_text: '',
    license_documentation: '',
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const [cData, sData, bData] = await Promise.all([
        fetchCreators(),
        fetchVideoSources(undefined, filterEligible),
        fetchIntakeBatches(20),
      ]);
      setCreators(cData);
      setSources(sData);
      setBatches(bData);
      setMessage(null);
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to load discovery data',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitBatch = async (e: React.FormEvent) => {
    e.preventDefault();
    const urls = batchInput
      .split('\n')
      .map((u) => u.trim())
      .filter((u) => u.length > 0);

    if (urls.length === 0) {
      setMessage({ type: 'error', text: 'Please enter at least one YouTube URL.' });
      return;
    }
    if (urls.length > 20) {
      setMessage({ type: 'error', text: 'Batch exceeds maximum limit of 20 URLs.' });
      return;
    }

    setSubmittingBatch(true);
    setMessage(null);
    try {
      const res = await submitBatchIntake(urls, batchNotes || undefined);
      setActiveBatchResult(res);
      setBatchInput('');
      setBatchNotes('');
      setMessage({
        type: 'success',
        text: `Batch ${res.batch_id.slice(0, 8)} processed: ${res.total_valid} valid, ${res.total_duplicates} duplicates, ${res.total_invalid} invalid.`,
      });
      await loadData();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Batch intake failed.' });
    } finally {
      setSubmittingBatch(false);
    }
  };

  const handleAttachMediaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!attachMediaSource) return;

    setAttachingMedia(true);
    setMessage(null);
    try {
      if (attachMode === 'upload') {
        if (!selectedFile) {
          throw new Error('Please select a video file to upload.');
        }
        await uploadSourceMedia(attachMediaSource.id, selectedFile);
      } else {
        if (!localPathInput.trim()) {
          throw new Error('Please enter a local file path.');
        }
        await linkSourceLocalMedia(attachMediaSource.id, localPathInput.trim());
      }
      setMessage({
        type: 'success',
        text: `Media successfully associated with "${attachMediaSource.title}".`,
      });
      setAttachMediaSource(null);
      setSelectedFile(null);
      setLocalPathInput('');
      await loadData();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to attach media.' });
    } finally {
      setAttachingMedia(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [filterEligible]);

  const handleGlobalDiscovery = async () => {
    setDiscovering(true);
    setMessage(null);
    try {
      const result = await runGlobalDiscovery();
      setMessage({
        type: 'success',
        text: `Discovery sweep completed: ${result.videos_discovered} new videos ingested, ${result.duplicates_skipped} duplicates skipped.`,
      });
      await loadData();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Discovery sweep failed',
      });
    } finally {
      setDiscovering(false);
    }
  };

  const handleChannelDiscover = async (creator: Creator) => {
    setDiscovering(true);
    try {
      const newItems = await discoverCreatorVideos(creator.id);
      setMessage({
        type: 'success',
        text: `Ingested ${newItems.length} new videos from ${creator.name}.`,
      });
      await loadData();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : `Failed to discover from ${creator.name}`,
      });
    } finally {
      setDiscovering(false);
    }
  };

  const handleCreateCreator = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createCreator({
        ...newCreator,
        approval_status: 'approved',
        is_monitored: true,
      });
      setShowCreatorModal(false);
      setNewCreator({
        name: '',
        channel_id: '',
        channel_handle: '',
        content_category: 'GTA 6 Gameplay',
        permission_tier: 'authorized_partner',
        notes: '',
      });
      setMessage({ type: 'success', text: 'Creator registered successfully.' });
      await loadData();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to register creator',
      });
    }
  };

  const handleManualImport = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await importManualSource(newSource);
      setShowImportModal(false);
      setNewSource({
        video_id: '',
        title: '',
        source_url: '',
        description: '',
        duration_seconds: 300,
        is_own_gameplay: true,
        attribution_text: 'Astro Rebel Gameplay Recording',
      });
      setMessage({ type: 'success', text: 'Video source registered into catalog.' });
      await loadData();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to import video source',
      });
    }
  };

  const handleDeleteCreator = async (id: number) => {
    if (!window.confirm('Remove this creator channel from monitoring?')) return;
    try {
      await deleteCreator(id);
      await loadData();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to remove creator',
      });
    }
  };

  const handleToggleMonitoring = async (creator: Creator) => {
    try {
      await updateCreator(creator.id, { is_monitored: !creator.is_monitored });
      await loadData();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to update monitoring status',
      });
    }
  };

  const openRightsEditor = (src: VideoSource) => {
    setEditingRightsSource(src);
    if (src.rights) {
      setRightsForm({
        permission_status: src.rights.permission_status,
        commercial_use_allowed: src.rights.commercial_use_allowed,
        allowed_editing_scope: src.rights.allowed_editing_scope,
        attribution_required: src.rights.attribution_required,
        attribution_text: src.rights.attribution_text || '',
        license_documentation: src.rights.license_documentation || '',
      });
    } else {
      setRightsForm({
        permission_status: 'pending',
        commercial_use_allowed: false,
        allowed_editing_scope: 'transformative_shorts',
        attribution_required: true,
        attribution_text: '',
        license_documentation: '',
      });
    }
  };

  const handleSaveRights = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingRightsSource) return;
    try {
      await updateSourceRights(editingRightsSource.id, rightsForm);
      setEditingRightsSource(null);
      setMessage({ type: 'success', text: 'Rights and permission record updated.' });
      await loadData();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to update rights',
      });
    }
  };

  const formatDuration = (seconds: number) => {
    if (!seconds) return '--:--';
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const eligibleCount = sources.filter((s) => s.is_eligible).length;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Workspace Top Header & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-vantyx-border pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono tracking-widest text-vantyx-accent uppercase mb-1">
            <span>Milestone 02</span>
            <span>•</span>
            <span>Source Discovery & Rights Intelligence</span>
          </div>
          <h2 className="text-xl font-light text-vantyx-textPrimary">
            GTA 6 Content Ingestion & Rights Governance
          </h2>
          <p className="text-xs text-vantyx-textSecondary mt-1">
            Monitor verified gameplay creators, ingest long-form sources, and strictly validate
            commercial rights before media can enter AI analysis.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleGlobalDiscovery}
            disabled={discovering || creators.length === 0}
            className="flex items-center gap-2 rounded border border-vantyx-accent bg-vantyx-accent/10 px-3.5 py-2 text-xs font-mono font-medium text-vantyx-accent hover:bg-vantyx-accent hover:text-black transition-all disabled:opacity-40"
          >
            <RefreshCw size={13} className={discovering ? 'animate-spin' : ''} />
            {discovering ? 'Polling Feeds...' : 'Run Discovery Sweep'}
          </button>

          <button
            onClick={() => setShowImportModal(true)}
            className="flex items-center gap-1.5 rounded border border-vantyx-border bg-vantyx-surface px-3 py-2 text-xs font-medium text-vantyx-textSecondary hover:text-vantyx-textPrimary hover:bg-vantyx-surfaceElevated transition-all"
          >
            <Upload size={13} />
            <span>Manual Import</span>
          </button>

          <button
            onClick={() => setShowCreatorModal(true)}
            className="flex items-center gap-1.5 rounded border border-vantyx-border bg-vantyx-surfaceElevated px-3 py-2 text-xs font-medium text-vantyx-textPrimary hover:border-vantyx-accent/50 transition-all"
          >
            <Plus size={14} className="text-vantyx-accent" />
            <span>Add Creator</span>
          </button>
        </div>
      </div>

      {/* Notifications / Alerts */}
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

      {/* Metric Cards Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded border border-vantyx-border bg-vantyx-surface p-4">
          <span className="text-[11px] font-mono uppercase text-vantyx-textMuted">Monitored Creators</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono font-light text-vantyx-textPrimary">
              {creators.filter((c) => c.is_monitored).length}
            </span>
            <span className="text-xs text-vantyx-textMuted font-mono">/ {creators.length} total</span>
          </div>
        </div>

        <div className="rounded border border-vantyx-border bg-vantyx-surface p-4">
          <span className="text-[11px] font-mono uppercase text-vantyx-textMuted">Discovered Sources</span>
          <div className="mt-2 text-2xl font-mono font-light text-vantyx-textPrimary">{sources.length}</div>
        </div>

        <div className="rounded border border-vantyx-border bg-vantyx-surface p-4">
          <span className="text-[11px] font-mono uppercase text-vantyx-textMuted">Pipeline Eligible</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-mono font-light text-emerald-400">{eligibleCount}</span>
            <span className="text-xs text-vantyx-textMuted font-mono">
              ({sources.length > 0 ? Math.round((eligibleCount / sources.length) * 100) : 0}%)
            </span>
          </div>
        </div>

        <div className="rounded border border-vantyx-border bg-vantyx-surface p-4">
          <span className="text-[11px] font-mono uppercase text-vantyx-textMuted">Commercial Rights Gate</span>
          <div className="mt-2 flex items-center gap-1.5 text-xs font-mono text-vantyx-accent">
            <ShieldCheck size={16} /> Strict Enforcement
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center justify-between border-b border-vantyx-border">
        <div className="flex gap-6">
          <button
            onClick={() => setActiveTab('sources')}
            className={`pb-3 text-xs font-mono transition-colors relative ${
              activeTab === 'sources'
                ? 'text-vantyx-accent font-medium'
                : 'text-vantyx-textMuted hover:text-vantyx-textPrimary'
            }`}
          >
            Video Catalog ({sources.length})
            {activeTab === 'sources' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-vantyx-accent" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('creators')}
            className={`pb-3 text-xs font-mono transition-colors relative ${
              activeTab === 'creators'
                ? 'text-vantyx-accent font-medium'
                : 'text-vantyx-textMuted hover:text-vantyx-textPrimary'
            }`}
          >
            Registered Creators ({creators.length})
            {activeTab === 'creators' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-vantyx-accent" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('batches')}
            className={`pb-3 text-xs font-mono transition-colors relative ${
              activeTab === 'batches'
                ? 'text-vantyx-accent font-medium'
                : 'text-vantyx-textMuted hover:text-vantyx-textPrimary'
            }`}
          >
            Batch URL Intake ({batches.length})
            {activeTab === 'batches' && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-vantyx-accent" />
            )}
          </button>
        </div>

        {activeTab === 'sources' && (
          <label className="flex items-center gap-2 text-xs font-mono text-vantyx-textSecondary cursor-pointer mb-2">
            <input
              type="checkbox"
              checked={filterEligible}
              onChange={(e) => setFilterEligible(e.target.checked)}
              className="rounded border-vantyx-border bg-vantyx-surface text-vantyx-accent focus:ring-0"
            />
            <span>Show Only Legally Eligible Videos</span>
          </label>
        )}
      </div>

      {/* Tab Content */}
      {loading ? (
        <div className="py-16 text-center text-xs font-mono text-vantyx-textMuted">
          Synchronizing discovery catalog...
        </div>
      ) : activeTab === 'sources' ? (
        /* Sources Table */
        <div className="space-y-4">
          {sources.length === 0 ? (
            <div className="rounded border border-vantyx-border bg-vantyx-surface/40 p-12 text-center space-y-3">
              <Radio size={28} className="mx-auto text-vantyx-textMuted" />
              <h3 className="text-sm font-medium text-vantyx-textPrimary">No Video Sources Found</h3>
              <p className="text-xs text-vantyx-textMuted max-w-md mx-auto leading-relaxed">
                Register a GTA creator channel or import your own gameplay recordings to begin autonomous
                intelligence analysis.
              </p>
              <div className="pt-2 flex justify-center gap-3">
                <button
                  onClick={() => setShowCreatorModal(true)}
                  className="rounded border border-vantyx-border bg-vantyx-surface px-3 py-1.5 text-xs text-vantyx-textPrimary hover:border-vantyx-accent"
                >
                  Register Creator
                </button>
                <button
                  onClick={() => setShowImportModal(true)}
                  className="rounded border border-vantyx-accent/50 bg-vantyx-accent/10 px-3 py-1.5 text-xs text-vantyx-accent"
                >
                  Import Own Gameplay
                </button>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto rounded border border-vantyx-border bg-vantyx-surface">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-vantyx-border bg-vantyx-surfaceElevated/50 text-[11px] font-mono uppercase text-vantyx-textMuted">
                  <tr>
                    <th className="py-3 px-4">Video</th>
                    <th className="py-3 px-4">Creator / Source</th>
                    <th className="py-3 px-4">Duration</th>
                    <th className="py-3 px-4">Media Asset</th>
                    <th className="py-3 px-4">Permission Status</th>
                    <th className="py-3 px-4">Commercial Rights</th>
                    <th className="py-3 px-4">Eligibility Gate</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-vantyx-border font-mono">
                  {sources.map((src) => {
                    const statusVal = src.rights?.permission_status || 'pending';
                    const mediaStatus = src.media_status || (src.local_video_path ? 'ready' : 'awaiting_media');
                    return (
                      <tr key={src.id} className="hover:bg-vantyx-surfaceElevated/30 transition-colors">
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-3 max-w-md">
                            {src.thumbnail_url ? (
                              <img
                                src={src.thumbnail_url}
                                alt=""
                                className="h-10 w-16 object-cover rounded border border-vantyx-border shrink-0"
                              />
                            ) : (
                              <div className="h-10 w-16 bg-vantyx-bg border border-vantyx-border rounded flex items-center justify-center shrink-0">
                                <Play size={12} className="text-vantyx-textMuted" />
                              </div>
                            )}
                            <div className="truncate">
                              <a
                                href={src.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="font-sans text-xs text-vantyx-textPrimary hover:text-vantyx-accent truncate block flex items-center gap-1"
                              >
                                {src.title}
                                <ExternalLink size={10} className="shrink-0 text-vantyx-textMuted" />
                              </a>
                              <span className="text-[10px] text-vantyx-textMuted font-mono">
                                ID: {src.video_id}
                              </span>
                            </div>
                          </div>
                        </td>

                        <td className="py-3 px-4 text-vantyx-textSecondary">
                          {src.creator_name || (src.rights?.permission_status === 'own_gameplay' ? 'Astro Rebel (Own)' : 'Unlinked')}
                        </td>

                        <td className="py-3 px-4 text-vantyx-textMuted">
                          <span className="flex items-center gap-1">
                            <Clock size={11} /> {formatDuration(src.duration_seconds)}
                          </span>
                        </td>

                        <td className="py-3 px-4">
                          {mediaStatus === 'ready' ? (
                            <span
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] uppercase border border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                              title={src.local_video_path || ''}
                            >
                              <HardDrive size={10} /> Media Ready
                            </span>
                          ) : mediaStatus === 'missing' ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] uppercase border border-rose-500/30 text-rose-400 bg-rose-500/10">
                              <AlertTriangle size={10} /> File Missing
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] uppercase border border-amber-500/30 text-amber-400 bg-amber-500/10">
                              <Clock size={10} /> Awaiting File
                            </span>
                          )}
                        </td>

                        <td className="py-3 px-4">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[10px] uppercase border ${
                              statusVal === 'authorized' || statusVal === 'own_gameplay'
                                ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10'
                                : statusVal === 'rejected' || statusVal === 'revoked'
                                ? 'border-rose-500/30 text-rose-400 bg-rose-500/10'
                                : 'border-vantyx-accent/30 text-vantyx-accent bg-vantyx-accent/10'
                            }`}
                          >
                            {statusVal.replace('_', ' ')}
                          </span>
                        </td>

                        <td className="py-3 px-4">
                          {src.rights?.commercial_use_allowed ? (
                            <span className="flex items-center gap-1 text-emerald-400 text-[11px]">
                              <CheckCircle2 size={13} /> Allowed
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-rose-400 text-[11px]">
                              <XCircle size={13} /> Forbidden
                            </span>
                          )}
                        </td>

                        <td className="py-3 px-4">
                          {src.is_eligible ? (
                            <span className="flex items-center gap-1 text-emerald-400 font-semibold text-[11px]">
                              <ShieldCheck size={14} /> ELIGIBLE
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-vantyx-textMuted text-[11px]">
                              <ShieldAlert size={14} className="text-vantyx-accent" /> BLOCKED
                            </span>
                          )}
                        </td>

                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => {
                                setAttachMediaSource(src);
                                setSelectedFile(null);
                                setLocalPathInput(src.local_video_path || '');
                              }}
                              className="rounded border border-vantyx-border px-2 py-1 text-[11px] text-vantyx-accent hover:border-vantyx-accent transition-colors"
                              title="Attach authorized video file"
                            >
                              Attach Media
                            </button>
                            <button
                              onClick={() => openRightsEditor(src)}
                              className="rounded border border-vantyx-border px-2 py-1 text-[11px] text-vantyx-textSecondary hover:border-vantyx-accent hover:text-vantyx-textPrimary transition-colors"
                            >
                              Rights
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : activeTab === 'creators' ? (
        /* Creators Table */
        <div className="space-y-4">
          <div className="overflow-x-auto rounded border border-vantyx-border bg-vantyx-surface">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-vantyx-border bg-vantyx-surfaceElevated/50 text-[11px] font-mono uppercase text-vantyx-textMuted">
                <tr>
                  <th className="py-3 px-4">Creator / Channel</th>
                  <th className="py-3 px-4">Channel ID</th>
                  <th className="py-3 px-4">OAuth / Ownership</th>
                  <th className="py-3 px-4">Content Category</th>
                  <th className="py-3 px-4">Permission Tier</th>
                  <th className="py-3 px-4">Monitoring</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-vantyx-border font-mono">
                {creators.map((c) => (
                  <tr key={c.id} className="hover:bg-vantyx-surfaceElevated/30 transition-colors">
                    <td className="py-3 px-4">
                      <div>
                        <span className="font-sans font-medium text-vantyx-textPrimary">{c.name}</span>
                        {c.channel_handle && (
                          <span className="block text-[11px] text-vantyx-textMuted font-mono">
                            {c.channel_handle}
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="py-3 px-4 text-vantyx-textMuted text-[11px]">
                      <code className="text-vantyx-textSecondary">{c.channel_id}</code>
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5">
                        {c.oauth_status === 'connected' ? (
                          <span className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded font-mono font-semibold">
                            <CheckCircle2 size={10} />
                            VERIFIED
                          </span>
                        ) : c.oauth_status === 'expired' ? (
                          <span className="flex items-center gap-1 text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded font-mono font-semibold">
                            <Clock size={10} />
                            EXPIRED
                          </span>
                        ) : c.oauth_status === 'revoked' ? (
                          <span className="flex items-center gap-1 text-[10px] text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded font-mono font-semibold">
                            <XCircle size={10} />
                            REVOKED
                          </span>
                        ) : (
                          <span className="text-[10px] text-neutral-400 bg-neutral-900 border border-neutral-700 px-2 py-0.5 rounded font-mono">
                            UNLINKED
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="py-3 px-4 text-vantyx-textSecondary">{c.content_category}</td>

                    <td className="py-3 px-4">
                      <span className="border border-vantyx-border px-2 py-0.5 rounded text-[10px] text-vantyx-accent uppercase">
                        {c.permission_tier.replace(/_/g, ' ')}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <button
                        onClick={() => handleToggleMonitoring(c)}
                        className={`px-2.5 py-0.5 rounded text-[10px] uppercase font-mono border transition-all ${
                          c.is_monitored
                            ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10'
                            : 'border-neutral-700 text-neutral-500 bg-neutral-900'
                        }`}
                      >
                        {c.is_monitored ? 'Active' : 'Paused'}
                      </button>
                    </td>

                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setSelectedManageCreator(c)}
                          className="rounded border border-vantyx-accent/40 bg-vantyx-accent/10 px-2 py-1 text-[11px] text-vantyx-accent hover:bg-vantyx-accent hover:text-vantyx-background font-medium transition-colors flex items-center gap-1"
                          title="Manage Google OAuth, Channel Ownership, and Master Media Vault"
                        >
                          <Key size={11} />
                          OAuth & Vault
                        </button>
                        <button
                          onClick={() => handleChannelDiscover(c)}
                          disabled={discovering}
                          className="rounded border border-vantyx-border px-2 py-1 text-[11px] text-vantyx-accent hover:border-vantyx-accent/60"
                          title="Poll latest videos from this channel"
                        >
                          Discover
                        </button>
                        <button
                          onClick={() => handleDeleteCreator(c.id)}
                          className="p-1 rounded text-vantyx-textMuted hover:text-rose-400"
                          title="Remove creator"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Batches Tab */
        <div className="space-y-6">
          {/* Batch Submission Card */}
          <div className="rounded border border-vantyx-border bg-vantyx-surface p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-3">
              <div className="flex items-center gap-2">
                <ListPlus size={16} className="text-vantyx-accent" />
                <h3 className="text-sm font-semibold text-vantyx-textPrimary">Batch YouTube URL Intake</h3>
              </div>
              <span className="font-mono text-xs text-vantyx-textMuted">Max 20 URLs per batch</span>
            </div>

            <p className="text-xs text-vantyx-textMuted leading-relaxed">
              Submit multiple gameplay URLs for autonomous intake. VANTYX will canonicalize each link, extract the 11-character video ID, check duplicate registers, enforce legal rights gates, and ready eligible sources for authorized media attachment.
            </p>

            <form onSubmit={handleSubmitBatch} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-vantyx-textMuted mb-1.5">
                  YouTube URLs (One URL per line)
                </label>
                <textarea
                  rows={5}
                  required
                  placeholder={"https://www.youtube.com/watch?v=dQw4w9WgXcQ\nhttps://youtu.be/dQw4w9WgXcQ\nhttps://www.youtube.com/shorts/dQw4w9WgXcQ"}
                  value={batchInput}
                  onChange={(e) => setBatchInput(e.target.value)}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg p-3 font-mono text-xs text-vantyx-textPrimary placeholder:text-vantyx-textMuted/40 focus:border-vantyx-accent focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-vantyx-textMuted mb-1.5">
                  Batch Ingestion Notes / Mission Tag (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Morning creator intake sweep - Mission 02"
                  value={batchNotes}
                  onChange={(e) => setBatchNotes(e.target.value)}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-xs font-mono text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                />
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={submittingBatch || !batchInput.trim()}
                  className="flex items-center gap-2 rounded bg-vantyx-accent px-4 py-2 text-xs font-mono font-medium text-black hover:bg-vantyx-accentHover transition-colors disabled:opacity-50"
                >
                  <RefreshCw size={12} className={submittingBatch ? 'animate-spin' : ''} />
                  <span>{submittingBatch ? 'Validating Batch...' : 'Submit Batch Ingestion'}</span>
                </button>
              </div>
            </form>
          </div>

          {/* Active / Latest Batch Breakdown */}
          {activeBatchResult && (
            <div className="rounded border border-vantyx-accent/40 bg-vantyx-surface p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-vantyx-border pb-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 size={16} className="text-emerald-400" />
                  <h3 className="text-sm font-semibold text-vantyx-textPrimary">
                    Intake Batch Results ({activeBatchResult.batch_id.slice(0, 8)})
                  </h3>
                </div>
                <div className="flex items-center gap-3 text-xs font-mono">
                  <span className="text-vantyx-textMuted">Submitted: {activeBatchResult.total_submitted}</span>
                  <span className="text-emerald-400 font-semibold">Valid: {activeBatchResult.total_valid}</span>
                  <span className="text-amber-400">Duplicates: {activeBatchResult.total_duplicates}</span>
                  <span className="text-rose-400">Invalid: {activeBatchResult.total_invalid}</span>
                </div>
              </div>

              <div className="overflow-x-auto rounded border border-vantyx-border bg-vantyx-bg">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="border-b border-vantyx-border bg-vantyx-surfaceElevated/50 text-[10px] uppercase text-vantyx-textMuted">
                    <tr>
                      <th className="py-2.5 px-3">Video ID</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Canonical URL</th>
                      <th className="py-2.5 px-3">Permission</th>
                      <th className="py-2.5 px-3">Details / Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-vantyx-border">
                    {activeBatchResult.items.map((item) => (
                      <tr key={item.id} className="hover:bg-vantyx-surfaceElevated/20">
                        <td className="py-2.5 px-3 font-semibold text-vantyx-textPrimary">
                          {item.video_id || '--'}
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`inline-block px-1.5 py-0.5 rounded text-[10px] uppercase border ${
                              item.status === 'imported'
                                ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10'
                                : item.status === 'duplicate'
                                ? 'border-amber-500/30 text-amber-400 bg-amber-500/10'
                                : 'border-rose-500/30 text-rose-400 bg-rose-500/10'
                            }`}
                          >
                            {item.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-vantyx-textMuted truncate max-w-xs">
                          {item.canonical_url || item.raw_url}
                        </td>
                        <td className="py-2.5 px-3 text-vantyx-textSecondary">
                          {item.permission_status || 'unverified'}
                        </td>
                        <td className="py-2.5 px-3 text-vantyx-textMuted truncate max-w-xs">
                          {item.error_message || (item.source_title ? `Source #${item.source_id}: ${item.source_title}` : 'Registered successfully')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Historical Batches Queue */}
          <div className="rounded border border-vantyx-border bg-vantyx-surface p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-3">
              <h3 className="text-sm font-semibold text-vantyx-textPrimary">Recent Intake Batches</h3>
              <span className="font-mono text-xs text-vantyx-textMuted">{batches.length} logged batches</span>
            </div>

            {batches.length === 0 ? (
              <p className="py-6 text-center text-xs text-vantyx-textMuted">
                No batches submitted yet. Paste YouTube URLs above to execute batch intake.
              </p>
            ) : (
              <div className="overflow-x-auto rounded border border-vantyx-border bg-vantyx-bg">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="border-b border-vantyx-border bg-vantyx-surfaceElevated/50 text-[10px] uppercase text-vantyx-textMuted">
                    <tr>
                      <th className="py-2.5 px-3">Batch ID</th>
                      <th className="py-2.5 px-3">Created</th>
                      <th className="py-2.5 px-3">Total</th>
                      <th className="py-2.5 px-3">Valid</th>
                      <th className="py-2.5 px-3">Duplicates</th>
                      <th className="py-2.5 px-3">Invalid</th>
                      <th className="py-2.5 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-vantyx-border">
                    {batches.map((b) => (
                      <tr key={b.batch_id} className="hover:bg-vantyx-surfaceElevated/20">
                        <td className="py-2.5 px-3 font-semibold text-vantyx-textPrimary">
                          {b.batch_id.slice(0, 8)}...
                        </td>
                        <td className="py-2.5 px-3 text-vantyx-textMuted">
                          {new Date(b.created_at).toLocaleString()}
                        </td>
                        <td className="py-2.5 px-3">{b.total_submitted}</td>
                        <td className="py-2.5 px-3 text-emerald-400 font-semibold">{b.total_valid}</td>
                        <td className="py-2.5 px-3 text-amber-400">{b.total_duplicates}</td>
                        <td className="py-2.5 px-3 text-rose-400">{b.total_invalid}</td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            onClick={() => setActiveBatchResult(b)}
                            className="rounded border border-vantyx-border px-2 py-0.5 text-[10px] text-vantyx-accent hover:border-vantyx-accent"
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ----------------- Register Creator Modal ----------------- */}
      {showCreatorModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-lg border border-vantyx-border bg-vantyx-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-3">
              <h3 className="text-sm font-semibold text-vantyx-textPrimary">Register GTA Creator Channel</h3>
              <button onClick={() => setShowCreatorModal(false)} className="text-vantyx-textMuted hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateCreator} className="space-y-3.5 text-xs font-mono">
              <div>
                <label className="block text-vantyx-textMuted mb-1">Creator / Channel Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Vice City Legend"
                  value={newCreator.name}
                  onChange={(e) => setNewCreator({ ...newCreator, name: e.target.value })}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-vantyx-textMuted mb-1">YouTube Channel ID (e.g. UC...)</label>
                <input
                  type="text"
                  required
                  placeholder="UCxxxxxxxxxxxxxxxxxxxx"
                  value={newCreator.channel_id}
                  onChange={(e) => setNewCreator({ ...newCreator, channel_id: e.target.value })}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-vantyx-textMuted mb-1">Channel Handle</label>
                  <input
                    type="text"
                    placeholder="@ViceCityLegend"
                    value={newCreator.channel_handle}
                    onChange={(e) => setNewCreator({ ...newCreator, channel_handle: e.target.value })}
                    className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-vantyx-textMuted mb-1">Content Category</label>
                  <input
                    type="text"
                    value={newCreator.content_category}
                    onChange={(e) => setNewCreator({ ...newCreator, content_category: e.target.value })}
                    className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-vantyx-textMuted mb-1">Initial Permission Tier</label>
                <select
                  value={newCreator.permission_tier}
                  onChange={(e) => setNewCreator({ ...newCreator, permission_tier: e.target.value })}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                >
                  <option value="authorized_partner">Authorized Partner (Commercial Approved)</option>
                  <option value="own_content">Own Content / In-House Gameplay</option>
                  <option value="public_creative_commons">Creative Commons Attribution</option>
                  <option value="unverified">Unverified (Requires Individual Video Sign-Off)</option>
                </select>
              </div>

              <div>
                <label className="block text-vantyx-textMuted mb-1">Agreement / Permission Notes</label>
                <textarea
                  rows={2}
                  placeholder="Document agreement details or license link..."
                  value={newCreator.notes}
                  onChange={(e) => setNewCreator({ ...newCreator, notes: e.target.value })}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreatorModal(false)}
                  className="rounded border border-vantyx-border px-3 py-1.5 text-vantyx-textSecondary hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded border border-vantyx-accent bg-vantyx-accent px-4 py-1.5 text-black font-semibold hover:bg-vantyx-accentHover"
                >
                  Register Channel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------- Manual Video Import Modal ----------------- */}
      {showImportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-lg border border-vantyx-border bg-vantyx-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-3">
              <h3 className="text-sm font-semibold text-vantyx-textPrimary">Import Video Source</h3>
              <button onClick={() => setShowImportModal(false)} className="text-vantyx-textMuted hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleManualImport} className="space-y-3.5 text-xs font-mono">
              <div>
                <label className="block text-vantyx-textMuted mb-1">Video Title</label>
                <input
                  type="text"
                  required
                  placeholder="GTA 6 Heist Mission Full Gameplay"
                  value={newSource.title}
                  onChange={(e) => setNewSource({ ...newSource, title: e.target.value })}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-vantyx-textMuted mb-1">Video Identifier</label>
                  <input
                    type="text"
                    required
                    placeholder="yt_v_xyz123"
                    value={newSource.video_id}
                    onChange={(e) => setNewSource({ ...newSource, video_id: e.target.value })}
                    className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-vantyx-textMuted mb-1">Duration (Seconds)</label>
                  <input
                    type="number"
                    min={1}
                    value={newSource.duration_seconds}
                    onChange={(e) => setNewSource({ ...newSource, duration_seconds: parseInt(e.target.value) || 0 })}
                    className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-vantyx-textMuted mb-1">Source / Storage URL</label>
                <input
                  type="url"
                  required
                  placeholder="https://www.youtube.com/watch?v=..."
                  value={newSource.source_url}
                  onChange={(e) => setNewSource({ ...newSource, source_url: e.target.value })}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                />
              </div>

              <label className="flex items-center gap-2 text-vantyx-textPrimary cursor-pointer pt-1">
                <input
                  type="checkbox"
                  checked={newSource.is_own_gameplay}
                  onChange={(e) => setNewSource({ ...newSource, is_own_gameplay: e.target.checked })}
                  className="rounded border-vantyx-border bg-vantyx-bg text-vantyx-accent focus:ring-0"
                />
                <span>This is own original gameplay (Astro Rebel recording)</span>
              </label>

              <div>
                <label className="block text-vantyx-textMuted mb-1">Attribution Notice</label>
                <input
                  type="text"
                  value={newSource.attribution_text}
                  onChange={(e) => setNewSource({ ...newSource, attribution_text: e.target.value })}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowImportModal(false)}
                  className="rounded border border-vantyx-border px-3 py-1.5 text-vantyx-textSecondary hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded border border-vantyx-accent bg-vantyx-accent px-4 py-1.5 text-black font-semibold hover:bg-vantyx-accentHover"
                >
                  Import Source
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------- Rights & Permissions Editor Modal ----------------- */}
      {editingRightsSource && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-lg border border-vantyx-border bg-vantyx-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-3">
              <div>
                <h3 className="text-sm font-semibold text-vantyx-textPrimary">Rights & Permissions Gate</h3>
                <span className="text-[11px] font-mono text-vantyx-textMuted truncate block max-w-sm">
                  {editingRightsSource.title}
                </span>
              </div>
              <button onClick={() => setEditingRightsSource(null)} className="text-vantyx-textMuted hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveRights} className="space-y-3.5 text-xs font-mono">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-vantyx-textMuted mb-1">Permission Status</label>
                  <select
                    value={rightsForm.permission_status}
                    onChange={(e) => setRightsForm({ ...rightsForm, permission_status: e.target.value })}
                    className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                  >
                    <option value="authorized">Authorized</option>
                    <option value="own_gameplay">Own Gameplay</option>
                    <option value="pending">Pending Review</option>
                    <option value="rejected">Rejected</option>
                    <option value="revoked">Revoked</option>
                  </select>
                </div>

                <div>
                  <label className="block text-vantyx-textMuted mb-1">Editing Scope</label>
                  <select
                    value={rightsForm.allowed_editing_scope}
                    onChange={(e) => setRightsForm({ ...rightsForm, allowed_editing_scope: e.target.value })}
                    className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                  >
                    <option value="transformative_shorts">Transformative Vertical Shorts</option>
                    <option value="clip_only">Clip Extraction Only</option>
                    <option value="full">Full Unrestricted</option>
                    <option value="restricted">Restricted (Blocked)</option>
                  </select>
                </div>
              </div>

              <label className="flex items-center gap-2 text-vantyx-textPrimary cursor-pointer">
                <input
                  type="checkbox"
                  checked={rightsForm.commercial_use_allowed}
                  onChange={(e) => setRightsForm({ ...rightsForm, commercial_use_allowed: e.target.checked })}
                  className="rounded border-vantyx-border bg-vantyx-bg text-vantyx-accent focus:ring-0"
                />
                <span className="font-semibold text-emerald-400">
                  Commercial-Use Authorized (Required for YouTube Monetized Pipeline)
                </span>
              </label>

              <div>
                <label className="block text-vantyx-textMuted mb-1">Required Attribution Text</label>
                <input
                  type="text"
                  placeholder="e.g. Gameplay footage courtesy of @ChannelName"
                  value={rightsForm.attribution_text}
                  onChange={(e) => setRightsForm({ ...rightsForm, attribution_text: e.target.value })}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-vantyx-textMuted mb-1">Documentation & Agreement Proof</label>
                <textarea
                  rows={3}
                  placeholder="Contract reference, permission email date, or license URL..."
                  value={rightsForm.license_documentation}
                  onChange={(e) => setRightsForm({ ...rightsForm, license_documentation: e.target.value })}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setEditingRightsSource(null)}
                  className="rounded border border-vantyx-border px-3 py-1.5 text-vantyx-textSecondary hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="rounded border border-vantyx-accent bg-vantyx-accent px-4 py-1.5 text-black font-semibold hover:bg-vantyx-accentHover"
                >
                  Apply & Gate Source
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------- Attach Authorized Media Modal ----------------- */}
      {attachMediaSource && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-lg border border-vantyx-border bg-vantyx-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-3">
              <div>
                <h3 className="text-sm font-semibold text-vantyx-textPrimary">
                  Attach Authorized Media File
                </h3>
                <span className="text-[11px] font-mono text-vantyx-textMuted truncate block max-w-sm">
                  Source: {attachMediaSource.title}
                </span>
              </div>
              <button
                onClick={() => setAttachMediaSource(null)}
                className="text-vantyx-textMuted hover:text-white"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-vantyx-textMuted leading-relaxed">
              YouTube URL registration establishes legal rights and metadata records. To execute frame-accurate AI scene indexing, audio waveform analysis, and vertical Shorts rendering, provide the creator-authorized source media file (.mp4, .mov, .mkv).
            </p>

            <div className="flex rounded border border-vantyx-border bg-vantyx-bg p-1 text-xs font-mono">
              <button
                type="button"
                onClick={() => setAttachMode('upload')}
                className={`flex-1 py-1.5 text-center rounded transition-all ${
                  attachMode === 'upload'
                    ? 'bg-vantyx-accent text-black font-semibold'
                    : 'text-vantyx-textMuted hover:text-vantyx-textPrimary'
                }`}
              >
                Upload File from PC
              </button>
              <button
                type="button"
                onClick={() => setAttachMode('link')}
                className={`flex-1 py-1.5 text-center rounded transition-all ${
                  attachMode === 'link'
                    ? 'bg-vantyx-accent text-black font-semibold'
                    : 'text-vantyx-textMuted hover:text-vantyx-textPrimary'
                }`}
              >
                Link Staged Local Path
              </button>
            </div>

            <form onSubmit={handleAttachMediaSubmit} className="space-y-4 text-xs font-mono">
              {attachMode === 'upload' ? (
                <div>
                  <label className="block text-vantyx-textMuted mb-2">
                    Select Gameplay Media File (.mp4, .mov, .mkv, .webm)
                  </label>
                  <input
                    type="file"
                    accept="video/mp4,video/quicktime,video/x-matroska,video/webm"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="w-full text-xs text-vantyx-textPrimary file:mr-3 file:py-2 file:px-3 file:rounded file:border-0 file:text-xs file:font-mono file:bg-vantyx-surfaceElevated file:text-vantyx-accent hover:file:bg-vantyx-border cursor-pointer"
                  />
                  {selectedFile && (
                    <div className="mt-2 text-[11px] text-emerald-400">
                      Selected: {selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(1)} MB)
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <label className="block text-vantyx-textMuted mb-1.5">
                    Absolute or Workspace Staged Path
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. C:\Users\Niketh Rajeev\Videos\gameplay.mp4"
                    value={localPathInput}
                    onChange={(e) => setLocalPathInput(e.target.value)}
                    className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                  />
                  <span className="mt-1 block text-[10px] text-vantyx-textMuted">
                    File must be accessible locally on disk with read permissions.
                  </span>
                </div>
              )}

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setAttachMediaSource(null)}
                  className="rounded border border-vantyx-border px-3 py-1.5 text-vantyx-textSecondary hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={attachingMedia || (attachMode === 'upload' ? !selectedFile : !localPathInput.trim())}
                  className="flex items-center gap-2 rounded border border-vantyx-accent bg-vantyx-accent px-4 py-1.5 text-black font-semibold hover:bg-vantyx-accentHover disabled:opacity-50"
                >
                  <RefreshCw size={12} className={attachingMedia ? 'animate-spin' : ''} />
                  <span>{attachingMedia ? 'Attaching Media...' : 'Associate Media'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ----------------- Creator OAuth & Vault Modal ----------------- */}
      {selectedManageCreator && (
        <CreatorOAuthVaultModal
          creator={selectedManageCreator}
          isOpen={true}
          onClose={() => setSelectedManageCreator(null)}
          onCreatorUpdated={(updated) => {
            setCreators((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
            setSelectedManageCreator(updated);
          }}
        />
      )}
    </div>
  );
};
