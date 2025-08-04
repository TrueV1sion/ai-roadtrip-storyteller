import React, { useState, useEffect, useCallback } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Image,
  Alert,
} from 'react-native';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { ApiClient } from '../services/api/ApiClient';
import { Card } from '../components/Card';
import { SafeArea } from '../components/SafeArea';
import { formatters } from '../utils/formatters';

interface Reservation {
  id: string;
  confirmationNumber: string;
  status: 'confirmed' | 'cancelled' | 'completed' | 'no_show';
  provider: string;
  venueName: string;
  venueImage?: string;
  venueAddress?: string;
  dateTime: string;
  partySize: number;
  specialRequests?: string;
  modificationAllowed: boolean;
  cancellationDeadline?: string;
}

const TAB_OPTIONS = [
  { id: 'upcoming', label: 'Upcoming' },
  { id: 'past', label: 'Past' },
  { id: 'cancelled', label: 'Cancelled' },
];

export const MyReservationsScreen: React.FC = () => {
  const navigation = useNavigation();
  const apiClient = new ApiClient();

  const [activeTab, setActiveTab] = useState('upcoming');
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchReservations = useCallback(async (showLoader = true) => {
    if (showLoader) setLoading(true);
    try {
      const response = await apiClient.get('/api/reservations/my-reservations');
      setReservations(response.data.reservations);
    } catch (error) {
      logger.error('Error fetching reservations:', error);
      Alert.alert('Error', 'Unable to load reservations. Please try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchReservations();
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchReservations(false);
    }, [])
  );

  const handleRefresh = () => {
    setRefreshing(true);
    fetchReservations(false);
  };

  const getFilteredReservations = () => {
    const now = new Date();
    return reservations.filter((reservation) => {
      const reservationDate = new Date(reservation.dateTime);
      
      switch (activeTab) {
        case 'upcoming':
          return reservation.status === 'confirmed' && reservationDate >= now;
        case 'past':
          return (
            (reservation.status === 'completed' || 
             (reservation.status === 'confirmed' && reservationDate < now))
          );
        case 'cancelled':
          return reservation.status === 'cancelled' || reservation.status === 'no_show';
        default:
          return false;
      }
    }).sort((a, b) => {
      const dateA = new Date(a.dateTime).getTime();
      const dateB = new Date(b.dateTime).getTime();
      return activeTab === 'upcoming' ? dateA - dateB : dateB - dateA;
    });
  };

  const handleViewReservation = (reservation: Reservation) => {
    navigation.navigate('ReservationDetailsScreen', { reservation });
  };

  const handleModifyReservation = (reservation: Reservation) => {
    const now = new Date();
    const deadlineDate = reservation.cancellationDeadline 
      ? new Date(reservation.cancellationDeadline)
      : new Date(reservation.dateTime);

    if (!reservation.modificationAllowed || now >= deadlineDate) {
      Alert.alert(
        'Cannot Modify',
        'This reservation can no longer be modified. Please contact the restaurant directly.'
      );
      return;
    }

    navigation.navigate('ModificationFlow', { reservation });
  };

  const handleCancelReservation = async (reservation: Reservation) => {
    const now = new Date();
    const deadlineDate = reservation.cancellationDeadline 
      ? new Date(reservation.cancellationDeadline)
      : new Date(reservation.dateTime);

    if (!reservation.modificationAllowed || now >= deadlineDate) {
      Alert.alert(
        'Cannot Cancel',
        'This reservation can no longer be cancelled. Please contact the restaurant directly.'
      );
      return;
    }

    Alert.alert(
      'Cancel Reservation',
      `Are you sure you want to cancel your reservation at ${reservation.venueName}?`,
      [
        { text: 'No', style: 'cancel' },
        {
          text: 'Yes, Cancel',
          style: 'destructive',
          onPress: async () => {
            try {
              await apiClient.post(`/api/reservations/${reservation.id}/cancel`);
              Alert.alert('Success', 'Your reservation has been cancelled.');
              fetchReservations(false);
            } catch (error) {
              logger.error('Cancellation error:', error);
              Alert.alert(
                'Cancellation Failed',
                'Unable to cancel reservation. Please try again.'
              );
            }
          },
        },
      ]
    );
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'confirmed':
        return '#4CAF50';
      case 'cancelled':
      case 'no_show':
        return '#FF3B30';
      case 'completed':
        return '#666';
      default:
        return '#666';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'confirmed':
        return 'Confirmed';
      case 'cancelled':
        return 'Cancelled';
      case 'no_show':
        return 'No Show';
      case 'completed':
        return 'Completed';
      default:
        return status;
    }
  };

  const renderReservation = ({ item }: { item: Reservation }) => {
    const reservationDate = new Date(item.dateTime);
    const isPast = reservationDate < new Date();
    const canModify = item.modificationAllowed && 
      item.status === 'confirmed' && 
      !isPast &&
      (item.cancellationDeadline ? new Date() < new Date(item.cancellationDeadline) : true);

    return (
      <Card style={styles.reservationCard}>
        <TouchableOpacity
          onPress={() => handleViewReservation(item)}
          activeOpacity={0.7}
        >
          <View style={styles.reservationHeader}>
            {item.venueImage && (
              <Image source={{ uri: item.venueImage }} style={styles.venueImage} />
            )}
            <View style={styles.reservationInfo}>
              <Text style={styles.venueName}>{item.venueName}</Text>
              <View style={styles.dateTimeRow}>
                <Ionicons name="calendar-outline" size={14} color="#666" />
                <Text style={styles.dateTimeText}>
                  {formatters.formatDate(reservationDate)}
                </Text>
                <Ionicons name="time-outline" size={14} color="#666" style={{ marginLeft: 12 }} />
                <Text style={styles.dateTimeText}>
                  {formatters.formatTime(reservationDate)}
                </Text>
              </View>
              <View style={styles.detailRow}>
                <Ionicons name="people-outline" size={14} color="#666" />
                <Text style={styles.detailText}>
                  {item.partySize} {item.partySize === 1 ? 'guest' : 'guests'}
                </Text>
              </View>
            </View>
            <View style={styles.statusContainer}>
              <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) }]}>
                <Text style={styles.statusText}>{getStatusText(item.status)}</Text>
              </View>
            </View>
          </View>

          <View style={styles.reservationFooter}>
            <Text style={styles.confirmationText}>
              Confirmation #{item.confirmationNumber}
            </Text>
            <Text style={styles.providerText}>via {item.provider}</Text>
          </View>

          {canModify && (
            <View style={styles.actionButtons}>
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => handleModifyReservation(item)}
              >
                <Ionicons name="create-outline" size={20} color="#007AFF" />
                <Text style={styles.actionButtonText}>Modify</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.actionButton, styles.cancelActionButton]}
                onPress={() => handleCancelReservation(item)}
              >
                <Ionicons name="close-circle-outline" size={20} color="#FF3B30" />
                <Text style={[styles.actionButtonText, { color: '#FF3B30' }]}>Cancel</Text>
              </TouchableOpacity>
            </View>
          )}
        </TouchableOpacity>
      </Card>
    );
  };

  const renderEmptyState = () => {
    const emptyMessages = {
      upcoming: 'No upcoming reservations',
      past: 'No past reservations',
      cancelled: 'No cancelled reservations',
    };

    const emptyIcons = {
      upcoming: 'calendar-outline',
      past: 'time-outline',
      cancelled: 'close-circle-outline',
    };

    return (
      <View style={styles.emptyContainer}>
        <Ionicons
          name={emptyIcons[activeTab as keyof typeof emptyIcons]}
          size={64}
          color="#ccc"
        />
        <Text style={styles.emptyText}>
          {emptyMessages[activeTab as keyof typeof emptyMessages]}
        </Text>
        {activeTab === 'upcoming' && (
          <TouchableOpacity
            style={styles.searchButton}
            onPress={() => navigation.navigate('ReservationSearchScreen')}
          >
            <Text style={styles.searchButtonText}>Find Restaurants</Text>
          </TouchableOpacity>
        )}
      </View>
    );
  };

  return (
    <SafeArea>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>My Reservations</Text>
          <TouchableOpacity
            onPress={() => navigation.navigate('ReservationSearchScreen')}
            style={styles.addButton}
          >
            <Ionicons name="add-circle" size={28} color="#007AFF" />
          </TouchableOpacity>
        </View>

        <View style={styles.tabContainer}>
          {TAB_OPTIONS.map((tab) => (
            <TouchableOpacity
              key={tab.id}
              style={[
                styles.tab,
                activeTab === tab.id && styles.activeTab,
              ]}
              onPress={() => setActiveTab(tab.id)}
            >
              <Text style={[
                styles.tabText,
                activeTab === tab.id && styles.activeTabText,
              ]}>
                {tab.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#007AFF" />
          </View>
        ) : (
          <FlatList
            data={getFilteredReservations()}
            keyExtractor={(item) => item.id}
            renderItem={renderReservation}
            contentContainerStyle={styles.listContent}
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={handleRefresh}
                tintColor="#007AFF"
              />
            }
            ListEmptyComponent={renderEmptyState}
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
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  addButton: {
    padding: 4,
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: 'white',
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  tab: {
    flex: 1,
    paddingVertical: 16,
    alignItems: 'center',
  },
  activeTab: {
    borderBottomWidth: 3,
    borderBottomColor: '#007AFF',
  },
  tabText: {
    fontSize: 16,
    color: '#666',
  },
  activeTabText: {
    color: '#007AFF',
    fontWeight: '600',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  listContent: {
    padding: 16,
  },
  reservationCard: {
    marginBottom: 16,
    padding: 16,
  },
  reservationHeader: {
    flexDirection: 'row',
  },
  venueImage: {
    width: 60,
    height: 60,
    borderRadius: 8,
    marginRight: 12,
  },
  reservationInfo: {
    flex: 1,
  },
  venueName: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  dateTimeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  dateTimeText: {
    fontSize: 14,
    color: '#666',
    marginLeft: 4,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  detailText: {
    fontSize: 14,
    color: '#666',
    marginLeft: 4,
  },
  statusContainer: {
    alignItems: 'flex-end',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
  reservationFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  confirmationText: {
    fontSize: 12,
    color: '#666',
  },
  providerText: {
    fontSize: 12,
    color: '#666',
  },
  actionButtons: {
    flexDirection: 'row',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 16,
    marginRight: 12,
  },
  cancelActionButton: {
    marginLeft: 'auto',
    marginRight: 0,
  },
  actionButtonText: {
    marginLeft: 6,
    fontSize: 14,
    color: '#007AFF',
    fontWeight: '500',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 64,
  },
  emptyText: {
    fontSize: 18,
    color: '#666',
    marginTop: 16,
    marginBottom: 24,
  },
  searchButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 24,
  },
  searchButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});