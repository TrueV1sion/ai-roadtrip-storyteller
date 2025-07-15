import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Platform,
  ActivityIndicator
} from 'react-native';
import Slider from '@react-native-community/slider';
import { FontAwesome5, MaterialIcons, Ionicons } from '@expo/vector-icons';
import { EmotionType } from '../../types/voice';

interface SpeechControlPanelProps {
  isPlaying: boolean;
  isPaused: boolean;
  isLoading: boolean;
  progress: number;
  duration: number;
  characterName: string;
  emotion: EmotionType;
  onPlayPause: () => void;
  onStop: () => void;
  onSeek: (position: number) => void;
  onEmotionChange?: (emotion: EmotionType) => void;
  speakingText?: string;
}

const SpeechControlPanel: React.FC<SpeechControlPanelProps> = ({
  isPlaying,
  isPaused,
  isLoading,
  progress,
  duration,
  characterName,
  emotion,
  onPlayPause,
  onStop,
  onSeek,
  onEmotionChange,
  speakingText
}) => {
  const [sliderValue, setSliderValue] = useState(0);
  const [isSeeking, setIsSeeking] = useState(false);
  const animatedValue = useRef(new Animated.Value(0)).current;
  
  // Update slider value when progress changes
  useEffect(() => {
    if (!isSeeking && duration > 0) {
      setSliderValue(progress / duration);
    }
  }, [progress, duration, isSeeking]);
  
  // Start animation when playing
  useEffect(() => {
    if (isPlaying && !isPaused) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(animatedValue, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: true,
          }),
          Animated.timing(animatedValue, {
            toValue: 0.3,
            duration: 1000,
            useNativeDriver: true,
          }),
        ])
      ).start();
    } else {
      animatedValue.setValue(0.7);
      Animated.timing(animatedValue).stop();
    }
  }, [isPlaying, isPaused, animatedValue]);
  
  // Format time in mm:ss
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };
  
  // Get emotion icon
  const getEmotionIcon = (emotionType: EmotionType) => {
    switch (emotionType) {
      case 'happy':
        return <FontAwesome5 name="smile" size={18} color="#4CAF50" />;
      case 'sad':
        return <FontAwesome5 name="frown" size={18} color="#607D8B" />;
      case 'angry':
        return <FontAwesome5 name="angry" size={18} color="#F44336" />;
      case 'excited':
        return <FontAwesome5 name="grin-stars" size={18} color="#FF9800" />;
      case 'calm':
        return <FontAwesome5 name="meh" size={18} color="#03A9F4" />;
      case 'fearful':
        return <FontAwesome5 name="grimace" size={18} color="#9C27B0" />;
      case 'surprised':
        return <FontAwesome5 name="surprise" size={18} color="#FFEB3B" />;
      default:
        return <FontAwesome5 name="meh-blank" size={18} color="#9E9E9E" />;
    }
  };
  
  // Handle slider change
  const handleSliderChange = (value: number) => {
    setSliderValue(value);
  };
  
  // Handle slider complete
  const handleSliderComplete = (value: number) => {
    setIsSeeking(false);
    if (duration > 0) {
      onSeek(value * duration);
    }
  };
  
  return (
    <View style={styles.container}>
      <View style={styles.characterInfoContainer}>
        <View style={styles.nameContainer}>
          <Text style={styles.characterName}>{characterName}</Text>
          {getEmotionIcon(emotion)}
        </View>
        
        {speakingText && (
          <Text style={styles.speakingText} numberOfLines={1} ellipsizeMode="tail">
            {speakingText}
          </Text>
        )}
      </View>
      
      <View style={styles.controlsContainer}>
        <Animated.View style={[
          styles.soundWaveContainer,
          { opacity: animatedValue }
        ]}>
          <View style={styles.soundWave}>
            <View style={[styles.waveLine, styles.waveLineSmall]} />
            <View style={[styles.waveLine, styles.waveLineMedium]} />
            <View style={[styles.waveLine, styles.waveLineTall]} />
            <View style={[styles.waveLine, styles.waveLineMedium]} />
            <View style={[styles.waveLine, styles.waveLineSmall]} />
          </View>
        </Animated.View>
        
        <View style={styles.buttons}>
          {isLoading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="small" color="#2196F3" />
            </View>
          ) : (
            <TouchableOpacity
              style={styles.playPauseButton}
              onPress={onPlayPause}
            >
              <FontAwesome5 
                name={isPlaying && !isPaused ? "pause" : "play"} 
                size={20} 
                color="white" 
              />
            </TouchableOpacity>
          )}
          
          <TouchableOpacity
            style={styles.stopButton}
            onPress={onStop}
          >
            <FontAwesome5 name="stop" size={16} color="white" />
          </TouchableOpacity>
          
          {onEmotionChange && (
            <TouchableOpacity
              style={styles.emotionButton}
              onPress={() => {
                // Simple emotion cycling logic
                const emotions: EmotionType[] = ['neutral', 'happy', 'sad', 'excited', 'calm'];
                const currentIndex = emotions.indexOf(emotion);
                const nextIndex = (currentIndex + 1) % emotions.length;
                onEmotionChange(emotions[nextIndex]);
              }}
            >
              {getEmotionIcon(emotion)}
            </TouchableOpacity>
          )}
        </View>
      </View>
      
      <View style={styles.progressContainer}>
        <Text style={styles.timeText}>
          {formatTime(progress)}
        </Text>
        
        <Slider
          style={styles.slider}
          minimumValue={0}
          maximumValue={1}
          value={sliderValue}
          minimumTrackTintColor="#2196F3"
          maximumTrackTintColor="#E0E0E0"
          thumbTintColor="#2196F3"
          onValueChange={handleSliderChange}
          onSlidingStart={() => setIsSeeking(true)}
          onSlidingComplete={handleSliderComplete}
        />
        
        <Text style={styles.timeText}>
          {formatTime(duration)}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    margin: 16,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
      },
      android: {
        elevation: 3,
      },
    }),
  },
  characterInfoContainer: {
    marginBottom: 12,
  },
  nameContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  characterName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginRight: 8,
  },
  speakingText: {
    fontSize: 12,
    color: '#757575',
    fontStyle: 'italic',
  },
  controlsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  soundWaveContainer: {
    flex: 1,
    height: 40,
    justifyContent: 'center',
  },
  soundWave: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    height: 40,
  },
  waveLine: {
    width: 3,
    backgroundColor: '#2196F3',
    marginHorizontal: 3,
    borderRadius: 1.5,
  },
  waveLineSmall: {
    height: 10,
  },
  waveLineMedium: {
    height: 20,
  },
  waveLineTall: {
    height: 30,
  },
  buttons: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  loadingContainer: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  playPauseButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#2196F3',
    justifyContent: 'center',
    alignItems: 'center',
  },
  stopButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#F44336',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 10,
  },
  emotionButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#f0f0f0',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 10,
  },
  progressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  timeText: {
    fontSize: 12,
    color: '#757575',
    width: 35,
    textAlign: 'center',
  },
  slider: {
    flex: 1,
    height: 40,
    marginHorizontal: 8,
  },
});

export default SpeechControlPanel;