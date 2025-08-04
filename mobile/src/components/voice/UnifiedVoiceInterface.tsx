/**
 * Unified Voice Interface Component
 * 
 * Implements the "One Voice, Zero Friction" principle
 * This is the ONLY interface users need while driving
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Dimensions,
  Platform,
  AccessibilityInfo,
  ScrollView,
  Modal,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import * as Haptics from 'expo-haptics';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import unifiedVoiceOrchestrator from '../../services/voice/unifiedVoiceOrchestrator';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface UnifiedVoiceInterfaceProps {
  isDriving?: boolean;
  onVisualDataReceived?: (data: any) => void;
}

export const UnifiedVoiceInterface: React.FC<UnifiedVoiceInterfaceProps> = ({
  isDriving = true,
  onVisualDataReceived,
}) => {
  const insets = useSafeAreaInsets();
  
  // Animation values
  const [pulseAnim] = useState(new Animated.Value(1));
  const [fadeAnim] = useState(new Animated.Value(0));
  const [voiceWaveAnim] = useState(new Animated.Value(0));
  
  // State
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [conversationState, setConversationState] = useState<string>('idle');
  const [proactiveSuggestion, setProactiveSuggestion] = useState<any>(null);
  const [recentActions, setRecentActions] = useState<any[]>([]);
  
  // Refs
  const transcriptTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    // Subscribe to orchestrator events
    const handleRecordingStarted = () => {
      setIsListening(true);
      startPulseAnimation();
    };
    
    const handleRecordingStopped = () => {
      setIsListening(false);
      stopPulseAnimation();
    };
    
    const handleProcessing = () => {
      setIsProcessing(true);
    };
    
    const handleTranscriptReceived = (transcript: string) => {
      setCurrentTranscript(transcript);
      setIsProcessing(false);
      showTranscript();
    };
    
    const handlePlaybackStarted = () => {
      setIsPlaying(true);
      startVoiceWaveAnimation();
    };
    
    const handlePlaybackFinished = () => {
      setIsPlaying(false);
      stopVoiceWaveAnimation();
    };
    
    const handleStateChanged = (state: string) => {
      setConversationState(state);
    };
    
    const handleActionsCompleted = (actions: any[]) => {
      setRecentActions(actions);
      // Show actions briefly
      setTimeout(() => setRecentActions([]), 5000);
    };
    
    const handleProactiveSuggestion = (suggestion: any) => {
      setProactiveSuggestion(suggestion);
      // Auto-dismiss after 10 seconds if dismissible
      if (suggestion.can_dismiss) {
        setTimeout(() => setProactiveSuggestion(null), 10000);
      }
    };
    
    const handleVisualData = (data: any) => {
      onVisualDataReceived?.(data);
    };
    
    const handleError = (error: string) => {
      setCurrentTranscript(`Error: ${error}`);
      showTranscript();
      setIsProcessing(false);
      setIsListening(false);
    };

    // Subscribe to events
    unifiedVoiceOrchestrator.on('recordingStarted', handleRecordingStarted);
    unifiedVoiceOrchestrator.on('recordingStopped', handleRecordingStopped);
    unifiedVoiceOrchestrator.on('processing', handleProcessing);
    unifiedVoiceOrchestrator.on('transcriptReceived', handleTranscriptReceived);
    unifiedVoiceOrchestrator.on('playbackStarted', handlePlaybackStarted);
    unifiedVoiceOrchestrator.on('playbackFinished', handlePlaybackFinished);
    unifiedVoiceOrchestrator.on('stateChanged', handleStateChanged);
    unifiedVoiceOrchestrator.on('actionsCompleted', handleActionsCompleted);
    unifiedVoiceOrchestrator.on('proactiveSuggestion', handleProactiveSuggestion);
    unifiedVoiceOrchestrator.on('visualDataReceived', handleVisualData);
    unifiedVoiceOrchestrator.on('error', handleError);

    return () => {
      // Unsubscribe from events
      unifiedVoiceOrchestrator.off('recordingStarted', handleRecordingStarted);
      unifiedVoiceOrchestrator.off('recordingStopped', handleRecordingStopped);
      unifiedVoiceOrchestrator.off('processing', handleProcessing);
      unifiedVoiceOrchestrator.off('transcriptReceived', handleTranscriptReceived);
      unifiedVoiceOrchestrator.off('playbackStarted', handlePlaybackStarted);
      unifiedVoiceOrchestrator.off('playbackFinished', handlePlaybackFinished);
      unifiedVoiceOrchestrator.off('stateChanged', handleStateChanged);
      unifiedVoiceOrchestrator.off('actionsCompleted', handleActionsCompleted);
      unifiedVoiceOrchestrator.off('proactiveSuggestion', handleProactiveSuggestion);
      unifiedVoiceOrchestrator.off('visualDataReceived', handleVisualData);
      unifiedVoiceOrchestrator.off('error', handleError);
    };
  }, [onVisualDataReceived]);

  // Animation methods
  const startPulseAnimation = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.3,
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
    pulseAnim.stopAnimation();
    Animated.timing(pulseAnim, {
      toValue: 1,
      duration: 300,
      useNativeDriver: true,
    }).start();
  };

  const startVoiceWaveAnimation = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(voiceWaveAnim, {
          toValue: 1,
          duration: 2000,
          useNativeDriver: true,
        }),
        Animated.timing(voiceWaveAnim, {
          toValue: 0,
          duration: 2000,
          useNativeDriver: true,
        }),
      ])
    ).start();
  };

  const stopVoiceWaveAnimation = () => {
    voiceWaveAnim.stopAnimation();
    Animated.timing(voiceWaveAnim, {
      toValue: 0,
      duration: 300,
      useNativeDriver: true,
    }).start();
  };

  const showTranscript = () => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 300,
      useNativeDriver: true,
    }).start();

    // Clear previous timeout
    if (transcriptTimeoutRef.current) {
      clearTimeout(transcriptTimeoutRef.current);
    }

    // Hide after 5 seconds
    transcriptTimeoutRef.current = setTimeout(() => {
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }).start(() => {
        setCurrentTranscript('');
      });
    }, 5000);
  };

  // Main voice button handler
  const handleVoicePress = useCallback(async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    
    try {
      await unifiedVoiceOrchestrator.startVoiceInteraction();
      
      const message = isListening ? 'Stopped listening' : 'Listening for your command';
      AccessibilityInfo.announceForAccessibility(message);
    } catch (error) {
      logger.error('Voice interaction error:', error);
    }
  }, [isListening]);

  // Dismiss proactive suggestion
  const dismissProactiveSuggestion = useCallback(() => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setProactiveSuggestion(null);
  }, []);

  // Get state color
  const getStateColor = () => {
    switch (conversationState) {
      case 'gathering_info': return '#FFA500';
      case 'awaiting_confirmation': return '#FF6B6B';
      case 'processing_request': return '#4ECDC4';
      case 'telling_story': return '#95E1D3';
      default: return '#007AFF';
    }
  };

  // Get voice button size
  const voiceButtonSize = isDriving ? 140 : 100;

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Minimal feedback area */}
      <View style={styles.feedbackArea}>
        {/* Transcript display */}
        {currentTranscript !== '' && (
          <Animated.View
            style={[
              styles.transcriptContainer,
              { opacity: fadeAnim }
            ]}
          >
            <BlurView intensity={80} style={styles.transcriptBlur}>
              <Text style={styles.transcriptText} numberOfLines={3}>
                {currentTranscript}
              </Text>
            </BlurView>
          </Animated.View>
        )}

        {/* Recent actions feedback */}
        {recentActions.length > 0 && (
          <View style={styles.actionsContainer}>
            {recentActions.map((action, index) => (
              <View key={index} style={styles.actionItem}>
                <MaterialIcons name="check-circle" size={20} color="#4CAF50" />
                <Text style={styles.actionText}>{action.detail}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Voice wave visualization when playing */}
        {isPlaying && (
          <Animated.View
            style={[
              styles.voiceWaveContainer,
              {
                opacity: voiceWaveAnim,
                transform: [{
                  scale: voiceWaveAnim.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.8, 1.2],
                  })
                }]
              }
            ]}
          >
            {[...Array(5)].map((_, i) => (
              <View
                key={i}
                style={[
                  styles.voiceWave,
                  { height: 20 + Math.random() * 30 }
                ]}
              />
            ))}
          </Animated.View>
        )}
      </View>

      {/* Voice activation button */}
      <View style={styles.voiceButtonContainer}>
        <TouchableOpacity
          style={[
            styles.voiceButton,
            {
              width: voiceButtonSize,
              height: voiceButtonSize,
              borderRadius: voiceButtonSize / 2,
              backgroundColor: getStateColor(),
            }
          ]}
          onPress={handleVoicePress}
          activeOpacity={0.8}
          accessibilityLabel="Voice command"
          accessibilityHint="Tap to talk to your road trip companion"
          accessibilityRole="button"
          disabled={isProcessing}
        >
          <Animated.View
            style={{
              transform: [{ scale: pulseAnim }],
            }}
          >
            {isProcessing ? (
              <MaterialIcons name="hourglass-empty" size={60} color="#FFFFFF" />
            ) : isListening ? (
              <MaterialIcons name="mic" size={60} color="#FFFFFF" />
            ) : isPlaying ? (
              <MaterialIcons name="volume-up" size={60} color="#FFFFFF" />
            ) : (
              <MaterialIcons name="mic-none" size={60} color="#FFFFFF" />
            )}
          </Animated.View>
        </TouchableOpacity>

        {/* Conversation state indicator */}
        <Text style={styles.stateText}>
          {conversationState === 'idle' ? 'Tap to speak' :
           conversationState === 'gathering_info' ? 'Tell me more...' :
           conversationState === 'awaiting_confirmation' ? 'Confirm?' :
           conversationState === 'processing_request' ? 'Working on it...' :
           conversationState === 'telling_story' ? 'Sharing story...' :
           'Ready'}
        </Text>
      </View>

      {/* Proactive suggestion popup */}
      {proactiveSuggestion && (
        <Animated.View
          style={[
            styles.proactiveSuggestion,
            {
              transform: [{
                translateY: Animated.subtract(0, Animated.multiply(fadeAnim, 100))
              }]
            }
          ]}
        >
          <BlurView intensity={90} style={styles.suggestionBlur}>
            <View style={styles.suggestionContent}>
              <MaterialIcons name="lightbulb-outline" size={24} color="#FFA500" />
              <Text style={styles.suggestionText}>{proactiveSuggestion.transcript}</Text>
              {proactiveSuggestion.can_dismiss && (
                <TouchableOpacity
                  onPress={dismissProactiveSuggestion}
                  style={styles.dismissButton}
                  accessibilityLabel="Dismiss suggestion"
                >
                  <MaterialIcons name="close" size={20} color="#666" />
                </TouchableOpacity>
              )}
            </View>
          </BlurView>
        </Animated.View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  feedbackArea: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  transcriptContainer: {
    position: 'absolute',
    top: 50,
    left: 20,
    right: 20,
  },
  transcriptBlur: {
    borderRadius: 20,
    overflow: 'hidden',
    padding: 16,
  },
  transcriptText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    textAlign: 'center',
  },
  actionsContainer: {
    position: 'absolute',
    bottom: 200,
    left: 20,
    right: 20,
  },
  actionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 20,
    padding: 12,
    marginBottom: 8,
  },
  actionText: {
    marginLeft: 8,
    fontSize: 16,
    color: '#333',
    flex: 1,
  },
  voiceWaveContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 60,
    gap: 8,
  },
  voiceWave: {
    width: 4,
    backgroundColor: '#007AFF',
    borderRadius: 2,
  },
  voiceButtonContainer: {
    position: 'absolute',
    bottom: 60,
    alignSelf: 'center',
    alignItems: 'center',
  },
  voiceButton: {
    justifyContent: 'center',
    alignItems: 'center',
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.3,
        shadowRadius: 10,
      },
      android: {
        elevation: 10,
      },
    }),
  },
  stateText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
    fontWeight: '500',
  },
  proactiveSuggestion: {
    position: 'absolute',
    top: 100,
    left: 20,
    right: 20,
  },
  suggestionBlur: {
    borderRadius: 16,
    overflow: 'hidden',
  },
  suggestionContent: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  suggestionText: {
    flex: 1,
    marginHorizontal: 12,
    fontSize: 16,
    color: '#333',
  },
  dismissButton: {
    padding: 4,
  },
});