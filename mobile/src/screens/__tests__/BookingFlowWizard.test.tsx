import React from 'react';
import { render, fireEvent, waitFor, screen } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import { Provider } from 'react-redux';
import BookingFlowWizard from '../BookingFlowWizard';
import { mockStore } from '../../test-utils/mockStore';
import { mockNavigation } from '../../test-utils/mockNavigation';
import * as bookingService from '@services/bookingService';
import * as paymentService from '@services/paymentService';

// Mock services
jest.mock('@services/bookingService');
jest.mock('@services/paymentService');
jest.mock('@react-native-async-storage/async-storage');

describe('BookingFlowWizard', () => {
  let store: any;
  let navigation: any;

  const mockBookingData = {
    type: 'hotel',
    location: 'New York, NY',
    checkIn: '2024-12-25',
    checkOut: '2024-12-28',
    guests: 2,
    rooms: 1,
  };

  const mockHotelOptions = [
    {
      id: 'hotel-1',
      name: 'Grand Hotel NYC',
      price: 250,
      rating: 4.5,
      amenities: ['WiFi', 'Parking', 'Pool'],
      image: 'https://example.com/hotel1.jpg',
    },
    {
      id: 'hotel-2',
      name: 'Budget Inn Manhattan',
      price: 120,
      rating: 3.8,
      amenities: ['WiFi', 'Breakfast'],
      image: 'https://example.com/hotel2.jpg',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    
    store = mockStore({
      user: { 
        isAuthenticated: true,
        profile: {
          id: 'user-123',
          name: 'Test User',
          email: 'test@example.com',
        }
      },
      booking: {
        currentBooking: null,
        isLoading: false,
      },
    });
    
    navigation = mockNavigation();
    
    // Setup default mocks
    (bookingService.searchHotels as jest.Mock).mockResolvedValue(mockHotelOptions);
    (bookingService.createBooking as jest.Mock).mockResolvedValue({
      id: 'booking-123',
      confirmationNumber: 'CONF123',
    });
    (paymentService.processPayment as jest.Mock).mockResolvedValue({
      success: true,
      transactionId: 'trans-123',
    });
  });

  const renderWizard = (initialStep = 0) => {
    return render(
      <Provider store={store}>
        <NavigationContainer>
          <BookingFlowWizard
            navigation={navigation}
            route={{
              params: {
                bookingType: 'hotel',
                initialStep,
                bookingData: mockBookingData,
              },
            }}
          />
        </NavigationContainer>
      </Provider>
    );
  };

  describe('Step Navigation', () => {
    it('should render the first step by default', () => {
      const { getByText } = renderWizard();
      
      expect(getByText('Search Hotels')).toBeTruthy();
      expect(getByText('Step 1 of 4')).toBeTruthy();
    });

    it('should navigate to next step', async () => {
      const { getByText, getByTestId } = renderWizard();
      
      // Fill search form
      const searchButton = getByTestId('search-button');
      fireEvent.press(searchButton);
      
      await waitFor(() => {
        expect(getByText('Select Hotel')).toBeTruthy();
        expect(getByText('Step 2 of 4')).toBeTruthy();
      });
    });

    it('should navigate to previous step', async () => {
      const { getByText, getByTestId } = renderWizard(1);
      
      const backButton = getByTestId('back-button');
      fireEvent.press(backButton);
      
      await waitFor(() => {
        expect(getByText('Search Hotels')).toBeTruthy();
        expect(getByText('Step 1 of 4')).toBeTruthy();
      });
    });

    it('should disable back button on first step', () => {
      const { getByTestId } = renderWizard(0);
      
      const backButton = getByTestId('back-button');
      expect(backButton.props.disabled).toBe(true);
    });
  });

  describe('Search Step', () => {
    it('should validate search form', async () => {
      const { getByText, getByTestId } = renderWizard();
      
      // Try to search without filling required fields
      const searchButton = getByTestId('search-button');
      fireEvent.press(searchButton);
      
      await waitFor(() => {
        expect(getByText('Location is required')).toBeTruthy();
      });
    });

    it('should search for hotels with valid data', async () => {
      const { getByTestId, getByPlaceholderText } = renderWizard();
      
      // Fill search form
      fireEvent.changeText(getByPlaceholderText('Enter city or address'), 'New York');
      fireEvent.changeText(getByTestId('check-in-date'), '2024-12-25');
      fireEvent.changeText(getByTestId('check-out-date'), '2024-12-28');
      
      const searchButton = getByTestId('search-button');
      fireEvent.press(searchButton);
      
      await waitFor(() => {
        expect(bookingService.searchHotels).toHaveBeenCalledWith({
          location: 'New York',
          checkIn: '2024-12-25',
          checkOut: '2024-12-28',
          guests: 2,
          rooms: 1,
        });
      });
    });

    it('should handle search errors', async () => {
      (bookingService.searchHotels as jest.Mock).mockRejectedValue(
        new Error('Search failed')
      );
      
      const { getByTestId, getByText } = renderWizard();
      
      const searchButton = getByTestId('search-button');
      fireEvent.press(searchButton);
      
      await waitFor(() => {
        expect(getByText('Failed to search hotels. Please try again.')).toBeTruthy();
      });
    });
  });

  describe('Selection Step', () => {
    it('should display search results', async () => {
      const { getByText } = renderWizard(1);
      
      await waitFor(() => {
        expect(getByText('Grand Hotel NYC')).toBeTruthy();
        expect(getByText('$250')).toBeTruthy();
        expect(getByText('Budget Inn Manhattan')).toBeTruthy();
        expect(getByText('$120')).toBeTruthy();
      });
    });

    it('should filter results', async () => {
      const { getByTestId, queryByText } = renderWizard(1);
      
      // Apply price filter
      const maxPriceSlider = getByTestId('max-price-slider');
      fireEvent(maxPriceSlider, 'valueChange', 150);
      
      await waitFor(() => {
        expect(queryByText('Grand Hotel NYC')).toBeNull();
        expect(queryByText('Budget Inn Manhattan')).toBeTruthy();
      });
    });

    it('should sort results', async () => {
      const { getByTestId, getAllByTestId } = renderWizard(1);
      
      const sortButton = getByTestId('sort-button');
      fireEvent.press(sortButton);
      
      const priceLowToHigh = getByTestId('sort-price-low-high');
      fireEvent.press(priceLowToHigh);
      
      await waitFor(() => {
        const hotelCards = getAllByTestId('hotel-card');
        expect(hotelCards[0]).toHaveTextContent('Budget Inn Manhattan');
        expect(hotelCards[1]).toHaveTextContent('Grand Hotel NYC');
      });
    });

    it('should select a hotel', async () => {
      const { getByText, getByTestId } = renderWizard(1);
      
      await waitFor(() => {
        const selectButton = getByTestId('select-hotel-1');
        fireEvent.press(selectButton);
      });
      
      await waitFor(() => {
        expect(getByText('Guest Details')).toBeTruthy();
        expect(getByText('Step 3 of 4')).toBeTruthy();
      });
    });
  });

  describe('Guest Details Step', () => {
    it('should pre-fill user details', async () => {
      const { getByDisplayValue } = renderWizard(2);
      
      await waitFor(() => {
        expect(getByDisplayValue('Test User')).toBeTruthy();
        expect(getByDisplayValue('test@example.com')).toBeTruthy();
      });
    });

    it('should validate guest details', async () => {
      const { getByText, getByTestId, getByPlaceholderText } = renderWizard(2);
      
      // Clear required field
      fireEvent.changeText(getByPlaceholderText('Phone number'), '');
      
      const continueButton = getByTestId('continue-button');
      fireEvent.press(continueButton);
      
      await waitFor(() => {
        expect(getByText('Phone number is required')).toBeTruthy();
      });
    });

    it('should add special requests', async () => {
      const { getByTestId, getByPlaceholderText } = renderWizard(2);
      
      const specialRequests = getByPlaceholderText('Any special requests?');
      fireEvent.changeText(specialRequests, 'Late check-in please');
      
      const continueButton = getByTestId('continue-button');
      fireEvent.press(continueButton);
      
      await waitFor(() => {
        expect(getByTestId('review-special-requests')).toHaveTextContent('Late check-in please');
      });
    });
  });

  describe('Payment Step', () => {
    it('should display booking summary', async () => {
      const { getByText, getByTestId } = renderWizard(3);
      
      await waitFor(() => {
        expect(getByText('Booking Summary')).toBeTruthy();
        expect(getByText('Grand Hotel NYC')).toBeTruthy();
        expect(getByText('3 nights')).toBeTruthy();
        expect(getByText('Total: $750')).toBeTruthy();
      });
    });

    it('should validate payment details', async () => {
      const { getByText, getByTestId } = renderWizard(3);
      
      const payButton = getByTestId('pay-button');
      fireEvent.press(payButton);
      
      await waitFor(() => {
        expect(getByText('Card number is required')).toBeTruthy();
      });
    });

    it('should process payment successfully', async () => {
      const { getByTestId, getByPlaceholderText } = renderWizard(3);
      
      // Fill payment details
      fireEvent.changeText(getByPlaceholderText('Card number'), '4242424242424242');
      fireEvent.changeText(getByPlaceholderText('MM/YY'), '12/25');
      fireEvent.changeText(getByPlaceholderText('CVV'), '123');
      fireEvent.changeText(getByPlaceholderText('Name on card'), 'Test User');
      
      const payButton = getByTestId('pay-button');
      fireEvent.press(payButton);
      
      await waitFor(() => {
        expect(paymentService.processPayment).toHaveBeenCalled();
        expect(bookingService.createBooking).toHaveBeenCalled();
      });
    });

    it('should handle payment errors', async () => {
      (paymentService.processPayment as jest.Mock).mockRejectedValue(
        new Error('Payment declined')
      );
      
      const { getByTestId, getByText, getByPlaceholderText } = renderWizard(3);
      
      // Fill payment details
      fireEvent.changeText(getByPlaceholderText('Card number'), '4000000000000002');
      
      const payButton = getByTestId('pay-button');
      fireEvent.press(payButton);
      
      await waitFor(() => {
        expect(getByText('Payment declined. Please try another card.')).toBeTruthy();
      });
    });

    it('should show confirmation after successful booking', async () => {
      const { getByTestId, getByText, getByPlaceholderText } = renderWizard(3);
      
      // Fill and submit payment
      fireEvent.changeText(getByPlaceholderText('Card number'), '4242424242424242');
      fireEvent.changeText(getByPlaceholderText('MM/YY'), '12/25');
      fireEvent.changeText(getByPlaceholderText('CVV'), '123');
      
      const payButton = getByTestId('pay-button');
      fireEvent.press(payButton);
      
      await waitFor(() => {
        expect(getByText('Booking Confirmed!')).toBeTruthy();
        expect(getByText('Confirmation #CONF123')).toBeTruthy();
      });
    });
  });

  describe('Offline Support', () => {
    it('should save draft booking offline', async () => {
      const { getByTestId } = renderWizard();
      
      // Simulate offline
      (bookingService.searchHotels as jest.Mock).mockRejectedValue(
        new Error('Network error')
      );
      
      const saveButton = getByTestId('save-draft-button');
      fireEvent.press(saveButton);
      
      await waitFor(() => {
        expect(getByTestId('draft-saved-message')).toBeTruthy();
      });
    });

    it('should load saved draft', async () => {
      const savedDraft = {
        step: 2,
        data: mockBookingData,
        selectedHotel: mockHotelOptions[0],
      };
      
      const AsyncStorage = require('@react-native-async-storage/async-storage');
      AsyncStorage.getItem.mockResolvedValue(JSON.stringify(savedDraft));
      
      const { getByText } = renderWizard();
      
      await waitFor(() => {
        expect(getByText('Resume booking?')).toBeTruthy();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper accessibility labels', () => {
      const { getByLabelText } = renderWizard();
      
      expect(getByLabelText('Search location')).toBeTruthy();
      expect(getByLabelText('Check-in date')).toBeTruthy();
      expect(getByLabelText('Check-out date')).toBeTruthy();
    });

    it('should announce step changes', async () => {
      const { getByTestId } = renderWizard();
      
      const searchButton = getByTestId('search-button');
      fireEvent.press(searchButton);
      
      await waitFor(() => {
        expect(getByTestId('step-announcement')).toHaveTextContent('Step 2 of 4: Select Hotel');
      });
    });
  });

  describe('Integration', () => {
    it('should complete full booking flow', async () => {
      const { getByTestId, getByPlaceholderText, getByText } = renderWizard();
      
      // Step 1: Search
      fireEvent.changeText(getByPlaceholderText('Enter city or address'), 'New York');
      fireEvent.press(getByTestId('search-button'));
      
      // Step 2: Select hotel
      await waitFor(() => {
        fireEvent.press(getByTestId('select-hotel-1'));
      });
      
      // Step 3: Guest details
      await waitFor(() => {
        fireEvent.changeText(getByPlaceholderText('Phone number'), '555-1234');
        fireEvent.press(getByTestId('continue-button'));
      });
      
      // Step 4: Payment
      await waitFor(() => {
        fireEvent.changeText(getByPlaceholderText('Card number'), '4242424242424242');
        fireEvent.changeText(getByPlaceholderText('MM/YY'), '12/25');
        fireEvent.changeText(getByPlaceholderText('CVV'), '123');
        fireEvent.press(getByTestId('pay-button'));
      });
      
      // Confirmation
      await waitFor(() => {
        expect(getByText('Booking Confirmed!')).toBeTruthy();
        expect(navigation.navigate).toHaveBeenCalledWith('MyReservations');
      });
    });
  });
});