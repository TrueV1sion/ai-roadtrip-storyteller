import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import { Animated } from 'react-native';
import AudioSceneVisualizer from '../audio/AudioSceneVisualizer';
import { audioSceneService } from '@/services/audioSceneService';

// Mock dependencies
jest.mock('@/services/audioSceneService');
jest.mock('@expo/vector-icons', () => ({
  MaterialIcons: 'Icon',
  MaterialCommunityIcons: 'Icon',
  Ionicons: 'Icon',
}));
jest.mock('react-native-svg', () => ({
  Svg: 'Svg',
  Circle: 'Circle',
  Line: 'Line',
  Path: 'Path',
  G: 'G',
  Text: 'Text',
  Defs: 'Defs',
  LinearGradient: 'LinearGradient',
  Stop: 'Stop',
}));

describe('AudioSceneVisualizer', () => {
  const mockAudioScene = {
    id: 'scene-1',
    name: 'Highway Drive',
    sources: [
      {
        id: 'engine',
        type: 'vehicle',
        label: 'Engine Sound',
        position: { x: 0, y: 0, z: 0 },
        volume: 0.7,
        frequency: 150,
        active: true,
      },
      {
        id: 'wind',
        type: 'environment',
        label: 'Wind Noise',
        position: { x: 0, y: 1, z: -2 },
        volume: 0.4,
        frequency: 800,
        active: true,
      },
      {
        id: 'music',
        type: 'music',
        label: 'Background Music',
        position: { x: -1, y: 0, z: 0 },
        volume: 0.5,
        frequency: 440,
        active: true,
      },
    ],
    ambientLevel: 0.3,
    reverbLevel: 0.2,
    environment: 'highway',
  };

  const mockFrequencyData = new Float32Array([
    0.2, 0.5, 0.8, 0.6, 0.4, 0.3, 0.7, 0.9,
    0.5, 0.4, 0.6, 0.3, 0.2, 0.5, 0.7, 0.4,
  ]);

  beforeEach(() => {
    jest.clearAllMocks();
    (audioSceneService.getCurrentScene as jest.Mock).mockReturnValue(mockAudioScene);
    (audioSceneService.getFrequencyData as jest.Mock).mockReturnValue(mockFrequencyData);
    (audioSceneService.isActive as jest.Mock).mockReturnValue(true);
  });

  it('renders visualizer with scene name', () => {
    const { getByText } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    expect(getByText('Highway Drive')).toBeTruthy();
  });

  it('displays audio sources', () => {
    const { getByText } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    expect(getByText('Engine Sound')).toBeTruthy();
    expect(getByText('Wind Noise')).toBeTruthy();
    expect(getByText('Background Music')).toBeTruthy();
  });

  it('shows frequency spectrum', () => {
    const { getByTestId } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    expect(getByTestId('frequency-spectrum')).toBeTruthy();
    // Check for frequency bars
    mockFrequencyData.forEach((_, index) => {
      expect(getByTestId(`freq-bar-${index}`)).toBeTruthy();
    });
  });

  it('toggles between visualization modes', async () => {
    const { getByText, getByTestId } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    // Default is spectrum
    expect(getByTestId('frequency-spectrum')).toBeTruthy();
    
    // Switch to waveform
    const waveformButton = getByText('Waveform');
    fireEvent.press(waveformButton);
    
    await waitFor(() => {
      expect(getByTestId('waveform-display')).toBeTruthy();
    });
    
    // Switch to 3D
    const threeDButton = getByText('3D');
    fireEvent.press(threeDButton);
    
    await waitFor(() => {
      expect(getByTestId('3d-scene')).toBeTruthy();
    });
  });

  it('displays source volume levels', () => {
    const { getByTestId } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    mockAudioScene.sources.forEach(source => {
      const volumeBar = getByTestId(`volume-bar-${source.id}`);
      expect(volumeBar).toBeTruthy();
    });
  });

  it('shows environment info', () => {
    const { getByText } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    expect(getByText('Environment: Highway')).toBeTruthy();
    expect(getByText(/Ambient: 30%/)).toBeTruthy();
    expect(getByText(/Reverb: 20%/)).toBeTruthy();
  });

  it('toggles individual source visualization', async () => {
    const { getByTestId } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    const sourceToggle = getByTestId('source-toggle-engine');
    fireEvent.press(sourceToggle);
    
    await waitFor(() => {
      expect(audioSceneService.toggleSourceVisualization).toHaveBeenCalledWith('engine');
    });
  });

  it('shows peak levels', () => {
    const { getByTestId } = render(
      <AudioSceneVisualizer isVisible={true} showPeakLevels={true} />
    );
    
    expect(getByTestId('peak-level-indicator')).toBeTruthy();
    expect(getByTestId('peak-value')).toBeTruthy();
  });

  it('handles scene transitions', async () => {
    const newScene = {
      ...mockAudioScene,
      id: 'scene-2',
      name: 'City Streets',
      environment: 'urban',
    };
    
    const { getByText, rerender } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    expect(getByText('Highway Drive')).toBeTruthy();
    
    (audioSceneService.getCurrentScene as jest.Mock).mockReturnValue(newScene);
    
    rerender(<AudioSceneVisualizer isVisible={true} />);
    
    await waitFor(() => {
      expect(getByText('City Streets')).toBeTruthy();
    });
  });

  it('pauses visualization when not visible', () => {
    const { rerender } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    expect(audioSceneService.startVisualization).toHaveBeenCalled();
    
    rerender(<AudioSceneVisualizer isVisible={false} />);
    
    expect(audioSceneService.pauseVisualization).toHaveBeenCalled();
  });

  it('displays color-coded source types', () => {
    const { getByTestId } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    const engineSource = getByTestId('source-indicator-engine');
    const windSource = getByTestId('source-indicator-wind');
    const musicSource = getByTestId('source-indicator-music');
    
    // Check for different colors based on type
    expect(engineSource.props.style).toContainEqual(
      expect.objectContaining({ backgroundColor: expect.any(String) })
    );
    expect(windSource.props.style).toContainEqual(
      expect.objectContaining({ backgroundColor: expect.any(String) })
    );
    expect(musicSource.props.style).toContainEqual(
      expect.objectContaining({ backgroundColor: expect.any(String) })
    );
  });

  it('shows frequency analysis details', async () => {
    const { getByText, getByTestId } = render(
      <AudioSceneVisualizer isVisible={true} showAnalysis={true} />
    );
    
    expect(getByText('Frequency Analysis')).toBeTruthy();
    expect(getByTestId('dominant-frequency')).toBeTruthy();
    expect(getByTestId('frequency-range')).toBeTruthy();
  });

  it('handles fullscreen mode', async () => {
    const { getByTestId } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    const fullscreenButton = getByTestId('fullscreen-button');
    fireEvent.press(fullscreenButton);
    
    await waitFor(() => {
      expect(getByTestId('fullscreen-visualizer')).toBeTruthy();
    });
  });

  it('exports visualization snapshot', async () => {
    const { getByTestId } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    const exportButton = getByTestId('export-snapshot');
    fireEvent.press(exportButton);
    
    await waitFor(() => {
      expect(audioSceneService.exportSnapshot).toHaveBeenCalled();
    });
  });

  it('shows loading state during initialization', () => {
    (audioSceneService.isActive as jest.Mock).mockReturnValue(false);
    
    const { getByText } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    expect(getByText('Initializing audio visualization...')).toBeTruthy();
  });

  it('handles error state', () => {
    (audioSceneService.getCurrentScene as jest.Mock).mockImplementation(() => {
      throw new Error('Audio service error');
    });
    
    const { getByText } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    expect(getByText(/Unable to load audio visualization/)).toBeTruthy();
  });

  it('updates animation frame rate', async () => {
    const { getByTestId } = render(
      <AudioSceneVisualizer 
        isVisible={true} 
        targetFPS={30}
      />
    );
    
    expect(audioSceneService.setFrameRate).toHaveBeenCalledWith(30);
  });

  it('displays accessibility labels', () => {
    const { getByLabelText } = render(
      <AudioSceneVisualizer isVisible={true} />
    );
    
    expect(getByLabelText('Audio scene visualizer')).toBeTruthy();
    expect(getByLabelText('Frequency spectrum display')).toBeTruthy();
  });
});