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
} from '@/lib/api';
import { Creator, VideoSource } from '@/types';

export const DiscoveryView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'sources' | 'creators'>('sources');
  const [creators, setCreators] = useState<Creator[]>([]);
  const [sources, setSources] = useState<VideoSource[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [discovering, setDiscovering] = useState<boolean>(false);
  const [filterEligible, setFilterEligible] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modals
  const [showCreatorModal, setShowCreatorModal] = useState<boolean>(false);
  const [showImportModal, setShowImportModal] = useState<boolean>(false);
  const [editingRightsSource, setEditingRightsSource] = useState<VideoSource | null>(null);

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
      const [cData, sData] = await Promise.all([
        fetchCreators(),
        fetchVideoSources(undefined, filterEligible),
      ]);
      setCreators(cData);
      setSources(sData);
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
                    <th className="py-3 px-4">Permission Status</th>
                    <th className="py-3 px-4">Commercial Rights</th>
                    <th className="py-3 px-4">Eligibility Gate</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-vantyx-border font-mono">
                  {sources.map((src) => {
                    const statusVal = src.rights?.permission_status || 'pending';
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
                          <button
                            onClick={() => openRightsEditor(src)}
                            className="rounded border border-vantyx-border px-2.5 py-1 text-[11px] text-vantyx-textSecondary hover:border-vantyx-accent hover:text-vantyx-textPrimary"
                          >
                            Manage Rights
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Creators Table */
        <div className="space-y-4">
          <div className="overflow-x-auto rounded border border-vantyx-border bg-vantyx-surface">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-vantyx-border bg-vantyx-surfaceElevated/50 text-[11px] font-mono uppercase text-vantyx-textMuted">
                <tr>
                  <th className="py-3 px-4">Creator / Channel</th>
                  <th className="py-3 px-4">Channel ID</th>
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
    </div>
  );
};
