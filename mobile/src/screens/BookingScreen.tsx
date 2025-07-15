/**
 * Booking Screen
 * 
 * Provides visual booking interface that works seamlessly with voice
 * Users can start booking via voice and complete visually when stopped
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  SafeAreaView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';
import apiClient from '../services/apiClient';
import { format } from 'date-fns';

interface BookingItem {
  id: string;
  type: 'hotel' | 'restaurant' | 'activity';
  name: string;
  rating: number;
  price: number;
  image_url?: string;
  description: string;
  availability: boolean;
  booking_details?: any;
}

interface RouteParams {
  bookingData?: any;
  fromVoice?: boolean;
}

export const BookingScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const params = route.params as RouteParams;
  
  const [bookingType, setBookingType] = useState<'hotel' | 'restaurant' | 'activity'>('hotel');
  const [bookingItems, setBookingItems] = useState<BookingItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<BookingItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [bookingInProgress, setBookingInProgress] = useState(false);

  useEffect(() => {
    // If coming from voice with data, populate it
    if (params?.bookingData) {
      const { type, items } = params.bookingData;
      setBookingType(type);
      setBookingItems(items);
      
      // If voice already selected an item, show it
      if (params.bookingData.selected) {
        setSelectedItem(params.bookingData.selected);
      }
    } else {
      // Load default recommendations
      loadRecommendations();
    }
  }, [params]);

  const loadRecommendations = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get(`/api/booking/recommendations/${bookingType}`);
      setBookingItems(response.data.items);
    } catch (error) {
      console.error('Failed to load recommendations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleBooking = async (item: BookingItem) => {
    setBookingInProgress(true);
    
    try {
      const response = await apiClient.post('/api/booking/create', {
        item_id: item.id,
        type: item.type,
        booking_details: item.booking_details || {},
      });

      if (response.data.success) {
        Alert.alert(
          'Booking Confirmed!',
          `Your ${item.type} booking at ${item.name} has been confirmed.`,
          [
            {
              text: 'View Details',
              onPress: () => navigation.navigate('BookingConfirmation', {
                booking: response.data.booking
              }),
            },
            { text: 'OK' }
          ]
        );
      }
    } catch (error) {
      Alert.alert('Booking Failed', 'Unable to complete your booking. Please try again.');
    } finally {
      setBookingInProgress(false);
    }
  };

  const renderBookingItem = (item: BookingItem) => (
    <TouchableOpacity
      key={item.id}
      style={styles.itemCard}
      onPress={() => setSelectedItem(item)}
      activeOpacity={0.8}
    >
      {item.image_url && (
        <Image source={{ uri: item.image_url }} style={styles.itemImage} />
      )}
      
      <View style={styles.itemContent}>
        <View style={styles.itemHeader}>
          <Text style={styles.itemName} numberOfLines={1}>{item.name}</Text>
          <View style={styles.ratingContainer}>
            <MaterialIcons name="star" size={16} color="#FFD700" />
            <Text style={styles.rating}>{item.rating}</Text>
          </View>
        </View>
        
        <Text style={styles.itemDescription} numberOfLines={2}>
          {item.description}
        </Text>
        
        <View style={styles.itemFooter}>
          <Text style={styles.price}>
            ${item.price}
            {item.type === 'hotel' && '/night'}
            {item.type === 'restaurant' && '/person'}
          </Text>
          
          {item.availability ? (
            <View style={styles.availableIndicator}>
              <MaterialIcons name="check-circle" size={16} color="#4CAF50" />
              <Text style={styles.availableText}>Available</Text>
            </View>
          ) : (
            <Text style={styles.unavailableText}>Not Available</Text>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );

  const renderSelectedItemDetails = () => {
    if (!selectedItem) return null;

    return (
      <View style={styles.detailsContainer}>
        <View style={styles.detailsHeader}>
          <Text style={styles.detailsTitle}>{selectedItem.name}</Text>
          <TouchableOpacity
            onPress={() => setSelectedItem(null)}
            style={styles.closeButton}
          >
            <MaterialIcons name="close" size={24} color="#666" />
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.detailsContent}>
          {selectedItem.image_url && (
            <Image 
              source={{ uri: selectedItem.image_url }} 
              style={styles.detailsImage}
            />
          )}

          <View style={styles.detailsInfo}>
            <View style={styles.detailRow}>
              <MaterialIcons name="star" size={20} color="#FFD700" />
              <Text style={styles.detailText}>
                {selectedItem.rating} rating
              </Text>
            </View>

            <View style={styles.detailRow}>
              <MaterialIcons name="attach-money" size={20} color="#4CAF50" />
              <Text style={styles.detailText}>
                ${selectedItem.price}
                {selectedItem.type === 'hotel' && ' per night'}
                {selectedItem.type === 'restaurant' && ' per person'}
              </Text>
            </View>

            <Text style={styles.detailDescription}>
              {selectedItem.description}
            </Text>

            {selectedItem.booking_details && (
              <View style={styles.bookingDetails}>
                <Text style={styles.bookingDetailsTitle}>Booking Details</Text>
                {Object.entries(selectedItem.booking_details).map(([key, value]) => (
                  <View key={key} style={styles.detailRow}>
                    <Text style={styles.detailLabel}>{key}:</Text>
                    <Text style={styles.detailValue}>{String(value)}</Text>
                  </View>
                ))}
              </View>
            )}
          </View>

          <TouchableOpacity
            style={[
              styles.bookButton,
              !selectedItem.availability && styles.bookButtonDisabled
            ]}
            onPress={() => handleBooking(selectedItem)}
            disabled={!selectedItem.availability || bookingInProgress}
          >
            {bookingInProgress ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <MaterialIcons name="check" size={24} color="#FFFFFF" />
                <Text style={styles.bookButtonText}>
                  Confirm Booking
                </Text>
              </>
            )}
          </TouchableOpacity>
        </ScrollView>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backButton}
        >
          <MaterialIcons name="arrow-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Book Your Experience</Text>
        {params?.fromVoice && (
          <View style={styles.voiceIndicator}>
            <MaterialIcons name="mic" size={20} color="#007AFF" />
          </View>
        )}
      </View>

      {/* Type Selector */}
      <View style={styles.typeSelector}>
        {(['hotel', 'restaurant', 'activity'] as const).map((type) => (
          <TouchableOpacity
            key={type}
            style={[
              styles.typeButton,
              bookingType === type && styles.typeButtonActive
            ]}
            onPress={() => {
              setBookingType(type);
              loadRecommendations();
            }}
          >
            <MaterialIcons
              name={
                type === 'hotel' ? 'hotel' :
                type === 'restaurant' ? 'restaurant' :
                'local-activity'
              }
              size={24}
              color={bookingType === type ? '#FFFFFF' : '#666'}
            />
            <Text
              style={[
                styles.typeButtonText,
                bookingType === type && styles.typeButtonTextActive
              ]}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}s
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Finding best options...</Text>
        </View>
      ) : selectedItem ? (
        renderSelectedItemDetails()
      ) : (
        <ScrollView style={styles.itemsList}>
          {bookingItems.map(renderBookingItem)}
          {bookingItems.length === 0 && (
            <View style={styles.emptyContainer}>
              <MaterialIcons name="search" size={48} color="#CCC" />
              <Text style={styles.emptyText}>
                No {bookingType}s available at this location
              </Text>
            </View>
          )}
        </ScrollView>
      )}
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
    padding: 16,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  backButton: {
    padding: 4,
  },
  headerTitle: {
    flex: 1,
    fontSize: 20,
    fontWeight: '600',
    color: '#333',
    marginLeft: 16,
  },
  voiceIndicator: {
    backgroundColor: '#E3F2FD',
    borderRadius: 12,
    padding: 6,
  },
  typeSelector: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: '#FFFFFF',
    gap: 12,
  },
  typeButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    borderRadius: 12,
    backgroundColor: '#F5F5F5',
    gap: 8,
  },
  typeButtonActive: {
    backgroundColor: '#007AFF',
  },
  typeButtonText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
  },
  typeButtonTextActive: {
    color: '#FFFFFF',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  itemsList: {
    flex: 1,
    padding: 16,
  },
  itemCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    marginBottom: 16,
    overflow: 'hidden',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  itemImage: {
    width: '100%',
    height: 150,
  },
  itemContent: {
    padding: 16,
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  itemName: {
    flex: 1,
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginRight: 12,
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  rating: {
    fontSize: 14,
    color: '#666',
  },
  itemDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12,
  },
  itemFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  price: {
    fontSize: 18,
    fontWeight: '600',
    color: '#007AFF',
  },
  availableIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  availableText: {
    fontSize: 14,
    color: '#4CAF50',
  },
  unavailableText: {
    fontSize: 14,
    color: '#F44336',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    marginTop: 16,
    fontSize: 16,
    color: '#999',
  },
  detailsContainer: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  detailsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  detailsTitle: {
    flex: 1,
    fontSize: 20,
    fontWeight: '600',
    color: '#333',
    marginRight: 16,
  },
  closeButton: {
    padding: 4,
  },
  detailsContent: {
    flex: 1,
  },
  detailsImage: {
    width: '100%',
    height: 200,
  },
  detailsInfo: {
    padding: 20,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 12,
  },
  detailText: {
    fontSize: 16,
    color: '#333',
  },
  detailDescription: {
    fontSize: 16,
    color: '#666',
    lineHeight: 24,
    marginTop: 16,
  },
  bookingDetails: {
    marginTop: 24,
    padding: 16,
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
  },
  bookingDetailsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  detailLabel: {
    fontSize: 14,
    color: '#666',
    textTransform: 'capitalize',
  },
  detailValue: {
    fontSize: 14,
    color: '#333',
    fontWeight: '500',
  },
  bookButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#007AFF',
    margin: 20,
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  bookButtonDisabled: {
    backgroundColor: '#CCC',
  },
  bookButtonText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});