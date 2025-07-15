import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  ActivityIndicator,
} from 'react-native';
import Slider from '@react-native-community/slider';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { Picker } from '@react-native-picker/picker';
import { apiManager } from '../../services/api/apiManager';
import { useAuth } from '../../contexts/AuthContext';

interface EnvironmentLayer {
  id: string;
  name: string;
  category: string;
  volume: number;
  enabled: boolean;
  frequency?: 'low' | 'mid' | 'high' | 'full';
}

interface WeatherEffect {
  type: string;
  intensity: number;
  enabled: boolean;
}

interface EnvironmentalAudioMixerProps {
  location?: {
    type: string;
    terrain?: string;
    population_density?: string;
  };
  weather?: {
    type: string;
    intensity?: number;
    wind_speed?: number;
  };
  timeOfDay?: string;
  speed?: number; // km/h
  onMixUpdate?: (mix: any) => void;
}

export const EnvironmentalAudioMixer: React.FC<EnvironmentalAudioMixerProps> = ({
  location = { type: 'rural' },
  weather = { type: 'clear' },
  timeOfDay = 'day',
  speed = 0,
  onMixUpdate,
}) => {
  const { token } = useAuth();
  const [loading, setLoading] = useState(false);
  const [environmentType, setEnvironmentType] = useState(location.type);
  const [layers, setLayers] = useState<EnvironmentLayer[]>([
    {
      id: 'base_ambient',
      name: 'Base Ambience',
      category: 'ambient',
      volume: 0.6,
      enabled: true,
      frequency: 'full',
    },
    {
      id: 'nature',
      name: 'Nature Sounds',
      category: 'biological',
      volume: 0.7,
      enabled: true,
      frequency: 'high',
    },
    {
      id: 'weather',
      name: 'Weather Effects',
      category: 'weather',
      volume: 0.5,
      enabled: weather.type !== 'clear',
      frequency: 'full',
    },
    {
      id: 'wind',
      name: 'Wind Simulation',
      category: 'wind',
      volume: 0.4,
      enabled: speed > 50,
      frequency: 'low',
    },
  ]);
  const [weatherEffects, setWeatherEffects] = useState<WeatherEffect[]>([
    { type: 'rain', intensity: 0.5, enabled: weather.type === 'rain' },
    { type: 'thunder', intensity: 0.7, enabled: weather.type === 'storm' },
    { type: 'wind', intensity: 0.4, enabled: true },
  ]);
  const [adaptiveMode, setAdaptiveMode] = useState(true);
  const [detailLevel, setDetailLevel] = useState(1.0);

  const environmentTypes = [
    { label: 'Forest', value: 'forest' },
    { label: 'City', value: 'city' },
    { label: 'Beach', value: 'beach' },
    { label: 'Mountain', value: 'mountain' },
    { label: 'Desert', value: 'desert' },
    { label: 'Rural', value: 'rural' },
    { label: 'Highway', value: 'highway' },
    { label: 'Suburban', value: 'suburban' },
  ];

  const timePresets = [
    { label: 'Dawn', value: 'dawn', icon: 'wb-twilight' },
    { label: 'Morning', value: 'morning', icon: 'wb-sunny' },
    { label: 'Day', value: 'day', icon: 'light-mode' },
    { label: 'Dusk', value: 'dusk', icon: 'wb-twilight' },
    { label: 'Night', value: 'night', icon: 'nights-stay' },
  ];

  useEffect(() => {
    if (adaptiveMode) {
      adaptToConditions();
    }
  }, [speed, weather, timeOfDay, environmentType, adaptiveMode]);

  const adaptToConditions = useCallback(() => {
    // Adapt layers based on speed
    const speedFactor = Math.min(1.0, speed / 100);
    const detailReduction = 1.0 - speedFactor * 0.7;
    
    setDetailLevel(detailReduction);
    
    // Update nature sounds based on speed
    setLayers((prevLayers) =>
      prevLayers.map((layer) => {
        if (layer.category === 'biological') {
          return { ...layer, volume: 0.7 * detailReduction };
        }
        if (layer.category === 'wind') {
          return { ...layer, enabled: speed > 30, volume: 0.2 + speedFactor * 0.4 };
        }
        return layer;
      })
    );

    // Update weather effects
    setWeatherEffects((prevEffects) =>
      prevEffects.map((effect) => {
        if (effect.type === 'wind') {
          const windSpeed = weather.wind_speed || 0;
          const totalWind = windSpeed + speed * 0.5;
          return {
            ...effect,
            intensity: Math.min(1.0, totalWind / 100),
            enabled: totalWind > 10,
          };
        }
        return effect;
      })
    );
  }, [speed, weather]);

  const updateLayer = useCallback(
    (layerId: string, updates: Partial<EnvironmentLayer>) => {
      setLayers((prevLayers) =>
        prevLayers.map((layer) =>
          layer.id === layerId ? { ...layer, ...updates } : layer
        )
      );
      generateMix();
    },
    []
  );

  const updateWeatherEffect = useCallback(
    (type: string, updates: Partial<WeatherEffect>) => {
      setWeatherEffects((prevEffects) =>
        prevEffects.map((effect) =>
          effect.type === type ? { ...effect, ...updates } : effect
        )
      );
      generateMix();
    },
    []
  );

  const generateMix = useCallback(async () => {
    setLoading(true);
    try {
      // Prepare mix data
      const activeLayers = layers.filter((layer) => layer.enabled);
      const activeWeather = weatherEffects.filter((effect) => effect.enabled);
      
      const mixData = {
        environment_type: environmentType,
        layers: activeLayers.map((layer) => ({
          ...layer,
          volume: layer.volume * detailLevel,
        })),
        weather_effects: activeWeather,
        time_of_day: timeOfDay,
        speed_kmh: speed,
        adaptive_mode: adaptiveMode,
        detail_level: detailLevel,
      };

      // Call API to generate environmental audio
      const response = await apiManager.generateEnvironmentalAudio(
        {
          type: environmentType,
          terrain: location.terrain || 'flat',
          population_density: location.population_density || 'medium',
        },
        {
          type: weather.type,
          intensity: weather.intensity,
          wind_speed: weather.wind_speed,
        },
        {
          hour: getHourFromTimeOfDay(timeOfDay),
          season: 'spring', // Could be dynamic
        },
        speed / 3.6, // Convert km/h to m/s
        token
      );

      if (response.success) {
        onMixUpdate?.(response.environmental_audio);
      }
    } catch (error) {
      console.error('Error generating environmental mix:', error);
    } finally {
      setLoading(false);
    }
  }, [
    layers,
    weatherEffects,
    environmentType,
    timeOfDay,
    speed,
    adaptiveMode,
    detailLevel,
    location,
    weather,
    token,
    onMixUpdate,
  ]);

  const getHourFromTimeOfDay = (tod: string): number => {
    const hourMap: { [key: string]: number } = {
      dawn: 6,
      morning: 9,
      day: 14,
      dusk: 18,
      night: 22,
    };
    return hourMap[tod] || 12;
  };

  const applyPreset = useCallback((preset: string) => {
    switch (preset) {
      case 'immersive':
        setLayers((prev) =>
          prev.map((layer) => ({ ...layer, enabled: true, volume: 0.8 }))
        );
        setDetailLevel(1.2);
        break;
      case 'focused':
        setLayers((prev) =>
          prev.map((layer) => ({
            ...layer,
            enabled: layer.category === 'ambient',
            volume: 0.4,
          }))
        );
        setDetailLevel(0.6);
        break;
      case 'realistic':
        setAdaptiveMode(true);
        adaptToConditions();
        break;
    }
    generateMix();
  }, [adaptToConditions, generateMix]);

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Environment Selection */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Environment Type</Text>
        <View style={styles.pickerContainer}>
          <Picker
            selectedValue={environmentType}
            onValueChange={setEnvironmentType}
            style={styles.picker}
          >
            {environmentTypes.map((type) => (
              <Picker.Item key={type.value} label={type.label} value={type.value} />
            ))}
          </Picker>
        </View>
      </View>

      {/* Time of Day */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Time of Day</Text>
        <View style={styles.timePresets}>
          {timePresets.map((preset) => (
            <TouchableOpacity
              key={preset.value}
              style={[
                styles.timePresetButton,
                timeOfDay === preset.value && styles.selectedPreset,
              ]}
              onPress={() => onMixUpdate?.({ time_of_day: preset.value })}
            >
              <Icon
                name={preset.icon}
                size={24}
                color={timeOfDay === preset.value ? '#FFF' : '#666'}
              />
              <Text
                style={[
                  styles.timePresetText,
                  timeOfDay === preset.value && styles.selectedPresetText,
                ]}
              >
                {preset.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Adaptive Mode */}
      <View style={styles.section}>
        <View style={styles.switchRow}>
          <Icon name="auto-awesome" size={24} color="#666" />
          <Text style={styles.switchLabel}>Adaptive Mode</Text>
          <Switch
            value={adaptiveMode}
            onValueChange={setAdaptiveMode}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>
        <Text style={styles.helpText}>
          Automatically adjusts audio based on speed and conditions
        </Text>
      </View>

      {/* Environmental Layers */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Environmental Layers</Text>
        
        {layers.map((layer) => (
          <View key={layer.id} style={styles.layerContainer}>
            <View style={styles.layerHeader}>
              <Text style={[styles.layerName, !layer.enabled && styles.disabledText]}>
                {layer.name}
              </Text>
              <Switch
                value={layer.enabled}
                onValueChange={(enabled) => updateLayer(layer.id, { enabled })}
                trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
              />
            </View>
            
            {layer.enabled && (
              <>
                <Slider
                  style={styles.slider}
                  value={layer.volume}
                  onValueChange={(volume) => updateLayer(layer.id, { volume })}
                  minimumValue={0}
                  maximumValue={1}
                  minimumTrackTintColor="#007AFF"
                  maximumTrackTintColor="#E0E0E0"
                />
                <Text style={styles.volumeText}>
                  Volume: {Math.round(layer.volume * 100)}%
                </Text>
              </>
            )}
          </View>
        ))}
      </View>

      {/* Weather Effects */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Weather Effects</Text>
        
        {weatherEffects.map((effect) => (
          <View key={effect.type} style={styles.weatherEffect}>
            <View style={styles.effectHeader}>
              <Icon
                name={
                  effect.type === 'rain'
                    ? 'water-drop'
                    : effect.type === 'thunder'
                    ? 'bolt'
                    : 'air'
                }
                size={20}
                color={effect.enabled ? '#007AFF' : '#CCC'}
              />
              <Text style={[styles.effectName, !effect.enabled && styles.disabledText]}>
                {effect.type.charAt(0).toUpperCase() + effect.type.slice(1)}
              </Text>
              <Switch
                value={effect.enabled}
                onValueChange={(enabled) =>
                  updateWeatherEffect(effect.type, { enabled })
                }
                trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
              />
            </View>
            
            {effect.enabled && (
              <Slider
                style={styles.effectSlider}
                value={effect.intensity}
                onValueChange={(intensity) =>
                  updateWeatherEffect(effect.type, { intensity })
                }
                minimumValue={0}
                maximumValue={1}
                minimumTrackTintColor="#007AFF"
                maximumTrackTintColor="#E0E0E0"
              />
            )}
          </View>
        ))}
      </View>

      {/* Detail Level */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Detail Level</Text>
        <Text style={styles.detailText}>
          Current: {Math.round(detailLevel * 100)}% (Speed: {Math.round(speed)} km/h)
        </Text>
        <Slider
          style={styles.slider}
          value={detailLevel}
          onValueChange={setDetailLevel}
          minimumValue={0}
          maximumValue={1.5}
          minimumTrackTintColor="#007AFF"
          maximumTrackTintColor="#E0E0E0"
          disabled={adaptiveMode}
        />
      </View>

      {/* Quick Presets */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Quick Presets</Text>
        <View style={styles.presetButtons}>
          <TouchableOpacity
            style={styles.presetButton}
            onPress={() => applyPreset('immersive')}
          >
            <Icon name="surround-sound" size={20} color="#007AFF" />
            <Text style={styles.presetButtonText}>Immersive</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={styles.presetButton}
            onPress={() => applyPreset('focused')}
          >
            <Icon name="center-focus-strong" size={20} color="#007AFF" />
            <Text style={styles.presetButtonText}>Focused</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={styles.presetButton}
            onPress={() => applyPreset('realistic')}
          >
            <Icon name="auto-fix-high" size={20} color="#007AFF" />
            <Text style={styles.presetButtonText}>Realistic</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Generate Button */}
      <TouchableOpacity
        style={[styles.generateButton, loading && styles.generateButtonDisabled]}
        onPress={generateMix}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="white" />
        ) : (
          <>
            <Icon name="refresh" size={20} color="white" />
            <Text style={styles.generateButtonText}>Generate Mix</Text>
          </>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
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
  pickerContainer: {
    borderWidth: 1,
    borderColor: '#E0E0E0',
    borderRadius: 8,
    overflow: 'hidden',
  },
  picker: {
    height: 50,
  },
  timePresets: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  timePresetButton: {
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#F5F5F5',
  },
  selectedPreset: {
    backgroundColor: '#007AFF',
  },
  timePresetText: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  selectedPresetText: {
    color: 'white',
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  switchLabel: {
    flex: 1,
    fontSize: 16,
    color: '#333',
    marginLeft: 12,
  },
  helpText: {
    fontSize: 12,
    color: '#666',
    marginTop: 8,
    marginLeft: 36,
  },
  layerContainer: {
    marginBottom: 16,
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
  },
  disabledText: {
    color: '#CCC',
  },
  slider: {
    height: 40,
  },
  volumeText: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
  },
  weatherEffect: {
    marginBottom: 16,
  },
  effectHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  effectName: {
    flex: 1,
    fontSize: 16,
    color: '#333',
    marginLeft: 8,
  },
  effectSlider: {
    height: 30,
  },
  detailText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
  },
  presetButtons: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  presetButton: {
    alignItems: 'center',
    padding: 16,
    borderRadius: 8,
    backgroundColor: '#F5F5F5',
    flex: 1,
    marginHorizontal: 4,
  },
  presetButtonText: {
    fontSize: 12,
    color: '#007AFF',
    marginTop: 4,
  },
  generateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#007AFF',
    padding: 16,
    margin: 16,
    borderRadius: 8,
  },
  generateButtonDisabled: {
    opacity: 0.6,
  },
  generateButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
});