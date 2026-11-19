import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { App } from '@/app/App';

// Mock fetch globally for testing
global.fetch = vi.fn().mockImplementation((url: string) => {
  if (url.includes('/api/v1/health/ready')) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          status: 'ready',
          timestamp: new Date().toISOString(),
          components: {
            database: {
              status: 'healthy',
              message: 'Database connection active',
            },
          },
        }),
    });
  }
  return Promise.resolve({
    ok: true,
    json: () =>
      Promise.resolve({
        status: 'ok',
        app: 'VANTYX',
        version: '0.1.0',
        environment: 'development',
        timestamp: new Date().toISOString(),
      }),
  });
});

describe('App', () => {
  it('renders application brand mark and overview workspace', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getAllByText('VANTYX').length).toBeGreaterThan(0);
    });

    expect(screen.getByText(/The intelligence behind every moment/i)).toBeInTheDocument();
    expect(screen.getByText(/Platform Foundation/i)).toBeInTheDocument();
  });
});
