import React, { useEffect, useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Key,
  HardDrive,
  FileText,
  RefreshCw,
  XCircle,
  Trash2,
  Plus,
  Unlink,
} from 'lucide-react';
import {
  initiateCreatorOAuth,
  submitCreatorOAuthCallback,
  fetchCreatorOAuthStatus,
  refreshCreatorOAuthToken,
  revokeCreatorOAuth,
  disconnectCreatorChannel,
  fetchCreatorAuditLogs,
  fetchCreatorVaultStatus,
  associateCreatorAsset,
  deleteCreatorAssetAssociation,
} from '@/lib/api';
import {
  Creator,
  CreatorAuditLogResponse,
  CreatorOAuthStatusResponse,
  CreatorVaultStatusResponse,
} from '@/types';

interface CreatorOAuthVaultModalProps {
  creator: Creator;
  isOpen: boolean;
  onClose: () => void;
  onCreatorUpdated?: (updated: Creator) => void;
}

export const CreatorOAuthVaultModal: React.FC<CreatorOAuthVaultModalProps> = ({
  creator,
  isOpen,
  onClose,
  onCreatorUpdated,
}) => {
  const [activeTab, setActiveTab] = useState<'oauth' | 'vault' | 'audit'>('oauth');
  const [oauthStatus, setOauthStatus] = useState<CreatorOAuthStatusResponse | null>(null);
  const [vaultStatus, setVaultStatus] = useState<CreatorVaultStatusResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<CreatorAuditLogResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // Associate asset form state
  const [assocVideoId, setAssocVideoId] = useState<string>('');
  const [assocFilename, setAssocFilename] = useState<string>('');
  const [assocNotes, setAssocNotes] = useState<string>('');

  useEffect(() => {
    if (isOpen) {
      loadAllData();
    }
  }, [isOpen, creator.id]);

  const loadAllData = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const [oauth, vault, logs] = await Promise.all([
        fetchCreatorOAuthStatus(creator.id),
        fetchCreatorVaultStatus(creator.id),
        fetchCreatorAuditLogs(creator.id, 30),
      ]);
      setOauthStatus(oauth);
      setVaultStatus(vault);
      setAuditLogs(logs);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to load creator authorization details' });
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const handleInitiateOAuth = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      const res = await initiateCreatorOAuth(creator.id);
      if (res.configured && res.authorization_url) {
        window.location.href = res.authorization_url;
      } else {
        setMessage({
          type: 'info',
          text: res.message || 'OAuth not configured. Use developer simulation mode to test.',
        });
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to initiate Google OAuth flow' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleSimulateOAuth = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      // Initiate to obtain valid CSRF state
      const initRes = await initiateCreatorOAuth(creator.id);
      if (!initRes.state) throw new Error('Failed to generate secure OAuth state');

      // Exchange mock code with state
      const statusRes = await submitCreatorOAuthCallback(
        creator.id,
        `mock_auth_code_${creator.id}_${Date.now()}`,
        initRes.state
      );
      setOauthStatus(statusRes);
      setMessage({
        type: 'success',
        text: `Simulated Google OAuth completed for testing: channel verified as '${statusRes.verified_channel_title}'`,
      });
      await loadAllData();
      if (onCreatorUpdated) {
        onCreatorUpdated({
          ...creator,
          oauth_status: 'connected',
          verified_channel_id: statusRes.verified_channel_id,
          verified_channel_title: statusRes.verified_channel_title,
          approval_status: 'approved',
          permission_tier: 'own_content',
        });
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Simulated OAuth failed' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleRefreshToken = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      const updated = await refreshCreatorOAuthToken(creator.id);
      setOauthStatus(updated);
      setMessage({ type: 'success', text: 'Google OAuth access token successfully refreshed.' });
      await loadAllData();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Token refresh failed' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevokeOAuth = async () => {
    if (!window.confirm('Are you sure you want to revoke this channel authorization? Verified video ownership will be invalidated.')) {
      return;
    }
    setActionLoading(true);
    setMessage(null);
    try {
      const updated = await revokeCreatorOAuth(creator.id, 'Revoked by operator in URL Studio');
      setOauthStatus(updated);
      setMessage({ type: 'info', text: 'Channel authorization revoked. Access credentials cleared.' });
      await loadAllData();
      if (onCreatorUpdated) {
        onCreatorUpdated({
          ...creator,
          oauth_status: 'revoked',
          is_revoked: true,
        });
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Revocation failed' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      const updated = await disconnectCreatorChannel(creator.id);
      setOauthStatus(updated);
      setMessage({ type: 'info', text: 'Channel disconnected from Google OAuth.' });
      await loadAllData();
      if (onCreatorUpdated) {
        onCreatorUpdated({
          ...creator,
          oauth_status: 'disconnected',
        });
      }
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Disconnect failed' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleAssociateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assocVideoId.trim() || !assocFilename.trim()) {
      setMessage({ type: 'error', text: 'Video ID and Master Filename are required' });
      return;
    }
    setActionLoading(true);
    setMessage(null);
    try {
      await associateCreatorAsset(creator.id, {
        video_id: assocVideoId.trim(),
        asset_filename: assocFilename.trim(),
        notes: assocNotes.trim() || undefined,
      });
      setMessage({
        type: 'success',
        text: `Successfully mapped '${assocFilename}' to YouTube video '${assocVideoId}'`,
      });
      setAssocVideoId('');
      setAssocFilename('');
      setAssocNotes('');
      await loadAllData();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to associate master asset' });
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteAssociation = async (assocId: number) => {
    setActionLoading(true);
    setMessage(null);
    try {
      await deleteCreatorAssetAssociation(creator.id, assocId);
      setMessage({ type: 'info', text: 'Asset mapping removed' });
      await loadAllData();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to remove mapping' });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-3xl rounded-lg border border-vantyx-border bg-vantyx-surface shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-vantyx-border px-6 py-4 bg-vantyx-surfaceElevated/50">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded border border-vantyx-border bg-vantyx-surface">
              <Key size={18} className="text-vantyx-accent" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-vantyx-textPrimary">
                Channel Authorization & Media Vault
              </h2>
              <span className="text-[11px] font-mono text-vantyx-textMuted">
                Creator: <span className="text-vantyx-textSecondary">{creator.name}</span> (#{creator.id}) •{' '}
                <span className="text-vantyx-accent">{creator.channel_id}</span>
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-vantyx-textMuted hover:text-vantyx-textPrimary hover:bg-vantyx-surfaceElevated transition-colors"
          >
            <XCircle size={18} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-vantyx-border bg-vantyx-surface px-6">
          <button
            onClick={() => setActiveTab('oauth')}
            className={`flex items-center gap-2 border-b-2 py-3 px-3 text-xs font-medium transition-colors ${
              activeTab === 'oauth'
                ? 'border-vantyx-accent text-vantyx-accent'
                : 'border-transparent text-vantyx-textMuted hover:text-vantyx-textSecondary'
            }`}
          >
            <ShieldCheck size={14} />
            YouTube OAuth & Identity
          </button>
          <button
            onClick={() => setActiveTab('vault')}
            className={`flex items-center gap-2 border-b-2 py-3 px-3 text-xs font-medium transition-colors ${
              activeTab === 'vault'
                ? 'border-vantyx-accent text-vantyx-accent'
                : 'border-transparent text-vantyx-textMuted hover:text-vantyx-textSecondary'
            }`}
          >
            <HardDrive size={14} />
            Media Vault & Assets ({vaultStatus?.total_files || 0})
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`flex items-center gap-2 border-b-2 py-3 px-3 text-xs font-medium transition-colors ${
              activeTab === 'audit'
                ? 'border-vantyx-accent text-vantyx-accent'
                : 'border-transparent text-vantyx-textMuted hover:text-vantyx-textSecondary'
            }`}
          >
            <FileText size={14} />
            Security Audit Trail ({auditLogs.length})
          </button>
        </div>

        {/* Messages */}
        {message && (
          <div
            className={`px-6 py-2.5 text-xs flex items-center justify-between ${
              message.type === 'success'
                ? 'bg-emerald-950/40 text-emerald-400 border-b border-emerald-900/50'
                : message.type === 'error'
                ? 'bg-rose-950/40 text-rose-400 border-b border-rose-900/50'
                : 'bg-sky-950/40 text-sky-400 border-b border-sky-900/50'
            }`}
          >
            <span>{message.text}</span>
            <button onClick={() => setMessage(null)} className="text-xs opacity-70 hover:opacity-100">
              Dismiss
            </button>
          </div>
        )}

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3 text-vantyx-textMuted">
              <RefreshCw size={24} className="animate-spin text-vantyx-accent" />
              <span className="text-xs font-mono">Loading creator authorization records...</span>
            </div>
          ) : activeTab === 'oauth' ? (
            /* TAB 1: OAuth & Identity */
            <div className="space-y-6">
              {/* Status Banner */}
              <div className="rounded-lg border border-vantyx-border bg-vantyx-surfaceElevated/40 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono uppercase text-vantyx-textMuted">Authorization Status</span>
                  <span
                    className={`px-2.5 py-0.5 rounded text-[11px] font-mono font-semibold uppercase ${
                      oauthStatus?.oauth_status === 'connected'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : oauthStatus?.oauth_status === 'expired'
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                        : oauthStatus?.oauth_status === 'revoked'
                        ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                        : 'bg-neutral-800 text-neutral-400 border border-neutral-700'
                    }`}
                  >
                    {oauthStatus?.oauth_status || 'Disconnected'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 text-xs font-mono pt-2 border-t border-vantyx-border/50">
                  <div>
                    <span className="text-vantyx-textMuted block text-[10px] uppercase">Registered Channel ID</span>
                    <span className="text-vantyx-textPrimary">{creator.channel_id}</span>
                  </div>
                  <div>
                    <span className="text-vantyx-textMuted block text-[10px] uppercase">Verified Identity</span>
                    <span className="text-vantyx-accent">
                      {oauthStatus?.verified_channel_id ? (
                        <>
                          {oauthStatus.verified_channel_title || 'Authenticated Channel'} (
                          {oauthStatus.verified_channel_id})
                        </>
                      ) : (
                        <span className="text-neutral-500">Unverified</span>
                      )}
                    </span>
                  </div>
                  <div>
                    <span className="text-vantyx-textMuted block text-[10px] uppercase">Credential Expiry</span>
                    <span className="text-vantyx-textSecondary">
                      {oauthStatus?.token_expires_at
                        ? new Date(oauthStatus.token_expires_at).toLocaleString()
                        : 'No token recorded'}
                    </span>
                  </div>
                  <div>
                    <span className="text-vantyx-textMuted block text-[10px] uppercase">Ownership Verified At</span>
                    <span className="text-vantyx-textSecondary">
                      {oauthStatus?.verified_at
                        ? new Date(oauthStatus.verified_at).toLocaleString()
                        : 'Not verified'}
                    </span>
                  </div>
                </div>

                {oauthStatus?.is_revoked && (
                  <div className="rounded border border-rose-500/30 bg-rose-950/20 p-2.5 text-xs text-rose-400 flex items-center gap-2">
                    <ShieldAlert size={14} className="shrink-0" />
                    <span>Channel authorization revoked. Videos from this channel will be halted at the rights gate.</span>
                  </div>
                )}
              </div>

              {/* Action Controls */}
              <div className="rounded-lg border border-vantyx-border bg-vantyx-surface p-4 space-y-3">
                <h3 className="text-xs font-semibold text-vantyx-textPrimary">OAuth Controls & Authorization</h3>
                <p className="text-xs text-vantyx-textMuted leading-relaxed">
                  Authenticates creator identity through Google OAuth with minimal read-only scope (
                  <code className="text-[11px] text-vantyx-accent">youtube.readonly</code>). Credentials are encrypted at rest using AES-256 and never exposed to the browser.
                </p>

                <div className="flex flex-wrap items-center gap-2 pt-2">
                  <button
                    onClick={handleInitiateOAuth}
                    disabled={actionLoading}
                    className="flex items-center gap-2 rounded bg-vantyx-accent px-3 py-1.5 text-xs font-semibold text-vantyx-background hover:bg-vantyx-accent/90 disabled:opacity-50 transition-colors"
                  >
                    <Key size={13} />
                    Connect via Google OAuth
                  </button>

                  <button
                    onClick={handleSimulateOAuth}
                    disabled={actionLoading}
                    className="flex items-center gap-2 rounded border border-vantyx-border px-3 py-1.5 text-xs text-vantyx-textSecondary hover:border-vantyx-accent/60 hover:text-vantyx-accent disabled:opacity-50 transition-colors"
                    title="Simulate complete OAuth verification for testing"
                  >
                    <ShieldCheck size={13} />
                    Simulate Developer Auth (Local Test)
                  </button>

                  {oauthStatus?.oauth_status === 'connected' && (
                    <>
                      <button
                        onClick={handleRefreshToken}
                        disabled={actionLoading}
                        className="flex items-center gap-1.5 rounded border border-vantyx-border px-3 py-1.5 text-xs text-vantyx-textSecondary hover:text-vantyx-textPrimary disabled:opacity-50"
                      >
                        <RefreshCw size={12} className={actionLoading ? 'animate-spin' : ''} />
                        Refresh Token
                      </button>

                      <button
                        onClick={handleDisconnect}
                        disabled={actionLoading}
                        className="flex items-center gap-1.5 rounded border border-vantyx-border px-3 py-1.5 text-xs text-neutral-400 hover:text-neutral-200 disabled:opacity-50"
                      >
                        <Unlink size={12} />
                        Disconnect
                      </button>

                      <button
                        onClick={handleRevokeOAuth}
                        disabled={actionLoading}
                        className="flex items-center gap-1.5 rounded border border-rose-500/30 px-3 py-1.5 text-xs text-rose-400 hover:bg-rose-500/10 disabled:opacity-50"
                      >
                        <ShieldAlert size={12} />
                        Revoke Authorization
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ) : activeTab === 'vault' ? (
            /* TAB 2: Vault & Master Media Association */
            <div className="space-y-6">
              {/* Vault Directory Summary */}
              <div className="rounded-lg border border-vantyx-border bg-vantyx-surfaceElevated/30 p-4 space-y-2">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-vantyx-textMuted">Local Creator Vault</span>
                  <code className="text-vantyx-accent">{vaultStatus?.vault_directory}</code>
                </div>
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-vantyx-textMuted">Total Staged Assets</span>
                  <span className="text-vantyx-textPrimary">
                    {vaultStatus?.total_files || 0} files ({((vaultStatus?.total_size_bytes || 0) / (1024 * 1024)).toFixed(2)} MB)
                  </span>
                </div>
              </div>

              {/* Explicit Association Form */}
              <form onSubmit={handleAssociateAsset} className="rounded-lg border border-vantyx-border bg-vantyx-surface p-4 space-y-3">
                <h4 className="text-xs font-semibold text-vantyx-textPrimary flex items-center gap-1.5">
                  <Plus size={14} className="text-vantyx-accent" />
                  Map Vault Master File to YouTube Video ID
                </h4>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block text-[10px] font-mono uppercase text-vantyx-textMuted mb-1">
                      YouTube Video ID (11 chars)
                    </label>
                    <input
                      type="text"
                      value={assocVideoId}
                      onChange={(e) => setAssocVideoId(e.target.value)}
                      placeholder="e.g. ast_3d6a14_"
                      className="w-full rounded border border-vantyx-border bg-vantyx-surfaceElevated px-3 py-1.5 text-xs font-mono text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-mono uppercase text-vantyx-textMuted mb-1">
                      Master Filename in Vault
                    </label>
                    <input
                      type="text"
                      value={assocFilename}
                      onChange={(e) => setAssocFilename(e.target.value)}
                      placeholder="e.g. gameplay_master_01.mp4"
                      className="w-full rounded border border-vantyx-border bg-vantyx-surfaceElevated px-3 py-1.5 text-xs font-mono text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                    />
                  </div>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <input
                    type="text"
                    value={assocNotes}
                    onChange={(e) => setAssocNotes(e.target.value)}
                    placeholder="Optional notes or bilateral agreement details"
                    className="w-2/3 rounded border border-vantyx-border bg-vantyx-surfaceElevated px-3 py-1.5 text-xs text-vantyx-textSecondary focus:border-vantyx-accent focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="rounded bg-vantyx-accent px-4 py-1.5 text-xs font-semibold text-vantyx-background hover:bg-vantyx-accent/90 disabled:opacity-50"
                  >
                    Save Mapping
                  </button>
                </div>
              </form>

              {/* Files in Vault Table */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-vantyx-textPrimary">Files in Creator Vault</h4>
                {vaultStatus?.files.length === 0 ? (
                  <p className="text-xs text-vantyx-textMuted italic py-3">
                    No video files staged in {vaultStatus?.vault_directory}. Place master gameplay MP4 files in this folder to allow autonomous resolution.
                  </p>
                ) : (
                  <div className="overflow-x-auto rounded border border-vantyx-border">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="border-b border-vantyx-border bg-vantyx-surfaceElevated/60 text-[10px] uppercase text-vantyx-textMuted">
                        <tr>
                          <th className="py-2 px-3">Filename</th>
                          <th className="py-2 px-3">Size / Duration</th>
                          <th className="py-2 px-3">Integrity</th>
                          <th className="py-2 px-3">Associated Video</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-vantyx-border">
                        {vaultStatus?.files.map((f) => (
                          <tr key={f.filename} className="hover:bg-vantyx-surfaceElevated/30">
                            <td className="py-2 px-3 text-vantyx-textPrimary">{f.filename}</td>
                            <td className="py-2 px-3 text-vantyx-textMuted">
                              {(f.file_size_bytes / (1024 * 1024)).toFixed(2)} MB • {f.duration_seconds.toFixed(1)}s
                            </td>
                            <td className="py-2 px-3">
                              {f.is_valid ? (
                                <span className="text-emerald-400 text-[10px]">VERIFIED (FFmpeg)</span>
                              ) : (
                                <span className="text-rose-400 text-[10px]">{f.integrity_message}</span>
                              )}
                            </td>
                            <td className="py-2 px-3">
                              {f.associated_video_id ? (
                                <span className="text-vantyx-accent font-semibold">{f.associated_video_id}</span>
                              ) : (
                                <button
                                  onClick={() => setAssocFilename(f.filename)}
                                  className="text-[10px] text-vantyx-textMuted hover:text-vantyx-accent underline"
                                >
                                  + Link to Video
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Active Explicit Associations */}
              {vaultStatus?.associations && vaultStatus.associations.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold text-vantyx-textPrimary">Verified Video Mappings</h4>
                  <div className="overflow-x-auto rounded border border-vantyx-border">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="border-b border-vantyx-border bg-vantyx-surfaceElevated/60 text-[10px] uppercase text-vantyx-textMuted">
                        <tr>
                          <th className="py-2 px-3">Video ID</th>
                          <th className="py-2 px-3">Mapped Master File</th>
                          <th className="py-2 px-3">Status</th>
                          <th className="py-2 px-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-vantyx-border">
                        {vaultStatus.associations.map((a) => (
                          <tr key={a.id} className="hover:bg-vantyx-surfaceElevated/30">
                            <td className="py-2 px-3 text-vantyx-accent font-semibold">{a.video_id}</td>
                            <td className="py-2 px-3 text-vantyx-textSecondary">{a.asset_filename}</td>
                            <td className="py-2 px-3">
                              <span className="text-emerald-400 text-[10px]">READY FOR SHORT RENDER</span>
                            </td>
                            <td className="py-2 px-3 text-right">
                              <button
                                onClick={() => handleDeleteAssociation(a.id)}
                                className="text-vantyx-textMuted hover:text-rose-400 p-1"
                                title="Remove association"
                              >
                                <Trash2 size={12} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* TAB 3: Audit Trail */
            <div className="space-y-3">
              <h4 className="text-xs font-semibold text-vantyx-textPrimary">Immutable Security Audit Trail</h4>
              <p className="text-xs text-vantyx-textMuted">
                Cryptographic log of all Google OAuth, channel identity verification, token refresh, and revocation events.
              </p>

              {auditLogs.length === 0 ? (
                <p className="text-xs text-vantyx-textMuted italic py-6 text-center">No audit events recorded yet.</p>
              ) : (
                <div className="overflow-x-auto rounded border border-vantyx-border">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="border-b border-vantyx-border bg-vantyx-surfaceElevated/60 text-[10px] uppercase text-vantyx-textMuted">
                      <tr>
                        <th className="py-2 px-3">Timestamp (UTC)</th>
                        <th className="py-2 px-3">Event Type</th>
                        <th className="py-2 px-3">Channel</th>
                        <th className="py-2 px-3">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-vantyx-border">
                      {auditLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-vantyx-surfaceElevated/30">
                          <td className="py-2 px-3 text-vantyx-textMuted whitespace-nowrap">
                            {new Date(log.created_at).toLocaleString()}
                          </td>
                          <td className="py-2 px-3">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] uppercase ${
                                log.event_type.includes('failure') || log.event_type.includes('revoked')
                                  ? 'bg-rose-500/10 text-rose-400'
                                  : log.event_type.includes('verified')
                                  ? 'bg-emerald-500/10 text-emerald-400'
                                  : 'bg-neutral-800 text-neutral-300'
                              }`}
                            >
                              {log.event_type}
                            </span>
                          </td>
                          <td className="py-2 px-3 text-vantyx-textSecondary">{log.channel_id || '—'}</td>
                          <td className="py-2 px-3 text-vantyx-textMuted">{log.details || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-vantyx-border px-6 py-3 bg-vantyx-surfaceElevated/40">
          <span className="text-[11px] font-mono text-vantyx-textMuted">
            VANTYX Autonomous Security Engine • Token AES-256 Protected
          </span>
          <button
            onClick={onClose}
            className="rounded border border-vantyx-border px-4 py-1.5 text-xs text-vantyx-textSecondary hover:text-vantyx-textPrimary"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
