import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ViewStyle,
  TextStyle,
  StatusBar,
  Platform,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { THEME } from '@/config';

interface HeaderAction {
  icon: string;
  onPress: () => void;
  color?: string;
}

interface HeaderProps {
  title: string;
  showBack?: boolean;
  actions?: HeaderAction[];
  style?: ViewStyle;
  titleStyle?: TextStyle;
  backgroundColor?: string;
  textColor?: string;
  elevation?: number;
}

export function Header({
  title,
  showBack = true,
  actions = [],
  style,
  titleStyle,
  backgroundColor = THEME.colors.primary,
  textColor = '#ffffff',
  elevation = 4,
}: HeaderProps) {
  const navigation = useNavigation();

  return (
    <>
      <StatusBar
        backgroundColor={backgroundColor}
        barStyle={
          backgroundColor === '#ffffff' ? 'dark-content' : 'light-content'
        }
      />
      <View
        testID="header-container"
        style={[
          styles.container,
          {
            backgroundColor,
            elevation,
            shadowOpacity: elevation * 0.05,
            shadowRadius: elevation * 2,
          },
          style,
        ]}
      >
        <View style={styles.leftContainer}>
          {showBack && (
            <TouchableOpacity
              testID="back-button"
              style={styles.backButton}
              onPress={() => navigation.goBack()}
            >
              <Icon name="arrow-left" size={24} color={textColor} />
            </TouchableOpacity>
          )}
          <Text
            style={[
              styles.title,
              { color: textColor },
              titleStyle,
            ]}
            numberOfLines={1}
          >
            {title}
          </Text>
        </View>
        {actions.length > 0 && (
          <View style={styles.actions}>
            {actions.map((action, index) => (
              <TouchableOpacity
                key={index}
                testID="action-button"
                style={styles.action}
                onPress={action.onPress}
              >
                <Icon
                  testID="action-icon"
                  name={action.icon}
                  size={24}
                  color={action.color || textColor}
                />
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: Platform.OS === 'ios' ? 44 : StatusBar.currentHeight,
    paddingHorizontal: THEME.spacing.md,
    paddingBottom: THEME.spacing.md,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
  },
  leftContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  backButton: {
    marginRight: THEME.spacing.sm,
    padding: THEME.spacing.xs,
  },
  title: {
    ...THEME.typography.h2,
    flex: 1,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  action: {
    padding: THEME.spacing.sm,
    marginLeft: THEME.spacing.sm,
  },
}); 