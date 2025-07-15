/**
 * Design Showcase Screen
 * Demonstrates all FAANG-quality components
 */

import React, { useState } from 'react';
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { VoiceButton, StoryCard, NavigationStatus } from '../design/components';
import { lightTheme as theme } from '../design/theme';

export const DesignShowcaseScreen: React.FC = () => {
  const [isListening, setIsListening] = useState(false);
  const [navigationProgress, setNavigationProgress] = useState(0.45);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={theme.colors.neutral[900]} />
      
      {/* Background gradient */}
      <LinearGradient
        colors={theme.colors.gradients.dark}
        style={StyleSheet.absoluteFill}
      />
      
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>AI Road Trip Storyteller</Text>
          <Text style={styles.subtitle}>FAANG-Quality Design System</Text>
        </View>

        {/* Section: Voice Interaction */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Voice Interaction</Text>
          <View style={styles.voiceContainer}>
            <VoiceButton
              isListening={isListening}
              onPress={() => setIsListening(!isListening)}
              transcript={isListening ? "Navigate to Disneyland" : undefined}
            />
          </View>
        </View>

        {/* Section: Navigation Status */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Navigation Status</Text>
          <NavigationStatus
            status="On route to Disneyland Resort"
            progress={navigationProgress}
            eta="2h 15m"
            distance="127 miles"
            nextTurn={{
              direction: 'right',
              distance: '0.5 mi',
              instruction: 'Turn right onto Harbor Blvd',
            }}
            speed={65}
            speedLimit={65}
          />
        </View>

        {/* Section: Story Cards */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Story Cards</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.cardsContainer}
          >
            <StoryCard
              title="The Legend of Sleeping Beauty Castle"
              description="Discover the enchanting story behind Disneyland's iconic centerpiece and Walt Disney's personal touches."
              duration="5:23"
              imageUrl="https://images.unsplash.com/photo-1605972820726-668b4dd2e135?w=400"
              narrator="Mickey Mouse"
              isPlaying={true}
              progress={0.3}
              onPress={() => console.log('Story 1 pressed')}
              style={styles.storyCard}
            />
            
            <StoryCard
              title="Route 66: America's Main Street"
              description="Journey through the history of the Mother Road and its influence on American culture."
              duration="8:45"
              imageUrl="https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=400"
              narrator="Local Historian"
              onPress={() => console.log('Story 2 pressed')}
              style={styles.storyCard}
            />
            
            <StoryCard
              title="California Coastal Wildlife"
              description="Learn about the diverse marine life and ecosystems along the Pacific Coast Highway."
              duration="6:12"
              imageUrl="https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=400"
              narrator="Nature Guide"
              onPress={() => console.log('Story 3 pressed')}
              style={styles.storyCard}
            />
          </ScrollView>
        </View>

        {/* Section: Color Palette */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Aurora Color Palette</Text>
          <View style={styles.colorGrid}>
            {Object.entries(theme.colors.aurora).map(([name, color]) => (
              <View key={name} style={styles.colorItem}>
                <View style={[styles.colorSwatch, { backgroundColor: color }]} />
                <Text style={styles.colorName}>{name}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Section: Gradients */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Gradient System</Text>
          <View style={styles.gradientGrid}>
            {Object.entries(theme.colors.gradients).map(([name, colors]) => (
              <View key={name} style={styles.gradientItem}>
                <LinearGradient
                  colors={colors as string[]}
                  style={styles.gradientSwatch}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                />
                <Text style={styles.gradientName}>{name}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Bottom spacing */}
        <View style={{ height: theme.spacing.xxxl }} />
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.neutral[900],
  },
  scrollContent: {
    paddingTop: theme.safeArea.top,
  },
  header: {
    alignItems: 'center',
    paddingVertical: theme.spacing.xl,
    paddingHorizontal: theme.spacing.md,
  },
  title: {
    ...theme.typography.displaySmall,
    color: theme.colors.text.inverse,
    textAlign: 'center',
  },
  subtitle: {
    ...theme.typography.titleMedium,
    color: theme.colors.primary[400],
    marginTop: theme.spacing.xs,
  },
  section: {
    paddingVertical: theme.spacing.lg,
    paddingHorizontal: theme.spacing.md,
  },
  sectionTitle: {
    ...theme.typography.headlineSmall,
    color: theme.colors.text.inverse,
    marginBottom: theme.spacing.md,
  },
  voiceContainer: {
    alignItems: 'center',
    paddingVertical: theme.spacing.xl,
  },
  cardsContainer: {
    paddingRight: theme.spacing.md,
    gap: theme.spacing.md,
  },
  storyCard: {
    marginRight: theme.spacing.md,
  },
  colorGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: theme.spacing.md,
  },
  colorItem: {
    alignItems: 'center',
    gap: theme.spacing.xs,
  },
  colorSwatch: {
    width: 60,
    height: 60,
    borderRadius: theme.layout.borderRadius.lg,
    ...theme.elevation.low,
  },
  colorName: {
    ...theme.typography.labelSmall,
    color: theme.colors.text.inverse,
    textTransform: 'capitalize',
  },
  gradientGrid: {
    gap: theme.spacing.md,
  },
  gradientItem: {
    gap: theme.spacing.xs,
  },
  gradientSwatch: {
    height: 60,
    borderRadius: theme.layout.borderRadius.lg,
    ...theme.elevation.low,
  },
  gradientName: {
    ...theme.typography.labelMedium,
    color: theme.colors.text.inverse,
    textTransform: 'capitalize',
  },
});