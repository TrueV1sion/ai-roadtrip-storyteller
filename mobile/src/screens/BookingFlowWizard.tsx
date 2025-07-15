import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  Image,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { Ionicons } from '@expo/vector-icons';
import { ApiClient } from '../services/api/ApiClient';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { SafeArea } from '../components/SafeArea';
import { formatters } from '../utils/formatters';

interface BookingStep {
  id: string;
  title: string;
  icon: string;
}

const BOOKING_STEPS: BookingStep[] = [
  { id: 'datetime', title: 'Date & Time', icon: 'calendar' },
  { id: 'details', title: 'Details', icon: 'people' },
  { id: 'contact', title: 'Contact Info', icon: 'person' },
  { id: 'confirm', title: 'Confirm', icon: 'checkmark-circle' },
];

interface BookingData {
  date: Date;
  time: Date;
  partySize: number;
  specialRequests?: string;
  occasionType?: string;
  dietaryRestrictions?: string[];
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  marketingOptIn: boolean;
}

export const BookingFlowWizard: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { venue, initialDate, initialTime, initialPartySize } = route.params as any;
  const apiClient = new ApiClient();

  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);
  
  const [bookingData, setBookingData] = useState<BookingData>({
    date: initialDate || new Date(),
    time: initialTime || new Date(),
    partySize: initialPartySize || 2,
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    marketingOptIn: false,
  });

  const [selectedDietaryRestrictions, setSelectedDietaryRestrictions] = useState<string[]>([]);
  const dietaryOptions = [
    'Vegetarian', 'Vegan', 'Gluten-Free', 'Dairy-Free',
    'Nut Allergy', 'Shellfish Allergy', 'Kosher', 'Halal'
  ];

  const occasionOptions = [
    'Casual Dining', 'Birthday', 'Anniversary', 'Business Meeting',
    'Date Night', 'Family Gathering', 'Special Celebration'
  ];

  const validateStep = useCallback(() => {
    switch (BOOKING_STEPS[currentStep].id) {
      case 'datetime':
        return true; // Date and time are always valid
      case 'details':
        return bookingData.partySize > 0;
      case 'contact':
        return (
          bookingData.firstName.trim() !== '' &&
          bookingData.lastName.trim() !== '' &&
          bookingData.email.includes('@') &&
          bookingData.phone.length >= 10
        );
      case 'confirm':
        return true;
      default:
        return false;
    }
  }, [currentStep, bookingData]);

  const handleNext = useCallback(() => {
    if (!validateStep()) {
      Alert.alert('Missing Information', 'Please fill in all required fields.');
      return;
    }

    if (currentStep < BOOKING_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  }, [currentStep, validateStep]);

  const handlePrevious = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  }, [currentStep]);

  const handleConfirmBooking = useCallback(async () => {
    setLoading(true);
    try {
      const combinedDateTime = new Date(bookingData.date);
      combinedDateTime.setHours(
        bookingData.time.getHours(),
        bookingData.time.getMinutes()
      );

      const response = await apiClient.post('/api/reservations/book', {
        provider: venue.provider,
        venueId: venue.venueId,
        dateTime: combinedDateTime.toISOString(),
        partySize: bookingData.partySize,
        customerInfo: {
          firstName: bookingData.firstName,
          lastName: bookingData.lastName,
          email: bookingData.email,
          phone: bookingData.phone,
        },
        specialRequests: bookingData.specialRequests,
        occasionType: bookingData.occasionType,
        dietaryRestrictions: selectedDietaryRestrictions,
        marketingOptIn: bookingData.marketingOptIn,
      });

      navigation.navigate('ReservationConfirmationScreen', {
        reservation: response.data.reservation,
        venue: venue,
      });
    } catch (error) {
      console.error('Booking error:', error);
      Alert.alert(
        'Booking Failed',
        'Unable to complete your reservation. Please try again or contact the restaurant directly.'
      );
    } finally {
      setLoading(false);
    }
  }, [bookingData, selectedDietaryRestrictions, venue, navigation]);

  const renderStepIndicator = () => (
    <View style={styles.stepIndicator}>
      {BOOKING_STEPS.map((step, index) => (
        <View key={step.id} style={styles.stepItem}>
          <TouchableOpacity
            style={[
              styles.stepCircle,
              index === currentStep && styles.stepCircleActive,
              index < currentStep && styles.stepCircleCompleted,
            ]}
            onPress={() => index < currentStep && setCurrentStep(index)}
            disabled={index > currentStep}
          >
            <Ionicons
              name={index < currentStep ? 'checkmark' : step.icon}
              size={20}
              color={index <= currentStep ? 'white' : '#ccc'}
            />
          </TouchableOpacity>
          <Text style={[
            styles.stepLabel,
            index === currentStep && styles.stepLabelActive,
          ]}>
            {step.title}
          </Text>
          {index < BOOKING_STEPS.length - 1 && (
            <View style={[
              styles.stepLine,
              index < currentStep && styles.stepLineCompleted,
            ]} />
          )}
        </View>
      ))}
    </View>
  );

  const renderDateTimeStep = () => (
    <View style={styles.stepContent}>
      <Card style={styles.venueCard}>
        <View style={styles.venueHeader}>
          {venue.imageUrl && (
            <Image source={{ uri: venue.imageUrl }} style={styles.venueImage} />
          )}
          <View style={styles.venueInfo}>
            <Text style={styles.venueName}>{venue.name}</Text>
            <Text style={styles.venueDetails}>{venue.cuisine}</Text>
            <View style={styles.venueRating}>
              <Ionicons name="star" size={16} color="#FFD700" />
              <Text style={styles.ratingText}>{venue.rating.toFixed(1)}</Text>
            </View>
          </View>
        </View>
      </Card>

      <Text style={styles.sectionTitle}>Select Date & Time</Text>
      
      <TouchableOpacity
        style={styles.dateTimeSelector}
        onPress={() => setShowDatePicker(true)}
      >
        <Ionicons name="calendar" size={24} color="#007AFF" />
        <Text style={styles.dateTimeText}>
          {formatters.formatDate(bookingData.date)}
        </Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.dateTimeSelector}
        onPress={() => setShowTimePicker(true)}
      >
        <Ionicons name="time" size={24} color="#007AFF" />
        <Text style={styles.dateTimeText}>
          {formatters.formatTime(bookingData.time)}
        </Text>
      </TouchableOpacity>

      <View style={styles.availableTimesContainer}>
        <Text style={styles.subsectionTitle}>Suggested times:</Text>
        <View style={styles.timeSlots}>
          {venue.availableTimes?.slice(0, 6).map((time: string, index: number) => (
            <TouchableOpacity
              key={index}
              style={styles.timeSlot}
              onPress={() => {
                const [hours, minutes] = time.split(':');
                const newTime = new Date();
                newTime.setHours(parseInt(hours), parseInt(minutes));
                setBookingData(prev => ({ ...prev, time: newTime }));
              }}
            >
              <Text style={styles.timeSlotText}>{time}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>
    </View>
  );

  const renderDetailsStep = () => (
    <View style={styles.stepContent}>
      <Text style={styles.sectionTitle}>Reservation Details</Text>
      
      <View style={styles.partySizeContainer}>
        <Text style={styles.fieldLabel}>Party Size</Text>
        <View style={styles.partySizeControls}>
          <TouchableOpacity
            onPress={() => setBookingData(prev => ({
              ...prev,
              partySize: Math.max(1, prev.partySize - 1)
            }))}
            style={styles.partySizeButton}
          >
            <Ionicons name="remove-circle" size={32} color="#007AFF" />
          </TouchableOpacity>
          <Text style={styles.partySizeText}>{bookingData.partySize} guests</Text>
          <TouchableOpacity
            onPress={() => setBookingData(prev => ({
              ...prev,
              partySize: Math.min(20, prev.partySize + 1)
            }))}
            style={styles.partySizeButton}
          >
            <Ionicons name="add-circle" size={32} color="#007AFF" />
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.fieldContainer}>
        <Text style={styles.fieldLabel}>Occasion (Optional)</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          {occasionOptions.map((occasion) => (
            <TouchableOpacity
              key={occasion}
              style={[
                styles.optionChip,
                bookingData.occasionType === occasion && styles.optionChipSelected
              ]}
              onPress={() => setBookingData(prev => ({
                ...prev,
                occasionType: occasion === prev.occasionType ? undefined : occasion
              }))}
            >
              <Text style={[
                styles.optionChipText,
                bookingData.occasionType === occasion && styles.optionChipTextSelected
              ]}>
                {occasion}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      <View style={styles.fieldContainer}>
        <Text style={styles.fieldLabel}>Dietary Restrictions (Optional)</Text>
        <View style={styles.dietaryGrid}>
          {dietaryOptions.map((restriction) => (
            <TouchableOpacity
              key={restriction}
              style={[
                styles.dietaryOption,
                selectedDietaryRestrictions.includes(restriction) && styles.dietaryOptionSelected
              ]}
              onPress={() => {
                setSelectedDietaryRestrictions(prev =>
                  prev.includes(restriction)
                    ? prev.filter(r => r !== restriction)
                    : [...prev, restriction]
                );
              }}
            >
              <Ionicons
                name={selectedDietaryRestrictions.includes(restriction) ? 'checkbox' : 'square-outline'}
                size={20}
                color={selectedDietaryRestrictions.includes(restriction) ? '#007AFF' : '#666'}
              />
              <Text style={styles.dietaryOptionText}>{restriction}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <View style={styles.fieldContainer}>
        <Text style={styles.fieldLabel}>Special Requests (Optional)</Text>
        <TextInput
          style={styles.textArea}
          placeholder="Any special requests or notes for the restaurant..."
          value={bookingData.specialRequests}
          onChangeText={(text) => setBookingData(prev => ({ ...prev, specialRequests: text }))}
          multiline
          numberOfLines={3}
          textAlignVertical="top"
        />
      </View>
    </View>
  );

  const renderContactStep = () => (
    <KeyboardAvoidingView
      style={styles.stepContent}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <Text style={styles.sectionTitle}>Contact Information</Text>
      
      <View style={styles.fieldContainer}>
        <Text style={styles.fieldLabel}>First Name *</Text>
        <TextInput
          style={styles.input}
          placeholder="Enter your first name"
          value={bookingData.firstName}
          onChangeText={(text) => setBookingData(prev => ({ ...prev, firstName: text }))}
          autoCapitalize="words"
        />
      </View>

      <View style={styles.fieldContainer}>
        <Text style={styles.fieldLabel}>Last Name *</Text>
        <TextInput
          style={styles.input}
          placeholder="Enter your last name"
          value={bookingData.lastName}
          onChangeText={(text) => setBookingData(prev => ({ ...prev, lastName: text }))}
          autoCapitalize="words"
        />
      </View>

      <View style={styles.fieldContainer}>
        <Text style={styles.fieldLabel}>Email *</Text>
        <TextInput
          style={styles.input}
          placeholder="your@email.com"
          value={bookingData.email}
          onChangeText={(text) => setBookingData(prev => ({ ...prev, email: text }))}
          keyboardType="email-address"
          autoCapitalize="none"
        />
      </View>

      <View style={styles.fieldContainer}>
        <Text style={styles.fieldLabel}>Phone Number *</Text>
        <TextInput
          style={styles.input}
          placeholder="(555) 123-4567"
          value={bookingData.phone}
          onChangeText={(text) => setBookingData(prev => ({ ...prev, phone: text }))}
          keyboardType="phone-pad"
        />
      </View>

      <TouchableOpacity
        style={styles.marketingOption}
        onPress={() => setBookingData(prev => ({ ...prev, marketingOptIn: !prev.marketingOptIn }))}
      >
        <Ionicons
          name={bookingData.marketingOptIn ? 'checkbox' : 'square-outline'}
          size={24}
          color={bookingData.marketingOptIn ? '#007AFF' : '#666'}
        />
        <Text style={styles.marketingText}>
          I'd like to receive updates and special offers from {venue.name}
        </Text>
      </TouchableOpacity>
    </KeyboardAvoidingView>
  );

  const renderConfirmStep = () => {
    const combinedDateTime = new Date(bookingData.date);
    combinedDateTime.setHours(
      bookingData.time.getHours(),
      bookingData.time.getMinutes()
    );

    return (
      <ScrollView style={styles.stepContent}>
        <Text style={styles.sectionTitle}>Confirm Your Reservation</Text>
        
        <Card style={styles.confirmationCard}>
          <View style={styles.confirmSection}>
            <Text style={styles.confirmLabel}>Restaurant</Text>
            <Text style={styles.confirmValue}>{venue.name}</Text>
          </View>

          <View style={styles.confirmSection}>
            <Text style={styles.confirmLabel}>Date & Time</Text>
            <Text style={styles.confirmValue}>
              {formatters.formatDate(bookingData.date)} at {formatters.formatTime(bookingData.time)}
            </Text>
          </View>

          <View style={styles.confirmSection}>
            <Text style={styles.confirmLabel}>Party Size</Text>
            <Text style={styles.confirmValue}>{bookingData.partySize} guests</Text>
          </View>

          {bookingData.occasionType && (
            <View style={styles.confirmSection}>
              <Text style={styles.confirmLabel}>Occasion</Text>
              <Text style={styles.confirmValue}>{bookingData.occasionType}</Text>
            </View>
          )}

          {selectedDietaryRestrictions.length > 0 && (
            <View style={styles.confirmSection}>
              <Text style={styles.confirmLabel}>Dietary Restrictions</Text>
              <Text style={styles.confirmValue}>
                {selectedDietaryRestrictions.join(', ')}
              </Text>
            </View>
          )}

          {bookingData.specialRequests && (
            <View style={styles.confirmSection}>
              <Text style={styles.confirmLabel}>Special Requests</Text>
              <Text style={styles.confirmValue}>{bookingData.specialRequests}</Text>
            </View>
          )}

          <View style={[styles.confirmSection, styles.confirmSectionLast]}>
            <Text style={styles.confirmLabel}>Contact</Text>
            <Text style={styles.confirmValue}>
              {bookingData.firstName} {bookingData.lastName}
            </Text>
            <Text style={styles.confirmValueSmall}>{bookingData.email}</Text>
            <Text style={styles.confirmValueSmall}>{bookingData.phone}</Text>
          </View>
        </Card>

        <View style={styles.termsContainer}>
          <Ionicons name="information-circle" size={20} color="#666" />
          <Text style={styles.termsText}>
            By confirming, you agree to the restaurant's cancellation policy and terms of service.
          </Text>
        </View>
      </ScrollView>
    );
  };

  const renderCurrentStep = () => {
    switch (BOOKING_STEPS[currentStep].id) {
      case 'datetime':
        return renderDateTimeStep();
      case 'details':
        return renderDetailsStep();
      case 'contact':
        return renderContactStep();
      case 'confirm':
        return renderConfirmStep();
      default:
        return null;
    }
  };

  return (
    <SafeArea>
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <Ionicons name="close" size={24} color="#333" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Book a Table</Text>
          <View style={{ width: 24 }} />
        </View>

        {renderStepIndicator()}

        <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
          {renderCurrentStep()}
        </ScrollView>

        <View style={styles.footer}>
          <Button
            title="Previous"
            onPress={handlePrevious}
            variant="outline"
            style={[styles.footerButton, { opacity: currentStep === 0 ? 0.5 : 1 }]}
            disabled={currentStep === 0}
          />
          
          {currentStep === BOOKING_STEPS.length - 1 ? (
            <Button
              title="Confirm Booking"
              onPress={handleConfirmBooking}
              loading={loading}
              style={[styles.footerButton, styles.confirmButton]}
            />
          ) : (
            <Button
              title="Next"
              onPress={handleNext}
              style={styles.footerButton}
            />
          )}
        </View>

        {showDatePicker && (
          <DateTimePicker
            value={bookingData.date}
            mode="date"
            minimumDate={new Date()}
            onChange={(event, date) => {
              setShowDatePicker(false);
              if (date) {
                setBookingData(prev => ({ ...prev, date }));
              }
            }}
          />
        )}

        {showTimePicker && (
          <DateTimePicker
            value={bookingData.time}
            mode="time"
            onChange={(event, time) => {
              setShowTimePicker(false);
              if (time) {
                setBookingData(prev => ({ ...prev, time }));
              }
            }}
          />
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  stepIndicator: {
    flexDirection: 'row',
    paddingVertical: 24,
    paddingHorizontal: 16,
    backgroundColor: 'white',
  },
  stepItem: {
    flex: 1,
    alignItems: 'center',
    position: 'relative',
  },
  stepCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#f0f0f0',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  stepCircleActive: {
    backgroundColor: '#007AFF',
  },
  stepCircleCompleted: {
    backgroundColor: '#4CAF50',
  },
  stepLabel: {
    fontSize: 12,
    color: '#666',
  },
  stepLabelActive: {
    color: '#007AFF',
    fontWeight: '600',
  },
  stepLine: {
    position: 'absolute',
    top: 20,
    left: '50%',
    right: '-50%',
    height: 2,
    backgroundColor: '#e0e0e0',
    zIndex: -1,
  },
  stepLineCompleted: {
    backgroundColor: '#4CAF50',
  },
  content: {
    flex: 1,
  },
  stepContent: {
    padding: 16,
  },
  venueCard: {
    marginBottom: 24,
    padding: 16,
  },
  venueHeader: {
    flexDirection: 'row',
  },
  venueImage: {
    width: 60,
    height: 60,
    borderRadius: 8,
    marginRight: 12,
  },
  venueInfo: {
    flex: 1,
  },
  venueName: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  venueDetails: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  venueRating: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  ratingText: {
    marginLeft: 4,
    fontSize: 14,
    fontWeight: '500',
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 16,
  },
  subsectionTitle: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 12,
    color: '#666',
  },
  dateTimeSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  dateTimeText: {
    fontSize: 16,
    marginLeft: 12,
    flex: 1,
  },
  availableTimesContainer: {
    marginTop: 16,
  },
  timeSlots: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  timeSlot: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 16,
    marginRight: 8,
    marginBottom: 8,
  },
  timeSlotText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '500',
  },
  fieldContainer: {
    marginBottom: 20,
  },
  fieldLabel: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 8,
    color: '#333',
  },
  input: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  textArea: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    minHeight: 80,
  },
  partySizeContainer: {
    marginBottom: 24,
  },
  partySizeControls: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 12,
  },
  partySizeButton: {
    padding: 8,
  },
  partySizeText: {
    fontSize: 20,
    fontWeight: '600',
    marginHorizontal: 24,
  },
  optionChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: 'white',
    borderWidth: 1,
    borderColor: '#e0e0e0',
    marginRight: 8,
  },
  optionChipSelected: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  optionChipText: {
    fontSize: 14,
    color: '#333',
  },
  optionChipTextSelected: {
    color: 'white',
  },
  dietaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  dietaryOption: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '50%',
    paddingVertical: 8,
  },
  dietaryOptionSelected: {
    // No additional styles needed
  },
  dietaryOptionText: {
    marginLeft: 8,
    fontSize: 14,
  },
  marketingOption: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 16,
  },
  marketingText: {
    marginLeft: 8,
    fontSize: 14,
    flex: 1,
    color: '#666',
  },
  confirmationCard: {
    padding: 16,
    marginBottom: 16,
  },
  confirmSection: {
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  confirmSectionLast: {
    borderBottomWidth: 0,
    marginBottom: 0,
    paddingBottom: 0,
  },
  confirmLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  confirmValue: {
    fontSize: 16,
    fontWeight: '500',
  },
  confirmValueSmall: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  termsContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  termsText: {
    fontSize: 12,
    color: '#666',
    marginLeft: 8,
    flex: 1,
  },
  footer: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  footerButton: {
    flex: 1,
    marginHorizontal: 8,
  },
  confirmButton: {
    backgroundColor: '#4CAF50',
  },
});