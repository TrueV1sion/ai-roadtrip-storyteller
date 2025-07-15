import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  ActivityIndicator,
  Animated,
  Dimensions,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

import { Card, Button, Header } from '../components';
import { gameApi } from '../services/api/gameApi';
import { useAuth } from '../contexts/AuthContext';

const { width } = Dimensions.get('window');

interface TriviaQuestion {
  id: string;
  text: string;
  options: string[];
  time_limit: number;
  category: string;
  points: int;
}

interface GameSession {
  session_id: string;
  players: Array<{ id: string; name: string; score: number }>;
  leaderboard: Array<[string, number]>;
}

export const TriviaGameScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { user } = useAuth();
  
  const [session, setSession] = useState<GameSession | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<TriviaQuestion | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [timeRemaining, setTimeRemaining] = useState(30);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [score, setScore] = useState(0);
  const [streak, setStreak] = useState(0);
  const [loading, setLoading] = useState(true);
  const [answering, setAnswering] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [correctAnswer, setCorrectAnswer] = useState<string | null>(null);
  const [achievements, setAchievements] = useState<any[]>([]);
  
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const progressAnim = useRef(new Animated.Value(1)).current;

  // Initialize game session
  useEffect(() => {
    initializeGame();
  }, []);

  // Timer effect
  useEffect(() => {
    if (!currentQuestion || showResult || selectedAnswer) return;

    const timer = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          handleTimeUp();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    // Animate progress bar
    Animated.timing(progressAnim, {
      toValue: 0,
      duration: currentQuestion.time_limit * 1000,
      useNativeDriver: false,
    }).start();

    return () => clearInterval(timer);
  }, [currentQuestion, showResult, selectedAnswer]);

  const initializeGame = async () => {
    try {
      setLoading(true);
      
      // Create game session
      const sessionData = await gameApi.createSession({
        game_type: 'trivia',
        players: [{ id: user.id, name: user.name, age: user.age || 25 }],
        location: route.params?.location || { lat: 0, lng: 0, name: 'Unknown' },
        difficulty: route.params?.difficulty || 'medium',
      });
      
      setSession(sessionData);
      
      // Get first question
      await loadNextQuestion(sessionData.session_id);
    } catch (error) {
      console.error('Error initializing game:', error);
      Alert.alert('Error', 'Failed to start game');
      navigation.goBack();
    } finally {
      setLoading(false);
    }
  };

  const loadNextQuestion = async (sessionId: string) => {
    try {
      setShowResult(false);
      setSelectedAnswer(null);
      setCorrectAnswer(null);
      
      const question = await gameApi.getNextQuestion(sessionId);
      
      if (!question) {
        // Game over
        endGame();
        return;
      }
      
      setCurrentQuestion(question);
      setTimeRemaining(question.time_limit);
      progressAnim.setValue(1);
      
      // Animate question entrance
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
        Animated.spring(scaleAnim, {
          toValue: 1,
          friction: 8,
          tension: 40,
          useNativeDriver: true,
        }),
      ]).start();
    } catch (error) {
      console.error('Error loading question:', error);
      Alert.alert('Error', 'Failed to load question');
    }
  };

  const handleAnswerSelect = async (answer: string) => {
    if (selectedAnswer || answering) return;
    
    setSelectedAnswer(answer);
    setAnswering(true);
    
    const timeTaken = currentQuestion!.time_limit - timeRemaining;
    
    try {
      const result = await gameApi.submitAnswer(session!.session_id, {
        answer,
        time_taken: timeTaken,
      });
      
      setCorrectAnswer(result.correct_answer);
      setScore(result.player_score);
      setStreak(result.current_streak);
      setShowResult(true);
      
      // Handle new achievements
      if (result.new_achievements) {
        setAchievements(result.new_achievements);
        showAchievementAnimation(result.new_achievements);
      }
      
      // Show result for 2 seconds then load next question
      setTimeout(() => {
        setQuestionNumber((prev) => prev + 1);
        loadNextQuestion(session!.session_id);
      }, 2000);
    } catch (error) {
      console.error('Error submitting answer:', error);
      Alert.alert('Error', 'Failed to submit answer');
    } finally {
      setAnswering(false);
    }
  };

  const handleTimeUp = () => {
    if (!selectedAnswer && !showResult) {
      handleAnswerSelect(''); // Submit empty answer
    }
  };

  const endGame = async () => {
    try {
      const results = await gameApi.endSession(session!.session_id);
      
      navigation.navigate('GameResults', {
        results,
        gameType: 'trivia',
        score,
        streak,
        achievements,
      });
    } catch (error) {
      console.error('Error ending game:', error);
      navigation.goBack();
    }
  };

  const showAchievementAnimation = (newAchievements: any[]) => {
    // This would show a nice achievement unlock animation
    Alert.alert(
      '🎉 Achievement Unlocked!',
      newAchievements.map(a => `${a.icon} ${a.name}`).join('\n')
    );
  };

  const getOptionStyle = (option: string) => {
    if (!showResult) return styles.optionButton;
    
    if (option === correctAnswer) {
      return [styles.optionButton, styles.correctOption];
    }
    
    if (option === selectedAnswer && option !== correctAnswer) {
      return [styles.optionButton, styles.incorrectOption];
    }
    
    return [styles.optionButton, styles.disabledOption];
  };

  const renderProgressBar = () => {
    const percentage = (timeRemaining / (currentQuestion?.time_limit || 30)) * 100;
    const color = percentage > 50 ? '#4CAF50' : percentage > 20 ? '#FFC107' : '#F44336';
    
    return (
      <View style={styles.progressContainer}>
        <Animated.View
          style={[
            styles.progressBar,
            {
              width: progressAnim.interpolate({
                inputRange: [0, 1],
                outputRange: ['0%', '100%'],
              }),
              backgroundColor: color,
            },
          ]}
        />
        <Text style={styles.timerText}>{timeRemaining}s</Text>
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Starting game...</Text>
      </View>
    );
  }

  return (
    <LinearGradient colors={['#E3F2FD', '#BBDEFB']} style={styles.container}>
      <Header
        title="Trivia Challenge"
        leftAction={() => {
          Alert.alert(
            'Exit Game',
            'Are you sure you want to exit?',
            [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Exit', onPress: () => endGame() },
            ]
          );
        }}
      />
      
      <View style={styles.scoreContainer}>
        <View style={styles.scoreItem}>
          <Text style={styles.scoreLabel}>Score</Text>
          <Text style={styles.scoreValue}>{score}</Text>
        </View>
        <View style={styles.scoreItem}>
          <Text style={styles.scoreLabel}>Question</Text>
          <Text style={styles.scoreValue}>{questionNumber}</Text>
        </View>
        <View style={styles.scoreItem}>
          <Text style={styles.scoreLabel}>Streak</Text>
          <Text style={styles.scoreValue}>{streak} 🔥</Text>
        </View>
      </View>
      
      {renderProgressBar()}
      
      {currentQuestion && (
        <Animated.View
          style={[
            styles.questionContainer,
            {
              opacity: fadeAnim,
              transform: [{ scale: scaleAnim }],
            },
          ]}
        >
          <Card style={styles.questionCard}>
            <View style={styles.categoryContainer}>
              <Ionicons name="bookmark" size={16} color="#666" />
              <Text style={styles.categoryText}>{currentQuestion.category}</Text>
            </View>
            
            <Text style={styles.questionText}>{currentQuestion.text}</Text>
            
            <View style={styles.pointsContainer}>
              <Text style={styles.pointsText}>
                {currentQuestion.points} points
              </Text>
            </View>
          </Card>
          
          <View style={styles.optionsContainer}>
            {currentQuestion.options.map((option, index) => (
              <TouchableOpacity
                key={index}
                style={getOptionStyle(option)}
                onPress={() => handleAnswerSelect(option)}
                disabled={!!selectedAnswer || answering}
              >
                <Text
                  style={[
                    styles.optionText,
                    showResult && option === correctAnswer && styles.correctText,
                    showResult && option === selectedAnswer && option !== correctAnswer && styles.incorrectText,
                  ]}
                >
                  {String.fromCharCode(65 + index)}. {option}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </Animated.View>
      )}
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  scoreContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  scoreItem: {
    alignItems: 'center',
  },
  scoreLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  scoreValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  progressContainer: {
    height: 40,
    backgroundColor: '#E0E0E0',
    marginHorizontal: 20,
    marginBottom: 20,
    borderRadius: 20,
    overflow: 'hidden',
    position: 'relative',
  },
  progressBar: {
    height: '100%',
    borderRadius: 20,
  },
  timerText: {
    position: 'absolute',
    right: 16,
    top: 10,
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  questionContainer: {
    flex: 1,
    paddingHorizontal: 20,
  },
  questionCard: {
    marginBottom: 24,
  },
  categoryContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  categoryText: {
    marginLeft: 8,
    fontSize: 14,
    color: '#666',
    textTransform: 'capitalize',
  },
  questionText: {
    fontSize: 18,
    lineHeight: 26,
    color: '#333',
    marginBottom: 16,
  },
  pointsContainer: {
    alignItems: 'flex-end',
  },
  pointsText: {
    fontSize: 14,
    color: '#007AFF',
    fontWeight: '600',
  },
  optionsContainer: {
    flex: 1,
  },
  optionButton: {
    backgroundColor: 'white',
    paddingVertical: 16,
    paddingHorizontal: 20,
    marginBottom: 12,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#E0E0E0',
  },
  optionText: {
    fontSize: 16,
    color: '#333',
  },
  correctOption: {
    backgroundColor: '#E8F5E9',
    borderColor: '#4CAF50',
  },
  incorrectOption: {
    backgroundColor: '#FFEBEE',
    borderColor: '#F44336',
  },
  disabledOption: {
    opacity: 0.5,
  },
  correctText: {
    color: '#2E7D32',
    fontWeight: 'bold',
  },
  incorrectText: {
    color: '#C62828',
    fontWeight: 'bold',
  },
});