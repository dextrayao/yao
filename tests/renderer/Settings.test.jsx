import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Settings from '../../src/renderer/components/Settings';

beforeAll(() => {
  window.api = {
    getSetting: jest.fn().mockResolvedValue(null),
    setSetting: jest.fn().mockResolvedValue(true),
  };
});

describe('Settings component', () => {
  it('renders after loading', async () => {
    render(<Settings />);
    await waitFor(() => {
      expect(screen.getByText('Settings')).toBeTruthy();
    });
  });

  it('renders API key input', async () => {
    render(<Settings />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText('sk-ant-...')).toBeTruthy();
    });
  });

  it('disables Save when input is empty', async () => {
    render(<Settings />);
    await waitFor(() => {
      const btn = screen.getByText('Save');
      expect(btn.disabled).toBe(true);
    });
  });

  it('enables Save when key is entered', async () => {
    render(<Settings />);
    await waitFor(() => {
      const input = screen.getByPlaceholderText('sk-ant-...');
      fireEvent.change(input, { target: { value: 'sk-ant-test123' } });
      const btn = screen.getByText('Save');
      expect(btn.disabled).toBe(false);
    });
  });

  it('calls setSetting on Save', async () => {
    render(<Settings />);
    await waitFor(() => {
      const input = screen.getByPlaceholderText('sk-ant-...');
      fireEvent.change(input, { target: { value: 'sk-ant-test123' } });
    });
    fireEvent.click(screen.getByText('Save'));
    await waitFor(() => {
      expect(window.api.setSetting).toHaveBeenCalledWith(
        'anthropic_api_key',
        'sk-ant-test123'
      );
    });
  });
});
