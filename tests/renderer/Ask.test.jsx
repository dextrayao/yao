import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Ask from '../../src/renderer/components/Ask';

beforeAll(() => {
  window.api = {
    askQuestion: jest.fn().mockResolvedValue('This is a test answer.'),
  };
});

describe('Ask component', () => {
  it('renders the title', () => {
    render(<Ask />);
    expect(screen.getByText('Ask')).toBeTruthy();
  });

  it('renders the textarea', () => {
    render(<Ask />);
    expect(screen.getByPlaceholderText(/Ask anything/)).toBeTruthy();
  });

  it('disables button when empty', () => {
    render(<Ask />);
    const btn = screen.getByText('Ask Claude');
    expect(btn.disabled).toBe(true);
  });

  it('enables button when text entered', () => {
    render(<Ask />);
    const textarea = screen.getByPlaceholderText(/Ask anything/);
    fireEvent.change(textarea, { target: { value: 'What is React?' } });
    expect(screen.getByText('Ask Claude').disabled).toBe(false);
  });
});
