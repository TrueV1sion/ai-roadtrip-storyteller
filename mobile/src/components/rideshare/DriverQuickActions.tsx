import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { theme } from '../../theme';

const { width } = Dimensions.get('window');

interface QuickAction {
  id: string;
  label: string;
  icon: string;
  onPress: () => void;
}

interface DriverQuickActionsProps {
  actions: QuickAction[];
  columns?: number;
}

export const DriverQuickActions: React.FC<DriverQuickActionsProps> = ({
  actions,
  columns = 2,
}) => {
  const buttonSize = (width - (theme.spacing.md * (columns + 1))) / columns;

  const getIconComponent = (iconName: string, size: number = 40) => {
    const iconProps = { size, color: theme.colors.primary };
    
    switch (iconName) {
      case 'gas-pump':
        return <MaterialCommunityIcons name="gas-station" {...iconProps} />;
      case 'food':
        return <Ionicons name="fast-food" {...iconProps} />;
      case 'coffee':
        return <Ionicons name="cafe" {...iconProps} />;
      case 'location':
        return <Ionicons name="location" {...iconProps} />;
      case 'trending-up':
        return <Ionicons name="trending-up" {...iconProps} />;
      case 'time':
        return <Ionicons name="time" {...iconProps} />;
      case 'cash':
        return <Ionicons name="cash" {...iconProps} />;
      case 'car':
        return <Ionicons name="car" {...iconProps} />;
      default:
        return <Ionicons name="apps" {...iconProps} />;
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.grid}>
        {actions.map((action) => (
          <TouchableOpacity
            key={action.id}
            style={[
              styles.actionButton,
              { width: buttonSize, height: buttonSize }
            ]}
            onPress={action.onPress}
            activeOpacity={0.8}
          >
            <View style={styles.iconContainer}>
              {getIconComponent(action.icon)}
            </View>
            <Text style={styles.label} numberOfLines={2}>
              {action.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: theme.spacing.md,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  actionButton: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  iconContainer: {
    marginBottom: theme.spacing.sm,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.text,
    textAlign: 'center',
  },
});