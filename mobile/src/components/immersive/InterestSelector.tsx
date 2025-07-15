import React, { useState, useCallback } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import {
  Text,
  Chip,
  TextInput,
  Button,
  Surface,
  IconButton,
  ProgressBar,
} from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';
import { COLORS, SPACING } from '../../theme';

interface InterestSelectorProps {
  currentInterests: string[];
  onUpdateInterests: (interests: string[]) => Promise<void>;
}

// Predefined interest categories
const INTEREST_CATEGORIES = {
  history: [
    'Ancient Civilizations',
    'Medieval History',
    'Modern History',
    'Military History',
    'Cultural Heritage',
    'Architecture',
    'Art History',
    'Local Legends',
  ],
  nature: [
    'Wildlife',
    'Plants',
    'Geology',
    'Weather',
    'Conservation',
    'Natural Wonders',
    'Ecosystems',
    'Astronomy',
  ],
  culture: [
    'Local Customs',
    'Food & Cuisine',
    'Music',
    'Art',
    'Festivals',
    'Traditional Crafts',
    'Languages',
    'Fashion',
  ],
  adventure: [
    'Hiking',
    'Exploration',
    'Adventure Sports',
    'Hidden Gems',
    'Urban Exploration',
    'Road Trips',
    'Photography',
    'Travel Tips',
  ],
  science: [
    'Physics',
    'Chemistry',
    'Biology',
    'Technology',
    'Space',
    'Innovation',
    'Engineering',
    'Environmental Science',
  ],
};

export const InterestSelector: React.FC<InterestSelectorProps> = ({
  currentInterests,
  onUpdateInterests,
}) => {
  const [selectedInterests, setSelectedInterests] = useState<string[]>(
    currentInterests
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<keyof typeof INTEREST_CATEGORIES>(
    'history'
  );

  // Calculate interest distribution
  const interestDistribution = Object.entries(INTEREST_CATEGORIES).map(
    ([category, interests]) => ({
      category,
      count: selectedInterests.filter(i => interests.includes(i)).length,
      total: interests.length,
    })
  );

  // Handle interest selection
  const toggleInterest = useCallback((interest: string) => {
    setSelectedInterests(current =>
      current.includes(interest)
        ? current.filter(i => i !== interest)
        : [...current, interest]
    );
  }, []);

  // Filter interests based on search
  const filteredInterests = searchQuery
    ? Object.values(INTEREST_CATEGORIES)
        .flat()
        .filter(interest =>
          interest.toLowerCase().includes(searchQuery.toLowerCase())
        )
    : INTEREST_CATEGORIES[activeCategory];

  // Save changes
  const handleSave = useCallback(async () => {
    await onUpdateInterests(selectedInterests);
  }, [selectedInterests, onUpdateInterests]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Customize Your Experience</Text>
      <Text style={styles.subtitle}>
        Select your interests to personalize stories and music
      </Text>

      {/* Search Bar */}
      <Surface style={styles.searchBar}>
        <MaterialIcons name="search" size={24} color={COLORS.textSecondary} />
        <TextInput
          placeholder="Search interests..."
          value={searchQuery}
          onChangeText={setSearchQuery}
          style={styles.searchInput}
        />
      </Surface>

      {/* Category Tabs */}
      {!searchQuery && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.categoryTabs}
        >
          {Object.entries(INTEREST_CATEGORIES).map(([category, interests]) => {
            const { count } = interestDistribution.find(
              d => d.category === category
            ) || { count: 0 };
            
            return (
              <TouchableOpacity
                key={category}
                onPress={() => setActiveCategory(category as keyof typeof INTEREST_CATEGORIES)}
                style={[
                  styles.categoryTab,
                  activeCategory === category && styles.activeTab,
                ]}
              >
                <Text
                  style={[
                    styles.categoryText,
                    activeCategory === category && styles.activeText,
                  ]}
                >
                  {category.charAt(0).toUpperCase() + category.slice(1)}
                </Text>
                {count > 0 && (
                  <View style={styles.badge}>
                    <Text style={styles.badgeText}>{count}</Text>
                  </View>
                )}
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      )}

      {/* Interest Distribution */}
      <View style={styles.distribution}>
        {interestDistribution.map(({ category, count, total }) => (
          <View key={category} style={styles.distributionItem}>
            <Text style={styles.distributionLabel}>
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </Text>
            <ProgressBar
              progress={count / total}
              style={styles.distributionBar}
              color={COLORS.primary}
            />
          </View>
        ))}
      </View>

      {/* Interest Chips */}
      <ScrollView style={styles.interestList}>
        <View style={styles.chipContainer}>
          {filteredInterests.map(interest => (
            <Chip
              key={interest}
              selected={selectedInterests.includes(interest)}
              onPress={() => toggleInterest(interest)}
              style={styles.chip}
              selectedColor={COLORS.primary}
            >
              {interest}
            </Chip>
          ))}
        </View>
      </ScrollView>

      {/* Action Buttons */}
      <View style={styles.actions}>
        <Button
          mode="outlined"
          onPress={() => setSelectedInterests([])}
          style={styles.clearButton}
        >
          Clear All
        </Button>
        <Button
          mode="contained"
          onPress={handleSave}
          style={styles.saveButton}
        >
          Save Changes
        </Button>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: SPACING.xsmall,
  },
  subtitle: {
    fontSize: 16,
    color: COLORS.textSecondary,
    marginBottom: SPACING.medium,
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: SPACING.small,
    marginBottom: SPACING.medium,
    borderRadius: 8,
  },
  searchInput: {
    flex: 1,
    marginLeft: SPACING.small,
    backgroundColor: 'transparent',
  },
  categoryTabs: {
    flexGrow: 0,
    marginBottom: SPACING.medium,
  },
  categoryTab: {
    paddingHorizontal: SPACING.medium,
    paddingVertical: SPACING.small,
    marginRight: SPACING.small,
    borderRadius: 20,
    backgroundColor: COLORS.surface,
    flexDirection: 'row',
    alignItems: 'center',
  },
  activeTab: {
    backgroundColor: COLORS.primary,
  },
  categoryText: {
    color: COLORS.text,
  },
  activeText: {
    color: COLORS.white,
    fontWeight: 'bold',
  },
  badge: {
    backgroundColor: COLORS.error,
    borderRadius: 10,
    minWidth: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: SPACING.xsmall,
  },
  badgeText: {
    color: COLORS.white,
    fontSize: 12,
    fontWeight: 'bold',
  },
  distribution: {
    marginBottom: SPACING.medium,
  },
  distributionItem: {
    marginBottom: SPACING.small,
  },
  distributionLabel: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginBottom: SPACING.xsmall,
  },
  distributionBar: {
    height: 4,
    borderRadius: 2,
  },
  interestList: {
    flex: 1,
  },
  chipContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: SPACING.small,
  },
  chip: {
    margin: SPACING.xsmall,
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: SPACING.medium,
  },
  clearButton: {
    flex: 1,
    marginRight: SPACING.small,
  },
  saveButton: {
    flex: 1,
    marginLeft: SPACING.small,
  },
});

export default InterestSelector; 