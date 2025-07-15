import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
} from 'react-native';
import Slider from '@react-native-community/slider';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { Picker } from '@react-native-picker/picker';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiManager } from '../../services/api/apiManager';
import { useAuth } from '../../contexts/AuthContext';

interface AudioSettings {
  // Audio Quality
  quality: 'low' | 'medium' | 'high' | 'adaptive';
  bitrate: number;
  sampleRate: number;
  
  // Spatial Audio
  spatialAudioEnabled: boolean;
  binauralEnabled: boolean;
  hrtfProfile: 'generic' | 'personalized';
  roomSimulation: boolean;
  
  // Processing
  dynamicRangeCompression: boolean;
  compressionRatio: number;
  noiseReduction: boolean;
  voiceEnhancement: boolean;
  
  // Accessibility
  monoAudio: boolean;
  audioBalance: number; // -1 (left) to 1 (right)
  subtitlesEnabled: boolean;
  audioDescriptions: boolean;
  
  // Performance
  bufferSize: number;
  preloadDuration: number;
  cacheSize: number;
  offlineMode: boolean;
  
  // Safety
  volumeLimiter: boolean;
  maxVolume: number;
  duckingEnabled: boolean;
  emergencyAlerts: boolean;
}

export const AudioSettingsPanel: React.FC = () => {
  const { token } = useAuth();
  const [settings, setSettings] = useState<AudioSettings>({
    quality: 'high',
    bitrate: 256,
    sampleRate: 44100,
    spatialAudioEnabled: true,
    binauralEnabled: true,
    hrtfProfile: 'generic',
    roomSimulation: false,
    dynamicRangeCompression: true,
    compressionRatio: 2.0,
    noiseReduction: true,
    voiceEnhancement: true,
    monoAudio: false,
    audioBalance: 0,
    subtitlesEnabled: false,
    audioDescriptions: false,
    bufferSize: 2048,
    preloadDuration: 30,
    cacheSize: 100,
    offlineMode: false,
    volumeLimiter: true,
    maxVolume: 0.85,
    duckingEnabled: true,
    emergencyAlerts: true,
  });
  const [unsavedChanges, setUnsavedChanges] = useState(false);

  const updateSetting = useCallback(<K extends keyof AudioSettings>(
    key: K,
    value: AudioSettings[K]
  ) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setUnsavedChanges(true);
  }, []);

  const saveSettings = useCallback(async () => {
    try {
      // Save to local storage
      await AsyncStorage.setItem('audioSettings', JSON.stringify(settings));
      
      // Save to backend
      await apiManager.saveAudioPreferences(settings, token);
      
      setUnsavedChanges(false);
      Alert.alert('Success', 'Audio settings saved successfully');
    } catch (error) {
      console.error('Error saving settings:', error);
      Alert.alert('Error', 'Failed to save audio settings');
    }
  }, [settings, token]);

  const resetToDefaults = useCallback(() => {
    Alert.alert(
      'Reset Settings',
      'Are you sure you want to reset all audio settings to defaults?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: () => {
            setSettings({
              quality: 'high',
              bitrate: 256,
              sampleRate: 44100,
              spatialAudioEnabled: true,
              binauralEnabled: true,
              hrtfProfile: 'generic',
              roomSimulation: false,
              dynamicRangeCompression: true,
              compressionRatio: 2.0,
              noiseReduction: true,
              voiceEnhancement: true,
              monoAudio: false,
              audioBalance: 0,
              subtitlesEnabled: false,
              audioDescriptions: false,
              bufferSize: 2048,
              preloadDuration: 30,
              cacheSize: 100,
              offlineMode: false,
              volumeLimiter: true,
              maxVolume: 0.85,
              duckingEnabled: true,
              emergencyAlerts: true,
            });
            setUnsavedChanges(true);
          },
        },
      ]
    );
  }, []);

  const calibrateHRTF = useCallback(async () => {
    Alert.alert(
      'HRTF Calibration',
      'This will play test sounds to calibrate spatial audio for your ears. Make sure you are wearing headphones.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Start',
          onPress: async () => {
            // In a real implementation, this would start the calibration process
            Alert.alert('Coming Soon', 'HRTF calibration will be available in a future update.');
          },
        },
      ]
    );
  }, []);

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Audio Quality Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Icon name="high-quality" size={24} color="#007AFF" />
          <Text style={styles.sectionTitle}>Audio Quality</Text>
        </View>
        
        <View style={styles.setting}>
          <Text style={styles.settingLabel}>Quality Preset</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={settings.quality}
              onValueChange={(value) => updateSetting('quality', value)}
              style={styles.picker}
            >
              <Picker.Item label="Low (64 kbps)" value="low" />
              <Picker.Item label="Medium (128 kbps)" value="medium" />
              <Picker.Item label="High (256 kbps)" value="high" />
              <Picker.Item label="Adaptive" value="adaptive" />
            </Picker>
          </View>
        </View>

        <View style={styles.setting}>
          <Text style={styles.settingLabel}>Sample Rate</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={settings.sampleRate}
              onValueChange={(value) => updateSetting('sampleRate', value)}
              style={styles.picker}
            >
              <Picker.Item label="22.05 kHz" value={22050} />
              <Picker.Item label="44.1 kHz (CD Quality)" value={44100} />
              <Picker.Item label="48 kHz (Studio)" value={48000} />
            </Picker>
          </View>
        </View>
      </View>

      {/* Spatial Audio Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Icon name="3d-rotation" size={24} color="#007AFF" />
          <Text style={styles.sectionTitle}>Spatial Audio</Text>
        </View>
        
        <View style={styles.switchSetting}>
          <Text style={styles.settingLabel}>Enable Spatial Audio</Text>
          <Switch
            value={settings.spatialAudioEnabled}
            onValueChange={(value) => updateSetting('spatialAudioEnabled', value)}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>

        {settings.spatialAudioEnabled && (
          <>
            <View style={styles.switchSetting}>
              <Text style={styles.settingLabel}>Binaural Processing</Text>
              <Switch
                value={settings.binauralEnabled}
                onValueChange={(value) => updateSetting('binauralEnabled', value)}
                trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
              />
            </View>

            <View style={styles.switchSetting}>
              <Text style={styles.settingLabel}>Room Simulation</Text>
              <Switch
                value={settings.roomSimulation}
                onValueChange={(value) => updateSetting('roomSimulation', value)}
                trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
              />
            </View>

            <TouchableOpacity style={styles.calibrateButton} onPress={calibrateHRTF}>
              <Icon name="hearing" size={20} color="#007AFF" />
              <Text style={styles.calibrateButtonText}>Calibrate HRTF Profile</Text>
            </TouchableOpacity>
          </>
        )}
      </View>

      {/* Audio Processing Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Icon name="equalizer" size={24} color="#007AFF" />
          <Text style={styles.sectionTitle}>Audio Processing</Text>
        </View>
        
        <View style={styles.switchSetting}>
          <Text style={styles.settingLabel}>Dynamic Range Compression</Text>
          <Switch
            value={settings.dynamicRangeCompression}
            onValueChange={(value) => updateSetting('dynamicRangeCompression', value)}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>

        {settings.dynamicRangeCompression && (
          <View style={styles.setting}>
            <Text style={styles.settingLabel}>
              Compression Ratio: {settings.compressionRatio.toFixed(1)}:1
            </Text>
            <Slider
              style={styles.slider}
              value={settings.compressionRatio}
              onValueChange={(value) => updateSetting('compressionRatio', value)}
              minimumValue={1}
              maximumValue={10}
              minimumTrackTintColor="#007AFF"
              maximumTrackTintColor="#E0E0E0"
            />
          </View>
        )}

        <View style={styles.switchSetting}>
          <Text style={styles.settingLabel}>Noise Reduction</Text>
          <Switch
            value={settings.noiseReduction}
            onValueChange={(value) => updateSetting('noiseReduction', value)}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>

        <View style={styles.switchSetting}>
          <Text style={styles.settingLabel}>Voice Enhancement</Text>
          <Switch
            value={settings.voiceEnhancement}
            onValueChange={(value) => updateSetting('voiceEnhancement', value)}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>
      </View>

      {/* Accessibility Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Icon name="accessibility" size={24} color="#007AFF" />
          <Text style={styles.sectionTitle}>Accessibility</Text>
        </View>
        
        <View style={styles.switchSetting}>
          <Text style={styles.settingLabel}>Mono Audio</Text>
          <Switch
            value={settings.monoAudio}
            onValueChange={(value) => updateSetting('monoAudio', value)}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>

        {!settings.monoAudio && (
          <View style={styles.setting}>
            <Text style={styles.settingLabel}>Audio Balance</Text>
            <View style={styles.balanceContainer}>
              <Text style={styles.balanceLabel}>L</Text>
              <Slider
                style={styles.balanceSlider}
                value={settings.audioBalance}
                onValueChange={(value) => updateSetting('audioBalance', value)}
                minimumValue={-1}
                maximumValue={1}
                minimumTrackTintColor="#007AFF"
                maximumTrackTintColor="#007AFF"
              />
              <Text style={styles.balanceLabel}>R</Text>
            </View>
          </View>
        )}

        <View style={styles.switchSetting}>
          <Text style={styles.settingLabel}>Enable Subtitles</Text>
          <Switch
            value={settings.subtitlesEnabled}
            onValueChange={(value) => updateSetting('subtitlesEnabled', value)}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>

        <View style={styles.switchSetting}>
          <Text style={styles.settingLabel}>Audio Descriptions</Text>
          <Switch
            value={settings.audioDescriptions}
            onValueChange={(value) => updateSetting('audioDescriptions', value)}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>
      </View>

      {/* Performance Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Icon name="speed" size={24} color="#007AFF" />
          <Text style={styles.sectionTitle}>Performance</Text>
        </View>
        
        <View style={styles.setting}>
          <Text style={styles.settingLabel}>Buffer Size</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={settings.bufferSize}
              onValueChange={(value) => updateSetting('bufferSize', value)}
              style={styles.picker}
            >
              <Picker.Item label="Small (512)" value={512} />
              <Picker.Item label="Medium (1024)" value={1024} />
              <Picker.Item label="Large (2048)" value={2048} />
              <Picker.Item label="Extra Large (4096)" value={4096} />
            </Picker>
          </View>
        </View>

        <View style={styles.setting}>
          <Text style={styles.settingLabel}>
            Preload Duration: {settings.preloadDuration}s
          </Text>
          <Slider
            style={styles.slider}
            value={settings.preloadDuration}
            onValueChange={(value) => updateSetting('preloadDuration', Math.round(value))}
            minimumValue={10}
            maximumValue={60}
            minimumTrackTintColor="#007AFF"
            maximumTrackTintColor="#E0E0E0"
          />
        </View>

        <View style={styles.setting}>
          <Text style={styles.settingLabel}>
            Cache Size: {settings.cacheSize} MB
          </Text>
          <Slider
            style={styles.slider}
            value={settings.cacheSize}
            onValueChange={(value) => updateSetting('cacheSize', Math.round(value))}
            minimumValue={50}
            maximumValue={500}
            minimumTrackTintColor="#007AFF"
            maximumTrackTintColor="#E0E0E0"
          />
        </View>

        <View style={styles.switchSetting}>
          <Text style={styles.settingLabel}>Offline Mode</Text>
          <Switch
            value={settings.offlineMode}
            onValueChange={(value) => updateSetting('offlineMode', value)}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>
      </View>

      {/* Safety Section */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Icon name="security" size={24} color="#007AFF" />
          <Text style={styles.sectionTitle}>Safety</Text>
        </View>
        
        <View style={styles.switchSetting}>
          <Text style={styles.settingLabel}>Volume Limiter</Text>
          <Switch
            value={settings.volumeLimiter}
            onValueChange={(value) => updateSetting('volumeLimiter', value)}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>

        {settings.volumeLimiter && (
          <View style={styles.setting}>
            <Text style={styles.settingLabel}>
              Max Volume: {Math.round(settings.maxVolume * 100)}%
            </Text>
            <Slider
              style={styles.slider}
              value={settings.maxVolume}
              onValueChange={(value) => updateSetting('maxVolume', value)}
              minimumValue={0.5}
              maximumValue={1}
              minimumTrackTintColor="#007AFF"
              maximumTrackTintColor="#E0E0E0"
            />
          </View>
        )}

        <View style={styles.switchSetting}>
          <Text style={styles.settingLabel}>Audio Ducking</Text>
          <Switch
            value={settings.duckingEnabled}
            onValueChange={(value) => updateSetting('duckingEnabled', value)}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>

        <View style={styles.switchSetting}>
          <Text style={styles.settingLabel}>Emergency Alerts</Text>
          <Switch
            value={settings.emergencyAlerts}
            onValueChange={(value) => updateSetting('emergencyAlerts', value)}
            trackColor={{ false: '#E0E0E0', true: '#007AFF' }}
          />
        </View>
      </View>

      {/* Action Buttons */}
      <View style={styles.actionButtons}>
        <TouchableOpacity style={styles.resetButton} onPress={resetToDefaults}>
          <Icon name="refresh" size={20} color="#FF3B30" />
          <Text style={styles.resetButtonText}>Reset to Defaults</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.saveButton, !unsavedChanges && styles.saveButtonDisabled]}
          onPress={saveSettings}
          disabled={!unsavedChanges}
        >
          <Icon name="save" size={20} color="white" />
          <Text style={styles.saveButtonText}>Save Settings</Text>
        </TouchableOpacity>
      </View>
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
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginLeft: 8,
  },
  setting: {
    marginBottom: 20,
  },
  settingLabel: {
    fontSize: 16,
    color: '#333',
    marginBottom: 8,
  },
  switchSetting: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
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
  slider: {
    height: 40,
  },
  balanceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  balanceLabel: {
    fontSize: 14,
    color: '#666',
    width: 20,
    textAlign: 'center',
  },
  balanceSlider: {
    flex: 1,
    height: 40,
  },
  calibrateButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F5F5F5',
    padding: 12,
    borderRadius: 8,
    marginTop: 12,
  },
  calibrateButtonText: {
    fontSize: 16,
    color: '#007AFF',
    marginLeft: 8,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 16,
  },
  resetButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFE5E5',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
  },
  resetButtonText: {
    fontSize: 16,
    color: '#FF3B30',
    marginLeft: 8,
  },
  saveButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#007AFF',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
  },
  saveButtonDisabled: {
    opacity: 0.5,
  },
  saveButtonText: {
    fontSize: 16,
    color: 'white',
    marginLeft: 8,
    fontWeight: '600',
  },
});