import React from 'react';
import { View, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';

import { useTheme } from '../hooks/useTheme';

interface NavigationMapControlsProps {
  mapMode: 'navigation' | 'overview';
  onToggleMode: () => void;
  onRecenter: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
}

export const NavigationMapControls: React.FC<NavigationMapControlsProps> = ({
  mapMode,
  onToggleMode,
  onRecenter,
  onZoomIn,
  onZoomOut
}) => {
  const { theme } = useTheme();

  return (
    <View style={styles.container}>
      {/* Map mode toggle */}
      <TouchableOpacity onPress={onToggleMode} style={styles.controlButton}>
        <BlurView intensity={80} style={styles.blurButton}>
          <View style={[styles.buttonContent, { backgroundColor: theme.colors.background + 'dd' }]}>
            <MaterialIcons
              name={mapMode === 'navigation' ? 'explore' : 'navigation'}
              size={28}
              color={theme.colors.primary}
            />
          </View>
        </BlurView>
      </TouchableOpacity>

      {/* Recenter button */}
      <TouchableOpacity onPress={onRecenter} style={styles.controlButton}>
        <BlurView intensity={80} style={styles.blurButton}>
          <View style={[styles.buttonContent, { backgroundColor: theme.colors.background + 'dd' }]}>
            <MaterialIcons
              name="my-location"
              size={28}
              color={theme.colors.primary}
            />
          </View>
        </BlurView>
      </TouchableOpacity>

      {/* Zoom controls */}
      <View style={styles.zoomControls}>
        <TouchableOpacity onPress={onZoomIn} style={styles.zoomButton}>
          <BlurView intensity={80} style={styles.blurButton}>
            <View style={[styles.buttonContent, { backgroundColor: theme.colors.background + 'dd' }]}>
              <MaterialIcons
                name="add"
                size={24}
                color={theme.colors.text}
              />
            </View>
          </BlurView>
        </TouchableOpacity>
        
        <TouchableOpacity onPress={onZoomOut} style={styles.zoomButton}>
          <BlurView intensity={80} style={styles.blurButton}>
            <View style={[styles.buttonContent, { backgroundColor: theme.colors.background + 'dd' }]}>
              <MaterialIcons
                name="remove"
                size={24}
                color={theme.colors.text}
              />
            </View>
          </BlurView>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    right: 16,
    top: '50%',
    transform: [{ translateY: -100 }],
  },
  controlButton: {
    marginBottom: 12,
  },
  blurButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    overflow: 'hidden',
  },
  buttonContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  zoomControls: {
    marginTop: 24,
  },
  zoomButton: {
    marginBottom: 8,
  },
});