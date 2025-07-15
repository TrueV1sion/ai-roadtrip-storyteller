import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { NavigationContainer } from '@react-navigation/native';

import AirportAmenitiesScreen from '../AirportAmenitiesScreen';
import { AirportService } from '../../../services/api/airportApi';

// Mock dependencies
jest.mock('../../../services/api/airportApi');

const mockAirportService = AirportService as jest.Mocked<typeof AirportService>;

const mockStore = configureStore({
  reducer: {
    airport: (state = { 
      currentAirport: { code: 'SFO', name: 'San Francisco International' },
      amenities: [],
    }) => state,
    user: (state = { preferences: { lounge: 'priority_pass' } }) => state,
  },
});

const mockAmenities = [
  {
    id: '1',
    name: 'United Club',
    type: 'lounge',
    terminal: 'Terminal 3',
    gate: 'Near Gate 70',
    hours: '5:00 AM - 11:00 PM',
    access: ['United Club', 'Priority Pass'],
    amenities: ['WiFi', 'Showers', 'Bar', 'Hot Food'],
    rating: 4.5,
  },
  {
    id: '2',
    name: 'The Manufactory Food Hall',
    type: 'dining',
    terminal: 'Terminal 2',
    cuisine: ['American', 'Cafe'],
    priceRange: '$$',
    hours: '5:00 AM - 10:00 PM',
    rating: 4.2,
  },
  {
    id: '3',
    name: 'Be Relax Spa',
    type: 'spa',
    terminal: 'International Terminal',
    services: ['Massage', 'Manicure', 'Pedicure'],
    priceRange: '$$$',
    hours: '7:00 AM - 9:00 PM',
    rating: 4.7,
  },
];

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <Provider store={mockStore}>
      <NavigationContainer>
        {component}
      </NavigationContainer>
    </Provider>
  );
};

describe('AirportAmenitiesScreen Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAirportService.getAmenities.mockResolvedValue(mockAmenities);
  });

  it('renders airport name and loads amenities', async () => {
    const { getByText } = renderWithProviders(<AirportAmenitiesScreen />);
    
    expect(getByText('San Francisco International')).toBeTruthy();
    expect(getByText('Airport Amenities')).toBeTruthy();
    
    await waitFor(() => {
      expect(mockAirportService.getAmenities).toHaveBeenCalledWith('SFO');
      expect(getByText('United Club')).toBeTruthy();
      expect(getByText('The Manufactory Food Hall')).toBeTruthy();
      expect(getByText('Be Relax Spa')).toBeTruthy();
    });
  });

  it('filters amenities by type', async () => {
    const { getByText, queryByText } = renderWithProviders(<AirportAmenitiesScreen />);
    
    await waitFor(() => {
      expect(getByText('United Club')).toBeTruthy();
    });
    
    // Filter by lounges
    fireEvent.press(getByText('Lounges'));
    
    await waitFor(() => {
      expect(getByText('United Club')).toBeTruthy();
      expect(queryByText('The Manufactory Food Hall')).toBeNull();
      expect(queryByText('Be Relax Spa')).toBeNull();
    });
  });

  it('shows amenity details when tapped', async () => {
    const { getByText, getByTestId } = renderWithProviders(<AirportAmenitiesScreen />);
    
    await waitFor(() => {
      expect(getByText('United Club')).toBeTruthy();
    });
    
    fireEvent.press(getByTestId('amenity-card-1'));
    
    await waitFor(() => {
      expect(getByText('Terminal 3')).toBeTruthy();
      expect(getByText('Near Gate 70')).toBeTruthy();
      expect(getByText('5:00 AM - 11:00 PM')).toBeTruthy();
      expect(getByText('WiFi')).toBeTruthy();
      expect(getByText('Showers')).toBeTruthy();
    });
  });

  it('highlights Priority Pass eligible lounges', async () => {
    const { getByTestId } = renderWithProviders(<AirportAmenitiesScreen />);
    
    await waitFor(() => {
      const loungeCard = getByTestId('amenity-card-1');
      expect(loungeCard.props.style).toMatchObject({
        borderColor: expect.any(String),
      });
    });
  });

  it('allows searching amenities', async () => {
    const { getByPlaceholderText, getByText, queryByText } = renderWithProviders(
      <AirportAmenitiesScreen />
    );
    
    await waitFor(() => {
      expect(getByText('United Club')).toBeTruthy();
    });
    
    const searchInput = getByPlaceholderText('Search amenities...');
    fireEvent.changeText(searchInput, 'spa');
    
    await waitFor(() => {
      expect(queryByText('United Club')).toBeNull();
      expect(queryByText('The Manufactory Food Hall')).toBeNull();
      expect(getByText('Be Relax Spa')).toBeTruthy();
    });
  });

  it('sorts amenities by distance from gate', async () => {
    const amenitiesWithDistance = mockAmenities.map((a, i) => ({
      ...a,
      distance: (3 - i) * 100, // Reverse order by distance
    }));
    
    mockAirportService.getAmenities.mockResolvedValue(amenitiesWithDistance);
    
    const { getAllByTestId } = renderWithProviders(<AirportAmenitiesScreen userGate="70" />);
    
    await waitFor(() => {
      const cards = getAllByTestId(/amenity-card-/);
      expect(cards[0]).toHaveTextContent('Be Relax Spa'); // Closest
      expect(cards[2]).toHaveTextContent('United Club'); // Farthest
    });
  });

  it('shows walking time to amenities', async () => {
    const { getByText } = renderWithProviders(<AirportAmenitiesScreen userGate="70" />);
    
    await waitFor(() => {
      expect(getByText(/min walk/)).toBeTruthy();
    });
  });

  it('allows booking lounges directly', async () => {
    const { getByText, getByTestId } = renderWithProviders(<AirportAmenitiesScreen />);
    
    await waitFor(() => {
      expect(getByText('United Club')).toBeTruthy();
    });
    
    const bookButton = getByTestId('book-lounge-1');
    fireEvent.press(bookButton);
    
    await waitFor(() => {
      expect(getByText('Book Lounge Access')).toBeTruthy();
      expect(getByText('Select Access Method')).toBeTruthy();
    });
  });

  it('filters by currently open amenities', async () => {
    const { getByText, getAllByTestId } = renderWithProviders(<AirportAmenitiesScreen />);
    
    await waitFor(() => {
      expect(getByText('United Club')).toBeTruthy();
    });
    
    const openNowFilter = getByText('Open Now');
    fireEvent.press(openNowFilter);
    
    await waitFor(() => {
      const cards = getAllByTestId(/amenity-card-/);
      cards.forEach(card => {
        expect(card).not.toHaveTextContent('Closed');
      });
    });
  });

  it('shows loading state while fetching', () => {
    mockAirportService.getAmenities.mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 1000))
    );
    
    const { getByTestId } = renderWithProviders(<AirportAmenitiesScreen />);
    expect(getByTestId('loading-indicator')).toBeTruthy();
  });

  it('handles errors gracefully', async () => {
    mockAirportService.getAmenities.mockRejectedValue(new Error('Network error'));
    
    const { getByText } = renderWithProviders(<AirportAmenitiesScreen />);
    
    await waitFor(() => {
      expect(getByText('Unable to load amenities')).toBeTruthy();
      expect(getByText('Retry')).toBeTruthy();
    });
  });

  it('shows terminal map view', async () => {
    const { getByText, getByTestId } = renderWithProviders(<AirportAmenitiesScreen />);
    
    await waitFor(() => {
      expect(getByText('United Club')).toBeTruthy();
    });
    
    const mapButton = getByTestId('view-map-button');
    fireEvent.press(mapButton);
    
    await waitFor(() => {
      expect(getByTestId('terminal-map')).toBeTruthy();
      expect(getByTestId('amenity-pin-1')).toBeTruthy();
    });
  });
});