import React from 'react';
import { ConnectionState } from '@/types';

interface StatusBadgeProps {
  state: ConnectionState;
  showText?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ state, showText = true }) => {
  const config = {
    connected: {
      dot: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.3)]',
      text: 'text-emerald-400',
      label: 'Operational',
    },
    degraded: {
      dot: 'bg-vantyx-accent shadow-[0_0_8px_rgba(212,154,69,0.3)]',
      text: 'text-vantyx-accent',
      label: 'Degraded',
    },
    connecting: {
      dot: 'bg-neutral-500 animate-pulse',
      text: 'text-neutral-400',
      label: 'Connecting',
    },
    offline: {
      dot: 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.3)]',
      text: 'text-rose-400',
      label: 'Backend Offline',
    },
  }[state];

  return (
    <div className="inline-flex items-center gap-2 rounded border border-vantyx-border bg-vantyx-surface px-2.5 py-1 text-xs font-mono">
      <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
      {showText && <span className={`${config.text} text-[11px] tracking-wide`}>{config.label}</span>}
    </div>
  );
};
