import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { BlurView } from 'expo-blur';
import { MaterialIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

import { useTheme } from '../hooks/useTheme';
import { formatDistance, formatDuration } from '../utils/formatters';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface NavigationOverlayProps {
  currentStep: any;
  nextStep: any;
  distanceToManeuver: number;
  timeToManeuver: number;
  currentSpeed: number;
}

export const NavigationOverlay: React.FC<NavigationOverlayProps> = ({
  currentStep,
  nextStep,
  distanceToManeuver,
  timeToManeuver,
  currentSpeed
}) => {
  const { theme } = useTheme();

  const getManeuverIcon = (maneuver: string) => {
    const iconMap: { [key: string]: string } = {
      'turn-left': 'turn-left',
      'turn-right': 'turn-right',
      'turn-sharp-left': 'turn-sharp-left',
      'turn-sharp-right': 'turn-sharp-right',
      'turn-slight-left': 'turn-slight-left',
      'turn-slight-right': 'turn-slight-right',
      'straight': 'straight',
      'merge': 'merge-type',
      'ramp-left': 'trending-down',
      'ramp-right': 'trending-up',
      'fork-left': 'call-split',
      'fork-right': 'call-split',
      'roundabout': 'loop',
      'uturn': 'u-turn-left',
      'exit': 'exit-to-app',
      'arrive': 'place'
    };

    return iconMap[maneuver] || 'navigation';
  };

  const stripHtml = (html: string) => {
    return html.replace(/<[^>]*>/g, '');
  };

  return (
    <>
      {/* Top instruction panel */}
      <View style={styles.topPanel}>
        <BlurView intensity={90} style={styles.blurContainer}>
          <LinearGradient
            colors={[theme.colors.background + 'ee', theme.colors.background + 'cc']}
            style={styles.gradientOverlay}
          >
            <View style={styles.instructionContainer}>
              {/* Maneuver icon and distance */}
              <View style={styles.maneuverSection}>
                <View style={[styles.maneuverIconContainer, { backgroundColor: theme.colors.primary }]}>
                  <MaterialIcons
                    name={getManeuverIcon(currentStep?.maneuver || 'straight')}
                    size={48}
                    color="white"
                  />
                </View>
                <View style={styles.distanceInfo}>
                  <Text style={[styles.distanceText, { color: theme.colors.text }]}>
                    {formatDistance(distanceToManeuver)}
                  </Text>
                  <Text style={[styles.timeText, { color: theme.colors.textSecondary }]}>
                    {formatDuration(timeToManeuver)}
                  </Text>
                </View>
              </View>

              {/* Current instruction */}
              <View style={styles.instructionTextContainer}>
                <Text style={[styles.instructionText, { color: theme.colors.text }]} numberOfLines={2}>
                  {currentStep ? stripHtml(currentStep.html_instructions) : 'Continue on route'}
                </Text>
                {nextStep && (
                  <View style={styles.nextStepContainer}>
                    <MaterialIcons
                      name={getManeuverIcon(nextStep.maneuver)}
                      size={16}
                      color={theme.colors.textSecondary}
                    />
                    <Text style={[styles.nextStepText, { color: theme.colors.textSecondary }]}>
                      Then: {stripHtml(nextStep.html_instructions)}
                    </Text>
                  </View>
                )}
              </View>
            </View>
          </LinearGradient>
        </BlurView>
      </View>

      {/* Bottom status bar */}
      <View style={styles.bottomBar}>
        <BlurView intensity={80} style={styles.blurContainer}>
          <View style={[styles.statusBar, { backgroundColor: theme.colors.background + 'dd' }]}>
            {/* Current speed */}
            <View style={styles.statusItem}>
              <MaterialIcons name="speed" size={20} color={theme.colors.textSecondary} />
              <Text style={[styles.statusValue, { color: theme.colors.text }]}>
                {Math.round(currentSpeed * 0.621371)} mph
              </Text>
            </View>

            {/* ETA */}
            <View style={styles.statusItem}>
              <MaterialIcons name="access-time" size={20} color={theme.colors.textSecondary} />
              <Text style={[styles.statusValue, { color: theme.colors.text }]}>
                {new Date(Date.now() + timeToManeuver * 1000).toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </Text>
            </View>

            {/* Distance remaining */}
            <View style={styles.statusItem}>
              <MaterialIcons name="route" size={20} color={theme.colors.textSecondary} />
              <Text style={[styles.statusValue, { color: theme.colors.text }]}>
                {formatDistance(distanceToManeuver)} left
              </Text>
            </View>
          </View>
        </BlurView>
      </View>
    </>
  );
};

const styles = StyleSheet.create({
  topPanel: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    paddingTop: 50, // Safe area
  },
  blurContainer: {
    overflow: 'hidden',
  },
  gradientOverlay: {
    padding: 20,
  },
  instructionContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  maneuverSection: {
    alignItems: 'center',
    marginRight: 20,
  },
  maneuverIconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  distanceInfo: {
    alignItems: 'center',
  },
  distanceText: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  timeText: {
    fontSize: 14,
    marginTop: 4,
  },
  instructionTextContainer: {
    flex: 1,
    justifyContent: 'center',
  },
  instructionText: {
    fontSize: 20,
    fontWeight: '600',
    lineHeight: 28,
  },
  nextStepContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
  },
  nextStepText: {
    fontSize: 14,
    marginLeft: 8,
    flex: 1,
  },
  bottomBar: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
  },
  statusBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 12,
    paddingBottom: 34, // Safe area
  },
  statusItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusValue: {
    fontSize: 16,
    fontWeight: '500',
  },
});