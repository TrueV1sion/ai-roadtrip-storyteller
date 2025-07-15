"""Tests for booking flow components."""

import React from 'react';
import { render, fireEvent, waitFor, screen } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import AsyncStorage from '@react-native-async-storage/async-storage';

import BookingFlow from '../booking/BookingFlow';
import RestaurantBooking from '../booking/RestaurantBooking';
import AttractionBooking from '../booking/AttractionBooking';
import BookingConfirmation from '../booking/BookingConfirmation';
import BookingHistory from '../booking/BookingHistory';
import { BookingService } from '../../services/bookingService';
import { AuthContext } from '../../contexts/AuthContext';

// Mock dependencies
jest.mock('../../services/bookingService');
jest.mock('@react-native-async-storage/async-storage');
jest.mock('react-native-maps', () => ({
  default: jest.fn(() => null),
  Marker: jest.fn(() => null),
}));

const mockBookingService = BookingService as jest.Mocked<typeof BookingService>;
const mockNavigation = {
  navigate: jest.fn(),
  goBack: jest.fn(),
  setOptions: jest.fn(),
};

const mockStore = configureStore({
  reducer: {
    user: (state = { preferences: {} }) => state,
    location: (state = { current: { lat: 37.7749, lng: -122.4194 } }) => state,
  },
});

const mockAuthContext = {
  user: { id: 1, email: 'test@example.com' },
  token: 'test-token',
  isAuthenticated: true,
};

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <Provider store={mockStore}>
      <AuthContext.Provider value={mockAuthContext}>
        <NavigationContainer>
          {component}
        </NavigationContainer>
      </AuthContext.Provider>
    </Provider>
  );
};

describe('BookingFlow Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders booking type selection', () => {
    const { getByText } = renderWithProviders(<BookingFlow navigation={mockNavigation} />);
    
    expect(getByText('What would you like to book?')).toBeTruthy();
    expect(getByText('Restaurant')).toBeTruthy();
    expect(getByText('Attraction')).toBeTruthy();
    expect(getByText('Hotel')).toBeTruthy();
  });

  it('navigates to restaurant booking when selected', () => {
    const { getByText } = renderWithProviders(<BookingFlow navigation={mockNavigation} />);
    
    fireEvent.press(getByText('Restaurant'));
    
    expect(mockNavigation.navigate).toHaveBeenCalledWith('RestaurantBooking', {
      bookingType: 'restaurant',
    });
  });

  it('handles voice command for booking', async () => {
    mockBookingService.parseVoiceCommand.mockResolvedValue({
      type: 'restaurant',
      details: {
        partySize: 4,
        time: '7:00 PM',
        cuisine: 'italian',
      },
    });

    const { getByTestId } = renderWithProviders(<BookingFlow navigation={mockNavigation} />);
    
    fireEvent.press(getByTestId('voice-button'));
    
    await waitFor(() => {
      expect(mockNavigation.navigate).toHaveBeenCalledWith('RestaurantBooking', {
        bookingType: 'restaurant',
        voiceDetails: {
          partySize: 4,
          time: '7:00 PM',
          cuisine: 'italian',
        },
      });
    });
  });
});

describe('RestaurantBooking Component', () => {
  const mockRoute = {
    params: {
      bookingType: 'restaurant',
      voiceDetails: {
        partySize: 4,
        time: '7:00 PM',
        cuisine: 'italian',
      },
    },
  };

  beforeEach(() => {
    mockBookingService.searchRestaurants.mockResolvedValue([
      {
        id: 'r1',
        name: 'Italian Bistro',
        cuisine: 'italian',
        rating: 4.5,
        priceRange: '$$',
        distance: '0.5 miles',
      },
      {
        id: 'r2',
        name: 'Roma Restaurant',
        cuisine: 'italian',
        rating: 4.3,
        priceRange: '$$$',
        distance: '1.2 miles',
      },
    ]);

    mockBookingService.checkAvailability.mockResolvedValue({
      available: true,
      slots: ['6:30 PM', '7:00 PM', '7:30 PM'],
    });
  });

  it('pre-fills form with voice details', () => {
    const { getByDisplayValue } = renderWithProviders(
      <RestaurantBooking navigation={mockNavigation} route={mockRoute} />
    );
    
    expect(getByDisplayValue('4')).toBeTruthy();
    expect(getByDisplayValue('7:00 PM')).toBeTruthy();
  });

  it('searches for restaurants based on criteria', async () => {
    const { getByText, getByTestId } = renderWithProviders(
      <RestaurantBooking navigation={mockNavigation} route={mockRoute} />
    );
    
    fireEvent.press(getByTestId('search-button'));
    
    await waitFor(() => {
      expect(mockBookingService.searchRestaurants).toHaveBeenCalledWith({
        location: { lat: 37.7749, lng: -122.4194 },
        cuisine: 'italian',
        partySize: 4,
        time: '7:00 PM',
      });
    });
    
    expect(getByText('Italian Bistro')).toBeTruthy();
    expect(getByText('Roma Restaurant')).toBeTruthy();
  });

  it('checks availability when restaurant selected', async () => {
    const { getByText, getByTestId } = renderWithProviders(
      <RestaurantBooking navigation={mockNavigation} route={mockRoute} />
    );
    
    fireEvent.press(getByTestId('search-button'));
    
    await waitFor(() => {
      expect(getByText('Italian Bistro')).toBeTruthy();
    });
    
    fireEvent.press(getByText('Italian Bistro'));
    
    await waitFor(() => {
      expect(mockBookingService.checkAvailability).toHaveBeenCalledWith({
        restaurantId: 'r1',
        date: expect.any(String),
        time: '7:00 PM',
        partySize: 4,
      });
    });
    
    expect(getByText('Available times:')).toBeTruthy();
    expect(getByText('6:30 PM')).toBeTruthy();
    expect(getByText('7:30 PM')).toBeTruthy();
  });

  it('creates booking when confirmed', async () => {
    mockBookingService.createBooking.mockResolvedValue({
      bookingId: 'B123',
      confirmationCode: 'CONF123',
      status: 'confirmed',
      details: {
        restaurant: 'Italian Bistro',
        time: '7:00 PM',
        partySize: 4,
      },
      commission: 15.00,
    });

    const { getByText, getByTestId } = renderWithProviders(
      <RestaurantBooking navigation={mockNavigation} route={mockRoute} />
    );
    
    // Search and select restaurant
    fireEvent.press(getByTestId('search-button'));
    await waitFor(() => expect(getByText('Italian Bistro')).toBeTruthy());
    fireEvent.press(getByText('Italian Bistro'));
    
    // Confirm booking
    await waitFor(() => expect(getByText('Confirm Booking')).toBeTruthy());
    fireEvent.press(getByText('Confirm Booking'));
    
    await waitFor(() => {
      expect(mockBookingService.createBooking).toHaveBeenCalledWith({
        type: 'restaurant',
        restaurantId: 'r1',
        date: expect.any(String),
        time: '7:00 PM',
        partySize: 4,
        specialRequests: '',
      });
    });
    
    expect(mockNavigation.navigate).toHaveBeenCalledWith('BookingConfirmation', {
      booking: expect.objectContaining({
        bookingId: 'B123',
        confirmationCode: 'CONF123',
      }),
    });
  });

  it('handles booking errors gracefully', async () => {
    mockBookingService.createBooking.mockRejectedValue(new Error('Booking failed'));

    const { getByText, getByTestId } = renderWithProviders(
      <RestaurantBooking navigation={mockNavigation} route={mockRoute} />
    );
    
    // Search and select restaurant
    fireEvent.press(getByTestId('search-button'));
    await waitFor(() => expect(getByText('Italian Bistro')).toBeTruthy());
    fireEvent.press(getByText('Italian Bistro'));
    
    // Try to confirm booking
    await waitFor(() => expect(getByText('Confirm Booking')).toBeTruthy());
    fireEvent.press(getByText('Confirm Booking'));
    
    await waitFor(() => {
      expect(getByText('Booking failed. Please try again.')).toBeTruthy();
    });
  });
});

describe('BookingConfirmation Component', () => {
  const mockBooking = {
    bookingId: 'B123',
    confirmationCode: 'CONF123',
    status: 'confirmed',
    type: 'restaurant',
    details: {
      restaurant: 'Italian Bistro',
      date: '2024-01-20',
      time: '7:00 PM',
      partySize: 4,
      address: '123 Main St, San Francisco, CA',
    },
    commission: 15.00,
  };

  const mockRoute = {
    params: { booking: mockBooking },
  };

  it('displays booking confirmation details', () => {
    const { getByText } = renderWithProviders(
      <BookingConfirmation navigation={mockNavigation} route={mockRoute} />
    );
    
    expect(getByText('Booking Confirmed!')).toBeTruthy();
    expect(getByText('CONF123')).toBeTruthy();
    expect(getByText('Italian Bistro')).toBeTruthy();
    expect(getByText('January 20, 2024')).toBeTruthy();
    expect(getByText('7:00 PM')).toBeTruthy();
    expect(getByText('Party of 4')).toBeTruthy();
  });

  it('allows adding to calendar', async () => {
    const { getByText } = renderWithProviders(
      <BookingConfirmation navigation={mockNavigation} route={mockRoute} />
    );
    
    fireEvent.press(getByText('Add to Calendar'));
    
    // Would test calendar integration here
    await waitFor(() => {
      expect(AsyncStorage.setItem).toHaveBeenCalled();
    });
  });

  it('allows modifying booking', () => {
    const { getByText } = renderWithProviders(
      <BookingConfirmation navigation={mockNavigation} route={mockRoute} />
    );
    
    fireEvent.press(getByText('Modify Booking'));
    
    expect(mockNavigation.navigate).toHaveBeenCalledWith('ModifyBooking', {
      booking: mockBooking,
    });
  });

  it('allows cancelling booking', async () => {
    mockBookingService.cancelBooking.mockResolvedValue({
      success: true,
      refundAmount: 0,
      cancellationFee: 0,
    });

    const { getByText } = renderWithProviders(
      <BookingConfirmation navigation={mockNavigation} route={mockRoute} />
    );
    
    fireEvent.press(getByText('Cancel Booking'));
    
    // Confirm cancellation
    await waitFor(() => expect(getByText('Confirm Cancellation')).toBeTruthy());
    fireEvent.press(getByText('Confirm Cancellation'));
    
    await waitFor(() => {
      expect(mockBookingService.cancelBooking).toHaveBeenCalledWith('B123');
      expect(mockNavigation.goBack).toHaveBeenCalled();
    });
  });
});

describe('BookingHistory Component', () => {
  const mockBookings = [
    {
      bookingId: 'B1',
      type: 'restaurant',
      status: 'confirmed',
      date: '2024-01-20',
      details: { restaurant: 'Italian Bistro' },
    },
    {
      bookingId: 'B2',
      type: 'attraction',
      status: 'completed',
      date: '2024-01-15',
      details: { attraction: 'City Museum' },
    },
    {
      bookingId: 'B3',
      type: 'hotel',
      status: 'cancelled',
      date: '2024-01-10',
      details: { hotel: 'Grand Hotel' },
    },
  ];

  beforeEach(() => {
    mockBookingService.getUserBookings.mockResolvedValue(mockBookings);
  });

  it('displays user booking history', async () => {
    const { getByText } = renderWithProviders(
      <BookingHistory navigation={mockNavigation} />
    );
    
    await waitFor(() => {
      expect(getByText('Italian Bistro')).toBeTruthy();
      expect(getByText('City Museum')).toBeTruthy();
      expect(getByText('Grand Hotel')).toBeTruthy();
    });
  });

  it('filters bookings by status', async () => {
    const { getByText, queryByText } = renderWithProviders(
      <BookingHistory navigation={mockNavigation} />
    );
    
    await waitFor(() => expect(getByText('Italian Bistro')).toBeTruthy());
    
    // Filter to show only completed
    fireEvent.press(getByText('Completed'));
    
    await waitFor(() => {
      expect(queryByText('Italian Bistro')).toBeNull();
      expect(getByText('City Museum')).toBeTruthy();
      expect(queryByText('Grand Hotel')).toBeNull();
    });
  });

  it('allows rebooking from history', async () => {
    const { getByText, getAllByTestId } = renderWithProviders(
      <BookingHistory navigation={mockNavigation} />
    );
    
    await waitFor(() => expect(getByText('Italian Bistro')).toBeTruthy());
    
    const rebookButtons = getAllByTestId('rebook-button');
    fireEvent.press(rebookButtons[0]);
    
    expect(mockNavigation.navigate).toHaveBeenCalledWith('RestaurantBooking', {
      rebookDetails: expect.objectContaining({
        restaurant: 'Italian Bistro',
      }),
    });
  });

  it('shows booking analytics', async () => {
    mockBookingService.getUserAnalytics.mockResolvedValue({
      totalBookings: 25,
      totalSpent: 1500.00,
      totalSaved: 150.00,
      favoriteType: 'restaurant',
    });

    const { getByText } = renderWithProviders(
      <BookingHistory navigation={mockNavigation} />
    );
    
    await waitFor(() => {
      expect(getByText('Total Bookings: 25')).toBeTruthy();
      expect(getByText('Total Spent: $1,500.00')).toBeTruthy();
      expect(getByText('Total Saved: $150.00')).toBeTruthy();
    });
  });
});