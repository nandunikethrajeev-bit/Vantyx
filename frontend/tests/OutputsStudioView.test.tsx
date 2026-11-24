import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { OutputsStudioView } from '@/features/outputs/OutputsStudioView';

vi.mock('@/lib/api', () => ({
  fetchUnifiedOutputs: vi.fn().mockResolvedValue([
    {
      job_id: 101,
      candidate_id: 201,
      source_id: 301,
      status: 'completed',
      progress_pct: 100,
      resolution: '1080x1920',
      layout_style: 'smart_crop',
      format_aspect: '9:16',
      has_burned_subtitles: true,
      is_synthetic: true,
      created_at: new Date().toISOString(),
      output_file_path: 'data/exports/test_render_101.mp4',
      file_exists: true,
      file_size_mb: 4.8,
      source_title: 'Downtown Helicopter Heist Raw',
      source_url: 'https://youtube.com/watch?v=heist123',
      video_id: 'heist123',
      clip_title: 'Incredible Heli Evasion 360 Spin',
      duration_seconds: 24.5,
      overall_score: 0.92,
      hook_score: 0.95,
      retention_score: 0.89,
      context_score: 0.85,
      audio_score: 0.91,
      approval_status: 'approved',
      error_message: null,
    },
  ]),
  getRenderStreamUrl: vi.fn().mockReturnValue('/api/v1/production/jobs/101/stream'),
  getRenderThumbnailUrl: vi.fn().mockReturnValue('/api/v1/production/jobs/101/thumbnail'),
  getRenderDownloadUrl: vi.fn().mockReturnValue('/api/v1/production/jobs/101/download'),
}));

describe('OutputsStudioView', () => {
  it('renders the Unified Outputs Studio and output cards', async () => {
    render(<OutputsStudioView />);

    expect(screen.getByText('Unified Outputs Studio')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Incredible Heli Evasion 360 Spin')).toBeInTheDocument();
      expect(screen.getByText('From: Downtown Helicopter Heist Raw')).toBeInTheDocument();
      expect(screen.getByText('Preview Short')).toBeInTheDocument();
    });

    expect(screen.getByText('SYNTHETIC')).toBeInTheDocument();
  });

  it('opens video preview modal on preview click', async () => {
    render(<OutputsStudioView />);

    await waitFor(() => {
      expect(screen.getByText('Preview Short')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Preview Short'));
    expect(screen.getByText('Download MP4')).toBeInTheDocument();
  });
});
