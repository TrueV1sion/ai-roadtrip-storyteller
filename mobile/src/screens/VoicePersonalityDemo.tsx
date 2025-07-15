/**
 * Voice Personality Demo Screen
 * Demonstrates Google Cloud TTS with all personality options
 */

import React, { useState, useEffect } from 'react';
import {
  ScrollView,
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import Animated, { 
  FadeInDown, 
  FadeInUp,
  Layout,
  ZoomIn,
} from 'react-native-reanimated';
import { VoiceButton, StoryCard } from '../design/components';
import { lightTheme as theme } from '../design/theme';
import enhancedVoiceService from '../services/voice/enhancedVoiceService';
import voiceRecognitionService from '../services/voiceRecognitionService';

// Sample stories for demo
const DEMO_STORIES = [
  {
    id: '1',
    title: 'Welcome to Your Journey',
    content: 'Welcome aboard the AI Road Trip Storyteller! I\'m excited to be your guide on this magical journey. Together, we\'ll discover amazing stories, explore hidden gems, and create memories that will last a lifetime. Are you ready to begin our adventure?',
    duration: '0:45',
    imageUrl: 'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=400',
  },
  {
    id: '2', 
    title: 'The Magic of Discovery',
    content: 'Every journey begins with a single mile, but the stories we discover along the way transform simple travels into extraordinary adventures. As we cruise down this highway, let me share the fascinating history of this region and the tales that have shaped its character.',
    duration: '1:15',
    imageUrl: 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=400',
  },
];

interface PersonalityOption {
  id: string;
  name: string;
  description: string;
  category: 'core' | 'event' | 'seasonal' | 'regional';
  icon: string;
  gradient: string[];
}

const PERSONALITIES: PersonalityOption[] = [
  // Core
  {
    id: 'navigator',
    name: 'Professional Navigator',
    description: 'Clear, professional guidance',
    category: 'core',
    icon: '🧭',
    gradient: theme.colors.gradients.journey,
  },
  {
    id: 'friendly-guide',
    name: 'Friendly Guide',
    description: 'Warm and conversational',
    category: 'core',
    icon: '😊',
    gradient: theme.colors.gradients.sunset,
  },
  {
    id: 'educational-expert',
    name: 'Educational Expert',
    description: 'Informative and engaging',
    category: 'core',
    icon: '🎓',
    gradient: [theme.colors.primary[600], theme.colors.primary[400]],
  },
  
  // Event
  {
    id: 'mickey-mouse',
    name: 'Mickey Mouse',
    description: 'Oh boy! Disney magic awaits!',
    category: 'event',
    icon: '🐭',
    gradient: [theme.colors.error, theme.colors.warning],
  },
  {
    id: 'rock-dj',
    name: 'Rock DJ',
    description: 'High energy concert vibes',
    category: 'event',
    icon: '🎸',
    gradient: [theme.colors.secondary[600], theme.colors.accent[500]],
  },
  
  // Seasonal
  {
    id: 'santa-claus',
    name: 'Santa Claus',
    description: 'Ho ho ho! Holiday cheer',
    category: 'seasonal',
    icon: '🎅',
    gradient: [theme.colors.error, theme.colors.success],
  },
  {
    id: 'halloween-narrator',
    name: 'Halloween Narrator',
    description: 'Spooky tales await...',
    category: 'seasonal',
    icon: '🎃',
    gradient: [theme.colors.neutral[800], theme.colors.accent[600]],
  },
  
  // Regional
  {
    id: 'southern-charm',
    name: 'Southern Charm',
    description: 'Sweet as sweet tea',
    category: 'regional',
    icon: '🍑',
    gradient: [theme.colors.accent[400], theme.colors.secondary[400]],
  },
  {
    id: 'texas-ranger',
    name: 'Texas Ranger',
    description: 'Big stories from the Lone Star State',
    category: 'regional',
    icon: '🤠',
    gradient: [theme.colors.accent[600], theme.colors.primary[700]],
  },
];

export const VoicePersonalityDemoScreen: React.FC = () => {
  const [selectedPersonality, setSelectedPersonality] = useState('navigator');
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [currentStory, setCurrentStory] = useState(0);

  useEffect(() => {
    // Set up voice recognition
    voiceRecognitionService.onSpeechResults((results) => {
      if (results && results.length > 0) {
        setTranscript(results[0]);
      }
    });

    voiceRecognitionService.onSpeechError((error) => {
      console.error('Speech recognition error:', error);
      setIsListening(false);
    });

    // Preload common phrases
    enhancedVoiceService.preloadCommonPhrases();

    return () => {
      voiceRecognitionService.stopListening();
      enhancedVoiceService.stopNarration();
    };
  }, []);

  const handleVoicePress = async () => {
    if (isListening) {
      await voiceRecognitionService.stopListening();
      setIsListening(false);
      
      // Process the transcript
      if (transcript) {
        await handleVoiceCommand(transcript);
      }
    } else {
      setTranscript('');
      setIsListening(true);
      await voiceRecognitionService.startListening();
    }
  };

  const handleVoiceCommand = async (command: string) => {
    // Simple command processing
    const lowerCommand = command.toLowerCase();
    
    if (lowerCommand.includes('next story')) {
      setCurrentStory((prev) => (prev + 1) % DEMO_STORIES.length);
      await playCurrentStory();
    } else if (lowerCommand.includes('change voice') || lowerCommand.includes('switch personality')) {
      // Cycle through personalities
      const currentIndex = PERSONALITIES.findIndex(p => p.id === selectedPersonality);
      const nextIndex = (currentIndex + 1) % PERSONALITIES.length;
      await selectPersonality(PERSONALITIES[nextIndex].id);
    } else {
      // Default: speak the command back
      await enhancedVoiceService.synthesizeSpeech(
        `You said: ${command}`,
        { immediate: true }
      );
    }
  };

  const selectPersonality = async (personalityId: string) => {
    try {
      setSelectedPersonality(personalityId);
      await enhancedVoiceService.setPersonality(personalityId);
      
      // Announce the change
      const personality = PERSONALITIES.find(p => p.id === personalityId);
      if (personality) {
        await enhancedVoiceService.synthesizeSpeech(
          `Voice changed to ${personality.name}. ${personality.description}`,
          { immediate: true }
        );
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to change voice personality');
    }
  };

  const playCurrentStory = async () => {
    try {
      setIsSpeaking(true);
      const story = DEMO_STORIES[currentStory];
      await enhancedVoiceService.startStoryNarration({
        ...story,
        relatedStories: [],
      });
      setIsSpeaking(false);
    } catch (error) {
      setIsSpeaking(false);
      Alert.alert('Error', 'Failed to play story');
    }
  };

  const renderPersonalityCard = (personality: PersonalityOption, index: number) => {
    const isSelected = selectedPersonality === personality.id;
    
    return (
      <Animated.View
        key={personality.id}
        entering={ZoomIn.delay(index * 50)}
        layout={Layout.springify()}
      >
        <TouchableOpacity
          onPress={() => selectPersonality(personality.id)}
          activeOpacity={0.8}
        >
          <View style={[
            styles.personalityCard,
            isSelected && styles.personalityCardSelected,
          ]}>
            <LinearGradient
              colors={personality.gradient}
              style={styles.personalityGradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
            >
              <Text style={styles.personalityIcon}>{personality.icon}</Text>
            </LinearGradient>
            <View style={styles.personalityInfo}>
              <Text style={[
                styles.personalityName,
                isSelected && styles.personalityNameSelected,
              ]}>
                {personality.name}
              </Text>
              <Text style={styles.personalityDescription}>
                {personality.description}
              </Text>
            </View>
            {isSelected && (
              <View style={styles.selectedIndicator}>
                <View style={styles.selectedDot} />
              </View>
            )}
          </View>
        </TouchableOpacity>
      </Animated.View>
    );
  };

  const renderCategory = (category: string, personalities: PersonalityOption[]) => (
    <View key={category} style={styles.categorySection}>
      <Text style={styles.categoryTitle}>
        {category.charAt(0).toUpperCase() + category.slice(1)} Personalities
      </Text>
      <View style={styles.personalityGrid}>
        {personalities.map((p, i) => renderPersonalityCard(p, i))}
      </View>
    </View>
  );

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
        <Animated.View 
          entering={FadeInDown.delay(100)}
          style={styles.header}
        >
          <Text style={styles.title}>Voice Personalities</Text>
          <Text style={styles.subtitle}>
            Choose your AI companion's voice
          </Text>
        </Animated.View>

        {/* Voice Interaction */}
        <Animated.View 
          entering={FadeInDown.delay(200)}
          style={styles.voiceSection}
        >
          <VoiceButton
            isListening={isListening}
            onPress={handleVoicePress}
            transcript={transcript}
          />
          <Text style={styles.voiceHint}>
            Try saying "Change voice" or "Next story"
          </Text>
        </Animated.View>

        {/* Current Story */}
        <Animated.View 
          entering={FadeInDown.delay(300)}
          style={styles.storySection}
        >
          <StoryCard
            {...DEMO_STORIES[currentStory]}
            narrator={PERSONALITIES.find(p => p.id === selectedPersonality)?.name}
            isPlaying={isSpeaking}
            onPress={playCurrentStory}
          />
        </Animated.View>

        {/* Personality Categories */}
        <Animated.View entering={FadeInUp.delay(400)}>
          {['core', 'event', 'seasonal', 'regional'].map((category) => 
            renderCategory(
              category,
              PERSONALITIES.filter(p => p.category === category)
            )
          )}
        </Animated.View>

        {/* Cache Info */}
        <Animated.View 
          entering={FadeInUp.delay(500)}
          style={styles.cacheInfo}
        >
          <Text style={styles.cacheText}>
            Cache Size: {(enhancedVoiceService.getCacheSize() / 1024 / 1024).toFixed(1)} MB
          </Text>
          <TouchableOpacity
            onPress={() => enhancedVoiceService.clearCache()}
            style={styles.clearCacheButton}
          >
            <Text style={styles.clearCacheText}>Clear Cache</Text>
          </TouchableOpacity>
        </Animated.View>
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
    paddingBottom: theme.spacing.xxxl,
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
  voiceSection: {
    alignItems: 'center',
    paddingVertical: theme.spacing.xl,
  },
  voiceHint: {
    ...theme.typography.bodyMedium,
    color: theme.colors.text.secondary,
    marginTop: theme.spacing.md,
    fontStyle: 'italic',
  },
  storySection: {
    paddingHorizontal: theme.spacing.md,
    marginBottom: theme.spacing.xl,
    alignItems: 'center',
  },
  categorySection: {
    paddingHorizontal: theme.spacing.md,
    marginBottom: theme.spacing.xl,
  },
  categoryTitle: {
    ...theme.typography.headlineSmall,
    color: theme.colors.text.inverse,
    marginBottom: theme.spacing.md,
  },
  personalityGrid: {
    gap: theme.spacing.md,
  },
  personalityCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface.card,
    borderRadius: theme.layout.borderRadius.lg,
    padding: theme.spacing.md,
    ...theme.elevation.low,
  },
  personalityCardSelected: {
    backgroundColor: theme.colors.primary[900],
    ...theme.elevation.medium,
  },
  personalityGradient: {
    width: 56,
    height: 56,
    borderRadius: theme.layout.borderRadius.full,
    alignItems: 'center',
    justifyContent: 'center',
  },
  personalityIcon: {
    fontSize: 28,
  },
  personalityInfo: {
    flex: 1,
    marginLeft: theme.spacing.md,
  },
  personalityName: {
    ...theme.typography.titleMedium,
    color: theme.colors.text.primary,
  },
  personalityNameSelected: {
    color: theme.colors.text.inverse,
  },
  personalityDescription: {
    ...theme.typography.bodySmall,
    color: theme.colors.text.secondary,
    marginTop: 2,
  },
  selectedIndicator: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: theme.colors.primary[500],
    alignItems: 'center',
    justifyContent: 'center',
  },
  selectedDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: theme.colors.text.inverse,
  },
  cacheInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: theme.spacing.md,
    paddingTop: theme.spacing.xl,
  },
  cacheText: {
    ...theme.typography.bodyMedium,
    color: theme.colors.text.secondary,
  },
  clearCacheButton: {
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
    borderRadius: theme.layout.borderRadius.md,
    backgroundColor: theme.colors.primary[800],
  },
  clearCacheText: {
    ...theme.typography.labelMedium,
    color: theme.colors.primary[300],
  },
});