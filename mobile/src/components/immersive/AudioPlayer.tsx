import React, { useState, useEffect } from 'react';
import { View, TouchableOpacity, StyleSheet, Text } from 'react-native';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';

interface AudioPlayerProps {
  audioBase64?: string;
  onPlaybackStatusUpdate?: (isPlaying: boolean) => void;
  onError?: (error: string) => void;
}

const AudioPlayer: React.FC<AudioPlayerProps> = ({
  audioBase64,
  onPlaybackStatusUpdate,
  onError
}) => {
  const [sound, setSound] = useState<Audio.Sound | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    return () => {
      if (sound) {
        sound.unloadAsync();
      }
    };
  }, [sound]);

  useEffect(() => {
    // If we get new audio content, unload the previous sound
    if (audioBase64 && sound) {
      (async () => {
        await sound.unloadAsync();
        setSound(null);
        setIsPlaying(false);
      })();
    }
  }, [audioBase64]);

  const togglePlayback = async () => {
    try {
      if (!audioBase64) {
        if (onError) onError('No audio available to play');
        return;
      }

      setIsLoading(true);

      if (sound) {
        const status = await sound.getStatusAsync();
        
        if (status.isLoaded) {
          if (isPlaying) {
            await sound.pauseAsync();
            setIsPlaying(false);
            if (onPlaybackStatusUpdate) onPlaybackStatusUpdate(false);
            setIsLoading(false);
            return;
          } else {
            await sound.playAsync();
            setIsPlaying(true);
            if (onPlaybackStatusUpdate) onPlaybackStatusUpdate(true);
            setIsLoading(false);
            return;
          }
        } else {
          // Unload if we have a sound object but it's not properly loaded
          await sound.unloadAsync();
          setSound(null);
        }
      }
      
      // Create and load new sound
      const audioUri = `data:audio/mpeg;base64,${audioBase64}`;
      
      const { sound: newSound } = await Audio.Sound.createAsync(
        { uri: audioUri },
        { shouldPlay: true, volume: 1.0 },
        (status) => {
          if (status.isLoaded) {
            setIsPlaying(status.isPlaying);
            if (onPlaybackStatusUpdate) onPlaybackStatusUpdate(status.isPlaying);
            
            if (status.didJustFinish) {
              setIsPlaying(false);
              if (onPlaybackStatusUpdate) onPlaybackStatusUpdate(false);
            }
          }
        }
      );
      
      setSound(newSound);
      setIsPlaying(true);
      if (onPlaybackStatusUpdate) onPlaybackStatusUpdate(true);
      
      // Explicitly start playback
      await newSound.playAsync();
      
    } catch (error) {
      console.error('Error playing audio:', error);
      if (onError) onError('Failed to play audio. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={styles.playButton}
        onPress={togglePlayback}
        disabled={isLoading || !audioBase64}
      >
        <Ionicons
          name={isPlaying ? 'pause' : 'play'}
          size={24}
          color="#fff"
        />
      </TouchableOpacity>
      <Text style={styles.playbackText}>
        {isLoading ? 'Loading...' : isPlaying ? 'Pause Narration' : 'Play Narration'}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 10
  },
  playButton: {
    backgroundColor: '#f4511e',
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12
  },
  playbackText: {
    fontSize: 16,
    color: '#333'
  }
});

export default AudioPlayer; 