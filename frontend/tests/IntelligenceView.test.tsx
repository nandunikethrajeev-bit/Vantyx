import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { IntelligenceView } from '@/features/intelligence/IntelligenceView';
import * as api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  fetchVideoSources: vi.fn(),
  fetchAnalysisJobs: vi.fn(),
  triggerVideoAnalysis: vi.fn(),
}));

describe('IntelligenceView', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.fetchVideoSources).mockResolvedValue([
      {
        id: 101,
        video_id: 'gta_vid_1',
        title: 'GTA 6 Bank Escape Supercut',
        duration_seconds: 360,
        source_url: 'https://youtube.com/watch?v=gta_vid_1',
        discovery_method: 'feed_ingest',
        is_eligible: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);

    vi.mocked(api.fetchAnalysisJobs).mockResolvedValue([
      {
        id: 1,
        source_id: 101,
        status: 'completed',
        provider: 'heuristic',
        scene_count: 2,
        scenes: [
          {
            id: 201,
            job_id: 1,
            source_id: 101,
            start_time: 15.0,
            end_time: 60.0,
            duration_seconds: 45.0,
            scene_label: 'Epic Vault Breach',
            speech_transcript: 'Vault open, grab the loot and go!',
            action_intensity: 0.9,
            excitement_score: 0.95,
            tags: ['heist', 'intense_action'],
            created_at: new Date().toISOString(),
          },
        ],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);
  });

  it('renders intelligence workspace with segmented scenes', async () => {
    render(<IntelligenceView />);

    await waitFor(() => {
      expect(screen.getByText('Epic Vault Breach')).toBeInTheDocument();
      expect(screen.getByText(/Vault open, grab the loot and go!/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/AI Multimodal Intelligence Engine/i)).toBeInTheDocument();
    expect(screen.getByText('#heist')).toBeInTheDocument();
    expect(screen.getByText('95%')).toBeInTheDocument();
  });

  it('displays transparency notice when heuristic provider is active', async () => {
    render(<IntelligenceView />);

    await waitFor(() => {
      expect(screen.getByText(/Heuristic Metadata Segmentation Active/i)).toBeInTheDocument();
      expect(screen.getByText(/GEMINI_API_KEY/i)).toBeInTheDocument();
    });
  });
});
