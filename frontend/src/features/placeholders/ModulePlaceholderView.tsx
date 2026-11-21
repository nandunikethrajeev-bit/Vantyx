import React from 'react';
import { Layers } from 'lucide-react';
import { NavigationSection } from '@/types';

interface ModulePlaceholderViewProps {
  section: NavigationSection;
}

const MODULE_DETAILS: Record<
  NavigationSection,
  {
    name: string;
    milestone: string;
    description: string;
    plannedResponsibilities: string[];
  }
> = {
  overview: {
    name: 'Overview',
    milestone: 'Milestone 01',
    description: 'System foundation and architecture.',
    plannedResponsibilities: [],
  },
  discovery: {
    name: 'Discovery Module',
    milestone: 'Milestone 02',
    description: 'Autonomous video discovery and source permission validation.',
    plannedResponsibilities: [
      'Approved creator registry and channel monitoring',
      'Commercial-use rights and licensing verification',
      'Attribution tracking and source origin metadata storage',
      'Candidate gameplay video ingestion queuing',
    ],
  },
  intelligence: {
    name: 'Intelligence Module',
    milestone: 'Milestone 03',
    description: 'Multimodal AI video understanding and semantic feature indexing.',
    plannedResponsibilities: [
      'Visual scene boundary segmentation',
      'Speech transcription and acoustic intensity scoring',
      'Gameplay action classification (heists, pursuits, cinematic moments)',
      'Candidate moment metadata synthesis',
    ],
  },
  selection: {
    name: 'Selection Module',
    milestone: 'Milestone 04',
    description: 'Intelligent candidate clip scoring and non-overlapping ranking.',
    plannedResponsibilities: [
      'Hook strength and retention curve scoring',
      'Narrative context completeness evaluation',
      'Timestamp overlap resolution',
      'Daily 4-Shorts quota target management',
    ],
  },
  production: {
    name: 'Production Module',
    milestone: 'Milestone 05',
    description: 'High-quality vertical video synthesis and audio mastering.',
    plannedResponsibilities: [
      'Intelligent 9:16 reframing with subject tracking',
      'Dynamic typography and subtitle rendering',
      'Cinematic color grading and audio normalization',
      'Isolated render worker dispatch',
    ],
  },
  distribution: {
    name: 'Distribution Module',
    milestone: 'Milestone 06',
    description: 'Channel authorization, scheduling, and publication dispatch.',
    plannedResponsibilities: [
      'YouTube Data API OAuth2 token rotation and scope limits',
      'Editorial release calendar and scheduled queue',
      'Title, description, and hashtag optimization',
      'Publication confirmation and permalink tracking',
    ],
  },
  analytics: {
    name: 'Analytics Module',
    milestone: 'Milestone 07',
    description: 'Audience retention analysis and selection feedback loops.',
    plannedResponsibilities: [
      'YouTube Analytics API metric ingestion',
      'Average percentage viewed (APV) correlation',
      'Hook retention curve modeling',
      'Moment selection weight adjustment feedback loop',
    ],
  },
  settings: {
    name: 'Settings & Security',
    milestone: 'Milestone 01',
    description: 'System configuration and environment isolation parameters.',
    plannedResponsibilities: [
      'Environment variable inspection',
      'CORS origin whitelist inspection',
      'Database connection string verification',
      'Logging verbosity and credential masking filters',
    ],
  },
};

export const ModulePlaceholderView: React.FC<ModulePlaceholderViewProps> = ({ section }) => {
  const details = MODULE_DETAILS[section];

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      {/* Module Header */}
      <div className="border-b border-vantyx-border pb-6">
        <div className="flex items-center gap-2 text-xs font-mono text-vantyx-accent uppercase tracking-wider mb-2">
          <span>{details.milestone}</span>
          <span>•</span>
          <span>Pending Implementation</span>
        </div>
        <h2 className="text-xl font-light text-vantyx-textPrimary">{details.name}</h2>
        <p className="mt-1 text-sm text-vantyx-textSecondary">{details.description}</p>
      </div>

      {/* Honest Boundary Notice */}
      <div className="rounded border border-vantyx-border bg-vantyx-surface/50 p-5 space-y-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded border border-vantyx-border bg-vantyx-surfaceElevated text-vantyx-accent">
            <Layers size={16} />
          </div>
          <div>
            <h3 className="text-xs font-mono font-medium text-vantyx-textPrimary uppercase">
              Architectural Boundary Established
            </h3>
            <p className="text-[11px] text-vantyx-textMuted mt-0.5">
              Backend service interface exists in <code className="text-vantyx-textSecondary">app/modules/{section}/service.py</code>
            </p>
          </div>
        </div>

        <p className="text-xs text-vantyx-textSecondary leading-relaxed">
          In adherence to Milestone 01 engineering discipline, this automation engine is not simulated with
          fake data or decorative UI cards. The concrete business logic and external integrations belong to{' '}
          <strong className="text-vantyx-accent font-mono">{details.milestone}</strong>.
        </p>

        {details.plannedResponsibilities.length > 0 && (
          <div className="pt-3 border-t border-vantyx-borderSubtle">
            <h4 className="text-[11px] font-mono uppercase text-vantyx-textMuted mb-2">
              Planned Capabilities ({details.milestone})
            </h4>
            <ul className="space-y-1.5 text-xs text-vantyx-textSecondary font-mono">
              {details.plannedResponsibilities.map((item, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <span className="h-1 w-1 rounded-full bg-vantyx-accent" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
