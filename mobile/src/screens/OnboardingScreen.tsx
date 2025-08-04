import React, { useState, useRef } from 'react';
import { View, StyleSheet, FlatList, Dimensions, Animated, Image } from 'react-native';
import { Text, Button, Surface, ProgressBar } from 'react-native-paper';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { MaterialIcons } from '@expo/vector-icons';
import { useTranslation } from '../i18n';

import { COLORS, SPACING } from '../theme';

import { logger } from '@/services/logger';
const { width } = Dimensions.get('window');

const onboardingData = [
  {
    id: '1',
    title: 'Welcome to Road Trip Storyteller',
    description: 'Transform your journey with location-based stories, trivia, and music that bring your surroundings to life.',
    iconName: 'map',
    backgroundColor: COLORS.primary + '15',
  },
  {
    id: '2',
    title: 'Discover Local Stories',
    description: 'Our AI generates fascinating stories about landmarks, historical events, and hidden gems along your route.',
    iconName: 'auto-stories',
    backgroundColor: COLORS.secondary + '15',
  },
  {
    id: '3',
    title: 'Navigate With Confidence',
    description: 'Turn-by-turn directions with immersive content, even when offline.',
    iconName: 'navigation',
    backgroundColor: COLORS.success + '15',
  },
  {
    id: '4',
    title: 'Travel Games & Trivia',
    description: 'Interactive trivia and games about the places you pass through, perfect for long drives.',
    iconName: 'psychology',
    backgroundColor: COLORS.warning + '15',
  },
  {
    id: '5',
    title: 'Offline Mode',
    description: 'Download routes, maps, and stories before your trip to enjoy them without an internet connection.',
    iconName: 'cloud-download',
    backgroundColor: COLORS.info + '15',
  },
];

const OnboardingScreen = ({ navigation }) => {
  const { t } = useTranslation();
  const [currentIndex, setCurrentIndex] = useState(0);
  const scrollX = useRef(new Animated.Value(0)).current;
  const slidesRef = useRef(null);

  const viewableItemsChanged = useRef(({ viewableItems }) => {
    setCurrentIndex(viewableItems[0]?.index || 0);
  }).current;

  const viewConfig = useRef({ viewAreaCoveragePercentThreshold: 50 }).current;

  const scrollTo = () => {
    if (currentIndex < onboardingData.length - 1) {
      slidesRef.current?.scrollToIndex({ index: currentIndex + 1 });
    } else {
      completeOnboarding();
    }
  };

  const completeOnboarding = async () => {
    try {
      await AsyncStorage.setItem('hasCompletedOnboarding', 'true');
      navigation.navigate('Permissions');
    } catch (error) {
      logger.error('Error saving onboarding status:', error);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.titleContainer}>
        <Text style={styles.appTitle}>Road Trip Storyteller</Text>
      </View>
      
      <View style={styles.slidesContainer}>
        <FlatList
          data={onboardingData}
          renderItem={({ item }) => <OnboardingItem item={item} />}
          horizontal
          showsHorizontalScrollIndicator={false}
          pagingEnabled
          bounces={false}
          keyExtractor={(item) => item.id}
          onScroll={Animated.event(
            [{ nativeEvent: { contentOffset: { x: scrollX } } }],
            { useNativeDriver: false }
          )}
          scrollEventThrottle={32}
          onViewableItemsChanged={viewableItemsChanged}
          viewabilityConfig={viewConfig}
          ref={slidesRef}
        />
      </View>

      <View style={styles.pagination}>
        <View style={styles.dotsContainer}>
          {onboardingData.map((_, i) => {
            const inputRange = [(i - 1) * width, i * width, (i + 1) * width];
            const dotWidth = scrollX.interpolate({
              inputRange,
              outputRange: [10, 20, 10],
              extrapolate: 'clamp',
            });
            const opacity = scrollX.interpolate({
              inputRange,
              outputRange: [0.3, 1, 0.3],
              extrapolate: 'clamp',
            });
            return (
              <Animated.View
                key={i.toString()}
                style={[styles.dot, { width: dotWidth, opacity }]}
              />
            );
          })}
        </View>

        <View style={styles.buttonsContainer}>
          {currentIndex < onboardingData.length - 1 ? (
            <>
              <Button
                mode="text"
                onPress={completeOnboarding}
                style={styles.skipButton}
                labelStyle={styles.skipButtonText}
                accessibilityLabel={t('onboarding.skip')}
                accessibilityHint={t('onboarding.skipHint')}
              >
                {t('onboarding.skip')}
              </Button>
              <Button
                mode="contained"
                onPress={scrollTo}
                style={styles.button}
                accessibilityLabel={t('onboarding.next')}
              >
                {t('onboarding.next')}
              </Button>
            </>
          ) : (
            <Button
              mode="contained"
              onPress={completeOnboarding}
              style={[styles.button, styles.getStartedButton]}
              accessibilityLabel={t('onboarding.getStarted')}
            >
              {t('onboarding.getStarted')}
            </Button>
          )}
        </View>
      </View>
    </SafeAreaView>
  );
};

const OnboardingItem = ({ item }) => {
  return (
    <View style={[styles.slide, { width }]}>
      <View style={[styles.iconContainer, { backgroundColor: item.backgroundColor }]}>
        <MaterialIcons name={item.iconName} size={80} color={COLORS.primary} />
      </View>
      <Text style={styles.title}>{item.title}</Text>
      <Text style={styles.description}>{item.description}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  titleContainer: {
    alignItems: 'center',
    marginTop: SPACING.large,
    marginBottom: SPACING.medium,
  },
  appTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: COLORS.primary,
  },
  slidesContainer: {
    flex: 3,
  },
  slide: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: SPACING.large,
  },
  iconContainer: {
    width: 160,
    height: 160,
    borderRadius: 80,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.large,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: SPACING.medium,
    color: COLORS.text,
  },
  description: {
    fontSize: 16,
    textAlign: 'center',
    color: COLORS.textSecondary,
    lineHeight: 24,
  },
  pagination: {
    flex: 1,
    justifyContent: 'space-between',
    paddingHorizontal: SPACING.large,
    paddingBottom: SPACING.large,
  },
  dotsContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: SPACING.medium,
  },
  dot: {
    height: 10,
    borderRadius: 5,
    backgroundColor: COLORS.primary,
    marginHorizontal: 5,
  },
  buttonsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  button: {
    paddingVertical: SPACING.small,
    flex: 1,
  },
  skipButton: {
    flex: 1,
  },
  skipButtonText: {
    color: COLORS.textSecondary,
  },
  getStartedButton: {
    flex: 1,
  },
});

export default OnboardingScreen; 