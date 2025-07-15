import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import * as Location from 'expo-location';
import { Camera } from 'expo-camera';

import ARView from '../ARView';
import { ARService } from '../../../services/ar/arService';

// Mock dependencies
jest.mock('expo-location');
jest.mock('expo-camera');
jest.mock('../../../services/ar/arService');

const mockLocation = Location as jest.Mocked<typeof Location>;
const mockCamera = Camera as jest.Mocked<typeof Camera>;
const mockARService = ARService as jest.Mocked<typeof ARService>;

describe('ARView Component', () => {
  const mockPOIs = [
    {
      id: '1',
      name: 'Golden Gate Bridge',
      type: 'landmark',
      location: { lat: 37.8199, lng: -122.4783 },
      distance: 2.5,
      bearing: 45,
      description: 'Iconic San Francisco bridge',
    },
    {
      id: '2',
      name: 'Alcatraz Island',
      type: 'landmark',
      location: { lat: 37.8267, lng: -122.4230 },
      distance: 5.2,
      bearing: 90,
      description: 'Former federal prison',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    
    mockCamera.requestCameraPermissionsAsync.mockResolvedValue({ status: 'granted' });
    mockLocation.requestForegroundPermissionsAsync.mockResolvedValue({ status: 'granted' });
    mockLocation.getCurrentPositionAsync.mockResolvedValue({
      coords: {
        latitude: 37.7749,
        longitude: -122.4194,
        altitude: 10,
        accuracy: 5,
        altitudeAccuracy: 5,
        heading: 0,
        speed: 0,
      },
      timestamp: Date.now(),
    });
    
    mockARService.getNearbyPOIs.mockResolvedValue(mockPOIs);
  });

  it('requests necessary permissions on mount', async () => {
    render(<ARView />);
    
    await waitFor(() => {
      expect(mockCamera.requestCameraPermissionsAsync).toHaveBeenCalled();
      expect(mockLocation.requestForegroundPermissionsAsync).toHaveBeenCalled();
    });
  });

  it('shows permission denied message if camera denied', async () => {
    mockCamera.requestCameraPermissionsAsync.mockResolvedValue({ status: 'denied' });
    
    const { getByText } = render(<ARView />);
    
    await waitFor(() => {
      expect(getByText('Camera permission is required for AR features')).toBeTruthy();
    });
  });

  it('renders AR overlay with POIs', async () => {
    const { getByText, getAllByTestId } = render(<ARView />);
    
    await waitFor(() => {
      expect(mockARService.getNearbyPOIs).toHaveBeenCalled();
      expect(getByText('Golden Gate Bridge')).toBeTruthy();
      expect(getByText('Alcatraz Island')).toBeTruthy();
    });
    
    const arElements = getAllByTestId(/ar-element-/);
    expect(arElements).toHaveLength(2);
  });

  it('updates POI positions based on device orientation', async () => {
    const { getAllByTestId } = render(<ARView />);
    
    await waitFor(() => {
      expect(mockARService.getNearbyPOIs).toHaveBeenCalled();
    });
    
    // Simulate device rotation
    const mockOrientation = {
      alpha: 90, // Rotation around z-axis
      beta: 0,
      gamma: 0,
    };
    
    fireEvent(window, 'deviceorientation', mockOrientation);
    
    await waitFor(() => {
      const arElements = getAllByTestId(/ar-element-/);
      arElements.forEach(element => {
        expect(element.props.style.transform).toBeDefined();
      });
    });
  });

  it('shows distance to POIs', async () => {
    const { getByText } = render(<ARView />);
    
    await waitFor(() => {
      expect(getByText('2.5 km')).toBeTruthy();
      expect(getByText('5.2 km')).toBeTruthy();
    });
  });

  it('allows tapping on POI for details', async () => {
    const { getByText, getByTestId } = render(<ARView />);
    
    await waitFor(() => {
      expect(getByText('Golden Gate Bridge')).toBeTruthy();
    });
    
    fireEvent.press(getByTestId('ar-element-1'));
    
    await waitFor(() => {
      expect(getByText('Iconic San Francisco bridge')).toBeTruthy();
      expect(getByText('Navigate')).toBeTruthy();
      expect(getByText('More Info')).toBeTruthy();
    });
  });

  it('filters POIs by type', async () => {
    const { getByText, queryByText } = render(<ARView />);
    
    await waitFor(() => {
      expect(getByText('Golden Gate Bridge')).toBeTruthy();
    });
    
    // Add restaurant POI
    const restaurantPOI = {
      id: '3',
      name: 'Famous Restaurant',
      type: 'restaurant',
      location: { lat: 37.7849, lng: -122.4094 },
      distance: 0.5,
      bearing: 180,
    };
    
    mockARService.getNearbyPOIs.mockResolvedValue([...mockPOIs, restaurantPOI]);
    
    // Toggle filter
    fireEvent.press(getByText('Filter'));
    fireEvent.press(getByText('Restaurants'));
    
    await waitFor(() => {
      expect(queryByText('Golden Gate Bridge')).toBeNull();
      expect(queryByText('Alcatraz Island')).toBeNull();
      expect(getByText('Famous Restaurant')).toBeTruthy();
    });
  });

  it('shows radar view with POI directions', async () => {
    const { getByTestId, getAllByTestId } = render(<ARView showRadar={true} />);
    
    await waitFor(() => {
      expect(getByTestId('ar-radar')).toBeTruthy();
    });
    
    const radarDots = getAllByTestId(/radar-dot-/);
    expect(radarDots).toHaveLength(2);
  });

  it('updates POI list as user moves', async () => {
    const { rerender } = render(<ARView />);
    
    await waitFor(() => {
      expect(mockARService.getNearbyPOIs).toHaveBeenCalledTimes(1);
    });
    
    // Simulate location change
    mockLocation.getCurrentPositionAsync.mockResolvedValue({
      coords: {
        latitude: 37.7849,
        longitude: -122.4094,
        altitude: 10,
        accuracy: 5,
        altitudeAccuracy: 5,
        heading: 0,
        speed: 0,
      },
      timestamp: Date.now(),
    });
    
    // Trigger location update
    rerender(<ARView />);
    
    await waitFor(() => {
      expect(mockARService.getNearbyPOIs).toHaveBeenCalledTimes(2);
    });
  });

  it('handles AR tracking loss gracefully', async () => {
    const { getByText } = render(<ARView />);
    
    // Simulate tracking loss
    fireEvent(window, 'arSessionInterrupted');
    
    await waitFor(() => {
      expect(getByText('Move your device slowly to restore AR tracking')).toBeTruthy();
    });
  });

  it('provides haptic feedback when POI is in view', async () => {
    const mockHaptic = jest.fn();
    jest.mock('expo-haptics', () => ({
      impactAsync: mockHaptic,
    }));
    
    const { getByTestId } = render(<ARView enableHaptics={true} />);
    
    await waitFor(() => {
      expect(mockARService.getNearbyPOIs).toHaveBeenCalled();
    });
    
    // Simulate POI entering center of view
    fireEvent(getByTestId('ar-element-1'), 'onEnterFocus');
    
    expect(mockHaptic).toHaveBeenCalled();
  });

  it('saves POI to favorites', async () => {
    const onSavePOI = jest.fn();
    const { getByText, getByTestId } = render(<ARView onSavePOI={onSavePOI} />);
    
    await waitFor(() => {
      expect(getByText('Golden Gate Bridge')).toBeTruthy();
    });
    
    fireEvent.press(getByTestId('ar-element-1'));
    fireEvent.press(getByText('Save'));
    
    expect(onSavePOI).toHaveBeenCalledWith(mockPOIs[0]);
  });
});