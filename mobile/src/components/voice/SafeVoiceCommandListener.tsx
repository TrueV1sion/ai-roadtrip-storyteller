import React, { useEffect, useState, useCallback, useRef } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  Modal,
  FlatList,
  Alert,
  Vibration,
  AppState,
  AppStateStatus
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import { useVoiceCommands, VoiceCommandResult } from '../../hooks/useVoiceCommands';
import { VoiceCommand, RecognizedCommand } from '../../services/voiceCommandService';
import { voiceSafetyService, SafetyLevel, SafetyContext } from '../../services/voice/voiceSafetyService';
import { useDrivingContext } from '../../hooks/useDrivingContext';

interface SafeVoiceCommandListenerProps {
  onStoryCommand?: (action: string, params?: string[]) => void;
  onNavigationCommand?: (action: string, params?: string[]) => void;
  onPlaybackCommand?: (action: string, params?: string[]) => void;
  onBookingCommand?: (action: string, params?: string[]) => void;
  voiceFirst?: boolean;
  isDriving?: boolean;
  onSafetyAlert?: (alert: string) => void;
}

// Emergency commands that are always allowed
const EMERGENCY_COMMANDS = ['stop', 'pause', 'quiet', 'emergency', 'help', 'cancel'];

// Simple commands allowed while driving
const SIMPLE_DRIVING_COMMANDS = [
  ...EMERGENCY_COMMANDS,
  'yes', 'no', 'next', 'previous', 'louder', 'quieter', 'repeat'
];

const SafeVoiceCommandListener: React.FC<SafeVoiceCommandListenerProps> = ({
  onStoryCommand,
  onNavigationCommand,
  onPlaybackCommand,
  onBookingCommand,
  voiceFirst = false,
  isDriving = false,
  onSafetyAlert
}) => {
  const [helpModalVisible, setHelpModalVisible] = useState(false);
  const [lastCommandText, setLastCommandText] = useState<string>('');
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [safetyWarning, setSafetyWarning] = useState<string | null>(null);
  const [emergencyMode, setEmergencyMode] = useState(false);
  const [autoPaused, setAutoPaused] = useState(false);
  const [safetyLevel, setSafetyLevel] = useState<SafetyLevel>(SafetyLevel.PARKED);
  
  const drivingContext = useDrivingContext();
  const appState = useRef(AppState.currentState);
  const interactionStartTime = useRef<number | null>(null);
  const emergencySound = useRef<Audio.Sound | null>(null);

  // Load emergency sound
  useEffect(() => {
    loadEmergencySound();
    return () => {
      if (emergencySound.current) {
        emergencySound.current.unloadAsync();
      }
    };
  }, []);

  const loadEmergencySound = async () => {
    try {
      const { sound } = await Audio.Sound.createAsync(
        require('../../assets/sounds/emergency-beep.mp3'),
        { shouldPlay: false }
      );
      emergencySound.current = sound;
    } catch (error) {
      console.error('Failed to load emergency sound:', error);
    }
  };

  // Handle app state changes for safety
  useEffect(() => {
    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription.remove();
  }, []);

  const handleAppStateChange = (nextAppState: AppStateStatus) => {
    if (appState.current === 'active' && nextAppState.match(/inactive|background/)) {
      // App going to background - pause voice interactions
      if (isDriving) {
        handleEmergencyStop('App backgrounded while driving');
      }
    }
    appState.current = nextAppState;
  };

  // Update safety context
  useEffect(() => {
    if (drivingContext) {
      const context: SafetyContext = {
        speed: drivingContext.speed,
        isNavigating: drivingContext.isNavigating,
        trafficCondition: drivingContext.trafficCondition,
        weatherCondition: drivingContext.weatherCondition,
        upcomingManeuver: drivingContext.upcomingManeuver,
        maneuverDistance: drivingContext.maneuverDistance
      };
      
      voiceSafetyService.updateContext(context);
      setSafetyLevel(voiceSafetyService.getCurrentSafetyLevel());
      
      // Check for auto-pause conditions
      const shouldPause = voiceSafetyService.shouldAutoPause();
      if (shouldPause && !autoPaused) {
        handleAutoPause(shouldPause.reason);
      } else if (!shouldPause && autoPaused) {
        handleAutoResume();
      }
    }
  }, [drivingContext, autoPaused]);

  // Enhanced command handler with safety validation
  const handleCommand = useCallback(async (command: RecognizedCommand) => {
    // Always allow emergency commands
    if (EMERGENCY_COMMANDS.includes(command.action.toLowerCase())) {
      handleEmergencyCommand(command);
      return;
    }

    // Start interaction timing
    interactionStartTime.current = Date.now();

    // Validate command safety
    const validation = await voiceSafetyService.validateCommand(command.action, isDriving);
    
    if (!validation.isAllowed) {
      // Command not allowed in current context
      setSafetyWarning(validation.reason || 'Command not available while driving');
      provideSafetyFeedback(validation.reason || 'Please wait until stopped', true);
      
      // Log safety violation
      voiceSafetyService.logSafetyEvent({
        type: 'command_blocked',
        command: command.action,
        reason: validation.reason,
        safetyLevel: safetyLevel
      });
      
      return;
    }

    // Show any warnings
    if (validation.warnings.length > 0) {
      setSafetyWarning(validation.warnings[0]);
    }

    setLastCommandText(`Command: ${command.action}`);
    
    // Process command based on type
    switch (command.action) {
      case 'play':
      case 'pause':
      case 'resume':
        onPlaybackCommand?.(command.action, command.params);
        setFeedbackMessage(`Playback: ${command.action}`);
        break;
      case 'next':
      case 'previous':
        if (safetyLevel === SafetyLevel.CRITICAL || safetyLevel === SafetyLevel.HIGHWAY) {
          provideSafetyFeedback('Command simplified for safety', false);
        }
        onStoryCommand?.(command.action, command.params);
        setFeedbackMessage(`Story: ${command.action}`);
        break;
      case 'topic':
        if (isDriving && safetyLevel !== SafetyLevel.PARKED) {
          provideSafetyFeedback('Topic selection available when stopped', true);
          return;
        }
        onStoryCommand?.(command.action, command.params);
        setFeedbackMessage(`Story: ${command.action}`);
        break;
      case 'navigate':
        if (validation.requiresConfirmation) {
          // Require voice confirmation for navigation changes while driving
          requestVoiceConfirmation('Change navigation?', () => {
            onNavigationCommand?.(command.action, command.params);
          });
        } else {
          onNavigationCommand?.(command.action, command.params);
        }
        setFeedbackMessage(`Navigation: ${command.action}`);
        break;
      case 'book':
      case 'reserve':
        if (isDriving && safetyLevel !== SafetyLevel.PARKED) {
          provideSafetyFeedback('Booking available when stopped', true);
          return;
        }
        onBookingCommand?.(command.action, command.params);
        setFeedbackMessage(`Booking: ${command.action}`);
        break;
      case 'help':
        provideVoiceHelp();
        break;
      default:
        setFeedbackMessage("Command not recognized");
    }

    // Record interaction completion
    if (interactionStartTime.current) {
      const duration = Date.now() - interactionStartTime.current;
      voiceSafetyService.recordInteraction({
        command: command.action,
        duration,
        safetyLevel: safetyLevel,
        completed: true
      });
    }
    
    // Clear feedback after appropriate time
    const clearTime = isDriving ? 2000 : 3000;
    setTimeout(() => {
      setFeedbackMessage(null);
      setSafetyWarning(null);
    }, clearTime);
  }, [isDriving, safetyLevel, onPlaybackCommand, onStoryCommand, onNavigationCommand, onBookingCommand]);

  // Handle emergency commands
  const handleEmergencyCommand = (command: RecognizedCommand) => {
    switch (command.action.toLowerCase()) {
      case 'stop':
      case 'emergency':
        handleEmergencyStop('Voice command');
        break;
      case 'pause':
      case 'quiet':
        onPlaybackCommand?.('pause', []);
        setFeedbackMessage('Paused');
        break;
      case 'help':
        if (isDriving) {
          provideVoiceHelp();
        } else {
          setHelpModalVisible(true);
        }
        break;
      case 'cancel':
        setFeedbackMessage('Cancelled');
        break;
    }
  };

  // Emergency stop handler
  const handleEmergencyStop = async (reason: string) => {
    setEmergencyMode(true);
    
    // Immediate actions
    onPlaybackCommand?.('stop', []);
    stopListening();
    
    // Vibrate for haptic feedback
    Vibration.vibrate([0, 200, 100, 200]);
    
    // Play emergency sound
    if (emergencySound.current) {
      await emergencySound.current.replayAsync();
    }
    
    // Log emergency event
    voiceSafetyService.logSafetyEvent({
      type: 'emergency_stop',
      reason,
      safetyLevel: safetyLevel
    });
    
    // Notify parent
    onSafetyAlert?.(`Emergency stop: ${reason}`);
    
    provideSafetyFeedback('All interactions stopped', false);
    
    // Auto-clear emergency mode after 30 seconds
    setTimeout(() => {
      setEmergencyMode(false);
    }, 30000);
  };

  // Auto-pause handler
  const handleAutoPause = (reason: string) => {
    setAutoPaused(true);
    onPlaybackCommand?.('pause', []);
    
    provideSafetyFeedback(`Auto-paused: ${reason}`, false);
    
    voiceSafetyService.logSafetyEvent({
      type: 'auto_pause',
      reason,
      safetyLevel: safetyLevel
    });
  };

  // Auto-resume handler
  const handleAutoResume = () => {
    setAutoPaused(false);
    provideSafetyFeedback('Safe to resume', false);
  };

  // Voice confirmation for critical actions
  const requestVoiceConfirmation = (question: string, onConfirm: () => void) => {
    provideSafetyFeedback(question + ' Say yes to confirm', false);
    
    // Set up temporary confirmation handler
    const confirmationTimeout = setTimeout(() => {
      provideSafetyFeedback('Confirmation timeout', false);
    }, 5000);
    
    // Listen for yes/no response
    // This would integrate with the voice command system
  };

  // Provide voice help appropriate to driving context
  const provideVoiceHelp = () => {
    const availableCommands = voiceSafetyService.getAvailableCommands(isDriving);
    const helpText = isDriving 
      ? `Available commands: ${availableCommands.join(', ')}. Say stop anytime.`
      : 'Say "show help" to see all commands';
    
    provideSafetyFeedback(helpText, false);
  };

  // Safety feedback with voice
  const provideSafetyFeedback = (message: string, isWarning: boolean) => {
    setFeedbackMessage(message);
    
    if (isDriving || voiceFirst) {
      // Use TTS for feedback
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(message);
        utterance.rate = 1.1; // Slightly faster for driving
        utterance.pitch = isWarning ? 1.2 : 1.0; // Higher pitch for warnings
        window.speechSynthesis.speak(utterance);
      }
    }
  };

  // Define safety-aware commands
  const getSafetyAwareCommands = (): VoiceCommand[] => {
    const baseCommands: VoiceCommand[] = [
      // Emergency commands (always available)
      {
        patterns: ['stop', 'emergency stop', 'stop everything'],
        action: 'stop',
        description: 'Emergency stop',
        examples: ['stop', 'emergency stop'],
        priority: 100,
        alwaysAvailable: true
      },
      {
        patterns: ['pause', 'pause story', 'be quiet', 'quiet'],
        action: 'pause',
        description: 'Pause playback',
        examples: ['pause', 'quiet'],
        priority: 99,
        alwaysAvailable: true
      },
      {
        patterns: ['help', 'what can I say', 'commands'],
        action: 'help',
        description: 'Get help',
        examples: ['help', 'what can I say'],
        priority: 98,
        alwaysAvailable: true
      }
    ];

    // Add driving-safe commands
    if (isDriving && safetyLevel !== SafetyLevel.PARKED) {
      return [
        ...baseCommands,
        {
          patterns: ['yes', 'confirm', 'correct'],
          action: 'yes',
          description: 'Confirm',
          examples: ['yes'],
          priority: 90
        },
        {
          patterns: ['no', 'cancel', 'negative'],
          action: 'no',
          description: 'Decline',
          examples: ['no'],
          priority: 90
        },
        {
          patterns: ['louder', 'volume up', 'speak up'],
          action: 'louder',
          description: 'Increase volume',
          examples: ['louder'],
          priority: 80
        },
        {
          patterns: ['quieter', 'volume down', 'softer'],
          action: 'quieter',
          description: 'Decrease volume',
          examples: ['quieter'],
          priority: 80
        }
      ];
    }

    // Full commands when parked or not driving
    return [
      ...baseCommands,
      {
        patterns: ['play story', 'read story', 'start reading'],
        action: 'play',
        description: 'Start playing the current story',
        examples: ['play story', 'start reading']
      },
      {
        patterns: ['resume', 'continue', 'continue story'],
        action: 'resume',
        description: 'Resume playing',
        examples: ['resume', 'continue']
      },
      {
        patterns: ['next story', 'skip story', 'another story'],
        action: 'next',
        description: 'Next story',
        examples: ['next story', 'skip']
      },
      {
        patterns: ['previous story', 'go back', 'last story'],
        action: 'previous',
        description: 'Previous story',
        examples: ['previous story', 'go back']
      },
      {
        patterns: ['tell me about', 'what about', 'story about'],
        action: 'topic',
        paramRegex: /tell me about (.*)|what about (.*)|story about (.*)/i,
        description: 'Get a story about a topic',
        examples: ['tell me about history']
      },
      {
        patterns: ['go to', 'navigate to', 'take me to'],
        action: 'navigate',
        paramRegex: /go to (.*)|navigate to (.*)|take me to (.*)/i,
        description: 'Navigate to location',
        examples: ['go to New York']
      },
      {
        patterns: ['book', 'reserve', 'make reservation'],
        action: 'book',
        paramRegex: /book (.*)|reserve (.*)|make reservation at (.*)/i,
        description: 'Make a reservation',
        examples: ['book a restaurant']
      }
    ];
  };

  // Initialize voice commands with safety features
  const {
    isListening,
    commands,
    startListening,
    stopListening,
    processCommand
  } = useVoiceCommands(handleCommand, getSafetyAwareCommands(), {
    continuous: voiceFirst && !emergencyMode,
    autoStart: voiceFirst && !emergencyMode,
    safetyMode: isDriving
  });

  // Safety indicator component
  const SafetyIndicator = () => {
    const getIndicatorColor = () => {
      if (emergencyMode) return '#ff0000';
      if (autoPaused) return '#ff9800';
      switch (safetyLevel) {
        case SafetyLevel.PARKED: return '#4caf50';
        case SafetyLevel.LOW_SPEED: return '#8bc34a';
        case SafetyLevel.MODERATE: return '#ffc107';
        case SafetyLevel.HIGHWAY: return '#ff9800';
        case SafetyLevel.CRITICAL: return '#f44336';
        default: return '#9e9e9e';
      }
    };

    return (
      <View style={[styles.safetyIndicator, { backgroundColor: getIndicatorColor() }]}>
        <Text style={styles.safetyText}>
          {emergencyMode ? 'EMERGENCY' : safetyLevel.toUpperCase()}
        </Text>
      </View>
    );
  };

  // Enhanced help modal with safety information
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
          <Text style={styles.modalSubtitle}>
            {isDriving 
              ? 'Limited commands available while driving'
              : 'Say "App" or "Journey" before each command'
            }
          </Text>
          
          {isDriving && (
            <View style={styles.safetyNotice}>
              <Ionicons name="warning" size={20} color="#ff9800" />
              <Text style={styles.safetyNoticeText}>
                For your safety, complex commands are disabled while driving
              </Text>
            </View>
          )}
          
          <FlatList
            data={commands.filter(cmd => 
              !isDriving || cmd.alwaysAvailable || SIMPLE_DRIVING_COMMANDS.includes(cmd.action)
            )}
            keyExtractor={(item, index) => `command-${index}`}
            renderItem={({ item }) => (
              <View style={styles.commandItem}>
                <Text style={styles.commandName}>{item.description}</Text>
                {item.examples && item.examples.length > 0 && (
                  <Text style={styles.commandExample}>
                    Example: "{item.examples[0]}"
                  </Text>
                )}
                {item.alwaysAvailable && (
                  <Text style={styles.alwaysAvailable}>Always available</Text>
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

  return (
    <View style={[styles.container, voiceFirst && styles.voiceFirstContainer]}>
      {renderHelpModal()}
      
      {/* Safety indicator */}
      {isDriving && <SafetyIndicator />}
      
      {/* Safety warning */}
      {safetyWarning && (
        <View style={styles.safetyWarningContainer}>
          <Ionicons name="warning" size={16} color="#ff9800" />
          <Text style={styles.safetyWarningText}>{safetyWarning}</Text>
        </View>
      )}
      
      {/* Feedback message */}
      {feedbackMessage && (
        <View style={[
          styles.feedbackContainer,
          emergencyMode && styles.emergencyFeedback
        ]}>
          <Text style={styles.feedbackText}>{feedbackMessage}</Text>
        </View>
      )}
      
      {/* Last command */}
      {lastCommandText && !emergencyMode ? (
        <View style={styles.lastCommandContainer}>
          <Text style={styles.lastCommandText}>{lastCommandText}</Text>
        </View>
      ) : null}
      
      {/* Voice button - enhanced for safety */}
      <TouchableOpacity 
        style={[
          styles.voiceButton,
          isListening && styles.voiceButtonActive,
          voiceFirst && styles.voiceFirstButton,
          isDriving && styles.drivingModeButton,
          emergencyMode && styles.emergencyButton,
          autoPaused && styles.pausedButton
        ]}
        onPress={() => {
          if (emergencyMode) {
            setEmergencyMode(false);
            provideSafetyFeedback('Emergency mode cleared', false);
          } else {
            if (isListening) {
              stopListening();
              setFeedbackMessage("Voice recognition stopped");
            } else {
              startListening();
              setFeedbackMessage("Listening...");
            }
          }
        }}
        onLongPress={() => handleEmergencyStop('Long press')}
      >
        <Ionicons 
          name={emergencyMode ? "hand-left" : (isListening ? "mic" : "mic-outline")} 
          size={voiceFirst || isDriving ? 48 : 24} 
          color="#fff" 
        />
        {(voiceFirst || isDriving) && (
          <Text style={styles.voiceFirstText}>
            {emergencyMode ? 'STOPPED' : (isListening ? 'Listening...' : 'Tap to speak')}
          </Text>
        )}
      </TouchableOpacity>
      
      {/* Emergency stop button for driving mode */}
      {isDriving && !emergencyMode && (
        <TouchableOpacity 
          style={styles.emergencyStopButton}
          onPress={() => handleEmergencyStop('Button press')}
        >
          <Ionicons name="hand-left" size={32} color="#fff" />
          <Text style={styles.emergencyStopText}>STOP</Text>
        </TouchableOpacity>
      )}
      
      {/* Help button */}
      <TouchableOpacity 
        style={styles.helpButton}
        onPress={() => {
          if (isDriving) {
            provideVoiceHelp();
          } else {
            setHelpModalVisible(true);
          }
        }}
      >
        <Ionicons name="help-circle-outline" size={24} color="#555" />
      </TouchableOpacity>
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
  emergencyButton: {
    backgroundColor: '#f44336',
  },
  pausedButton: {
    backgroundColor: '#ff9800',
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
  emergencyFeedback: {
    backgroundColor: 'rgba(244, 67, 54, 0.9)',
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
  safetyIndicator: {
    position: 'absolute',
    top: -80,
    right: 0,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  safetyText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  safetyWarningContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 152, 0, 0.9)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
    position: 'absolute',
    bottom: 140,
    right: -10,
    gap: 4,
  },
  safetyWarningText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
  },
  emergencyStopButton: {
    position: 'absolute',
    bottom: 180,
    right: 40,
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#f44336',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 5,
    elevation: 8,
  },
  emergencyStopText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
    marginTop: 4,
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
  safetyNotice: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff3e0',
    padding: 10,
    borderRadius: 8,
    marginBottom: 15,
    gap: 8,
  },
  safetyNoticeText: {
    flex: 1,
    fontSize: 12,
    color: '#e65100',
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
  alwaysAvailable: {
    fontSize: 10,
    color: '#4caf50',
    fontWeight: 'bold',
    marginTop: 2,
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
});

export default SafeVoiceCommandListener;