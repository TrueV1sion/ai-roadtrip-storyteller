import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Animated } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import AudioPlayer from './AudioPlayer';

interface StoryCardProps {
  title: string;
  content: string;
  audioBase64?: string;
  onRefresh: () => void;
  onPlaybackStatusUpdate?: (isPlaying: boolean) => void;
  onError?: (error: string) => void;
  fadeAnim: Animated.Value;
  slideAnim: Animated.Value;
}

const StoryCard: React.FC<StoryCardProps> = ({
  title,
  content,
  audioBase64,
  onRefresh,
  onPlaybackStatusUpdate,
  onError,
  fadeAnim,
  slideAnim
}) => {
  return (
    <Animated.View
      style={[
        styles.container,
        {
          opacity: fadeAnim,
          transform: [{ translateY: slideAnim }]
        }
      ]}
    >
      <View style={styles.header}>
        <Text style={styles.title}>{title}</Text>
        <TouchableOpacity onPress={onRefresh} style={styles.refreshButton}>
          <Ionicons name="refresh" size={24} color="#f4511e" />
        </TouchableOpacity>
      </View>
      
      <Text style={styles.content}>{content}</Text>
      
      <View style={styles.audioContainer}>
        <AudioPlayer 
          audioBase64={audioBase64}
          onPlaybackStatusUpdate={onPlaybackStatusUpdate}
          onError={onError}
        />
      </View>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginVertical: 10,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#444',
    flex: 1,
  },
  refreshButton: {
    padding: 8,
  },
  content: {
    fontSize: 16,
    lineHeight: 24,
    color: '#333',
    marginBottom: 16,
  },
  audioContainer: {
    marginTop: 8,
  }
});

export default StoryCard; 