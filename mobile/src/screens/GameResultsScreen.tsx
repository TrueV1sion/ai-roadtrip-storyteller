import React, { useEffect, useRef } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Animated,
  Dimensions,
  Share,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import LottieView from 'lottie-react-native';

import { Button, Card } from '../components';
import { gameApi } from '../services/api/gameApi';

const { width } = Dimensions.get('window');

interface GameResultsScreenProps {
  route: {
    params: {
      results: any;
      gameType: string;
      score: number;
      streak?: number;
      achievements?: any[];
      itemsFound?: number;
      totalItems?: number;
    };
  };
}

export const GameResultsScreen: React.FC<GameResultsScreenProps> = ({ route }) => {
  const navigation = useNavigation();
  const { results, gameType, score, streak, achievements, itemsFound, totalItems } = route.params;
  
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;

  useEffect(() => {
    // Animate entrance
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 8,
        tension: 40,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 600,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  const handleShare = async () => {
    try {
      const message = gameType === 'trivia'
        ? `I just scored ${score} points in Road Trip Trivia! 🎮🚗`
        : `I found ${itemsFound}/${totalItems} items in the Road Trip Scavenger Hunt! 🔍🚗`;
      
      await Share.share({
        message,
        title: 'Road Trip Game Results',
      });
    } catch (error) {
      logger.error('Error sharing:', error);
    }
  };

  const getPerformanceRating = () => {
    if (gameType === 'trivia') {
      const accuracy = results.session_summary?.accuracy || 0;
      if (accuracy >= 90) return { rating: 'Excellent!', color: '#4CAF50', icon: 'star' };
      if (accuracy >= 70) return { rating: 'Great Job!', color: '#2196F3', icon: 'star-half' };
      if (accuracy >= 50) return { rating: 'Good Effort!', color: '#FF9800', icon: 'star-outline' };
      return { rating: 'Keep Practicing!', color: '#9E9E9E', icon: 'star-outline' };
    } else {
      const percentage = (itemsFound! / totalItems!) * 100;
      if (percentage === 100) return { rating: 'Perfect!', color: '#4CAF50', icon: 'trophy' };
      if (percentage >= 80) return { rating: 'Excellent!', color: '#2196F3', icon: 'medal' };
      if (percentage >= 60) return { rating: 'Great Job!', color: '#FF9800', icon: 'ribbon' };
      return { rating: 'Good Start!', color: '#9E9E9E', icon: 'flag' };
    }
  };

  const performance = getPerformanceRating();

  return (
    <LinearGradient colors={['#E3F2FD', '#BBDEFB']} style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Animated.View
          style={[
            styles.headerContainer,
            {
              opacity: fadeAnim,
              transform: [{ scale: scaleAnim }],
            },
          ]}
        >
          <MaterialCommunityIcons name={performance.icon} size={80} color={performance.color} />
          <Text style={[styles.performanceText, { color: performance.color }]}>
            {performance.rating}
          </Text>
        </Animated.View>

        <Animated.View
          style={[
            styles.scoreContainer,
            {
              opacity: fadeAnim,
              transform: [{ translateY: slideAnim }],
            },
          ]}
        >
          <Card style={styles.scoreCard}>
            <Text style={styles.scoreTitle}>Final Score</Text>
            <Text style={styles.scoreValue}>{score}</Text>
            <Text style={styles.scoreLabel}>points</Text>
          </Card>
        </Animated.View>

        <Animated.View
          style={[
            styles.statsContainer,
            {
              opacity: fadeAnim,
              transform: [{ translateY: slideAnim }],
            },
          ]}
        >
          {gameType === 'trivia' ? (
            <>
              <View style={styles.statItem}>
                <Ionicons name="checkmark-circle" size={24} color="#4CAF50" />
                <Text style={styles.statValue}>
                  {results.session_summary?.questions_correct || 0}
                </Text>
                <Text style={styles.statLabel}>Correct</Text>
              </View>
              <View style={styles.statItem}>
                <Ionicons name="flame" size={24} color="#FF5722" />
                <Text style={styles.statValue}>{streak || 0}</Text>
                <Text style={styles.statLabel}>Best Streak</Text>
              </View>
              <View style={styles.statItem}>
                <Ionicons name="time" size={24} color="#2196F3" />
                <Text style={styles.statValue}>
                  {results.session_summary?.duration_minutes || 0}m
                </Text>
                <Text style={styles.statLabel}>Duration</Text>
              </View>
            </>
          ) : (
            <>
              <View style={styles.statItem}>
                <MaterialCommunityIcons name="treasure-chest" size={24} color="#4CAF50" />
                <Text style={styles.statValue}>{itemsFound}/{totalItems}</Text>
                <Text style={styles.statLabel}>Items Found</Text>
              </View>
              <View style={styles.statItem}>
                <Ionicons name="time" size={24} color="#2196F3" />
                <Text style={styles.statValue}>
                  {results.session_summary?.duration_minutes || 0}m
                </Text>
                <Text style={styles.statLabel}>Duration</Text>
              </View>
            </>
          )}
        </Animated.View>

        {achievements && achievements.length > 0 && (
          <Animated.View
            style={[
              styles.achievementsContainer,
              {
                opacity: fadeAnim,
                transform: [{ translateY: slideAnim }],
              },
            ]}
          >
            <Text style={styles.sectionTitle}>New Achievements!</Text>
            {achievements.map((achievement, index) => (
              <Card key={index} style={styles.achievementCard}>
                <Text style={styles.achievementIcon}>{achievement.icon}</Text>
                <View style={styles.achievementInfo}>
                  <Text style={styles.achievementName}>{achievement.name}</Text>
                  <Text style={styles.achievementDescription}>{achievement.description}</Text>
                  <Text style={styles.achievementPoints}>+{achievement.points} points</Text>
                </View>
              </Card>
            ))}
          </Animated.View>
        )}

        {results.session_summary?.final_standings && (
          <Animated.View
            style={[
              styles.leaderboardContainer,
              {
                opacity: fadeAnim,
                transform: [{ translateY: slideAnim }],
              },
            ]}
          >
            <Text style={styles.sectionTitle}>Final Standings</Text>
            {results.session_summary.final_standings.map((standing: any, index: number) => (
              <View key={index} style={styles.standingItem}>
                <Text style={styles.standingRank}>#{index + 1}</Text>
                <Text style={styles.standingName}>{standing.player}</Text>
                <Text style={styles.standingScore}>{standing.score} pts</Text>
              </View>
            ))}
          </Animated.View>
        )}

        <Animated.View
          style={[
            styles.actionsContainer,
            {
              opacity: fadeAnim,
              transform: [{ translateY: slideAnim }],
            },
          ]}
        >
          <Button
            title="Play Again"
            onPress={() => {
              navigation.navigate('GameSelection', { gameType });
            }}
            style={styles.primaryButton}
          />
          
          <TouchableOpacity style={styles.secondaryButton} onPress={handleShare}>
            <Ionicons name="share-social" size={20} color="#007AFF" />
            <Text style={styles.secondaryButtonText}>Share Results</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => navigation.navigate('Leaderboard')}
          >
            <MaterialCommunityIcons name="trophy" size={20} color="#007AFF" />
            <Text style={styles.secondaryButtonText}>View Leaderboard</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={styles.textButton}
            onPress={() => navigation.navigate('Home')}
          >
            <Text style={styles.textButtonText}>Back to Home</Text>
          </TouchableOpacity>
        </Animated.View>
      </ScrollView>
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    paddingTop: 60,
    paddingBottom: 40,
    paddingHorizontal: 20,
  },
  headerContainer: {
    alignItems: 'center',
    marginBottom: 30,
  },
  performanceText: {
    fontSize: 28,
    fontWeight: 'bold',
    marginTop: 16,
  },
  scoreContainer: {
    alignItems: 'center',
    marginBottom: 30,
  },
  scoreCard: {
    alignItems: 'center',
    paddingVertical: 30,
    paddingHorizontal: 50,
  },
  scoreTitle: {
    fontSize: 16,
    color: '#666',
    marginBottom: 8,
  },
  scoreValue: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#333',
  },
  scoreLabel: {
    fontSize: 16,
    color: '#666',
    marginTop: 4,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 30,
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginVertical: 8,
  },
  statLabel: {
    fontSize: 14,
    color: '#666',
  },
  achievementsContainer: {
    marginBottom: 30,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 16,
  },
  achievementCard: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    padding: 16,
  },
  achievementIcon: {
    fontSize: 36,
    marginRight: 16,
  },
  achievementInfo: {
    flex: 1,
  },
  achievementName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  achievementDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  achievementPoints: {
    fontSize: 14,
    color: '#4CAF50',
    fontWeight: '600',
  },
  leaderboardContainer: {
    marginBottom: 30,
  },
  standingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    padding: 16,
    marginBottom: 8,
    borderRadius: 8,
  },
  standingRank: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#666',
    width: 40,
  },
  standingName: {
    flex: 1,
    fontSize: 16,
    color: '#333',
  },
  standingScore: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  actionsContainer: {
    alignItems: 'center',
  },
  primaryButton: {
    width: '100%',
    marginBottom: 16,
  },
  secondaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    marginBottom: 12,
    width: '100%',
    justifyContent: 'center',
  },
  secondaryButtonText: {
    marginLeft: 8,
    fontSize: 16,
    color: '#007AFF',
    fontWeight: '600',
  },
  textButton: {
    paddingVertical: 12,
    marginTop: 8,
  },
  textButtonText: {
    fontSize: 16,
    color: '#666',
  },
});