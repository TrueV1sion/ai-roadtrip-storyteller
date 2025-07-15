import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  StatusBar,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useKeepAwake } from 'expo-keep-awake';
import { VoiceNavigationInterface } from './VoiceNavigationInterface';
import { navigationService } from '../../services/navigation/navigationService';
import { voiceService } from '../../services/voice/voiceService';

const { width, height } = Dimensions.get('window');

interface DrivingSafetyInterfaceProps {
  navigation: any;
  route: any;
}

export const DrivingSafetyInterface: React.FC<DrivingSafetyInterfaceProps> = ({
  navigation,
  route,
}) => {
  const insets = useSafeAreaInsets();
  const [currentSpeed, setCurrentSpeed] = useState(0);
  const [nextDirection, setNextDirection] = useState('');
  const [distanceToNext, setDistanceToNext] = useState('');
  const [eta, setEta] = useState('');
  const [isNightMode, setIsNightMode] = useState(false);
  
  // Keep screen awake while driving
  useKeepAwake();
  
  useEffect(() => {
    // Subscribe to navigation updates
    const unsubscribe = navigationService.subscribeToUpdates((update) => {
      if (update.currentSpeed) setCurrentSpeed(update.currentSpeed);
      if (update.nextDirection) setNextDirection(update.nextDirection);
      if (update.distanceToNext) setDistanceToNext(update.distanceToNext);
      if (update.eta) setEta(update.eta);
    });
    
    // Auto-detect night mode based on time
    const hour = new Date().getHours();
    setIsNightMode(hour < 6 || hour > 20);
    
    // Announce start of driving mode
    voiceService.speak('Driving mode activated. I\'ll keep the screen simple and use voice for all interactions.');
    
    return () => {
      unsubscribe();
    };
  }, []);
  
  const handleEmergencyStop = async () => {
    await navigationService.stopNavigation();
    await voiceService.stopAll();
    voiceService.speak('Navigation stopped. All activities paused.');
    navigation.goBack();
  };
  
  const handleQuickAction = async (action: string) => {
    switch (action) {
      case 'mute':
        await voiceService.toggleMute();
        break;
      case 'louder':
        await voiceService.increaseVolume();
        break;
      case 'quieter':
        await voiceService.decreaseVolume();
        break;
      case 'pause':
        await voiceService.pauseStory();
        break;
    }
  };
  
  const backgroundColor = isNightMode ? '#000' : '#FFF';
  const textColor = isNightMode ? '#FFF' : '#000';
  const accentColor = isNightMode ? '#4CAF50' : '#007AFF';
  
  return (
    <View style={[styles.container, { backgroundColor, paddingTop: insets.top }]}>
      <StatusBar barStyle={isNightMode ? 'light-content' : 'dark-content'} />
      
      {/* Minimal navigation display */}
      <View style={styles.navigationDisplay}>
        {/* Next direction */}
        <View style={styles.directionContainer}>
          <Text style={[styles.directionArrow, { color: accentColor }]}>
            {getDirectionArrow(nextDirection)}
          </Text>
          <Text style={[styles.distanceText, { color: textColor }]}>
            {distanceToNext}
          </Text>
        </View>
        
        {/* Current speed */}
        <View style={styles.speedContainer}>
          <Text style={[styles.speedValue, { color: textColor }]}>
            {currentSpeed}
          </Text>
          <Text style={[styles.speedUnit, { color: textColor }]}>
            mph
          </Text>
        </View>
        
        {/* ETA */}
        <View style={styles.etaContainer}>
          <Text style={[styles.etaLabel, { color: textColor }]}>
            ETA
          </Text>
          <Text style={[styles.etaValue, { color: textColor }]}>
            {eta}
          </Text>
        </View>
      </View>
      
      {/* Voice control area - takes most of the screen */}
      <View style={styles.voiceControlArea}>
        <VoiceNavigationInterface isDriving={true} />
      </View>
      
      {/* Quick action buttons - large and easy to tap */}
      <View style={[styles.quickActions, { paddingBottom: insets.bottom + 20 }]}>
        <TouchableOpacity
          style={[styles.quickButton, { backgroundColor: accentColor }]}
          onPress={() => handleQuickAction('mute')}
          activeOpacity={0.8}
        >
          <Text style={styles.quickButtonIcon}>🔇</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.quickButton, { backgroundColor: accentColor }]}
          onPress={() => handleQuickAction('pause')}
          activeOpacity={0.8}
        >
          <Text style={styles.quickButtonIcon}>⏸️</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.emergencyButton]}
          onPress={handleEmergencyStop}
          activeOpacity={0.8}
        >
          <Text style={styles.emergencyButtonText}>STOP</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

// Helper function to get direction arrow
const getDirectionArrow = (direction: string): string => {
  const directionMap: { [key: string]: string } = {
    'straight': '↑',
    'left': '←',
    'right': '→',
    'slight-left': '↖',
    'slight-right': '↗',
    'u-turn': '↻',
    'merge': '↔',
  };
  
  return directionMap[direction.toLowerCase()] || '↑';
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  navigationDisplay: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(128, 128, 128, 0.2)',
  },
  directionContainer: {
    alignItems: 'center',
  },
  directionArrow: {
    fontSize: 48,
    fontWeight: 'bold',
  },
  distanceText: {
    fontSize: 18,
    marginTop: 5,
  },
  speedContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
  },
  speedValue: {
    fontSize: 48,
    fontWeight: 'bold',
  },
  speedUnit: {
    fontSize: 20,
    marginLeft: 5,
  },
  etaContainer: {
    alignItems: 'center',
  },
  etaLabel: {
    fontSize: 14,
    opacity: 0.7,
  },
  etaValue: {
    fontSize: 24,
    fontWeight: 'bold',
    marginTop: 5,
  },
  voiceControlArea: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  quickActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 20,
  },
  quickButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  quickButtonIcon: {
    fontSize: 36,
  },
  emergencyButton: {
    width: 100,
    height: 80,
    backgroundColor: '#FF3B30',
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emergencyButtonText: {
    color: '#FFF',
    fontSize: 24,
    fontWeight: 'bold',
  },
});