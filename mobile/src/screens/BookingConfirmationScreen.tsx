/**
 * Booking Confirmation Screen
 * 
 * Shows booking details and allows users to manage their reservations
 * Integrates with voice for hands-free confirmation reading
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  Share,
  Alert,
  Linking,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';
import QRCode from 'react-native-qrcode-svg';
import * as Calendar from 'expo-calendar';
import { format } from 'date-fns';
import apiClient from '../services/apiClient';
import unifiedVoiceOrchestrator from '../services/voice/unifiedVoiceOrchestrator';

interface Booking {
  id: string;
  confirmation_number: string;
  type: 'hotel' | 'restaurant' | 'activity';
  name: string;
  address: string;
  date: string;
  time?: string;
  party_size?: number;
  nights?: number;
  total_price: number;
  status: 'confirmed' | 'pending' | 'cancelled';
  contact_phone?: string;
  contact_email?: string;
  special_requests?: string;
  cancellation_policy?: string;
}

interface RouteParams {
  booking: Booking;
}

export const BookingConfirmationScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { booking } = route.params as RouteParams;
  
  const [speakingConfirmation, setSpeakingConfirmation] = useState(false);

  useEffect(() => {
    // Optionally speak confirmation on mount
    if (booking.status === 'confirmed') {
      speakConfirmation();
    }
  }, []);

  const speakConfirmation = async () => {
    setSpeakingConfirmation(true);
    
    const confirmationText = `
      Your ${booking.type} booking is confirmed!
      ${booking.name} on ${format(new Date(booking.date), 'MMMM do')}.
      Your confirmation number is ${booking.confirmation_number}.
      I've saved all the details for you.
    `;
    
    try {
      // Use the unified voice orchestrator to speak
      await unifiedVoiceOrchestrator.updatePreferences({
        audio_priority: 'balanced'
      });
      
      // This would trigger a voice response
      // In real implementation, we'd have a method to speak without recording
      console.log('Speaking:', confirmationText);
    } catch (error) {
      console.error('Failed to speak confirmation:', error);
    } finally {
      setSpeakingConfirmation(false);
    }
  };

  const shareBooking = async () => {
    try {
      const message = `
My ${booking.type} booking:
${booking.name}
Date: ${format(new Date(booking.date), 'MMM dd, yyyy')}
${booking.time ? `Time: ${booking.time}` : ''}
Confirmation: ${booking.confirmation_number}
      `.trim();

      await Share.share({
        message,
        title: 'Booking Confirmation',
      });
    } catch (error) {
      console.error('Error sharing:', error);
    }
  };

  const addToCalendar = async () => {
    try {
      const { status } = await Calendar.requestCalendarPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Denied', 'Calendar access is required to add events.');
        return;
      }

      const calendars = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
      const defaultCalendar = calendars.find(cal => cal.isPrimary) || calendars[0];
      
      if (!defaultCalendar) {
        Alert.alert('No Calendar', 'No calendar found on device.');
        return;
      }

      const eventDetails = {
        title: `${booking.type}: ${booking.name}`,
        startDate: new Date(booking.date),
        endDate: new Date(booking.date),
        location: booking.address,
        notes: `Confirmation: ${booking.confirmation_number}`,
        calendarId: defaultCalendar.id,
      };

      await Calendar.createEventAsync(defaultCalendar.id, eventDetails);
      Alert.alert('Success', 'Added to calendar!');
    } catch (error) {
      console.error('Calendar error:', error);
      Alert.alert('Error', 'Failed to add to calendar.');
    }
  };

  const callVenue = () => {
    if (booking.contact_phone) {
      Linking.openURL(`tel:${booking.contact_phone}`);
    }
  };

  const openMaps = () => {
    const address = encodeURIComponent(booking.address);
    const url = Platform.select({
      ios: `maps://app?address=${address}`,
      android: `geo:0,0?q=${address}`,
    });
    
    Linking.openURL(url).catch(() => {
      // Fallback to Google Maps
      Linking.openURL(`https://maps.google.com/maps?q=${address}`);
    });
  };

  const cancelBooking = async () => {
    Alert.alert(
      'Cancel Booking',
      'Are you sure you want to cancel this booking?',
      [
        { text: 'No', style: 'cancel' },
        {
          text: 'Yes, Cancel',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiClient.post(`/api/booking/${booking.id}/cancel`);
              Alert.alert('Cancelled', 'Your booking has been cancelled.');
              navigation.goBack();
            } catch (error) {
              Alert.alert('Error', 'Failed to cancel booking.');
            }
          },
        },
      ]
    );
  };

  const getStatusColor = () => {
    switch (booking.status) {
      case 'confirmed': return '#4CAF50';
      case 'pending': return '#FFA500';
      case 'cancelled': return '#F44336';
      default: return '#666';
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity
            onPress={() => navigation.goBack()}
            style={styles.backButton}
          >
            <MaterialIcons name="close" size={24} color="#333" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Booking Confirmation</Text>
          <TouchableOpacity
            onPress={shareBooking}
            style={styles.shareButton}
          >
            <MaterialIcons name="share" size={24} color="#007AFF" />
          </TouchableOpacity>
        </View>

        {/* Status Banner */}
        <View style={[styles.statusBanner, { backgroundColor: getStatusColor() }]}>
          <MaterialIcons 
            name={booking.status === 'confirmed' ? 'check-circle' : 'info'} 
            size={24} 
            color="#FFFFFF" 
          />
          <Text style={styles.statusText}>
            {booking.status === 'confirmed' ? 'Booking Confirmed!' : 
             booking.status === 'pending' ? 'Booking Pending' : 'Booking Cancelled'}
          </Text>
        </View>

        {/* QR Code */}
        <View style={styles.qrContainer}>
          <QRCode
            value={booking.confirmation_number}
            size={150}
            backgroundColor="#FFFFFF"
          />
          <Text style={styles.confirmationNumber}>{booking.confirmation_number}</Text>
          <Text style={styles.qrHint}>Show this code at check-in</Text>
        </View>

        {/* Booking Details */}
        <View style={styles.detailsContainer}>
          <Text style={styles.venueName}>{booking.name}</Text>
          
          <View style={styles.detailRow}>
            <MaterialIcons name="location-on" size={20} color="#666" />
            <Text style={styles.detailText}>{booking.address}</Text>
          </View>

          <View style={styles.detailRow}>
            <MaterialIcons name="event" size={20} color="#666" />
            <Text style={styles.detailText}>
              {format(new Date(booking.date), 'EEEE, MMMM d, yyyy')}
            </Text>
          </View>

          {booking.time && (
            <View style={styles.detailRow}>
              <MaterialIcons name="access-time" size={20} color="#666" />
              <Text style={styles.detailText}>{booking.time}</Text>
            </View>
          )}

          {booking.party_size && (
            <View style={styles.detailRow}>
              <MaterialIcons name="people" size={20} color="#666" />
              <Text style={styles.detailText}>{booking.party_size} guests</Text>
            </View>
          )}

          {booking.nights && (
            <View style={styles.detailRow}>
              <MaterialIcons name="nights-stay" size={20} color="#666" />
              <Text style={styles.detailText}>{booking.nights} nights</Text>
            </View>
          )}

          <View style={styles.priceRow}>
            <Text style={styles.priceLabel}>Total Price</Text>
            <Text style={styles.priceValue}>${booking.total_price}</Text>
          </View>

          {booking.special_requests && (
            <View style={styles.specialRequests}>
              <Text style={styles.sectionTitle}>Special Requests</Text>
              <Text style={styles.specialRequestsText}>{booking.special_requests}</Text>
            </View>
          )}

          {booking.cancellation_policy && (
            <View style={styles.cancellationPolicy}>
              <Text style={styles.sectionTitle}>Cancellation Policy</Text>
              <Text style={styles.policyText}>{booking.cancellation_policy}</Text>
            </View>
          )}
        </View>

        {/* Action Buttons */}
        <View style={styles.actionsContainer}>
          <TouchableOpacity
            style={styles.actionButton}
            onPress={addToCalendar}
          >
            <MaterialIcons name="event" size={24} color="#007AFF" />
            <Text style={styles.actionButtonText}>Add to Calendar</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionButton}
            onPress={openMaps}
          >
            <MaterialIcons name="directions" size={24} color="#007AFF" />
            <Text style={styles.actionButtonText}>Get Directions</Text>
          </TouchableOpacity>

          {booking.contact_phone && (
            <TouchableOpacity
              style={styles.actionButton}
              onPress={callVenue}
            >
              <MaterialIcons name="phone" size={24} color="#007AFF" />
              <Text style={styles.actionButtonText}>Call Venue</Text>
            </TouchableOpacity>
          )}

          <TouchableOpacity
            style={styles.actionButton}
            onPress={speakConfirmation}
            disabled={speakingConfirmation}
          >
            <MaterialIcons 
              name={speakingConfirmation ? "volume-up" : "volume-down"} 
              size={24} 
              color="#007AFF" 
            />
            <Text style={styles.actionButtonText}>
              {speakingConfirmation ? "Speaking..." : "Read Aloud"}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Cancel Button */}
        {booking.status !== 'cancelled' && (
          <TouchableOpacity
            style={styles.cancelButton}
            onPress={cancelBooking}
          >
            <Text style={styles.cancelButtonText}>Cancel Booking</Text>
          </TouchableOpacity>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  backButton: {
    padding: 4,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  shareButton: {
    padding: 4,
  },
  statusBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    gap: 8,
  },
  statusText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  qrContainer: {
    alignItems: 'center',
    padding: 24,
    backgroundColor: '#FFFFFF',
  },
  confirmationNumber: {
    fontSize: 20,
    fontWeight: '600',
    color: '#333',
    marginTop: 16,
    letterSpacing: 1,
  },
  qrHint: {
    fontSize: 14,
    color: '#666',
    marginTop: 8,
  },
  detailsContainer: {
    backgroundColor: '#FFFFFF',
    marginTop: 8,
    padding: 20,
  },
  venueName: {
    fontSize: 24,
    fontWeight: '600',
    color: '#333',
    marginBottom: 16,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 12,
  },
  detailText: {
    flex: 1,
    fontSize: 16,
    color: '#333',
  },
  priceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 20,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  priceLabel: {
    fontSize: 16,
    color: '#666',
  },
  priceValue: {
    fontSize: 24,
    fontWeight: '600',
    color: '#007AFF',
  },
  specialRequests: {
    marginTop: 20,
    padding: 16,
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  specialRequestsText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  cancellationPolicy: {
    marginTop: 16,
    padding: 16,
    backgroundColor: '#FFF3E0',
    borderRadius: 12,
  },
  policyText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  actionsContainer: {
    backgroundColor: '#FFFFFF',
    marginTop: 8,
    padding: 16,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#F5F5F5',
    marginBottom: 12,
    gap: 12,
  },
  actionButtonText: {
    fontSize: 16,
    color: '#007AFF',
    fontWeight: '500',
  },
  cancelButton: {
    margin: 16,
    padding: 16,
    alignItems: 'center',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#F44336',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#F44336',
  },
});