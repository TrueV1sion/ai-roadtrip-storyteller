import React from 'react';
import {
  SafeAreaView,
  StyleSheet,
  ViewStyle,
  StatusBar,
  Platform,
} from 'react-native';
import { THEME } from '@/config';

interface SafeAreaProps {
  children: React.ReactNode;
  style?: ViewStyle;
  backgroundColor?: string;
  edges?: ('top' | 'right' | 'bottom' | 'left')[];
}

export function SafeArea({
  children,
  style,
  backgroundColor = THEME.colors.background,
  edges,
}: SafeAreaProps) {
  return (
    <SafeAreaView
      style={[
        styles.container,
        { backgroundColor },
        style,
      ]}
      edges={edges}
    >
      <StatusBar
        backgroundColor={backgroundColor}
        barStyle={
          backgroundColor === '#ffffff' ? 'dark-content' : 'light-content'
        }
      />
      {children}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0,
  },
}); 