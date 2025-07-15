import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
} from 'react-native';
import {
  Portal,
  Modal,
  Text,
  Card,
  Button,
  Title,
  Paragraph,
  IconButton,
  Surface,
} from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import LottieView from 'lottie-react-native';

import { COLORS, SPACING } from '../../theme';

export interface TriviaQuestion {
  id: string;
  question: string;
  options: string[];
  correct: string;
  fun_fact: string;
  difficulty?: 'easy' | 'medium' | 'hard';
  category?: string;
  image_url?: string;
}

interface TriviaModalProps {
  visible: boolean;
  onDismiss: () => void;
  onComplete: (score: number, totalQuestions: number) => void;
  questions: TriviaQuestion[];
}

const TriviaModal: React.FC<TriviaModalProps> = ({
  visible,
  onDismiss,
  onComplete,
  questions,
}) => {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isAnswered, setIsAnswered] = useState(false);
  const [score, setScore] = useState(0);
  const [timeLeft, setTimeLeft] = useState(30);
  const [timerActive, setTimerActive] = useState(true);
  const [animation] = useState(new Animated.Value(0));
  const [sound, setSound] = useState<Audio.Sound | null>(null);
  const [showFact, setShowFact] = useState(false);
  
  const currentQuestion = questions[currentQuestionIndex];
  
  // Reset state when questions change or modal visibility changes
  useEffect(() => {
    if (visible) {
      setCurrentQuestionIndex(0);
      setSelectedOption(null);
      setIsAnswered(false);
      setScore(0);
      setTimeLeft(30);
      setTimerActive(true);
      setShowFact(false);
    }
  }, [visible, questions]);
  
  // Timer effect
  useEffect(() => {
    let timer: NodeJS.Timeout;
    
    if (visible && timerActive && timeLeft > 0) {
      timer = setTimeout(() => {
        setTimeLeft(timeLeft - 1);
      }, 1000);
    } else if (timeLeft === 0 && timerActive) {
      handleTimeout();
    }
    
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [timeLeft, timerActive, visible]);
  
  // Load sounds
  useEffect(() => {
    const loadSounds = async () => {
      try {
        const { sound } = await Audio.Sound.createAsync(
          require('../../../assets/sounds/trivia.mp3')
        );
        setSound(sound);
      } catch (error) {
        console.error('Error loading sound:', error);
      }
    };
    
    loadSounds();
    
    return () => {
      if (sound) {
        sound.unloadAsync();
      }
    };
  }, []);
  
  // Play sound when selecting an option
  const playSound = async (correct: boolean) => {
    try {
      if (sound) {
        await sound.stopAsync();
        await sound.setPositionAsync(0);
        await sound.setVolumeAsync(correct ? 1.0 : 0.7);
        await sound.playAsync();
      }
    } catch (error) {
      console.error('Error playing sound:', error);
    }
  };
  
  const handleTimeout = () => {
    setTimerActive(false);
    setIsAnswered(true);
    playSound(false);
  };
  
  const handleOptionSelect = (option: string) => {
    if (isAnswered) return;
    
    setSelectedOption(option);
    setIsAnswered(true);
    setTimerActive(false);
    
    const isCorrect = option === currentQuestion.correct;
    if (isCorrect) {
      setScore(score + 1);
      playSound(true);
      
      // Animate correct answer
      Animated.sequence([
        Animated.timing(animation, {
          toValue: 1,
          duration: 400,
          useNativeDriver: true,
        }),
        Animated.timing(animation, {
          toValue: 0,
          duration: 400,
          useNativeDriver: true,
        }),
      ]).start();
    } else {
      playSound(false);
    }
  };
  
  const handleNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setSelectedOption(null);
      setIsAnswered(false);
      setTimeLeft(30);
      setTimerActive(true);
      setShowFact(false);
    } else {
      // Quiz completed
      onComplete(score, questions.length);
    }
  };
  
  const handleShowFact = () => {
    setShowFact(true);
  };
  
  // Render timer
  const renderTimer = () => {
    const timerColor = 
      timeLeft > 20 ? COLORS.success :
      timeLeft > 10 ? COLORS.warning :
      COLORS.error;
    
    return (
      <View style={styles.timerContainer}>
        <MaterialIcons name="timer" size={24} color={timerColor} />
        <Text style={[styles.timerText, { color: timerColor }]}>
          {timeLeft}s
        </Text>
      </View>
    );
  };
  
  // Render options
  const renderOptions = () => {
    return currentQuestion.options.map((option, index) => {
      const isSelected = selectedOption === option;
      const isCorrect = option === currentQuestion.correct;
      
      let optionStyle = styles.option;
      let textStyle = styles.optionText;
      
      if (isAnswered) {
        if (isCorrect) {
          optionStyle = styles.correctOption;
          textStyle = styles.correctOptionText;
        } else if (isSelected) {
          optionStyle = styles.incorrectOption;
          textStyle = styles.incorrectOptionText;
        }
      } else if (isSelected) {
        optionStyle = styles.selectedOption;
      }
      
      return (
        <TouchableOpacity
          key={index}
          style={[styles.optionContainer, optionStyle]}
          onPress={() => handleOptionSelect(option)}
          disabled={isAnswered}
        >
          <Text style={textStyle}>{option}</Text>
          {isAnswered && isCorrect && (
            <MaterialIcons name="check-circle" size={24} color={COLORS.success} />
          )}
          {isAnswered && isSelected && !isCorrect && (
            <MaterialIcons name="cancel" size={24} color={COLORS.error} />
          )}
        </TouchableOpacity>
      );
    });
  };
  
  // Render fun fact card
  const renderFunFact = () => {
    if (!showFact || !currentQuestion.fun_fact) return null;
    
    return (
      <Card style={styles.factCard}>
        <Card.Content>
          <Title>Fun Fact!</Title>
          <Paragraph>{currentQuestion.fun_fact}</Paragraph>
        </Card.Content>
      </Card>
    );
  };
  
  if (!currentQuestion) return null;
  
  return (
    <Portal>
      <Modal
        visible={visible}
        onDismiss={onDismiss}
        contentContainerStyle={styles.modalContainer}
      >
        <Surface style={styles.container}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.progressContainer}>
              <Text style={styles.progressText}>
                Question {currentQuestionIndex + 1}/{questions.length}
              </Text>
              <Text style={styles.scoreText}>Score: {score}</Text>
            </View>
            {!isAnswered && renderTimer()}
            <IconButton
              icon="close"
              size={24}
              onPress={onDismiss}
              style={styles.closeButton}
            />
          </View>
          
          {/* Question */}
          <View style={styles.questionContainer}>
            <Text style={styles.questionText}>
              {currentQuestion.question}
            </Text>
          </View>
          
          {/* Options */}
          <View style={styles.optionsContainer}>
            {renderOptions()}
          </View>
          
          {/* Fun Fact */}
          {renderFunFact()}
          
          {/* Bottom Buttons */}
          {isAnswered && (
            <View style={styles.buttonContainer}>
              {!showFact && currentQuestion.fun_fact && (
                <Button
                  mode="outlined"
                  onPress={handleShowFact}
                  style={styles.factButton}
                >
                  Show Fun Fact
                </Button>
              )}
              <Button
                mode="contained"
                onPress={handleNext}
                style={styles.nextButton}
              >
                {currentQuestionIndex < questions.length - 1 ? 'Next Question' : 'Finish Quiz'}
              </Button>
            </View>
          )}
          
          {/* Celebration Animation */}
          {isAnswered && selectedOption === currentQuestion.correct && (
            <Animated.View
              style={[
                styles.celebrationContainer,
                {
                  opacity: animation,
                  transform: [
                    {
                      scale: animation.interpolate({
                        inputRange: [0, 1],
                        outputRange: [0.5, 1.2],
                      }),
                    },
                  ],
                },
              ]}
            >
              <MaterialIcons name="emoji-events" size={64} color={COLORS.primary} />
              <Text style={styles.celebrationText}>Great job!</Text>
            </Animated.View>
          )}
        </Surface>
      </Modal>
    </Portal>
  );
};

const { width } = Dimensions.get('window');

const styles = StyleSheet.create({
  modalContainer: {
    margin: SPACING.medium,
  },
  container: {
    borderRadius: 12,
    padding: SPACING.medium,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.medium,
  },
  progressContainer: {
    flex: 1,
  },
  progressText: {
    fontSize: 14,
    color: COLORS.textSecondary,
  },
  scoreText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: COLORS.primary,
  },
  timerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: SPACING.medium,
  },
  timerText: {
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: SPACING.xsmall,
  },
  closeButton: {
    margin: 0,
  },
  questionContainer: {
    marginBottom: SPACING.large,
  },
  questionText: {
    fontSize: 18,
    fontWeight: 'bold',
    lineHeight: 24,
  },
  optionsContainer: {
    marginBottom: SPACING.medium,
  },
  optionContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: SPACING.medium,
    borderRadius: 8,
    marginBottom: SPACING.small,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  option: {
    backgroundColor: COLORS.surface,
  },
  selectedOption: {
    backgroundColor: COLORS.primary + '20',
    borderColor: COLORS.primary,
  },
  correctOption: {
    backgroundColor: COLORS.success + '20',
    borderColor: COLORS.success,
  },
  incorrectOption: {
    backgroundColor: COLORS.error + '20',
    borderColor: COLORS.error,
  },
  optionText: {
    fontSize: 16,
    flex: 1,
  },
  correctOptionText: {
    fontWeight: 'bold',
    color: COLORS.success,
  },
  incorrectOptionText: {
    color: COLORS.error,
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: SPACING.medium,
  },
  factButton: {
    flex: 1,
    marginRight: SPACING.small,
  },
  nextButton: {
    flex: 1,
  },
  factCard: {
    marginBottom: SPACING.medium,
  },
  celebrationContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    zIndex: 10,
  },
  celebrationText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: COLORS.primary,
    marginTop: SPACING.medium,
  },
});

export default TriviaModal; 