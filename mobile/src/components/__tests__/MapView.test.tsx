import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import { Alert } from 'react-native';
import MapScreenComponent from '../MapView';
import { locationService } from '@/services/locationService';
import { apiClient } from '@/services/api/ApiClient';

// Mock dependencies
jest.mock('@/services/locationService');
jest.mock('@/services/api/ApiClient');
jest.mock('react-native-maps', () => {
  const { View } = require('react-native');
  return {
    __esModule: true,
    default: jest.fn(props => <View testID="map-view" {...props} />),
    Marker: jest.fn(props => <View testID="map-marker" {...props} />),
    Polyline: jest.fn(props => <View testID="map-polyline" {...props} />),
    PROVIDER_GOOGLE: 'google',
  };
});

// Mock Alert
jest.spyOn(Alert, 'alert');

describe('MapScreenComponent', () => {
  const mockLocation = {
    latitude: 37.7749,
    longitude: -122.4194,
    timestamp: Date.now(),
    accuracy: 10,
    altitude: null,
    altitudeAccuracy: null,
    heading: null,
    speed: null,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (locationService.initialize as jest.Mock).mockResolvedValue(undefined);
    (locationService.getCurrentLocation as jest.Mock).mockResolvedValue(mockLocation);
  });

  it('renders loading state initially', () => {
    const { getByText } = render(<MapScreenComponent />);
    
    expect(getByText('Getting your location...')).toBeTruthy();
  });

  it('renders map after location is loaded', async () => {
    const { getByTestId, queryByText } = render(<MapScreenComponent />);
    
    await waitFor(() => {
      expect(queryByText('Getting your location...')).toBeNull();
    });
    
    expect(getByTestId('map-view')).toBeTruthy();
  });

  it('shows error when location cannot be determined', async () => {
    (locationService.getCurrentLocation as jest.Mock).mockResolvedValue(null);
    
    const { getByText } = render(<MapScreenComponent />);
    
    await waitFor(() => {
      expect(getByText(/Could not get current location/)).toBeTruthy();
    });
  });

  it('fetches route when button is pressed', async () => {
    const mockRoute = {
      routes: [{
        overview_polyline: {
          points: '_p~iF~ps|U_ulLnnqC_mqNvxq`@'
        }
      }]
    };
    
    (apiClient.post as jest.Mock).mockResolvedValue(mockRoute);
    
    const { getByText, queryByTestId } = render(<MapScreenComponent />);
    
    await waitFor(() => {
      expect(getByText('Route to Times Square')).toBeTruthy();
    });
    
    fireEvent.press(getByText('Route to Times Square'));
    
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/directions', {
        origin: '37.7749,-122.4194',
        destination: 'Times Square, New York, NY',
        mode: 'driving'
      });
    });
    
    await waitFor(() => {
      expect(queryByTestId('map-polyline')).toBeTruthy();
    });
  });

  it('shows error alert when location not available for route', async () => {
    (locationService.getCurrentLocation as jest.Mock).mockResolvedValue(null);
    
    const { getByText } = render(<MapScreenComponent />);
    
    await waitFor(() => {
      expect(getByText(/Location could not be determined/)).toBeTruthy();
    });
  });

  it('handles route fetch error', async () => {
    (apiClient.post as jest.Mock).mockRejectedValue(new Error('Network error'));
    
    const { getByText } = render(<MapScreenComponent />);
    
    await waitFor(() => {
      expect(getByText('Route to Times Square')).toBeTruthy();
    });
    
    fireEvent.press(getByText('Route to Times Square'));
    
    await waitFor(() => {
      expect(getByText(/Failed to fetch route: Network error/)).toBeTruthy();
    });
  });

  it('disables button while fetching route', async () => {
    let resolvePost: (value: any) => void;
    const postPromise = new Promise(resolve => {
      resolvePost = resolve;
    });
    
    (apiClient.post as jest.Mock).mockReturnValue(postPromise);
    
    const { getByText } = render(<MapScreenComponent />);
    
    await waitFor(() => {
      expect(getByText('Route to Times Square')).toBeTruthy();
    });
    
    fireEvent.press(getByText('Route to Times Square'));
    
    await waitFor(() => {
      expect(getByText('Fetching Route...')).toBeTruthy();
    });
    
    // Button should be disabled
    expect(getByText('Fetching Route...').props.disabled).toBe(true);
    
    // Resolve the promise
    resolvePost!({
      routes: [{
        overview_polyline: { points: '_p~iF~ps|U_ulLnnqC' }
      }]
    });
    
    await waitFor(() => {
      expect(getByText('Route to Times Square')).toBeTruthy();
    });
  });

  it('handles empty route response', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({ routes: [] });
    
    const { getByText } = render(<MapScreenComponent />);
    
    await waitFor(() => {
      expect(getByText('Route to Times Square')).toBeTruthy();
    });
    
    fireEvent.press(getByText('Route to Times Square'));
    
    await waitFor(() => {
      expect(getByText('No route found.')).toBeTruthy();
    });
  });

  it('initializes location service on mount', async () => {
    render(<MapScreenComponent />);
    
    await waitFor(() => {
      expect(locationService.initialize).toHaveBeenCalled();
      expect(locationService.getCurrentLocation).toHaveBeenCalled();
    });
  });

  it('sets correct initial region for map', async () => {
    const { getByTestId } = render(<MapScreenComponent />);
    
    await waitFor(() => {
      const mapView = getByTestId('map-view');
      expect(mapView.props.initialRegion).toEqual({
        latitude: 37.7749,
        longitude: -122.4194,
        latitudeDelta: 0.0922,
        longitudeDelta: 0.0421,
      });
    });
  });
});