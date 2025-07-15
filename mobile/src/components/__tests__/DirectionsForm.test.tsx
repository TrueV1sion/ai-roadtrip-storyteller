import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import DirectionsForm, { DirectionsParams } from '../navigation/DirectionsForm';
import { useLocationSearch } from '@/hooks/useLocationSearch';
import { useCurrentLocation } from '@/hooks/useCurrentLocation';
import { TravelMode } from '@/types/navigation';

// Mock dependencies
jest.mock('@/hooks/useLocationSearch');
jest.mock('@/hooks/useCurrentLocation');
jest.mock('@expo/vector-icons', () => ({
  MaterialIcons: 'Icon',
  MaterialCommunityIcons: 'Icon',
}));
jest.mock('react-native-paper', () => ({
  ...jest.requireActual('react-native-paper'),
  Portal: ({ children }: any) => children,
  Modal: ({ visible, children }: any) => visible ? children : null,
}));
jest.mock('react-native-maps', () => ({
  __esModule: true,
  default: jest.fn(props => <div testID="map-view" {...props} />),
  Marker: jest.fn(props => <div testID="map-marker" {...props} />),
  Polyline: jest.fn(props => <div testID="map-polyline" {...props} />),
  PROVIDER_GOOGLE: 'google',
}));
jest.mock('react-native-chart-kit', () => ({
  LineChart: jest.fn(props => <div testID="line-chart" {...props} />),
}));

// Mock fetch
global.fetch = jest.fn();

describe('DirectionsForm', () => {
  const mockOnSubmit = jest.fn();
  const mockSearchLocations = jest.fn();
  
  const mockLocation = {
    latitude: 37.7749,
    longitude: -122.4194,
    name: 'San Francisco',
    address: '123 Main St',
    id: 'sf-1',
  };
  
  const mockDestination = {
    latitude: 34.0522,
    longitude: -118.2437,
    name: 'Los Angeles',
    address: '456 Broadway',
    id: 'la-1',
  };
  
  const mockSearchResults = [
    {
      id: '1',
      name: 'Golden Gate Bridge',
      address: 'Golden Gate Bridge, San Francisco, CA',
      latitude: 37.8199,
      longitude: -122.4783,
    },
    {
      id: '2',
      name: 'Fisherman\'s Wharf',
      address: 'Fisherman\'s Wharf, San Francisco, CA',
      latitude: 37.8080,
      longitude: -122.4177,
    },
  ];

  const mockRoutePreview = {
    coordinates: [
      { latitude: 37.7749, longitude: -122.4194 },
      { latitude: 36.7783, longitude: -119.4179 },
      { latitude: 34.0522, longitude: -118.2437 },
    ],
    distance: 616000, // meters
    duration: 21600, // seconds (6 hours)
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useLocationSearch as jest.Mock).mockReturnValue({
      searchLocations: mockSearchLocations,
      results: mockSearchResults,
      loading: false,
    });
    (useCurrentLocation as jest.Mock).mockReturnValue({
      currentLocation: mockLocation,
    });
    (fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockRoutePreview,
    });
  });

  it('renders form with initial values', () => {
    const { getByLabelText } = render(
      <DirectionsForm 
        onSubmit={mockOnSubmit}
        initialOrigin={mockLocation}
        initialDestination={mockDestination}
      />
    );
    
    expect(getByLabelText('Starting point')).toBeTruthy();
    expect(getByLabelText('Destination')).toBeTruthy();
  });

  it('handles origin selection', async () => {
    const { getByLabelText, getByText } = render(
      <DirectionsForm onSubmit={mockOnSubmit} />
    );
    
    const originInput = getByLabelText('Starting point');
    fireEvent.focus(originInput);
    fireEvent.changeText(originInput, 'Golden Gate');
    
    await waitFor(() => {
      expect(mockSearchLocations).toHaveBeenCalledWith('Golden Gate');
    });
    
    // Select a search result
    fireEvent.press(getByText('Golden Gate Bridge'));
    
    await waitFor(() => {
      expect(originInput.props.value).toContain('Golden Gate Bridge');
    });
  });

  it('handles destination selection', async () => {
    const { getByLabelText, getByText } = render(
      <DirectionsForm onSubmit={mockOnSubmit} />
    );
    
    const destinationInput = getByLabelText('Destination');
    fireEvent.focus(destinationInput);
    fireEvent.changeText(destinationInput, 'Fisherman');
    
    await waitFor(() => {
      expect(mockSearchLocations).toHaveBeenCalledWith('Fisherman');
    });
    
    fireEvent.press(getByText('Fisherman\'s Wharf'));
    
    await waitFor(() => {
      expect(destinationInput.props.value).toContain('Fisherman\'s Wharf');
    });
  });

  it('uses current location when GPS button is pressed', async () => {
    const { getByTestId } = render(
      <DirectionsForm onSubmit={mockOnSubmit} />
    );
    
    const gpsButton = getByTestId('use-current-location');
    fireEvent.press(gpsButton);
    
    await waitFor(() => {
      const originInput = getByTestId('origin-input');
      expect(originInput.props.value).toBe('San Francisco');
    });
  });

  it('adds and removes waypoints', async () => {
    const { getByText, getAllByLabelText, getByTestId } = render(
      <DirectionsForm onSubmit={mockOnSubmit} />
    );
    
    // Add waypoint
    fireEvent.press(getByText('Add stop'));
    
    await waitFor(() => {
      expect(getByLabelText('Stop 1')).toBeTruthy();
    });
    
    // Remove waypoint
    const removeButton = getByTestId('remove-waypoint-0');
    fireEvent.press(removeButton);
    
    await waitFor(() => {
      expect(getAllByLabelText(/Stop/).length).toBe(0);
    });
  });

  it('changes route type', async () => {
    const { getByText } = render(
      <DirectionsForm onSubmit={mockOnSubmit} />
    );
    
    // Default is 'balanced'
    const scenicButton = getByText('Scenic');
    fireEvent.press(scenicButton);
    
    // Check if scenic is selected (would have different styling)
    await waitFor(() => {
      expect(scenicButton.parent.props.style).toMatchObject({
        backgroundColor: expect.any(String),
      });
    });
  });

  it('changes travel mode', async () => {
    const { getByText } = render(
      <DirectionsForm onSubmit={mockOnSubmit} />
    );
    
    const walkingChip = getByText('Walking');
    fireEvent.press(walkingChip);
    
    // Chip should be selected
    await waitFor(() => {
      expect(walkingChip.parent.props.selected).toBe(true);
    });
  });

  it('opens and configures advanced options', async () => {
    const { getByText, getByTestId } = render(
      <DirectionsForm onSubmit={mockOnSubmit} />
    );
    
    fireEvent.press(getByText('Route options'));
    
    await waitFor(() => {
      expect(getByText('Route Options')).toBeTruthy();
    });
    
    // Toggle switches
    const trafficSwitch = getByTestId('traffic-switch');
    fireEvent(trafficSwitch, 'onValueChange', false);
    
    const alternativesSwitch = getByTestId('alternatives-switch');
    fireEvent(alternativesSwitch, 'onValueChange', true);
    
    fireEvent.press(getByText('Done'));
    
    await waitFor(() => {
      expect(getByText('Route Options')).not.toBeTruthy();
    });
  });

  it('fetches and displays route preview', async () => {
    const { getByLabelText, getByText } = render(
      <DirectionsForm 
        onSubmit={mockOnSubmit}
        initialOrigin={mockLocation}
        initialDestination={mockDestination}
      />
    );
    
    // Wait for preview to load
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/directions/preview'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.stringContaining('"origin"'),
        })
      );
    });
    
    await waitFor(() => {
      expect(getByText('Route Preview')).toBeTruthy();
      expect(getByText(/Distance: .* km/)).toBeTruthy();
      expect(getByText(/Time: .* hours/)).toBeTruthy();
    });
  });

  it('submits form with all parameters', async () => {
    const { getByText } = render(
      <DirectionsForm 
        onSubmit={mockOnSubmit}
        initialOrigin={mockLocation}
        initialDestination={mockDestination}
      />
    );
    
    // Change some options
    fireEvent.press(getByText('Eco'));
    fireEvent.press(getByText('Transit'));
    
    // Submit
    fireEvent.press(getByText('Start Navigation'));
    
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        origin: mockLocation,
        destination: mockDestination,
        mode: 'transit',
        optimizeRoute: true,
        includeTraffic: true,
        includePlaces: true,
        alternatives: false,
        routeType: 'eco',
      } as DirectionsParams);
    });
  });

  it('disables submit button without origin and destination', () => {
    const { getByText } = render(
      <DirectionsForm onSubmit={mockOnSubmit} />
    );
    
    const submitButton = getByText('Start Navigation');
    expect(submitButton.props.disabled).toBe(true);
  });

  it('handles route preview error gracefully', async () => {
    (fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));
    
    const { queryByText } = render(
      <DirectionsForm 
        onSubmit={mockOnSubmit}
        initialOrigin={mockLocation}
        initialDestination={mockDestination}
      />
    );
    
    // Should not show preview on error
    await waitFor(() => {
      expect(queryByText('Route Preview')).toBeNull();
    });
  });

  it('displays alternative routes when enabled', async () => {
    const alternativeRoutes = [
      {
        ...mockRoutePreview,
        scenicScore: 85,
        trafficDelay: 1200,
      },
      {
        ...mockRoutePreview,
        distance: 650000,
        duration: 23400,
        scenicScore: 95,
      },
    ];
    
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ...mockRoutePreview, alternatives: alternativeRoutes }),
    });
    
    const { getByText } = render(
      <DirectionsForm 
        onSubmit={mockOnSubmit}
        initialOrigin={mockLocation}
        initialDestination={mockDestination}
      />
    );
    
    // Enable alternatives
    fireEvent.press(getByText('Route options'));
    await waitFor(() => {
      const alternativesSwitch = getByTestId('alternatives-switch');
      fireEvent(alternativesSwitch, 'onValueChange', true);
    });
    fireEvent.press(getByText('Done'));
    
    await waitFor(() => {
      expect(getByText('Route Alternatives')).toBeTruthy();
      expect(getByText('Route 1 (Selected)')).toBeTruthy();
      expect(getByText('Route 2')).toBeTruthy();
    });
  });

  it('toggles elevation and weather views', async () => {
    const { getByText, getByTestId } = render(
      <DirectionsForm 
        onSubmit={mockOnSubmit}
        initialOrigin={mockLocation}
        initialDestination={mockDestination}
      />
    );
    
    await waitFor(() => {
      expect(getByText('Route Preview')).toBeTruthy();
    });
    
    // Toggle elevation
    const elevationChip = getByText('Elevation');
    fireEvent.press(elevationChip);
    
    await waitFor(() => {
      expect(getByTestId('line-chart')).toBeTruthy();
    });
    
    // Toggle weather
    const weatherChip = getByText('Weather');
    fireEvent.press(weatherChip);
    
    await waitFor(() => {
      expect(getByText('Weather Along Route')).toBeTruthy();
    });
  });

  it('handles waypoint reordering', async () => {
    const { getByText, getByLabelText } = render(
      <DirectionsForm onSubmit={mockOnSubmit} />
    );
    
    // Add multiple waypoints
    fireEvent.press(getByText('Add stop'));
    fireEvent.press(getByText('Add stop'));
    
    await waitFor(() => {
      expect(getByLabelText('Stop 1')).toBeTruthy();
      expect(getByLabelText('Stop 2')).toBeTruthy();
    });
    
    // Select locations for waypoints
    const stop1 = getByLabelText('Stop 1');
    fireEvent.focus(stop1);
    fireEvent.changeText(stop1, 'Golden Gate');
    fireEvent.press(getByText('Golden Gate Bridge'));
    
    const stop2 = getByLabelText('Stop 2');
    fireEvent.focus(stop2);
    fireEvent.changeText(stop2, 'Fisherman');
    fireEvent.press(getByText('Fisherman\'s Wharf'));
    
    // Verify waypoints are set correctly
    await waitFor(() => {
      expect(stop1.props.value).toContain('Golden Gate Bridge');
      expect(stop2.props.value).toContain('Fisherman\'s Wharf');
    });
  });
});