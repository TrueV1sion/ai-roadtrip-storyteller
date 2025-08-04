/**
 * Audio Settings Screen
 * Allows users to customize their audio experience
 */

import React, { useState, useEffect } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Switch,
  Slider,
  TouchableOpacity,
  Alert
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { audioManager, AudioCategory } from '../services/audio/audioManager';
import { unifiedVoiceOrchestrator } from '../services/voice/unifiedVoiceOrchestrator';
import { Ionicons } from '@expo/vector-icons';

interface AudioSettings {
  masterVolume: number;
  categoryVolumes: Record<AudioCategory, number>;
  spatialAudioEnabled: boolean;
  musicDuckingEnabled: boolean;
  drivingModeEnabled: boolean;
  voicePersonality: string;
  proactiveSuggestionsEnabled: boolean;
}

const AudioSettingsScreen: React.FC = () => {
  const [settings, setSettings] = useState<AudioSettings>({
    masterVolume: 1.0,
    categoryVolumes: {
      [AudioCategory.VOICE]: 1.0,
      [AudioCategory.NAVIGATION]: 1.0,
      [AudioCategory.MUSIC]: 0.3,
      [AudioCategory.AMBIENT]: 0.4,
      [AudioCategory.EFFECT]: 0.7
    },
    spatialAudioEnabled: true,
    musicDuckingEnabled: true,
    drivingModeEnabled: false,
    voicePersonality: 'wise_narrator',
    proactiveSuggestionsEnabled: true
  });

  const [testingCategory, setTestingCategory] = useState<AudioCategory | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const stored = await AsyncStorage.getItem('@audio_settings');
      if (stored) {
        setSettings(JSON.parse(stored));
      }
    } catch (error) {
      logger.error('Failed to load settings:', error);
    }
  };

  const saveSettings = async (newSettings: AudioSettings) => {
    try {
      await AsyncStorage.setItem('@audio_settings', JSON.stringify(newSettings));
      setSettings(newSettings);
      
      // Apply settings to audio manager
      await audioManager.setMasterVolume(newSettings.masterVolume);
      for (const [category, volume] of Object.entries(newSettings.categoryVolumes)) {
        await audioManager.setCategoryVolume(category as AudioCategory, volume);
      }
      
      // Apply voice settings
      await unifiedVoiceOrchestrator.updatePreferences({
        personality: newSettings.voicePersonality,
        proactive_suggestions: newSettings.proactiveSuggestionsEnabled
      });
    } catch (error) {
      logger.error('Failed to save settings:', error);
      Alert.alert('Error', 'Failed to save audio settings');
    }
  };

  const updateCategoryVolume = (category: AudioCategory, volume: number) => {
    const newSettings = {
      ...settings,
      categoryVolumes: {
        ...settings.categoryVolumes,
        [category]: volume
      }
    };
    saveSettings(newSettings);
  };

  const testAudioCategory = async (category: AudioCategory) => {
    setTestingCategory(category);
    
    try {
      // Play a test sound for the category
      const testSounds = {
        [AudioCategory.VOICE]: 'Testing voice audio',
        [AudioCategory.NAVIGATION]: 'Turn right in 500 feet',
        [AudioCategory.MUSIC]: 'Sample music playing',
        [AudioCategory.AMBIENT]: 'Birds chirping',
        [AudioCategory.EFFECT]: 'Notification sound'
      };

      // In a real app, you would play actual audio files
      Alert.alert('Audio Test', testSounds[category]);
      
      setTimeout(() => setTestingCategory(null), 2000);
    } catch (error) {
      logger.error('Failed to test audio:', error);
      setTestingCategory(null);
    }
  };

  const voicePersonalities = [
    { id: 'wise_narrator', name: 'Wise Narrator', emoji: '🧙' },
    { id: 'enthusiastic_buddy', name: 'Enthusiastic Buddy', emoji: '🤗' },
    { id: 'local_expert', name: 'Local Expert', emoji: '🗺️' },
    { id: 'mystical_shaman', name: 'Mystical Shaman', emoji: '🔮' },
    { id: 'comedic_relief', name: 'Comedic Relief', emoji: '😄' }
  ];

  const getCategoryEmoji = (category: AudioCategory): string => {
    const emojis = {
      [AudioCategory.VOICE]: '🎙️',
      [AudioCategory.NAVIGATION]: '🧭',
      [AudioCategory.MUSIC]: '🎵',
      [AudioCategory.AMBIENT]: '🌿',
      [AudioCategory.EFFECT]: '✨'
    };
    return emojis[category] || '🔊';
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.title}>Audio Settings</Text>

        {/* Master Volume */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Master Volume</Text>
          <View style={styles.sliderContainer}>
            <Ionicons name="volume-low" size={24} color="#666" />
            <Slider
              style={styles.slider}
              value={settings.masterVolume}
              minimumValue={0}
              maximumValue={1}
              onSlidingComplete={(value) => {
                saveSettings({ ...settings, masterVolume: value });
              }}
            />
            <Ionicons name="volume-high" size={24} color="#666" />
          </View>
          <Text style={styles.volumeText}>
            {Math.round(settings.masterVolume * 100)}%
          </Text>
        </View>

        {/* Category Volumes */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Audio Categories</Text>
          {Object.entries(settings.categoryVolumes).map(([category, volume]) => (
            <View key={category} style={styles.categoryRow}>
              <View style={styles.categoryHeader}>
                <Text style={styles.categoryEmoji}>
                  {getCategoryEmoji(category as AudioCategory)}
                </Text>
                <Text style={styles.categoryName}>{category}</Text>
                <TouchableOpacity
                  onPress={() => testAudioCategory(category as AudioCategory)}
                  disabled={testingCategory !== null}
                >
                  <Ionicons
                    name="play-circle"
                    size={24}
                    color={testingCategory === category ? '#2196F3' : '#666'}
                  />
                </TouchableOpacity>
              </View>
              <View style={styles.sliderContainer}>
                <Slider
                  style={styles.categorySlider}
                  value={volume}
                  minimumValue={0}
                  maximumValue={1.5}
                  onSlidingComplete={(value) => {
                    updateCategoryVolume(category as AudioCategory, value);
                  }}
                />
                <Text style={styles.categoryVolume}>
                  {Math.round(volume * 100)}%
                </Text>
              </View>
            </View>
          ))}
        </View>

        {/* Audio Features */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Audio Features</Text>
          
          <View style={styles.toggleRow}>
            <Text style={styles.toggleLabel}>Spatial Audio</Text>
            <Switch
              value={settings.spatialAudioEnabled}
              onValueChange={(value) => {
                saveSettings({ ...settings, spatialAudioEnabled: value });
              }}
            />
          </View>

          <View style={styles.toggleRow}>
            <Text style={styles.toggleLabel}>Music Ducking</Text>
            <Switch
              value={settings.musicDuckingEnabled}
              onValueChange={(value) => {
                saveSettings({ ...settings, musicDuckingEnabled: value });
              }}
            />
          </View>

          <View style={styles.toggleRow}>
            <Text style={styles.toggleLabel}>Driving Mode</Text>
            <Switch
              value={settings.drivingModeEnabled}
              onValueChange={async (value) => {
                await audioManager.setDrivingMode(value);
                saveSettings({ ...settings, drivingModeEnabled: value });
              }}
            />
          </View>

          <View style={styles.toggleRow}>
            <Text style={styles.toggleLabel}>Proactive Suggestions</Text>
            <Switch
              value={settings.proactiveSuggestionsEnabled}
              onValueChange={(value) => {
                saveSettings({ ...settings, proactiveSuggestionsEnabled: value });
              }}
            />
          </View>
        </View>

        {/* Voice Personality */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Voice Personality</Text>
          <View style={styles.personalityGrid}>
            {voicePersonalities.map((personality) => (
              <TouchableOpacity
                key={personality.id}
                style={[
                  styles.personalityCard,
                  settings.voicePersonality === personality.id && styles.selectedPersonality
                ]}
                onPress={() => {
                  saveSettings({ ...settings, voicePersonality: personality.id });
                }}
              >
                <Text style={styles.personalityEmoji}>{personality.emoji}</Text>
                <Text style={styles.personalityName}>{personality.name}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Reset Button */}
        <TouchableOpacity
          style={styles.resetButton}
          onPress={() => {
            Alert.alert(
              'Reset Audio Settings',
              'Are you sure you want to reset all audio settings to defaults?',
              [
                { text: 'Cancel', style: 'cancel' },
                {
                  text: 'Reset',
                  style: 'destructive',
                  onPress: async () => {
                    const defaultSettings: AudioSettings = {
                      masterVolume: 1.0,
                      categoryVolumes: {
                        [AudioCategory.VOICE]: 1.0,
                        [AudioCategory.NAVIGATION]: 1.0,
                        [AudioCategory.MUSIC]: 0.3,
                        [AudioCategory.AMBIENT]: 0.4,
                        [AudioCategory.EFFECT]: 0.7
                      },
                      spatialAudioEnabled: true,
                      musicDuckingEnabled: true,
                      drivingModeEnabled: false,
                      voicePersonality: 'wise_narrator',
                      proactiveSuggestionsEnabled: true
                    };
                    await saveSettings(defaultSettings);
                  }
                }
              ]
            );
          }}
        >
          <Text style={styles.resetButtonText}>Reset to Defaults</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 20,
    color: '#333',
  },
  section: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 15,
    color: '#333',
  },
  sliderContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 10,
  },
  slider: {
    flex: 1,
    marginHorizontal: 10,
  },
  volumeText: {
    textAlign: 'center',
    fontSize: 16,
    color: '#666',
  },
  categoryRow: {
    marginBottom: 20,
  },
  categoryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  categoryEmoji: {
    fontSize: 20,
    marginRight: 10,
  },
  categoryName: {
    flex: 1,
    fontSize: 16,
    color: '#333',
    textTransform: 'capitalize',
  },
  categorySlider: {
    flex: 1,
  },
  categoryVolume: {
    width: 50,
    textAlign: 'right',
    fontSize: 14,
    color: '#666',
  },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#EEE',
  },
  toggleLabel: {
    fontSize: 16,
    color: '#333',
  },
  personalityGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -5,
  },
  personalityCard: {
    width: '30%',
    aspectRatio: 1,
    margin: '1.66%',
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 10,
  },
  selectedPersonality: {
    backgroundColor: '#2196F3',
  },
  personalityEmoji: {
    fontSize: 30,
    marginBottom: 5,
  },
  personalityName: {
    fontSize: 12,
    textAlign: 'center',
    color: '#333',
  },
  resetButton: {
    backgroundColor: '#F44336',
    borderRadius: 8,
    padding: 15,
    alignItems: 'center',
  },
  resetButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default AudioSettingsScreen;