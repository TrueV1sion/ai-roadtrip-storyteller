import React, { useState } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  Switch,
  Slider,
  ScrollView,
  Platform
} from 'react-native';
import { FontAwesome5, MaterialIcons, AntDesign } from '@expo/vector-icons';
import { ApiClient } from '../../services/api/ApiClient';
import { ARRenderSettingsUpdate } from '../../types/ar';

interface ARControlsProps {
  onClose: () => void;
}

const ARControls: React.FC<ARControlsProps> = ({ onClose }) => {
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    distance_scale: 1.0,
    opacity: 0.85,
    color_scheme: 'default',
    show_labels: true,
    show_distances: true,
    show_arrows: true,
    animation_speed: 1.0,
    detail_level: 2,
    accessibility_mode: false
  });

  const toggleSettings = () => {
    setShowSettings(!showSettings);
  };

  const handleSettingChange = async (key: string, value: any) => {
    // Update local state
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));

    // Send update to server
    try {
      const updatePayload: ARRenderSettingsUpdate = {
        [key]: value
      };
      
      await ApiClient.patch('/ar/render/settings', updatePayload);
    } catch (error) {
      logger.error('Failed to update AR settings:', error);
    }
  };

  // Color scheme options
  const colorSchemes = [
    { label: 'Default', value: 'default' },
    { label: 'High Contrast', value: 'high_contrast' },
    { label: 'Pastel', value: 'pastel' },
    { label: 'Night', value: 'night' },
    { label: 'Vintage', value: 'vintage' }
  ];

  return (
    <View style={styles.container}>
      <View style={styles.controlsBar}>
        <TouchableOpacity style={styles.controlButton} onPress={toggleSettings}>
          <FontAwesome5 name="sliders-h" size={22} color="white" />
        </TouchableOpacity>
        
        <View style={styles.controlsDivider} />
        
        <TouchableOpacity style={styles.controlButton}>
          <MaterialIcons name="layers" size={24} color="white" />
        </TouchableOpacity>
        
        <View style={styles.controlsDivider} />
        
        <TouchableOpacity style={styles.controlButton}>
          <FontAwesome5 name="compass" size={22} color="white" />
        </TouchableOpacity>
        
        <View style={styles.spacer} />
        
        <TouchableOpacity style={styles.closeButton} onPress={onClose}>
          <AntDesign name="close" size={24} color="white" />
        </TouchableOpacity>
      </View>
      
      {/* Settings Modal */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={showSettings}
        onRequestClose={() => setShowSettings(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>AR Settings</Text>
              <TouchableOpacity onPress={() => setShowSettings(false)}>
                <AntDesign name="close" size={24} color="#333" />
              </TouchableOpacity>
            </View>
            
            <ScrollView style={styles.settingsScrollView}>
              {/* Accessibility Mode */}
              <View style={styles.settingRow}>
                <Text style={styles.settingLabel}>Accessibility Mode</Text>
                <Switch
                  value={settings.accessibility_mode}
                  onValueChange={(value) => handleSettingChange('accessibility_mode', value)}
                  trackColor={{ false: '#767577', true: '#81b0ff' }}
                  thumbColor={settings.accessibility_mode ? '#2196F3' : '#f4f3f4'}
                  ios_backgroundColor="#3e3e3e"
                />
              </View>
              
              {/* Show Labels */}
              <View style={styles.settingRow}>
                <Text style={styles.settingLabel}>Show Labels</Text>
                <Switch
                  value={settings.show_labels}
                  onValueChange={(value) => handleSettingChange('show_labels', value)}
                  trackColor={{ false: '#767577', true: '#81b0ff' }}
                  thumbColor={settings.show_labels ? '#2196F3' : '#f4f3f4'}
                  ios_backgroundColor="#3e3e3e"
                />
              </View>
              
              {/* Show Distances */}
              <View style={styles.settingRow}>
                <Text style={styles.settingLabel}>Show Distances</Text>
                <Switch
                  value={settings.show_distances}
                  onValueChange={(value) => handleSettingChange('show_distances', value)}
                  trackColor={{ false: '#767577', true: '#81b0ff' }}
                  thumbColor={settings.show_distances ? '#2196F3' : '#f4f3f4'}
                  ios_backgroundColor="#3e3e3e"
                />
              </View>
              
              {/* Show Arrows */}
              <View style={styles.settingRow}>
                <Text style={styles.settingLabel}>Show Direction Arrows</Text>
                <Switch
                  value={settings.show_arrows}
                  onValueChange={(value) => handleSettingChange('show_arrows', value)}
                  trackColor={{ false: '#767577', true: '#81b0ff' }}
                  thumbColor={settings.show_arrows ? '#2196F3' : '#f4f3f4'}
                  ios_backgroundColor="#3e3e3e"
                />
              </View>
              
              {/* Opacity Slider */}
              <View style={styles.sliderSettingRow}>
                <Text style={styles.settingLabel}>Element Opacity: {Math.round(settings.opacity * 100)}%</Text>
                <Slider
                  style={styles.slider}
                  minimumValue={0.3}
                  maximumValue={1.0}
                  step={0.05}
                  value={settings.opacity}
                  onValueChange={(value) => setSettings(prev => ({ ...prev, opacity: value }))}
                  onSlidingComplete={(value) => handleSettingChange('opacity', value)}
                  minimumTrackTintColor="#2196F3"
                  maximumTrackTintColor="#d3d3d3"
                  thumbTintColor="#2196F3"
                />
              </View>
              
              {/* Distance Scale Slider */}
              <View style={styles.sliderSettingRow}>
                <Text style={styles.settingLabel}>Distance Scale: {settings.distance_scale.toFixed(1)}x</Text>
                <Slider
                  style={styles.slider}
                  minimumValue={0.5}
                  maximumValue={2.0}
                  step={0.1}
                  value={settings.distance_scale}
                  onValueChange={(value) => setSettings(prev => ({ ...prev, distance_scale: value }))}
                  onSlidingComplete={(value) => handleSettingChange('distance_scale', value)}
                  minimumTrackTintColor="#2196F3"
                  maximumTrackTintColor="#d3d3d3"
                  thumbTintColor="#2196F3"
                />
              </View>
              
              {/* Animation Speed Slider */}
              <View style={styles.sliderSettingRow}>
                <Text style={styles.settingLabel}>Animation Speed: {settings.animation_speed.toFixed(1)}x</Text>
                <Slider
                  style={styles.slider}
                  minimumValue={0.5}
                  maximumValue={2.0}
                  step={0.1}
                  value={settings.animation_speed}
                  onValueChange={(value) => setSettings(prev => ({ ...prev, animation_speed: value }))}
                  onSlidingComplete={(value) => handleSettingChange('animation_speed', value)}
                  minimumTrackTintColor="#2196F3"
                  maximumTrackTintColor="#d3d3d3"
                  thumbTintColor="#2196F3"
                />
              </View>
              
              {/* Detail Level */}
              <View style={styles.sliderSettingRow}>
                <Text style={styles.settingLabel}>Detail Level: {settings.detail_level}</Text>
                <Slider
                  style={styles.slider}
                  minimumValue={1}
                  maximumValue={3}
                  step={1}
                  value={settings.detail_level}
                  onValueChange={(value) => setSettings(prev => ({ ...prev, detail_level: Math.round(value) }))}
                  onSlidingComplete={(value) => handleSettingChange('detail_level', Math.round(value))}
                  minimumTrackTintColor="#2196F3"
                  maximumTrackTintColor="#d3d3d3"
                  thumbTintColor="#2196F3"
                />
              </View>
              
              {/* Color Scheme Selector */}
              <Text style={[styles.settingLabel, { marginTop: 10 }]}>Color Scheme</Text>
              <View style={styles.colorSchemeContainer}>
                {colorSchemes.map((scheme) => (
                  <TouchableOpacity
                    key={scheme.value}
                    style={[
                      styles.colorSchemeButton,
                      settings.color_scheme === scheme.value && styles.colorSchemeSelected
                    ]}
                    onPress={() => handleSettingChange('color_scheme', scheme.value)}
                  >
                    <Text style={[
                      styles.colorSchemeText,
                      settings.color_scheme === scheme.value && styles.colorSchemeTextSelected
                    ]}>
                      {scheme.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
              
              {/* Reset Button */}
              <TouchableOpacity 
                style={styles.resetButton}
                onPress={() => {
                  // Reset to defaults
                  const defaults = {
                    distance_scale: 1.0,
                    opacity: 0.85,
                    color_scheme: 'default',
                    show_labels: true,
                    show_distances: true,
                    show_arrows: true,
                    animation_speed: 1.0,
                    detail_level: 2,
                    accessibility_mode: false
                  };
                  setSettings(defaults);
                  
                  // Send to server
                  ApiClient.patch('/ar/render/settings', defaults)
                    .catch(error => logger.error('Failed to reset AR settings:', error));
                }}
              >
                <Text style={styles.resetButtonText}>Reset to Defaults</Text>
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: Platform.OS === 'ios' ? 50 : 20,
    right: 0,
    left: 0,
    alignItems: 'center',
  },
  controlsBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: 25,
    paddingHorizontal: 15,
    paddingVertical: 10,
  },
  controlButton: {
    padding: 10,
  },
  controlsDivider: {
    width: 1,
    height: 20,
    backgroundColor: 'rgba(255,255,255,0.3)',
    marginHorizontal: 5,
  },
  spacer: {
    flex: 1,
    minWidth: 20,
  },
  closeButton: {
    padding: 10,
    backgroundColor: 'rgba(255,0,0,0.5)',
    borderRadius: 20,
  },
  modalContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  modalContent: {
    width: '85%',
    maxHeight: '80%',
    backgroundColor: 'white',
    borderRadius: 15,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    paddingBottom: 10,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  settingsScrollView: {
    maxHeight: '90%',
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  sliderSettingRow: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  settingLabel: {
    fontSize: 16,
    color: '#333',
  },
  slider: {
    width: '100%',
    height: 40,
  },
  colorSchemeContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: 5,
    marginBottom: 15,
  },
  colorSchemeButton: {
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#f0f0f0',
    margin: 5,
  },
  colorSchemeSelected: {
    backgroundColor: '#2196F3',
  },
  colorSchemeText: {
    fontSize: 14,
    color: '#333',
  },
  colorSchemeTextSelected: {
    color: 'white',
  },
  resetButton: {
    backgroundColor: '#f44336',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 20,
    marginBottom: 10,
  },
  resetButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default ARControls;