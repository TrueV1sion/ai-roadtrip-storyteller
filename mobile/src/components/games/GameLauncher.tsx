import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  FlatList,
  Image,
  ActivityIndicator,
  Alert,
  Platform
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { gameStateManager, GameType, GameDifficulty } from '../../services/gameEngine/GameStateManager';
import { triviaGameEngine } from '../../services/gameEngine/TriviaGameEngine';
import TriviaGame from './TriviaGame';
import { locationService, LocationData } from '../../services/locationService';
import { locationBasedTriggers, TriggeredEvent } from '../../services/gameEngine/LocationBasedTriggers';

interface GameLauncherProps {
  visible: boolean;
  onClose: () => void;
  initialGameType?: GameType;
  location?: LocationData;
}

interface GameOption {
  type: GameType;
  title: string;
  description: string;
  icon: string;
  available: boolean;
  difficulty?: GameDifficulty;
  comingSoon?: boolean;
}

const GameLauncher: React.FC<GameLauncherProps> = ({
  visible,
  onClose,
  initialGameType,
  location: initialLocation
}) => {
  // State
  const [selectedGame, setSelectedGame] = useState<GameType | null>(initialGameType || null);
  const [gameStarted, setGameStarted] = useState(false);
  const [currentLocation, setCurrentLocation] = useState<LocationData | null>(initialLocation || null);
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState<{ id: string, name: string, description: string, icon: string }[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [difficulty, setDifficulty] = useState<GameDifficulty>(GameDifficulty.MEDIUM);
  const [questionCount, setQuestionCount] = useState<number>(5);
  const [showCategorySelector, setShowCategorySelector] = useState(false);
  
  // Game options
  const gameOptions: GameOption[] = [
    {
      type: GameType.TRIVIA,
      title: 'Location Trivia',
      description: 'Test your knowledge of this area with fun trivia questions',
      icon: 'help-circle-outline',
      available: true
    },
    {
      type: GameType.SCAVENGER_HUNT,
      title: 'Scavenger Hunt',
      description: 'Search for hidden items at this location',
      icon: 'search-outline',
      available: false,
      comingSoon: true
    },
    {
      type: GameType.STORY_ADVENTURE,
      title: 'Story Adventure',
      description: 'Embark on an interactive story adventure',
      icon: 'book-outline',
      available: false,
      comingSoon: true
    }
  ];
  
  // Get available game types from state manager
  const availableGames = gameStateManager.getState().unlockedGameTypes;
  
  // Update available games
  useEffect(() => {
    // Mark games as available if they're unlocked
    gameOptions.forEach(option => {
      option.available = availableGames.includes(option.type);
    });
    
    // Get trivia categories
    if (triviaGameEngine) {
      setCategories(triviaGameEngine.getCategories());
    }
    
    // Initialize game state manager if needed
    gameStateManager.initialize();
    
    // Initialize location-based triggers
    initializeLocationTriggers();
    
    // Set initial location if not provided
    if (!currentLocation) {
      getLocation();
    }
  }, []);
  
  // Initialize location-based triggers
  const initializeLocationTriggers = async () => {
    await locationBasedTriggers.initialize();
    
    // Add callback for location triggers
    locationBasedTriggers.addCallback(handleLocationTrigger);
    
    // Start monitoring
    locationBasedTriggers.startMonitoring();
    
    // Add some sample POIs (in a real app, these would come from a backend)
    addSamplePOIs();
  };
  
  // Add sample points of interest
  const addSamplePOIs = () => {
    // These would be replaced with actual POIs from a backend
    if (currentLocation) {
      // Add a POI near the current location (+/- 0.01 degrees)
      const nearbyLatitude = currentLocation.latitude + (Math.random() * 0.02 - 0.01);
      const nearbyLongitude = currentLocation.longitude + (Math.random() * 0.02 - 0.01);
      
      // Add the POI
      const poiId = locationBasedTriggers.addPointOfInterest(
        'Historical Landmark',
        nearbyLatitude,
        nearbyLongitude,
        200, // 200 meter radius
        {
          type: 'historical',
          description: 'A significant historical landmark in this area'
        }
      );
      
      // Set up a game trigger
      locationBasedTriggers.setupGameTrigger(
        poiId,
        GameType.TRIVIA,
        {
          difficulty: GameDifficulty.MEDIUM,
          questionCount: 5,
          categories: ['history', 'landmarks']
        },
        false // Not one-time
      );
      
      console.log('Added sample POI and game trigger at', nearbyLatitude, nearbyLongitude);
    }
  };
  
  // Handle location triggers
  const handleLocationTrigger = (event: TriggeredEvent) => {
    console.log('Location trigger:', event);
    
    // Check if it's a game trigger
    if (event.action === 'start_game' && event.actionParams?.gameType) {
      const gameType = event.actionParams.gameType as GameType;
      
      // Show game notification
      Alert.alert(
        'Game Available!',
        `You're near a location with a ${gameType} game. Would you like to play?`,
        [
          {
            text: 'No thanks',
            style: 'cancel'
          },
          {
            text: 'Let\'s play!',
            onPress: () => {
              // Set game options from trigger
              if (gameType === GameType.TRIVIA && event.actionParams) {
                if (event.actionParams.difficulty) {
                  setDifficulty(event.actionParams.difficulty as GameDifficulty);
                }
                if (event.actionParams.questionCount) {
                  setQuestionCount(event.actionParams.questionCount as number);
                }
                if (event.actionParams.categories) {
                  setSelectedCategories(event.actionParams.categories as string[]);
                }
              }
              
              // Start the game
              setSelectedGame(gameType);
              setTimeout(() => setGameStarted(true), 300);
            }
          }
        ]
      );
    }
  };
  
  // Get current location
  const getLocation = async () => {
    try {
      const location = await locationService.getCurrentLocation();
      if (location) {
        setCurrentLocation(location);
      } else {
        // Use simulated location if can't get real location
        setCurrentLocation(locationService.getSimulatedLocation());
      }
    } catch (error) {
      console.error('Error getting location:', error);
      // Use simulated location as fallback
      setCurrentLocation(locationService.getSimulatedLocation());
    }
  };
  
  // Start selected game
  const startGame = () => {
    if (!selectedGame) return;
    
    // Ensure we have a location
    if (!currentLocation) {
      Alert.alert(
        'Location Required',
        'We need your location to provide a location-based game experience. Please enable location services and try again.',
        [
          { text: 'OK' }
        ]
      );
      return;
    }
    
    // Start the game
    setGameStarted(true);
  };
  
  // Handle game completion
  const handleGameClose = () => {
    setGameStarted(false);
    setSelectedGame(null);
    onClose();
  };
  
  // Toggle category selection
  const toggleCategory = (categoryId: string) => {
    if (selectedCategories.includes(categoryId)) {
      // Remove category
      setSelectedCategories(selectedCategories.filter(id => id !== categoryId));
    } else {
      // Add category
      setSelectedCategories([...selectedCategories, categoryId]);
    }
  };
  
  // Render game content
  const renderGameContent = () => {
    if (gameStarted && selectedGame === GameType.TRIVIA && currentLocation) {
      return (
        <TriviaGame
          onClose={handleGameClose}
          difficulty={difficulty}
          categories={selectedCategories.length > 0 ? selectedCategories : undefined}
          questionCount={questionCount}
          location={currentLocation}
        />
      );
    }
    
    return null;
  };
  
  // Render category selector modal
  const renderCategorySelector = () => (
    <Modal
      visible={showCategorySelector}
      transparent={true}
      animationType="slide"
      onRequestClose={() => setShowCategorySelector(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Select Categories</Text>
            <TouchableOpacity onPress={() => setShowCategorySelector(false)}>
              <Ionicons name="close" size={24} color="#333" />
            </TouchableOpacity>
          </View>
          
          <FlatList
            data={categories}
            keyExtractor={item => item.id}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={[
                  styles.categoryItem,
                  selectedCategories.includes(item.id) && styles.categoryItemSelected
                ]}
                onPress={() => toggleCategory(item.id)}
              >
                <Ionicons
                  name={item.icon as any}
                  size={24}
                  color={selectedCategories.includes(item.id) ? '#fff' : '#333'}
                />
                <View style={styles.categoryTextContainer}>
                  <Text style={[
                    styles.categoryTitle,
                    selectedCategories.includes(item.id) && styles.categoryTitleSelected
                  ]}>{item.name}</Text>
                  <Text style={[
                    styles.categoryDescription,
                    selectedCategories.includes(item.id) && styles.categoryDescriptionSelected
                  ]}>{item.description}</Text>
                </View>
                {selectedCategories.includes(item.id) && (
                  <Ionicons name="checkmark-circle" size={24} color="#fff" />
                )}
              </TouchableOpacity>
            )}
          />
          
          <TouchableOpacity
            style={styles.doneButton}
            onPress={() => setShowCategorySelector(false)}
          >
            <Text style={styles.doneButtonText}>Done</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
  
  // Main render
  if (gameStarted) {
    return renderGameContent();
  }
  
  return (
    <Modal
      visible={visible}
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Games</Text>
          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Ionicons name="close" size={24} color="#fff" />
          </TouchableOpacity>
        </View>
        
        <FlatList
          data={gameOptions}
          keyExtractor={item => item.type}
          contentContainerStyle={styles.gamesList}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[
                styles.gameCard,
                selectedGame === item.type && styles.gameCardSelected,
                !item.available && styles.gameCardDisabled
              ]}
              onPress={() => item.available && setSelectedGame(item.type)}
              disabled={!item.available}
            >
              <View style={styles.gameIconContainer}>
                <Ionicons
                  name={item.icon as any}
                  size={32}
                  color={selectedGame === item.type ? '#fff' : '#333'}
                />
              </View>
              <View style={styles.gameDetails}>
                <Text style={[
                  styles.gameTitle,
                  selectedGame === item.type && styles.gameTitleSelected
                ]}>{item.title}</Text>
                <Text style={[
                  styles.gameDescription,
                  selectedGame === item.type && styles.gameDescriptionSelected
                ]}>{item.description}</Text>
              </View>
              {item.comingSoon && (
                <View style={styles.comingSoonBadge}>
                  <Text style={styles.comingSoonText}>Coming Soon</Text>
                </View>
              )}
            </TouchableOpacity>
          )}
        />
        
        {selectedGame === GameType.TRIVIA && (
          <View style={styles.optionsContainer}>
            <Text style={styles.optionsTitle}>Game Options</Text>
            
            <View style={styles.optionRow}>
              <Text style={styles.optionLabel}>Difficulty:</Text>
              <View style={styles.difficultyOptions}>
                {Object.values(GameDifficulty).map(level => (
                  <TouchableOpacity
                    key={level}
                    style={[
                      styles.difficultyOption,
                      difficulty === level && styles.difficultyOptionSelected
                    ]}
                    onPress={() => setDifficulty(level)}
                  >
                    <Text style={[
                      styles.difficultyText,
                      difficulty === level && styles.difficultyTextSelected
                    ]}>{level.charAt(0).toUpperCase() + level.slice(1)}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
            
            <View style={styles.optionRow}>
              <Text style={styles.optionLabel}>Categories:</Text>
              <TouchableOpacity
                style={styles.categoriesButton}
                onPress={() => setShowCategorySelector(true)}
              >
                <Text style={styles.categoriesButtonText}>
                  {selectedCategories.length === 0
                    ? 'All Categories'
                    : `${selectedCategories.length} Selected`}
                </Text>
                <Ionicons name="chevron-forward" size={20} color="#f4511e" />
              </TouchableOpacity>
            </View>
            
            <View style={styles.optionRow}>
              <Text style={styles.optionLabel}>Questions:</Text>
              <View style={styles.questionsOptions}>
                {[5, 10, 15].map(count => (
                  <TouchableOpacity
                    key={count}
                    style={[
                      styles.questionCountOption,
                      questionCount === count && styles.questionCountOptionSelected
                    ]}
                    onPress={() => setQuestionCount(count)}
                  >
                    <Text style={[
                      styles.questionCountText,
                      questionCount === count && styles.questionCountTextSelected
                    ]}>{count}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          </View>
        )}
        
        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={[
              styles.startButton,
              !selectedGame && styles.startButtonDisabled
            ]}
            onPress={startGame}
            disabled={!selectedGame}
          >
            <Text style={styles.startButtonText}>Start Game</Text>
          </TouchableOpacity>
        </View>
        
        {renderCategorySelector()}
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7f9fc',
  },
  header: {
    backgroundColor: '#f4511e',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: Platform.OS === 'ios' ? 44 : 16,
    paddingBottom: 16,
    paddingHorizontal: 20,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  closeButton: {
    position: 'absolute',
    right: 20,
    top: Platform.OS === 'ios' ? 44 : 16,
  },
  gamesList: {
    padding: 16,
  },
  gameCard: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 2,
    borderColor: '#e0e0e0',
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
    position: 'relative',
  },
  gameCardSelected: {
    borderColor: '#f4511e',
    backgroundColor: '#f4511e',
  },
  gameCardDisabled: {
    opacity: 0.7,
  },
  gameIconContainer: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#f0f0f0',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  gameDetails: {
    flex: 1,
    justifyContent: 'center',
  },
  gameTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
    color: '#333',
  },
  gameTitleSelected: {
    color: '#fff',
  },
  gameDescription: {
    fontSize: 14,
    color: '#666',
  },
  gameDescriptionSelected: {
    color: '#fff',
    opacity: 0.9,
  },
  comingSoonBadge: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: '#ffc107',
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  comingSoonText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#333',
  },
  optionsContainer: {
    padding: 16,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  optionsTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#333',
  },
  optionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  optionLabel: {
    width: 100,
    fontSize: 16,
    color: '#333',
  },
  difficultyOptions: {
    flexDirection: 'row',
    flex: 1,
  },
  difficultyOption: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 4,
    marginHorizontal: 4,
    alignItems: 'center',
  },
  difficultyOptionSelected: {
    backgroundColor: '#f4511e',
    borderColor: '#f4511e',
  },
  difficultyText: {
    fontSize: 14,
    color: '#333',
  },
  difficultyTextSelected: {
    color: '#fff',
    fontWeight: 'bold',
  },
  categoriesButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 4,
  },
  categoriesButtonText: {
    fontSize: 14,
    color: '#f4511e',
  },
  questionsOptions: {
    flexDirection: 'row',
    flex: 1,
  },
  questionCountOption: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 4,
    marginHorizontal: 4,
    alignItems: 'center',
  },
  questionCountOptionSelected: {
    backgroundColor: '#f4511e',
    borderColor: '#f4511e',
  },
  questionCountText: {
    fontSize: 14,
    color: '#333',
  },
  questionCountTextSelected: {
    color: '#fff',
    fontWeight: 'bold',
  },
  buttonContainer: {
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    backgroundColor: '#fff',
  },
  startButton: {
    backgroundColor: '#f4511e',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  startButtonDisabled: {
    backgroundColor: '#ccc',
  },
  startButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    width: '90%',
    maxHeight: '80%',
    backgroundColor: '#fff',
    borderRadius: 16,
    overflow: 'hidden',
    padding: 0,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  categoryItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  categoryItemSelected: {
    backgroundColor: '#f4511e',
  },
  categoryTextContainer: {
    flex: 1,
    marginLeft: 16,
  },
  categoryTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  categoryTitleSelected: {
    color: '#fff',
  },
  categoryDescription: {
    fontSize: 14,
    color: '#666',
  },
  categoryDescriptionSelected: {
    color: '#fff',
    opacity: 0.9,
  },
  doneButton: {
    backgroundColor: '#f4511e',
    padding: 16,
    alignItems: 'center',
  },
  doneButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default GameLauncher;
