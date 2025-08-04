/**
 * Voice Personality Test Screen
 * Demonstrates all 20+ voice personalities with TTS
 */

import React, { useState, useCallback } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  ScrollView,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import googleCloudTTS from '../services/googleCloudTTS';
import { audioPlaybackService } from '../services/audioPlaybackService';
import { PERSONALITY_INFO, FrontendPersonalityId } from '../constants/personalityMappings';
import { VoiceButton } from '../design/components/VoiceButton/VoiceButton';
import { PersonalitySelector } from '../components/PersonalitySelector';
import { lightTheme as theme } from '../design/theme';

export const VoicePersonalityTestScreen: React.FC = () => {
  const [currentPersonality, setCurrentPersonality] = useState<string>('friendly-guide');
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectorVisible, setSelectorVisible] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, boolean>>({});

  const testPhrases = {
    'friendly-guide': "Welcome aboard! I'm your friendly guide for this amazing journey ahead.",
    'navigator': "Turn right in 500 feet, then continue straight for 2 miles.",
    'educational-expert': "Did you know? This historic landmark was built in 1856 and played a crucial role in American history.",
    'adventurer': "Look at that incredible mountain peak! Adventure is calling our names!",
    'comedian': "Why don't scientists trust atoms? Because they make up everything!",
    'local-expert': "Folks around here know the best barbecue joint is just off Exit 42.",
    'mickey-mouse': "Oh boy! This is going to be the most magical road trip ever! Ha-ha!",
    'rock-dj': "Alright road warriors! Let's crank up the volume and rock this highway!",
    'santa-claus': "Ho ho ho! Have you been good this year? Let's spread some Christmas cheer!",
    'halloween-narrator': "Listen carefully... on nights like this, strange things happen on these roads...",
    'cupid': "Love is in the air! This scenic route is perfect for romance.",
    'leprechaun': "Top of the morning! Follow me to find the pot of gold at the end of this rainbow!",
    'patriot': "This great nation's highways tell the story of American freedom and ingenuity!",
    'harvest-guide': "Gather 'round! Let's give thanks for this beautiful autumn journey.",
    'inspirational': "Every mile you travel is a step toward your dreams. Believe in the journey!",
    'southern-charm': "Well, bless your heart! Y'all are in for some real Southern hospitality!",
    'new-england-scholar': "Indeed, this route passes through some of America's most historically significant locations.",
    'midwest-neighbor': "Oh, you betcha! This here's the scenic route through God's country!",
    'west-coast-cool': "Dude, this coastal drive is totally epic. Just chill and enjoy the vibes.",
    'mountain-sage': "The mountains teach us patience and perspective. Listen to their ancient wisdom.",
    'texas-ranger': "Everything's bigger in Texas, partner! Including the adventures on these roads!",
    'jazz-storyteller': "Let me tell you a smooth story about this jazzy little town coming up...",
    'beach-vibes': "Surf's up! Feel that ocean breeze as we cruise along the coast.",
  };

  const playPersonality = useCallback(async (personalityId: string) => {
    if (isPlaying || isLoading) {
      await audioPlaybackService.stop();
      setIsPlaying(false);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setCurrentPersonality(personalityId);

    try {
      const text = testPhrases[personalityId as keyof typeof testPhrases] || 
        `Hello! I'm ${PERSONALITY_INFO[personalityId as FrontendPersonalityId].name}.`;

      const audioPath = await googleCloudTTS.synthesizeSpeech({
        text,
        personalityId,
        ssml: true,
      });

      setIsLoading(false);
      setIsPlaying(true);

      await audioPlaybackService.play(audioPath, {
        volume: 0.9,
        onComplete: () => {
          setIsPlaying(false);
          setTestResults(prev => ({ ...prev, [personalityId]: true }));
        },
      });
    } catch (error) {
      logger.error('Failed to play personality:', error);
      setIsLoading(false);
      setIsPlaying(false);
      setTestResults(prev => ({ ...prev, [personalityId]: false }));
    }
  }, [isPlaying, isLoading]);

  const testAllPersonalities = useCallback(async () => {
    for (const personalityId of Object.keys(PERSONALITY_INFO)) {
      await playPersonality(personalityId);
      // Wait for playback to complete
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
  }, [playPersonality]);

  return (
    <SafeAreaView style={styles.container}>
      <LinearGradient
        colors={theme.colors.gradients.background}
        style={styles.gradient}
      >
        <ScrollView contentContainerStyle={styles.scrollContent}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>Voice Personality Test</Text>
            <Text style={styles.subtitle}>Tap any personality to preview</Text>
          </View>

          {/* Current Personality Display */}
          <View style={styles.currentPersonalityCard}>
            <Text style={styles.currentLabel}>Current Voice</Text>
            <Text style={styles.currentName}>
              {PERSONALITY_INFO[currentPersonality as FrontendPersonalityId]?.name}
            </Text>
            <Text style={styles.currentDescription}>
              {PERSONALITY_INFO[currentPersonality as FrontendPersonalityId]?.description}
            </Text>
          </View>

          {/* Voice Button */}
          <View style={styles.voiceButtonContainer}>
            <VoiceButton
              isListening={isPlaying}
              onPress={() => playPersonality(currentPersonality)}
              disabled={isLoading}
            />
          </View>

          {/* Quick Actions */}
          <View style={styles.quickActions}>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => setSelectorVisible(true)}
            >
              <LinearGradient
                colors={theme.colors.gradients.journey}
                style={styles.actionButtonGradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
              >
                <Text style={styles.actionButtonText}>Browse All Voices</Text>
              </LinearGradient>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.actionButton}
              onPress={testAllPersonalities}
              disabled={isPlaying || isLoading}
            >
              <LinearGradient
                colors={theme.colors.gradients.aurora}
                style={styles.actionButtonGradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
              >
                <Text style={styles.actionButtonText}>Test All Voices</Text>
              </LinearGradient>
            </TouchableOpacity>
          </View>

          {/* Personality Grid */}
          <View style={styles.personalityGrid}>
            {Object.entries(PERSONALITY_INFO).map(([id, info]) => (
              <TouchableOpacity
                key={id}
                style={[
                  styles.personalityTile,
                  currentPersonality === id && styles.personalityTileActive,
                  testResults[id] === true && styles.personalityTileSuccess,
                  testResults[id] === false && styles.personalityTileError,
                ]}
                onPress={() => playPersonality(id)}
                disabled={isLoading}
              >
                <Text style={styles.personalityTileName} numberOfLines={1}>
                  {info.name}
                </Text>
                <Text style={styles.personalityTileCategory}>
                  {info.category}
                </Text>
                {isLoading && currentPersonality === id && (
                  <ActivityIndicator
                    size="small"
                    color={theme.colors.primary[500]}
                    style={styles.personalityTileLoader}
                  />
                )}
              </TouchableOpacity>
            ))}
          </View>

          {/* Test Status */}
          <View style={styles.statusContainer}>
            <Text style={styles.statusText}>
              Tested: {Object.keys(testResults).length} / {Object.keys(PERSONALITY_INFO).length}
            </Text>
            <Text style={styles.statusText}>
              Successful: {Object.values(testResults).filter(v => v).length}
            </Text>
          </View>
        </ScrollView>

        {/* Personality Selector Modal */}
        <PersonalitySelector
          visible={selectorVisible}
          currentPersonality={currentPersonality}
          onSelect={setCurrentPersonality}
          onClose={() => setSelectorVisible(false)}
        />
      </LinearGradient>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  gradient: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: theme.spacing.xl,
  },
  header: {
    alignItems: 'center',
    paddingTop: theme.spacing.xl,
    paddingBottom: theme.spacing.lg,
  },
  title: {
    ...theme.typography.headlineLarge,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.xs,
  },
  subtitle: {
    ...theme.typography.bodyMedium,
    color: theme.colors.text.secondary,
  },
  currentPersonalityCard: {
    marginHorizontal: theme.spacing.lg,
    padding: theme.spacing.lg,
    backgroundColor: theme.colors.surface.elevated,
    borderRadius: theme.layout.borderRadius.lg,
    alignItems: 'center',
    ...theme.elevation.medium,
  },
  currentLabel: {
    ...theme.typography.labelMedium,
    color: theme.colors.text.secondary,
    marginBottom: theme.spacing.xs,
  },
  currentName: {
    ...theme.typography.headlineMedium,
    color: theme.colors.text.primary,
    marginBottom: theme.spacing.sm,
  },
  currentDescription: {
    ...theme.typography.bodyMedium,
    color: theme.colors.text.secondary,
    textAlign: 'center',
  },
  voiceButtonContainer: {
    alignItems: 'center',
    marginVertical: theme.spacing.xl,
  },
  quickActions: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: theme.spacing.md,
    marginBottom: theme.spacing.xl,
  },
  actionButton: {
    borderRadius: theme.layout.borderRadius.full,
    overflow: 'hidden',
  },
  actionButtonGradient: {
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.md,
  },
  actionButtonText: {
    ...theme.typography.labelLarge,
    color: theme.colors.text.inverse,
  },
  personalityGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: theme.spacing.md,
    gap: theme.spacing.sm,
  },
  personalityTile: {
    width: '30%',
    padding: theme.spacing.md,
    backgroundColor: theme.colors.surface.base,
    borderRadius: theme.layout.borderRadius.md,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: 'transparent',
  },
  personalityTileActive: {
    borderColor: theme.colors.primary[500],
    backgroundColor: theme.colors.surface.elevated,
  },
  personalityTileSuccess: {
    borderColor: theme.colors.success[500],
  },
  personalityTileError: {
    borderColor: theme.colors.error[500],
  },
  personalityTileName: {
    ...theme.typography.labelMedium,
    color: theme.colors.text.primary,
    textAlign: 'center',
    marginBottom: theme.spacing.xs,
  },
  personalityTileCategory: {
    ...theme.typography.bodySmall,
    color: theme.colors.text.secondary,
    textAlign: 'center',
  },
  personalityTileLoader: {
    position: 'absolute',
    top: theme.spacing.xs,
    right: theme.spacing.xs,
  },
  statusContainer: {
    marginTop: theme.spacing.xl,
    paddingHorizontal: theme.spacing.lg,
    alignItems: 'center',
    gap: theme.spacing.sm,
  },
  statusText: {
    ...theme.typography.bodyMedium,
    color: theme.colors.text.secondary,
  },
});