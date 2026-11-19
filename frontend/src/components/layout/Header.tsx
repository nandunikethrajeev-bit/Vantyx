import React from 'react';
import { RefreshCw } from 'lucide-react';
import { StatusBadge } from '../ui/StatusBadge';
import { ConnectionState, NavigationSection } from '@/types';

interface HeaderProps {
  currentSection: NavigationSection;
  connectionState: ConnectionState;
  isChecking: boolean;
  onRefresh: () => void;
  lastChecked: Date | null;
}

const SECTION_TITLES: Record<NavigationSection, { title: string; subtitle: string }> = {
  overview: {
    title: 'Platform Foundation',
    subtitle: 'System core status and architectural verification',
  },
  discovery: {
    title: 'Source Discovery',
    subtitle: 'Creator ingestion pipelines and rights validation (Milestone 02)',
  },
  intelligence: {
    title: 'Media Intelligence',
    subtitle: 'Multimodal analysis and semantic scene indexing (Milestone 03)',
  },
  production: {
    title: 'Shorts Production',
    subtitle: 'Dynamic 9:16 vertical re-framing and composition (Milestone 05)',
  },
  distribution: {
    title: 'Channel Distribution',
    subtitle: 'Release queues and authorized publishing pipelines (Milestone 06)',
  },
  analytics: {
    title: 'Audience Intelligence',
    subtitle: 'Retention metrics and feedback loop optimization (Milestone 07)',
  },
  settings: {
    title: 'System Configuration',
    subtitle: 'Environment boundaries, credentials and security parameters',
  },
};

export const Header: React.FC<HeaderProps> = ({
  currentSection,
  connectionState,
  isChecking,
  onRefresh,
  lastChecked,
}) => {
  const current = SECTION_TITLES[currentSection];

  return (
    <header className="flex h-16 items-center justify-between border-b border-vantyx-border bg-vantyx-bg px-8">
      {/* Workspace Context */}
      <div>
        <h1 className="text-sm font-semibold tracking-wide text-vantyx-textPrimary">
          {current.title}
        </h1>
        <p className="text-[11px] text-vantyx-textMuted tracking-normal">
          {current.subtitle}
        </p>
      </div>

      {/* Real-time System Connectivity Area */}
      <div className="flex items-center gap-3">
        <StatusBadge state={connectionState} />

        <button
          onClick={onRefresh}
          disabled={isChecking}
          className="flex h-7 w-7 items-center justify-center rounded border border-vantyx-border bg-vantyx-surface text-vantyx-textMuted transition-colors hover:border-vantyx-accent/40 hover:text-vantyx-textPrimary disabled:opacity-50"
          title={`Refresh health probes (last checked: ${
            lastChecked ? lastChecked.toLocaleTimeString() : 'never'
          })`}
          aria-label="Refresh health probe"
        >
          <RefreshCw size={13} className={isChecking ? 'animate-spin text-vantyx-accent' : ''} />
        </button>
      </div>
    </header>
  );
};
