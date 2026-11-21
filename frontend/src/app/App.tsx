import React, { useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { OverviewView } from '@/features/overview/OverviewView';
import { DiscoveryView } from '@/features/discovery/DiscoveryView';
import { ModulePlaceholderView } from '@/features/placeholders/ModulePlaceholderView';
import { useSystemHealth } from '@/hooks/useSystemHealth';
import { NavigationSection } from '@/types';

export const App: React.FC = () => {
  const [currentSection, setCurrentSection] = useState<NavigationSection>('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);

  const {
    connectionState,
    liveness,
    readiness,
    errorMessage,
    isChecking,
    lastChecked,
    refresh,
  } = useSystemHealth(12000);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-vantyx-bg text-vantyx-textPrimary">
      {/* Collapsible Left Navigation Sidebar */}
      <Sidebar
        currentSection={currentSection}
        onSelectSection={setCurrentSection}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        connectionState={connectionState}
      />

      {/* Main Content Workspace */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Workspace Top Header */}
        <Header
          currentSection={currentSection}
          connectionState={connectionState}
          isChecking={isChecking}
          onRefresh={refresh}
          lastChecked={lastChecked}
        />

        {/* Central Workspace Scroll Area */}
        <main className="flex-1 overflow-y-auto px-8 py-8">
          {currentSection === 'overview' && (
            <OverviewView
              connectionState={connectionState}
              liveness={liveness}
              readiness={readiness}
              errorMessage={errorMessage}
            />
          )}
          {currentSection === 'discovery' && <DiscoveryView />}
          {currentSection !== 'overview' && currentSection !== 'discovery' && (
            <ModulePlaceholderView section={currentSection} />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
