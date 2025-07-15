import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  Animated,
  TouchableOpacity,
  RefreshControl,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';

interface LeaderboardEntry {
  player_name: string;
  score: number;
  games_played: number;
  achievements: string[];
  rank: number;
  avatar?: string;
  isCurrentUser?: boolean;
}

interface GameLeaderboardProps {
  entries: LeaderboardEntry[];
  onRefresh?: () => Promise<void>;
  onPlayerPress?: (player: LeaderboardEntry) => void;
  title?: string;
  showAchievements?: boolean;
}

export const GameLeaderboard: React.FC<GameLeaderboardProps> = ({
  entries,
  onRefresh,
  onPlayerPress,
  title = 'Leaderboard',
  showAchievements = true,
}) => {
  const [refreshing, setRefreshing] = React.useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true,
      }),
      Animated.spring(slideAnim, {
        toValue: 0,
        friction: 8,
        tension: 40,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  const handleRefresh = async () => {
    if (!onRefresh) return;
    setRefreshing(true);
    await onRefresh();
    setRefreshing(false);
  };

  const getRankColor = (rank: number) => {
    switch (rank) {
      case 1:
        return ['#FFD700', '#FFA000']; // Gold
      case 2:
        return ['#C0C0C0', '#757575']; // Silver
      case 3:
        return ['#CD7F32', '#8D6E63']; // Bronze
      default:
        return ['#E3F2FD', '#BBDEFB']; // Default blue
    }
  };

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return '🥇';
      case 2:
        return '🥈';
      case 3:
        return '🥉';
      default:
        return null;
    }
  };

  const renderEntry = (entry: LeaderboardEntry, index: number) => {
    const delay = index * 50;
    const rankIcon = getRankIcon(entry.rank);

    return (
      <Animated.View
        key={`${entry.player_name}-${entry.rank}`}
        style={[
          {
            opacity: fadeAnim,
            transform: [
              {
                translateY: slideAnim.interpolate({
                  inputRange: [0, 50],
                  outputRange: [0, 50],
                }),
              },
            ],
          },
        ]}
      >
        <TouchableOpacity
          style={[
            styles.entryContainer,
            entry.isCurrentUser && styles.currentUserEntry,
          ]}
          onPress={() => onPlayerPress?.(entry)}
          activeOpacity={0.7}
        >
          <LinearGradient
            colors={entry.rank <= 3 ? getRankColor(entry.rank) : ['transparent', 'transparent']}
            style={styles.rankContainer}
          >
            {rankIcon ? (
              <Text style={styles.rankIcon}>{rankIcon}</Text>
            ) : (
              <Text style={styles.rankNumber}>{entry.rank}</Text>
            )}
          </LinearGradient>

          <View style={styles.playerInfo}>
            {entry.avatar ? (
              <Image source={{ uri: entry.avatar }} style={styles.avatar} />
            ) : (
              <View style={[styles.avatar, styles.placeholderAvatar]}>
                <Ionicons name="person" size={20} color="#666" />
              </View>
            )}
            
            <View style={styles.playerDetails}>
              <Text style={[styles.playerName, entry.isCurrentUser && styles.currentUserText]}>
                {entry.player_name}
                {entry.isCurrentUser && ' (You)'}
              </Text>
              <View style={styles.statsRow}>
                <Text style={styles.statText}>
                  <Ionicons name="game-controller" size={12} color="#666" />
                  {' '}{entry.games_played} games
                </Text>
                {showAchievements && (
                  <Text style={styles.statText}>
                    <Ionicons name="trophy" size={12} color="#666" />
                    {' '}{entry.achievements.length} achievements
                  </Text>
                )}
              </View>
            </View>
          </View>

          <View style={styles.scoreContainer}>
            <Text style={styles.scoreValue}>{entry.score.toLocaleString()}</Text>
            <Text style={styles.scoreLabel}>points</Text>
          </View>
        </TouchableOpacity>
      </Animated.View>
    );
  };

  const topThree = entries.slice(0, 3);
  const remaining = entries.slice(3);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>{title}</Text>
        <MaterialCommunityIcons name="trophy" size={24} color="#FFC107" />
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        refreshControl={
          onRefresh ? (
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
          ) : undefined
        }
      >
        {topThree.length > 0 && (
          <View style={styles.podiumContainer}>
            {topThree[1] && (
              <View style={styles.podiumItem}>
                <View style={styles.podiumAvatar}>
                  <Text style={styles.podiumEmoji}>🥈</Text>
                </View>
                <Text style={styles.podiumName}>{topThree[1].player_name}</Text>
                <Text style={styles.podiumScore}>{topThree[1].score}</Text>
                <View style={[styles.podiumBar, styles.silverBar]} />
              </View>
            )}
            
            {topThree[0] && (
              <View style={[styles.podiumItem, styles.goldPodium]}>
                <View style={styles.podiumAvatar}>
                  <Text style={styles.podiumEmoji}>🥇</Text>
                </View>
                <Text style={styles.podiumName}>{topThree[0].player_name}</Text>
                <Text style={styles.podiumScore}>{topThree[0].score}</Text>
                <View style={[styles.podiumBar, styles.goldBar]} />
              </View>
            )}
            
            {topThree[2] && (
              <View style={styles.podiumItem}>
                <View style={styles.podiumAvatar}>
                  <Text style={styles.podiumEmoji}>🥉</Text>
                </View>
                <Text style={styles.podiumName}>{topThree[2].player_name}</Text>
                <Text style={styles.podiumScore}>{topThree[2].score}</Text>
                <View style={[styles.podiumBar, styles.bronzeBar]} />
              </View>
            )}
          </View>
        )}

        <View style={styles.listContainer}>
          {remaining.map((entry, index) => renderEntry(entry, index + 3))}
        </View>

        {entries.length === 0 && (
          <View style={styles.emptyContainer}>
            <MaterialCommunityIcons name="trophy-outline" size={64} color="#CCC" />
            <Text style={styles.emptyText}>No entries yet</Text>
            <Text style={styles.emptySubtext}>Be the first to play!</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 20,
  },
  podiumContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'flex-end',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 30,
    backgroundColor: 'white',
  },
  podiumItem: {
    alignItems: 'center',
    marginHorizontal: 10,
    flex: 1,
  },
  goldPodium: {
    marginBottom: 20,
  },
  podiumAvatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  podiumEmoji: {
    fontSize: 36,
  },
  podiumName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
    textAlign: 'center',
  },
  podiumScore: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#007AFF',
    marginBottom: 8,
  },
  podiumBar: {
    width: '100%',
    borderRadius: 4,
  },
  goldBar: {
    height: 100,
    backgroundColor: '#FFD700',
  },
  silverBar: {
    height: 80,
    backgroundColor: '#C0C0C0',
  },
  bronzeBar: {
    height: 60,
    backgroundColor: '#CD7F32',
  },
  listContainer: {
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  entryContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    padding: 16,
    marginBottom: 8,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  currentUserEntry: {
    backgroundColor: '#E3F2FD',
    borderWidth: 2,
    borderColor: '#2196F3',
  },
  rankContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  rankIcon: {
    fontSize: 24,
  },
  rankNumber: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#666',
  },
  playerInfo: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    marginRight: 12,
  },
  placeholderAvatar: {
    backgroundColor: '#E0E0E0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  playerDetails: {
    flex: 1,
  },
  playerName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  currentUserText: {
    color: '#2196F3',
  },
  statsRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statText: {
    fontSize: 12,
    color: '#666',
    marginRight: 12,
  },
  scoreContainer: {
    alignItems: 'flex-end',
  },
  scoreValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  scoreLabel: {
    fontSize: 12,
    color: '#666',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#666',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
  },
});