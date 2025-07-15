import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';
import { voicePersonalityService } from '../../services/voicePersonalityService';
import { VoicePersonality } from '../../types/voice';

interface PersonalitySelectorProps {
  onPersonalitySelect: (personality: VoicePersonality) => void;
  currentLocation?: { lat: number; lng: number; state?: string };
  selectedPersonalityId?: string;
}

export const PersonalitySelector: React.FC<PersonalitySelectorProps> = ({
  onPersonalitySelect,
  currentLocation,
  selectedPersonalityId,
}) => {
  const { user } = useAuth();
  const [personalities, setPersonalities] = useState<VoicePersonality[]>([]);
  const [activePersonality, setActivePersonality] = useState<VoicePersonality | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAllPersonalities, setShowAllPersonalities] = useState(false);

  useEffect(() => {
    loadPersonalities();
  }, [currentLocation]);

  const loadPersonalities = async () => {
    try {
      setLoading(true);
      const availablePersonalities = await voicePersonalityService.getAvailablePersonalities({
        location: currentLocation,
        userId: user?.id,
      });

      const contextualPersonality = await voicePersonalityService.getContextualPersonality({
        location: currentLocation,
        userPreferences: user?.preferences,
      });

      setPersonalities(availablePersonalities);
      setActivePersonality(contextualPersonality);

      if (!selectedPersonalityId && contextualPersonality) {
        onPersonalitySelect(contextualPersonality);
      }
    } catch (error) {
      console.error('Failed to load personalities:', error);
      Alert.alert('Error', 'Failed to load voice personalities');
    } finally {
      setLoading(false);
    }
  };

  const handlePersonalitySelect = (personality: VoicePersonality) => {
    setActivePersonality(personality);
    onPersonalitySelect(personality);
    
    // Play greeting sample
    voicePersonalityService.playGreetingSample(personality.id);
  };

  const getPersonalityIcon = (personalityId: string): string => {
    const iconMap: Record<string, string> = {
      friendly_guide: 'human-greeting',
      local_expert: 'map-marker-account',
      historian: 'book-open-variant',
      adventurer: 'hiking',
      comedian: 'emoticon-happy',
      santa: 'santa',
      halloween_narrator: 'ghost',
      cupid: 'heart',
      leprechaun: 'clover',
      patriot: 'flag',
      harvest_guide: 'corn',
      inspirational: 'white-balance-sunny',
      southern_charm: 'flower',
      texas_ranger: 'cowboy',
      new_england_scholar: 'school',
      midwest_neighbor: 'home-heart',
      west_coast_cool: 'surfing',
      mountain_sage: 'mountain',
      jazz_storyteller: 'saxophone',
      beach_vibes: 'beach',
    };

    return iconMap[personalityId] || 'account';
  };

  const renderPersonalityCard = (personality: VoicePersonality) => {
    const isActive = activePersonality?.id === personality.id;
    const isSpecial = personality.activeHolidays || personality.activeSeason;

    return (
      <TouchableOpacity
        key={personality.id}
        style={[
          styles.personalityCard,
          isActive && styles.activeCard,
          isSpecial && styles.specialCard,
        ]}
        onPress={() => handlePersonalitySelect(personality)}
      >
        <View style={styles.cardHeader}>
          <MaterialCommunityIcons
            name={getPersonalityIcon(personality.id)}
            size={32}
            color={isActive ? '#ffffff' : '#333333'}
          />
          {isSpecial && (
            <View style={styles.specialBadge}>
              <Text style={styles.specialBadgeText}>LIMITED</Text>
            </View>
          )}
        </View>
        
        <Text style={[styles.personalityName, isActive && styles.activeName]}>
          {personality.name}
        </Text>
        
        <Text style={[styles.personalityDescription, isActive && styles.activeDescription]}>
          {personality.description}
        </Text>

        {personality.catchphrases && personality.catchphrases.length > 0 && (
          <Text style={[styles.catchphrase, isActive && styles.activeCatchphrase]}>
            "{personality.catchphrases[0]}"
          </Text>
        )}

        {personality.regionalAccent && (
          <View style={styles.accentBadge}>
            <Text style={styles.accentText}>{personality.regionalAccent}</Text>
          </View>
        )}

        {isActive && (
          <View style={styles.activeIndicator}>
            <MaterialCommunityIcons name="check-circle" size={24} color="#ffffff" />
          </View>
        )}
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#0066cc" />
        <Text style={styles.loadingText}>Loading voice personalities...</Text>
      </View>
    );
  }

  // Separate special/seasonal personalities from regular ones
  const currentDate = new Date();
  const specialPersonalities = personalities.filter(p => {
    if (p.activeHolidays) {
      // Check if current date is within holiday period
      return voicePersonalityService.isHolidayActive(p.activeHolidays[0]);
    }
    return false;
  });

  const regularPersonalities = personalities.filter(p => !specialPersonalities.includes(p));
  const displayedPersonalities = showAllPersonalities ? regularPersonalities : regularPersonalities.slice(0, 6);

  return (
    <ScrollView style={styles.container}>
      {specialPersonalities.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>✨ Special Edition Voices</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.horizontalScroll}>
            {specialPersonalities.map(renderPersonalityCard)}
          </ScrollView>
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Voice Personalities</Text>
        <View style={styles.personalityGrid}>
          {displayedPersonalities.map(renderPersonalityCard)}
        </View>

        {regularPersonalities.length > 6 && (
          <TouchableOpacity
            style={styles.showMoreButton}
            onPress={() => setShowAllPersonalities(!showAllPersonalities)}
          >
            <Text style={styles.showMoreText}>
              {showAllPersonalities ? 'Show Less' : `Show ${regularPersonalities.length - 6} More`}
            </Text>
            <MaterialCommunityIcons
              name={showAllPersonalities ? 'chevron-up' : 'chevron-down'}
              size={24}
              color="#0066cc"
            />
          </TouchableOpacity>
        )}
      </View>

      {activePersonality && (
        <View style={styles.activePersonalityInfo}>
          <Text style={styles.activeInfoTitle}>Current Voice</Text>
          <Text style={styles.activeInfoName}>{activePersonality.name}</Text>
          <TouchableOpacity
            style={styles.previewButton}
            onPress={() => voicePersonalityService.playGreetingSample(activePersonality.id)}
          >
            <MaterialCommunityIcons name="play-circle" size={24} color="#ffffff" />
            <Text style={styles.previewButtonText}>Play Sample Greeting</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666666',
  },
  section: {
    marginVertical: 10,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333333',
    marginHorizontal: 15,
    marginBottom: 15,
  },
  horizontalScroll: {
    paddingHorizontal: 10,
  },
  personalityGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 10,
  },
  personalityCard: {
    width: '45%',
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 15,
    margin: '2.5%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  activeCard: {
    backgroundColor: '#0066cc',
  },
  specialCard: {
    borderWidth: 2,
    borderColor: '#ffd700',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  specialBadge: {
    backgroundColor: '#ffd700',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  specialBadgeText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#333333',
  },
  personalityName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333333',
    marginBottom: 5,
  },
  activeName: {
    color: '#ffffff',
  },
  personalityDescription: {
    fontSize: 12,
    color: '#666666',
    marginBottom: 8,
  },
  activeDescription: {
    color: '#e6f2ff',
  },
  catchphrase: {
    fontSize: 11,
    fontStyle: 'italic',
    color: '#999999',
    marginTop: 5,
  },
  activeCatchphrase: {
    color: '#cce0ff',
  },
  accentBadge: {
    backgroundColor: '#e6f2ff',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
    marginTop: 5,
    alignSelf: 'flex-start',
  },
  accentText: {
    fontSize: 10,
    color: '#0066cc',
    fontWeight: '600',
  },
  activeIndicator: {
    position: 'absolute',
    top: 10,
    right: 10,
  },
  showMoreButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 15,
    marginTop: 10,
  },
  showMoreText: {
    fontSize: 16,
    color: '#0066cc',
    marginRight: 5,
  },
  activePersonalityInfo: {
    backgroundColor: '#0066cc',
    borderRadius: 12,
    padding: 20,
    margin: 15,
    alignItems: 'center',
  },
  activeInfoTitle: {
    fontSize: 14,
    color: '#cce0ff',
    marginBottom: 5,
  },
  activeInfoName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 15,
  },
  previewButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0052a3',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
  },
  previewButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 8,
  },
});