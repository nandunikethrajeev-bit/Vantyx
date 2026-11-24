import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DiscoveryView } from '@/features/discovery/DiscoveryView';
import * as api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  fetchCreators: vi.fn(),
  fetchVideoSources: vi.fn(),
  createCreator: vi.fn(),
  deleteCreator: vi.fn(),
  discoverCreatorVideos: vi.fn(),
  runGlobalDiscovery: vi.fn(),
  updateCreator: vi.fn(),
  importManualSource: vi.fn(),
  updateSourceRights: vi.fn(),
  fetchIntakeBatches: vi.fn(() => Promise.resolve([])),
  submitBatchIntake: vi.fn(),
  uploadSourceMedia: vi.fn(),
  linkSourceLocalMedia: vi.fn(),
}));

describe('DiscoveryView', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.fetchIntakeBatches).mockResolvedValue([]);
    vi.mocked(api.fetchCreators).mockResolvedValue([
      {
        id: 1,
        name: 'Vice City Clips',
        channel_id: 'UC123456789',
        channel_handle: '@ViceCityClips',
        content_category: 'GTA 6 Gameplay',
        is_monitored: true,
        approval_status: 'approved',
        permission_tier: 'authorized_partner',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);
    vi.mocked(api.fetchVideoSources).mockResolvedValue([
      {
        id: 10,
        video_id: 'vid_999',
        title: 'GTA 6 Speedrun World Record',
        duration_seconds: 420,
        source_url: 'https://youtube.com/watch?v=vid_999',
        discovery_method: 'feed_ingest',
        is_eligible: true,
        creator_name: 'Vice City Clips',
        rights: {
          id: 5,
          source_id: 10,
          permission_status: 'authorized',
          commercial_use_allowed: true,
          allowed_editing_scope: 'transformative_shorts',
          attribution_required: true,
          attribution_text: 'Courtesy of Vice City Clips',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);
  });

  it('renders discovery dashboard with video catalog', async () => {
    render(<DiscoveryView />);

    await waitFor(() => {
      expect(screen.getByText('GTA 6 Speedrun World Record')).toBeInTheDocument();
      expect(screen.getByText('ELIGIBLE')).toBeInTheDocument();
    });

    expect(screen.getByText(/GTA 6 Content Ingestion & Rights Governance/i)).toBeInTheDocument();
    expect(screen.getByText('Run Discovery Sweep')).toBeInTheDocument();
  });

  it('switches to creators tab and displays registered channels', async () => {
    render(<DiscoveryView />);

    await waitFor(() => {
      expect(screen.getByText('GTA 6 Speedrun World Record')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Registered Creators/i));

    await waitFor(() => {
      expect(screen.getByText('Vice City Clips')).toBeInTheDocument();
      expect(screen.getByText('UC123456789')).toBeInTheDocument();
    });
  });

  it('opens register creator modal on click', async () => {
    render(<DiscoveryView />);

    const addButton = screen.getByText('Add Creator');
    fireEvent.click(addButton);

    expect(screen.getByText('Register GTA Creator Channel')).toBeInTheDocument();
  });
});
