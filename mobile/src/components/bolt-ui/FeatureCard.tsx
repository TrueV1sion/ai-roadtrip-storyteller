/**
 * FeatureCard Component
 * Clean feature cards from Bolt's landing page
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ViewStyle,
} from 'react-native';
import Animated, {
  FadeInDown,
  FadeInUp,
} from 'react-native-reanimated';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { unifiedTheme } from '../../theme/unified';

interface FeatureCardProps {
  icon: string;
  iconColor?: string;
  title: string;
  description: string;
  delay?: number;
  style?: ViewStyle;
}

export const FeatureCard: React.FC<FeatureCardProps> = ({
  icon,
  iconColor = unifiedTheme.colors.primary[600],
  title,
  description,
  delay = 0,
  style,
}) => {
  return (
    <Animated.View
      entering={FadeInUp.delay(delay).springify()}
      style={[styles.card, style]}
    >
      <View style={[styles.iconContainer, { backgroundColor: unifiedTheme.utils.withOpacity(iconColor, 0.1) }]}>
        <MaterialCommunityIcons
          name={icon as any}
          size={28}
          color={iconColor}
        />
      </View>
      
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.description}>{description}</Text>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: unifiedTheme.colors.surface.card,
    borderRadius: unifiedTheme.borderRadius.xl,
    padding: unifiedTheme.spacing[6],
    alignItems: 'center',
    ...unifiedTheme.shadows.base,
    borderWidth: 1,
    borderColor: unifiedTheme.colors.surface.border,
  },
  iconContainer: {
    width: 56,
    height: 56,
    borderRadius: unifiedTheme.borderRadius.lg,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: unifiedTheme.spacing[4],
  },
  title: {
    ...unifiedTheme.typography.h6,
    color: unifiedTheme.colors.neutral[900],
    textAlign: 'center',
    marginBottom: unifiedTheme.spacing[2],
  },
  description: {
    ...unifiedTheme.typography.bodySmall,
    color: unifiedTheme.colors.neutral[600],
    textAlign: 'center',
    lineHeight: unifiedTheme.lineHeights.relaxed * unifiedTheme.fontSizes.sm,
  },
});
