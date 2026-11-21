import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DistributionView } from '@/features/distribution/DistributionView';
import * as api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  fetchChannelStatus: vi.fn(),
  fetchOAuthUrl: vi.fn(),
  fetchDailySlots: vi.fn(),
  fetchSchedules: vi.fn(),
  disconnectChannel: vi.fn(),
  createSchedule: vi.fn(),
  cancelSchedule: vi.fn(),
  triggerPublish: vi.fn(),
  fetchRenderJobs: vi.fn(),
  fetchCandidates: vi.fn(),
}));

describe('DistributionView', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.fetchChannelStatus).mockResolvedValue({
      id: 1,
      channel_id: 'UC_astro_rebel_official',
      channel_title: 'Astro Rebel',
      channel_handle: '@astrorebel',
      thumbnail_url: null,
      is_active: true,
      connected_at: '2026-11-20T10:00:00Z',
    });

    vi.mocked(api.fetchOAuthUrl).mockResolvedValue({
      configured: true,
      auth_url: 'https://accounts.google.com/o/oauth2/v2/auth?test',
      message: 'Configured',
    });

    vi.mocked(api.fetchDailySlots).mockResolvedValue({
      target_date: '2026-11-21',
      timezone: 'Asia/Kolkata',
      slots: [
        {
          slot_name: '09:00',
          scheduled_time_utc: '2026-11-21T03:30:00Z',
          scheduled_time_local: '2026-11-21 09:00:00 IST',
          status: 'unfilled',
          schedule: null,
        },
        {
          slot_name: '13:00',
          scheduled_time_utc: '2026-11-21T07:30:00Z',
          scheduled_time_local: '2026-11-21 13:00:00 IST',
          status: 'scheduled',
          schedule: {
            id: 201,
            candidate_id: 1,
            render_job_id: 101,
            scheduled_time: '2026-11-21T07:30:00Z',
            slot_name: '13:00',
            timezone: 'Asia/Kolkata',
            target_channel: 'Astro Rebel',
            title: 'GTA 6 Bank Heist Getaway #Shorts',
            description: 'Gameplay by Astro Rebel #Shorts #GTA6',
            tags: 'GTA 6,Shorts',
            privacy_status: 'private',
            status: 'scheduled',
            youtube_video_id: null,
            publish_url: null,
            retry_count: 0,
            is_mock: false,
            error_message: null,
            created_at: '2026-11-20T12:00:00Z',
            updated_at: '2026-11-20T12:00:00Z',
          },
        },
        {
          slot_name: '17:00',
          scheduled_time_utc: '2026-11-21T11:30:00Z',
          scheduled_time_local: '2026-11-21 17:00:00 IST',
          status: 'published',
          schedule: {
            id: 202,
            candidate_id: 2,
            render_job_id: 102,
            scheduled_time: '2026-11-21T11:30:00Z',
            slot_name: '17:00',
            timezone: 'Asia/Kolkata',
            target_channel: 'Astro Rebel',
            title: 'GTA 6 Vice City Sunset Drift #Shorts',
            privacy_status: 'private',
            status: 'published',
            youtube_video_id: 'mock_yt_202',
            publish_url: 'https://youtube.com/shorts/mock_yt_202',
            retry_count: 0,
            is_mock: true,
            created_at: '2026-11-20T12:00:00Z',
            updated_at: '2026-11-20T12:00:00Z',
          },
        },
        {
          slot_name: '21:00',
          scheduled_time_utc: '2026-11-21T15:30:00Z',
          scheduled_time_local: '2026-11-21 21:00:00 IST',
          status: 'unfilled',
          schedule: null,
        },
      ],
    });

    vi.mocked(api.fetchSchedules).mockResolvedValue([]);
    vi.mocked(api.fetchRenderJobs).mockResolvedValue([
      {
        id: 101,
        candidate_id: 1,
        source_id: 10,
        status: 'completed',
        progress_pct: 100,
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
        start_time: 10,
        end_time: 45,
        duration_seconds: 35,
        title_suggestion: 'GTA 6 Bank Heist Getaway',
        hook_score: 90,
        retention_score: 85,
        context_score: 80,
        audio_score: 80,
        overall_score: 85,
        status: 'approved',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);
  });

  it('renders distribution workspace with Astro Rebel channel and 4 daily slots', async () => {
    render(<DistributionView />);

    expect(screen.getByText('Distribution & Publishing Engine')).toBeInTheDocument();
    expect(screen.getByText('M06 ACTIVE')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Astro Rebel')).toBeInTheDocument();
      expect(screen.getByText('Authorized')).toBeInTheDocument();
    });

    expect(screen.getByText('09:00')).toBeInTheDocument();
    expect(screen.getByText('13:00')).toBeInTheDocument();
    expect(screen.getByText('17:00')).toBeInTheDocument();
    expect(screen.getByText('21:00')).toBeInTheDocument();

    // Check slot statuses
    expect(screen.getByText('GTA 6 Bank Heist Getaway #Shorts')).toBeInTheDocument();
    expect(screen.getByText('mock_yt_202')).toBeInTheDocument();
  });

  it('opens and closes the Google OAuth setup guide modal', async () => {
    render(<DistributionView />);

    const guideBtn = screen.getByText('OAuth Setup Guide');
    fireEvent.click(guideBtn);

    expect(screen.getByText('Google Cloud Console & OAuth Setup Guide')).toBeInTheDocument();
    expect(screen.getByText('http://localhost:8000/api/v1/distribution/oauth/callback')).toBeInTheDocument();

    const closeBtn = screen.getByText('Close Guide');
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByText('Google Cloud Console & OAuth Setup Guide')).not.toBeInTheDocument();
    });
  });

  it('triggers publishing when Publish Now is clicked', async () => {
    vi.mocked(api.triggerPublish).mockResolvedValue({
      schedule_id: 201,
      status: 'published',
      youtube_video_id: 'mock_yt_201',
      publish_url: 'https://youtube.com/shorts/mock_yt_201',
      is_mock: true,
      message: 'Video published',
    });

    render(<DistributionView />);

    await waitFor(() => {
      expect(screen.getByText('Publish Now')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Publish Now'));

    await waitFor(() => {
      expect(api.triggerPublish).toHaveBeenCalledWith(201, false);
    });
  });
});
