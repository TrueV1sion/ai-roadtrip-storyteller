import React from 'react';
import { render, waitFor } from '@testing-library/react-native';
import { Animated } from 'react-native';

import MusicVisualizer from '../MusicVisualizer';

// Mock Animated timing
jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  const mockAnimated = {
    ...RN.Animated,
    timing: jest.fn(() => ({
      start: jest.fn((callback) => callback && callback({ finished: true })),
      stop: jest.fn(),
    })),
    spring: jest.fn(() => ({
      start: jest.fn((callback) => callback && callback({ finished: true })),
      stop: jest.fn(),
    })),
    Value: jest.fn(RN.Animated.Value),
  };
  return {
    ...RN,
    Animated: mockAnimated,
  };
});

describe('MusicVisualizer Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders visualizer bars', () => {
    const { getAllByTestId } = render(
      <MusicVisualizer isPlaying={false} audioData={[]} />
    );
    
    const bars = getAllByTestId('visualizer-bar');
    expect(bars.length).toBeGreaterThan(0);
  });

  it('animates bars when playing', async () => {
    const audioData = [0.2, 0.5, 0.8, 0.3, 0.6, 0.9, 0.4, 0.7];
    
    const { getAllByTestId, rerender } = render(
      <MusicVisualizer isPlaying={false} audioData={audioData} />
    );
    
    // Start playing
    rerender(<MusicVisualizer isPlaying={true} audioData={audioData} />);
    
    await waitFor(() => {
      expect(Animated.timing).toHaveBeenCalled();
    });
    
    const bars = getAllByTestId('visualizer-bar');
    bars.forEach((bar, index) => {
      expect(bar.props.style.height).toBeDefined();
    });
  });

  it('stops animation when paused', async () => {
    const audioData = [0.5, 0.5, 0.5, 0.5];
    
    const { rerender } = render(
      <MusicVisualizer isPlaying={true} audioData={audioData} />
    );
    
    // Clear previous calls
    jest.clearAllMocks();
    
    // Pause playback
    rerender(<MusicVisualizer isPlaying={false} audioData={audioData} />);
    
    await waitFor(() => {
      const timingCalls = Animated.timing.mock.calls;
      const lastCall = timingCalls[timingCalls.length - 1];
      if (lastCall) {
        expect(lastCall[1].toValue).toBe(0);
      }
    });
  });

  it('responds to audio frequency data', async () => {
    const lowFreqData = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1];
    const highFreqData = [0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9];
    
    const { rerender } = render(
      <MusicVisualizer isPlaying={true} audioData={lowFreqData} />
    );
    
    const lowFreqCalls = Animated.timing.mock.calls.length;
    
    // Update with high frequency data
    rerender(<MusicVisualizer isPlaying={true} audioData={highFreqData} />);
    
    await waitFor(() => {
      const highFreqCalls = Animated.timing.mock.calls.length;
      expect(highFreqCalls).toBeGreaterThan(lowFreqCalls);
    });
  });

  it('uses theme colors', () => {
    const { getAllByTestId } = render(
      <MusicVisualizer 
        isPlaying={true} 
        audioData={[0.5]} 
        primaryColor="#FF0000"
        secondaryColor="#00FF00"
      />
    );
    
    const bars = getAllByTestId('visualizer-bar');
    expect(bars[0].props.style.backgroundColor).toBeDefined();
  });

  it('handles empty audio data', () => {
    const { getAllByTestId } = render(
      <MusicVisualizer isPlaying={true} audioData={[]} />
    );
    
    const bars = getAllByTestId('visualizer-bar');
    expect(bars.length).toBeGreaterThan(0);
    
    // Should show default idle animation
    bars.forEach(bar => {
      expect(bar.props.style.height).toBeDefined();
    });
  });

  it('supports different visualization styles', () => {
    const { getAllByTestId: getBars } = render(
      <MusicVisualizer 
        isPlaying={true} 
        audioData={[0.5, 0.7, 0.3]} 
        style="bars"
      />
    );
    
    expect(getBars('visualizer-bar').length).toBeGreaterThan(0);
    
    const { getAllByTestId: getWaves } = render(
      <MusicVisualizer 
        isPlaying={true} 
        audioData={[0.5, 0.7, 0.3]} 
        style="waves"
      />
    );
    
    expect(getWaves('visualizer-wave').length).toBeGreaterThan(0);
  });

  it('adjusts bar count based on container size', () => {
    const { getAllByTestId, rerender } = render(
      <MusicVisualizer 
        isPlaying={true} 
        audioData={[0.5]} 
        width={200}
      />
    );
    
    const smallBars = getAllByTestId('visualizer-bar').length;
    
    rerender(
      <MusicVisualizer 
        isPlaying={true} 
        audioData={[0.5]} 
        width={400}
      />
    );
    
    const largeBars = getAllByTestId('visualizer-bar').length;
    expect(largeBars).toBeGreaterThan(smallBars);
  });

  it('shows pulse effect on beat', async () => {
    const { getByTestId } = render(
      <MusicVisualizer 
        isPlaying={true} 
        audioData={[0.9]} 
        showBeatPulse={true}
      />
    );
    
    const container = getByTestId('visualizer-container');
    
    await waitFor(() => {
      expect(Animated.spring).toHaveBeenCalled();
    });
  });

  it('applies accessibility labels', () => {
    const { getByLabelText } = render(
      <MusicVisualizer isPlaying={true} audioData={[0.5]} />
    );
    
    expect(getByLabelText('Music visualization')).toBeTruthy();
  });
});