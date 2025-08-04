import React, { useState, useEffect, useCallback } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  Switch,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import Slider from '@react-native-community/slider';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useNavigation } from '@react-navigation/native';
import { apiManager } from '../../services/api/apiManager';
import { useAuth } from '../../contexts/AuthContext';

interface AudioLayer {
  id: string;
  name: string;
  category: string;
  volume: number;
  enabled: boolean;
  icon: string;
}

interface AudioPreset {
  name: string;
  description: string;
  settings: {
    music_volume: number;
    ambient_volume?: number;
    nature_emphasis?: number;
    spatial_width?: number;
    [key: string]: any;
  };
}

export const SpatialAudioController: React.FC = () => {
  const navigation = useNavigation();
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [currentSceneId, setCurrentSceneId] = useState<string | null>(null);
  const [masterVolume, setMasterVolume] = useState(0.8);
  const [spatialWidth, setSpatialWidth] = useState(1.0);
  const [conversationMode, setConversationMode] = useState(false);
  const [audioLayers, setAudioLayers] = useState<AudioLayer[]>([
    {
      id: 'music',
      name: 'Background Music',
      category: 'music',
      volume: 0.6,
      enabled: true,
      icon: 'music-note',
    },
    {
      id: 'ambient',
      name: 'Environmental Sounds',
      category: 'ambient',
      volume: 0.7,
      enabled: true,
      icon: 'nature',
    },
    {
      id: 'narration',
      name: 'Story Narration',
      category: 'narration',
      volume: 1.0,
      enabled: true,
      icon: 'record-voice-over',
    },
    {
      id: 'effects',
      name: 'Sound Effects',
      category: 'effect',
      volume: 0.5,
      enabled: true,
      icon: 'audiotrack',
    },
  ]);
  const [selectedPreset, setSelectedPreset] = useState<string>('custom');
  const [presets, setPresets] = useState<Record<string, AudioPreset>>({});

  useEffect(() => {
    loadAudioPresets();
    checkCurrentScene();
  }, []);

  const loadAudioPresets = async () => {
    try {
      const response = await apiManager.getAudioScenePresets(token);
      if (response.success) {
        setPresets(response.presets);
      }
    } catch (error) {
      logger.error('Error loading audio presets:', error);
    }
  };

  const checkCurrentScene = async () => {
    try {
      setLoading(true);
      // In a real implementation, get current scene from context or API
      // For now, we'll simulate having a scene
      setCurrentSceneId('current-scene-id');
    } catch (error) {
      logger.error('Error checking current scene:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateLayerVolume = useCallback(
    async (layerId: string, volume: number) => {
      const updatedLayers = audioLayers.map((layer) =>
        layer.id === layerId ? { ...layer, volume } : layer
      );
      setAudioLayers(updatedLayers);

      // Update the scene if we have one
      if (currentSceneId) {
        try {
          await apiManager.updateAudioScene(
            currentSceneId,
            {
              volume_adjustments: [
                {
                  category: updatedLayers.find((l) => l.id === layerId)?.category,
                  factor: volume,
                },
              ],
            },
            token
          );
        } catch (error) {
          logger.error('Error updating layer volume:', error);
        }
      }
    },
    [audioLayers, currentSceneId, token]
  );

  const toggleLayer = useCallback(
    async (layerId: string) => {
      const updatedLayers = audioLayers.map((layer) =>
        layer.id === layerId ? { ...layer, enabled: !layer.enabled } : layer
      );
      setAudioLayers(updatedLayers);

      const layer = updatedLayers.find((l) => l.id === layerId);
      if (currentSceneId && layer) {
        try {
          if (!layer.enabled) {
            // Remove the layer category
            await apiManager.updateAudioScene(
              currentSceneId,
              {
                remove_categories: [layer.category],
              },
              token
            );
          } else {
            // Re-add the layer
            await apiManager.updateAudioScene(
              currentSceneId,
              {
                add_layers: [
                  {
                    category: layer.category,
                    volume: layer.volume,
                  },
                ],
              },
              token
            );
          }
        } catch (error) {
          logger.error('Error toggling layer:', error);
        }
      }
    },
    [audioLayers, currentSceneId, token]
  );

  const applyPreset = useCallback(
    async (presetKey: string) => {
      if (presetKey === 'custom') {
        setSelectedPreset('custom');
        return;
      }

      const preset = presets[presetKey];
      if (!preset) return;

      setSelectedPreset(presetKey);

      // Apply preset settings
      if (preset.settings.music_volume !== undefined) {
        const musicLayer = audioLayers.find((l) => l.category === 'music');
        if (musicLayer) {
          updateLayerVolume(musicLayer.id, preset.settings.music_volume);
        }
      }

      if (preset.settings.ambient_volume !== undefined) {
        const ambientLayer = audioLayers.find((l) => l.category === 'ambient');
        if (ambientLayer) {
          updateLayerVolume(ambientLayer.id, preset.settings.ambient_volume);
        }
      }

      if (preset.settings.spatial_width !== undefined) {
        setSpatialWidth(preset.settings.spatial_width);
      }

      Alert.alert('Preset Applied', `${preset.name} settings have been applied.`);
    },
    [presets, audioLayers, updateLayerVolume]
  );

  const handleConversationModeToggle = useCallback(async () => {
    const newMode = !conversationMode;
    setConversationMode(newMode);

    if (newMode) {
      // Duck all audio for conversation
      const updates = audioLayers
        .filter((layer) => layer.category !== 'alert')
        .map((layer) => ({
          category: layer.category,
          factor: 0.3, // Duck to 30%
        }));

      if (currentSceneId) {
        try {
          await apiManager.updateAudioScene(
            currentSceneId,
            { volume_adjustments: updates },
            token
          );
        } catch (error) {
          logger.error('Error enabling conversation mode:', error);
        }
      }
    } else {
      // Restore normal volumes
      const updates = audioLayers.map((layer) => ({
        category: layer.category,
        factor: layer.volume,
      }));

      if (currentSceneId) {
        try {
          await apiManager.updateAudioScene(
            currentSceneId,
            { volume_adjustments: updates },
            token
          );
        } catch (error) {
          logger.error('Error disabling conversation mode:', error);
        }
      }
    }
  }, [conversationMode, audioLayers, currentSceneId, token]);

  const openAdvancedSettings = () => {
    navigation.navigate('AudioSettingsScreen' as never);
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading audio settings...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Master Controls */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Master Controls</Text>
        
        <View style={styles.controlRow}>
          <Icon name="volume-up" size={24} color="#666" />
          <Text style={styles.controlLabel}>Master Volume</Text>
          <Text style={styles.valueText}>{Math.round(masterVolume * 100)}%</Text>
        </View>
        <Slider
          style={styles.slider}
          value={masterVolume}
          onValueChange={setMasterVolume}
          minimumValue={0}
          maximumValue={1}
          minimumTrackTintColor="#007AFF"
          maximumTrackTintColor="#E0E0E0"
        />

        <View style={styles.controlRow}>
          <Icon name="surround-sound" size={24} color="#666" />
          <Text style={styles.controlLabel}>Spatial Width</Text>
          <Text style={styles.valueText}>
            {spatialWidth === 0 ? 'Mono' : spatialWidth === 1 ? 'Normal' : 'Wide'}
          </Text>
        </View>
        <Slider
          style={styles.slider}
          value={spatialWidth}
          onValueChange={setSpatialWidth}
          minimumValue={0}
          maximumValue={2}
          minimumTrackTintColor="#007AFF"
          maximumTrackTintColor="#E0E0E0"
        />

        <View style={styles.switchRow}>
          <Icon name="chat" size={24} color="#666" />
          <Text style={styles.controlLabel}>Conversation Mode</Text>
          <Switch
            value={conversationMode}
            onValueChange={handleConversationModeToggle}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>
      </View>

      {/* Audio Layers */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Audio Layers</Text>
        
        {audioLayers.map((layer) => (
          <View key={layer.id} style={styles.layerContainer}>
            <View style={styles.layerHeader}>
              <Icon name={layer.icon} size={24} color={layer.enabled ? '#007AFF' : '#CCC'} />
              <Text style={[styles.layerName, !layer.enabled && styles.disabledText]}>
                {layer.name}
              </Text>
              <Switch
                value={layer.enabled}
                onValueChange={() => toggleLayer(layer.id)}
                trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
              />
            </View>
            
            {layer.enabled && (
              <>
                <Slider
                  style={styles.layerSlider}
                  value={layer.volume}
                  onValueChange={(value) => updateLayerVolume(layer.id, value)}
                  minimumValue={0}
                  maximumValue={1}
                  minimumTrackTintColor="#007AFF"
                  maximumTrackTintColor="#E0E0E0"
                  disabled={!layer.enabled}
                />
                <Text style={styles.layerVolume}>{Math.round(layer.volume * 100)}%</Text>
              </>
            )}
          </View>
        ))}
      </View>

      {/* Presets */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Audio Presets</Text>
        
        <TouchableOpacity
          style={[styles.presetButton, selectedPreset === 'custom' && styles.selectedPreset]}
          onPress={() => applyPreset('custom')}
        >
          <Icon name="tune" size={20} color={selectedPreset === 'custom' ? '#FFF' : '#007AFF'} />
          <Text style={[styles.presetText, selectedPreset === 'custom' && styles.selectedPresetText]}>
            Custom
          </Text>
        </TouchableOpacity>

        {Object.entries(presets).map(([key, preset]) => (
          <TouchableOpacity
            key={key}
            style={[styles.presetButton, selectedPreset === key && styles.selectedPreset]}
            onPress={() => applyPreset(key)}
          >
            <Text style={[styles.presetText, selectedPreset === key && styles.selectedPresetText]}>
              {preset.name}
            </Text>
            <Text style={[styles.presetDescription, selectedPreset === key && styles.selectedPresetText]}>
              {preset.description}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Advanced Settings */}
      <TouchableOpacity style={styles.advancedButton} onPress={openAdvancedSettings}>
        <Icon name="settings" size={20} color="#007AFF" />
        <Text style={styles.advancedButtonText}>Advanced Audio Settings</Text>
        <Icon name="chevron-right" size={20} color="#007AFF" />
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  section: {
    backgroundColor: 'white',
    marginVertical: 8,
    paddingHorizontal: 16,
    paddingVertical: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 16,
  },
  controlRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  controlLabel: {
    flex: 1,
    fontSize: 16,
    color: '#333',
    marginLeft: 12,
  },
  valueText: {
    fontSize: 14,
    color: '#666',
  },
  slider: {
    height: 40,
    marginBottom: 16,
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
  },
  layerContainer: {
    marginBottom: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  layerHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  layerName: {
    flex: 1,
    fontSize: 16,
    color: '#333',
    marginLeft: 12,
  },
  disabledText: {
    color: '#CCC',
  },
  layerSlider: {
    height: 30,
  },
  layerVolume: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
  },
  presetButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    marginBottom: 12,
    backgroundColor: '#F5F5F5',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E0E0E0',
  },
  selectedPreset: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  presetText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
    marginLeft: 8,
  },
  selectedPresetText: {
    color: 'white',
  },
  presetDescription: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
    marginLeft: 28,
  },
  advancedButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'white',
    padding: 16,
    marginVertical: 8,
  },
  advancedButtonText: {
    flex: 1,
    fontSize: 16,
    color: '#007AFF',
    marginLeft: 12,
  },
});