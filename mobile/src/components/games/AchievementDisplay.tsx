import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Animated,
  Dimensions,
  TouchableOpacity,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');

interface Achievement {
  id: string;
  name: string;
  description: string;
  icon: string;
  points: number;
  unlocked: boolean;
  unlocked_at?: string;
  progress?: number;
  requirement?: any;
}

interface AchievementDisplayProps {
  achievements: Achievement[];
  onPress?: (achievement: Achievement) => void;
  showProgress?: boolean;
}

export const AchievementDisplay: React.FC<AchievementDisplayProps> = ({
  achievements,
  onPress,
  showProgress = true,
}) => {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.9)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 8,
        tension: 40,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  const renderAchievement = (achievement: Achievement, index: number) => {
    const isUnlocked = achievement.unlocked;
    const delay = index * 100;

    return (
      <Animated.View
        key={achievement.id}
        style={[
          styles.achievementContainer,
          {
            opacity: fadeAnim,
            transform: [
              {
                scale: scaleAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.9, 1],
                }),
              },
              {
                translateY: fadeAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [20, 0],
                }),
              },
            ],
          },
        ]}
      >
        <TouchableOpacity
          style={[styles.achievementCard, !isUnlocked && styles.lockedCard]}
          onPress={() => onPress?.(achievement)}
          activeOpacity={0.8}
        >
          <LinearGradient
            colors={
              isUnlocked
                ? ['#FFF9C4', '#FFECB3']
                : ['#F5F5F5', '#E0E0E0']
            }
            style={styles.iconContainer}
          >
            <Text style={styles.icon}>{achievement.icon}</Text>
            {!isUnlocked && (
              <View style={styles.lockOverlay}>
                <Ionicons name="lock-closed" size={24} color="#999" />
              </View>
            )}
          </LinearGradient>

          <View style={styles.achievementInfo}>
            <Text style={[styles.achievementName, !isUnlocked && styles.lockedText]}>
              {achievement.name}
            </Text>
            <Text style={[styles.achievementDescription, !isUnlocked && styles.lockedText]}>
              {achievement.description}
            </Text>
            
            {showProgress && achievement.progress !== undefined && !isUnlocked && (
              <View style={styles.progressContainer}>
                <View style={styles.progressBar}>
                  <View
                    style={[
                      styles.progressFill,
                      { width: `${achievement.progress * 100}%` },
                    ]}
                  />
                </View>
                <Text style={styles.progressText}>
                  {Math.round(achievement.progress * 100)}%
                </Text>
              </View>
            )}
            
            <View style={styles.pointsContainer}>
              <Ionicons
                name="star"
                size={16}
                color={isUnlocked ? '#FFC107' : '#999'}
              />
              <Text style={[styles.pointsText, !isUnlocked && styles.lockedText]}>
                {achievement.points} points
              </Text>
            </View>
          </View>

          {isUnlocked && achievement.unlocked_at && (
            <View style={styles.unlockedBadge}>
              <Ionicons name="checkmark-circle" size={20} color="#4CAF50" />
            </View>
          )}
        </TouchableOpacity>
      </Animated.View>
    );
  };

  const unlockedCount = achievements.filter(a => a.unlocked).length;
  const totalPoints = achievements
    .filter(a => a.unlocked)
    .reduce((sum, a) => sum + a.points, 0);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Achievements</Text>
        <View style={styles.stats}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{unlockedCount}/{achievements.length}</Text>
            <Text style={styles.statLabel}>Unlocked</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{totalPoints}</Text>
            <Text style={styles.statLabel}>Points</Text>
          </View>
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {achievements.map((achievement, index) => renderAchievement(achievement, index))}
      </ScrollView>
    </View>
  );
};

export const AchievementUnlockAnimation: React.FC<{
  achievement: Achievement;
  onComplete?: () => void;
}> = ({ achievement, onComplete }) => {
  const scaleAnim = useRef(new Animated.Value(0)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.sequence([
      Animated.parallel([
        Animated.spring(scaleAnim, {
          toValue: 1.2,
          friction: 3,
          tension: 40,
          useNativeDriver: true,
        }),
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]),
      Animated.parallel([
        Animated.spring(scaleAnim, {
          toValue: 1,
          friction: 5,
          useNativeDriver: true,
        }),
        Animated.timing(rotateAnim, {
          toValue: 1,
          duration: 600,
          useNativeDriver: true,
        }),
      ]),
    ]).start(() => {
      setTimeout(() => {
        Animated.timing(fadeAnim, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }).start(onComplete);
      }, 1500);
    });
  }, []);

  return (
    <Animated.View
      style={[
        styles.unlockContainer,
        {
          opacity: fadeAnim,
          transform: [
            { scale: scaleAnim },
            {
              rotate: rotateAnim.interpolate({
                inputRange: [0, 1],
                outputRange: ['0deg', '360deg'],
              }),
            },
          ],
        },
      ]}
    >
      <LinearGradient
        colors={['#FFD700', '#FFA000']}
        style={styles.unlockCard}
      >
        <Text style={styles.unlockIcon}>{achievement.icon}</Text>
        <Text style={styles.unlockTitle}>Achievement Unlocked!</Text>
        <Text style={styles.unlockName}>{achievement.name}</Text>
        <Text style={styles.unlockDescription}>{achievement.description}</Text>
        <View style={styles.unlockPoints}>
          <Ionicons name="star" size={20} color="#FFF" />
          <Text style={styles.unlockPointsText}>+{achievement.points} points</Text>
        </View>
      </LinearGradient>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  stats: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  statDivider: {
    width: 1,
    height: 30,
    backgroundColor: '#E0E0E0',
    marginHorizontal: 20,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
  },
  achievementContainer: {
    marginBottom: 16,
  },
  achievementCard: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  lockedCard: {
    backgroundColor: '#FAFAFA',
  },
  iconContainer: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  icon: {
    fontSize: 32,
  },
  lockOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 30,
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
    marginBottom: 8,
  },
  lockedText: {
    color: '#999',
  },
  progressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 8,
  },
  progressBar: {
    flex: 1,
    height: 4,
    backgroundColor: '#E0E0E0',
    borderRadius: 2,
    marginRight: 8,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#007AFF',
    borderRadius: 2,
  },
  progressText: {
    fontSize: 12,
    color: '#666',
    minWidth: 35,
  },
  pointsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  pointsText: {
    fontSize: 14,
    color: '#333',
    marginLeft: 4,
    fontWeight: '600',
  },
  unlockedBadge: {
    position: 'absolute',
    top: 12,
    right: 12,
  },
  unlockContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
  },
  unlockCard: {
    width: width * 0.8,
    padding: 32,
    borderRadius: 20,
    alignItems: 'center',
  },
  unlockIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  unlockTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFF',
    marginBottom: 8,
  },
  unlockName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFF',
    marginBottom: 8,
  },
  unlockDescription: {
    fontSize: 14,
    color: '#FFF',
    textAlign: 'center',
    marginBottom: 16,
  },
  unlockPoints: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  unlockPointsText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#FFF',
    marginLeft: 8,
  },
});