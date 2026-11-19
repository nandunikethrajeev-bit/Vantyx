import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusBadge } from '@/components/ui/StatusBadge';

describe('StatusBadge', () => {
  it('renders operational state correctly', () => {
    render(<StatusBadge state="connected" />);
    expect(screen.getByText('Operational')).toBeInTheDocument();
  });

  it('renders degraded state correctly', () => {
    render(<StatusBadge state="degraded" />);
    expect(screen.getByText('Degraded')).toBeInTheDocument();
  });

  it('renders offline state correctly', () => {
    render(<StatusBadge state="offline" />);
    expect(screen.getByText('Backend Offline')).toBeInTheDocument();
  });

  it('renders connecting state correctly', () => {
    render(<StatusBadge state="connecting" />);
    expect(screen.getByText('Connecting')).toBeInTheDocument();
  });
});
