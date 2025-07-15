import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

import { apiManager } from '../services/api/apiManager';

interface NowPlayingWidgetProps {
  onPress?: () => void;
  style?: any;
}

export const NowPlayingWidget: React.FC<NowPlayingWidgetProps> = ({
  onPress,
  style,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTrack, setCurrentTrack] = useState<any>(null);
  const [musicContext, setMusicContext] = useState<string>('');
  const animatedValue = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    checkPlayback();
    const interval = setInterval(checkPlayback, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Pulse animation for playing state
    if (isPlaying) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(animatedValue, {
            toValue: 1,
            duration: 1500,
            useNativeDriver: true,
          }),
          Animated.timing(animatedValue, {
            toValue: 0,
            duration: 1500,
            useNativeDriver: true,
          }),
        ])
      ).start();
    } else {
      animatedValue.setValue(0);
    }
  }, [isPlaying]);

  const checkPlayback = async () => {
    try {
      const response = await apiManager.get('/spotify/playback/current');
      const data = response.data;
      
      if (data.is_playing && data.track) {
        setIsPlaying(true);
        setCurrentTrack(data.track);
        
        // Check if music is location or mood based
        const context = await apiManager.get('/music/context');
        if (context.data.location) {
          setMusicContext(`Music for ${context.data.location}`);
        } else if (context.data.mood) {
          setMusicContext(`${context.data.mood} vibes`);
        }
      } else {
        setIsPlaying(false);
        setCurrentTrack(null);
      }
    } catch (error) {
      // Silently fail - widget is non-critical
    }
  };

  if (!currentTrack) {
    return null; // Don't show widget if nothing is playing
  }

  const pulseScale = animatedValue.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 1.05],
  });

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.9}>
      <Animated.View
        style={[
          styles.container,
          style,
          {
            transform: [{ scale: pulseScale }],
          },
        ]}
      >
        <LinearGradient
          colors={['#1DB954', '#1ED760']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.gradient}
        >
          <View style={styles.content}>
            <View style={styles.iconContainer}>
              <Ionicons
                name={isPlaying ? 'musical-notes' : 'pause'}
                size={24}
                color="white"
              />
              {isPlaying && (
                <View style={styles.playingIndicator}>
                  <Animated.View
                    style={[
                      styles.bar,
                      {
                        transform: [
                          {
                            scaleY: animatedValue.interpolate({
                              inputRange: [0, 1],
                              outputRange: [0.3, 1],
                            }),
                          },
                        ],
                      },
                    ]}
                  />
                  <Animated.View
                    style={[
                      styles.bar,
                      {
                        transform: [
                          {
                            scaleY: animatedValue.interpolate({
                              inputRange: [0, 1],
                              outputRange: [1, 0.3],
                            }),
                          },
                        ],
                      },
                    ]}
                  />
                  <Animated.View
                    style={[
                      styles.bar,
                      {
                        transform: [
                          {
                            scaleY: animatedValue.interpolate({
                              inputRange: [0, 1],
                              outputRange: [0.5, 1],
                            }),
                          },
                        ],
                      },
                    ]}
                  />
                </View>
              )}
            </View>

            <View style={styles.textContainer}>
              <Text style={styles.trackName} numberOfLines={1}>
                {currentTrack.name}
              </Text>
              <Text style={styles.artistName} numberOfLines={1}>
                {currentTrack.artist}
              </Text>
              {musicContext && (
                <Text style={styles.contextText} numberOfLines={1}>
                  {musicContext}
                </Text>
              )}
            </View>

            <Ionicons name="chevron-forward" size={20} color="white" />
          </View>
        </LinearGradient>
      </Animated.View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 16,
    marginVertical: 8,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 5,
  },
  gradient: {
    borderRadius: 16,
    overflow: 'hidden',
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  iconContainer: {
    marginRight: 12,
    position: 'relative',
  },
  playingIndicator: {
    position: 'absolute',
    bottom: -8,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'flex-end',
    height: 12,
  },
  bar: {
    width: 3,
    height: 8,
    backgroundColor: 'white',
    marginHorizontal: 1,
    borderRadius: 1.5,
  },
  textContainer: {
    flex: 1,
    marginRight: 12,
  },
  trackName: {
    fontSize: 16,
    fontWeight: '600',
    color: 'white',
  },
  artistName: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginTop: 2,
  },
  contextText: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.6)',
    marginTop: 2,
    fontStyle: 'italic',
  },
});