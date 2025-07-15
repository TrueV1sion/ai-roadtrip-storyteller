import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Animated,
  Alert,
  ActivityIndicator,
  SafeAreaView
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { 
  triviaGameEngine, 
  TriviaGame as TriviaGameType,
  TriviaQuestion,
  TriviaResult,
  TriviaCategory
} from '../../services/gameEngine/TriviaGameEngine';
import { gameStateManager, GameDifficulty } from '../../services/gameEngine/GameStateManager';
import { locationService, LocationData } from '../../services/locationService';

interface TriviaGameProps {
  onClose: () => void;
  difficulty?: GameDifficulty;
  categories?: string[];
  questionCount?: number;
  location?: LocationData;
}

const TriviaGameComponent: React.FC<TriviaGameProps> = ({
  onClose,
  difficulty = GameDifficulty.MEDIUM,
  categories,
  questionCount = 5,
  location: initialLocation
}) => {
  // Game state
  const [game, setGame] = useState<TriviaGameType | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<TriviaQuestion | null>(null);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [isAnswerCorrect, setIsAnswerCorrect] = useState<boolean | null>(null);
  const [result, setResult] = useState<TriviaResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeLeft, setTimeLeft] = useState<number>(0);
  const [currentLocation, setCurrentLocation] = useState<LocationData | null>(initialLocation || null);
  
  // Animation values
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;
  const timerAnim = useRef(new Animated.Value(1)).current;
  const timerInterval = useRef<NodeJS.Timeout | null>(null);
  
  // Initialize the game
  useEffect(() => {
    const initGame = async () => {
      setLoading(true);
      
      // Get current location if not provided
      let gameLocation = currentLocation;
      if (!gameLocation) {
        try {
          gameLocation = await locationService.getCurrentLocation();
          
          // Fall back to simulated location if needed
          if (!gameLocation) {
            gameLocation = locationService.getSimulatedLocation();
          }
          
          setCurrentLocation(gameLocation);
        } catch (error) {
          console.error('Error getting location:', error);
          gameLocation = locationService.getSimulatedLocation();
          setCurrentLocation(gameLocation);
        }
      }
      
      // Generate a new game
      const newGame = triviaGameEngine.generateGame(
        gameLocation,
        difficulty,
        questionCount,
        categories
      );
      
      // Update state
      setGame(newGame);
      setCurrentQuestion(newGame.questions[0]);
      setTimeLeft(newGame.questions[0].timeLimit || 30);
      setLoading(false);
      
      // Start animations
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 500,
          useNativeDriver: true
        }),
        Animated.timing(slideAnim, {
          toValue: 0,
          duration: 500,
          useNativeDriver: true
        })
      ]).start();
    };
    
    initGame();
    
    // Clean up
    return () => {
      if (timerInterval.current) {
        clearInterval(timerInterval.current);
      }
    };
  }, []);
  
  // Set up timer for current question
  useEffect(() => {
    if (!currentQuestion || loading || showExplanation) return;
    
    // Reset timer animation
    timerAnim.setValue(1);
    
    // Animate timer bar
    Animated.timing(timerAnim, {
      toValue: 0,
      duration: (currentQuestion.timeLimit || 30) * 1000,
      useNativeDriver: false
    }).start();
    
    // Set up countdown timer
    timerInterval.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          // Time's up, automatically skip
          clearInterval(timerInterval.current!);
          handleSkip();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    return () => {
      if (timerInterval.current) {
        clearInterval(timerInterval.current);
      }
    };
  }, [currentQuestion, loading, showExplanation]);
  
  // Handle option selection
  const handleSelectOption = (index: number) => {
    if (selectedOption !== null || showExplanation) return;
    
    setSelectedOption(index);
    
    // Stop timer
    if (timerInterval.current) {
      clearInterval(timerInterval.current);
    }
    
    // Check if answer is correct
    const isCorrect = triviaGameEngine.answerQuestion(index);
    setIsAnswerCorrect(isCorrect);
    
    // Show explanation
    setShowExplanation(true);
    
    // Schedule next question after delay
    setTimeout(() => {
      moveToNextQuestion();
    }, 3000);
  };
  
  // Handle skipping a question
  const handleSkip = () => {
    if (showExplanation) return;
    
    // Stop timer
    if (timerInterval.current) {
      clearInterval(timerInterval.current);
    }
    
    triviaGameEngine.skipQuestion();
    setSelectedOption(null);
    setIsAnswerCorrect(null);
    
    // Move to next question immediately
    moveToNextQuestion();
  };
  
  // Move to the next question
  const moveToNextQuestion = () => {
    const updatedGame = triviaGameEngine.getActiveGame();
    
    if (!updatedGame || updatedGame.isCompleted) {
      // Game is over, show results
      const gameResult = triviaGameEngine.completeGame();
      setResult(gameResult);
      return;
    }
    
    // Reset state for next question
    setSelectedOption(null);
    setIsAnswerCorrect(null);
    setShowExplanation(false);
    
    // Get the next question
    const nextQuestion = updatedGame.questions[updatedGame.currentQuestionIndex];
    
    // Animate transition
    Animated.sequence([
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true
        }),
        Animated.timing(slideAnim, {
          toValue: -50,
          duration: 300,
          useNativeDriver: true
        })
      ]),
      Animated.timing(slideAnim, {
        toValue: 50,
        duration: 0,
        useNativeDriver: true
      })
    ]).start(() => {
      // Update question
      setCurrentQuestion(nextQuestion);
      setTimeLeft(nextQuestion.timeLimit || 30);
      
      // Animate in
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true
        }),
        Animated.timing(slideAnim, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true
        })
      ]).start();
    });
  };
  
  // Handle play again
  const handlePlayAgain = () => {
    setResult(null);
    setGame(null);
    setCurrentQuestion(null);
    setLoading(true);
    
    // Initialize a new game
    setTimeout(() => {
      if (currentLocation) {
        const newGame = triviaGameEngine.generateGame(
          currentLocation,
          difficulty,
          questionCount,
          categories
        );
        
        setGame(newGame);
        setCurrentQuestion(newGame.questions[0]);
        setTimeLeft(newGame.questions[0].timeLimit || 30);
        setLoading(false);
      }
    }, 500);
  };
  
  // Render loading state
  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#f4511e" />
          <Text style={styles.loadingText}>Preparing your trivia game...</Text>
        </View>
      </SafeAreaView>
    );
  }
  
  // Render results
  if (result) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Game Results</Text>
          <TouchableOpacity style={styles.closeButton} onPress={onClose}>
            <Ionicons name="close" size={24} color="#fff" />
          </TouchableOpacity>
        </View>
        
        <ScrollView style={styles.scrollContainer}>
          <View style={styles.resultContainer}>
            <View style={styles.scoreCircle}>
              <Text style={styles.scoreText}>{result.score}</Text>
              <Text style={styles.scoreMaxText}>/{result.maxScore}</Text>
            </View>
            
            <Text style={styles.percentageText}>
              {result.percentageCorrect.toFixed(0)}% Correct
            </Text>
            
            <View style={styles.statsContainer}>
              <View style={styles.statItem}>
                <Ionicons name="checkmark-circle" size={22} color="#28A745" />
                <Text style={styles.statText}>{result.correctAnswers} Correct</Text>
              </View>
              
              <View style={styles.statItem}>
                <Ionicons name="close-circle" size={22} color="#DC3545" />
                <Text style={styles.statText}>{result.incorrectAnswers} Incorrect</Text>
              </View>
              
              <View style={styles.statItem}>
                <Ionicons name="help-circle" size={22} color="#6C757D" />
                <Text style={styles.statText}>{result.skippedAnswers} Skipped</Text>
              </View>
            </View>
            
            <View style={styles.timeContainer}>
              <Ionicons name="time-outline" size={22} color="#6C757D" />
              <Text style={styles.timeText}>
                Time: {Math.floor(result.timeSpentSeconds / 60)}m {result.timeSpentSeconds % 60}s
              </Text>
            </View>
            
            <View style={styles.buttonContainer}>
              <TouchableOpacity style={styles.playAgainButton} onPress={handlePlayAgain}>
                <Text style={styles.playAgainText}>Play Again</Text>
              </TouchableOpacity>
              
              <TouchableOpacity style={styles.exitButton} onPress={onClose}>
                <Text style={styles.exitText}>Exit</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }
  
  // Render game
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>
          {game ? `Question ${game.currentQuestionIndex + 1}/${game.questions.length}` : 'Trivia'}
        </Text>
        <TouchableOpacity testID="close-button" style={styles.closeButton} onPress={() => {
          Alert.alert(
            'Quit Game',
            'Are you sure you want to quit? Your progress will be lost.',
            [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Quit', style: 'destructive', onPress: onClose }
            ]
          );
        }}>
          <Ionicons name="close" size={24} color="#fff" />
        </TouchableOpacity>
      </View>
      
      {/* Timer bar */}
      <Animated.View
        style={[
          styles.timerBar,
          {
            width: timerAnim.interpolate({
              inputRange: [0, 1],
              outputRange: ['0%', '100%']
            }),
            backgroundColor: timerAnim.interpolate({
              inputRange: [0, 0.2, 0.5, 1],
              outputRange: ['#DC3545', '#FFC107', '#28A745', '#28A745']
            })
          }
        ]}
      />
      
      <ScrollView style={styles.scrollContainer}>
        {currentQuestion && (
          <Animated.View
            style={[
              styles.questionContainer,
              {
                opacity: fadeAnim,
                transform: [{ translateY: slideAnim }]
              }
            ]}
          >
            {/* Category badge */}
            <View style={styles.categoryBadge}>
              <Text style={styles.categoryText}>
                {currentQuestion.category.toUpperCase()}
              </Text>
            </View>
            
            {/* Question */}
            <Text style={styles.questionText}>{currentQuestion.question}</Text>
            
            {/* Options */}
            <View style={styles.optionsContainer}>
              {currentQuestion.options.map((option, index) => (
                <TouchableOpacity
                  key={index}
                  style={[
                    styles.optionButton,
                    selectedOption === index && styles.selectedOption,
                    showExplanation && index === currentQuestion.correctOptionIndex && styles.correctOption,
                    showExplanation && selectedOption === index && selectedOption !== currentQuestion.correctOptionIndex && styles.incorrectOption
                  ]}
                  onPress={() => handleSelectOption(index)}
                  disabled={selectedOption !== null || showExplanation}
                >
                  <Text style={[
                    styles.optionText,
                    selectedOption === index && styles.selectedOptionText,
                    showExplanation && index === currentQuestion.correctOptionIndex && styles.correctOptionText,
                    showExplanation && selectedOption === index && selectedOption !== currentQuestion.correctOptionIndex && styles.incorrectOptionText
                  ]}>
                    {String.fromCharCode(65 + index)}. {option}
                  </Text>
                  
                  {showExplanation && index === currentQuestion.correctOptionIndex && (
                    <Ionicons name="checkmark-circle" size={22} color="#fff" style={styles.optionIcon} />
                  )}
                  
                  {showExplanation && selectedOption === index && selectedOption !== currentQuestion.correctOptionIndex && (
                    <Ionicons name="close-circle" size={22} color="#fff" style={styles.optionIcon} />
                  )}
                </TouchableOpacity>
              ))}
            </View>
            
            {/* Explanation */}
            {showExplanation && currentQuestion.explanation && (
              <View style={styles.explanationContainer}>
                <Text style={styles.explanationTitle}>
                  {isAnswerCorrect ? 'Correct!' : 'Incorrect!'}
                </Text>
                <Text style={styles.explanationText}>{currentQuestion.explanation}</Text>
              </View>
            )}
            
            {/* Skip button */}
            {!showExplanation && (
              <TouchableOpacity style={styles.skipButton} onPress={handleSkip}>
                <Text style={styles.skipText}>Skip</Text>
              </TouchableOpacity>
            )}
            
            {/* Timer */}
            <View style={styles.timerContainer}>
              <Ionicons name="time-outline" size={18} color="#6C757D" />
              <Text style={styles.timerText}>{timeLeft}s</Text>
            </View>
          </Animated.View>
        )}
      </ScrollView>
    </SafeAreaView>
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
    paddingVertical: 16,
    paddingHorizontal: 20,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    flex: 1,
    textAlign: 'center',
  },
  closeButton: {
    position: 'absolute',
    right: 12,
  },
  timerBar: {
    height: 6,
    backgroundColor: '#28A745',
  },
  scrollContainer: {
    flex: 1,
  },
  questionContainer: {
    padding: 20,
    marginBottom: 20,
  },
  categoryBadge: {
    backgroundColor: '#3498db',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
    alignSelf: 'flex-start',
    marginBottom: 12,
  },
  categoryText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
  questionText: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 24,
    color: '#333',
  },
  optionsContainer: {
    marginBottom: 20,
  },
  optionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
  },
  selectedOption: {
    backgroundColor: '#f4511e',
    borderColor: '#f4511e',
  },
  correctOption: {
    backgroundColor: '#28A745',
    borderColor: '#28A745',
  },
  incorrectOption: {
    backgroundColor: '#DC3545',
    borderColor: '#DC3545',
  },
  optionText: {
    fontSize: 16,
    color: '#333',
    flex: 1,
  },
  selectedOptionText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  correctOptionText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  incorrectOptionText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  optionIcon: {
    marginLeft: 8,
  },
  explanationContainer: {
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    padding: 16,
    marginTop: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  explanationTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
  },
  explanationText: {
    fontSize: 14,
    color: '#555',
    lineHeight: 20,
  },
  skipButton: {
    alignItems: 'center',
    backgroundColor: '#6C757D',
    padding: 12,
    borderRadius: 8,
    marginTop: 12,
  },
  skipText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  timerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    marginTop: 16,
  },
  timerText: {
    color: '#6C757D',
    fontSize: 14,
    marginLeft: 4,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#555',
  },
  resultContainer: {
    padding: 20,
    alignItems: 'center',
  },
  scoreCircle: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: '#f4511e',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
    flexDirection: 'row',
  },
  scoreText: {
    fontSize: 40,
    fontWeight: 'bold',
    color: '#fff',
  },
  scoreMaxText: {
    fontSize: 20,
    color: '#fff',
    opacity: 0.8,
    marginTop: 8,
  },
  percentageText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 20,
  },
  statsContainer: {
    width: '100%',
    marginBottom: 20,
  },
  statItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
    elevation: 1,
  },
  statText: {
    fontSize: 16,
    marginLeft: 8,
    color: '#333',
  },
  timeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 30,
  },
  timeText: {
    fontSize: 16,
    marginLeft: 8,
    color: '#6C757D',
  },
  buttonContainer: {
    flexDirection: 'row',
    width: '100%',
    justifyContent: 'space-between',
  },
  playAgainButton: {
    backgroundColor: '#f4511e',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    flex: 1,
    marginRight: 8,
    alignItems: 'center',
  },
  playAgainText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  exitButton: {
    backgroundColor: '#6C757D',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    flex: 1,
    marginLeft: 8,
    alignItems: 'center',
  },
  exitText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default TriviaGameComponent;
