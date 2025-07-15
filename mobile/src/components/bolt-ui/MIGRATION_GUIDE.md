# Bolt UI Migration Guide

## Overview
This guide helps you migrate RoadTrip screens to use Bolt's beautiful UI components while maintaining Redux state management.

## Quick Start

### 1. Import the Unified Theme
```typescript
import { unifiedTheme } from '../theme/unified';
// Replace old theme imports
```

### 2. Use Bolt UI Components
```typescript
import { 
  PersonalityCard, 
  StoryCard, 
  PrimaryButton,
  FeatureCard,
  HeaderSection 
} from '../components/bolt-ui';
```

### 3. State Management Adapter
```typescript
// Old Redux pattern:
const dispatch = useDispatch();
const user = useSelector(state => state.auth.user);

// With adapter (Zustand-like):
const { state: user, login, logout } = useStoreAdapter(
  (state) => state.auth.user,
  { login: authActions.login, logout: authActions.logout }
);
```

## Component Migration Examples

### Before (RoadTrip Style):
```typescript
<TouchableOpacity style={styles.button} onPress={handlePress}>
  <Text style={styles.buttonText}>Start Journey</Text>
</TouchableOpacity>
```

### After (Bolt Style):
```typescript
<PrimaryButton
  title="Start Journey"
  onPress={handlePress}
  icon="navigation"
  size="large"
/>
```

## Screen Migration Example

### Original VoicePersonalityScreen (Complex)
```typescript
// Complex Redux logic, basic styling
```

### Migrated with Bolt UI:
```typescript
import React from 'react';
import { ScrollView, View } from 'react-native';
import { HeaderSection, PersonalityCard } from '../components/bolt-ui';
import { unifiedTheme } from '../theme/unified';

export const VoicePersonalityScreen = () => {
  return (
    <ScrollView style={{ backgroundColor: unifiedTheme.colors.surface.background }}>
      <HeaderSection
        icon="microphone-variant"
        title="Choose Your Voice"
        subtitle="Select a personality for your journey"
        centered
      />
      
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        {personalities.map(personality => (
          <PersonalityCard
            key={personality.id}
            personality={personality}
            isSelected={selectedId === personality.id}
            onPress={handleSelect}
          />
        ))}
      </ScrollView>
    </ScrollView>
  );
};
```

## Styling Migration

### Old Pattern:
```typescript
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  }
});
```

### New Pattern:
```typescript
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: unifiedTheme.colors.surface.background,
    padding: unifiedTheme.spacing[4],
  },
  title: {
    ...unifiedTheme.typography.h3,
    color: unifiedTheme.colors.neutral[900],
  }
});
```

## Animation Migration

### Old:
```typescript
Animated.timing(animValue, {
  toValue: 1,
  duration: 300,
  useNativeDriver: true,
}).start();
```

### New (with Reanimated):
```typescript
animValue.value = withSpring(1, unifiedTheme.animations.spring.gentle);
```

## Best Practices

1. **Keep Redux for Complex State** - Don't migrate everything to Zustand patterns
2. **Use Theme Consistently** - Always use unified theme values
3. **Maintain Accessibility** - Bolt components include a11y props
4. **Test on Both Platforms** - Ensure iOS and Android compatibility
5. **Progressive Migration** - Start with visual components, then screens

## Common Pitfalls

1. **Don't Mix Navigators** - Keep react-navigation, don't use expo-router patterns
2. **Redux Actions** - Remember to dispatch actions, don't call them directly
3. **Async Handling** - RoadTrip uses Redux Thunk, not Zustand's simpler patterns
4. **Type Safety** - Update TypeScript types when migrating

## Performance Tips

1. Use `React.memo` for list items
2. Implement `keyExtractor` properly
3. Use `FlatList` for long lists, not ScrollView
4. Lazy load heavy components

## Migration Checklist

- [ ] Install Inter font family
- [ ] Update color constants to unified theme
- [ ] Replace custom buttons with PrimaryButton
- [ ] Update cards to use Bolt card components
- [ ] Migrate animations to Reanimated 3
- [ ] Test on iOS and Android devices
- [ ] Update TypeScript types
- [ ] Run performance profiler
- [ ] Update unit tests
- [ ] Document any custom modifications
