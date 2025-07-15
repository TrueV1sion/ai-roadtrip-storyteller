/**
 * TabBar Component
 * Beautiful tab bar from Bolt's design
 * Adapted for react-navigation
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Platform,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  interpolate,
} from 'react-native-reanimated';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { unifiedTheme } from '../../theme/unified';

export interface TabConfig {
  name: string;
  label: string;
  icon: string;
  activeIcon?: string;
}

interface TabBarProps {
  state: any; // Navigation state
  descriptors: any;
  navigation: any;
  tabs?: TabConfig[];
}

const defaultTabs: TabConfig[] = [
  { name: 'Home', label: 'Home', icon: 'home-outline', activeIcon: 'home' },
  { name: 'Search', label: 'Search', icon: 'magnify' },
  { name: 'Storyteller', label: 'Story', icon: 'microphone-outline', activeIcon: 'microphone' },
  { name: 'Navigation', label: 'Navigate', icon: 'navigation-outline', activeIcon: 'navigation' },
  { name: 'Profile', label: 'Profile', icon: 'account-outline', activeIcon: 'account' },
];

export const TabBar: React.FC<TabBarProps> = ({
  state,
  descriptors,
  navigation,
  tabs = defaultTabs,
}) => {
  const insets = useSafeAreaInsets();
  const indicatorPosition = useSharedValue(0);

  React.useEffect(() => {
    const tabWidth = 100 / tabs.length;
    indicatorPosition.value = withSpring(
      state.index * tabWidth + tabWidth / 2,
      unifiedTheme.animations.spring.noWobble
    );
  }, [state.index, tabs.length]);

  const indicatorStyle = useAnimatedStyle(() => ({
    left: `${indicatorPosition.value}%`,
  }));

  return (
    <View style={[styles.container, { paddingBottom: insets.bottom }]}>
      {/* Active Indicator */}
      <Animated.View style={[styles.indicator, indicatorStyle]} />
      
      {/* Tabs */}
      <View style={styles.tabs}>
        {state.routes.map((route: any, index: number) => {
          const { options } = descriptors[route.key];
          const isFocused = state.index === index;
          const tab = tabs[index] || defaultTabs[index];
          
          const onPress = () => {
            const event = navigation.emit({
              type: 'tabPress',
              target: route.key,
              canPreventDefault: true,
            });

            if (!isFocused && !event.defaultPrevented) {
              navigation.navigate(route.name);
            }
          };

          const onLongPress = () => {
            navigation.emit({
              type: 'tabLongPress',
              target: route.key,
            });
          };

          return (
            <TabItem
              key={route.key}
              tab={tab}
              isFocused={isFocused}
              onPress={onPress}
              onLongPress={onLongPress}
            />
          );
        })}
      </View>
    </View>
  );
};

interface TabItemProps {
  tab: TabConfig;
  isFocused: boolean;
  onPress: () => void;
  onLongPress: () => void;
}

const TabItem: React.FC<TabItemProps> = ({
  tab,
  isFocused,
  onPress,
  onLongPress,
}) => {
  const scale = useSharedValue(1);
  const opacity = useSharedValue(isFocused ? 1 : 0.6);

  React.useEffect(() => {
    scale.value = withSpring(isFocused ? 1.1 : 1, unifiedTheme.animations.spring.gentle);
    opacity.value = withSpring(isFocused ? 1 : 0.6);
  }, [isFocused]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: opacity.value,
  }));

  const iconName = isFocused && tab.activeIcon ? tab.activeIcon : tab.icon;
  const iconColor = isFocused 
    ? unifiedTheme.colors.primary[600] 
    : unifiedTheme.colors.neutral[400];

  return (
    <TouchableOpacity
      style={styles.tab}
      onPress={onPress}
      onLongPress={onLongPress}
      activeOpacity={0.7}
    >
      <Animated.View style={[styles.tabContent, animatedStyle]}>
        <MaterialCommunityIcons
          name={iconName as any}
          size={24}
          color={iconColor}
        />
        <Text style={[
          styles.label,
          { color: iconColor }
        ]}>
          {tab.label}
        </Text>
      </Animated.View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: unifiedTheme.colors.surface.background,
    borderTopWidth: 1,
    borderTopColor: unifiedTheme.colors.surface.border,
    position: 'relative',
    ...Platform.select({
      ios: {
        ...unifiedTheme.shadows.base,
      },
      android: {
        elevation: 8,
      },
    }),
  },
  tabs: {
    flexDirection: 'row',
    paddingTop: unifiedTheme.spacing[2],
    paddingBottom: unifiedTheme.spacing[1],
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: unifiedTheme.spacing[2],
  },
  tabContent: {
    alignItems: 'center',
    gap: unifiedTheme.spacing[1],
  },
  label: {
    ...unifiedTheme.typography.caption,
    fontFamily: unifiedTheme.fontFamilies.medium,
  },
  indicator: {
    position: 'absolute',
    top: 0,
    width: 40,
    height: 3,
    backgroundColor: unifiedTheme.colors.primary[600],
    borderRadius: unifiedTheme.borderRadius.full,
    marginLeft: -20,
  },
});
