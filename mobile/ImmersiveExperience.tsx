import React, { useState, useEffect, useRef } from 'react';
import { 
  View, 
  Text, 
  TouchableOpacity, 
  StyleSheet, 
  ScrollView, 
  ActivityIndicator, 
  SafeAreaView,
  Animated,
  Modal
} from 'react-native';
import { StackNavigationProp } from '@react-navigation/stack';
import { Ionicons } from '@expo/vector-icons';
import { immersiveService, ImmersiveResponse } from './src/services/api/ImmersiveService';
import InteractiveFeatureButton from './src/components/InteractiveFeatureButton';
import VoiceCommandListener from './src/components/VoiceCommandListener';
import LocationEnrichmentCard from './src/components/LocationEnrichmentCard';
import { PlaceDetails } from './src/services/locationEnrichmentService';

// Import new refactored components
import AudioPlayer from './src/components/immersive/AudioPlayer';
import StoryCard from './src/components/immersive/StoryCard';
import { LocationContextProvider, useLocationContext } from './src/components/immersive/LocationContextProvider';

type RootStackParamList = {
  ImmersiveExperience: undefined;
  Home: undefined;
};

type ImmersiveExperienceProps = {
  navigation: StackNavigationProp<RootStackParamList, 'ImmersiveExperience'>;
};

const ImmersiveExperienceContent: React.FC<ImmersiveExperienceProps> = ({ navigation }) => {
  const [experience, setExperience] = useState<ImmersiveResponse | null>(null);
  const [experienceLoading, setExperienceLoading] = useState<boolean>(false);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [showLocationInfo, setShowLocationInfo] = useState<boolean>(false);
  const [selectedPlace, setSelectedPlace] = useState<PlaceDetails | null>(null);
  const [showPlaceDetails, setShowPlaceDetails] = useState<boolean>(false);
  
  // Animation values
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;

  // Get location context
  const { 
    location, 
    timeOfDay, 
    weather, 
    mood, 
    refreshLocation, 
    loading: locationLoading, 
    error: locationError 
  } = useLocationContext();

  // Fetch experience when location changes
  useEffect(() => {
    if (location) {
      fetchExperience();
    }
  }, [location, timeOfDay, weather, mood]);

  // Start animations whenever there's new content
  useEffect(() => {
    startAnimations();
  }, [experience]);

  const startAnimations = () => {
    // Reset animation values
    fadeAnim.setValue(0);
    slideAnim.setValue(50);
    
    // Start animations
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 1000,
        useNativeDriver: true
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 800,
        useNativeDriver: true
      })
    ]).start();
  };

  const fetchExperience = async () => {
    if (!location) {
      setError('Location is not available. Please check your location permissions.');
      return;
    }
    
    setExperienceLoading(true);
    setError(null);
    
    try {
      // Create a unique conversation ID using timestamp
      const conversationId = `session_${Date.now()}`;
      
      // User interests - in a real app, this would come from user preferences
      const userInterests = ['history', 'nature', 'architecture', 'culture'];
      
      console.log('Fetching immersive experience with location:', location);
      
      const response = await immersiveService.getImmersiveExperience({
        conversation_id: conversationId,
        location: location,
        interests: userInterests,
        context: {
          time_of_day: timeOfDay,
          weather: weather,
          mood: mood
        }
      });
      
      console.log('Received experience data');
      setExperience(response);
      
    } catch (error: any) {
      console.error('Error fetching immersive experience:', error);
      setError(error.message || 'Failed to load experience. Please try again.');
    } finally {
      setExperienceLoading(false);
    }
  };

  const refreshExperience = async () => {
    try {
      await refreshLocation();
      fetchExperience();
    } catch (error: any) {
      setError('Failed to refresh location. Please try again.');
    }
  };

  const handlePlaybackStatusUpdate = (status: boolean) => {
    setIsPlaying(status);
  };

  const handleAudioError = (errorMessage: string) => {
    setError(errorMessage);
  };

  const handleShowLocationInfo = () => {
    setShowLocationInfo(true);
  };

  const handleHideLocationInfo = () => {
    setShowLocationInfo(false);
  };

  const handleSelectPlace = (place: PlaceDetails) => {
    setSelectedPlace(place);
    setShowPlaceDetails(true);
  };

  const handleClosePlaceDetails = () => {
    setShowPlaceDetails(false);
  };

  // Render loading state
  const renderLoading = () => (
    <View style={styles.loadingContainer}>
      <ActivityIndicator size="large" color="#f4511e" />
      <Text style={styles.loadingText}>Creating your magical road trip experience...</Text>
    </View>
  );

  // Render error state
  const renderError = () => (
    <View style={styles.errorContainer}>
      <Ionicons name="alert-circle" size={50} color="#f4511e" />
      <Text style={styles.errorTitle}>Oops!</Text>
      <Text style={styles.errorText}>{error || 'Something went wrong. Please try again.'}</Text>
      <TouchableOpacity style={styles.retryButton} onPress={refreshExperience}>
        <Text style={styles.retryButtonText}>Try Again</Text>
      </TouchableOpacity>
    </View>
  );

  // Render experience content
  const renderExperience = () => (
    <ScrollView style={styles.scrollContainer} contentContainerStyle={styles.contentContainer}>
      {/* Story Card */}
      <StoryCard
        title={experience?.title || 'Your Road Trip Story'}
        content={experience?.content || ''}
        audioBase64={experience?.tts_audio}
        onRefresh={refreshExperience}
        onPlaybackStatusUpdate={handlePlaybackStatusUpdate}
        onError={handleAudioError}
        fadeAnim={fadeAnim}
        slideAnim={slideAnim}
      />
      
      {/* Interactive Features */}
      <View style={styles.featureButtonsContainer}>
        <InteractiveFeatureButton
          icon="map"
          label="Nearby Places"
          onPress={handleShowLocationInfo}
        />
        <InteractiveFeatureButton
          icon="game-controller"
          label="Road Trip Games"
          onPress={() => navigation.navigate('Home')}
        />
        <InteractiveFeatureButton
          icon="musical-notes"
          label="Playlist"
          onPress={() => console.log('Show playlist')}
        />
      </View>
      
      {/* Location Info Modal */}
      <Modal
        visible={showLocationInfo}
        animationType="slide"
        transparent={true}
        onRequestClose={handleHideLocationInfo}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Nearby Attractions</Text>
              <TouchableOpacity onPress={handleHideLocationInfo}>
                <Ionicons name="close" size={24} color="#333" />
              </TouchableOpacity>
            </View>
            
            <ScrollView style={styles.placesContainer}>
              {experience?.nearby_places?.map((place, index) => (
                <LocationEnrichmentCard
                  key={`${place.name}-${index}`}
                  place={place}
                  onPress={() => handleSelectPlace(place)}
                />
              ))}
              
              {(!experience?.nearby_places || experience.nearby_places.length === 0) && (
                <Text style={styles.noPlacesText}>
                  No notable places found nearby.
                </Text>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>
      
      {/* Place Details Modal */}
      <Modal
        visible={showPlaceDetails}
        animationType="slide"
        transparent={true}
        onRequestClose={handleClosePlaceDetails}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>{selectedPlace?.name}</Text>
              <TouchableOpacity onPress={handleClosePlaceDetails}>
                <Ionicons name="close" size={24} color="#333" />
              </TouchableOpacity>
            </View>
            
            <ScrollView style={styles.placeDetailsContainer}>
              {selectedPlace?.image_url && (
                <View style={styles.placeImageContainer}>
                  <Image 
                    source={{ uri: selectedPlace.image_url }} 
                    style={styles.placeImage}
                    resizeMode="cover"
                  />
                </View>
              )}
              
              <Text style={styles.placeDescription}>{selectedPlace?.description}</Text>
              
              {selectedPlace?.facts && selectedPlace.facts.length > 0 && (
                <View style={styles.factsContainer}>
                  <Text style={styles.factsTitle}>Interesting Facts</Text>
                  {selectedPlace.facts.map((fact, index) => (
                    <View key={index} style={styles.factItem}>
                      <Ionicons name="information-circle" size={20} color="#f4511e" />
                      <Text style={styles.factText}>{fact}</Text>
                    </View>
                  ))}
                </View>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );

  // Render empty state when no experience or location
  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Ionicons name="navigate-circle-outline" size={80} color="#f4511e" />
      <Text style={styles.emptyTitle}>Let's Start Your Journey</Text>
      <Text style={styles.emptyText}>
        Allow location access to get personalized stories and information about places along your route.
      </Text>
      <TouchableOpacity style={styles.startButton} onPress={refreshLocation}>
        <Text style={styles.startButtonText}>Find My Location</Text>
      </TouchableOpacity>
    </View>
  );

  // Determine what to render based on state
  if (locationLoading || experienceLoading) {
    return renderLoading();
  }
  
  if (locationError || error) {
    return renderError();
  }
  
  if (!location || !experience) {
    return renderEmpty();
  }
  
  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {/* Voice Command Listener */}
        <VoiceCommandListener
          isPlaying={isPlaying}
          onCommand={(command) => console.log('Voice command:', command)}
        />
        
        {renderExperience()}
      </View>
    </SafeAreaView>
  );
};

// Wrap the component with LocationContextProvider
const ImmersiveExperience: React.FC<ImmersiveExperienceProps> = (props) => {
  return (
    <LocationContextProvider>
      <ImmersiveExperienceContent {...props} />
    </LocationContextProvider>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#f8f8f8',
  },
  container: {
    flex: 1,
  },
  scrollContainer: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 32,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 20,
    fontSize: 16,
    color: '#555',
    textAlign: 'center',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#f4511e',
    marginTop: 12,
    marginBottom: 8,
  },
  errorText: {
    fontSize: 16,
    color: '#555',
    textAlign: 'center',
    marginBottom: 24,
  },
  retryButton: {
    backgroundColor: '#f4511e',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 24,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  emptyTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 16,
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 32,
    lineHeight: 24,
  },
  startButton: {
    backgroundColor: '#f4511e',
    paddingVertical: 14,
    paddingHorizontal: 28,
    borderRadius: 28,
  },
  startButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  featureButtonsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 16,
    marginBottom: 8,
  },
  modalContainer: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  placesContainer: {
    maxHeight: 400,
  },
  placeDetailsContainer: {
    maxHeight: 500,
  },
  noPlacesText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginTop: 24,
  },
  placeImageContainer: {
    height: 200,
    borderRadius: 12,
    overflow: 'hidden',
    marginBottom: 16,
  },
  placeImage: {
    width: '100%',
    height: '100%',
  },
  placeDescription: {
    fontSize: 16,
    lineHeight: 24,
    color: '#333',
    marginBottom: 16,
  },
  factsContainer: {
    marginTop: 8,
  },
  factsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  factItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  factText: {
    fontSize: 15,
    color: '#444',
    flex: 1,
    marginLeft: 8,
    lineHeight: 22,
  },
});

export default ImmersiveExperience;
