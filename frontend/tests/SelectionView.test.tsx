import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SelectionView } from '@/features/selection/SelectionView';
import * as api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  fetchCandidates: vi.fn(),
  fetchDailyQueue: vi.fn(),
  fetchVideoSources: vi.fn(),
  updateCandidate: vi.fn(),
  generateCandidates: vi.fn(),
}));

describe('SelectionView', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.fetchCandidates).mockResolvedValue([
      {
        id: 1,
        source_id: 10,
        scene_id: 1,
        start_time: 15.0,
        end_time: 55.0,
        duration_seconds: 40.0,
        title_suggestion: 'GTA 6: Police Helicopter Evade #Shorts',
        hook_score: 88.0,
        retention_score: 92.0,
        context_score: 90.0,
        audio_score: 85.0,
        overall_score: 89.2,
        status: 'candidate',
        rationale: 'High hook velocity (88/100). Optimal Shorts duration (40.0s). Rich audio/speech.',
        video_title: 'Full Mission Playthrough',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);
    vi.mocked(api.fetchDailyQueue).mockResolvedValue({
      target_count: 4,
      selected_count: 1,
      has_sufficient_moments: false,
      candidates: [],
    });
    vi.mocked(api.fetchVideoSources).mockResolvedValue([
      {
        id: 10,
        video_id: 'vid_123',
        title: 'Full Mission Playthrough',
        duration_seconds: 360,
        source_url: 'https://youtube.com/watch?v=vid_123',
        discovery_method: 'manual',
        is_eligible: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);
  });

  it('renders daily quota banner and candidate cards', async () => {
    render(<SelectionView />);

    expect(screen.getByText('Intelligent Clip Selection')).toBeInTheDocument();
    expect(screen.getByText('Daily YouTube Shorts Quota')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('GTA 6: Police Helicopter Evade #Shorts')).toBeInTheDocument();
      expect(screen.getByText('89.2 PTS')).toBeInTheDocument();
      expect(screen.getByText(/Optimal Shorts duration/)).toBeInTheDocument();
    });
  });

  it('allows approving candidate clips', async () => {
    vi.mocked(api.updateCandidate).mockResolvedValue({
      id: 1,
      source_id: 10,
      start_time: 15.0,
      end_time: 55.0,
      duration_seconds: 40.0,
      title_suggestion: 'GTA 6: Police Helicopter Evade #Shorts',
      hook_score: 88.0,
      retention_score: 92.0,
      context_score: 90.0,
      audio_score: 85.0,
      overall_score: 89.2,
      status: 'approved',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    render(<SelectionView />);

    await waitFor(() => {
      expect(screen.getByText('Approve')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Approve'));

    await waitFor(() => {
      expect(api.updateCandidate).toHaveBeenCalledWith(1, { status: 'approved' });
    });
  });
});
