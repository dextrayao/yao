import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Sidebar from '../../src/renderer/components/Sidebar';

describe('Sidebar component', () => {
  it('renders the app title', () => {
    render(<Sidebar activePage="capture" onNavigate={() => {}} />);
    expect(screen.getByText('Noted')).toBeTruthy();
  });

  it('renders all nav items', () => {
    render(<Sidebar activePage="capture" onNavigate={() => {}} />);
    expect(screen.getByText('Capture')).toBeTruthy();
    expect(screen.getByText('Library')).toBeTruthy();
    expect(screen.getByText('Ask')).toBeTruthy();
    expect(screen.getByText('Settings')).toBeTruthy();
  });

  it('highlights the active page', () => {
    render(<Sidebar activePage="library" onNavigate={() => {}} />);
    const libraryBtn = screen.getByText('Library').closest('button');
    expect(libraryBtn.className).toContain('active');
  });

  it('calls onNavigate when a nav item is clicked', () => {
    const onNavigate = jest.fn();
    render(<Sidebar activePage="capture" onNavigate={onNavigate} />);
    fireEvent.click(screen.getByText('Ask'));
    expect(onNavigate).toHaveBeenCalledWith('ask');
  });
});
