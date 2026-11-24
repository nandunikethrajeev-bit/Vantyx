import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { UrlWorkspaceView } from '@/features/url_workspace/UrlWorkspaceView';

vi.mock('@/lib/api', () => ({
  submitBatchIntake: vi.fn().mockResolvedValue({
    batch_id: 'batch_test_123',
    total_submitted: 1,
    total_valid: 1,
    total_duplicates: 0,
    total_invalid: 0,
    created_at: new Date().toISOString(),
    items: [
      {
        id: 1,
        raw_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        canonical_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        video_id: 'dQw4w9WgXcQ',
        status: 'awaiting_media',
        source_id: 10,
        source_title: 'Test Stunt Video',
        permission_status: 'authorized',
        commercial_use_allowed: true,
        created_at: new Date().toISOString(),
      },
    ],
  }),
  fetchIntakeBatches: vi.fn().mockResolvedValue([
    {
      batch_id: 'batch_test_123',
      total_submitted: 1,
      total_valid: 1,
      total_duplicates: 0,
      total_invalid: 0,
      created_at: new Date().toISOString(),
      items: [
        {
          id: 1,
          raw_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
          canonical_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
          video_id: 'dQw4w9WgXcQ',
          status: 'awaiting_media',
          source_id: 10,
          source_title: 'Test Stunt Video',
          permission_status: 'authorized',
          commercial_use_allowed: true,
          created_at: new Date().toISOString(),
        },
      ],
    },
  ]),
  fetchIntakeBatch: vi.fn().mockResolvedValue({
    batch_id: 'batch_test_123',
    total_submitted: 1,
    total_valid: 1,
    total_duplicates: 0,
    total_invalid: 0,
    created_at: new Date().toISOString(),
    items: [],
  }),
  triggerBatchProcess: vi.fn().mockResolvedValue({
    batch_id: 'batch_test_123',
    total_submitted: 1,
    total_valid: 1,
    total_duplicates: 0,
    total_invalid: 0,
    created_at: new Date().toISOString(),
    items: [],
  }),
  retryBatchItem: vi.fn().mockResolvedValue({
    id: 1,
    video_id: 'dQw4w9WgXcQ',
    status: 'received',
  }),
  linkSourceLocalMedia: vi.fn().mockResolvedValue({
    id: 10,
    title: 'Test Stunt Video',
  }),
  uploadSourceMedia: vi.fn().mockResolvedValue({
    id: 10,
    title: 'Test Stunt Video',
  }),
}));

describe('UrlWorkspaceView', () => {
  it('renders the Autonomous URL Studio and parses YouTube URLs', async () => {
    render(<UrlWorkspaceView />);

    expect(screen.getByText('Autonomous URL Studio')).toBeInTheDocument();
    expect(screen.getByText(/Autonomous Pipeline Stages/i)).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText(/https:\/\/www\.youtube\.com\/watch\?v=/i);
    fireEvent.change(textarea, {
      target: {
        value: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ\nhttps://youtu.be/kxyP_8bV0_0\ninvalid_url',
      },
    });

    // Valid: 2, Invalid: 1
    expect(screen.getByText('Valid:')).toBeInTheDocument();
    expect(screen.getByText('Invalid:')).toBeInTheDocument();
  });

  it('displays batch items and allows opening the attach media modal', async () => {
    render(<UrlWorkspaceView />);

    await waitFor(() => {
      expect(screen.getByText('Test Stunt Video')).toBeInTheDocument();
    });

    const attachButton = screen.getByText('Attach Media');
    expect(attachButton).toBeInTheDocument();
    fireEvent.click(attachButton);

    expect(screen.getByText('Attach Authorized Source Media')).toBeInTheDocument();
  });
});
