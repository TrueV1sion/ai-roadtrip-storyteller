/**
 * Booking Flow Component
 * 
 * Manages the complete booking flow with voice integration
 * Can be triggered by voice or manual selection
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Modal,
  Dimensions,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import DateTimePicker from '@react-native-community/datetimepicker';
import { format, addDays } from 'date-fns';
import apiClient from '../../services/apiClient';
import unifiedVoiceOrchestrator from '../../services/voice/unifiedVoiceOrchestrator';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface BookingFlowProps {
  visible: boolean;
  onClose: () => void;
  onComplete: (booking: any) => void;
  initialData?: {
    type: 'hotel' | 'restaurant' | 'activity';
    item?: any;
    date?: Date;
    partySize?: number;
  };
  fromVoice?: boolean;
}

interface BookingStep {
  id: string;
  title: string;
  icon: string;
}

const BOOKING_STEPS: BookingStep[] = [
  { id: 'select', title: 'Select', icon: 'search' },
  { id: 'details', title: 'Details', icon: 'edit' },
  { id: 'confirm', title: 'Confirm', icon: 'check' },
];

export const BookingFlow: React.FC<BookingFlowProps> = ({
  visible,
  onClose,
  onComplete,
  initialData,
  fromVoice = false,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [bookingType, setBookingType] = useState<'hotel' | 'restaurant' | 'activity'>(
    initialData?.type || 'restaurant'
  );
  const [selectedItem, setSelectedItem] = useState(initialData?.item || null);
  const [bookingDate, setBookingDate] = useState(initialData?.date || new Date());
  const [bookingTime, setBookingTime] = useState(new Date());
  const [partySize, setPartySize] = useState(initialData?.partySize || 2);
  const [nights, setNights] = useState(1);
  const [specialRequests, setSpecialRequests] = useState('');
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchResults, setSearchResults] = useState([]);

  useEffect(() => {
    if (visible && !initialData?.item) {
      searchNearby();
    }
  }, [visible, bookingType]);

  const searchNearby = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get(`/api/booking/search/${bookingType}`, {
        params: {
          date: format(bookingDate, 'yyyy-MM-dd'),
          party_size: partySize,
        },
      });
      setSearchResults(response.data.results);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleNext = () => {
    if (currentStep < BOOKING_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
      
      // Announce step change for accessibility
      const nextStep = BOOKING_STEPS[currentStep + 1];
      if (fromVoice) {
        announceStep(nextStep.title);
      }
    } else {
      // Complete booking
      confirmBooking();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const announceStep = async (stepName: string) => {
    // In a real app, this would use TTS
    console.log(`Now at ${stepName} step`);
  };

  const confirmBooking = async () => {
    setLoading(true);
    try {
      const bookingData = {
        type: bookingType,
        item_id: selectedItem.id,
        date: format(bookingDate, 'yyyy-MM-dd'),
        time: bookingType === 'restaurant' ? format(bookingTime, 'HH:mm') : null,
        party_size: partySize,
        nights: bookingType === 'hotel' ? nights : null,
        special_requests: specialRequests,
      };

      const response = await apiClient.post('/api/booking/create', bookingData);
      
      if (response.data.success) {
        onComplete(response.data.booking);
        onClose();
      }
    } catch (error) {
      console.error('Booking failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderStepIndicator = () => (
    <View style={styles.stepIndicator}>
      {BOOKING_STEPS.map((step, index) => (
        <View key={step.id} style={styles.stepItem}>
          <View
            style={[
              styles.stepCircle,
              index <= currentStep && styles.stepCircleActive,
            ]}
          >
            <MaterialIcons
              name={step.icon as any}
              size={20}
              color={index <= currentStep ? '#FFFFFF' : '#999'}
            />
          </View>
          <Text
            style={[
              styles.stepText,
              index <= currentStep && styles.stepTextActive,
            ]}
          >
            {step.title}
          </Text>
          {index < BOOKING_STEPS.length - 1 && (
            <View
              style={[
                styles.stepLine,
                index < currentStep && styles.stepLineActive,
              ]}
            />
          )}
        </View>
      ))}
    </View>
  );

  const renderSelectStep = () => (
    <View style={styles.stepContent}>
      {/* Type Selector */}
      <View style={styles.typeSelector}>
        {(['hotel', 'restaurant', 'activity'] as const).map((type) => (
          <TouchableOpacity
            key={type}
            style={[
              styles.typeOption,
              bookingType === type && styles.typeOptionActive,
            ]}
            onPress={() => {
              setBookingType(type);
              searchNearby();
            }}
          >
            <MaterialIcons
              name={
                type === 'hotel' ? 'hotel' :
                type === 'restaurant' ? 'restaurant' :
                'local-activity'
              }
              size={32}
              color={bookingType === type ? '#007AFF' : '#999'}
            />
            <Text
              style={[
                styles.typeText,
                bookingType === type && styles.typeTextActive,
              ]}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Search Results */}
      {loading ? (
        <ActivityIndicator size="large" color="#007AFF" style={styles.loader} />
      ) : (
        <ScrollView style={styles.resultsList}>
          {searchResults.map((item: any) => (
            <TouchableOpacity
              key={item.id}
              style={[
                styles.resultItem,
                selectedItem?.id === item.id && styles.resultItemSelected,
              ]}
              onPress={() => setSelectedItem(item)}
            >
              <View style={styles.resultInfo}>
                <Text style={styles.resultName}>{item.name}</Text>
                <View style={styles.resultMeta}>
                  <MaterialIcons name="star" size={16} color="#FFD700" />
                  <Text style={styles.resultRating}>{item.rating}</Text>
                  <Text style={styles.resultPrice}>${item.price}</Text>
                </View>
              </View>
              {selectedItem?.id === item.id && (
                <MaterialIcons name="check-circle" size={24} color="#007AFF" />
              )}
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}
    </View>
  );

  const renderDetailsStep = () => (
    <View style={styles.stepContent}>
      <ScrollView>
        {/* Date Selection */}
        <TouchableOpacity
          style={styles.detailRow}
          onPress={() => setShowDatePicker(true)}
        >
          <MaterialIcons name="event" size={24} color="#666" />
          <View style={styles.detailInfo}>
            <Text style={styles.detailLabel}>Date</Text>
            <Text style={styles.detailValue}>
              {format(bookingDate, 'EEEE, MMM d, yyyy')}
            </Text>
          </View>
          <MaterialIcons name="chevron-right" size={24} color="#999" />
        </TouchableOpacity>

        {/* Time Selection (Restaurant only) */}
        {bookingType === 'restaurant' && (
          <TouchableOpacity
            style={styles.detailRow}
            onPress={() => setShowTimePicker(true)}
          >
            <MaterialIcons name="access-time" size={24} color="#666" />
            <View style={styles.detailInfo}>
              <Text style={styles.detailLabel}>Time</Text>
              <Text style={styles.detailValue}>
                {format(bookingTime, 'h:mm a')}
              </Text>
            </View>
            <MaterialIcons name="chevron-right" size={24} color="#999" />
          </TouchableOpacity>
        )}

        {/* Party Size */}
        <View style={styles.detailRow}>
          <MaterialIcons name="people" size={24} color="#666" />
          <View style={styles.detailInfo}>
            <Text style={styles.detailLabel}>
              {bookingType === 'hotel' ? 'Guests' : 'Party Size'}
            </Text>
            <View style={styles.counter}>
              <TouchableOpacity
                onPress={() => setPartySize(Math.max(1, partySize - 1))}
                style={styles.counterButton}
              >
                <MaterialIcons name="remove" size={20} color="#007AFF" />
              </TouchableOpacity>
              <Text style={styles.counterValue}>{partySize}</Text>
              <TouchableOpacity
                onPress={() => setPartySize(partySize + 1)}
                style={styles.counterButton}
              >
                <MaterialIcons name="add" size={20} color="#007AFF" />
              </TouchableOpacity>
            </View>
          </View>
        </View>

        {/* Nights (Hotel only) */}
        {bookingType === 'hotel' && (
          <View style={styles.detailRow}>
            <MaterialIcons name="nights-stay" size={24} color="#666" />
            <View style={styles.detailInfo}>
              <Text style={styles.detailLabel}>Nights</Text>
              <View style={styles.counter}>
                <TouchableOpacity
                  onPress={() => setNights(Math.max(1, nights - 1))}
                  style={styles.counterButton}
                >
                  <MaterialIcons name="remove" size={20} color="#007AFF" />
                </TouchableOpacity>
                <Text style={styles.counterValue}>{nights}</Text>
                <TouchableOpacity
                  onPress={() => setNights(nights + 1)}
                  style={styles.counterButton}
                >
                  <MaterialIcons name="add" size={20} color="#007AFF" />
                </TouchableOpacity>
              </View>
            </View>
          </View>
        )}

        {/* Special Requests */}
        <View style={styles.specialRequestsContainer}>
          <Text style={styles.detailLabel}>Special Requests</Text>
          <TouchableOpacity
            style={styles.specialRequestsInput}
            onPress={() => {
              // In real app, open text input modal
              console.log('Open special requests input');
            }}
          >
            <Text style={styles.specialRequestsText}>
              {specialRequests || 'Tap to add special requests...'}
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );

  const renderConfirmStep = () => (
    <View style={styles.stepContent}>
      <ScrollView>
        <View style={styles.confirmationDetails}>
          <Text style={styles.confirmTitle}>Review Your Booking</Text>
          
          <View style={styles.confirmItem}>
            <Text style={styles.confirmLabel}>Venue</Text>
            <Text style={styles.confirmValue}>{selectedItem?.name}</Text>
          </View>

          <View style={styles.confirmItem}>
            <Text style={styles.confirmLabel}>Date</Text>
            <Text style={styles.confirmValue}>
              {format(bookingDate, 'EEEE, MMM d, yyyy')}
            </Text>
          </View>

          {bookingType === 'restaurant' && (
            <View style={styles.confirmItem}>
              <Text style={styles.confirmLabel}>Time</Text>
              <Text style={styles.confirmValue}>
                {format(bookingTime, 'h:mm a')}
              </Text>
            </View>
          )}

          <View style={styles.confirmItem}>
            <Text style={styles.confirmLabel}>
              {bookingType === 'hotel' ? 'Guests' : 'Party Size'}
            </Text>
            <Text style={styles.confirmValue}>{partySize}</Text>
          </View>

          {bookingType === 'hotel' && (
            <View style={styles.confirmItem}>
              <Text style={styles.confirmLabel}>Nights</Text>
              <Text style={styles.confirmValue}>{nights}</Text>
            </View>
          )}

          {specialRequests && (
            <View style={styles.confirmItem}>
              <Text style={styles.confirmLabel}>Special Requests</Text>
              <Text style={styles.confirmValue}>{specialRequests}</Text>
            </View>
          )}

          <View style={styles.totalPrice}>
            <Text style={styles.totalLabel}>Total Price</Text>
            <Text style={styles.totalValue}>
              ${selectedItem?.price * (bookingType === 'hotel' ? nights : partySize)}
            </Text>
          </View>
        </View>
      </ScrollView>
    </View>
  );

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 0:
        return renderSelectStep();
      case 1:
        return renderDetailsStep();
      case 2:
        return renderConfirmStep();
      default:
        return null;
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <BlurView intensity={95} style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          {/* Header */}
          <View style={styles.header}>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <MaterialIcons name="close" size={24} color="#333" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Make a Booking</Text>
            {fromVoice && (
              <View style={styles.voiceIndicator}>
                <MaterialIcons name="mic" size={16} color="#007AFF" />
              </View>
            )}
          </View>

          {/* Step Indicator */}
          {renderStepIndicator()}

          {/* Step Content */}
          {renderCurrentStep()}

          {/* Navigation Buttons */}
          <View style={styles.navigation}>
            {currentStep > 0 && (
              <TouchableOpacity
                style={styles.navButton}
                onPress={handleBack}
              >
                <MaterialIcons name="arrow-back" size={24} color="#666" />
                <Text style={styles.navButtonText}>Back</Text>
              </TouchableOpacity>
            )}
            
            <TouchableOpacity
              style={[
                styles.navButton,
                styles.navButtonPrimary,
                (!selectedItem || loading) && styles.navButtonDisabled,
              ]}
              onPress={handleNext}
              disabled={!selectedItem || loading}
            >
              <Text style={styles.navButtonTextPrimary}>
                {currentStep === BOOKING_STEPS.length - 1 ? 'Confirm' : 'Next'}
              </Text>
              <MaterialIcons name="arrow-forward" size={24} color="#FFFFFF" />
            </TouchableOpacity>
          </View>
        </View>
      </BlurView>

      {/* Date Picker */}
      {showDatePicker && (
        <DateTimePicker
          value={bookingDate}
          mode="date"
          minimumDate={new Date()}
          maximumDate={addDays(new Date(), 90)}
          onChange={(event, date) => {
            setShowDatePicker(false);
            if (date) setBookingDate(date);
          }}
        />
      )}

      {/* Time Picker */}
      {showTimePicker && (
        <DateTimePicker
          value={bookingTime}
          mode="time"
          onChange={(event, time) => {
            setShowTimePicker(false);
            if (time) setBookingTime(time);
          }}
        />
      )}
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    width: SCREEN_WIDTH * 0.9,
    maxHeight: '85%',
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  closeButton: {
    padding: 4,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  voiceIndicator: {
    backgroundColor: '#E3F2FD',
    borderRadius: 10,
    padding: 6,
  },
  stepIndicator: {
    flexDirection: 'row',
    padding: 20,
    justifyContent: 'center',
  },
  stepItem: {
    alignItems: 'center',
    position: 'relative',
  },
  stepCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#E0E0E0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  stepCircleActive: {
    backgroundColor: '#007AFF',
  },
  stepText: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
  stepTextActive: {
    color: '#007AFF',
    fontWeight: '600',
  },
  stepLine: {
    position: 'absolute',
    top: 20,
    left: 40,
    width: 60,
    height: 2,
    backgroundColor: '#E0E0E0',
  },
  stepLineActive: {
    backgroundColor: '#007AFF',
  },
  stepContent: {
    flex: 1,
    padding: 20,
  },
  typeSelector: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 20,
  },
  typeOption: {
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#F5F5F5',
  },
  typeOptionActive: {
    backgroundColor: '#E3F2FD',
  },
  typeText: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
  },
  typeTextActive: {
    color: '#007AFF',
    fontWeight: '600',
  },
  loader: {
    marginTop: 40,
  },
  resultsList: {
    flex: 1,
  },
  resultItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#F5F5F5',
    marginBottom: 12,
  },
  resultItemSelected: {
    backgroundColor: '#E3F2FD',
    borderWidth: 1,
    borderColor: '#007AFF',
  },
  resultInfo: {
    flex: 1,
  },
  resultName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  resultMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  resultRating: {
    fontSize: 14,
    color: '#666',
  },
  resultPrice: {
    fontSize: 14,
    fontWeight: '600',
    color: '#007AFF',
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  detailInfo: {
    flex: 1,
    marginLeft: 16,
  },
  detailLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  detailValue: {
    fontSize: 16,
    color: '#333',
    fontWeight: '500',
  },
  counter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  counterButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#E3F2FD',
    justifyContent: 'center',
    alignItems: 'center',
  },
  counterValue: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    minWidth: 30,
    textAlign: 'center',
  },
  specialRequestsContainer: {
    padding: 16,
  },
  specialRequestsInput: {
    marginTop: 8,
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#F5F5F5',
    minHeight: 60,
  },
  specialRequestsText: {
    fontSize: 14,
    color: '#666',
  },
  confirmationDetails: {
    padding: 20,
  },
  confirmTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 20,
  },
  confirmItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  confirmLabel: {
    fontSize: 14,
    color: '#666',
  },
  confirmValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  totalPrice: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 20,
    paddingTop: 20,
  },
  totalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  totalValue: {
    fontSize: 24,
    fontWeight: '600',
    color: '#007AFF',
  },
  navigation: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  navButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
    gap: 8,
  },
  navButtonPrimary: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 20,
  },
  navButtonDisabled: {
    backgroundColor: '#CCC',
  },
  navButtonText: {
    fontSize: 16,
    color: '#666',
  },
  navButtonTextPrimary: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});