import React, { useState, useEffect, useCallback } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  Button,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  RefreshControl,
  TouchableOpacity
} from 'react-native';
import { Audio } from 'expo-av';
import { StackNavigationProp } from '@react-navigation/stack';
import { RootStackParamList } from '../App';
import { immersiveApi, Experience, ExperienceRequest } from '@/services/api/immersiveApi';
import { LocationData, locationService } from '@/services/locationService';
import { VoiceNavigationInterface } from '@/components/voice/VoiceNavigationInterface';
import { VoiceCommandProcessor } from '@/components/voice/VoiceCommandProcessor';
import VoiceCommandListener from '@/components/VoiceCommandListener';

type ImmersiveExperienceProps = {
  navigation: StackNavigationProp<RootStackParamList, 'ImmersiveExperience'>;
};

const ImmersiveExperience: React.FC<ImmersiveExperienceProps> = ({ navigation }) => {
  const [experience, setExperience] = useState<Experience | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [sound, setSound] = useState<Audio.Sound | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [currentLocation, setCurrentLocation] = useState<LocationData | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [voiceFirstMode, setVoiceFirstMode] = useState<boolean>(true);
  const [isDriving, setIsDriving] = useState<boolean>(false);

  const getCurrentLocation = async () => {
    try {
      // locationService.getCurrentLocation() will handle initialization and simulated permissions.
      return await locationService.getCurrentLocation();
    } catch (error) {
      logger.error('Error getting location:', error);
      setError('Failed to get location. Please enable location services.');
      return null;
    }
  };

  const fetchExperience = async (useCurrentLocation = true) => {
    setLoading(true);
    setError(null);
    try {
      let location = useCurrentLocation ? await getCurrentLocation() : null;
      
      if (!location) {
        location = {
          latitude: 12.34,
          longitude: 56.78,
          heading: 0,
          speed: 0,
          altitude: 0,
          accuracy: 0,
        };
      }

      const request: ExperienceRequest = {
        conversation_id: 'test123',
        location: {
          latitude: location.latitude,
          longitude: location.longitude
        },
        interests: ['history', 'nature'],
        context: {
          time_of_day: new Date().getHours() < 12 ? 'morning' : 
                       new Date().getHours() < 18 ? 'afternoon' : 'evening',
          weather: 'sunny', // TODO: Integrate with weather API
          mood: 'happy'
        }
      };

      const data = await immersiveApi.getExperience(request);
      setExperience(data);
    } catch (error) {
      logger.error('Error fetching immersive experience:', error);
      setError(error instanceof Error ? error.message : 'Failed to load experience. Please try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchExperience();
  }, []);

  useEffect(() => {
    fetchExperience();
    return () => {
      if (sound) {
        sound.unloadAsync();
      }
    };
  }, []);

  const playTTS = async () => {
    if (!experience?.tts_audio_url) return;
    try {
      if (sound) {
        if (isPlaying) {
          await sound.pauseAsync();
          setIsPlaying(false);
          return;
        }
        await sound.playAsync();
        setIsPlaying(true);
        return;
      }

      const { sound: newSound } = await Audio.Sound.createAsync(
        { uri: experience.tts_audio_url },
        { shouldPlay: true }
      );
      
      newSound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded) {
          setIsPlaying(status.isPlaying);
          if (status.didJustFinish) {
            setIsPlaying(false);
          }
        }
      });
      
      setSound(newSound);
      setIsPlaying(true);
    } catch (error) {
      logger.error('Error playing TTS audio:', error);
      setError('Failed to play audio. Please try again.');
    }
  };

  const handleVoiceCommand = (command: string, result: any) => {
    logger.debug('Voice command:', command, result);
    // Handle voice commands specific to this screen
    if (result.type === 'story' && result.action === 'play') {
      playTTS();
    } else if (result.type === 'navigation' && result.action === 'back') {
      navigation.goBack();
    }
  };

  const handleStoryCommand = (action: string, params?: string[]) => {
    if (action === 'play' || action === 'resume') {
      playTTS();
    } else if (action === 'pause' && isPlaying) {
      sound?.pauseAsync();
      setIsPlaying(false);
    } else if (action === 'next') {
      fetchExperience();
    }
  };

  const handleNavigationCommand = (action: string, params?: string[]) => {
    if (params && params[0]) {
      // Navigate to specific destination
      navigation.navigate('NavigationView', { destination: params[0] });
    }
  };

  const handleBookingCommand = (action: string, params?: string[]) => {
    if (params && params[0]) {
      navigation.navigate('VoiceBooking', { venue: params[0] });
    }
  };

  const saveExperience = async () => {
    if (!experience) return;
    try {
      await immersiveApi.saveExperience(experience);
      // Show success message or update UI
    } catch (error) {
      logger.error('Error saving experience:', error);
      setError('Failed to save experience. Please try again.');
    }
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#f4511e" />
        <Text style={styles.loadingText}>Loading your experience...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>{error}</Text>
        <Button title="Try Again" onPress={() => fetchExperience()} color="#f4511e" />
      </View>
    );
  }

  return (
    <View style={styles.mainContainer}>
      {/* Voice Command Processor - runs in background */}
      <VoiceCommandProcessor 
        onCommandProcessed={handleVoiceCommand}
        continuousListening={voiceFirstMode}
      />
      
      {/* Voice-first interface for driving */}
      {voiceFirstMode && isDriving ? (
        <VoiceNavigationInterface 
          onCommandProcessed={handleVoiceCommand}
          isDriving={isDriving}
        />
      ) : (
        <ScrollView 
          style={styles.container}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              colors={['#f4511e']}
            />
          }
        >
          {experience ? (
        <>
          <Text style={styles.locationText}>
            {currentLocation ? 
              `�� ${currentLocation.latitude.toFixed(4)}, ${currentLocation.longitude.toFixed(4)}` :
              'Location not available'}
          </Text>
          <Text style={styles.storyText}>{experience.story}</Text>
          <View style={styles.buttonContainer}>
            <TouchableOpacity
              style={[styles.button, isPlaying && styles.buttonActive]}
              onPress={playTTS}
            >
              <Text style={styles.buttonText}>
                {isPlaying ? '⏸ Pause Story' : '▶ Play Story'}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.button}
              onPress={saveExperience}
            >
              <Text style={styles.buttonText}>💾 Save Experience</Text>
            </TouchableOpacity>
          </View>
          {experience.playlist && (
            <View style={styles.playlistContainer}>
              <Text style={styles.playlistTitle}>🎵 Suggested Playlist</Text>
              {experience.playlist.tracks.map((track, index) => (
                <Text key={track.id || track.title + '-' + track.artist || index} style={styles.trackText}>
                  {track.title} - {track.artist}
                </Text>
              ))}
            </View>
          )}
          </>
        ) : (
          <Text style={styles.loadingText}>No experience available</Text>
        )}
        </ScrollView>
      )}
      
      {/* Voice Command Listener - floating button */}
      {!isDriving && (
        <VoiceCommandListener 
          onStoryCommand={handleStoryCommand}
          onNavigationCommand={handleNavigationCommand}
          onBookingCommand={handleBookingCommand}
          voiceFirst={voiceFirstMode}
          isDriving={isDriving}
        />
      )}
      
      {/* Toggle voice-first mode */}
      <TouchableOpacity
        style={styles.voiceModeToggle}
        onPress={() => setVoiceFirstMode(!voiceFirstMode)}
      >
        <Text style={styles.voiceModeText}>
          {voiceFirstMode ? '🎙️ Voice Mode' : '👆 Touch Mode'}
        </Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  mainContainer: {
    flex: 1,
    backgroundColor: '#fff',
  },
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#fff',
  },
  storyText: {
    fontSize: 16,
    lineHeight: 24,
    marginBottom: 20,
  },
  loadingText: {
    textAlign: 'center',
    marginTop: 20,
    fontSize: 16,
    color: '#666',
  },
  errorText: {
    color: '#f44336',
    textAlign: 'center',
    marginBottom: 20,
  },
  locationText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 10,
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 20,
  },
  button: {
    backgroundColor: '#f4511e',
    padding: 10,
    borderRadius: 5,
    minWidth: 150,
    alignItems: 'center',
  },
  buttonActive: {
    backgroundColor: '#d84315',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  playlistContainer: {
    marginTop: 20,
    padding: 15,
    backgroundColor: '#f5f5f5',
    borderRadius: 10,
  },
  playlistTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  trackText: {
    fontSize: 14,
    color: '#333',
    marginVertical: 3,
  },
  voiceModeToggle: {
    position: 'absolute',
    top: 40,
    right: 20,
    backgroundColor: '#f4511e',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 20,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
  },
  voiceModeText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
});

export default ImmersiveExperience; 