import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  FlatList,
  Image,
  ActivityIndicator,
  Modal
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LocationData } from '../services/locationService';
import { 
  locationEnrichmentService, 
  PlaceDetails, 
  HistoricalFact, 
  WeatherData,
  LocationEnrichmentResult
} from '../services/locationEnrichmentService';

interface LocationEnrichmentCardProps {
  location: LocationData;
  onClose?: () => void;
  onPlaceSelected?: (place: PlaceDetails) => void;
}

type TabType = 'places' | 'history' | 'weather';

interface PlaceModalProps {
  place: PlaceDetails;
  visible: boolean;
  onClose: () => void;
}

const LocationEnrichmentCard: React.FC<LocationEnrichmentCardProps> = ({
  location,
  onClose,
  onPlaceSelected
}) => {
  // State
  const [activeTab, setActiveTab] = useState<TabType>('places');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<LocationEnrichmentResult | null>(null);
  const [selectedPlace, setSelectedPlace] = useState<PlaceDetails | null>(null);
  const [placeModalVisible, setPlaceModalVisible] = useState<boolean>(false);
  
  // Load location data
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Get enriched location data
        const enrichedData = await locationEnrichmentService.getEnrichedLocationInfo(location);
        setData(enrichedData);
      } catch (err) {
        console.error('Error loading location enrichment data:', err);
        setError('Failed to load location information');
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, [location]);
  
  // Handlers
  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
  };
  
  const handlePlacePress = (place: PlaceDetails) => {
    setSelectedPlace(place);
    setPlaceModalVisible(true);
    
    // Also notify parent component if callback provided
    if (onPlaceSelected) {
      onPlaceSelected(place);
    }
  };
  
  const handleCloseModal = () => {
    setPlaceModalVisible(false);
    setSelectedPlace(null);
  };
  
  // Render loading state
  if (loading) {
    return (
      <View style={styles.card}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Location Information</Text>
          {onClose && (
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <Ionicons name="close" size={24} color="#333" />
            </TouchableOpacity>
          )}
        </View>
        
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#f4511e" />
          <Text style={styles.loadingText}>Loading location information...</Text>
        </View>
      </View>
    );
  }
  
  // Render error state
  if (error || !data) {
    return (
      <View style={styles.card}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Location Information</Text>
          {onClose && (
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <Ionicons name="close" size={24} color="#333" />
            </TouchableOpacity>
          )}
        </View>
        
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle-outline" size={48} color="#f44336" />
          <Text style={styles.errorText}>{error || 'Failed to load data'}</Text>
          <TouchableOpacity 
            style={styles.retryButton}
            onPress={() => setLoading(true)} // This will trigger the useEffect again
          >
            <Text style={styles.retryButtonText}>Retry</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }
  
  // Group places by type for better organization
  const groupedPlaces = locationEnrichmentService.formatPlacesForDisplay(data.places);
  
  // Format historical facts
  const formattedFacts = locationEnrichmentService.formatHistoricalFactsForDisplay(data.historicalFacts);
  
  // Render places tab content
  const renderPlacesTab = () => {
    return (
      <ScrollView style={styles.tabContent}>
        <Text style={styles.locationName}>{data.locationName}</Text>
        
        {/* Places by category */}
        {Object.keys(groupedPlaces).map((category, index) => (
          <View key={`category-${index}`} style={styles.categorySection}>
            <Text style={styles.categoryTitle}>{category}</Text>
            
            {/* Places in this category */}
            {groupedPlaces[category].map((place) => (
              <TouchableOpacity 
                key={place.id} 
                style={styles.placeItem}
                onPress={() => handlePlacePress(place)}
              >
                <View style={styles.placeContent}>
                  <Text style={styles.placeName}>{place.name}</Text>
                  
                  <View style={styles.placeDetails}>
                    {place.distance !== undefined && (
                      <Text style={styles.placeDistance}>
                        {(place.distance / 1000).toFixed(1)} km
                      </Text>
                    )}
                    
                    {place.rating && (
                      <View style={styles.ratingContainer}>
                        <Ionicons name="star" size={14} color="#FFD700" />
                        <Text style={styles.placeRating}>{place.rating.toFixed(1)}</Text>
                      </View>
                    )}
                  </View>
                  
                  {place.tags && place.tags.length > 0 && (
                    <View style={styles.tagsContainer}>
                      {place.tags.slice(0, 3).map((tag, tagIndex) => (
                        <View key={`tag-${tagIndex}`} style={styles.tag}>
                          <Text style={styles.tagText}>{tag}</Text>
                        </View>
                      ))}
                    </View>
                  )}
                </View>
                
                <Ionicons name="chevron-forward" size={20} color="#999" />
              </TouchableOpacity>
            ))}
          </View>
        ))}
      </ScrollView>
    );
  };
  
  // Render history tab content
  const renderHistoryTab = () => {
    return (
      <ScrollView style={styles.tabContent}>
        <Text style={styles.locationName}>{data.locationName}</Text>
        
        {/* Historical facts */}
        {formattedFacts.map((fact) => (
          <View key={fact.id} style={styles.factItem}>
            <View style={styles.factHeader}>
              <Text style={styles.factTitle}>{fact.title}</Text>
              {fact.year && <Text style={styles.factYear}>{fact.year}</Text>}
            </View>
            
            <Text style={styles.factDescription}>{fact.description}</Text>
            
            {fact.source && (
              <View style={styles.factSource}>
                <Text style={styles.factSourceText}>Source: {fact.source}</Text>
                {fact.link && (
                  <TouchableOpacity>
                    <Text style={styles.factSourceLink}>View Source</Text>
                  </TouchableOpacity>
                )}
              </View>
            )}
            
            {fact.tags && fact.tags.length > 0 && (
              <View style={styles.tagsContainer}>
                {fact.tags.slice(0, 3).map((tag, tagIndex) => (
                  <View key={`tag-${tagIndex}`} style={styles.tag}>
                    <Text style={styles.tagText}>{tag}</Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        ))}
      </ScrollView>
    );
  };
  
  // Render weather tab content
  const renderWeatherTab = () => {
    if (!data.weather) {
      return (
        <View style={[styles.tabContent, styles.noDataContainer]}>
          <Ionicons name="cloud-offline-outline" size={48} color="#999" />
          <Text style={styles.noDataText}>Weather data is not available</Text>
        </View>
      );
    }
    
    // Format weather data for display
    const weatherDisplay = locationEnrichmentService.formatWeatherForDisplay(data.weather);
    
    return (
      <ScrollView style={styles.tabContent}>
        <Text style={styles.locationName}>{data.locationName}</Text>
        
        {/* Current weather */}
        <View style={styles.currentWeatherContainer}>
          <View style={styles.temperatureContainer}>
            <Text style={styles.temperature}>
              {data.weather.currentConditions.temperature}°C
            </Text>
            <Text style={styles.weatherCondition}>
              {data.weather.currentConditions.condition}
            </Text>
          </View>
          
          <View style={styles.weatherDetails}>
            {weatherDisplay.conditions.map((condition, index) => (
              <Text key={`condition-${index}`} style={styles.weatherDetailItem}>
                {condition}
              </Text>
            ))}
          </View>
        </View>
        
        {/* Forecast */}
        <View style={styles.forecastContainer}>
          <Text style={styles.forecastTitle}>5-Day Forecast</Text>
          
          {data.weather.forecast.map((day, index) => (
            <View key={`forecast-${index}`} style={styles.forecastDay}>
              <Text style={styles.forecastDayName}>{day.dayOfWeek}</Text>
              <Text style={styles.forecastDate}>{day.date}</Text>
              <Text style={styles.forecastCondition}>{day.condition}</Text>
              <View style={styles.forecastTemperature}>
                <Text style={styles.forecastHigh}>{day.high}°</Text>
                <Text style={styles.forecastLow}>{day.low}°</Text>
              </View>
              <Text style={styles.forecastPrecip}>
                {day.precipitationProbability}% chance of precipitation
              </Text>
            </View>
          ))}
        </View>
      </ScrollView>
    );
  };
  
  // Render place detail modal
  const renderPlaceModal = () => {
    if (!selectedPlace) return null;
    
    return (
      <Modal
        visible={placeModalVisible}
        animationType="slide"
        transparent={true}
        onRequestClose={handleCloseModal}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <TouchableOpacity testID="modal-close-button" onPress={handleCloseModal} style={styles.modalCloseButton}>
                <Ionicons name="arrow-back" size={24} color="#333" />
              </TouchableOpacity>
              <Text style={styles.modalTitle}>{selectedPlace.name}</Text>
            </View>
            
            <ScrollView style={styles.modalScrollContent}>
              {/* Place type */}
              <Text style={styles.placeType}>{selectedPlace.type}</Text>
              
              {/* Address */}
              {selectedPlace.address && (
                <View style={styles.modalSection}>
                  <View style={styles.modalSectionHeader}>
                    <Ionicons name="location-outline" size={20} color="#f4511e" />
                    <Text style={styles.modalSectionTitle}>Address</Text>
                  </View>
                  <Text style={styles.modalSectionContent}>{selectedPlace.address}</Text>
                </View>
              )}
              
              {/* Contact information */}
              {selectedPlace.contact && (
                <View style={styles.modalSection}>
                  <View style={styles.modalSectionHeader}>
                    <Ionicons name="call-outline" size={20} color="#f4511e" />
                    <Text style={styles.modalSectionTitle}>Contact</Text>
                  </View>
                  
                  {selectedPlace.contact.phone && (
                    <Text style={styles.modalSectionContent}>Phone: {selectedPlace.contact.phone}</Text>
                  )}
                  
                  {selectedPlace.contact.website && (
                    <TouchableOpacity>
                      <Text style={[styles.modalSectionContent, styles.modalLink]}>
                        Website: {selectedPlace.contact.website}
                      </Text>
                    </TouchableOpacity>
                  )}
                </View>
              )}
              
              {/* Distance and rating */}
              <View style={styles.modalMetricsContainer}>
                {selectedPlace.distance && (
                  <View style={styles.modalMetric}>
                    <Ionicons name="walk-outline" size={20} color="#666" />
                    <Text style={styles.modalMetricValue}>
                      {(selectedPlace.distance / 1000).toFixed(1)} km
                    </Text>
                  </View>
                )}
                
                {selectedPlace.rating && (
                  <View style={styles.modalMetric}>
                    <Ionicons name="star" size={20} color="#FFD700" />
                    <Text style={styles.modalMetricValue}>
                      {selectedPlace.rating.toFixed(1)}
                      {selectedPlace.reviewCount && ` (${selectedPlace.reviewCount})`}
                    </Text>
                  </View>
                )}
              </View>
              
              {/* Tags */}
              {selectedPlace.tags && selectedPlace.tags.length > 0 && (
                <View style={styles.modalTagsContainer}>
                  {selectedPlace.tags.map((tag, tagIndex) => (
                    <View key={`modal-tag-${tagIndex}`} style={styles.tag}>
                      <Text style={styles.tagText}>{tag}</Text>
                    </View>
                  ))}
                </View>
              )}
              
              {/* Action buttons */}
              <View style={styles.modalActions}>
                <TouchableOpacity style={styles.modalActionButton}>
                  <Ionicons name="navigate-outline" size={20} color="#fff" />
                  <Text style={styles.modalActionText}>Directions</Text>
                </TouchableOpacity>
                
                <TouchableOpacity style={[styles.modalActionButton, styles.modalActionSecondary]}>
                  <Ionicons name="information-circle-outline" size={20} color="#f4511e" />
                  <Text style={styles.modalActionTextSecondary}>More Info</Text>
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
        </View>
      </Modal>
    );
  };
  
  // Main render
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Location Information</Text>
        {onClose && (
          <TouchableOpacity testID="header-close-button" onPress={onClose} style={styles.closeButton}>
            <Ionicons name="close" size={24} color="#333" />
          </TouchableOpacity>
        )}
      </View>
      
      {/* Tabs */}
      <View style={styles.tabs}>
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'places' && styles.activeTab]}
          onPress={() => handleTabChange('places')}
        >
          <Ionicons 
            name={activeTab === 'places' ? "location" : "location-outline"} 
            size={22} 
            color={activeTab === 'places' ? "#f4511e" : "#555"} 
          />
          <Text 
            style={[styles.tabText, activeTab === 'places' && styles.activeTabText]}
          >
            Places
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'history' && styles.activeTab]}
          onPress={() => handleTabChange('history')}
        >
          <Ionicons 
            name={activeTab === 'history' ? "time" : "time-outline"} 
            size={22} 
            color={activeTab === 'history' ? "#f4511e" : "#555"} 
          />
          <Text 
            style={[styles.tabText, activeTab === 'history' && styles.activeTabText]}
          >
            History
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={[styles.tab, activeTab === 'weather' && styles.activeTab]}
          onPress={() => handleTabChange('weather')}
        >
          <Ionicons 
            name={activeTab === 'weather' ? "sunny" : "sunny-outline"} 
            size={22} 
            color={activeTab === 'weather' ? "#f4511e" : "#555"} 
          />
          <Text 
            style={[styles.tabText, activeTab === 'weather' && styles.activeTabText]}
          >
            Weather
          </Text>
        </TouchableOpacity>
      </View>
      
      {/* Tab content */}
      {activeTab === 'places' && renderPlacesTab()}
      {activeTab === 'history' && renderHistoryTab()}
      {activeTab === 'weather' && renderWeatherTab()}
      
      {/* Place detail modal */}
      {renderPlaceModal()}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    overflow: 'hidden',
    maxHeight: '80%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    position: 'relative',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  closeButton: {
    position: 'absolute',
    right: 16,
    top: 16,
  },
  tabs: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: '#f4511e',
  },
  tabText: {
    marginLeft: 4,
    color: '#555',
    fontSize: 14,
  },
  activeTabText: {
    color: '#f4511e',
    fontWeight: 'bold',
  },
  tabContent: {
    padding: 16,
    maxHeight: 400,
  },
  loadingContainer: {
    padding: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    marginTop: 16,
    color: '#666',
    fontSize: 14,
  },
  errorContainer: {
    padding: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  errorText: {
    marginTop: 16,
    color: '#f44336',
    fontSize: 14,
    textAlign: 'center',
  },
  retryButton: {
    marginTop: 16,
    paddingVertical: 8,
    paddingHorizontal: 16,
    backgroundColor: '#f4511e',
    borderRadius: 4,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  locationName: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#333',
  },
  categorySection: {
    marginBottom: 20,
  },
  categoryTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
    paddingBottom: 4,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  placeItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  placeContent: {
    flex: 1,
  },
  placeName: {
    fontSize: 15,
    fontWeight: '500',
    color: '#333',
    marginBottom: 4,
  },
  placeDetails: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  placeDistance: {
    fontSize: 12,
    color: '#666',
    marginRight: 8,
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  placeRating: {
    fontSize: 12,
    color: '#666',
    marginLeft: 2,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  tag: {
    backgroundColor: '#f0f0f0',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    marginRight: 4,
    marginBottom: 4,
  },
  tagText: {
    fontSize: 10,
    color: '#666',
  },
  factItem: {
    marginBottom: 20,
    padding: 12,
    backgroundColor: '#f9f9f9',
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#f4511e',
  },
  factHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  factTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    flex: 1,
  },
  factYear: {
    fontSize: 14,
    color: '#666',
    fontWeight: 'bold',
  },
  factDescription: {
    fontSize: 14,
    color: '#444',
    lineHeight: 20,
    marginBottom: 8,
  },
  factSource: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
  },
  factSourceText: {
    fontSize: 12,
    color: '#888',
    fontStyle: 'italic',
  },
  factSourceLink: {
    fontSize: 12,
    color: '#f4511e',
    textDecorationLine: 'underline',
  },
  noDataContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
  },
  noDataText: {
    marginTop: 16,
    color: '#666',
    fontSize: 14,
    textAlign: 'center',
  },
  currentWeatherContainer: {
    marginBottom: 24,
    padding: 16,
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
  },
  temperatureContainer: {
    alignItems: 'center',
    marginBottom: 16,
  },
  temperature: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#333',
  },
  weatherCondition: {
    fontSize: 16,
    color: '#666',
  },
  weatherDetails: {
    padding: 8,
    backgroundColor: '#fff',
    borderRadius: 8,
  },
  weatherDetailItem: {
    fontSize: 14,
    color: '#555',
    marginBottom: 4,
  },
  forecastContainer: {
    marginBottom: 16,
  },
  forecastTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 12,
    color: '#333',
  },
  forecastDay: {
    padding: 12,
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    marginBottom: 8,
  },
  forecastDayName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  forecastDate: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  forecastCondition: {
    fontSize: 14,
    color: '#444',
    marginBottom: 4,
  },
  forecastTemperature: {
    flexDirection: 'row',
    marginBottom: 4,
  },
  forecastHigh: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#E53935',
    marginRight: 12,
  },
  forecastLow: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#1E88E5',
  },
  forecastPrecip: {
    fontSize: 12,
    color: '#666',
  },
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  modalCloseButton: {
    marginRight: 16,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    flex: 1,
  },
  modalScrollContent: {
    padding: 16,
  },
  placeType: {
    fontSize: 14,
    color: '#666',
    marginBottom: 16,
    textTransform: 'capitalize',
  },
  modalSection: {
    marginBottom: 16,
  },
  modalSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  modalSectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginLeft: 8,
  },
  modalSectionContent: {
    fontSize: 14,
    color: '#444',
    marginLeft: 28,
  },
  modalLink: {
    color: '#1E88E5',
    textDecorationLine: 'underline',
  },
  modalMetricsContainer: {
    flexDirection: 'row',
    marginBottom: 16,
  },
  modalMetric: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
  },
  modalMetricValue: {
    fontSize: 14,
    color: '#444',
    marginLeft: 4,
  },
  modalTagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 16,
  },
  modalActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  modalActionButton: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f4511e',
    padding: 12,
    borderRadius: 8,
    marginHorizontal: 4,
  },
  modalActionSecondary: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#f4511e',
  },
  modalActionText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
    marginLeft: 4,
  },
  modalActionTextSecondary: {
    color: '#f4511e',
    fontSize: 14,
    fontWeight: 'bold',
    marginLeft: 4,
  },
});

export default LocationEnrichmentCard;
