import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  Linking,
  Share,
  Image,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import QRCode from 'react-native-qrcode-svg';
import * as Calendar from 'expo-calendar';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { SafeArea } from '../components/SafeArea';
import { formatters } from '../utils/formatters';
import { ApiClient } from '../services/api/ApiClient';

interface Reservation {
  id: string;
  confirmationNumber: string;
  status: string;
  provider: string;
  venueName: string;
  venueAddress?: string;
  venuePhone?: string;
  dateTime: string;
  partySize: number;
  specialRequests?: string;
  customerInfo: {
    firstName: string;
    lastName: string;
    email: string;
    phone: string;
  };
  cancellationPolicy?: string;
  modificationAllowed: boolean;
  cancellationDeadline?: string;
}

export const ReservationConfirmationScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { reservation, venue } = route.params as { reservation: Reservation; venue: any };
  const apiClient = new ApiClient();

  const [showQRCode, setShowQRCode] = useState(false);
  const [calendarPermission, setCalendarPermission] = useState(false);

  useEffect(() => {
    checkCalendarPermission();
  }, []);

  const checkCalendarPermission = async () => {
    const { status } = await Calendar.requestCalendarPermissionsAsync();
    setCalendarPermission(status === 'granted');
  };

  const handleAddToCalendar = async () => {
    if (!calendarPermission) {
      Alert.alert(
        'Calendar Permission',
        'Please allow calendar access to add this reservation.'
      );
      return;
    }

    try {
      const calendars = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
      const defaultCalendar = calendars.find(
        (cal) => cal.source.name === 'Default' || cal.isPrimary
      );

      if (!defaultCalendar) {
        Alert.alert('Error', 'No calendar found.');
        return;
      }

      const reservationDate = new Date(reservation.dateTime);
      const endDate = new Date(reservationDate);
      endDate.setHours(endDate.getHours() + 2); // Assume 2-hour reservation

      await Calendar.createEventAsync(defaultCalendar.id, {
        title: `Reservation at ${reservation.venueName}`,
        startDate: reservationDate,
        endDate: endDate,
        location: reservation.venueAddress || venue.address,
        notes: `Confirmation #: ${reservation.confirmationNumber}\nParty size: ${reservation.partySize}\n${reservation.specialRequests ? `Special requests: ${reservation.specialRequests}` : ''}`,
        alarms: [{ relativeOffset: -60 }], // 1 hour before
      });

      Alert.alert('Success', 'Reservation added to your calendar!');
    } catch (error) {
      console.error('Calendar error:', error);
      Alert.alert('Error', 'Unable to add to calendar.');
    }
  };

  const handleShare = async () => {
    try {
      const message = `My reservation at ${reservation.venueName}\n` +
        `Date: ${formatters.formatDate(new Date(reservation.dateTime))}\n` +
        `Time: ${formatters.formatTime(new Date(reservation.dateTime))}\n` +
        `Party size: ${reservation.partySize} guests\n` +
        `Confirmation #: ${reservation.confirmationNumber}`;

      await Share.share({
        message,
        title: 'Restaurant Reservation',
      });
    } catch (error) {
      console.error('Share error:', error);
    }
  };

  const handleDirections = () => {
    if (venue.latitude && venue.longitude) {
      const url = Platform.select({
        ios: `maps://app?daddr=${venue.latitude},${venue.longitude}`,
        android: `google.navigation:q=${venue.latitude},${venue.longitude}`,
      });
      
      if (url) {
        Linking.openURL(url).catch(() => {
          Alert.alert('Error', 'Unable to open maps.');
        });
      }
    }
  };

  const handleCallRestaurant = () => {
    if (reservation.venuePhone) {
      Linking.openURL(`tel:${reservation.venuePhone}`);
    }
  };

  const handleModifyReservation = () => {
    navigation.navigate('ModificationFlow', { reservation });
  };

  const handleCancelReservation = async () => {
    Alert.alert(
      'Cancel Reservation',
      'Are you sure you want to cancel this reservation?',
      [
        { text: 'No', style: 'cancel' },
        {
          text: 'Yes, Cancel',
          style: 'destructive',
          onPress: async () => {
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
            }
          },
        },
      ]
    );
  };

  const reservationDate = new Date(reservation.dateTime);
  const canModify = reservation.modificationAllowed && 
    new Date() < new Date(reservation.cancellationDeadline || reservation.dateTime);

  return (
    <SafeArea>
      <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Ionicons name="checkmark-circle" size={80} color="#4CAF50" />
          <Text style={styles.successTitle}>Reservation Confirmed!</Text>
          <Text style={styles.confirmationNumber}>
            Confirmation #{reservation.confirmationNumber}
          </Text>
        </View>

        <Card style={styles.detailsCard}>
          <View style={styles.venueSection}>
            {venue.imageUrl && (
              <Image source={{ uri: venue.imageUrl }} style={styles.venueImage} />
            )}
            <View style={styles.venueInfo}>
              <Text style={styles.venueName}>{reservation.venueName}</Text>
              {reservation.venueAddress && (
                <Text style={styles.venueAddress}>{reservation.venueAddress}</Text>
              )}
            </View>
          </View>

          <View style={styles.detailRow}>
            <Ionicons name="calendar" size={20} color="#666" />
            <Text style={styles.detailText}>
              {formatters.formatDate(reservationDate)}
            </Text>
          </View>

          <View style={styles.detailRow}>
            <Ionicons name="time" size={20} color="#666" />
            <Text style={styles.detailText}>
              {formatters.formatTime(reservationDate)}
            </Text>
          </View>

          <View style={styles.detailRow}>
            <Ionicons name="people" size={20} color="#666" />
            <Text style={styles.detailText}>
              {reservation.partySize} {reservation.partySize === 1 ? 'guest' : 'guests'}
            </Text>
          </View>

          {reservation.specialRequests && (
            <View style={styles.specialRequestsSection}>
              <Text style={styles.sectionTitle}>Special Requests</Text>
              <Text style={styles.specialRequestsText}>
                {reservation.specialRequests}
              </Text>
            </View>
          )}
        </Card>

        <View style={styles.actionsContainer}>
          <TouchableOpacity style={styles.actionButton} onPress={handleAddToCalendar}>
            <Ionicons name="calendar-outline" size={24} color="#007AFF" />
            <Text style={styles.actionText}>Add to Calendar</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.actionButton} onPress={handleShare}>
            <Ionicons name="share-outline" size={24} color="#007AFF" />
            <Text style={styles.actionText}>Share</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.actionButton} onPress={handleDirections}>
            <Ionicons name="navigate-outline" size={24} color="#007AFF" />
            <Text style={styles.actionText}>Get Directions</Text>
          </TouchableOpacity>

          {reservation.venuePhone && (
            <TouchableOpacity style={styles.actionButton} onPress={handleCallRestaurant}>
              <Ionicons name="call-outline" size={24} color="#007AFF" />
              <Text style={styles.actionText}>Call Restaurant</Text>
            </TouchableOpacity>
          )}
        </View>

        <Card style={styles.qrCard}>
          <TouchableOpacity
            style={styles.qrHeader}
            onPress={() => setShowQRCode(!showQRCode)}
          >
            <Text style={styles.qrTitle}>Show QR Code</Text>
            <Ionicons
              name={showQRCode ? 'chevron-up' : 'chevron-down'}
              size={24}
              color="#666"
            />
          </TouchableOpacity>
          
          {showQRCode && (
            <View style={styles.qrContainer}>
              <QRCode
                value={`roadtrip-reservation:${reservation.id}:${reservation.confirmationNumber}`}
                size={200}
              />
              <Text style={styles.qrHint}>Show this at the restaurant</Text>
            </View>
          )}
        </Card>

        {canModify && (
          <View style={styles.modifySection}>
            <Button
              title="Modify Reservation"
              onPress={handleModifyReservation}
              variant="outline"
              style={styles.modifyButton}
            />
            <Button
              title="Cancel Reservation"
              onPress={handleCancelReservation}
              variant="outline"
              style={[styles.modifyButton, styles.cancelButton]}
            />
          </View>
        )}

        {reservation.cancellationPolicy && (
          <View style={styles.policySection}>
            <Text style={styles.policyTitle}>Cancellation Policy</Text>
            <Text style={styles.policyText}>{reservation.cancellationPolicy}</Text>
          </View>
        )}

        <Button
          title="View All Reservations"
          onPress={() => navigation.navigate('MyReservationsScreen')}
          style={styles.viewAllButton}
        />

        <TouchableOpacity
          style={styles.homeButton}
          onPress={() => navigation.navigate('Home')}
        >
          <Text style={styles.homeButtonText}>Back to Home</Text>
        </TouchableOpacity>
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
    alignItems: 'center',
    padding: 24,
    backgroundColor: 'white',
  },
  successTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    marginTop: 16,
    marginBottom: 8,
  },
  confirmationNumber: {
    fontSize: 16,
    color: '#666',
  },
  detailsCard: {
    margin: 16,
    padding: 16,
  },
  venueSection: {
    flexDirection: 'row',
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
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
  venueAddress: {
    fontSize: 14,
    color: '#666',
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  detailText: {
    fontSize: 16,
    marginLeft: 12,
  },
  specialRequestsSection: {
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    marginBottom: 8,
  },
  specialRequestsText: {
    fontSize: 14,
    color: '#333',
  },
  actionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  actionButton: {
    width: '50%',
    alignItems: 'center',
    paddingVertical: 16,
  },
  actionText: {
    fontSize: 14,
    color: '#007AFF',
    marginTop: 8,
  },
  qrCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
  },
  qrHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  qrTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  qrContainer: {
    alignItems: 'center',
    marginTop: 16,
  },
  qrHint: {
    fontSize: 14,
    color: '#666',
    marginTop: 12,
  },
  modifySection: {
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  modifyButton: {
    marginBottom: 12,
  },
  cancelButton: {
    borderColor: '#FF3B30',
  },
  policySection: {
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  policyTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    marginBottom: 8,
  },
  policyText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  viewAllButton: {
    marginHorizontal: 16,
    marginBottom: 12,
  },
  homeButton: {
    alignItems: 'center',
    paddingVertical: 16,
    marginBottom: 24,
  },
  homeButtonText: {
    fontSize: 16,
    color: '#007AFF',
  },
});