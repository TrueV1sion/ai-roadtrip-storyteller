/**
 * PersonalitySelector Component
 * Allows users to browse and select voice personalities
 */

import React, { useState, useCallback } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Modal,
  Dimensions,
  Platform,
} from 'react-native';
import Animated, {
  FadeIn,
  FadeOut,
  SlideInRight,
  useAnimatedStyle,
  withSpring,
} from 'react-native-reanimated';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Path } from 'react-native-svg';
import { lightTheme as theme } from '../../design/theme';
import { PERSONALITY_INFO, FrontendPersonalityId } from '../../constants/personalityMappings';
import googleCloudTTS from '../../services/googleCloudTTS';
import { audioPlaybackService } from '../../services/audioPlaybackService';
import * as Haptics from 'expo-haptics';

interface PersonalitySelectorProps {
  visible: boolean;
  currentPersonality: string;
  onSelect: (personalityId: string) => void;
  onClose: () => void;
}

const { width: screenWidth } = Dimensions.get('window');

// Group personalities by category
const groupedPersonalities = Object.entries(PERSONALITY_INFO).reduce((acc, [id, info]) => {
  const category = info.category;
  if (!acc[category]) {
    acc[category] = [];
  }
  acc[category].push({ id, ...info });
  return acc;
}, {} as Record<string, Array<{ id: string; name: string; description: string; category: string }>>);

const categoryOrder = ['core', 'event', 'seasonal', 'specialty', 'regional'];
const categoryNames = {
  core: 'Essential Guides',
  event: 'Event Companions',
  seasonal: 'Holiday Specials',
  specialty: 'Special Features',
  regional: 'Regional Voices',
};

export const PersonalitySelector: React.FC<PersonalitySelectorProps> = ({
  visible,
  currentPersonality,
  onSelect,
  onClose,
}) => {
  const [selectedCategory, setSelectedCategory] = useState('core');
  const [previewingPersonality, setPreviewingPersonality] = useState<string | null>(null);

  const handlePersonalityPress = useCallback(async (personalityId: string) => {
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onSelect(personalityId);
    onClose();
  }, [onSelect, onClose]);

  const handlePreview = useCallback(async (personalityId: string) => {
    if (previewingPersonality === personalityId) {
      // Stop preview
      await audioPlaybackService.stop();
      setPreviewingPersonality(null);
      return;
    }

    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setPreviewingPersonality(personalityId);

    try {
      // Generate preview text based on personality
      const previewTexts = {
        'santa-claus': 'Ho ho ho! Welcome aboard for a magical Christmas journey!',
        'mickey-mouse': 'Oh boy! Are you ready for an amazing adventure?',
        'rock-dj': "Let's rock this road trip! Turn it up to eleven!",
        'southern-charm': "Well, bless your heart! Y'all ready for some Southern hospitality?",
        'adventurer': 'Adventure awaits! Let\'s explore the incredible world around us!',
        'comedian': 'Why did the road trip cross the highway? To get to the punchline!',
      };

      const previewText = previewTexts[personalityId as keyof typeof previewTexts] || 
        `Hello! I'm ${PERSONALITY_INFO[personalityId as FrontendPersonalityId].name}, your road trip companion.`;

      // Synthesize preview speech
      const audioPath = await googleCloudTTS.synthesizeSpeech({
        text: previewText,
        personalityId,
        ssml: true,
      });

      // Play the preview
      await audioPlaybackService.play(audioPath, {
        volume: 0.8,
        onComplete: () => setPreviewingPersonality(null),
      });
    } catch (error) {
      logger.error('Preview failed:', error);
      setPreviewingPersonality(null);
    }
  }, [previewingPersonality]);

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={true}
      onRequestClose={onClose}
    >
      <View style={styles.modalOverlay}>
        <Animated.View
          entering={SlideInRight.duration(300)}
          exiting={FadeOut.duration(200)}
          style={styles.modalContent}
        >
          <LinearGradient
            colors={[theme.colors.background.primary, theme.colors.background.secondary]}
            style={styles.gradient}
          >
            {/* Header */}
            <View style={styles.header}>
              <Text style={styles.title}>Choose Your Guide</Text>
              <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                <Svg width={24} height={24} viewBox="0 0 24 24">
                  <Path
                    d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
                    fill={theme.colors.text.secondary}
                  />
                </Svg>
              </TouchableOpacity>
            </View>

            {/* Category Tabs */}
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              style={styles.categoryTabs}
              contentContainerStyle={styles.categoryTabsContent}
            >
              {categoryOrder.map((category) => (
                <TouchableOpacity
                  key={category}
                  onPress={() => setSelectedCategory(category)}
                  style={[
                    styles.categoryTab,
                    selectedCategory === category && styles.categoryTabActive,
                  ]}
                >
                  <Text
                    style={[
                      styles.categoryTabText,
                      selectedCategory === category && styles.categoryTabTextActive,
                    ]}
                  >
                    {categoryNames[category as keyof typeof categoryNames]}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>

            {/* Personalities Grid */}
            <ScrollView
              style={styles.personalitiesContainer}
              showsVerticalScrollIndicator={false}
            >
              <View style={styles.personalitiesGrid}>
                {groupedPersonalities[selectedCategory]?.map((personality) => (
                  <Animated.View
                    key={personality.id}
                    entering={FadeIn.delay(100)}
                    style={styles.personalityCardContainer}
                  >
                    <TouchableOpacity
                      onPress={() => handlePersonalityPress(personality.id)}
                      onLongPress={() => handlePreview(personality.id)}
                      delayLongPress={300}
                      style={[
                        styles.personalityCard,
                        currentPersonality === personality.id && styles.personalityCardActive,
                        previewingPersonality === personality.id && styles.personalityCardPreviewing,
                      ]}
                    >
                      <LinearGradient
                        colors={
                          currentPersonality === personality.id
                            ? theme.colors.gradients.aurora
                            : [theme.colors.surface.elevated, theme.colors.surface.base]
                        }
                        style={styles.personalityGradient}
                        start={{ x: 0, y: 0 }}
                        end={{ x: 1, y: 1 }}
                      >
                        {/* Personality Icon */}
                        <View style={styles.personalityIcon}>
                          {getPersonalityIcon(personality.id)}
                        </View>

                        {/* Personality Info */}
                        <Text style={styles.personalityName}>{personality.name}</Text>
                        <Text style={styles.personalityDescription} numberOfLines={2}>
                          {personality.description}
                        </Text>

                        {/* Preview indicator */}
                        {previewingPersonality === personality.id && (
                          <View style={styles.previewIndicator}>
                            <Text style={styles.previewText}>Playing...</Text>
                          </View>
                        )}
                      </LinearGradient>
                    </TouchableOpacity>
                  </Animated.View>
                ))}
              </View>
            </ScrollView>

            {/* Help Text */}
            <View style={styles.helpContainer}>
              <Text style={styles.helpText}>Tap to select • Hold to preview</Text>
            </View>
          </LinearGradient>
        </Animated.View>
      </View>
    </Modal>
  );
};

// Helper function to get personality-specific icons
function getPersonalityIcon(personalityId: string): React.ReactNode {
  const iconColor = theme.colors.text.inverse;
  const iconSize = 32;

  const icons: Record<string, React.ReactNode> = {
    'santa-claus': (
      <Svg width={iconSize} height={iconSize} viewBox="0 0 24 24">
        <Path
          d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2M16 17C16 15.9 16.9 15 18 15S20 15.9 20 17 19.1 19 18 19 16 18.1 16 17M6 17C6 15.9 5.1 15 4 15S2 15.9 2 17 2.9 19 4 19 6 18.1 6 17M11.5 7.5C11.5 6.7 10.8 6 10 6H8C7.2 6 6.5 6.7 6.5 7.5C6.5 8.3 7.2 9 8 9H10C10.8 9 11.5 8.3 11.5 7.5M16 10.5C16 9.7 15.3 9 14.5 9H13.5C12.7 9 12 9.7 12 10.5S12.7 12 13.5 12H14.5C15.3 12 16 11.3 16 10.5M12 17C12 14.8 10.2 13 8 13S4 14.8 4 17C4 19.2 5.8 21 8 21S12 19.2 12 17M20 17C20 14.8 18.2 13 16 13S12 14.8 12 17C12 19.2 13.8 21 16 21S20 19.2 20 17Z"
          fill={iconColor}
        />
      </Svg>
    ),
    'mickey-mouse': (
      <Svg width={iconSize} height={iconSize} viewBox="0 0 24 24">
        <Path
          d="M12 15.5C10.07 15.5 8.5 13.93 8.5 12S10.07 8.5 12 8.5 15.5 10.07 15.5 12 13.93 15.5 12 15.5M12 2C15.31 2 18 4.69 18 8C18 8.68 17.88 9.34 17.67 9.95C17.12 8.8 15.66 8 14 8C13.62 8 13.26 8.06 12.91 8.17C12.63 8.06 12.32 8 12 8C11.68 8 11.37 8.06 11.09 8.17C10.74 8.06 10.38 8 10 8C8.34 8 6.88 8.8 6.33 9.95C6.12 9.34 6 8.68 6 8C6 4.69 8.69 2 12 2M7 18C4.24 18 2 15.76 2 13S4.24 8 7 8 12 10.24 12 13 9.76 18 7 18M17 18C14.24 18 12 15.76 12 13S14.24 8 17 8 22 10.24 22 13 19.76 18 17 18Z"
          fill={iconColor}
        />
      </Svg>
    ),
    // Add more icons as needed
  };

  return icons[personalityId] || (
    <Svg width={iconSize} height={iconSize} viewBox="0 0 24 24">
      <Path
        d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"
        fill={iconColor}
      />
    </Svg>
  );
}

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    height: screenWidth > 400 ? '85%' : '90%',
    borderTopLeftRadius: theme.layout.borderRadius.xl,
    borderTopRightRadius: theme.layout.borderRadius.xl,
    overflow: 'hidden',
    ...theme.elevation.highest,
  },
  gradient: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
    paddingBottom: theme.spacing.md,
  },
  title: {
    ...theme.typography.headlineMedium,
    color: theme.colors.text.primary,
  },
  closeButton: {
    padding: theme.spacing.sm,
  },
  categoryTabs: {
    maxHeight: 50,
    marginBottom: theme.spacing.md,
  },
  categoryTabsContent: {
    paddingHorizontal: theme.spacing.lg,
    gap: theme.spacing.sm,
  },
  categoryTab: {
    paddingHorizontal: theme.spacing.lg,
    paddingVertical: theme.spacing.sm,
    borderRadius: theme.layout.borderRadius.full,
    backgroundColor: theme.colors.surface.elevated,
  },
  categoryTabActive: {
    backgroundColor: theme.colors.primary[500],
  },
  categoryTabText: {
    ...theme.typography.labelLarge,
    color: theme.colors.text.secondary,
  },
  categoryTabTextActive: {
    color: theme.colors.text.inverse,
  },
  personalitiesContainer: {
    flex: 1,
  },
  personalitiesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: theme.spacing.md,
    paddingBottom: theme.spacing.xl,
    gap: theme.spacing.md,
  },
  personalityCardContainer: {
    width: (screenWidth - theme.spacing.md * 4) / 2,
  },
  personalityCard: {
    height: 140,
    borderRadius: theme.layout.borderRadius.lg,
    overflow: 'hidden',
    ...theme.elevation.medium,
  },
  personalityCardActive: {
    ...theme.elevation.high,
  },
  personalityCardPreviewing: {
    transform: [{ scale: 0.95 }],
  },
  personalityGradient: {
    flex: 1,
    padding: theme.spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  personalityIcon: {
    marginBottom: theme.spacing.sm,
  },
  personalityName: {
    ...theme.typography.labelLarge,
    color: theme.colors.text.inverse,
    textAlign: 'center',
    marginBottom: theme.spacing.xs,
  },
  personalityDescription: {
    ...theme.typography.bodySmall,
    color: theme.colors.text.inverse,
    textAlign: 'center',
    opacity: 0.9,
  },
  previewIndicator: {
    position: 'absolute',
    top: theme.spacing.sm,
    right: theme.spacing.sm,
    backgroundColor: theme.colors.primary[500],
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
    borderRadius: theme.layout.borderRadius.sm,
  },
  previewText: {
    ...theme.typography.labelSmall,
    color: theme.colors.text.inverse,
  },
  helpContainer: {
    paddingVertical: theme.spacing.md,
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: theme.colors.border.subtle,
  },
  helpText: {
    ...theme.typography.bodySmall,
    color: theme.colors.text.secondary,
  },
});