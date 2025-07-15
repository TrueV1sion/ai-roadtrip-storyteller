/**
 * Spatial Audio Visualizer Component
 * Provides visual feedback for the immersive audio experience
 */

import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  StyleSheet,
  Animated,
  Dimensions,
  Text,
  TouchableOpacity
} from 'react-native';
import Svg, { Circle, Path, G, Defs, RadialGradient, Stop } from 'react-native-svg';
import { audioManager, AudioCategory } from '../../services/audio/audioManager';
import { BlurView } from 'expo-blur';

interface AudioSource {
  id: string;
  category: AudioCategory;
  position: { x: number; y: number; z: number };
  volume: number;
  isActive: boolean;
}

const { width: screenWidth } = Dimensions.get('window');
const visualizerSize = screenWidth * 0.8;

const SpatialAudioVisualizer: React.FC = () => {
  const [audioSources, setAudioSources] = useState<AudioSource[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Subscribe to audio state changes
    const updateAudioState = () => {
      const state = audioManager.getAudioState();
      const sources: AudioSource[] = state.activeStreams.map(stream => ({
        id: stream.id,
        category: stream.category,
        position: getPositionForCategory(stream.category),
        volume: stream.volume,
        isActive: stream.isPlaying
      }));
      setAudioSources(sources);
    };

    audioManager.on('streamStarted', updateAudioState);
    audioManager.on('streamStopped', updateAudioState);
    audioManager.on('playbackStatusUpdate', updateAudioState);

    // Initial state
    updateAudioState();

    // Ambient animation
    const pulseAnimation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.1,
          duration: 2000,
          useNativeDriver: true
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 2000,
          useNativeDriver: true
        })
      ])
    );
    pulseAnimation.start();

    // Rotation animation for ambient effects
    const rotateAnimation = Animated.loop(
      Animated.timing(rotateAnim, {
        toValue: 1,
        duration: 30000,
        useNativeDriver: true
      })
    );
    rotateAnimation.start();

    return () => {
      audioManager.off('streamStarted', updateAudioState);
      audioManager.off('streamStopped', updateAudioState);
      audioManager.off('playbackStatusUpdate', updateAudioState);
      pulseAnimation.stop();
      rotateAnimation.stop();
    };
  }, []);

  const getPositionForCategory = (category: AudioCategory): { x: number; y: number; z: number } => {
    const positions = {
      [AudioCategory.VOICE]: { x: 0, y: 0, z: 0.8 },
      [AudioCategory.NAVIGATION]: { x: 0, y: 0.3, z: 0.9 },
      [AudioCategory.MUSIC]: { x: 0, y: -0.5, z: -0.5 },
      [AudioCategory.AMBIENT]: { x: -0.7, y: 0, z: 0 },
      [AudioCategory.EFFECT]: { x: 0.7, y: 0, z: 0 }
    };
    return positions[category] || { x: 0, y: 0, z: 0 };
  };

  const getCategoryColor = (category: AudioCategory): string => {
    const colors = {
      [AudioCategory.VOICE]: '#4CAF50',
      [AudioCategory.NAVIGATION]: '#2196F3',
      [AudioCategory.MUSIC]: '#9C27B0',
      [AudioCategory.AMBIENT]: '#FF9800',
      [AudioCategory.EFFECT]: '#00BCD4'
    };
    return colors[category] || '#757575';
  };

  const getCategoryIcon = (category: AudioCategory): string => {
    const icons = {
      [AudioCategory.VOICE]: '🎙️',
      [AudioCategory.NAVIGATION]: '🧭',
      [AudioCategory.MUSIC]: '🎵',
      [AudioCategory.AMBIENT]: '🌿',
      [AudioCategory.EFFECT]: '✨'
    };
    return icons[category] || '🔊';
  };

  const renderAudioSource = (source: AudioSource) => {
    // Convert 3D position to 2D for visualization
    const centerX = visualizerSize / 2;
    const centerY = visualizerSize / 2;
    const x = centerX + (source.position.x * centerX * 0.7);
    const y = centerY - (source.position.y * centerY * 0.7);
    const scale = 0.5 + (source.position.z + 1) * 0.25; // Z affects size

    return (
      <G key={source.id}>
        {/* Ripple effect for active sources */}
        {source.isActive && (
          <AnimatedCircle
            cx={x}
            cy={y}
            r={20 * scale}
            fill={getCategoryColor(source.category)}
            opacity={0.3}
            style={{
              transform: [{ scale: pulseAnim }]
            }}
          />
        )}
        
        {/* Source circle */}
        <Circle
          cx={x}
          cy={y}
          r={12 * scale}
          fill={getCategoryColor(source.category)}
          opacity={source.volume}
        />
        
        {/* Category icon */}
        <SvgText
          x={x}
          y={y + 4}
          fontSize={16 * scale}
          textAnchor="middle"
          fill="white"
        >
          {getCategoryIcon(source.category)}
        </SvgText>
      </G>
    );
  };

  const renderSpatialGrid = () => {
    const gridLines = [];
    const gridSize = 50;
    const gridCount = Math.floor(visualizerSize / gridSize);

    for (let i = 0; i <= gridCount; i++) {
      const pos = i * gridSize;
      gridLines.push(
        <Path
          key={`h${i}`}
          d={`M 0 ${pos} L ${visualizerSize} ${pos}`}
          stroke="#333"
          strokeWidth="0.5"
          opacity="0.3"
        />
      );
      gridLines.push(
        <Path
          key={`v${i}`}
          d={`M ${pos} 0 L ${pos} ${visualizerSize}`}
          stroke="#333"
          strokeWidth="0.5"
          opacity="0.3"
        />
      );
    }
    return gridLines;
  };

  const AnimatedCircle = Animated.createAnimatedComponent(Circle);
  const AnimatedG = Animated.createAnimatedComponent(G);
  const SvgText = Text as any; // Workaround for SVG Text

  return (
    <TouchableOpacity
      style={[styles.container, isExpanded && styles.expandedContainer]}
      onPress={() => setIsExpanded(!isExpanded)}
      activeOpacity={0.9}
    >
      <BlurView intensity={80} style={styles.blurContainer}>
        {isExpanded ? (
          <View style={styles.expandedView}>
            <Text style={styles.title}>Spatial Audio</Text>
            
            <Svg width={visualizerSize} height={visualizerSize} style={styles.visualizer}>
              <Defs>
                <RadialGradient id="bgGradient" cx="50%" cy="50%">
                  <Stop offset="0%" stopColor="#000" stopOpacity="0.8" />
                  <Stop offset="100%" stopColor="#000" stopOpacity="0.3" />
                </RadialGradient>
              </Defs>
              
              {/* Background */}
              <Circle
                cx={visualizerSize / 2}
                cy={visualizerSize / 2}
                r={visualizerSize / 2}
                fill="url(#bgGradient)"
              />
              
              {/* Spatial grid */}
              <AnimatedG
                style={{
                  transform: [{
                    rotate: rotateAnim.interpolate({
                      inputRange: [0, 1],
                      outputRange: ['0deg', '360deg']
                    })
                  }]
                }}
              >
                {renderSpatialGrid()}
              </AnimatedG>
              
              {/* Listener position (center) */}
              <Circle
                cx={visualizerSize / 2}
                cy={visualizerSize / 2}
                r={8}
                fill="white"
              />
              
              {/* Audio sources */}
              {audioSources.map(renderAudioSource)}
            </Svg>
            
            {/* Legend */}
            <View style={styles.legend}>
              {Object.values(AudioCategory).map(category => (
                <View key={category} style={styles.legendItem}>
                  <View
                    style={[
                      styles.legendDot,
                      { backgroundColor: getCategoryColor(category) }
                    ]}
                  />
                  <Text style={styles.legendText}>{category}</Text>
                </View>
              ))}
            </View>
          </View>
        ) : (
          <View style={styles.compactView}>
            <View style={styles.audioIndicator}>
              {audioSources.filter(s => s.isActive).map((source, index) => (
                <Animated.View
                  key={source.id}
                  style={[
                    styles.compactDot,
                    {
                      backgroundColor: getCategoryColor(source.category),
                      transform: [{ scale: pulseAnim }],
                      left: 20 + index * 15
                    }
                  ]}
                />
              ))}
            </View>
            <Text style={styles.compactText}>
              {audioSources.filter(s => s.isActive).length} active
            </Text>
          </View>
        )}
      </BlurView>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 100,
    right: 20,
    borderRadius: 25,
    overflow: 'hidden',
  },
  expandedContainer: {
    top: 80,
    right: 20,
    left: 20,
  },
  blurContainer: {
    padding: 15,
  },
  expandedView: {
    alignItems: 'center',
  },
  compactView: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 5,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 10,
  },
  visualizer: {
    marginVertical: 10,
  },
  legend: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginTop: 10,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 10,
    marginVertical: 5,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 5,
  },
  legendText: {
    color: 'white',
    fontSize: 12,
  },
  audioIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 30,
    width: 80,
  },
  compactDot: {
    position: 'absolute',
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  compactText: {
    color: 'white',
    fontSize: 12,
    marginLeft: 10,
  },
});

export default SpatialAudioVisualizer;