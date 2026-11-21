import React from 'react';
import {
  LayoutDashboard,
  Radio,
  Cpu,
  Sparkles,
  Scissors,
  Share2,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  Database,
  Server,
} from 'lucide-react';
import { NavigationSection, ConnectionState } from '@/types';
import { BrandMark } from '../ui/BrandMark';

interface SidebarProps {
  currentSection: NavigationSection;
  onSelectSection: (section: NavigationSection) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  connectionState: ConnectionState;
}

interface NavItem {
  id: NavigationSection;
  label: string;
  icon: React.ElementType;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'discovery', label: 'Discovery', icon: Radio, badge: 'M02' },
  { id: 'intelligence', label: 'Intelligence', icon: Cpu, badge: 'M03' },
  { id: 'selection', label: 'Selection', icon: Sparkles, badge: 'M04' },
  { id: 'production', label: 'Production', icon: Scissors, badge: 'M05' },
  { id: 'distribution', label: 'Distribution', icon: Share2, badge: 'M06' },
  { id: 'analytics', label: 'Analytics', icon: BarChart3, badge: 'M07' },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentSection,
  onSelectSection,
  collapsed,
  onToggleCollapse,
  connectionState,
}) => {
  return (
    <aside
      className={`relative flex flex-col border-r border-vantyx-border bg-vantyx-surface/50 backdrop-blur-sm transition-all duration-300 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between border-b border-vantyx-border px-4">
        <BrandMark collapsed={collapsed} />
        <button
          onClick={onToggleCollapse}
          className="flex h-7 w-7 items-center justify-center rounded text-vantyx-textMuted transition-colors hover:bg-vantyx-surfaceElevated hover:text-vantyx-textPrimary"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 space-y-1.5 p-3">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = currentSection === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onSelectSection(item.id)}
              className={`group flex w-full items-center gap-3 rounded px-3 py-2 text-xs font-medium transition-all ${
                isActive
                  ? 'bg-vantyx-surfaceElevated text-vantyx-textPrimary border border-vantyx-border'
                  : 'text-vantyx-textSecondary hover:bg-vantyx-surface hover:text-vantyx-textPrimary'
              }`}
              title={collapsed ? item.label : undefined}
            >
              <Icon
                size={16}
                className={`transition-colors shrink-0 ${
                  isActive ? 'text-vantyx-accent' : 'text-vantyx-textMuted group-hover:text-vantyx-textSecondary'
                }`}
              />
              {!collapsed && (
                <div className="flex flex-1 items-center justify-between">
                  <span>{item.label}</span>
                  {item.badge && (
                    <span className="font-mono text-[9px] text-vantyx-textMuted border border-vantyx-border px-1.5 py-0.5 rounded">
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </nav>

      {/* System Status Footprint */}
      <div className="border-t border-vantyx-border p-3">
        {!collapsed ? (
          <div className="rounded border border-vantyx-border bg-vantyx-bg/70 p-2.5 font-mono text-[11px]">
            <div className="flex items-center justify-between text-vantyx-textMuted mb-1.5">
              <span>SYSTEM ARCH</span>
              <span className="text-[10px] text-vantyx-accent">M01</span>
            </div>
            <div className="space-y-1 text-vantyx-textSecondary">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Server size={12} className="text-vantyx-textMuted" /> API
                </span>
                <span className={connectionState === 'offline' ? 'text-rose-400' : 'text-emerald-400'}>
                  {connectionState === 'offline' ? 'Offline' : 'Online'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Database size={12} className="text-vantyx-textMuted" /> Database
                </span>
                <span className={connectionState === 'connected' ? 'text-emerald-400' : 'text-vantyx-accent'}>
                  {connectionState === 'connected' ? 'Ready' : 'Pending'}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <span
              className={`h-2 w-2 rounded-full ${
                connectionState === 'connected'
                  ? 'bg-emerald-500'
                  : connectionState === 'degraded'
                  ? 'bg-vantyx-accent'
                  : 'bg-rose-500'
              }`}
              title={`System Status: ${connectionState}`}
            />
          </div>
        )}
      </div>
    </aside>
  );
};
