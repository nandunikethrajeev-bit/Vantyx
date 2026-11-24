import React, { useState, useEffect } from 'react';
import {
  Film,
  Play,
  Download,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  RefreshCw,
  Search,
  Filter,
  X,
} from 'lucide-react';
import {
  fetchUnifiedOutputs,
  getRenderStreamUrl,
  getRenderThumbnailUrl,
  getRenderDownloadUrl,
} from '@/lib/api';
import { UnifiedOutputItem, NavigationSection } from '@/types';

interface OutputsStudioViewProps {
  onNavigate?: (section: NavigationSection) => void;
}

export const OutputsStudioView: React.FC<OutputsStudioViewProps> = ({ onNavigate }) => {
  const [outputs, setOutputs] = useState<UnifiedOutputItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activePreview, setActivePreview] = useState<UnifiedOutputItem | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadOutputs = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const data = await fetchUnifiedOutputs(60);
      setOutputs(data);
    } catch (err: any) {
      if (!silent) {
        setErrorMessage(`Failed to load outputs: ${err.message || 'Server error'}`);
      }
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    loadOutputs();
  }, []);

  const filteredOutputs = outputs.filter((item) => {
    if (filterStatus !== 'all' && item.status !== filterStatus) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = item.clip_title.toLowerCase().includes(q);
      const matchSource = item.source_title.toLowerCase().includes(q);
      const matchId = String(item.job_id).includes(q) || item.video_id.toLowerCase().includes(q);
      return matchTitle || matchSource || matchId;
    }
    return true;
  });

  const totalCompleted = outputs.filter((o) => o.status === 'completed' && o.file_exists).length;
  const totalMb = outputs.reduce((sum, o) => sum + (o.file_size_mb || 0), 0);

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="border-b border-neutral-800 pb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
                <Film className="w-4 h-4" />
              </span>
              <h1 className="text-2xl font-semibold tracking-tight text-white font-serif">
                Unified Outputs Studio
              </h1>
            </div>
            <p className="mt-1 text-sm text-neutral-400">
              Inspect, stream, and download production-ready 9:16 vertical Shorts generated through the autonomous pipeline.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {onNavigate && (
              <button
                onClick={() => onNavigate('url_workspace')}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded-lg transition-colors"
              >
                <Sparkles className="w-4 h-4" />
                Open URL Studio
              </button>
            )}
            <button
              onClick={() => loadOutputs(false)}
              disabled={loading}
              className="p-2 bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 rounded-lg text-neutral-400 hover:text-white transition-colors"
              title="Refresh Outputs"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-4">
            <span className="text-xs text-neutral-400">Total Outputs</span>
            <p className="text-xl font-bold text-white mt-1">{outputs.length}</p>
          </div>
          <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-4">
            <span className="text-xs text-emerald-400">Verified On Disk</span>
            <p className="text-xl font-bold text-emerald-400 mt-1">{totalCompleted}</p>
          </div>
          <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-4">
            <span className="text-xs text-amber-400">Total Storage</span>
            <p className="text-xl font-bold text-amber-400 mt-1">{totalMb.toFixed(1)} MB</p>
          </div>
          <div className="bg-neutral-900/60 border border-neutral-800 rounded-xl p-4">
            <span className="text-xs text-indigo-400">Output Standard</span>
            <p className="text-sm font-bold text-neutral-200 mt-1.5 font-mono">1080×1920 • 9:16 HD</p>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-800/40 text-rose-300 text-sm flex items-center justify-between">
          <span>{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="text-xs text-neutral-400 hover:text-white">
            Dismiss
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by clip title, source, or ID..."
            className="w-full bg-neutral-900 border border-neutral-800 rounded-xl pl-9 pr-4 py-2 text-xs text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-neutral-700"
          />
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Filter className="w-4 h-4 text-neutral-400" />
          <div className="flex rounded-lg bg-neutral-900 p-1 border border-neutral-800 text-xs">
            {['all', 'completed', 'processing', 'failed'].map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`px-3 py-1 rounded-md capitalize transition-colors ${
                  filterStatus === st
                    ? 'bg-amber-500 text-neutral-950 font-medium'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Outputs Gallery Grid */}
      {filteredOutputs.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredOutputs.map((item) => (
            <div
              key={item.job_id}
              className="bg-neutral-900/60 border border-neutral-800 rounded-2xl overflow-hidden shadow-lg hover:border-neutral-700 transition-all flex flex-col justify-between"
            >
              {/* Media Preview Box (9:16 Aspect ratio container) */}
              <div className="relative aspect-[9/16] max-h-72 w-full bg-neutral-950 overflow-hidden flex items-center justify-center group">
                <img
                  src={getRenderThumbnailUrl(item.job_id)}
                  alt={item.clip_title}
                  className="w-full h-full object-cover transition-transform group-hover:scale-105 duration-300"
                  onError={(e) => {
                    // Fallback to placeholder if thumbnail is missing
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />

                {/* Overlay Play Button */}
                {item.status === 'completed' && item.file_exists ? (
                  <button
                    onClick={() => setActivePreview(item)}
                    className="absolute inset-0 flex items-center justify-center bg-black/40 group-hover:bg-black/20 transition-all"
                  >
                    <span className="w-12 h-12 rounded-full bg-amber-500/90 text-neutral-950 flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform">
                      <Play className="w-5 h-5 fill-current ml-0.5" />
                    </span>
                  </button>
                ) : (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 p-4 text-center">
                    <AlertCircle className="w-8 h-8 text-neutral-500 mb-2" />
                    <span className="text-xs text-neutral-400">
                      {item.status === 'processing'
                        ? 'Rendering in progress...'
                        : item.error_message || 'Video file not available'}
                    </span>
                  </div>
                )}

                {/* Top Badges */}
                <div className="absolute top-3 left-3 flex flex-wrap gap-1.5">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-black/80 text-white border border-neutral-800 backdrop-blur-sm">
                    {item.resolution || '1080x1920'}
                  </span>
                  {item.is_synthetic && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30 backdrop-blur-sm">
                      SYNTHETIC
                    </span>
                  )}
                </div>

                {/* Duration Badge */}
                <div className="absolute bottom-3 right-3">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-black/80 text-neutral-200 border border-neutral-800 backdrop-blur-sm">
                    {item.duration_seconds.toFixed(1)}s
                  </span>
                </div>
              </div>

              {/* Details Content */}
              <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
                <div>
                  <h3 className="font-semibold text-white text-sm line-clamp-1" title={item.clip_title}>
                    {item.clip_title}
                  </h3>
                  <p className="text-xs text-neutral-400 line-clamp-1 mt-0.5" title={item.source_title}>
                    From: {item.source_title}
                  </p>
                </div>

                {/* Moment Scores Grid */}
                <div className="grid grid-cols-4 gap-1.5 p-2 bg-neutral-950/80 rounded-xl border border-neutral-800 text-center font-mono">
                  <div>
                    <span className="text-[9px] uppercase tracking-wider text-neutral-500 block">PTS</span>
                    <span className="text-xs font-semibold text-amber-400">
                      {(item.overall_score * 100).toFixed(0)}
                    </span>
                  </div>
                  <div>
                    <span className="text-[9px] uppercase tracking-wider text-neutral-500 block">Hook</span>
                    <span className="text-xs font-semibold text-neutral-300">
                      {(item.hook_score * 100).toFixed(0)}
                    </span>
                  </div>
                  <div>
                    <span className="text-[9px] uppercase tracking-wider text-neutral-500 block">Ret</span>
                    <span className="text-xs font-semibold text-neutral-300">
                      {(item.retention_score * 100).toFixed(0)}
                    </span>
                  </div>
                  <div>
                    <span className="text-[9px] uppercase tracking-wider text-neutral-500 block">Audio</span>
                    <span className="text-xs font-semibold text-indigo-400">
                      {(item.audio_score * 100).toFixed(0)}
                    </span>
                  </div>
                </div>

                {/* Verification & Storage Indicator */}
                <div className="flex items-center justify-between text-xs pt-1 border-t border-neutral-800/80">
                  <div className="flex items-center gap-1.5">
                    {item.file_exists ? (
                      <>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                        <span className="text-emerald-400 font-medium">Ready ({item.file_size_mb} MB)</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                        <span className="text-rose-400">Missing File</span>
                      </>
                    )}
                  </div>

                  <span className="text-[11px] text-neutral-500 font-mono">Job #{item.job_id}</span>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-2 pt-1">
                  {item.status === 'completed' && item.file_exists && (
                    <>
                      <button
                        onClick={() => setActivePreview(item)}
                        className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-medium rounded-xl transition-colors"
                      >
                        <Play className="w-3.5 h-3.5 fill-current" />
                        Preview Short
                      </button>

                      <a
                        href={getRenderDownloadUrl(item.job_id)}
                        download
                        className="inline-flex items-center justify-center p-2 bg-amber-500 hover:bg-amber-400 text-neutral-950 rounded-xl transition-colors"
                        title="Download MP4"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-neutral-900/40 border border-neutral-800/80 rounded-2xl p-16 text-center">
          <Film className="w-12 h-12 text-neutral-600 mx-auto mb-4" />
          <h3 className="text-base font-medium text-neutral-200">No output Shorts found</h3>
          <p className="text-xs text-neutral-500 mt-1 max-w-md mx-auto">
            {searchQuery || filterStatus !== 'all'
              ? 'No rendered Shorts matched your filter criteria.'
              : 'Submit YouTube URLs in the Autonomous URL Studio to analyze footage, identify top moments, and render 9:16 Shorts.'}
          </p>
          {onNavigate && (
            <button
              onClick={() => onNavigate('url_workspace')}
              className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-neutral-950 text-xs font-medium rounded-xl transition-colors shadow-lg"
            >
              <Sparkles className="w-4 h-4" />
              Go to URL Studio
            </button>
          )}
        </div>
      )}

      {/* Video Preview Modal */}
      {activePreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
              <div>
                <h3 className="font-semibold text-white text-base">{activePreview.clip_title}</h3>
                <p className="text-xs text-neutral-400 mt-0.5">{activePreview.source_title}</p>
              </div>
              <button
                onClick={() => setActivePreview(null)}
                className="p-1 rounded-lg hover:bg-neutral-800 text-neutral-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Video Player */}
            <div className="relative aspect-[9/16] max-h-[550px] mx-auto bg-black rounded-xl overflow-hidden shadow-2xl flex items-center justify-center">
              <video
                src={getRenderStreamUrl(activePreview.job_id)}
                controls
                autoPlay
                className="w-full h-full object-contain"
              />
            </div>

            {/* Modal Footer Controls */}
            <div className="flex items-center justify-between pt-3 border-t border-neutral-800">
              <div className="text-xs text-neutral-400 font-mono">
                {activePreview.resolution} • {activePreview.duration_seconds.toFixed(1)}s •{' '}
                {activePreview.file_size_mb} MB
              </div>

              <div className="flex items-center gap-3">
                <a
                  href={getRenderDownloadUrl(activePreview.job_id)}
                  download
                  className="inline-flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-400 text-neutral-950 text-xs font-medium rounded-xl transition-colors shadow"
                >
                  <Download className="w-4 h-4" />
                  Download MP4
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
