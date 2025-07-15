import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated, ViewStyle } from 'react-native';
import { COLORS } from '../../theme';

interface MusicVisualizerProps {
  isPlaying: boolean;
  style?: ViewStyle;
}

const BAR_COUNT = 32;
const MAX_BAR_HEIGHT = 50;
const MIN_BAR_HEIGHT = 3;

export const MusicVisualizer: React.FC<MusicVisualizerProps> = ({
  isPlaying,
  style,
}) => {
  // Create animated values for each bar
  const barHeights = useRef(
    Array.from({ length: BAR_COUNT }, () =>
      new Animated.Value(MIN_BAR_HEIGHT)
    )
  ).current;

  // Animate bars when playing
  useEffect(() => {
    if (isPlaying) {
      // Animate each bar with random heights and durations
      const animations = barHeights.map(height =>
        Animated.sequence([
          Animated.timing(height, {
            toValue: Math.random() * MAX_BAR_HEIGHT + MIN_BAR_HEIGHT,
            duration: Math.random() * 1000 + 500,
            useNativeDriver: false,
          }),
          Animated.timing(height, {
            toValue: MIN_BAR_HEIGHT,
            duration: Math.random() * 1000 + 500,
            useNativeDriver: false,
          }),
        ])
      );

      // Loop animations
      const loop = Animated.parallel(animations, { stopTogether: false });
      const loopAnimation = Animated.loop(loop);
      loopAnimation.start();

      return () => {
        loopAnimation.stop();
        // Reset bars to minimum height
        barHeights.forEach(height => height.setValue(MIN_BAR_HEIGHT));
      };
    }
  }, [isPlaying, barHeights]);

  return (
    <View style={[styles.container, style]}>
      {barHeights.map((height, index) => (
        <Animated.View
          key={index}
          style={[
            styles.bar,
            {
              height,
              backgroundColor: getBarColor(index, BAR_COUNT),
            },
          ]}
        />
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    height: MAX_BAR_HEIGHT,
  },
  bar: {
    width: 4,
    borderRadius: 2,
  },
});

// Helper function to generate gradient colors for bars
const getBarColor = (index: number, total: number): string => {
  const hue = (index / total) * 60 + 200; // Blue to purple gradient
  return `hsl(${hue}, 70%, 50%)`;
};

export default MusicVisualizer; 