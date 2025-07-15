import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Easing
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import GameLauncher from './games/GameLauncher';
import { GameType } from '../services/gameEngine/GameStateManager';
import { locationService } from '../services/locationService';
import { useVoiceCommands } from '../hooks/useVoiceCommands';
import VoiceCommandListener from './VoiceCommandListener';

interface InteractiveFeatureButtonProps {
  onImmersiveExperienceRequest?: () => void;
}

type FeatureType = 'game' | 'voice' | 'story';

interface FeatureOption {
  id: string;
  type: FeatureType;
  icon: string;
  label: string;
  color: string;
  action: () => void;
}

const InteractiveFeatureButton: React.FC<InteractiveFeatureButtonProps> = ({
  onImmersiveExperienceRequest
}) => {
  // State
  const [isExpanded, setIsExpanded] = useState(false);
  const [showGameLauncher, setShowGameLauncher] = useState(false);
  const [showVoiceCommandListener, setShowVoiceCommandListener] = useState(false);
  
  // Voice commands hook
  const { isListening, startListening, stopListening } = useVoiceCommands();
  
  // Animation values
  const expandAnim = useRef(new Animated.Value(0)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;
  
  // Feature options
  const featureOptions: FeatureOption[] = [
    {
      id: 'game',
      type: 'game',
      icon: 'game-controller-outline',
      label: 'Games',
      color: '#f4511e',
      action: () => {
        toggleExpand();
        setShowGameLauncher(true);
      }
    },
    {
      id: 'voice',
      type: 'voice',
      icon: 'mic-outline',
      label: 'Voice',
      color: '#4CAF50',
      action: () => {
        toggleExpand();
        handleVoiceCommand();
      }
    },
    {
      id: 'story',
      type: 'story',
      icon: 'book-outline',
      label: 'Story',
      color: '#2196F3',
      action: () => {
        toggleExpand();
        if (onImmersiveExperienceRequest) {
          onImmersiveExperienceRequest();
        }
      }
    }
  ];
  
  // Toggle expanded state
  const toggleExpand = () => {
    const newValue = !isExpanded;
    setIsExpanded(newValue);
    
    // Animation
    Animated.parallel([
      Animated.timing(expandAnim, {
        toValue: newValue ? 1 : 0,
        duration: 300,
        easing: Easing.bezier(0.4, 0, 0.2, 1),
        useNativeDriver: false
      }),
      Animated.timing(rotateAnim, {
        toValue: newValue ? 1 : 0,
        duration: 300,
        easing: Easing.bezier(0.4, 0, 0.2, 1),
        useNativeDriver: true
      })
    ]).start();
  };
  
  // Handle voice command
  const handleVoiceCommand = () => {
    // Toggle voice commands UI
    setShowVoiceCommandListener(!showVoiceCommandListener);
    
    // If we're showing the UI, start listening
    if (!showVoiceCommandListener) {
      startListening();
    } else {
      stopListening();
    }
  };
  
  // Handlers for voice commands
  const handleStoryCommand = (action: string, params?: string[]) => {
    console.log('Story command:', action, params);
    // Implement story command handling
  };
  
  const handleNavigationCommand = (action: string, params?: string[]) => {
    console.log('Navigation command:', action, params);
    // Implement navigation command handling
  };
  
  const handlePlaybackCommand = (action: string, params?: string[]) => {
    console.log('Playback command:', action, params);
    // Implement playback command handling
    
    if (action === 'play' && onImmersiveExperienceRequest) {
      onImmersiveExperienceRequest();
    }
  };
  
  // Computed styles
  const fabRotation = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '45deg']
  });
  
  // Render feature option buttons
  const renderFeatureOptions = () => {
    return featureOptions.map((option, index) => {
      const translateY = expandAnim.interpolate({
        inputRange: [0, 1],
        outputRange: [0, -60 * (index + 1)]
      });
      
      const scale = expandAnim.interpolate({
        inputRange: [0, 0.8, 1],
        outputRange: [0, 0.8, 1]
      });
      
      const opacity = expandAnim.interpolate({
        inputRange: [0, 0.8, 1],
        outputRange: [0, 0.5, 1]
      });
      
      return (
        <Animated.View
          key={option.id}
          style={[
            styles.optionContainer,
            {
              transform: [
                { translateY },
                { scale }
              ],
              opacity
            }
          ]}
        >
          <TouchableOpacity
            testID={`feature-option-${option.id}`}
            style={[styles.optionButton, { backgroundColor: option.color }]}
            onPress={option.action}
          >
            <Ionicons name={option.icon as any} size={24} color="#fff" />
          </TouchableOpacity>
          <Animated.View
            style={[
              styles.optionLabel,
              {
                opacity
              }
            ]}
          >
            <Text style={styles.optionLabelText}>{option.label}</Text>
          </Animated.View>
        </Animated.View>
      );
    });
  };
  
  return (
    <View style={styles.container}>
      {/* Feature options */}
      {renderFeatureOptions()}
      
      {/* Main FAB */}
      <TouchableOpacity testID="main-fab" style={styles.fab} onPress={toggleExpand} activeOpacity={0.8}>
        <Animated.View style={{ transform: [{ rotate: fabRotation }] }}>
          <Ionicons name="add" size={30} color="#fff" />
        </Animated.View>
        
        {/* Listening indicator */}
        {isListening && (
          <View testID="listening-indicator" style={styles.listeningIndicator} />
        )}
      </TouchableOpacity>
      
      {/* Game launcher modal */}
      <GameLauncher
        visible={showGameLauncher}
        onClose={() => setShowGameLauncher(false)}
      />
      
      {/* Voice command listener */}
      {showVoiceCommandListener && (
        <VoiceCommandListener
          onStoryCommand={handleStoryCommand}
          onNavigationCommand={handleNavigationCommand}
          onPlaybackCommand={handlePlaybackCommand}
        />
      )}
      
      {/* Backdrop overlay when expanded */}
      {isExpanded && (
        <TouchableOpacity
          testID="backdrop"
          style={styles.backdrop}
          activeOpacity={1}
          onPress={toggleExpand}
        />
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
    zIndex: 999,
  },
  fab: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#f4511e',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
    zIndex: 2,
  },
  optionContainer: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    paddingHorizontal: 8,
    zIndex: 1,
  },
  optionButton: {
    width: 46,
    height: 46,
    borderRadius: 23,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
  },
  optionLabel: {
    position: 'absolute',
    right: 56,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4,
  },
  optionLabelText: {
    color: '#fff',
    fontSize: 14,
  },
  backdrop: {
    position: 'absolute',
    top: -1000,
    left: -1000,
    right: -1000,
    bottom: -1000,
    backgroundColor: 'transparent',
    zIndex: 0,
  },
  listeningIndicator: {
    position: 'absolute',
    top: -8,
    right: -8,
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#f00',
    borderWidth: 2,
    borderColor: '#fff',
  },
});

export default InteractiveFeatureButton;
