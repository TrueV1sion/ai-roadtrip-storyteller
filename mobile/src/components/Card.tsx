import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
  TextStyle,
  Platform,
  AccessibilityRole,
  useWindowDimensions,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { THEME } from '@/config';

interface CardAction {
  icon: string;
  onPress?: () => void;
  color?: string;
  accessibilityLabel?: string;
}

interface CardProps {
  title?: string;
  subtitle?: string;
  content?: string;
  actions?: CardAction[];
  onPress?: () => void;
  style?: ViewStyle;
  titleStyle?: TextStyle;
  subtitleStyle?: TextStyle;
  contentStyle?: TextStyle;
  elevation?: number;
  children?: React.ReactNode;
  accessible?: boolean;
  accessibilityRole?: AccessibilityRole;
  accessibilityLabel?: string;
  accessibilityHint?: string;
}

export function Card({
  title,
  subtitle,
  content,
  actions,
  onPress,
  style,
  titleStyle,
  subtitleStyle,
  contentStyle,
  elevation = 2,
  children,
  accessible = true,
  accessibilityRole = 'button',
  accessibilityLabel,
  accessibilityHint,
}: CardProps) {
  const { width } = useWindowDimensions();
  const isSmallScreen = width < 375;
  const CardContainer = onPress ? TouchableOpacity : View;

  // Platform-specific shadow styles
  const shadowStyles = Platform.select({
    ios: {
      shadowColor: '#000',
      shadowOffset: { width: 0, height: elevation },
      shadowOpacity: elevation * 0.05,
      shadowRadius: elevation * 2,
    },
    android: {
      elevation,
    },
    default: {},
  });

  return (
    <CardContainer
      style={[styles.container, shadowStyles, style]}
      onPress={onPress}
      activeOpacity={0.7}
      testID="card-container"
      accessible={accessible}
      accessibilityRole={accessibilityRole}
      accessibilityLabel={accessibilityLabel || title}
      accessibilityHint={accessibilityHint || (onPress ? 'Double tap to interact' : undefined)}
    >
      {(title || subtitle) && (
        <View style={styles.header} testID="card-header">
          {title && (
            <Text 
              style={[
                styles.title,
                isSmallScreen && styles.smallScreenTitle,
                titleStyle,
              ]} 
              numberOfLines={2}
              testID="card-title"
              accessibilityRole="header"
            >
              {String(title)}
            </Text>
          )}
          {subtitle && (
            <Text 
              style={[
                styles.subtitle,
                isSmallScreen && styles.smallScreenSubtitle,
                subtitleStyle,
              ]} 
              numberOfLines={1}
              testID="card-subtitle"
            >
              {String(subtitle)}
            </Text>
          )}
        </View>
      )}
      {content && (
        <Text 
          style={[
            styles.content,
            isSmallScreen && styles.smallScreenContent,
            contentStyle,
          ]} 
          numberOfLines={3}
          testID="card-content"
        >
          {String(content)}
        </Text>
      )}
      {children && (
        <View testID="card-children">
          {children}
        </View>
      )}
      {actions && actions.length > 0 && (
        <View style={styles.actions} testID="card-actions">
          {actions.map((action, index) => (
            <TouchableOpacity
              key={index}
              style={styles.action}
              onPress={action.onPress}
              testID={`card-action-${index}`}
              accessible={true}
              accessibilityRole="button"
              accessibilityLabel={action.accessibilityLabel || `${action.icon} action`}
            >
              <Icon
                name={action.icon}
                size={24}
                color={action.color || THEME.colors.primary}
                testID={`card-action-icon-${index}`}
              />
            </TouchableOpacity>
          ))}
        </View>
      )}
    </CardContainer>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    marginVertical: THEME.spacing.sm,
  },
  header: {
    padding: THEME.spacing.md,
    paddingBottom: THEME.spacing.sm,
  },
  title: {
    ...THEME.typography.h3,
    color: THEME.colors.text,
    marginBottom: THEME.spacing.xs,
  },
  subtitle: {
    fontSize: 14,
    color: '#757575',
  },
  content: {
    padding: THEME.spacing.md,
    paddingTop: 0,
    color: THEME.colors.text,
    lineHeight: 22,
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    padding: THEME.spacing.sm,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  action: {
    padding: THEME.spacing.sm,
    marginLeft: THEME.spacing.sm,
  },
  // Responsive styles
  smallScreenTitle: {
    fontSize: 18,
    lineHeight: 24,
  },
  smallScreenSubtitle: {
    fontSize: 12,
    lineHeight: 16,
  },
  smallScreenContent: {
    fontSize: 14,
    lineHeight: 20,
  },
}); 