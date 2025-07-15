import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  Modal,
  Dimensions,
  Platform,
  AccessibilityInfo,
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import * as Haptics from 'expo-haptics';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

interface VoiceFirstInterfaceProps {
  isListening: boolean;
  onVoiceButtonPress: () => void;
  currentAction?: string;
  showConfirmation?: boolean;
  onConfirm?: () => void;
  onCancel?: () => void;
  voiceLevel?: number;
  isDriving?: boolean;
}

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

export const VoiceFirstInterface: React.FC<VoiceFirstInterfaceProps> = ({
  isListening,
  onVoiceButtonPress,
  currentAction,
  showConfirmation,
  onConfirm,
  onCancel,
  voiceLevel = 0,
  isDriving = true,
}) => {
  const insets = useSafeAreaInsets();
  const [pulseAnim] = useState(new Animated.Value(1));
  const [voiceLevelAnim] = useState(new Animated.Value(0));
  const [showHelp, setShowHelp] = useState(false);

  // Animate voice button when listening
  useEffect(() => {
    if (isListening) {
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
    } else {
      pulseAnim.setValue(1);
    }
  }, [isListening, pulseAnim]);

  // Animate voice level indicator
  useEffect(() => {
    Animated.timing(voiceLevelAnim, {
      toValue: voiceLevel,
      duration: 100,
      useNativeDriver: false,
    }).start();
  }, [voiceLevel, voiceLevelAnim]);

  const handleVoicePress = useCallback(() => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    onVoiceButtonPress();
    
    // Announce state change for accessibility
    const message = isListening ? 'Voice command stopped' : 'Listening for voice command';
    AccessibilityInfo.announceForAccessibility(message);
  }, [isListening, onVoiceButtonPress]);

  const handleConfirm = useCallback(() => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    onConfirm?.();
  }, [onConfirm]);

  const handleCancel = useCallback(() => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
    onCancel?.();
  }, [onCancel]);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      {/* Minimal visual feedback area */}
      <View style={styles.feedbackArea}>
        {currentAction && (
          <BlurView intensity={80} style={styles.actionDisplay}>
            <Text style={styles.actionText} numberOfLines={2}>
              {currentAction}
            </Text>
          </BlurView>
        )}
      </View>

      {/* Large voice activation button */}
      <View style={styles.voiceButtonContainer}>
        <TouchableOpacity
          style={styles.voiceButton}
          onPress={handleVoicePress}
          activeOpacity={0.8}
          accessibilityLabel="Voice command button"
          accessibilityHint="Double tap to start or stop voice commands"
          accessibilityRole="button"
        >
          <Animated.View
            style={[
              styles.voiceButtonInner,
              {
                transform: [{ scale: pulseAnim }],
              },
            ]}
          >
            <MaterialIcons
              name={isListening ? 'mic' : 'mic-none'}
              size={isDriving ? 60 : 48}
              color="#FFFFFF"
            />
          </Animated.View>
          
          {/* Voice level indicator */}
          {isListening && (
            <Animated.View
              style={[
                styles.voiceLevelIndicator,
                {
                  height: voiceLevelAnim.interpolate({
                    inputRange: [0, 1],
                    outputRange: ['0%', '100%'],
                  }),
                },
              ]}
            />
          )}
        </TouchableOpacity>

        {/* Quick action buttons - larger for driving */}
        <View style={styles.quickActions}>
          <TouchableOpacity
            style={[styles.quickActionButton, isDriving && styles.quickActionButtonLarge]}
            onPress={() => setShowHelp(true)}
            accessibilityLabel="Help"
            accessibilityHint="Show available voice commands"
          >
            <MaterialIcons name="help-outline" size={isDriving ? 36 : 28} color="#666" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Confirmation Modal */}
      {showConfirmation && (
        <Modal
          animationType="fade"
          transparent
          visible={showConfirmation}
          onRequestClose={handleCancel}
        >
          <BlurView intensity={90} style={styles.modalOverlay}>
            <View style={styles.confirmationModal}>
              <Text style={styles.confirmationText}>{currentAction}</Text>
              <View style={styles.confirmationButtons}>
                <TouchableOpacity
                  style={[styles.confirmButton, styles.confirmButtonYes]}
                  onPress={handleConfirm}
                  accessibilityLabel="Confirm"
                  accessibilityRole="button"
                >
                  <MaterialIcons name="check" size={40} color="#FFFFFF" />
                  <Text style={styles.confirmButtonText}>YES</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.confirmButton, styles.confirmButtonNo]}
                  onPress={handleCancel}
                  accessibilityLabel="Cancel"
                  accessibilityRole="button"
                >
                  <MaterialIcons name="close" size={40} color="#FFFFFF" />
                  <Text style={styles.confirmButtonText}>NO</Text>
                </TouchableOpacity>
              </View>
            </View>
          </BlurView>
        </Modal>
      )}

      {/* Help Modal */}
      <Modal
        animationType="slide"
        transparent
        visible={showHelp}
        onRequestClose={() => setShowHelp(false)}
      >
        <BlurView intensity={95} style={styles.modalOverlay}>
          <View style={styles.helpModal}>
            <View style={styles.helpHeader}>
              <Text style={styles.helpTitle}>Voice Commands</Text>
              <TouchableOpacity
                onPress={() => setShowHelp(false)}
                style={styles.helpCloseButton}
                accessibilityLabel="Close help"
              >
                <MaterialIcons name="close" size={32} color="#333" />
              </TouchableOpacity>
            </View>
            <View style={styles.helpContent}>
              <HelpSection
                title="Navigation"
                commands={[
                  'Navigate to [destination]',
                  'Find gas station',
                  'Find rest stop',
                  'Show alternative routes',
                ]}
              />
              <HelpSection
                title="Control"
                commands={['Pause/Resume', 'Volume up/down', 'Mute']}
              />
              <HelpSection
                title="Entertainment"
                commands={[
                  'Tell me a story',
                  'Play trivia',
                  'Find something interesting',
                ]}
              />
            </View>
          </View>
        </BlurView>
      </Modal>
    </View>
  );
};

const HelpSection: React.FC<{ title: string; commands: string[] }> = ({
  title,
  commands,
}) => (
  <View style={styles.helpSection}>
    <Text style={styles.helpSectionTitle}>{title}</Text>
    {commands.map((command, index) => (
      <Text key={index} style={styles.helpCommand}>
        "{command}"
      </Text>
    ))}
  </View>
);

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
  actionDisplay: {
    paddingHorizontal: 24,
    paddingVertical: 16,
    borderRadius: 20,
    maxWidth: SCREEN_WIDTH * 0.9,
  },
  actionText: {
    fontSize: 20,
    fontWeight: '600',
    color: '#333',
    textAlign: 'center',
  },
  voiceButtonContainer: {
    position: 'absolute',
    bottom: 40,
    alignSelf: 'center',
    alignItems: 'center',
  },
  voiceButton: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
      },
      android: {
        elevation: 8,
      },
    }),
  },
  voiceButtonInner: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  voiceLevelIndicator: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderBottomLeftRadius: 60,
    borderBottomRightRadius: 60,
  },
  quickActions: {
    flexDirection: 'row',
    marginTop: 20,
  },
  quickActionButton: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#F0F0F0',
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 8,
  },
  quickActionButtonLarge: {
    width: 72,
    height: 72,
    borderRadius: 36,
  },
  modalOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  confirmationModal: {
    backgroundColor: 'white',
    borderRadius: 20,
    padding: 24,
    width: SCREEN_WIDTH * 0.9,
    maxWidth: 400,
  },
  confirmationText: {
    fontSize: 24,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 32,
    color: '#333',
  },
  confirmationButtons: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  confirmButton: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: 'center',
    alignItems: 'center',
  },
  confirmButtonYes: {
    backgroundColor: '#4CAF50',
  },
  confirmButtonNo: {
    backgroundColor: '#F44336',
  },
  confirmButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 8,
  },
  helpModal: {
    backgroundColor: 'white',
    borderRadius: 20,
    width: SCREEN_WIDTH * 0.9,
    maxWidth: 400,
    maxHeight: SCREEN_HEIGHT * 0.8,
  },
  helpHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  helpTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  helpCloseButton: {
    padding: 4,
  },
  helpContent: {
    padding: 20,
  },
  helpSection: {
    marginBottom: 24,
  },
  helpSectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#007AFF',
    marginBottom: 8,
  },
  helpCommand: {
    fontSize: 16,
    color: '#666',
    paddingVertical: 4,
    paddingLeft: 12,
  },
});