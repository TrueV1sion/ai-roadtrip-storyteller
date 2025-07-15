import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Voice, { SpeechResultsEvent, SpeechErrorEvent } from '@react-native-voice/voice';
import { theme } from '../../theme';

const { width, height } = Dimensions.get('window');

interface RideshareVoiceInterfaceProps {
  mode: 'driver' | 'passenger';
  onCommand: (command: string) => void;
  quickCommands?: string[];
}

export const RideshareVoiceInterface: React.FC<RideshareVoiceInterfaceProps> = ({
  mode,
  onCommand,
  quickCommands = [],
}) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');

  useEffect(() => {
    Voice.onSpeechResults = onSpeechResults;
    Voice.onSpeechError = onSpeechError;
    Voice.onSpeechEnd = onSpeechEnd;

    return () => {
      Voice.destroy().then(Voice.removeAllListeners);
    };
  }, []);

  const onSpeechResults = (event: SpeechResultsEvent) => {
    if (event.value && event.value.length > 0) {
      const command = event.value[0];
      setTranscript(command);
      onCommand(command);
    }
  };

  const onSpeechError = (event: SpeechErrorEvent) => {
    console.error('Speech error:', event.error);
    setIsListening(false);
    Alert.alert('Voice Error', 'Please try again');
  };

  const onSpeechEnd = () => {
    setIsListening(false);
  };

  const startListening = async () => {
    try {
      setTranscript('');
      setIsListening(true);
      await Voice.start('en-US');
    } catch (error) {
      console.error('Error starting voice:', error);
      setIsListening(false);
    }
  };

  const stopListening = async () => {
    try {
      await Voice.stop();
      setIsListening(false);
    } catch (error) {
      console.error('Error stopping voice:', error);
    }
  };

  const defaultDriverCommands = [
    'Find gas',
    'Quick food',
    'Take break',
    'Show earnings',
  ];

  const defaultPassengerCommands = [
    'Play trivia',
    'Tell story',
    'Play music',
    'Local facts',
  ];

  const commands = quickCommands.length > 0 
    ? quickCommands 
    : (mode === 'driver' ? defaultDriverCommands : defaultPassengerCommands);

  return (
    <View style={styles.container}>
      {/* Large Voice Button */}
      <TouchableOpacity
        style={[styles.voiceButton, isListening && styles.voiceButtonActive]}
        onPress={isListening ? stopListening : startListening}
        activeOpacity={0.8}
      >
        <Ionicons 
          name={isListening ? "mic" : "mic-outline"} 
          size={60} 
          color="white" 
        />
        <Text style={styles.voiceButtonText}>
          {isListening ? 'Listening...' : 'Tap to Speak'}
        </Text>
      </TouchableOpacity>

      {/* Transcript Display */}
      {transcript !== '' && (
        <View style={styles.transcriptContainer}>
          <Text style={styles.transcriptText}>"{transcript}"</Text>
        </View>
      )}

      {/* Quick Command Buttons */}
      <View style={styles.quickCommandsContainer}>
        <Text style={styles.quickCommandsTitle}>Quick Commands</Text>
        <View style={styles.commandGrid}>
          {commands.slice(0, 4).map((command, index) => (
            <TouchableOpacity
              key={index}
              style={styles.commandButton}
              onPress={() => onCommand(command.toLowerCase())}
              activeOpacity={0.7}
            >
              <Text style={styles.commandText}>{command}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Mode Indicator */}
      <View style={styles.modeIndicator}>
        <Ionicons 
          name={mode === 'driver' ? 'car' : 'person'} 
          size={20} 
          color={theme.colors.primary} 
        />
        <Text style={styles.modeText}>
          {mode === 'driver' ? 'Driver Mode' : 'Passenger Mode'}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: theme.spacing.lg,
  },
  voiceButton: {
    width: width * 0.5,
    height: width * 0.5,
    borderRadius: width * 0.25,
    backgroundColor: theme.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.xl,
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  voiceButtonActive: {
    backgroundColor: theme.colors.error,
    transform: [{ scale: 1.1 }],
  },
  voiceButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: '600',
    marginTop: theme.spacing.md,
  },
  transcriptContainer: {
    backgroundColor: theme.colors.surface,
    padding: theme.spacing.lg,
    borderRadius: theme.borderRadius.lg,
    marginBottom: theme.spacing.xl,
    width: '100%',
  },
  transcriptText: {
    fontSize: 18,
    color: theme.colors.text,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  quickCommandsContainer: {
    width: '100%',
  },
  quickCommandsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.md,
    textAlign: 'center',
  },
  commandGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  commandButton: {
    width: '48%',
    backgroundColor: theme.colors.surface,
    padding: theme.spacing.lg,
    borderRadius: theme.borderRadius.md,
    marginBottom: theme.spacing.md,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: theme.colors.border,
  },
  commandText: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text,
    textAlign: 'center',
  },
  modeIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: theme.spacing.xl,
  },
  modeText: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginLeft: theme.spacing.sm,
  },
});