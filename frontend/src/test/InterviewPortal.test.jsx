import { describe, test, expect, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import React from 'react';
import InterviewPortal from '../components/InterviewPortal';

// Mock Navigator Media Devices API
Object.defineProperty(global.navigator, 'mediaDevices', {
  value: {
    getUserMedia: vi.fn().mockImplementation(() => Promise.resolve({
      getTracks: () => [{ stop: vi.fn() }]
    })),
  },
  writable: true
});

// Mock AudioContext
const mockAudioContext = vi.fn().mockImplementation(() => ({
  createMediaStreamSource: () => ({
    connect: () => {}
  }),
  createAnalyser: () => ({
    fftSize: 256,
    frequencyBinCount: 128,
    getByteTimeDomainData: () => {}
  })
}));
global.AudioContext = mockAudioContext;
global.webkitAudioContext = mockAudioContext;

describe('Candidate Interview Portal Component Tests', () => {
  test('renders device permissions setup flow first', () => {
    render(<InterviewPortal onBack={() => {}} />);
    
    expect(screen.getByText('Candidate Setup & Calibration')).toBeInTheDocument();
    expect(screen.getByText('Grant Mic Access')).toBeInTheDocument();
    expect(screen.queryByText('Voice Interview Room')).not.toBeInTheDocument();
  });

  test('successfully displays level calibration and enter button on mic approval', async () => {
    render(<InterviewPortal onBack={() => {}} />);
    
    const grantButton = screen.getByText('Grant Mic Access');
    await act(async () => {
      fireEvent.click(grantButton);
    });

    expect(screen.getByText(/Mic Access Granted/i)).toBeInTheDocument();
    expect(screen.getByText('Enter Interview Room')).toBeInTheDocument();
  });

  test('transitions into the active interview room showing question card and oscilloscope', async () => {
    render(<InterviewPortal onBack={() => {}} />);
    
    const grantButton = screen.getByText('Grant Mic Access');
    await act(async () => {
      fireEvent.click(grantButton);
    });

    const enterRoomButton = screen.getByText('Enter Interview Room');
    fireEvent.click(enterRoomButton);

    // Should transition to active interview screen
    expect(screen.getByText('Voice Interview Room')).toBeInTheDocument();
    expect(screen.getByText('AI Assistant Interviewer')).toBeInTheDocument();
    expect(screen.getByText(/Describe a complex/i)).toBeInTheDocument();
    expect(screen.getByTestId('oscilloscope-wrapper')).toBeInTheDocument();
  });

  test('handles muting microphone in active interview', async () => {
    vi.useFakeTimers();
    render(<InterviewPortal onBack={() => {}} />);
    
    await act(async () => {
      fireEvent.click(screen.getByText('Grant Mic Access'));
    });
    fireEvent.click(screen.getByText('Enter Interview Room'));

    // Fast-forward speech timer (4000ms)
    act(() => {
      vi.advanceTimersByTime(4000);
    });

    const muteButton = screen.getByText('Mute Mic');
    fireEvent.click(muteButton);

    expect(screen.getByText('Muted')).toBeInTheDocument();
    expect(screen.getByText('Unmute Mic')).toBeInTheDocument();
    vi.useRealTimers();
  });

  test('allows candidate to edit transcript manually and toggle speech sync', async () => {
    vi.useFakeTimers();
    render(<InterviewPortal onBack={() => {}} />);
    
    await act(async () => {
      fireEvent.click(screen.getByText('Grant Mic Access'));
    });
    fireEvent.click(screen.getByText('Enter Interview Room'));

    // Fast-forward past AI speaking phase to enter listening status
    act(() => {
      vi.advanceTimersByTime(4000);
    });

    const textarea = screen.getByPlaceholderText(/Speak into your microphone for real-time transcription/i);
    expect(textarea).toBeInTheDocument();

    // Type a candidate answer edit into textarea
    fireEvent.change(textarea, { target: { value: 'I built a distributed event pipeline using Python and Redis.' } });

    // Should indicate manual transcript edit status
    expect(screen.getByText(/Transcript Edited/i)).toBeInTheDocument();
    const resumeButton = screen.getByText(/Resume Speech Sync/i);
    expect(resumeButton).toBeInTheDocument();

    // Submit button should be enabled for edited response
    const submitButton = screen.getByText('Submit Answer');
    expect(submitButton).not.toBeDisabled();

    // Clicking Resume Speech Sync resets manual edit indicator
    fireEvent.click(resumeButton);
    expect(screen.queryByText(/Transcript Edited/i)).not.toBeInTheDocument();

    vi.useRealTimers();
  });
});

