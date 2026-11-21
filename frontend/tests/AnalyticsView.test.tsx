import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AnalyticsView } from '../src/features/analytics/AnalyticsView';
import * as api from '../src/lib/api';

vi.mock('../src/lib/api');

const mockOverview = {
  channel_id: 'UC_astro_rebel_official',
  channel_name: 'Astro Rebel',
  snapshot_date: '2027-03-01',
  total_views: 48500,
  total_subscribers: 3120,
  subscribers_gained: 85,
  total_videos: 6,
  estimated_minutes_watched: 12450.0,
  average_view_duration_seconds: 28.5,
  average_view_percentage: 79.4,
  collection_source: 'mock' as const,
  is_delayed_reporting: false,
  history_trend: [
    { date: '2027-02-28', views: 42000, subscribers: 3080, minutes_watched: 10800.0 },
    { date: '2027-03-01', views: 48500, subscribers: 3120, minutes_watched: 12450.0 },
  ],
};

const mockVideos = [
  {
    schedule_id: 1,
    youtube_video_id: 'yt_mock_vid_1',
    title: 'GTA 6: Police Helicopter Evade #Shorts',
    slot_name: '09:00',
    scheduled_time: '2027-03-01T03:30:00Z',
    age_days: 1,
    views: 8900,
    likes: 420,
    comments: 32,
    shares: 98,
    subscribers_gained: 18,
    average_view_duration_seconds: 31.2,
    average_view_percentage: 84.5,
    relative_retention_index: 86.0,
    hook_retention_rate: 88.0,
    category: 'chase',
    duration_bucket: '25-35s',
    reporting_status: 'complete' as const,
    is_delayed_reporting: false,
  },
];

const mockInsights = {
  top_clips: [],
  hook_insights: [
    {
      key: 'explosive_hook',
      label: 'High Action Hooks (≥75)',
      sample_size: 4,
      avg_views: 9200.0,
      avg_retention_pct: 82.5,
      confidence_level: 'medium' as const,
      relative_multiplier: 1.12,
      rationale: 'Strong opening hook prevents early dropoff.',
    },
  ],
  duration_insights: [
    {
      key: '25-35s',
      label: 'Duration 25-35s',
      sample_size: 5,
      avg_views: 8800.0,
      avg_retention_pct: 81.2,
      confidence_level: 'medium' as const,
      relative_multiplier: 1.05,
      rationale: 'Optimal pacing window.',
    },
  ],
  category_insights: [
    {
      key: 'chase',
      label: 'Chase Moments',
      sample_size: 4,
      avg_views: 9400.0,
      avg_retention_pct: 83.0,
      confidence_level: 'medium' as const,
      relative_multiplier: 1.08,
      rationale: 'High retention category.',
    },
  ],
  slot_insights: [
    {
      key: '09:00',
      label: '09:00 IST Slot',
      sample_size: 4,
      avg_views: 9100.0,
      avg_retention_pct: 81.0,
      confidence_level: 'medium' as const,
      relative_multiplier: 1.02,
      rationale: 'Morning slot performance.',
    },
  ],
  correlation_vs_causation_notice: 'STATISTICAL METHODOLOGY NOTE: Performance variations represent correlation.',
  overall_confidence: 'medium' as const,
  total_samples_analyzed: 6,
};

const mockFeedback = {
  feedback_enabled: false,
  max_impact: 0.15,
  min_sample_size: 3,
  category_multipliers: { chase: 1.08, heist: 1.12 },
  duration_multipliers: { '25-35s': 1.05 },
  hook_multipliers: { explosive: 1.05 },
  active_profiles_count: 6,
};

describe('AnalyticsView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchAnalyticsOverview).mockResolvedValue(mockOverview);
    vi.mocked(api.fetchPublishedVideosPerformance).mockResolvedValue(mockVideos);
    vi.mocked(api.fetchPerformanceInsights).mockResolvedValue(mockInsights);
    vi.mocked(api.fetchFeedbackStatus).mockResolvedValue(mockFeedback);
  });

  it('renders audience performance workspace with KPI cards and channel identity', async () => {
    render(<AnalyticsView />);

    await waitFor(() => {
      expect(screen.getByText('Audience Performance & Feedback Engine')).toBeInTheDocument();
      expect(screen.getByText('Astro Rebel')).toBeInTheDocument();
      expect(screen.getByText('48,500')).toBeInTheDocument(); // Total views
      expect(screen.getByText('79.4%')).toBeInTheDocument(); // AVP
    });
  });

  it('displays published shorts telemetry and category insights', async () => {
    render(<AnalyticsView />);

    await waitFor(() => {
      expect(screen.getByText('GTA 6: Police Helicopter Evade #Shorts')).toBeInTheDocument();
      expect(screen.getAllByText('09:00').length).toBeGreaterThan(0);
      expect(screen.getByText('84.5%')).toBeInTheDocument();
      expect(screen.getByText('STATISTICAL METHODOLOGY NOTE: Performance variations represent correlation.')).toBeInTheDocument();
    });
  });

  it('handles toggling closed-loop feedback engine', async () => {
    vi.mocked(api.updateFeedbackConfig).mockResolvedValue({
      feedback_enabled: true,
      max_impact: 0.15,
      min_sample_size: 3,
    });

    render(<AnalyticsView />);

    await waitFor(() => {
      expect(screen.getByText('Enable Feedback Engine')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Enable Feedback Engine'));

    await waitFor(() => {
      expect(api.updateFeedbackConfig).toHaveBeenCalledWith({ feedback_enabled: true });
    });
  });
});
