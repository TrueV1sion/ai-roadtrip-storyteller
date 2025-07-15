import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import LocationEnrichmentCard from '../LocationEnrichmentCard';
import { locationEnrichmentService } from '@/services/locationEnrichmentService';

// Mock dependencies
jest.mock('@/services/locationEnrichmentService');
jest.mock('@expo/vector-icons', () => ({
  Ionicons: 'Icon',
}));

describe('LocationEnrichmentCard', () => {
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

  const mockEnrichedData = {
    locationName: 'San Francisco',
    places: [
      {
        id: 'place1',
        name: 'Golden Gate Bridge',
        type: 'landmark',
        distance: 5000,
        rating: 4.8,
        reviewCount: 10000,
        tags: ['landmark', 'bridge', 'scenic'],
        address: '123 Bridge St',
        contact: {
          phone: '(415) 123-4567',
          website: 'www.example.com',
        },
      },
      {
        id: 'place2',
        name: 'Italian Restaurant',
        type: 'restaurant',
        distance: 1000,
        rating: 4.5,
        tags: ['italian', 'dinner'],
      },
    ],
    historicalFacts: [
      {
        id: 'fact1',
        title: 'Gold Rush Era',
        description: 'San Francisco grew rapidly during the California Gold Rush',
        year: '1849',
        source: 'History Channel',
        link: 'https://example.com',
        tags: ['history', 'gold rush'],
      },
    ],
    weather: {
      currentConditions: {
        temperature: 22,
        condition: 'Partly Cloudy',
        humidity: 65,
        windSpeed: 10,
      },
      forecast: [
        {
          dayOfWeek: 'Monday',
          date: '2024-01-01',
          condition: 'Sunny',
          high: 25,
          low: 15,
          precipitationProbability: 10,
        },
      ],
    },
  };

  const mockGroupedPlaces = {
    'Landmarks': [mockEnrichedData.places[0]],
    'Restaurants': [mockEnrichedData.places[1]],
  };

  const mockFormattedFacts = mockEnrichedData.historicalFacts;

  const mockWeatherDisplay = {
    conditions: ['Humidity: 65%', 'Wind: 10 km/h'],
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (locationEnrichmentService.getEnrichedLocationInfo as jest.Mock).mockResolvedValue(mockEnrichedData);
    (locationEnrichmentService.formatPlacesForDisplay as jest.Mock).mockReturnValue(mockGroupedPlaces);
    (locationEnrichmentService.formatHistoricalFactsForDisplay as jest.Mock).mockReturnValue(mockFormattedFacts);
    (locationEnrichmentService.formatWeatherForDisplay as jest.Mock).mockReturnValue(mockWeatherDisplay);
  });

  it('renders loading state initially', () => {
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    expect(getByText('Loading location information...')).toBeTruthy();
  });

  it('renders location data after loading', async () => {
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      expect(getByText('San Francisco')).toBeTruthy();
    });
  });

  it('renders tabs', async () => {
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      expect(getByText('Places')).toBeTruthy();
      expect(getByText('History')).toBeTruthy();
      expect(getByText('Weather')).toBeTruthy();
    });
  });

  it('switches tabs when pressed', async () => {
    const { getByText, getByTestId } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      expect(getByText('Places')).toBeTruthy();
    });
    
    // Switch to History tab
    fireEvent.press(getByText('History'));
    
    await waitFor(() => {
      expect(getByText('Gold Rush Era')).toBeTruthy();
    });
    
    // Switch to Weather tab
    fireEvent.press(getByText('Weather'));
    
    await waitFor(() => {
      expect(getByText('22°C')).toBeTruthy();
      expect(getByText('Partly Cloudy')).toBeTruthy();
    });
  });

  it('renders places by category', async () => {
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      expect(getByText('Landmarks')).toBeTruthy();
      expect(getByText('Golden Gate Bridge')).toBeTruthy();
      expect(getByText('Restaurants')).toBeTruthy();
      expect(getByText('Italian Restaurant')).toBeTruthy();
    });
  });

  it('shows place details when place is pressed', async () => {
    const mockOnPlaceSelected = jest.fn();
    const { getByText } = render(
      <LocationEnrichmentCard 
        location={mockLocation} 
        onPlaceSelected={mockOnPlaceSelected}
      />
    );
    
    await waitFor(() => {
      expect(getByText('Golden Gate Bridge')).toBeTruthy();
    });
    
    fireEvent.press(getByText('Golden Gate Bridge'));
    
    await waitFor(() => {
      expect(mockOnPlaceSelected).toHaveBeenCalledWith(mockEnrichedData.places[0]);
      // Modal should show
      expect(getByText('123 Bridge St')).toBeTruthy();
      expect(getByText('Phone: (415) 123-4567')).toBeTruthy();
    });
  });

  it('closes place modal when back button is pressed', async () => {
    const { getByText, getByTestId, queryByText } = render(
      <LocationEnrichmentCard location={mockLocation} />
    );
    
    await waitFor(() => {
      fireEvent.press(getByText('Golden Gate Bridge'));
    });
    
    await waitFor(() => {
      expect(getByText('123 Bridge St')).toBeTruthy();
    });
    
    // Find and press the back button in modal
    const backButton = getByTestId('modal-close-button');
    fireEvent.press(backButton);
    
    await waitFor(() => {
      expect(queryByText('123 Bridge St')).toBeNull();
    });
  });

  it('renders historical facts', async () => {
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      fireEvent.press(getByText('History'));
    });
    
    await waitFor(() => {
      expect(getByText('Gold Rush Era')).toBeTruthy();
      expect(getByText('1849')).toBeTruthy();
      expect(getByText('San Francisco grew rapidly during the California Gold Rush')).toBeTruthy();
      expect(getByText('Source: History Channel')).toBeTruthy();
    });
  });

  it('renders weather information', async () => {
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      fireEvent.press(getByText('Weather'));
    });
    
    await waitFor(() => {
      expect(getByText('22°C')).toBeTruthy();
      expect(getByText('Partly Cloudy')).toBeTruthy();
      expect(getByText('Humidity: 65%')).toBeTruthy();
      expect(getByText('Wind: 10 km/h')).toBeTruthy();
      expect(getByText('5-Day Forecast')).toBeTruthy();
      expect(getByText('Monday')).toBeTruthy();
      expect(getByText('25°')).toBeTruthy();
      expect(getByText('15°')).toBeTruthy();
    });
  });

  it('handles error state', async () => {
    (locationEnrichmentService.getEnrichedLocationInfo as jest.Mock).mockRejectedValue(
      new Error('Network error')
    );
    
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      expect(getByText('Failed to load location information')).toBeTruthy();
    });
  });

  it('handles retry after error', async () => {
    (locationEnrichmentService.getEnrichedLocationInfo as jest.Mock)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce(mockEnrichedData);
    
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      expect(getByText('Failed to load location information')).toBeTruthy();
    });
    
    fireEvent.press(getByText('Retry'));
    
    await waitFor(() => {
      expect(getByText('San Francisco')).toBeTruthy();
    });
  });

  it('shows no weather data message when weather is null', async () => {
    (locationEnrichmentService.getEnrichedLocationInfo as jest.Mock).mockResolvedValue({
      ...mockEnrichedData,
      weather: null,
    });
    
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      fireEvent.press(getByText('Weather'));
    });
    
    await waitFor(() => {
      expect(getByText('Weather data is not available')).toBeTruthy();
    });
  });

  it('calls onClose when close button is pressed', async () => {
    const mockOnClose = jest.fn();
    const { getByTestId } = render(
      <LocationEnrichmentCard location={mockLocation} onClose={mockOnClose} />
    );
    
    await waitFor(() => {
      const closeButton = getByTestId('header-close-button');
      fireEvent.press(closeButton);
    });
    
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('displays place rating and distance', async () => {
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      expect(getByText('4.8')).toBeTruthy();
      expect(getByText('5.0 km')).toBeTruthy();
    });
  });

  it('displays place tags', async () => {
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      expect(getByText('landmark')).toBeTruthy();
      expect(getByText('bridge')).toBeTruthy();
      expect(getByText('scenic')).toBeTruthy();
    });
  });

  it('renders place action buttons in modal', async () => {
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      fireEvent.press(getByText('Golden Gate Bridge'));
    });
    
    await waitFor(() => {
      expect(getByText('Directions')).toBeTruthy();
      expect(getByText('More Info')).toBeTruthy();
    });
  });

  it('displays review count in modal', async () => {
    const { getByText } = render(<LocationEnrichmentCard location={mockLocation} />);
    
    await waitFor(() => {
      fireEvent.press(getByText('Golden Gate Bridge'));
    });
    
    await waitFor(() => {
      expect(getByText('4.8 (10000)')).toBeTruthy();
    });
  });
});