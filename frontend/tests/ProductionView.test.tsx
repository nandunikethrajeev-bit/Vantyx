import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ProductionView } from '@/features/production/ProductionView';
import * as api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  fetchRenderJobs: vi.fn(),
  fetchCandidates: vi.fn(),
  triggerRender: vi.fn(),
  getRenderStreamUrl: vi.fn((id: number) => `/api/v1/production/jobs/${id}/stream`),
  getRenderThumbnailUrl: vi.fn((id: number) => `/api/v1/production/jobs/${id}/thumbnail`),
}));

describe('ProductionView', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.fetchRenderJobs).mockResolvedValue([
      {
        id: 101,
        candidate_id: 1,
        source_id: 10,
        status: 'completed',
        progress_pct: 100.0,
        output_file_path: '/path/to/vantyx_short_1.mp4',
        thumbnail_path: '/path/to/vantyx_thumb_1.jpg',
        resolution: '1080x1920',
        format_aspect: '9:16',
        layout_style: 'blurred_backdrop',
        has_burned_subtitles: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);
    vi.mocked(api.fetchCandidates).mockResolvedValue([
      {
        id: 1,
        source_id: 10,
        start_time: 15.0,
        end_time: 55.0,
        duration_seconds: 40.0,
        title_suggestion: 'GTA 6 Stunt Escapes Police Chopper',
        hook_score: 90.0,
        retention_score: 88.0,
        context_score: 85.0,
        audio_score: 80.0,
        overall_score: 87.5,
        status: 'approved',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);
  });

  it('renders production engine workspace and job cards', async () => {
    render(<ProductionView />);

    expect(screen.getByText('Shorts Production Engine')).toBeInTheDocument();
    expect(screen.getByText('M05 ACTIVE')).toBeInTheDocument();
    expect(screen.getByText('Ready to Render')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Job #101')).toBeInTheDocument();
      expect(screen.getByText('Preview Short')).toBeInTheDocument();
      expect(screen.getByText('GTA 6 Stunt Escapes Police Chopper')).toBeInTheDocument();
    });
  });

  it('opens video preview modal on preview click', async () => {
    render(<ProductionView />);

    await waitFor(() => {
      expect(screen.getByText('Preview Short')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Preview Short'));

    await waitFor(() => {
      expect(screen.getByText(/Short Preview \(Job #101\)/)).toBeInTheDocument();
    });
  });
});
