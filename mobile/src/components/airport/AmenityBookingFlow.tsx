import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Alert,
  TextInput,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { SafeArea } from '../SafeArea';
import { Card } from '../Card';
import { Button } from '../Button';
import { apiManager } from '../../services/api/apiManager';
import { theme } from '../../theme';

interface BookingDetails {
  amenity_id: string;
  user_id: string;
  access_type?: string;
  arrival_time?: Date;
  party_size: number;
  flight_number?: string;
  airline?: string;
  departure_time?: Date;
  special_requests?: string;
  payment_method?: string;
}

interface LoungeAccess {
  lounge_id: string;
  access_type: string;
  requirements: string[];
  guest_policy?: string;
  price?: number;
  duration_hours?: number;
  amenities: string[];
}

export const AmenityBookingFlow: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { amenity } = route.params as { amenity: any };

  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1);
  const [accessOptions, setAccessOptions] = useState<LoungeAccess[]>([]);
  const [selectedAccess, setSelectedAccess] = useState<LoungeAccess | null>(null);
  const [bookingDetails, setBookingDetails] = useState<BookingDetails>({
    amenity_id: amenity.id,
    user_id: 'current_user_id', // Would come from auth context
    party_size: 1,
    arrival_time: new Date(),
  });
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [confirmationLoading, setConfirmationLoading] = useState(false);

  useEffect(() => {
    if (amenity.type === 'lounge') {
      loadAccessOptions();
    }
  }, []);

  const loadAccessOptions = async () => {
    try {
      setLoading(true);
      const response = await apiManager.get(
        `/api/airport/lounges/${amenity.id}/access-options`,
        {
          params: {
            user_id: bookingDetails.user_id,
            flight_details: {
              airline: bookingDetails.airline,
              flight_number: bookingDetails.flight_number,
            },
          },
        }
      );
      setAccessOptions(response.data);
    } catch (error) {
      console.error('Failed to load access options:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBooking = async () => {
    try {
      setConfirmationLoading(true);

      const bookingData = {
        ...bookingDetails,
        access_type: selectedAccess?.access_type,
        arrival_time: bookingDetails.arrival_time?.toISOString(),
        departure_time: bookingDetails.departure_time?.toISOString(),
      };

      const response = await apiManager.post(
        '/api/airport/amenities/book',
        bookingData
      );

      if (response.data.booking_id) {
        navigation.navigate('BookingConfirmation', {
          booking: response.data,
          amenity,
        });
      }
    } catch (error) {
      console.error('Booking failed:', error);
      Alert.alert('Booking Failed', 'Unable to complete your booking. Please try again.');
    } finally {
      setConfirmationLoading(false);
    }
  };

  const renderStepIndicator = () => (
    <View style={styles.stepIndicator}>
      {[1, 2, 3].map((stepNum) => (
        <View key={stepNum} style={styles.stepItem}>
          <View
            style={[
              styles.stepCircle,
              step >= stepNum && styles.stepCircleActive,
            ]}
          >
            <Text
              style={[
                styles.stepNumber,
                step >= stepNum && styles.stepNumberActive,
              ]}
            >
              {stepNum}
            </Text>
          </View>
          {stepNum < 3 && (
            <View
              style={[
                styles.stepLine,
                step > stepNum && styles.stepLineActive,
              ]}
            />
          )}
        </View>
      ))}
    </View>
  );

  const renderStep1 = () => (
    <View style={styles.stepContent}>
      <Text style={styles.stepTitle}>Select Access Type</Text>
      {loading ? (
        <ActivityIndicator size="large" color={theme.colors.primary} />
      ) : (
        <ScrollView>
          {accessOptions.map((option, index) => (
            <TouchableOpacity
              key={index}
              onPress={() => setSelectedAccess(option)}
            >
              <Card
                style={[
                  styles.accessCard,
                  selectedAccess === option && styles.accessCardSelected,
                ]}
              >
                <View style={styles.accessHeader}>
                  <Text style={styles.accessType}>{option.access_type}</Text>
                  {option.price !== undefined && (
                    <Text style={styles.accessPrice}>
                      {option.price === 0 ? 'Free' : `$${option.price}`}
                    </Text>
                  )}
                </View>
                {option.requirements.length > 0 && (
                  <View style={styles.requirementsList}>
                    {option.requirements.map((req, idx) => (
                      <Text key={idx} style={styles.requirement}>
                        • {req}
                      </Text>
                    ))}
                  </View>
                )}
                {option.guest_policy && (
                  <Text style={styles.guestPolicy}>
                    Guest Policy: {option.guest_policy}
                  </Text>
                )}
              </Card>
            </TouchableOpacity>
          ))}

          {amenity.type === 'restaurant' && (
            <Card style={styles.accessCard}>
              <Text style={styles.accessType}>Table Reservation</Text>
              <Text style={styles.requirement}>
                Reserve your table and skip the wait
              </Text>
            </Card>
          )}
        </ScrollView>
      )}
      <Button
        title="Continue"
        onPress={() => setStep(2)}
        disabled={!selectedAccess && amenity.type === 'lounge'}
        style={styles.continueButton}
      />
    </View>
  );

  const renderStep2 = () => (
    <View style={styles.stepContent}>
      <Text style={styles.stepTitle}>Booking Details</Text>
      <ScrollView>
        <Card style={styles.detailsCard}>
          <Text style={styles.fieldLabel}>Party Size</Text>
          <View style={styles.partySizeContainer}>
            <TouchableOpacity
              onPress={() =>
                setBookingDetails({
                  ...bookingDetails,
                  party_size: Math.max(1, bookingDetails.party_size - 1),
                })
              }
              style={styles.partySizeButton}
            >
              <MaterialCommunityIcons name="minus" size={24} color={theme.colors.primary} />
            </TouchableOpacity>
            <Text style={styles.partySizeText}>{bookingDetails.party_size}</Text>
            <TouchableOpacity
              onPress={() =>
                setBookingDetails({
                  ...bookingDetails,
                  party_size: bookingDetails.party_size + 1,
                })
              }
              style={styles.partySizeButton}
            >
              <MaterialCommunityIcons name="plus" size={24} color={theme.colors.primary} />
            </TouchableOpacity>
          </View>
        </Card>

        <Card style={styles.detailsCard}>
          <Text style={styles.fieldLabel}>Arrival Time</Text>
          <TouchableOpacity
            onPress={() => setShowDatePicker(true)}
            style={styles.datePickerButton}
          >
            <MaterialCommunityIcons name="clock" size={20} color={theme.colors.textSecondary} />
            <Text style={styles.datePickerText}>
              {bookingDetails.arrival_time?.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Text>
          </TouchableOpacity>
        </Card>

        <Card style={styles.detailsCard}>
          <Text style={styles.fieldLabel}>Flight Information</Text>
          <TextInput
            style={styles.input}
            placeholder="Airline"
            value={bookingDetails.airline}
            onChangeText={(text) =>
              setBookingDetails({ ...bookingDetails, airline: text })
            }
          />
          <TextInput
            style={[styles.input, styles.inputMargin]}
            placeholder="Flight Number"
            value={bookingDetails.flight_number}
            onChangeText={(text) =>
              setBookingDetails({ ...bookingDetails, flight_number: text })
            }
          />
        </Card>

        <Card style={styles.detailsCard}>
          <Text style={styles.fieldLabel}>Special Requests (Optional)</Text>
          <TextInput
            style={[styles.input, styles.textArea]}
            placeholder="Any special requirements or requests?"
            value={bookingDetails.special_requests}
            onChangeText={(text) =>
              setBookingDetails({ ...bookingDetails, special_requests: text })
            }
            multiline
            numberOfLines={3}
          />
        </Card>
      </ScrollView>
      <View style={styles.buttonRow}>
        <Button
          title="Back"
          onPress={() => setStep(1)}
          variant="secondary"
          style={styles.backButton}
        />
        <Button
          title="Continue"
          onPress={() => setStep(3)}
          style={styles.continueButtonHalf}
        />
      </View>

      {showDatePicker && (
        <DateTimePicker
          value={bookingDetails.arrival_time || new Date()}
          mode="time"
          is24Hour={false}
          display="default"
          onChange={(event, selectedDate) => {
            setShowDatePicker(false);
            if (selectedDate) {
              setBookingDetails({ ...bookingDetails, arrival_time: selectedDate });
            }
          }}
        />
      )}
    </View>
  );

  const renderStep3 = () => (
    <View style={styles.stepContent}>
      <Text style={styles.stepTitle}>Review & Confirm</Text>
      <ScrollView>
        <Card style={styles.summaryCard}>
          <Text style={styles.summaryTitle}>{amenity.name}</Text>
          <Text style={styles.summaryLocation}>
            {amenity.terminal} • {amenity.location_description}
          </Text>

          <View style={styles.summaryDivider} />

          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Access Type:</Text>
            <Text style={styles.summaryValue}>
              {selectedAccess?.access_type || 'Reservation'}
            </Text>
          </View>

          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Party Size:</Text>
            <Text style={styles.summaryValue}>{bookingDetails.party_size} guests</Text>
          </View>

          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Arrival Time:</Text>
            <Text style={styles.summaryValue}>
              {bookingDetails.arrival_time?.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Text>
          </View>

          {bookingDetails.flight_number && (
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Flight:</Text>
              <Text style={styles.summaryValue}>
                {bookingDetails.airline} {bookingDetails.flight_number}
              </Text>
            </View>
          )}

          <View style={styles.summaryDivider} />

          <View style={styles.summaryRow}>
            <Text style={styles.totalLabel}>Total:</Text>
            <Text style={styles.totalValue}>
              {selectedAccess?.price === 0
                ? 'Free'
                : `$${(selectedAccess?.price || 0) * bookingDetails.party_size}`}
            </Text>
          </View>
        </Card>

        <Card style={styles.termsCard}>
          <MaterialCommunityIcons
            name="information"
            size={20}
            color={theme.colors.textSecondary}
          />
          <Text style={styles.termsText}>
            By confirming this booking, you agree to the terms and conditions.
            Free cancellation up to 2 hours before arrival.
          </Text>
        </Card>
      </ScrollView>

      <View style={styles.buttonRow}>
        <Button
          title="Back"
          onPress={() => setStep(2)}
          variant="secondary"
          style={styles.backButton}
        />
        <Button
          title="Confirm Booking"
          onPress={handleBooking}
          loading={confirmationLoading}
          style={styles.continueButtonHalf}
        />
      </View>
    </View>
  );

  return (
    <SafeArea>
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <MaterialCommunityIcons name="close" size={24} color={theme.colors.text} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Book {amenity.type === 'lounge' ? 'Lounge' : 'Restaurant'}</Text>
          <View style={{ width: 24 }} />
        </View>

        {renderStepIndicator()}

        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
      </View>
    </SafeArea>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text,
  },
  stepIndicator: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 24,
  },
  stepItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  stepCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: theme.colors.backgroundLight,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: theme.colors.border,
  },
  stepCircleActive: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primary,
  },
  stepNumber: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.textSecondary,
  },
  stepNumberActive: {
    color: '#fff',
  },
  stepLine: {
    width: 60,
    height: 2,
    backgroundColor: theme.colors.border,
    marginHorizontal: 8,
  },
  stepLineActive: {
    backgroundColor: theme.colors.primary,
  },
  stepContent: {
    flex: 1,
    paddingHorizontal: 16,
  },
  stepTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 20,
  },
  accessCard: {
    marginBottom: 12,
    padding: 16,
  },
  accessCardSelected: {
    borderColor: theme.colors.primary,
    borderWidth: 2,
  },
  accessHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  accessType: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text,
    textTransform: 'capitalize',
  },
  accessPrice: {
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.colors.primary,
  },
  requirementsList: {
    marginTop: 8,
  },
  requirement: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginBottom: 4,
  },
  guestPolicy: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginTop: 8,
    fontStyle: 'italic',
  },
  continueButton: {
    marginTop: 20,
  },
  detailsCard: {
    marginBottom: 16,
    padding: 16,
  },
  fieldLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: 12,
  },
  partySizeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  partySizeButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: theme.colors.backgroundLight,
    justifyContent: 'center',
    alignItems: 'center',
  },
  partySizeText: {
    fontSize: 24,
    fontWeight: '600',
    color: theme.colors.text,
    marginHorizontal: 32,
  },
  datePickerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.backgroundLight,
    padding: 12,
    borderRadius: 8,
  },
  datePickerText: {
    fontSize: 16,
    color: theme.colors.text,
    marginLeft: 8,
  },
  input: {
    backgroundColor: theme.colors.backgroundLight,
    padding: 12,
    borderRadius: 8,
    fontSize: 16,
    color: theme.colors.text,
  },
  inputMargin: {
    marginTop: 12,
  },
  textArea: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  buttonRow: {
    flexDirection: 'row',
    marginTop: 20,
  },
  backButton: {
    flex: 1,
    marginRight: 8,
  },
  continueButtonHalf: {
    flex: 1,
    marginLeft: 8,
  },
  summaryCard: {
    marginBottom: 16,
    padding: 20,
  },
  summaryTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 4,
  },
  summaryLocation: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  summaryDivider: {
    height: 1,
    backgroundColor: theme.colors.border,
    marginVertical: 16,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  summaryLabel: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  summaryValue: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.text,
  },
  totalLabel: {
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  totalValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.primary,
  },
  termsCard: {
    flexDirection: 'row',
    padding: 16,
    marginBottom: 16,
  },
  termsText: {
    flex: 1,
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginLeft: 12,
    lineHeight: 18,
  },
});