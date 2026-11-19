import { render, screen, fireEvent, within } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Sidebar } from '@/components/layout/Sidebar';

describe('Sidebar', () => {
  it('renders all required navigation sections', () => {
    const onSelectSection = vi.fn();
    const onToggleCollapse = vi.fn();

    render(
      <Sidebar
        currentSection="overview"
        onSelectSection={onSelectSection}
        collapsed={false}
        onToggleCollapse={onToggleCollapse}
        connectionState="connected"
      />
    );

    const nav = screen.getByRole('navigation');
    expect(within(nav).getByText('Overview')).toBeInTheDocument();
    expect(within(nav).getByText('Discovery')).toBeInTheDocument();
    expect(within(nav).getByText('Intelligence')).toBeInTheDocument();
    expect(within(nav).getByText('Production')).toBeInTheDocument();
    expect(within(nav).getByText('Distribution')).toBeInTheDocument();
    expect(within(nav).getByText('Analytics')).toBeInTheDocument();
    expect(within(nav).getByText('Settings')).toBeInTheDocument();
  });

  it('triggers onSelectSection when item is clicked', () => {
    const onSelectSection = vi.fn();
    const onToggleCollapse = vi.fn();

    render(
      <Sidebar
        currentSection="overview"
        onSelectSection={onSelectSection}
        collapsed={false}
        onToggleCollapse={onToggleCollapse}
        connectionState="connected"
      />
    );

    const nav = screen.getByRole('navigation');
    fireEvent.click(within(nav).getByText('Discovery'));
    expect(onSelectSection).toHaveBeenCalledWith('discovery');
  });

  it('triggers onToggleCollapse when collapse button is clicked', () => {
    const onSelectSection = vi.fn();
    const onToggleCollapse = vi.fn();

    render(
      <Sidebar
        currentSection="overview"
        onSelectSection={onSelectSection}
        collapsed={false}
        onToggleCollapse={onToggleCollapse}
        connectionState="connected"
      />
    );

    const button = screen.getByRole('button', { name: /collapse sidebar/i });
    fireEvent.click(button);
    expect(onToggleCollapse).toHaveBeenCalledTimes(1);
  });
});
