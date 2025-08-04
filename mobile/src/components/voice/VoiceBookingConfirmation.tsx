import React, { useState, useEffect } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import Voice from '@react-native-voice/voice';
import { SafeArea } from '../SafeArea';
import { voiceService } from '../../services/voice/voiceService';
import { api } from '../../services/api/ApiClient';

interface BookingData {
  type: 'restaurant' | 'attraction' | 'hotel';
  venue: string;
  date?: string;
  time?: string;
  partySize?: number;
  duration?: number;
}

interface VoiceBookingConfirmationProps {
  bookingData: BookingData;
  onConfirm?: (booking: any) => void;
  onCancel?: () => void;
  isDriving?: boolean;
}

export const VoiceBookingConfirmation: React.FC<VoiceBookingConfirmationProps> = ({
  bookingData,
  onConfirm,
  onCancel,
  isDriving = false,
}) => {
  const [currentStep, setCurrentStep] = useState<'review' | 'confirm' | 'complete'>('review');
  const [isListening, setIsListening] = useState(false);
  const [bookingDetails, setBookingDetails] = useState(bookingData);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Start voice guidance immediately
    provideVoiceGuidance();
    
    // Setup voice recognition
    Voice.onSpeechResults = onSpeechResults;
    Voice.onSpeechError = onSpeechError;
    
    return () => {
      Voice.destroy().then(Voice.removeAllListeners);
    };
  }, [currentStep]);

  const provideVoiceGuidance = async () => {
    let message = '';
    
    switch (currentStep) {
      case 'review':
        message = `I found ${bookingDetails.venue}. `;
        if (bookingDetails.type === 'restaurant') {
          message += `Would you like to book a table for ${bookingDetails.partySize || 2} people `;
          message += `on ${bookingDetails.date || 'today'} at ${bookingDetails.time || 'the next available time'}? `;
        } else if (bookingDetails.type === 'attraction') {
          message += `Would you like to book tickets for ${bookingDetails.date || 'today'}? `;
        }
        message += 'Say "confirm" to proceed or "change" to modify.';
        break;
        
      case 'confirm':
        message = 'Processing your booking. One moment please.';
        break;
        
      case 'complete':
        message = 'Your booking is confirmed! I\'ll send the details to your phone.';
        break;
    }
    
    await voiceService.speak(message);
    
    // Start listening after speaking (except when processing)
    if (currentStep !== 'confirm') {
      setTimeout(() => startListening(), 500);
    }
  };

  const startListening = async () => {
    try {
      setIsListening(true);
      await Voice.start('en-US');
    } catch (error) {
      logger.error('Error starting voice recognition:', error);
      setIsListening(false);
    }
  };

  const stopListening = async () => {
    try {
      setIsListening(false);
      await Voice.stop();
    } catch (error) {
      logger.error('Error stopping voice recognition:', error);
    }
  };

  const onSpeechResults = async (e: any) => {
    if (e.value && e.value[0]) {
      const command = e.value[0].toLowerCase();
      await handleVoiceCommand(command);
    }
  };

  const onSpeechError = (e: any) => {
    logger.error('Speech recognition error:', e);
    setIsListening(false);
  };

  const handleVoiceCommand = async (command: string) => {
    stopListening();
    
    if (currentStep === 'review') {
      if (command.includes('confirm') || command.includes('yes') || command.includes('book')) {
        await confirmBooking();
      } else if (command.includes('change') || command.includes('modify')) {
        await handleModification(command);
      } else if (command.includes('cancel') || command.includes('no')) {
        await cancelBooking();
      } else {
        await voiceService.speak('I didn\'t understand. Please say "confirm" or "change".');
        setTimeout(() => startListening(), 500);
      }
    }
  };

  const handleModification = async (command: string) => {
    // Extract modification details from voice command
    if (command.includes('time')) {
      await voiceService.speak('What time would you prefer?');
      // Listen for time modification
    } else if (command.includes('date')) {
      await voiceService.speak('What date would you like?');
      // Listen for date modification
    } else if (command.includes('people') || command.includes('party')) {
      await voiceService.speak('How many people?');
      // Listen for party size modification
    }
    
    setTimeout(() => startListening(), 500);
  };

  const confirmBooking = async () => {
    setCurrentStep('confirm');
    setIsProcessing(true);
    
    try {
      // Make booking API call
      const response = await api.post('/api/reservations', bookingDetails);
      
      if (response.data.success) {
        setCurrentStep('complete');
        if (onConfirm) {
          onConfirm(response.data.booking);
        }
      } else {
        throw new Error(response.data.message || 'Booking failed');
      }
    } catch (error) {
      setError('Sorry, I couldn\'t complete the booking. Would you like to try again?');
      await voiceService.speak('Sorry, I couldn\'t complete the booking. Would you like to try again?');
      setCurrentStep('review');
    } finally {
      setIsProcessing(false);
    }
  };

  const cancelBooking = async () => {
    await voiceService.speak('Booking cancelled.');
    if (onCancel) {
      onCancel();
    }
  };

  const renderBookingDetails = () => {
    const details = [];
    
    if (bookingDetails.type === 'restaurant') {
      details.push(`Party size: ${bookingDetails.partySize || 2} people`);
    }
    
    if (bookingDetails.date) {
      details.push(`Date: ${bookingDetails.date}`);
    }
    
    if (bookingDetails.time) {
      details.push(`Time: ${bookingDetails.time}`);
    }
    
    return details;
  };

  return (
    <SafeArea>
      <View style={[styles.container, isDriving && styles.drivingContainer]}>
        <ScrollView 
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* Booking venue */}
          <Text style={[styles.venueName, isDriving && styles.drivingText]}>
            {bookingDetails.venue}
          </Text>
          
          {/* Booking type */}
          <Text style={[styles.bookingType, isDriving && styles.drivingSubtext]}>
            {bookingDetails.type.charAt(0).toUpperCase() + bookingDetails.type.slice(1)} Booking
          </Text>
          
          {/* Booking details */}
          {currentStep === 'review' && (
            <View style={styles.detailsContainer}>
              {renderBookingDetails().map((detail, index) => (
                <Text key={index} style={[styles.detailText, isDriving && styles.drivingDetailText]}>
                  {detail}
                </Text>
              ))}
            </View>
          )}
          
          {/* Status indicator */}
          {currentStep === 'confirm' && isProcessing && (
            <View style={styles.processingContainer}>
              <ActivityIndicator size="large" color={isDriving ? '#FFF' : '#007AFF'} />
              <Text style={[styles.processingText, isDriving && styles.drivingText]}>
                Processing your booking...
              </Text>
            </View>
          )}
          
          {/* Completion message */}
          {currentStep === 'complete' && (
            <View style={styles.completeContainer}>
              <Text style={styles.completeIcon}>✓</Text>
              <Text style={[styles.completeText, isDriving && styles.drivingText]}>
                Booking Confirmed!
              </Text>
            </View>
          )}
          
          {/* Error message */}
          {error && (
            <View style={styles.errorContainer}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}
          
          {/* Voice indicator */}
          <View style={styles.voiceIndicator}>
            <View style={[styles.voiceIcon, isListening && styles.voiceIconActive]} />
            <Text style={[styles.voiceText, isDriving && styles.drivingSubtext]}>
              {isListening ? 'Listening...' : 'Voice control active'}
            </Text>
          </View>
        </ScrollView>
        
        {/* Manual controls for safety */}
        {!isDriving && currentStep === 'review' && (
          <View style={styles.buttonContainer}>
            <TouchableOpacity
              style={[styles.button, styles.confirmButton]}
              onPress={confirmBooking}
              disabled={isProcessing}
            >
              <Text style={styles.buttonText}>Confirm Booking</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={[styles.button, styles.cancelButton]}
              onPress={cancelBooking}
              disabled={isProcessing}
            >
              <Text style={styles.buttonText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </SafeArea>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  drivingContainer: {
    backgroundColor: '#000',
  },
  scrollContent: {
    flexGrow: 1,
    padding: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  venueName: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 10,
    color: '#333',
  },
  bookingType: {
    fontSize: 18,
    color: '#666',
    marginBottom: 30,
  },
  drivingText: {
    color: '#FFF',
    fontSize: 36,
  },
  drivingSubtext: {
    color: '#CCC',
    fontSize: 24,
  },
  detailsContainer: {
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
    padding: 20,
    borderRadius: 10,
    marginBottom: 30,
    minWidth: 300,
  },
  detailText: {
    fontSize: 16,
    marginBottom: 10,
    color: '#333',
  },
  drivingDetailText: {
    color: '#FFF',
    fontSize: 20,
  },
  processingContainer: {
    alignItems: 'center',
    marginVertical: 40,
  },
  processingText: {
    marginTop: 20,
    fontSize: 18,
    color: '#666',
  },
  completeContainer: {
    alignItems: 'center',
    marginVertical: 40,
  },
  completeIcon: {
    fontSize: 72,
    color: '#4CAF50',
    marginBottom: 20,
  },
  completeText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  errorContainer: {
    backgroundColor: '#FFEBEE',
    padding: 15,
    borderRadius: 10,
    marginVertical: 20,
  },
  errorText: {
    color: '#F44336',
    fontSize: 16,
    textAlign: 'center',
  },
  voiceIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 30,
  },
  voiceIcon: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#999',
    marginRight: 10,
  },
  voiceIconActive: {
    backgroundColor: '#4CAF50',
  },
  voiceText: {
    fontSize: 14,
    color: '#666',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 20,
    paddingBottom: 20,
  },
  button: {
    flex: 1,
    paddingVertical: 15,
    borderRadius: 10,
    marginHorizontal: 10,
  },
  confirmButton: {
    backgroundColor: '#007AFF',
  },
  cancelButton: {
    backgroundColor: '#999',
  },
  buttonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
});