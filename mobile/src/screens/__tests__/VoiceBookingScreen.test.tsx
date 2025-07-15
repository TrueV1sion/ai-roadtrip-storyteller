import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { VoiceBookingScreen } from '../VoiceBookingScreen';
import { voiceCommandService } from '../../services/voiceCommandService';
import { apiManager } from '../../services/api/apiManager';
import { Alert } from 'react-native';

// Mock navigation
const mockNavigation = {
  navigate: jest.fn(),
  goBack: jest.fn(),
};

// Mock route
const mockRoute = {
  params: {
    bookingType: 'restaurant',
    venueId: '123',
    venueName: 'Test Restaurant',
  },
};

// Mock dependencies
jest.mock('../../services/voiceCommandService');
jest.mock('../../services/api/apiManager');
jest.mock('react-native/Libraries/Alert/Alert', () => ({
  alert: jest.fn(),
}));

describe('VoiceBookingScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly with booking details', () => {
    const { getByText, getByTestId } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    expect(getByText('Voice Booking')).toBeTruthy();
    expect(getByText('Test Restaurant')).toBeTruthy();
    expect(getByTestId('voice-button')).toBeTruthy();
  });

  it('starts voice recording when button pressed', async () => {
    (voiceCommandService.startListening as jest.Mock).mockResolvedValue(true);

    const { getByTestId } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    const voiceButton = getByTestId('voice-button');
    fireEvent.press(voiceButton);

    await waitFor(() => {
      expect(voiceCommandService.startListening).toHaveBeenCalled();
      expect(getByTestId('listening-indicator')).toBeTruthy();
    });
  });

  it('processes voice command for date and time', async () => {
    const mockTranscript = 'Tomorrow at 7 PM for 4 people';
    (voiceCommandService.getTranscript as jest.Mock).mockReturnValue(mockTranscript);

    const { getByTestId, getByText } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    // Start listening
    const voiceButton = getByTestId('voice-button');
    fireEvent.press(voiceButton);

    // Stop listening and process
    await waitFor(() => {
      fireEvent.press(voiceButton);
    });

    await waitFor(() => {
      expect(getByText(/Tomorrow/)).toBeTruthy();
      expect(getByText(/7:00 PM/)).toBeTruthy();
      expect(getByText(/4 people/)).toBeTruthy();
    });
  });

  it('handles booking confirmation', async () => {
    (apiManager.post as jest.Mock).mockResolvedValue({
      data: {
        booking_id: 'BOOK123',
        status: 'confirmed',
        confirmation_number: 'CONF123',
      },
    });

    const { getByTestId, getByText, queryByTestId } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    // Set booking details
    fireEvent.press(getByTestId('date-selector'));
    fireEvent.press(getByText('Tomorrow'));
    
    fireEvent.press(getByTestId('time-selector'));
    fireEvent.press(getByText('7:00 PM'));
    
    fireEvent.press(getByTestId('party-size-selector'));
    fireEvent.press(getByText('4'));

    // Confirm booking
    const confirmButton = getByTestId('confirm-booking-button');
    fireEvent.press(confirmButton);

    await waitFor(() => {
      expect(apiManager.post).toHaveBeenCalledWith(
        '/bookings/create',
        expect.objectContaining({
          venue_id: '123',
          booking_type: 'restaurant',
        })
      );
    });

    // Should show confirmation
    await waitFor(() => {
      expect(getByText('Booking Confirmed!')).toBeTruthy();
      expect(getByText('CONF123')).toBeTruthy();
    });
  });

  it('shows voice command suggestions', () => {
    const { getByText } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    expect(getByText('Try saying:')).toBeTruthy();
    expect(getByText('"Tomorrow at 7 PM for 2 people"')).toBeTruthy();
    expect(getByText('"Next Friday at noon for 4"')).toBeTruthy();
  });

  it('handles voice recognition errors', async () => {
    (voiceCommandService.startListening as jest.Mock).mockRejectedValue(
      new Error('Microphone permission denied')
    );

    const { getByTestId } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    const voiceButton = getByTestId('voice-button');
    fireEvent.press(voiceButton);

    await waitFor(() => {
      expect(Alert.alert).toHaveBeenCalledWith(
        'Voice Error',
        'Microphone permission denied'
      );
    });
  });

  it('validates booking details before confirmation', async () => {
    const { getByTestId } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    // Try to confirm without setting details
    const confirmButton = getByTestId('confirm-booking-button');
    fireEvent.press(confirmButton);

    await waitFor(() => {
      expect(Alert.alert).toHaveBeenCalledWith(
        'Missing Information',
        'Please select date, time, and party size'
      );
    });

    expect(apiManager.post).not.toHaveBeenCalled();
  });

  it('handles special requests via voice', async () => {
    const mockTranscript = 'Add a note: window table please';
    (voiceCommandService.getTranscript as jest.Mock).mockReturnValue(mockTranscript);

    const { getByTestId, getByText } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    // Start voice for special request
    fireEvent.press(getByTestId('special-request-voice-button'));

    await waitFor(() => {
      fireEvent.press(getByTestId('special-request-voice-button'));
    });

    await waitFor(() => {
      expect(getByText('Window table please')).toBeTruthy();
    });
  });

  it('navigates back when cancel pressed', () => {
    const { getByTestId } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    const cancelButton = getByTestId('cancel-button');
    fireEvent.press(cancelButton);

    expect(mockNavigation.goBack).toHaveBeenCalled();
  });

  it('handles booking API errors', async () => {
    (apiManager.post as jest.Mock).mockRejectedValue(
      new Error('No availability')
    );

    const { getByTestId, getByText } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    // Set required details
    fireEvent.press(getByTestId('date-selector'));
    fireEvent.press(getByText('Tomorrow'));
    
    fireEvent.press(getByTestId('time-selector'));
    fireEvent.press(getByText('7:00 PM'));
    
    fireEvent.press(getByTestId('party-size-selector'));
    fireEvent.press(getByText('4'));

    // Try to confirm
    const confirmButton = getByTestId('confirm-booking-button');
    fireEvent.press(confirmButton);

    await waitFor(() => {
      expect(Alert.alert).toHaveBeenCalledWith(
        'Booking Failed',
        'No availability'
      );
    });
  });

  it('shows loading state during booking', async () => {
    (apiManager.post as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 1000))
    );

    const { getByTestId, getByText } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    // Set required details
    fireEvent.press(getByTestId('date-selector'));
    fireEvent.press(getByText('Tomorrow'));
    
    fireEvent.press(getByTestId('time-selector'));
    fireEvent.press(getByText('7:00 PM'));
    
    fireEvent.press(getByTestId('party-size-selector'));
    fireEvent.press(getByText('4'));

    // Confirm
    const confirmButton = getByTestId('confirm-booking-button');
    fireEvent.press(confirmButton);

    // Should show loading
    expect(getByTestId('booking-loading')).toBeTruthy();
    expect(confirmButton.props.disabled).toBe(true);
  });

  it('supports different booking types', () => {
    const campgroundRoute = {
      params: {
        bookingType: 'campground',
        venueId: '456',
        venueName: 'Test Campground',
      },
    };

    const { getByText } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={campgroundRoute} />
    );

    expect(getByText('Campground Booking')).toBeTruthy();
    expect(getByText('Number of nights')).toBeTruthy();
  });

  it('handles voice command with multiple parameters', async () => {
    const mockTranscript = 'Book for tomorrow at 7:30 PM, party of 6, outdoor seating';
    (voiceCommandService.getTranscript as jest.Mock).mockReturnValue(mockTranscript);

    const { getByTestId, getByText } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    const voiceButton = getByTestId('voice-button');
    fireEvent.press(voiceButton);

    await waitFor(() => {
      fireEvent.press(voiceButton);
    });

    await waitFor(() => {
      expect(getByText(/Tomorrow/)).toBeTruthy();
      expect(getByText(/7:30 PM/)).toBeTruthy();
      expect(getByText(/6 people/)).toBeTruthy();
      expect(getByText(/Outdoor seating/)).toBeTruthy();
    });
  });

  it('provides voice feedback for confirmation', async () => {
    const mockSpeak = jest.fn();
    (voiceCommandService.speak as jest.Mock).mockImplementation(mockSpeak);

    (apiManager.post as jest.Mock).mockResolvedValue({
      data: {
        booking_id: 'BOOK123',
        status: 'confirmed',
        confirmation_number: 'CONF123',
      },
    });

    const { getByTestId, getByText } = render(
      <VoiceBookingScreen navigation={mockNavigation} route={mockRoute} />
    );

    // Set details and confirm
    fireEvent.press(getByTestId('date-selector'));
    fireEvent.press(getByText('Tomorrow'));
    
    fireEvent.press(getByTestId('time-selector'));
    fireEvent.press(getByText('7:00 PM'));
    
    fireEvent.press(getByTestId('party-size-selector'));
    fireEvent.press(getByText('4'));

    fireEvent.press(getByTestId('confirm-booking-button'));

    await waitFor(() => {
      expect(mockSpeak).toHaveBeenCalledWith(
        expect.stringContaining('Your booking has been confirmed')
      );
    });
  });
});