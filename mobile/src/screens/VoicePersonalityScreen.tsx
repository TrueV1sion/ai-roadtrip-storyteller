import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { PersonalitySelector } from '../components/voice/PersonalitySelector';
import { PersonalityVisualization } from '../components/voice/PersonalityVisualization';
import { voicePersonalityService } from '../services/voicePersonalityService';
import { useAuth } from '../contexts/AuthContext';
import { VoicePersonality } from '../types/voice';
import * as Location from 'expo-location';

export const VoicePersonalityScreen: React.FC = () => {
  const navigation = useNavigation();
  const { user } = useAuth();
  const [selectedPersonality, setSelectedPersonality] = useState<VoicePersonality | null>(null);
  const [currentLocation, setCurrentLocation] = useState<{ lat: number; lng: number; state?: string } | null>(null);
  const [autoPersonality, setAutoPersonality] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadCurrentLocation();
    loadSavedPreferences();
  }, []);

  const loadCurrentLocation = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        console.log('Location permission not granted');
        return;
      }

      const location = await Location.getCurrentPositionAsync({});
      const [address] = await Location.reverseGeocodeAsync({
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
      });

      setCurrentLocation({
        lat: location.coords.latitude,
        lng: location.coords.longitude,
        state: address?.region,
      });
    } catch (error) {
      console.error('Failed to get location:', error);
    }
  };

  const loadSavedPreferences = async () => {
    const savedPersonalityId = await voicePersonalityService.getSelectedPersonality();
    if (savedPersonalityId && !autoPersonality) {
      // Load the saved personality
      const personalities = await voicePersonalityService.getAvailablePersonalities({
        location: currentLocation,
        userId: user?.id,
      });
      const savedPersonality = personalities.find(p => p.id === savedPersonalityId);
      if (savedPersonality) {
        setSelectedPersonality(savedPersonality);
      }
    }
  };

  const handlePersonalitySelect = async (personality: VoicePersonality) => {
    setSelectedPersonality(personality);
    await voicePersonalityService.saveSelectedPersonality(personality.id);
    
    // Update user preferences on backend
    try {
      const response = await fetch(`/api/voice/personality/${personality.id}/select`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user?.token}`,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to save personality preference');
      }
    } catch (error) {
      console.error('Failed to save personality preference:', error);
    }
  };

  const handleAutoPersonalityToggle = (value: boolean) => {
    setAutoPersonality(value);
    if (value) {
      // Clear manual selection and let system choose
      setSelectedPersonality(null);
      voicePersonalityService.saveSelectedPersonality('');
    }
  };

  const testPersonality = async () => {
    if (!selectedPersonality) {
      Alert.alert('No Personality Selected', 'Please select a voice personality first.');
      return;
    }

    setIsLoading(true);
    try {
      await voicePersonalityService.playGreetingSample(selectedPersonality.id);
    } catch (error) {
      Alert.alert('Error', 'Failed to play personality sample');
    } finally {
      setIsLoading(false);
    }
  };

  const showPersonalityInfo = () => {
    if (!selectedPersonality) return;

    const info = `
${selectedPersonality.description}

Speaking Style: ${selectedPersonality.vocabulary_style}
Expertise: ${selectedPersonality.topics_of_expertise.join(', ')}
${selectedPersonality.regional_accent ? `Accent: ${selectedPersonality.regional_accent}` : ''}
${selectedPersonality.active_holidays ? `Special: Available during ${selectedPersonality.active_holidays.join(', ')}` : ''}
    `;

    Alert.alert(selectedPersonality.name, info.trim());
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Voice Personalities</Text>
        <TouchableOpacity onPress={showPersonalityInfo}>
          <MaterialCommunityIcons name="information" size={24} color="#333" />
        </TouchableOpacity>
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        {selectedPersonality && (
          <PersonalityVisualization
            personality={selectedPersonality}
            isActive={true}
            currentEmotion="neutral"
          />
        )}

        <View style={styles.settingsCard}>
          <View style={styles.settingRow}>
            <View>
              <Text style={styles.settingTitle}>Automatic Personality</Text>
              <Text style={styles.settingDescription}>
                Let the app choose based on location and context
              </Text>
            </View>
            <Switch
              value={autoPersonality}
              onValueChange={handleAutoPersonalityToggle}
              trackColor={{ false: '#767577', true: '#81b0ff' }}
              thumbColor={autoPersonality ? '#0066cc' : '#f4f3f4'}
            />
          </View>
        </View>

        {!autoPersonality && (
          <View style={styles.selectorContainer}>
            <Text style={styles.sectionTitle}>Choose Your Guide</Text>
            <PersonalitySelector
              onPersonalitySelect={handlePersonalitySelect}
              currentLocation={currentLocation}
              selectedPersonalityId={selectedPersonality?.id}
            />
          </View>
        )}

        {selectedPersonality && (
          <View style={styles.actionContainer}>
            <TouchableOpacity
              style={[styles.testButton, isLoading && styles.disabledButton]}
              onPress={testPersonality}
              disabled={isLoading}
            >
              <MaterialCommunityIcons 
                name="play-circle" 
                size={24} 
                color="#ffffff" 
              />
              <Text style={styles.testButtonText}>
                {isLoading ? 'Playing...' : 'Test Voice'}
              </Text>
            </TouchableOpacity>

            <View style={styles.personalityStats}>
              <Text style={styles.statsTitle}>Personality Traits</Text>
              {Object.entries(selectedPersonality.emotion_range)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 3)
                .map(([emotion, value]) => (
                  <View key={emotion} style={styles.statRow}>
                    <Text style={styles.statLabel}>
                      {emotion.charAt(0).toUpperCase() + emotion.slice(1)}
                    </Text>
                    <View style={styles.statBar}>
                      <View
                        style={[
                          styles.statBarFill,
                          { width: `${value * 100}%` },
                        ]}
                      />
                    </View>
                  </View>
                ))}
            </View>

            {selectedPersonality.catchphrases.length > 0 && (
              <View style={styles.catchphrasesContainer}>
                <Text style={styles.catchphrasesTitle}>Favorite Phrases</Text>
                {selectedPersonality.catchphrases.slice(0, 3).map((phrase, index) => (
                  <Text key={index} style={styles.catchphrase}>
                    "{phrase}"
                  </Text>
                ))}
              </View>
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333333',
  },
  settingsCard: {
    backgroundColor: '#ffffff',
    marginHorizontal: 15,
    marginTop: 15,
    borderRadius: 12,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  settingTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 4,
  },
  settingDescription: {
    fontSize: 14,
    color: '#666666',
    maxWidth: '80%',
  },
  selectorContainer: {
    marginTop: 20,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333333',
    marginHorizontal: 15,
    marginBottom: 15,
  },
  actionContainer: {
    paddingHorizontal: 15,
    paddingBottom: 30,
  },
  testButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0066cc',
    paddingVertical: 15,
    borderRadius: 12,
    marginTop: 20,
  },
  disabledButton: {
    opacity: 0.6,
  },
  testButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  personalityStats: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 20,
    marginTop: 20,
  },
  statsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 15,
  },
  statRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  statLabel: {
    fontSize: 14,
    color: '#666666',
    width: 100,
  },
  statBar: {
    flex: 1,
    height: 8,
    backgroundColor: '#e0e0e0',
    borderRadius: 4,
    overflow: 'hidden',
  },
  statBarFill: {
    height: '100%',
    backgroundColor: '#0066cc',
    borderRadius: 4,
  },
  catchphrasesContainer: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 20,
    marginTop: 20,
  },
  catchphrasesTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333333',
    marginBottom: 10,
  },
  catchphrase: {
    fontSize: 14,
    fontStyle: 'italic',
    color: '#666666',
    marginBottom: 8,
    paddingLeft: 10,
  },
});