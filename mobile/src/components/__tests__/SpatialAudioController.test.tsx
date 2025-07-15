import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import SpatialAudioController from '../audio/SpatialAudioController';
import { spatialAudioEngine } from '@/services/spatialAudioEngine';
import { locationService } from '@/services/locationService';

// Mock dependencies
jest.mock('@/services/spatialAudioEngine');
jest.mock('@/services/locationService');
jest.mock('@expo/vector-icons', () => ({
  MaterialIcons: 'Icon',
  MaterialCommunityIcons: 'Icon',
}));
jest.mock('react-native-paper', () => ({
  ...jest.requireActual('react-native-paper'),
  Portal: ({ children }: any) => children,
  Modal: ({ visible, children }: any) => visible ? children : null,
}));

describe('SpatialAudioController', () => {
  const mockOnSettingsChange = jest.fn();
  const mockOnClose = jest.fn();
  
  const mockLocation = {
    latitude: 37.7749,
    longitude: -122.4194,
    timestamp: Date.now(),
    accuracy: 10,
    altitude: null,
    altitudeAccuracy: null,
    heading: 45,
    speed: 30,
  };

  const mockAudioState = {
    isPlaying: true,
    volume: 0.8,
    spatialEnabled: true,
    sources: [
      {
        id: 'nature-1',
        type: 'nature',
        position: { x: 10, y: 0, z: 5 },
        volume: 0.6,
        label: 'Forest Ambience',
      },
      {
        id: 'story-1',
        type: 'story',
        position: { x: 0, y: 0, z: 0 },
        volume: 1.0,
        label: 'Narrator Voice',
      },
    ],
    listenerPosition: { x: 0, y: 0, z: 0 },
    listenerOrientation: { forward: [0, 0, -1], up: [0, 1, 0] },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (locationService.getCurrentLocation as jest.Mock).mockResolvedValue(mockLocation);
    (spatialAudioEngine.getState as jest.Mock).mockReturnValue(mockAudioState);
    (spatialAudioEngine.isInitialized as jest.Mock).mockReturnValue(true);
  });

  it('renders spatial audio controls', () => {
    const { getByText, getByTestId } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    expect(getByText('Spatial Audio')).toBeTruthy();
    expect(getByTestId('spatial-toggle')).toBeTruthy();
    expect(getByTestId('master-volume')).toBeTruthy();
  });

  it('toggles spatial audio', async () => {
    const { getByTestId } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    const toggle = getByTestId('spatial-toggle');
    fireEvent(toggle, 'onValueChange', false);
    
    await waitFor(() => {
      expect(spatialAudioEngine.setSpatialEnabled).toHaveBeenCalledWith(false);
      expect(mockOnSettingsChange).toHaveBeenCalledWith({
        spatialEnabled: false,
      });
    });
  });

  it('adjusts master volume', async () => {
    const { getByTestId } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    const volumeSlider = getByTestId('master-volume');
    fireEvent(volumeSlider, 'onValueChange', 0.5);
    
    await waitFor(() => {
      expect(spatialAudioEngine.setMasterVolume).toHaveBeenCalledWith(0.5);
      expect(mockOnSettingsChange).toHaveBeenCalledWith({
        volume: 0.5,
      });
    });
  });

  it('displays audio sources', () => {
    const { getByText } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    expect(getByText('Forest Ambience')).toBeTruthy();
    expect(getByText('Narrator Voice')).toBeTruthy();
  });

  it('adjusts individual source volume', async () => {
    const { getByTestId } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    const sourceVolume = getByTestId('source-volume-nature-1');
    fireEvent(sourceVolume, 'onValueChange', 0.3);
    
    await waitFor(() => {
      expect(spatialAudioEngine.setSourceVolume).toHaveBeenCalledWith('nature-1', 0.3);
    });
  });

  it('mutes individual source', async () => {
    const { getByTestId } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    const muteButton = getByTestId('mute-source-nature-1');
    fireEvent.press(muteButton);
    
    await waitFor(() => {
      expect(spatialAudioEngine.muteSource).toHaveBeenCalledWith('nature-1');
    });
  });

  it('opens advanced settings', async () => {
    const { getByText, getByTestId } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    const advancedButton = getByText('Advanced Settings');
    fireEvent.press(advancedButton);
    
    await waitFor(() => {
      expect(getByText('3D Audio Settings')).toBeTruthy();
      expect(getByTestId('doppler-effect')).toBeTruthy();
      expect(getByTestId('distance-model')).toBeTruthy();
    });
  });

  it('toggles doppler effect', async () => {
    const { getByText, getByTestId } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    // Open advanced settings
    fireEvent.press(getByText('Advanced Settings'));
    
    await waitFor(() => {
      const dopplerToggle = getByTestId('doppler-effect');
      fireEvent(dopplerToggle, 'onValueChange', true);
    });
    
    await waitFor(() => {
      expect(spatialAudioEngine.setDopplerEffect).toHaveBeenCalledWith(true);
    });
  });

  it('changes distance model', async () => {
    const { getByText } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    // Open advanced settings
    fireEvent.press(getByText('Advanced Settings'));
    
    await waitFor(() => {
      const exponentialChip = getByText('Exponential');
      fireEvent.press(exponentialChip);
    });
    
    await waitFor(() => {
      expect(spatialAudioEngine.setDistanceModel).toHaveBeenCalledWith('exponential');
    });
  });

  it('displays 3D visualization', () => {
    const { getByTestId } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
        show3DVisualization={true}
      />
    );
    
    expect(getByTestId('3d-visualization')).toBeTruthy();
    expect(getByTestId('listener-position')).toBeTruthy();
    mockAudioState.sources.forEach(source => {
      expect(getByTestId(`source-position-${source.id}`)).toBeTruthy();
    });
  });

  it('resets to defaults', async () => {
    const { getByText } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    const resetButton = getByText('Reset to Defaults');
    fireEvent.press(resetButton);
    
    await waitFor(() => {
      expect(spatialAudioEngine.reset).toHaveBeenCalled();
      expect(mockOnSettingsChange).toHaveBeenCalledWith({
        spatialEnabled: true,
        volume: 1.0,
      });
    });
  });

  it('handles initialization error', async () => {
    (spatialAudioEngine.isInitialized as jest.Mock).mockReturnValue(false);
    (spatialAudioEngine.initialize as jest.Mock).mockRejectedValue(new Error('Audio error'));
    
    const { getByText } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    await waitFor(() => {
      expect(getByText('Failed to initialize spatial audio')).toBeTruthy();
    });
  });

  it('handles close button', () => {
    const { getByTestId } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        onClose={mockOnClose}
        isVisible={true}
      />
    );
    
    const closeButton = getByTestId('close-button');
    fireEvent.press(closeButton);
    
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('updates on location change', async () => {
    const { rerender } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    const newLocation = { ...mockLocation, heading: 90 };
    (locationService.getCurrentLocation as jest.Mock).mockResolvedValue(newLocation);
    
    rerender(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    await waitFor(() => {
      expect(spatialAudioEngine.updateListenerOrientation).toHaveBeenCalled();
    });
  });

  it('displays audio presets', async () => {
    const { getByText } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    expect(getByText('Presets')).toBeTruthy();
    expect(getByText('Immersive')).toBeTruthy();
    expect(getByText('Focused')).toBeTruthy();
    expect(getByText('Ambient')).toBeTruthy();
  });

  it('applies audio preset', async () => {
    const { getByText } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
      />
    );
    
    const immersivePreset = getByText('Immersive');
    fireEvent.press(immersivePreset);
    
    await waitFor(() => {
      expect(spatialAudioEngine.applyPreset).toHaveBeenCalledWith('immersive');
      expect(mockOnSettingsChange).toHaveBeenCalled();
    });
  });

  it('shows performance impact warning', async () => {
    const { getByText } = render(
      <SpatialAudioController 
        onSettingsChange={mockOnSettingsChange}
        isVisible={true}
        showPerformanceWarning={true}
      />
    );
    
    expect(getByText(/may impact battery life/)).toBeTruthy();
  });
});