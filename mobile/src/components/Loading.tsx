import React from 'react';
import {
  View,
  ActivityIndicator,
  Text,
  StyleSheet,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { THEME } from '@/config';

interface LoadingProps {
  size?: 'small' | 'large';
  color?: string;
  message?: string;
  fullScreen?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  backgroundColor?: string;
}

export function Loading({
  size = 'large',
  color = THEME.colors.primary,
  message,
  fullScreen = false,
  style,
  textStyle,
  backgroundColor = 'rgba(255, 255, 255, 0.9)',
}: LoadingProps) {
  if (!fullScreen) {
    return (
      <View style={[styles.container, style]}>
        <ActivityIndicator size={size} color={color} />
        {message && (
          <Text style={[styles.message, textStyle]}>{message}</Text>
        )}
      </View>
    );
  }

  return (
    <View
      style={[
        styles.fullScreen,
        { backgroundColor },
        style,
      ]}
    >
      <View style={styles.content}>
        <ActivityIndicator size={size} color={color} />
        {message && (
          <Text style={[styles.message, textStyle]}>{message}</Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: THEME.spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fullScreen: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 999,
  },
  content: {
    padding: THEME.spacing.xl,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  message: {
    marginTop: THEME.spacing.md,
    color: THEME.colors.text,
    fontSize: 16,
    textAlign: 'center',
  },
}); 