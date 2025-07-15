import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  TextInput
} from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { VoiceCharacterType } from '../../types/voice';
import CharacterCard from './CharacterCard';

interface CharacterSelectorProps {
  characters: VoiceCharacterType[];
  selectedCharacterId?: string;
  onSelectCharacter: (character: VoiceCharacterType) => void;
  onPlaySample?: (character: VoiceCharacterType) => void;
  loading?: boolean;
  onSearch?: (query: string) => void;
  onFilterByTheme?: (theme: string) => void;
}

const CharacterSelector: React.FC<CharacterSelectorProps> = ({
  characters,
  selectedCharacterId,
  onSelectCharacter,
  onPlaySample,
  loading = false,
  onSearch,
  onFilterByTheme
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredCharacters, setFilteredCharacters] = useState<VoiceCharacterType[]>(characters);
  const [activeTheme, setActiveTheme] = useState<string | null>(null);
  
  // Common themes
  const themes = [
    "adventure",
    "historical",
    "nature",
    "sci-fi",
    "modern",
    "professional",
    "pirate"
  ];
  
  // Update filtered characters when characters or search query changes
  useEffect(() => {
    if (!searchQuery && !activeTheme) {
      setFilteredCharacters(characters);
      return;
    }
    
    let filtered = characters;
    
    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(character => 
        character.name.toLowerCase().includes(query) ||
        character.description.toLowerCase().includes(query) ||
        (character.personality_traits && 
          character.personality_traits.some(trait => trait.toLowerCase().includes(query)))
      );
    }
    
    // Apply theme filter
    if (activeTheme) {
      filtered = filtered.filter(character => 
        character.theme_affinity && 
        character.theme_affinity.some(theme => 
          theme.toLowerCase() === activeTheme.toLowerCase()
        )
      );
    }
    
    setFilteredCharacters(filtered);
  }, [characters, searchQuery, activeTheme]);
  
  // Handle search query change
  const handleSearchChange = (text: string) => {
    setSearchQuery(text);
    
    if (onSearch) {
      onSearch(text);
    }
  };
  
  // Handle theme filter
  const handleThemeFilter = (theme: string) => {
    if (activeTheme === theme) {
      // Turn off the filter if the same theme is clicked
      setActiveTheme(null);
      
      if (onFilterByTheme) {
        onFilterByTheme('');
      }
    } else {
      setActiveTheme(theme);
      
      if (onFilterByTheme) {
        onFilterByTheme(theme);
      }
    }
  };
  
  return (
    <View style={styles.container}>
      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <MaterialIcons name="search" size={20} color="#757575" style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          placeholder="Search characters..."
          value={searchQuery}
          onChangeText={handleSearchChange}
        />
        {searchQuery !== '' && (
          <TouchableOpacity 
            style={styles.clearButton}
            onPress={() => handleSearchChange('')}
          >
            <MaterialIcons name="clear" size={20} color="#757575" />
          </TouchableOpacity>
        )}
      </View>
      
      {/* Theme Filters */}
      <FlatList
        horizontal
        data={themes}
        keyExtractor={(item) => item}
        showsHorizontalScrollIndicator={false}
        style={styles.themesContainer}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[
              styles.themeButton,
              activeTheme === item && styles.activeThemeButton
            ]}
            onPress={() => handleThemeFilter(item)}
          >
            <Text 
              style={[
                styles.themeButtonText,
                activeTheme === item && styles.activeThemeButtonText
              ]}
            >
              {item}
            </Text>
          </TouchableOpacity>
        )}
      />
      
      {/* Characters List */}
      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#2196F3" />
          <Text style={styles.loadingText}>Loading characters...</Text>
        </View>
      ) : filteredCharacters.length === 0 ? (
        <View style={styles.emptyContainer}>
          <MaterialIcons name="voice-over-off" size={48} color="#9E9E9E" />
          <Text style={styles.emptyText}>No characters found</Text>
          <TouchableOpacity 
            style={styles.resetButton}
            onPress={() => {
              setSearchQuery('');
              setActiveTheme(null);
              
              if (onSearch) {
                onSearch('');
              }
              
              if (onFilterByTheme) {
                onFilterByTheme('');
              }
            }}
          >
            <Text style={styles.resetButtonText}>Reset filters</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={filteredCharacters}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <CharacterCard
              character={item}
              selected={selectedCharacterId === item.id}
              onSelect={() => onSelectCharacter(item)}
              onPlaySample={onPlaySample ? () => onPlaySample(item) : undefined}
            />
          )}
          contentContainerStyle={styles.listContent}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    borderRadius: 8,
    marginHorizontal: 16,
    marginVertical: 10,
    paddingHorizontal: 10,
    paddingVertical: 5,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    height: 40,
    fontSize: 14,
  },
  clearButton: {
    padding: 5,
  },
  themesContainer: {
    maxHeight: 50,
    marginBottom: 10,
    paddingHorizontal: 16,
  },
  themeButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#f0f0f0',
    borderRadius: 16,
    marginRight: 8,
    marginBottom: 8,
  },
  activeThemeButton: {
    backgroundColor: '#2196F3',
  },
  themeButtonText: {
    fontSize: 12,
    color: '#757575',
    textTransform: 'capitalize',
  },
  activeThemeButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#757575',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  emptyText: {
    marginTop: 10,
    fontSize: 16,
    color: '#757575',
    marginBottom: 20,
  },
  resetButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: '#2196F3',
    borderRadius: 4,
  },
  resetButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  listContent: {
    paddingBottom: 20,
  },
});

export default CharacterSelector;