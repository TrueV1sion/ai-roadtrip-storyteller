import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Alert } from 'react-native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RouteProp } from '@react-navigation/native';
import { DrivingSafetyInterface } from '@/components/voice/DrivingSafetyInterface';
import { VoiceCommandProcessor } from '@/components/voice/VoiceCommandProcessor';
import { LargeButtonInterface } from '@/components/voice/LargeButtonInterface';
import { navigationService } from '@/services/navigation/navigationService';
import { voiceService } from '@/services/voice/voiceService';
import { RootStackParamList } from '../navigation/types';

type DrivingModeScreenNavigationProp = StackNavigationProp<
  RootStackParamList,
  'DrivingMode'
>;

type DrivingModeScreenRouteProp = RouteProp<RootStackParamList, 'DrivingMode'>;

type Props = {
  navigation: DrivingModeScreenNavigationProp;
  route: DrivingModeScreenRouteProp;
};

export const DrivingModeScreen: React.FC<Props> = ({ navigation, route }) => {
  const [isVoiceActive, setIsVoiceActive] = useState(true);
  const [showLargeButtons, setShowLargeButtons] = useState(false);
  
  useEffect(() => {
    // Announce driving mode activation
    voiceService.speak(
      'Driving mode activated. I\'ll guide you with voice commands. ' +
      'Say "show buttons" if you need visual controls.'
    );
    
    // Start navigation if destination provided
    if (route.params?.destination) {
      navigationService.startNavigation(route.params.destination);
    }
    
    return () => {
      // Clean up when leaving driving mode
      voiceService.speak('Driving mode deactivated');
    };
  }, []);
  
  const handleVoiceCommand = (command: string, result: any) => {
    // Handle driving-specific voice commands
    if (result.type === 'control') {
      if (result.action === 'show_buttons') {
        setShowLargeButtons(true);
        voiceService.speak('Showing visual controls');
      } else if (result.action === 'hide_buttons') {
        setShowLargeButtons(false);
        voiceService.speak('Visual controls hidden');
      } else if (result.action === 'exit_driving') {
        exitDrivingMode();
      }
    }
  };
  
  const exitDrivingMode = () => {
    Alert.alert(
      'Exit Driving Mode',
      'Are you sure you want to exit driving mode?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Exit',
          onPress: () => {
            navigationService.stopNavigation();
            navigation.goBack();
          },
        },
      ],
      { cancelable: true }
    );
  };
  
  const handleNavigate = () => {
    voiceService.speak('Say your destination');
    // Voice command processor will handle the actual navigation
  };
  
  const handleBook = () => {
    navigation.navigate('VoiceBooking', { isDriving: true });
  };
  
  const handleStory = () => {
    voiceService.speak('What would you like to hear about?');
    // Voice command processor will handle story selection
  };
  
  const handleEmergency = () => {
    Alert.alert(
      'Emergency Assistance',
      'Do you need emergency help?',
      [
        {
          text: 'Call 911',
          onPress: () => {
            // In production, this would initiate emergency call
            voiceService.speak('Calling emergency services');
          },
          style: 'destructive',
        },
        {
          text: 'Roadside Assistance',
          onPress: () => {
            voiceService.speak('Connecting to roadside assistance');
          },
        },
        { text: 'Cancel', style: 'cancel' },
      ],
      { cancelable: true }
    );
  };
  
  const handleVoiceActivate = () => {
    setIsVoiceActive(!isVoiceActive);
    voiceService.speak(isVoiceActive ? 'Voice control paused' : 'Voice control activated');
  };
  
  return (
    <View style={styles.container}>
      {/* Voice Command Processor - always active */}
      <VoiceCommandProcessor
        onCommandProcessed={handleVoiceCommand}
        continuousListening={isVoiceActive}
      />
      
      {/* Show either driving safety interface or large buttons */}
      {showLargeButtons ? (
        <LargeButtonInterface
          onNavigate={handleNavigate}
          onBook={handleBook}
          onStory={handleStory}
          onEmergency={handleEmergency}
          onVoiceActivate={handleVoiceActivate}
          isDriving={true}
        />
      ) : (
        <DrivingSafetyInterface
          navigation={navigation}
          route={route}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
});

export default DrivingModeScreen;