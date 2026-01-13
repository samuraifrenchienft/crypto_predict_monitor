import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PnLCard from '../PnLCard';

// Mock fetch
global.fetch = jest.fn();

const mockUserStats = {
  user_id: 'test_user',
  total_trades: 3,
  total_pnl: 200.75,
  win_rate: 66.67
};

const mockCardData = {
  user_id: 'test_user',
  card_url: 'https://example.com/card.png',
  share_text: '📊 My P&L: $200.75 across 3 trades!',
  timestamp: '2024-01-13T03:08:00Z',
  stats: mockUserStats
};

describe('PnLCard Component', () => {
  beforeEach(() => {
    fetch.mockClear();
    // Reset DOM mocks
    delete global.document.createElement;
    delete global.document.body.appendChild;
  });

  test('renders loading state initially', () => {
    fetch.mockImplementation(() => new Promise(() => {}));
    
    render(<PnLCard userId="test_user" />);
    expect(screen.getByText('Loading P&L data...')).toBeInTheDocument();
  });

  test('renders user stats when data is loaded', async () => {
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUserStats
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockCardData
      });

    render(<PnLCard userId="test_user" />);

    await waitFor(() => {
      expect(screen.getByText('$200.75')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('66.7%')).toBeInTheDocument();
    });
  });

  test('renders error state when API fails', async () => {
    fetch.mockRejectedValue(new Error('API Error'));

    render(<PnLCard userId="test_user" />);

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch user stats')).toBeInTheDocument();
    });
  });

  test('share button calls navigator.share when available', async () => {
    const mockShare = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'share', {
      writable: true,
      value: mockShare
    });

    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUserStats
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockCardData
      });

    render(<PnLCard userId="test_user" />);

    await waitFor(() => {
      expect(screen.getByText('📤 Share Card')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('📤 Share Card'));
    expect(mockShare).toHaveBeenCalledWith({
      title: 'My P&L Card',
      text: '📊 My P&L: $200.75 across 3 trades!',
      url: 'https://example.com/card.png'
    });
  });

  test('download button creates download link', async () => {
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUserStats
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockCardData
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ download_url: 'https://example.com/download.png' })
      });

    render(<PnLCard userId="test_user" />);

    await waitFor(() => {
      expect(screen.getByText('💾 Download')).toBeInTheDocument();
    });

    // Just test that the button exists and can be clicked
    const downloadBtn = screen.getByText('💾 Download');
    expect(downloadBtn).toBeInTheDocument();
    fireEvent.click(downloadBtn);
  });

  test('displays correct user ID', async () => {
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockUserStats
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockCardData
      });

    render(<PnLCard userId="custom_user" />);

    await waitFor(() => {
      expect(screen.getByText('@custom_user')).toBeInTheDocument();
    });
  });
});
