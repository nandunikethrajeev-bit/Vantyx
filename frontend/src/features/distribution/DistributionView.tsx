import React, { useEffect, useState } from 'react';
import {
  Calendar,
  Clock,
  Youtube,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  UploadCloud,
  ExternalLink,
  ShieldCheck,
  Trash2,
  Film,
  Info,
  X,
  Lock,
} from 'lucide-react';
import {
  fetchChannelStatus,
  fetchDailySlots,
  fetchSchedules,
  fetchOAuthUrl,
  disconnectChannel,
  createSchedule,
  cancelSchedule,
  triggerPublish,
  fetchRenderJobs,
  fetchCandidates,
} from '@/lib/api';
import {
  YouTubeAccount,
  SlotInfo,
  PublishSchedule,
  RenderJob,
  CandidateClip,
  OAuthUrlResponse,
} from '@/types';

export const DistributionView: React.FC = () => {
  const [account, setAccount] = useState<YouTubeAccount | null>(null);
  const [oauthInfo, setOauthInfo] = useState<OAuthUrlResponse | null>(null);
  const [targetDate, setTargetDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  const [slots, setSlots] = useState<SlotInfo[]>([]);
  const [schedules, setSchedules] = useState<PublishSchedule[]>([]);
  const [completedJobs, setCompletedJobs] = useState<RenderJob[]>([]);
  const [candidates, setCandidates] = useState<CandidateClip[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Scheduling Modal State
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState<boolean>(false);
  const [selectedSlotName, setSelectedSlotName] = useState<string>('09:00');
  const [selectedJobId, setSelectedJobId] = useState<number | ''>('');
  const [scheduleTitle, setScheduleTitle] = useState<string>('');
  const [customDescription, setCustomDescription] = useState<string>('');
  const [scheduling, setScheduling] = useState<boolean>(false);

  // Setup Guide Modal State
  const [isGuideOpen, setIsGuideOpen] = useState<boolean>(false);

  // Action in-flight state
  const [publishingId, setPublishingId] = useState<number | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [
        accountData,
        oauthData,
        slotsData,
        schedulesData,
        jobsData,
        candidatesData,
      ] = await Promise.all([
        fetchChannelStatus(),
        fetchOAuthUrl(),
        fetchDailySlots(targetDate),
        fetchSchedules(undefined, 30),
        fetchRenderJobs('completed', 50),
        fetchCandidates(undefined, 'approved'),
      ]);

      setAccount(accountData);
      setOauthInfo(oauthData);
      setSlots(slotsData.slots || []);
      setSchedules(schedulesData);
      setCompletedJobs(jobsData);
      setCandidates(candidatesData);

      if (jobsData.length > 0 && selectedJobId === '') {
        setSelectedJobId(jobsData[0].id);
        const matchedCandidate = candidatesData.find((c) => c.id === jobsData[0].candidate_id);
        if (matchedCandidate) {
          setScheduleTitle(`GTA 6: ${matchedCandidate.title_suggestion || 'Epic Moment'} #Shorts`);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load distribution subsystem data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [targetDate]);

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect Astro Rebel from YouTube?')) return;
    try {
      await disconnectChannel();
      setSuccessMessage('YouTube account disconnected successfully.');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to disconnect account');
    }
  };

  const handleOpenScheduleModal = (slotName: string) => {
    setSelectedSlotName(slotName);
    if (completedJobs.length > 0) {
      const firstJob = completedJobs[0];
      setSelectedJobId(firstJob.id);
      const matched = candidates.find((c) => c.id === firstJob.candidate_id);
      setScheduleTitle(`GTA 6: ${matched?.title_suggestion || 'Moments'} #Shorts`);
    }
    setIsScheduleModalOpen(true);
  };

  const handleSelectJob = (jobId: number) => {
    setSelectedJobId(jobId);
    const chosenJob = completedJobs.find((j) => j.id === jobId);
    if (chosenJob) {
      const matched = candidates.find((c) => c.id === chosenJob.candidate_id);
      if (matched) {
        setScheduleTitle(`GTA 6: ${matched.title_suggestion || 'Moments'} #Shorts`);
      }
    }
  };

  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedJobId) {
      setError('Please select a completed rendered short');
      return;
    }

    const job = completedJobs.find((j) => j.id === Number(selectedJobId));
    if (!job) {
      setError('Selected render job was not found');
      return;
    }

    try {
      setScheduling(true);
      setError(null);
      await createSchedule({
        candidate_id: job.candidate_id,
        render_job_id: job.id,
        target_date: targetDate,
        slot_name: selectedSlotName,
        title: scheduleTitle,
        custom_description: customDescription || undefined,
      });

      setIsScheduleModalOpen(false);
      setSuccessMessage(`Short scheduled successfully for slot ${selectedSlotName} IST on ${targetDate}.`);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to create schedule');
    } finally {
      setScheduling(false);
    }
  };

  const handleCancelSchedule = async (scheduleId: number) => {
    if (!confirm('Are you sure you want to cancel this scheduled publish?')) return;
    try {
      await cancelSchedule(scheduleId);
      setSuccessMessage('Scheduled publish cancelled.');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to cancel schedule');
    }
  };

  const handlePublishNow = async (scheduleId: number) => {
    try {
      setPublishingId(scheduleId);
      setError(null);
      // Trigger upload via API (uses mock provider safely if credentials not configured)
      const res = await triggerPublish(scheduleId, !oauthInfo?.configured);
      setSuccessMessage(
        res.is_mock
          ? `[Mock Published] Upload verified: ${res.youtube_video_id}`
          : `[Live Published] Video published to YouTube: ${res.youtube_video_id}`
      );
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Publishing upload failed');
    } finally {
      setPublishingId(null);
    }
  };

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-light tracking-wide text-vantyx-textPrimary">
              Distribution & Publishing Engine
            </h1>
            <span className="rounded border border-vantyx-accent/40 bg-vantyx-accent/10 px-2 py-0.5 text-xs font-mono font-medium text-vantyx-accent">
              M06 ACTIVE
            </span>
          </div>
          <p className="mt-1 text-sm text-vantyx-textSecondary">
            Official YouTube Data API v3 publishing pipeline • 4 daily slots in Asia/Kolkata timezone.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsGuideOpen(true)}
            className="flex items-center gap-2 rounded border border-vantyx-border bg-vantyx-surface/60 px-3 py-1.5 text-xs text-vantyx-textSecondary transition hover:border-vantyx-accent/50 hover:text-vantyx-textPrimary"
          >
            <Info className="h-3.5 w-3.5" />
            OAuth Setup Guide
          </button>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-2 rounded border border-vantyx-border bg-vantyx-surface/80 px-3 py-1.5 text-xs text-vantyx-textSecondary transition hover:border-vantyx-accent/50 hover:text-vantyx-textPrimary disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="flex items-center justify-between rounded border border-red-500/30 bg-red-950/20 p-4 text-sm text-red-400">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-white">
            <X className="h-4 w-4" />
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
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* YouTube Channel Authorization Card */}
      <div className="rounded-lg border border-vantyx-border bg-vantyx-surface/40 p-6 backdrop-blur-sm">
        <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-red-500/30 bg-red-950/30 text-red-500 shadow-inner">
              <Youtube className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-medium text-vantyx-textPrimary">
                  Target Channel: <span className="font-semibold text-white">Astro Rebel</span>
                </h2>
                {account?.is_active ? (
                  <span className="flex items-center gap-1 rounded bg-emerald-950/50 px-2 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/30">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    Authorized
                  </span>
                ) : (
                  <span className="flex items-center gap-1 rounded bg-amber-950/50 px-2 py-0.5 text-xs font-medium text-amber-400 border border-amber-500/30">
                    <Lock className="h-3.5 w-3.5" />
                    OAuth Unlinked
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-vantyx-textSecondary">
                {account?.is_active
                  ? `Connected ID: ${account.channel_id} • Scope: youtube.upload • Tokens safely stored & encrypted.`
                  : oauthInfo?.configured
                  ? 'Google OAuth credentials configured. Authorize Astro Rebel to enable live autonomous scheduling.'
                  : 'Running in safe verified Mock Publishing mode. Live uploads require Google Cloud Console OAuth setup.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {account?.is_active ? (
              <button
                onClick={handleDisconnect}
                className="rounded border border-red-500/30 bg-red-950/20 px-4 py-2 text-xs font-medium text-red-300 hover:bg-red-900/40 hover:border-red-500/50 transition"
              >
                Disconnect Channel
              </button>
            ) : oauthInfo?.auth_url ? (
              <a
                href={oauthInfo.auth_url}
                className="flex items-center gap-2 rounded bg-red-600 px-4 py-2 text-xs font-medium text-white shadow-lg hover:bg-red-500 transition"
              >
                <Youtube className="h-4 w-4" />
                Connect Astro Rebel Account
              </a>
            ) : (
              <button
                onClick={() => setIsGuideOpen(true)}
                className="flex items-center gap-2 rounded border border-vantyx-accent/40 bg-vantyx-accent/10 px-4 py-2 text-xs font-medium text-vantyx-accent hover:bg-vantyx-accent/20 transition"
              >
                <Info className="h-4 w-4" />
                Configure Google OAuth
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Daily Slot Calendar Controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-vantyx-border pb-4">
        <div>
          <h3 className="text-base font-medium text-vantyx-textPrimary flex items-center gap-2">
            <Clock className="h-4 w-4 text-vantyx-accent" />
            Daily Publishing Schedule (Asia/Kolkata IST)
          </h3>
          <p className="text-xs text-vantyx-textSecondary">
            Cadence: 09:00, 13:00, 17:00, 21:00 IST (4 Shorts/day)
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              const d = new Date();
              setTargetDate(d.toISOString().split('T')[0]);
            }}
            className={`rounded px-3 py-1 text-xs font-mono transition ${
              targetDate === new Date().toISOString().split('T')[0]
                ? 'bg-vantyx-accent text-vantyx-bg font-semibold'
                : 'border border-vantyx-border bg-vantyx-surface/50 text-vantyx-textSecondary hover:text-white'
            }`}
          >
            Today
          </button>
          <button
            onClick={() => {
              const d = new Date();
              d.setDate(d.getDate() + 1);
              setTargetDate(d.toISOString().split('T')[0]);
            }}
            className="rounded border border-vantyx-border bg-vantyx-surface/50 px-3 py-1 text-xs font-mono text-vantyx-textSecondary hover:text-white transition"
          >
            Tomorrow
          </button>
          <div className="flex items-center gap-2 rounded border border-vantyx-border bg-vantyx-surface/80 px-3 py-1 text-xs">
            <Calendar className="h-3.5 w-3.5 text-vantyx-textSecondary" />
            <input
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="bg-transparent text-xs text-vantyx-textPrimary focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* 4 Daily Slots Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
        {slots.map((slot) => {
          const isUnfilled = slot.status === 'unfilled';
          const isScheduled = slot.status === 'scheduled';
          const isPublished = slot.status === 'published';
          const sched = slot.schedule;

          return (
            <div
              key={slot.slot_name}
              className={`flex flex-col justify-between rounded-lg border p-5 transition ${
                isPublished
                  ? 'border-emerald-500/40 bg-emerald-950/10'
                  : isScheduled
                  ? 'border-vantyx-accent/50 bg-vantyx-accent/5'
                  : 'border-vantyx-border bg-vantyx-surface/30'
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Clock className="h-4 w-4 text-vantyx-accent" />
                    <span className="font-mono text-lg font-semibold text-white">
                      {slot.slot_name}
                    </span>
                    <span className="text-[10px] font-mono text-vantyx-textSecondary">IST</span>
                  </div>
                  <span
                    className={`rounded px-2 py-0.5 text-[10px] font-mono font-medium uppercase tracking-wide border ${
                      isPublished
                        ? 'border-emerald-500/30 bg-emerald-950/40 text-emerald-400'
                        : isScheduled
                        ? 'border-vantyx-accent/40 bg-vantyx-accent/20 text-vantyx-accent'
                        : 'border-slate-700 bg-slate-800/40 text-slate-400'
                    }`}
                  >
                    {slot.status}
                  </span>
                </div>

                <div className="mt-4">
                  {isUnfilled && (
                    <div className="py-6 text-center">
                      <p className="text-xs text-vantyx-textSecondary">Slot open</p>
                      <button
                        onClick={() => handleOpenScheduleModal(slot.slot_name)}
                        className="mt-3 inline-flex items-center gap-1.5 rounded border border-vantyx-accent/40 bg-vantyx-accent/10 px-3 py-1.5 text-xs font-medium text-vantyx-accent hover:bg-vantyx-accent/20 transition"
                      >
                        <Film className="h-3.5 w-3.5" />
                        Assign Rendered Short
                      </button>
                    </div>
                  )}

                  {sched && (
                    <div className="space-y-3">
                      <div>
                        <p className="text-xs font-medium text-white line-clamp-2">
                          {sched.title}
                        </p>
                        <p className="mt-1 text-[11px] text-vantyx-textSecondary">
                          Target: {sched.target_channel}
                        </p>
                      </div>

                      {sched.publish_url && (
                        <div className="rounded bg-black/40 p-2.5 border border-vantyx-border">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="text-slate-400">YouTube Video:</span>
                            <a
                              href={sched.publish_url}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-center gap-1 text-vantyx-accent hover:underline font-mono"
                            >
                              {sched.youtube_video_id}
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          </div>
                          {sched.is_mock && (
                            <span className="mt-1 block text-[10px] font-mono text-amber-400">
                              [Verified Mock Pipeline]
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {sched && (
                <div className="mt-4 pt-4 border-t border-vantyx-border/60 flex items-center justify-between">
                  {isScheduled && (
                    <>
                      <button
                        onClick={() => handlePublishNow(sched.id)}
                        disabled={publishingId === sched.id}
                        className="flex items-center gap-1.5 rounded bg-vantyx-accent px-3 py-1 text-xs font-medium text-vantyx-bg hover:bg-vantyx-accent/90 transition disabled:opacity-50"
                      >
                        <UploadCloud className="h-3.5 w-3.5" />
                        {publishingId === sched.id ? 'Publishing...' : 'Publish Now'}
                      </button>

                      <button
                        onClick={() => handleCancelSchedule(sched.id)}
                        className="rounded p-1 text-slate-400 hover:text-red-400 transition"
                        title="Cancel Schedule"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </>
                  )}

                  {isPublished && (
                    <div className="flex items-center gap-1 text-[11px] text-emerald-400 font-mono">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Published
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Scheduled Queue History Table */}
      <div className="rounded-lg border border-vantyx-border bg-vantyx-surface/30 p-6">
        <h3 className="text-sm font-medium text-vantyx-textPrimary mb-4">
          All Publishing Schedules ({schedules.length})
        </h3>
        {schedules.length === 0 ? (
          <div className="py-8 text-center text-xs text-vantyx-textSecondary">
            No publishing schedules recorded yet. Select an open slot above to schedule a short.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-vantyx-border text-vantyx-textSecondary font-mono">
                <tr>
                  <th className="pb-3">Slot / Local Time</th>
                  <th className="pb-3">Title</th>
                  <th className="pb-3">Channel</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">YouTube Video</th>
                  <th className="pb-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-vantyx-border/40 text-vantyx-textPrimary">
                {schedules.map((s) => (
                  <tr key={s.id} className="hover:bg-vantyx-surface/40">
                    <td className="py-3 font-mono">
                      {s.slot_name} IST ({new Date(s.scheduled_time).toISOString().split('T')[0]})
                    </td>
                    <td className="py-3 font-medium max-w-xs truncate">{s.title}</td>
                    <td className="py-3 text-vantyx-textSecondary">{s.target_channel}</td>
                    <td className="py-3">
                      <span
                        className={`rounded px-2 py-0.5 font-mono text-[10px] uppercase border ${
                          s.status === 'published'
                            ? 'border-emerald-500/30 bg-emerald-950/40 text-emerald-400'
                            : s.status === 'scheduled'
                            ? 'border-vantyx-accent/40 bg-vantyx-accent/10 text-vantyx-accent'
                            : 'border-slate-700 bg-slate-800 text-slate-400'
                        }`}
                      >
                        {s.status}
                      </span>
                    </td>
                    <td className="py-3 font-mono">
                      {s.youtube_video_id ? (
                        <a
                          href={s.publish_url || `https://youtube.com/shorts/${s.youtube_video_id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 text-vantyx-accent hover:underline"
                        >
                          {s.youtube_video_id}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                    <td className="py-3 text-right">
                      {s.status === 'scheduled' && (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handlePublishNow(s.id)}
                            disabled={publishingId === s.id}
                            className="rounded bg-vantyx-accent/20 border border-vantyx-accent/40 px-2 py-1 text-[11px] text-vantyx-accent hover:bg-vantyx-accent/30 transition disabled:opacity-50"
                          >
                            Publish
                          </button>
                          <button
                            onClick={() => handleCancelSchedule(s.id)}
                            className="rounded p-1 text-slate-400 hover:text-red-400 transition"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Schedule Assignment Modal */}
      {isScheduleModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-xl border border-vantyx-border bg-vantyx-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-4">
              <h2 className="text-lg font-medium text-white flex items-center gap-2">
                <Clock className="h-4 w-4 text-vantyx-accent" />
                Schedule Short for {selectedSlotName} IST
              </h2>
              <button
                onClick={() => setIsScheduleModalOpen(false)}
                className="text-vantyx-textSecondary hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSchedule} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-mono text-vantyx-textSecondary mb-1">
                  Target Publish Date & Slot
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="date"
                    value={targetDate}
                    onChange={(e) => setTargetDate(e.target.value)}
                    className="flex-1 rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-xs text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                    required
                  />
                  <select
                    value={selectedSlotName}
                    onChange={(e) => setSelectedSlotName(e.target.value)}
                    className="rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-xs font-mono text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                  >
                    <option value="09:00">09:00 IST</option>
                    <option value="13:00">13:00 IST</option>
                    <option value="17:00">17:00 IST</option>
                    <option value="21:00">21:00 IST</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono text-vantyx-textSecondary mb-1">
                  Select Completed Rendered Short
                </label>
                {completedJobs.length === 0 ? (
                  <div className="rounded border border-amber-500/30 bg-amber-950/20 p-3 text-xs text-amber-300">
                    No completed rendered shorts found. Go to Production to render an approved clip first.
                  </div>
                ) : (
                  <select
                    value={selectedJobId}
                    onChange={(e) => handleSelectJob(Number(e.target.value))}
                    className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-xs text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                    required
                  >
                    {completedJobs.map((j) => {
                      const c = candidates.find((cand) => cand.id === j.candidate_id);
                      return (
                        <option key={j.id} value={j.id}>
                          Job #{j.id} • {c?.title_suggestion || 'GTA 6 Moment'} (9:16 {j.layout_style})
                        </option>
                      );
                    })}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-xs font-mono text-vantyx-textSecondary mb-1">
                  Shorts Title (max 100 chars, includes #Shorts)
                </label>
                <input
                  type="text"
                  value={scheduleTitle}
                  onChange={(e) => setScheduleTitle(e.target.value)}
                  maxLength={100}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-xs text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-vantyx-textSecondary mb-1">
                  Custom Description (Optional, creator attribution is automatically appended)
                </label>
                <textarea
                  value={customDescription}
                  onChange={(e) => setCustomDescription(e.target.value)}
                  rows={2}
                  className="w-full rounded border border-vantyx-border bg-vantyx-bg px-3 py-2 text-xs text-vantyx-textPrimary focus:border-vantyx-accent focus:outline-none"
                  placeholder="Additional context or links..."
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-vantyx-border">
                <button
                  type="button"
                  onClick={() => setIsScheduleModalOpen(false)}
                  className="rounded px-4 py-2 text-xs text-vantyx-textSecondary hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={scheduling || completedJobs.length === 0}
                  className="rounded bg-vantyx-accent px-5 py-2 text-xs font-medium text-vantyx-bg hover:bg-vantyx-accent/90 transition disabled:opacity-50"
                >
                  {scheduling ? 'Scheduling...' : 'Confirm Schedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Google Cloud Console Setup Guide Modal */}
      {isGuideOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-xl rounded-xl border border-vantyx-border bg-vantyx-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-vantyx-border pb-4">
              <h2 className="text-base font-medium text-white flex items-center gap-2">
                <Youtube className="h-4 w-4 text-red-500" />
                Google Cloud Console & OAuth Setup Guide
              </h2>
              <button
                onClick={() => setIsGuideOpen(false)}
                className="text-vantyx-textSecondary hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="mt-4 space-y-4 text-xs text-vantyx-textSecondary leading-relaxed">
              <p>
                To enable live publishing to the <strong className="text-white">Astro Rebel</strong> YouTube channel, follow these steps in the Google Cloud Console:
              </p>

              <ol className="list-decimal pl-4 space-y-2">
                <li>
                  <strong className="text-white">Create/Select Project:</strong> In Google Cloud Console, select your project.
                </li>
                <li>
                  <strong className="text-white">Enable API:</strong> Navigate to <em>APIs & Services &gt; Library</em> and enable <span className="font-mono text-vantyx-accent">YouTube Data API v3</span>.
                </li>
                <li>
                  <strong className="text-white">OAuth Consent Screen:</strong> Set User Type to <em>External</em>, add the Astro Rebel Google account as a <em>Test User</em>, and add the scope <span className="font-mono text-vantyx-accent">https://www.googleapis.com/auth/youtube.upload</span>.
                </li>
                <li>
                  <strong className="text-white">Create Credentials:</strong> Go to <em>Credentials &gt; Create Credentials &gt; OAuth Client ID</em>, choose <em>Web application</em>, and add this Authorized Redirect URI:
                  <div className="mt-1 rounded bg-black/60 p-2 font-mono text-[11px] text-emerald-400 select-all border border-vantyx-border">
                    http://localhost:8000/api/v1/distribution/oauth/callback
                  </div>
                </li>
                <li>
                  <strong className="text-white">Environment Configuration:</strong> Add the generated credentials to your <span className="font-mono text-white">backend/.env</span>:
                  <pre className="mt-1 rounded bg-black/60 p-2 font-mono text-[11px] text-slate-300 border border-vantyx-border">
{`YOUTUBE_CLIENT_ID="your_client_id.apps.googleusercontent.com"
YOUTUBE_CLIENT_SECRET="your_client_secret"
YOUTUBE_REDIRECT_URI="http://localhost:8000/api/v1/distribution/oauth/callback"
MOCK_YOUTUBE_PUBLISHING=False`}
                  </pre>
                </li>
              </ol>

              <div className="rounded border border-vantyx-accent/30 bg-vantyx-accent/10 p-3 text-[11px] text-vantyx-accent">
                <strong>Safe Testing Mode:</strong> When OAuth credentials are not provided or <span className="font-mono">MOCK_YOUTUBE_PUBLISHING=True</span>, VANTYX automatically simulates uploads safely without making unauthenticated external calls.
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setIsGuideOpen(false)}
                className="rounded bg-vantyx-accent px-4 py-1.5 text-xs font-medium text-vantyx-bg hover:bg-vantyx-accent/90 transition"
              >
                Close Guide
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DistributionView;
