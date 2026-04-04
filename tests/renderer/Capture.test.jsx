import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Capture from '../../src/renderer/components/Capture';

// Mock window.api
beforeAll(() => {
  window.api = {
    createNote: jest.fn().mockResolvedValue(1),
    onNoteUpdated: jest.fn(() => () => {}),
  };
});

describe('Capture component', () => {
  it('renders the title', () => {
    render(<Capture />);
    expect(screen.getByText('Capture')).toBeTruthy();
  });

  it('renders the textarea', () => {
    render(<Capture />);
    const textarea = screen.getByPlaceholderText(/What's on your mind/);
    expect(textarea).toBeTruthy();
  });

  it('renders the Save button as disabled when empty', () => {
    render(<Capture />);
    const btn = screen.getByText('Save');
    expect(btn.disabled).toBe(true);
  });

  it('enables Save button when text is entered', () => {
    render(<Capture />);
    const textarea = screen.getByPlaceholderText(/What's on your mind/);
    fireEvent.change(textarea, { target: { value: 'Hello world' } });
    const btn = screen.getByText('Save');
    expect(btn.disabled).toBe(false);
  });

  it('shows tag badges when # syntax is used', () => {
    render(<Capture />);
    const textarea = screen.getByPlaceholderText(/What's on your mind/);
    fireEvent.change(textarea, { target: { value: 'My note #react #coding' } });
    expect(screen.getByText('react')).toBeTruthy();
    expect(screen.getByText('coding')).toBeTruthy();
  });

  it('deduplicates tags', () => {
    render(<Capture />);
    const textarea = screen.getByPlaceholderText(/What's on your mind/);
    fireEvent.change(textarea, { target: { value: '#react #React #REACT' } });
    const badges = screen.getAllByText('react');
    expect(badges).toHaveLength(1);
  });

  it('calls createNote on Save click', async () => {
    const onNoteCreated = jest.fn();
    render(<Capture onNoteCreated={onNoteCreated} />);
    const textarea = screen.getByPlaceholderText(/What's on your mind/);
    fireEvent.change(textarea, { target: { value: 'Test note #demo' } });
    fireEvent.click(screen.getByText('Save'));
    // Wait for async
    await new Promise((r) => setTimeout(r, 50));
    expect(window.api.createNote).toHaveBeenCalledWith('Test note #demo', ['demo']);
  });
});
