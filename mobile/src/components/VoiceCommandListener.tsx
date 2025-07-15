import React, { useEffect, useState, useCallback } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  Modal,
  FlatList,
  Alert
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useVoiceCommands, VoiceCommandResult } from '../hooks/useVoiceCommands';
import { VoiceCommand, RecognizedCommand } from '../services/voiceCommandService';

interface VoiceCommandListenerProps {
  onStoryCommand?: (action: string, params?: string[]) => void;
  onNavigationCommand?: (action: string, params?: string[]) => void;
  onPlaybackCommand?: (action: string, params?: string[]) => void;
  onBookingCommand?: (action: string, params?: string[]) => void;
  voiceFirst?: boolean;
  isDriving?: boolean;
}

const VoiceCommandListener: React.FC<VoiceCommandListenerProps> = ({
  onStoryCommand,
  onNavigationCommand,
  onPlaybackCommand,
  onBookingCommand,
  voiceFirst = false,
  isDriving = false
}) => {
  const [helpModalVisible, setHelpModalVisible] = useState(false);
  const [lastCommandText, setLastCommandText] = useState<string>('');
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  
  // Handle recognized commands
  const handleCommand = useCallback((command: RecognizedCommand) => {
    setLastCommandText(`Command: ${command.action}`);
    
    // Handle different command types based on the action
    switch (command.action) {
      case 'play':
      case 'pause':
      case 'resume':
        onPlaybackCommand?.(command.action, command.params);
        setFeedbackMessage(`Playback: ${command.action}`);
        break;
      case 'next':
      case 'previous':
      case 'topic':
        onStoryCommand?.(command.action, command.params);
        setFeedbackMessage(`Story: ${command.action}`);
        break;
      case 'navigate':
        onNavigationCommand?.(command.action, command.params);
        setFeedbackMessage(`Navigation: ${command.action}`);
        break;
      case 'book':
      case 'reserve':
        onBookingCommand?.(command.action, command.params);
        setFeedbackMessage(`Booking: ${command.action}`);
        break;
      case 'help':
        setHelpModalVisible(true);
        setFeedbackMessage('Showing help');
        break;
      default:
        setFeedbackMessage("I didn't understand that command.");
    }
    
    // Clear feedback after 3 seconds
    setTimeout(() => setFeedbackMessage(null), 3000);
  }, [onPlaybackCommand, onStoryCommand, onNavigationCommand]);
  
  // Define custom commands
  const customCommands: VoiceCommand[] = [
    {
      patterns: ['play story', 'read story', 'start reading'],
      action: 'play',
      description: 'Start playing the current story',
      examples: ['play story', 'read story', 'start reading']
    },
    {
      patterns: ['pause', 'pause story', 'stop reading'],
      action: 'pause',
      description: 'Pause the current story',
      examples: ['pause', 'pause story', 'stop reading']
    },
    {
      patterns: ['resume', 'continue', 'continue story'],
      action: 'resume',
      description: 'Resume playing the current story',
      examples: ['resume', 'continue', 'continue story']
    },
    {
      patterns: ['next story', 'skip story', 'another story'],
      action: 'next',
      description: 'Go to the next story',
      examples: ['next story', 'skip story', 'another story']
    },
    {
      patterns: ['previous story', 'go back', 'last story'],
      action: 'previous',
      description: 'Go to the previous story',
      examples: ['previous story', 'go back', 'last story']
    },
    {
      patterns: ['tell me about', 'what about', 'story about'],
      action: 'topic',
      paramRegex: /tell me about (.*)|what about (.*)|story about (.*)/i,
      description: 'Get a story about a specific topic',
      examples: ['tell me about history', 'what about nature', 'story about dinosaurs']
    },
    {
      patterns: ['help', 'show help', 'what can I say'],
      action: 'help',
      description: 'Show help for voice commands',
      examples: ['help', 'show help', 'what can I say']
    },
    {
      patterns: ['go to', 'navigate to', 'take me to'],
      action: 'navigate',
      paramRegex: /go to (.*)|navigate to (.*)|take me to (.*)/i,
      description: 'Navigate to a specific location',
      examples: ['go to New York', 'navigate to Grand Canyon', 'take me to Chicago']
    },
    {
      patterns: ['book', 'reserve', 'make reservation'],
      action: 'book',
      paramRegex: /book (.*)|reserve (.*)|make reservation at (.*)/i,
      description: 'Book a restaurant or attraction',
      examples: ['book a restaurant', 'reserve table at Italian place', 'make reservation']
    }
  ];
  
  // Initialize voice commands
  const {
    isListening,
    commands,
    startListening,
    stopListening,
    processCommand
  } = useVoiceCommands(handleCommand, customCommands, {
    continuous: voiceFirst,
    autoStart: voiceFirst
  });
  
  // For testing in development
  const testCommand = useCallback((text: string) => {
    const success = processCommand(`app ${text}`);
    if (!success) {
      setFeedbackMessage("Command not recognized");
      setTimeout(() => setFeedbackMessage(null), 3000);
    }
  }, [processCommand]);
  
  // Toggle listening
  const toggleListening = () => {
    if (isListening) {
      stopListening();
      setFeedbackMessage("Voice recognition stopped");
    } else {
      startListening();
      setFeedbackMessage("Listening...");
    }
    
    // Clear feedback after 3 seconds
    setTimeout(() => setFeedbackMessage(null), 3000);
  };
  
  // Help modal with available commands
  const renderHelpModal = () => (
    <Modal
      animationType="slide"
      transparent={true}
      visible={helpModalVisible}
      onRequestClose={() => setHelpModalVisible(false)}
    >
      <View style={styles.modalContainer}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Voice Commands</Text>
          <Text style={styles.modalSubtitle}>Say "App" or "Journey" before each command</Text>
          
          <FlatList
            data={commands}
            keyExtractor={(item, index) => `command-${index}`}
            renderItem={({ item }) => (
              <View style={styles.commandItem}>
                <Text style={styles.commandName}>{item.description}</Text>
                {item.examples && item.examples.length > 0 && (
                  <Text style={styles.commandExample}>
                    Example: "{item.examples[0]}"
                  </Text>
                )}
              </View>
            )}
          />
          
          <TouchableOpacity 
            style={styles.closeButton}
            onPress={() => setHelpModalVisible(false)}
          >
            <Text style={styles.closeButtonText}>Close</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
  
  // Auto-start voice control for voice-first mode
  useEffect(() => {
    if (voiceFirst && !isListening) {
      startListening();
    }
  }, [voiceFirst, isListening, startListening]);

  // Voice feedback for driving mode
  useEffect(() => {
    if (isDriving && feedbackMessage) {
      // Speak feedback aloud in driving mode
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(feedbackMessage);
        window.speechSynthesis.speak(utterance);
      }
    }
  }, [isDriving, feedbackMessage]);

  return (
    <View style={[styles.container, voiceFirst && styles.voiceFirstContainer]}>
      {renderHelpModal()}
      
      {/* Feedback message */}
      {feedbackMessage && (
        <View style={styles.feedbackContainer}>
          <Text style={styles.feedbackText}>{feedbackMessage}</Text>
        </View>
      )}
      
      {/* Last command */}
      {lastCommandText ? (
        <View style={styles.lastCommandContainer}>
          <Text style={styles.lastCommandText}>{lastCommandText}</Text>
        </View>
      ) : null}
      
      {/* Voice button - larger for voice-first mode */}
      <TouchableOpacity 
        testID="voice-button"
        style={[
          styles.voiceButton,
          isListening ? styles.voiceButtonActive : null,
          voiceFirst && styles.voiceFirstButton,
          isDriving && styles.drivingModeButton
        ]}
        onPress={toggleListening}
      >
        <Ionicons 
          name={isListening ? "mic" : "mic-outline"} 
          size={voiceFirst ? 48 : 24} 
          color="#fff" 
        />
        {voiceFirst && (
          <Text style={styles.voiceFirstText}>
            {isListening ? 'Listening...' : 'Tap to speak'}
          </Text>
        )}
      </TouchableOpacity>
      
      {/* Help button */}
      <TouchableOpacity 
        testID="help-button"
        style={styles.helpButton}
        onPress={() => setHelpModalVisible(true)}
      >
        <Ionicons name="help-circle-outline" size={24} color="#555" />
      </TouchableOpacity>
      
      {/* Test buttons (DEV only) */}
      {__DEV__ && (
        <View style={styles.devButtons}>
          <TouchableOpacity 
            style={styles.devButton}
            onPress={() => testCommand('play story')}
          >
            <Text style={styles.devButtonText}>Test Play</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={styles.devButton}
            onPress={() => testCommand('help')}
          >
            <Text style={styles.devButtonText}>Test Help</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 20,
    right: 20,
    alignItems: 'center',
  },
  voiceFirstContainer: {
    bottom: 40,
    right: '50%',
    transform: [{ translateX: 50 }],
  },
  voiceButton: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#f4511e',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
    elevation: 5,
  },
  voiceButtonActive: {
    backgroundColor: '#e83e00',
    transform: [{ scale: 1.1 }],
  },
  voiceFirstButton: {
    width: 120,
    height: 120,
    borderRadius: 60,
    flexDirection: 'column',
    gap: 8,
  },
  drivingModeButton: {
    width: 160,
    height: 160,
    borderRadius: 80,
  },
  voiceFirstText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
    marginTop: 8,
  },
  feedbackContainer: {
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    padding: 10,
    borderRadius: 8,
    position: 'absolute',
    bottom: 80,
    right: 0,
    left: -100,
    alignItems: 'center',
  },
  feedbackText: {
    color: '#fff',
    fontSize: 14,
  },
  lastCommandContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    padding: 8,
    borderRadius: 6,
    position: 'absolute',
    bottom: 80,
    right: 0,
    minWidth: 100,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#ddd',
  },
  lastCommandText: {
    color: '#333',
    fontSize: 12,
  },
  helpButton: {
    position: 'absolute',
    top: -40,
    right: 18,
    width: 24,
    height: 24,
  },
  modalContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  modalContent: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    width: '80%',
    maxHeight: '80%',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 5,
    color: '#f4511e',
  },
  modalSubtitle: {
    fontSize: 14,
    color: '#666',
    marginBottom: 15,
  },
  commandItem: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  commandName: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  commandExample: {
    fontSize: 12,
    color: '#666',
    fontStyle: 'italic',
    marginTop: 4,
  },
  closeButton: {
    marginTop: 20,
    padding: 12,
    backgroundColor: '#f4511e',
    borderRadius: 8,
    alignItems: 'center',
  },
  closeButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  devButtons: {
    position: 'absolute',
    top: -80,
    right: 0,
    flexDirection: 'row',
  },
  devButton: {
    backgroundColor: '#333',
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginHorizontal: 2,
    borderRadius: 4,
  },
  devButtonText: {
    color: '#fff',
    fontSize: 10,
  },
});

export default VoiceCommandListener;
