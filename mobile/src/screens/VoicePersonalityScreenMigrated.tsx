/**
 * VoicePersonalityScreen - Migrated Version
 * Demonstrates Bolt UI integration with RoadTrip's functionality
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  RefreshControl,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { useDispatch, useSelector } from 'react-redux';
import Animated, { FadeIn } from 'react-native-reanimated';

// Bolt UI Components
import {
  HeaderSection,
  PersonalityCard,
  PrimaryButton,
  TabBar,
} from '../components/bolt-ui';

// Unified Theme
import { unifiedTheme } from '../theme/unified';

// RoadTrip functionality
import { voicePersonalityService } from '../services/voicePersonalityService';
import { 
  fetchPersonalities, 
  selectPersonality,
  setAutoMode,
} from '../store/slices/voiceSlice';
import { RootState } from '../store';
import { VoicePersonality } from '../types/voice';

const { width } = Dimensions.get('window');

export const VoicePersonalityScreenMigrated: React.FC = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  
  // Redux state
  const { 
    personalities, 
    selectedPersonality, 
    isLoading,
    autoSelect 
  } = useSelector((state: RootState) => state.voice);
  
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<string | null>(null);

  useEffect(() => {
    loadPersonalities();
  }, []);

  const loadPersonalities = async () => {
    dispatch(fetchPersonalities());
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadPersonalities();
    setRefreshing(false);
  };

  const handlePersonalitySelect = (personality: VoicePersonality) => {
    dispatch(selectPersonality(personality));
    // Play sample voice
    voicePersonalityService.playGreetingSample(personality.id);
  };

  const handleAutoModeToggle = () => {
    dispatch(setAutoMode(!autoSelect));
  };

  const filteredPersonalities = filter
    ? personalities.filter(p => p.category === filter)
    : personalities;

  const categories = [...new Set(personalities.map(p => p.category))];

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={unifiedTheme.colors.primary[600]}
          />
        }
      >
        {/* Beautiful Header from Bolt */}
        <HeaderSection
          icon="microphone-variant"
          iconColor={unifiedTheme.colors.primary[600]}
          title="Voice Personalities"
          subtitle="Choose your AI companion for the journey"
          centered
        />

        {/* Auto Mode Toggle */}
        <Animated.View 
          entering={FadeIn.delay(200)}
          style={styles.autoModeContainer}
        >
          <View style={styles.autoModeCard}>
            <View style={styles.autoModeText}>
              <Text style={styles.autoModeTitle}>Automatic Selection</Text>
              <Text style={styles.autoModeDescription}>
                Let AI choose the best personality based on your destination
              </Text>
            </View>
            <Switch
              value={autoSelect}
              onValueChange={handleAutoModeToggle}
              trackColor={{
                false: unifiedTheme.colors.neutral[300],
                true: unifiedTheme.colors.primary[600],
              }}
              thumbColor={autoSelect ? 'white' : unifiedTheme.colors.neutral[100]}
            />
          </View>
        </Animated.View>

        {/* Category Filter */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.filterContainer}
        >
          <PrimaryButton
            title="All"
            variant={filter === null ? 'primary' : 'ghost'}
            size="small"
            onPress={() => setFilter(null)}
            style={styles.filterButton}
          />
          {categories.map((category) => (
            <PrimaryButton
              key={category}
              title={category}
              variant={filter === category ? 'primary' : 'ghost'}
              size="small"
              onPress={() => setFilter(category)}
              style={styles.filterButton}
            />
          ))}
        </ScrollView>

        {/* Personality Cards */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.personalitiesContainer}
          decelerationRate="fast"
          snapToInterval={width * 0.8 + unifiedTheme.spacing[4]}
          snapToAlignment="center"
        >
          {filteredPersonalities.map((personality, index) => (
            <Animated.View
              key={personality.id}
              entering={FadeIn.delay(300 + index * 100).springify()}
            >
              <PersonalityCard
                personality={personality}
                isSelected={selectedPersonality?.id === personality.id}
                onPress={handlePersonalitySelect}
              />
            </Animated.View>
          ))}
        </ScrollView>

        {/* Action Buttons */}
        <View style={styles.actions}>
          <PrimaryButton
            title="Start Journey"
            icon="navigation"
            size="large"
            fullWidth
            disabled={!selectedPersonality && !autoSelect}
            onPress={() => navigation.navigate('Navigation')}
          />
          
          <PrimaryButton
            title="Preview Voice"
            icon="play-circle"
            variant="secondary"
            size="large"
            fullWidth
            disabled={!selectedPersonality}
            onPress={() => {
              if (selectedPersonality) {
                voicePersonalityService.playGreetingSample(selectedPersonality.id);
              }
            }}
            style={{ marginTop: unifiedTheme.spacing[3] }}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: unifiedTheme.colors.surface.background,
  },
  autoModeContainer: {
    paddingHorizontal: unifiedTheme.layout.screenPadding.horizontal,
    marginBottom: unifiedTheme.spacing[6],
  },
  autoModeCard: {
    backgroundColor: unifiedTheme.colors.surface.card,
    borderRadius: unifiedTheme.borderRadius.lg,
    padding: unifiedTheme.spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    ...unifiedTheme.shadows.base,
  },
  autoModeText: {
    flex: 1,
    marginRight: unifiedTheme.spacing[4],
  },
  autoModeTitle: {
    ...unifiedTheme.typography.h6,
    color: unifiedTheme.colors.neutral[900],
    marginBottom: unifiedTheme.spacing[1],
  },
  autoModeDescription: {
    ...unifiedTheme.typography.bodySmall,
    color: unifiedTheme.colors.neutral[600],
  },
  filterContainer: {
    paddingHorizontal: unifiedTheme.layout.screenPadding.horizontal,
    gap: unifiedTheme.spacing[2],
    marginBottom: unifiedTheme.spacing[6],
  },
  filterButton: {
    marginRight: unifiedTheme.spacing[2],
  },
  personalitiesContainer: {
    paddingHorizontal: unifiedTheme.layout.screenPadding.horizontal,
    paddingBottom: unifiedTheme.spacing[6],
  },
  actions: {
    paddingHorizontal: unifiedTheme.layout.screenPadding.horizontal,
    paddingBottom: unifiedTheme.spacing[8],
  },
});

// Export for use in navigation
export default VoicePersonalityScreenMigrated;
