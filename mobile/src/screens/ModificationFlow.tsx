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
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { Ionicons } from '@expo/vector-icons';
import { ApiClient } from '../services/api/ApiClient';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { SafeArea } from '../components/SafeArea';
import { formatters } from '../utils/formatters';

interface ModificationData {
  date: Date;
  time: Date;
  partySize: number;
  specialRequests?: string;
}

export const ModificationFlow: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { reservation } = route.params as { reservation: any };
  const apiClient = new ApiClient();

  const originalDate = new Date(reservation.dateTime);
  
  const [loading, setLoading] = useState(false);
  const [checkingAvailability, setCheckingAvailability] = useState(false);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);
  const [availableTimes, setAvailableTimes] = useState<string[]>([]);
  
  const [modificationData, setModificationData] = useState<ModificationData>({
    date: originalDate,
    time: originalDate,
    partySize: reservation.partySize,
    specialRequests: reservation.specialRequests || '',
  });

  const hasChanges = () => {
    return (
      modificationData.date.toDateString() !== originalDate.toDateString() ||
      modificationData.time.toTimeString() !== originalDate.toTimeString() ||
      modificationData.partySize !== reservation.partySize ||
      modificationData.specialRequests !== (reservation.specialRequests || '')
    );
  };

  const checkAvailability = useCallback(async () => {
    setCheckingAvailability(true);
    try {
      const response = await apiClient.post('/api/reservations/check-availability', {
        provider: reservation.provider,
        venueId: reservation.venueId,
        date: modificationData.date.toISOString(),
        time: modificationData.time.toISOString(),
        partySize: modificationData.partySize,
        excludeReservationId: reservation.id,
      });
      
      setAvailableTimes(response.data.availableTimes || []);
      
      if (response.data.availableTimes.length === 0) {
        Alert.alert(
          'No Availability',
          'No tables are available for the selected date and party size. Please try a different date or time.'
        );
      }
    } catch (error) {
      console.error('Availability check error:', error);
      Alert.alert('Error', 'Unable to check availability. Please try again.');
    } finally {
      setCheckingAvailability(false);
    }
  }, [modificationData, reservation]);

  const handleConfirmModification = useCallback(async () => {
    if (!hasChanges()) {
      Alert.alert('No Changes', 'No modifications have been made.');
      return;
    }

    Alert.alert(
      'Confirm Modification',
      'Are you sure you want to modify this reservation?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Confirm',
          onPress: async () => {
            setLoading(true);
            try {
              const combinedDateTime = new Date(modificationData.date);
              combinedDateTime.setHours(
                modificationData.time.getHours(),
                modificationData.time.getMinutes()
              );

              const response = await apiClient.put(`/api/reservations/${reservation.id}/modify`, {
                dateTime: combinedDateTime.toISOString(),
                partySize: modificationData.partySize,
                specialRequests: modificationData.specialRequests,
              });

              Alert.alert(
                'Modification Successful',
                'Your reservation has been updated successfully.',
                [
                  {
                    text: 'OK',
                    onPress: () => {
                      navigation.navigate('ReservationConfirmationScreen', {
                        reservation: response.data.reservation,
                        venue: { name: reservation.venueName },
                      });
                    },
                  },
                ]
              );
            } catch (error) {
              console.error('Modification error:', error);
              Alert.alert(
                'Modification Failed',
                'Unable to modify your reservation. Please try again or contact the restaurant directly.'
              );
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  }, [modificationData, reservation, navigation]);

  const handleCancelReservation = useCallback(async () => {
    Alert.alert(
      'Cancel Reservation',
      'Are you sure you want to cancel this reservation?',
      [
        { text: 'No', style: 'cancel' },
        {
          text: 'Yes, Cancel',
          style: 'destructive',
          onPress: async () => {
            setLoading(true);
            try {
              await apiClient.post(`/api/reservations/${reservation.id}/cancel`);
              Alert.alert(
                'Reservation Cancelled',
                'Your reservation has been cancelled successfully.',
                [
                  {
                    text: 'OK',
                    onPress: () => navigation.navigate('MyReservationsScreen'),
                  },
                ]
              );
            } catch (error) {
              console.error('Cancellation error:', error);
              Alert.alert(
                'Cancellation Failed',
                'Unable to cancel reservation. Please contact the restaurant directly.'
              );
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  }, [reservation, navigation]);

  return (
    <SafeArea>
      <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <Ionicons name="arrow-back" size={24} color="#333" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Modify Reservation</Text>
          <View style={{ width: 24 }} />
        </View>

        <Card style={styles.venueCard}>
          <Text style={styles.venueName}>{reservation.venueName}</Text>
          <Text style={styles.confirmationNumber}>
            Confirmation #{reservation.confirmationNumber}
          </Text>
        </Card>

        <Card style={styles.currentDetailsCard}>
          <Text style={styles.sectionTitle}>Current Reservation</Text>
          <View style={styles.detailRow}>
            <Ionicons name="calendar" size={20} color="#666" />
            <Text style={styles.detailText}>
              {formatters.formatDate(originalDate)}
            </Text>
          </View>
          <View style={styles.detailRow}>
            <Ionicons name="time" size={20} color="#666" />
            <Text style={styles.detailText}>
              {formatters.formatTime(originalDate)}
            </Text>
          </View>
          <View style={styles.detailRow}>
            <Ionicons name="people" size={20} color="#666" />
            <Text style={styles.detailText}>
              {reservation.partySize} {reservation.partySize === 1 ? 'guest' : 'guests'}
            </Text>
          </View>
        </Card>

        <View style={styles.modificationSection}>
          <Text style={styles.sectionTitle}>Modify Details</Text>
          
          <TouchableOpacity
            style={styles.dateTimeSelector}
            onPress={() => setShowDatePicker(true)}
          >
            <Ionicons name="calendar" size={24} color="#007AFF" />
            <Text style={styles.dateTimeText}>
              {formatters.formatDate(modificationData.date)}
            </Text>
            {modificationData.date.toDateString() !== originalDate.toDateString() && (
              <View style={styles.changeIndicator}>
                <Text style={styles.changeText}>Changed</Text>
              </View>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.dateTimeSelector}
            onPress={() => setShowTimePicker(true)}
          >
            <Ionicons name="time" size={24} color="#007AFF" />
            <Text style={styles.dateTimeText}>
              {formatters.formatTime(modificationData.time)}
            </Text>
            {modificationData.time.toTimeString() !== originalDate.toTimeString() && (
              <View style={styles.changeIndicator}>
                <Text style={styles.changeText}>Changed</Text>
              </View>
            )}
          </TouchableOpacity>

          <View style={styles.partySizeContainer}>
            <Text style={styles.fieldLabel}>Party Size</Text>
            <View style={styles.partySizeControls}>
              <TouchableOpacity
                onPress={() => setModificationData(prev => ({
                  ...prev,
                  partySize: Math.max(1, prev.partySize - 1)
                }))}
                style={styles.partySizeButton}
              >
                <Ionicons name="remove-circle" size={32} color="#007AFF" />
              </TouchableOpacity>
              <Text style={styles.partySizeText}>
                {modificationData.partySize} {modificationData.partySize === 1 ? 'guest' : 'guests'}
              </Text>
              <TouchableOpacity
                onPress={() => setModificationData(prev => ({
                  ...prev,
                  partySize: Math.min(20, prev.partySize + 1)
                }))}
                style={styles.partySizeButton}
              >
                <Ionicons name="add-circle" size={32} color="#007AFF" />
              </TouchableOpacity>
            </View>
            {modificationData.partySize !== reservation.partySize && (
              <View style={styles.changeIndicator}>
                <Text style={styles.changeText}>Changed from {reservation.partySize}</Text>
              </View>
            )}
          </View>

          <View style={styles.fieldContainer}>
            <Text style={styles.fieldLabel}>Special Requests (Optional)</Text>
            <TextInput
              style={styles.textArea}
              placeholder="Any special requests or notes..."
              value={modificationData.specialRequests}
              onChangeText={(text) => setModificationData(prev => ({ ...prev, specialRequests: text }))}
              multiline
              numberOfLines={3}
              textAlignVertical="top"
            />
          </View>

          {(modificationData.date.toDateString() !== originalDate.toDateString() ||
            modificationData.partySize !== reservation.partySize) && (
            <Button
              title="Check Availability"
              onPress={checkAvailability}
              loading={checkingAvailability}
              variant="outline"
              style={styles.checkButton}
            />
          )}

          {availableTimes.length > 0 && (
            <View style={styles.availableTimesContainer}>
              <Text style={styles.subsectionTitle}>Available times:</Text>
              <View style={styles.timeSlots}>
                {availableTimes.map((time, index) => (
                  <TouchableOpacity
                    key={index}
                    style={styles.timeSlot}
                    onPress={() => {
                      const [hours, minutes] = time.split(':');
                      const newTime = new Date();
                      newTime.setHours(parseInt(hours), parseInt(minutes));
                      setModificationData(prev => ({ ...prev, time: newTime }));
                    }}
                  >
                    <Text style={styles.timeSlotText}>{time}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          )}
        </View>

        {reservation.cancellationPolicy && (
          <Card style={styles.policyCard}>
            <Text style={styles.policyTitle}>Modification Policy</Text>
            <Text style={styles.policyText}>{reservation.cancellationPolicy}</Text>
          </Card>
        )}

        <View style={styles.actionButtons}>
          <Button
            title="Confirm Modification"
            onPress={handleConfirmModification}
            loading={loading}
            disabled={!hasChanges()}
            style={styles.confirmButton}
          />
          
          <Button
            title="Cancel Reservation"
            onPress={handleCancelReservation}
            variant="outline"
            style={[styles.cancelButton, { borderColor: '#FF3B30' }]}
          />
        </View>

        {showDatePicker && (
          <DateTimePicker
            value={modificationData.date}
            mode="date"
            minimumDate={new Date()}
            onChange={(event, date) => {
              setShowDatePicker(false);
              if (date) {
                setModificationData(prev => ({ ...prev, date }));
                setAvailableTimes([]);
              }
            }}
          />
        )}

        {showTimePicker && (
          <DateTimePicker
            value={modificationData.time}
            mode="time"
            onChange={(event, time) => {
              setShowTimePicker(false);
              if (time) {
                setModificationData(prev => ({ ...prev, time }));
              }
            }}
          />
        )}
      </ScrollView>
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
  venueCard: {
    margin: 16,
    padding: 16,
  },
  venueName: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  confirmationNumber: {
    fontSize: 14,
    color: '#666',
  },
  currentDetailsCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
  },
  subsectionTitle: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 12,
    color: '#666',
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  detailText: {
    fontSize: 16,
    marginLeft: 12,
  },
  modificationSection: {
    paddingHorizontal: 16,
    marginBottom: 16,
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
  changeIndicator: {
    backgroundColor: '#FFF3CD',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  changeText: {
    fontSize: 12,
    color: '#856404',
    fontWeight: '500',
  },
  partySizeContainer: {
    marginBottom: 20,
  },
  fieldLabel: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 12,
    color: '#333',
  },
  partySizeControls: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
  },
  partySizeButton: {
    padding: 8,
  },
  partySizeText: {
    fontSize: 20,
    fontWeight: '600',
    marginHorizontal: 24,
  },
  fieldContainer: {
    marginBottom: 20,
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
  checkButton: {
    marginBottom: 16,
  },
  availableTimesContainer: {
    marginBottom: 16,
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
  policyCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
  },
  policyTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  policyText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  actionButtons: {
    paddingHorizontal: 16,
    marginBottom: 32,
  },
  confirmButton: {
    marginBottom: 12,
  },
  cancelButton: {
    // Styles applied inline
  },
});