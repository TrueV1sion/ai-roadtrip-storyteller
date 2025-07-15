import React from 'react';
import { View, StyleSheet, Animated } from 'react-native';
import { Text, Surface } from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { COLORS, SPACING } from '../../theme';

interface OfflineNoticeProps {
  style?: any;
}

const OfflineNotice: React.FC<OfflineNoticeProps> = ({ style }) => {
  const insets = useSafeAreaInsets();
  
  return (
    <Surface style={[
      styles.container,
      { top: insets.top + 60 }, // Position below the header
      style
    ]}>
      <MaterialIcons name="cloud-off" size={20} color={COLORS.warning} />
      <Text style={styles.text}>Offline Mode - Using Saved Data</Text>
    </Surface>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 70, // Default if safe area insets aren't available
    left: SPACING.medium,
    right: SPACING.medium,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    borderRadius: 4,
    flexDirection: 'row',
    alignItems: 'center',
    padding: SPACING.small,
    zIndex: 100,
  },
  text: {
    color: COLORS.warning,
    marginLeft: SPACING.small,
    fontSize: 14,
    fontWeight: 'bold',
  },
});

export default OfflineNotice; 