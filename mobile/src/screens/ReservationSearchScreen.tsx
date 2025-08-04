import React, { useState, useEffect, useCallback } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Image,
  Alert,
  Platform,
  KeyboardAvoidingView,
} from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { ApiClient } from '../services/api/ApiClient';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { SafeArea } from '../components/SafeArea';
import { formatters } from '../utils/formatters';

interface SearchFilters {
  location: { lat: number; lng: number } | null;
  date: Date;
  time: Date;
  partySize: number;
  cuisine?: string;
  priceRange?: string;
  amenities?: string[];
}

interface SearchResult {
  provider: string;
  venueId: string;
  name: string;
  cuisine: string;
  rating: number;
  priceRange: string;
  distance: number;
  availableTimes: string[];
  imageUrl?: string;
  description?: string;
  amenities?: string[];
}

export const ReservationSearchScreen: React.FC = () => {
  const navigation = useNavigation();
  const apiClient = new ApiClient();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({
    location: null,
    date: new Date(),
    time: new Date(),
    partySize: 2,
  });
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showTimePicker, setShowTimePicker] = useState(false);
  const [selectedCuisines, setSelectedCuisines] = useState<string[]>([]);
  const [priceRange, setPriceRange] = useState<number[]>([1, 4]);

  const cuisineOptions = [
    'Italian', 'Mexican', 'Asian', 'American', 'French',
    'Mediterranean', 'Indian', 'Japanese', 'Thai', 'Seafood'
  ];

  const amenityOptions = [
    'Outdoor Seating', 'Private Dining', 'Wheelchair Accessible',
    'Parking', 'Bar', 'Live Music', 'Vegan Options', 'Kids Menu'
  ];

  useEffect(() => {
    // Get current location
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setFilters(prev => ({
          ...prev,
          location: {
            lat: position.coords.latitude,
            lng: position.coords.longitude
          }
        }));
      },
      (error) => {
        logger.error('Location error:', error);
      }
    );
  }, []);

  const handleSearch = useCallback(async () => {
    if (!filters.location) {
      Alert.alert('Location Required', 'Please enable location services to search for restaurants.');
      return;
    }

    setLoading(true);
    try {
      const response = await apiClient.post('/api/reservations/search', {
        query: searchQuery,
        location: filters.location,
        date: filters.date.toISOString(),
        time: filters.time.toISOString(),
        partySize: filters.partySize,
        cuisines: selectedCuisines,
        priceRange: `${priceRange[0]}-${priceRange[1]}`,
        amenities: filters.amenities
      });
      
      setSearchResults(response.data.results);
    } catch (error) {
      logger.error('Search error:', error);
      Alert.alert('Search Error', 'Unable to search for restaurants. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, filters, selectedCuisines, priceRange]);

  const handleSelectVenue = (result: SearchResult) => {
    navigation.navigate('BookingFlowWizard', {
      venue: result,
      initialDate: filters.date,
      initialTime: filters.time,
      initialPartySize: filters.partySize
    });
  };

  const renderSearchResult = ({ item }: { item: SearchResult }) => (
    <Card style={styles.resultCard}>
      <TouchableOpacity onPress={() => handleSelectVenue(item)}>
        <View style={styles.resultHeader}>
          {item.imageUrl && (
            <Image source={{ uri: item.imageUrl }} style={styles.venueImage} />
          )}
          <View style={styles.resultInfo}>
            <Text style={styles.venueName}>{item.name}</Text>
            <Text style={styles.cuisineText}>{item.cuisine}</Text>
            <View style={styles.ratingRow}>
              <Ionicons name="star" size={16} color="#FFD700" />
              <Text style={styles.ratingText}>{item.rating.toFixed(1)}</Text>
              <Text style={styles.priceText}>{'$'.repeat(parseInt(item.priceRange))}</Text>
            </View>
            <Text style={styles.distanceText}>{item.distance.toFixed(1)} miles away</Text>
          </View>
        </View>
        
        {item.availableTimes.length > 0 && (
          <View style={styles.timeSlotsContainer}>
            <Text style={styles.timeSlotsLabel}>Available times:</Text>
            <View style={styles.timeSlots}>
              {item.availableTimes.slice(0, 4).map((time, index) => (
                <TouchableOpacity
                  key={index}
                  style={styles.timeSlot}
                  onPress={() => {
                    const [hours, minutes] = time.split(':');
                    const selectedTime = new Date(filters.date);
                    selectedTime.setHours(parseInt(hours), parseInt(minutes));
                    setFilters(prev => ({ ...prev, time: selectedTime }));
                    handleSelectVenue(item);
                  }}
                >
                  <Text style={styles.timeSlotText}>{time}</Text>
                </TouchableOpacity>
              ))}
              {item.availableTimes.length > 4 && (
                <Text style={styles.moreTimesText}>+{item.availableTimes.length - 4} more</Text>
              )}
            </View>
          </View>
        )}
        
        <View style={styles.providerBadge}>
          <Text style={styles.providerText}>via {item.provider}</Text>
        </View>
      </TouchableOpacity>
    </Card>
  );

  return (
    <SafeArea>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <View style={styles.header}>
          <Text style={styles.title}>Find & Book Restaurants</Text>
          
          <View style={styles.searchBar}>
            <Ionicons name="search" size={20} color="#666" style={styles.searchIcon} />
            <TextInput
              style={styles.searchInput}
              placeholder="Search restaurants, cuisines..."
              value={searchQuery}
              onChangeText={setSearchQuery}
              onSubmitEditing={handleSearch}
            />
          </View>
        </View>

        <View style={styles.filtersContainer}>
          <View style={styles.filterRow}>
            <TouchableOpacity
              style={styles.filterButton}
              onPress={() => setShowDatePicker(true)}
            >
              <Ionicons name="calendar" size={20} color="#007AFF" />
              <Text style={styles.filterText}>
                {formatters.formatDate(filters.date)}
              </Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.filterButton}
              onPress={() => setShowTimePicker(true)}
            >
              <Ionicons name="time" size={20} color="#007AFF" />
              <Text style={styles.filterText}>
                {formatters.formatTime(filters.time)}
              </Text>
            </TouchableOpacity>
            
            <View style={styles.partySizeContainer}>
              <TouchableOpacity
                onPress={() => setFilters(prev => ({ 
                  ...prev, 
                  partySize: Math.max(1, prev.partySize - 1) 
                }))}
                style={styles.partySizeButton}
              >
                <Ionicons name="remove-circle" size={24} color="#007AFF" />
              </TouchableOpacity>
              <Text style={styles.partySizeText}>{filters.partySize} guests</Text>
              <TouchableOpacity
                onPress={() => setFilters(prev => ({ 
                  ...prev, 
                  partySize: Math.min(20, prev.partySize + 1) 
                }))}
                style={styles.partySizeButton}
              >
                <Ionicons name="add-circle" size={24} color="#007AFF" />
              </TouchableOpacity>
            </View>
          </View>

          <View style={styles.cuisineFilters}>
            <Text style={styles.filterLabel}>Cuisine</Text>
            <FlatList
              horizontal
              showsHorizontalScrollIndicator={false}
              data={cuisineOptions}
              keyExtractor={(item) => item}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    styles.cuisineChip,
                    selectedCuisines.includes(item) && styles.cuisineChipSelected
                  ]}
                  onPress={() => {
                    setSelectedCuisines(prev =>
                      prev.includes(item)
                        ? prev.filter(c => c !== item)
                        : [...prev, item]
                    );
                  }}
                >
                  <Text style={[
                    styles.cuisineChipText,
                    selectedCuisines.includes(item) && styles.cuisineChipTextSelected
                  ]}>
                    {item}
                  </Text>
                </TouchableOpacity>
              )}
            />
          </View>

          <Button
            title="Search"
            onPress={handleSearch}
            loading={loading}
            style={styles.searchButton}
          />
        </View>

        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#007AFF" />
            <Text style={styles.loadingText}>Searching restaurants...</Text>
          </View>
        ) : (
          <FlatList
            data={searchResults}
            keyExtractor={(item) => `${item.provider}-${item.venueId}`}
            renderItem={renderSearchResult}
            contentContainerStyle={styles.resultsContainer}
            ListEmptyComponent={
              searchResults.length === 0 && searchQuery ? (
                <View style={styles.emptyContainer}>
                  <Ionicons name="restaurant" size={48} color="#ccc" />
                  <Text style={styles.emptyText}>No restaurants found</Text>
                  <Text style={styles.emptySubtext}>Try adjusting your filters</Text>
                </View>
              ) : null
            }
          />
        )}

        {showDatePicker && (
          <DateTimePicker
            value={filters.date}
            mode="date"
            minimumDate={new Date()}
            onChange={(event, date) => {
              setShowDatePicker(false);
              if (date) {
                setFilters(prev => ({ ...prev, date }));
              }
            }}
          />
        )}

        {showTimePicker && (
          <DateTimePicker
            value={filters.time}
            mode="time"
            onChange={(event, time) => {
              setShowTimePicker(false);
              if (time) {
                setFilters(prev => ({ ...prev, time }));
              }
            }}
          />
        )}
      </KeyboardAvoidingView>
    </SafeArea>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: 'white',
    padding: 16,
    paddingTop: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 5,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f0f0f0',
    borderRadius: 12,
    paddingHorizontal: 12,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    height: 44,
    fontSize: 16,
  },
  filtersContainer: {
    backgroundColor: 'white',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  filterRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  filterButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f0f0f0',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  filterText: {
    marginLeft: 8,
    fontSize: 14,
    color: '#333',
  },
  partySizeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  partySizeButton: {
    padding: 4,
  },
  partySizeText: {
    marginHorizontal: 12,
    fontSize: 16,
    fontWeight: '500',
  },
  cuisineFilters: {
    marginBottom: 16,
  },
  filterLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
    color: '#666',
  },
  cuisineChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#f0f0f0',
    marginRight: 8,
  },
  cuisineChipSelected: {
    backgroundColor: '#007AFF',
  },
  cuisineChipText: {
    fontSize: 14,
    color: '#333',
  },
  cuisineChipTextSelected: {
    color: 'white',
  },
  searchButton: {
    marginTop: 8,
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
  resultsContainer: {
    padding: 16,
  },
  resultCard: {
    marginBottom: 16,
    padding: 16,
  },
  resultHeader: {
    flexDirection: 'row',
  },
  venueImage: {
    width: 80,
    height: 80,
    borderRadius: 8,
    marginRight: 12,
  },
  resultInfo: {
    flex: 1,
  },
  venueName: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  cuisineText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  ratingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  ratingText: {
    marginLeft: 4,
    marginRight: 12,
    fontSize: 14,
    fontWeight: '500',
  },
  priceText: {
    fontSize: 14,
    color: '#00AA00',
  },
  distanceText: {
    fontSize: 12,
    color: '#666',
  },
  timeSlotsContainer: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  timeSlotsLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
    color: '#666',
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
  moreTimesText: {
    alignSelf: 'center',
    color: '#007AFF',
    fontSize: 14,
    marginLeft: 8,
  },
  providerBadge: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: '#f0f0f0',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  providerText: {
    fontSize: 11,
    color: '#666',
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: 48,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '500',
    marginTop: 16,
    color: '#666',
  },
  emptySubtext: {
    fontSize: 14,
    marginTop: 8,
    color: '#999',
  },
});