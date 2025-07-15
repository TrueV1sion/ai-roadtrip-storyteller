import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  ScrollView,
  Vibration,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { voiceService } from '../../services/voice/voiceService';

const { width } = Dimensions.get('window');

interface LargeButtonInterfaceProps {
  onNavigate?: () => void;
  onBook?: () => void;
  onStory?: () => void;
  onEmergency?: () => void;
  onVoiceActivate?: () => void;
  isDriving?: boolean;
}

export const LargeButtonInterface: React.FC<LargeButtonInterfaceProps> = ({
  onNavigate,
  onBook,
  onStory,
  onEmergency,
  onVoiceActivate,
  isDriving = false,
}) => {
  const insets = useSafeAreaInsets();
  
  const handleButtonPress = async (action: string, callback?: () => void) => {
    // Haptic feedback for button press
    Vibration.vibrate(50);
    
    // Voice confirmation
    await voiceService.speak(`${action} activated`);
    
    if (callback) {
      callback();
    }
  };
  
  const buttonSize = isDriving ? width * 0.4 : width * 0.35;
  const fontSize = isDriving ? 24 : 20;
  
  return (
    <ScrollView 
      style={[styles.container, isDriving && styles.drivingContainer]}
      contentContainerStyle={[styles.scrollContent, { paddingBottom: insets.bottom + 20 }]}
      showsVerticalScrollIndicator={false}
    >
      {/* Voice activation - always at top */}
      <TouchableOpacity
        style={[
          styles.voiceButton,
          { width: buttonSize, height: buttonSize },
          isDriving && styles.drivingButton,
        ]}
        onPress={() => handleButtonPress('Voice control', onVoiceActivate)}
        activeOpacity={0.8}
      >
        <Text style={styles.buttonIcon}>🎙️</Text>
        <Text style={[styles.buttonText, { fontSize }, isDriving && styles.drivingText]}>
          Voice Control
        </Text>
      </TouchableOpacity>
      
      {/* Main action buttons */}
      <View style={styles.buttonGrid}>
        {/* Navigation */}
        <TouchableOpacity
          style={[
            styles.actionButton,
            styles.navigationButton,
            { width: buttonSize, height: buttonSize },
          ]}
          onPress={() => handleButtonPress('Navigation', onNavigate)}
          activeOpacity={0.8}
        >
          <Text style={styles.buttonIcon}>🦭</Text>
          <Text style={[styles.buttonText, { fontSize }]}>
            Navigate
          </Text>
        </TouchableOpacity>
        
        {/* Booking */}
        <TouchableOpacity
          style={[
            styles.actionButton,
            styles.bookingButton,
            { width: buttonSize, height: buttonSize },
          ]}
          onPress={() => handleButtonPress('Booking', onBook)}
          activeOpacity={0.8}
        >
          <Text style={styles.buttonIcon}>🍴</Text>
          <Text style={[styles.buttonText, { fontSize }]}>
            Book
          </Text>
        </TouchableOpacity>
        
        {/* Stories */}
        <TouchableOpacity
          style={[
            styles.actionButton,
            styles.storyButton,
            { width: buttonSize, height: buttonSize },
          ]}
          onPress={() => handleButtonPress('Stories', onStory)}
          activeOpacity={0.8}
        >
          <Text style={styles.buttonIcon}>📚</Text>
          <Text style={[styles.buttonText, { fontSize }]}>
            Stories
          </Text>
        </TouchableOpacity>
        
        {/* Emergency */}
        <TouchableOpacity
          style={[
            styles.actionButton,
            styles.emergencyButton,
            { width: buttonSize, height: buttonSize },
          ]}
          onPress={() => handleButtonPress('Emergency', onEmergency)}
          activeOpacity={0.8}
        >
          <Text style={styles.buttonIcon}>🆘</Text>
          <Text style={[styles.buttonText, { fontSize }]}>
            Emergency
          </Text>
        </TouchableOpacity>
      </View>
      
      {/* Quick tips */}
      {!isDriving && (
        <View style={styles.tipsContainer}>
          <Text style={styles.tipText}>
            Tap any button or use voice control
          </Text>
          <Text style={styles.tipText}>
            Say "Hey Roadtrip" to activate voice
          </Text>
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  drivingContainer: {
    backgroundColor: '#000',
  },
  scrollContent: {
    flexGrow: 1,
    paddingTop: 40,
    paddingHorizontal: 20,
    alignItems: 'center',
  },
  voiceButton: {
    backgroundColor: '#007AFF',
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 40,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  drivingButton: {
    backgroundColor: '#4CAF50',
  },
  buttonGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-around',
    width: '100%',
    gap: 20,
  },
  actionButton: {
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 6,
  },
  navigationButton: {
    backgroundColor: '#4CAF50',
  },
  bookingButton: {
    backgroundColor: '#FF9800',
  },
  storyButton: {
    backgroundColor: '#9C27B0',
  },
  emergencyButton: {
    backgroundColor: '#F44336',
  },
  buttonIcon: {
    fontSize: 48,
    marginBottom: 10,
  },
  buttonText: {
    color: '#FFF',
    fontWeight: 'bold',
    textAlign: 'center',
  },
  drivingText: {
    fontSize: 28,
  },
  tipsContainer: {
    marginTop: 40,
    alignItems: 'center',
  },
  tipText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
    textAlign: 'center',
  },
});