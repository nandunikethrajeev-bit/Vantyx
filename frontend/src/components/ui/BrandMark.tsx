import React from 'react';

interface BrandMarkProps {
  collapsed?: boolean;
}

export const BrandMark: React.FC<BrandMarkProps> = ({ collapsed = false }) => {
  return (
    <div className="flex items-center gap-3 select-none">
      {/* Monogram Symbol: Minimal geometric aperture / lens */}
      <div className="relative flex h-8 w-8 items-center justify-center rounded border border-vantyx-border bg-vantyx-surface">
        <div className="h-3 w-3 rotate-45 border border-vantyx-accent transition-transform duration-300 hover:rotate-90" />
        <div className="absolute h-1 w-1 rounded-full bg-vantyx-accent" />
      </div>

      {!collapsed && (
        <div className="flex flex-col">
          <span className="font-mono text-sm font-semibold tracking-widest text-vantyx-textPrimary">
            VANTYX
          </span>
          <span className="text-[10px] font-normal tracking-wider text-vantyx-textMuted uppercase">
            Intelligence
          </span>
        </div>
      )}
    </div>
  );
};
