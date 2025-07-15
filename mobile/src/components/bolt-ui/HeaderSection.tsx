/**
 * HeaderSection Component
 * Beautiful header sections from Bolt's design
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ViewStyle,
} from 'react-native';
import Animated, {
  FadeIn,
} from 'react-native-reanimated';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { unifiedTheme } from '../../theme/unified';

interface HeaderSectionProps {
  title: string;
  subtitle?: string;
  icon?: string;
  iconColor?: string;
  centered?: boolean;
  style?: ViewStyle;
  children?: React.ReactNode;
}

export const HeaderSection: React.FC<HeaderSectionProps> = ({
  title,
  subtitle,
  icon,
  iconColor = unifiedTheme.colors.primary[600],
  centered = false,
  style,
  children,
}) => {
  return (
    <Animated.View
      entering={FadeIn.duration(600)}
      style={[styles.container, centered && styles.centered, style]}
    >
      {icon && (
        <View style={styles.iconWrapper}>
          <MaterialCommunityIcons
            name={icon as any}
            size={48}
            color={iconColor}
          />
        </View>
      )}
      
      <View style={[styles.textContainer, centered && styles.textCentered]}>
        <Text style={[styles.title, centered && styles.titleCentered]}>
          {title}
        </Text>
        {subtitle && (
          <Text style={[styles.subtitle, centered && styles.subtitleCentered]}>
            {subtitle}
          </Text>
        )}
      </View>
      
      {children}
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: unifiedTheme.layout.screenPadding.horizontal,
    paddingVertical: unifiedTheme.spacing[8],
  },
  centered: {
    alignItems: 'center',
  },
  iconWrapper: {
    marginBottom: unifiedTheme.spacing[4],
  },
  textContainer: {
    gap: unifiedTheme.spacing[3],
  },
  textCentered: {
    alignItems: 'center',
  },
  title: {
    ...unifiedTheme.typography.h2,
    color: unifiedTheme.colors.neutral[900],
  },
  titleCentered: {
    textAlign: 'center',
  },
  subtitle: {
    ...unifiedTheme.typography.bodyLarge,
    color: unifiedTheme.colors.neutral[600],
  },
  subtitleCentered: {
    textAlign: 'center',
  },
});
