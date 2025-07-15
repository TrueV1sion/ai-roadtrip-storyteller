import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Platform,
} from 'react-native';
import { Audio } from 'expo-av';
import { useNavigation } from '@react-navigation/native';
import { SafeArea } from '../SafeArea';
import { useVoiceCommands } from '../../hooks/useVoiceCommands';
import { navigationService } from '../../services/navigation/navigationService';
import { voiceRecognitionService } from '../../services/voiceRecognitionService';
import { voiceSynthesisService } from '../../services/voiceSynthesisService';

interface VoiceNavigationInterfaceProps {
  onCommandProcessed?: (command: string, result: any) => void;
  isDriving?: boolean;
}

export const VoiceNavigationInterface: React.FC<VoiceNavigationInterfaceProps> = ({
  onCommandProcessed,
  isDriving = false,
}) => {
  const [isListening, setIsListening] = useState(false);
  const [currentCommand, setCurrentCommand] = useState('');
  const [feedback, setFeedback] = useState('');
  const [pulseAnim] = useState(new Animated.Value(1));
  const navigation = useNavigation();
  const { processCommand } = useVoiceCommands();

  // Voice recognition handlers
  useEffect(() => {
    // Initialize voice recognition on mount
    voiceRecognitionService.initialize();
    
    return () => {
      // Cleanup on unmount
      voiceRecognitionService.destroy();
    };
  }, []);

  const onSpeechStart = useCallback(() => {
    setIsListening(true);
    startPulseAnimation();
  }, []);

  const onSpeechEnd = useCallback(() => {
    setIsListening(false);
    stopPulseAnimation();
  }, []);

  const onSpeechResults = useCallback(async (results: string[]) => {
    if (results && results[0]) {
      const command = results[0];
      setCurrentCommand(command);
      await handleVoiceCommand(command);
    }
  }, []);

  const onSpeechPartialResults = useCallback((results: string[]) => {
    if (results && results[0]) {
      setCurrentCommand(results[0]);
    }
  }, []);

  const onSpeechError = useCallback((error: any) => {
    console.error('Speech recognition error:', error);
    setIsListening(false);
    stopPulseAnimation();
    provideFeedback('Sorry, I didn\'t catch that. Please try again.');
  }, []);

  // Animation for listening indicator
  const startPulseAnimation = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.2,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
      ])
    ).start();
  };

  const stopPulseAnimation = () => {
    pulseAnim.setValue(1);
  };

  // Voice command processing
  const handleVoiceCommand = async (command: string) => {
    try {
      // First check if it's a navigation command
      const navCommand = voiceRecognitionService.parseNavigationCommand(command);
      if (navCommand.isNavigation && navCommand.destination) {
        await navigationService.startNavigation(navCommand.destination);
        provideFeedback(`Starting navigation to ${navCommand.destination}`);
        if (onCommandProcessed) {
          onCommandProcessed(command, { type: 'navigation', destination: navCommand.destination });
        }
        return;
      }
      
      // Check for story control commands
      const storyCommand = voiceRecognitionService.parseStoryCommand(command);
      if (storyCommand.recognized && storyCommand.command) {
        switch (storyCommand.command) {
          case 'stop':
            await voiceSynthesisService.stop();
            provideFeedback('Stopped');
            break;
          case 'pause':
            await voiceSynthesisService.pause();
            provideFeedback('Paused');
            break;
          case 'resume':
            await voiceSynthesisService.resume();
            provideFeedback('Resumed');
            break;
        }
        if (onCommandProcessed) {
          onCommandProcessed(command, { type: 'story', action: storyCommand.command });
        }
        return;
      }
      
      // Fall back to general command processing
      const result = await processCommand(command);
      
      // Handle navigation commands
      if (result.type === 'navigation') {
        if (result.action === 'start') {
          await navigationService.startNavigation(result.destination);
          provideFeedback(`Starting navigation to ${result.destination}`);
        } else if (result.action === 'stop') {
          await navigationService.stopNavigation();
          provideFeedback('Navigation stopped');
        } else if (result.action === 'route_info') {
          const info = await navigationService.getCurrentRouteInfo();
          provideFeedback(`${info.duration} remaining, ${info.distance} to go`);
        }
      }
      
      // Handle booking commands
      else if (result.type === 'booking') {
        navigation.navigate('VoiceBooking', { bookingData: result });
        provideFeedback(`Opening booking for ${result.venue}`);
      }
      
      // Handle story commands
      else if (result.type === 'story') {
        if (result.action === 'play') {
          // Story will be played via TTS from backend
          provideFeedback('Starting story');
        } else if (result.action === 'pause') {
          await voiceSynthesisService.pause();
          provideFeedback('Story paused');
        } else if (result.action === 'resume') {
          await voiceSynthesisService.resume();
          provideFeedback('Story resumed');
        }
      }
      
      // Handle safety commands
      else if (result.type === 'safety') {
        if (result.action === 'emergency') {
          navigation.navigate('Emergency');
          provideFeedback('Opening emergency assistance');
        }
      }
      
      if (onCommandProcessed) {
        onCommandProcessed(command, result);
      }
    } catch (error) {
      console.error('Error processing command:', error);
      provideFeedback('Sorry, I couldn\'t process that command');
    }
  };

  // Voice feedback
  const provideFeedback = async (message: string) => {
    setFeedback(message);
    await voiceSynthesisService.speak(message);
    
    // Clear feedback after a delay
    setTimeout(() => {
      setFeedback('');
    }, 3000);
  };

  // Start/stop listening
  const toggleListening = async () => {
    try {
      if (isListening) {
        await voiceRecognitionService.stopListening();
      } else {
        await voiceRecognitionService.startListening(
          { language: 'en-US' },
          {
            onStart: onSpeechStart,
            onEnd: onSpeechEnd,
            onResults: onSpeechResults,
            onPartialResults: onSpeechPartialResults,
            onError: onSpeechError,
          }
        );
      }
    } catch (error) {
      console.error('Error toggling voice recognition:', error);
    }
  };

  // Emergency stop for driving safety
  const emergencyStop = async () => {
    await navigationService.stopNavigation();
    await voiceSynthesisService.stop();
    await voiceRecognitionService.stopListening();
    provideFeedback('All activities stopped');
  };

  return (
    <SafeArea>
      <View style={[styles.container, isDriving && styles.drivingContainer]}>
        {/* Voice activation button - large for driving safety */}
        <TouchableOpacity
          style={[styles.voiceButton, isDriving && styles.drivingVoiceButton]}
          onPress={toggleListening}
          activeOpacity={0.8}
        >
          <Animated.View
            style={[
              styles.voiceButtonInner,
              isListening && styles.listeningButton,
              { transform: [{ scale: pulseAnim }] },
            ]}
          >
            <Text style={[styles.voiceButtonText, isDriving && styles.drivingText]}>
              {isListening ? '🎤' : '🎙️'}
            </Text>
          </Animated.View>
        </TouchableOpacity>

        {/* Current command display */}
        {currentCommand ? (
          <View style={styles.commandContainer}>
            <Text style={[styles.commandText, isDriving && styles.drivingText]}>
              "{currentCommand}"
            </Text>
          </View>
        ) : null}

        {/* Feedback display */}
        {feedback ? (
          <View style={styles.feedbackContainer}>
            <Text style={[styles.feedbackText, isDriving && styles.drivingText]}>
              {feedback}
            </Text>
          </View>
        ) : null}

        {/* Emergency stop button for driving */}
        {isDriving && (
          <TouchableOpacity
            style={styles.emergencyButton}
            onPress={emergencyStop}
            activeOpacity={0.8}
          >
            <Text style={styles.emergencyButtonText}>STOP ALL</Text>
          </TouchableOpacity>
        )}

        {/* Voice command hints */}
        {!isDriving && (
          <View style={styles.hintsContainer}>
            <Text style={styles.hintTitle}>Try saying:</Text>
            <Text style={styles.hintText}>"Navigate to [destination]"</Text>
            <Text style={styles.hintText}>"Book a restaurant nearby"</Text>
            <Text style={styles.hintText}>"Tell me about this area"</Text>
            <Text style={styles.hintText}>"Play a story"</Text>
          </View>
        )}
      </View>
    </SafeArea>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  drivingContainer: {
    backgroundColor: '#000',
  },
  voiceButton: {
    width: 120,
    height: 120,
    borderRadius: 60,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 30,
  },
  drivingVoiceButton: {
    width: 200,
    height: 200,
    borderRadius: 100,
  },
  voiceButtonInner: {
    width: '100%',
    height: '100%',
    borderRadius: 60,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.2,
        shadowRadius: 4,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  listeningButton: {
    backgroundColor: '#FF3B30',
  },
  voiceButtonText: {
    fontSize: 48,
  },
  drivingText: {
    fontSize: 72,
    color: '#FFF',
  },
  commandContainer: {
    padding: 20,
    backgroundColor: 'rgba(0, 0, 0, 0.1)',
    borderRadius: 10,
    marginBottom: 20,
    minWidth: 250,
  },
  commandText: {
    fontSize: 18,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  feedbackContainer: {
    padding: 20,
    backgroundColor: 'rgba(0, 122, 255, 0.1)',
    borderRadius: 10,
    marginBottom: 20,
    minWidth: 250,
  },
  feedbackText: {
    fontSize: 16,
    textAlign: 'center',
    color: '#007AFF',
  },
  emergencyButton: {
    position: 'absolute',
    bottom: 40,
    backgroundColor: '#FF3B30',
    paddingHorizontal: 40,
    paddingVertical: 20,
    borderRadius: 30,
  },
  emergencyButtonText: {
    color: '#FFF',
    fontSize: 24,
    fontWeight: 'bold',
  },
  hintsContainer: {
    position: 'absolute',
    bottom: 40,
    alignItems: 'center',
  },
  hintTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#666',
  },
  hintText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
});