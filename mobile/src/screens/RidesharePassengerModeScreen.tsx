import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  ScrollView,
  Alert,
  Modal,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { api } from '../services/api/ApiClient';
import { theme } from '../theme';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Loading } from '../components/Loading';

interface EntertainmentOption {
  id: string;
  name: string;
  type: string;
  duration: string;
  description: string;
}

export const RidesharePassengerModeScreen = () => {
  const navigation = useNavigation();
  const [entertainment, setEntertainment] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeGame, setActiveGame] = useState<string | null>(null);
  const [showTrivia, setShowTrivia] = useState(false);
  const [triviaData, setTriviaData] = useState<any>(null);

  useEffect(() => {
    loadEntertainmentOptions();
  }, []);

  const loadEntertainmentOptions = async () => {
    try {
      const response = await api.post('/rideshare/passenger/entertainment', {
        max_duration: 30 // Default 30 min trip
      });
      setEntertainment(response.data);
    } catch (error) {
      console.error('Error loading entertainment:', error);
    } finally {
      setLoading(false);
    }
  };

  const startActivity = async (activity: EntertainmentOption) => {
    if (activity.type === 'game' && activity.id === 'trivia') {
      await startTrivia();
    } else if (activity.type === 'story') {
      await playStory(activity);
    } else if (activity.type === 'music') {
      await startMusic();
    }
  };

  const startTrivia = async () => {
    try {
      const response = await api.post('/rideshare/voice/command', {
        voice_input: 'play trivia',
        mode: 'passenger',
        context: {}
      });
      
      if (response.data.data) {
        setTriviaData(response.data.data);
        setShowTrivia(true);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to start trivia');
    }
  };

  const playStory = async (story: EntertainmentOption) => {
    try {
      const response = await api.post('/rideshare/voice/command', {
        voice_input: 'tell me a story',
        mode: 'passenger',
        context: { story_type: story.id }
      });
      
      Alert.alert(story.name, response.data.response);
    } catch (error) {
      Alert.alert('Error', 'Failed to load story');
    }
  };

  const startMusic = async () => {
    Alert.alert('Music', 'Opening music player...');
    // Would integrate with music service
  };

  const handleTriviaAnswer = (answer: string) => {
    const isCorrect = answer === triviaData.correct;
    Alert.alert(
      isCorrect ? '🎉 Correct!' : '❌ Wrong',
      triviaData.fact,
      [{ text: 'Next Question', onPress: () => startTrivia() }]
    );
    setShowTrivia(false);
  };

  const getActivityIcon = (type: string, id: string) => {
    if (type === 'game') {
      return <MaterialCommunityIcons name="gamepad-variant" size={32} color={theme.colors.primary} />;
    } else if (type === 'story') {
      return <Ionicons name="book" size={32} color={theme.colors.primary} />;
    } else if (type === 'music') {
      return <Ionicons name="musical-notes" size={32} color={theme.colors.primary} />;
    }
    return <Ionicons name="star" size={32} color={theme.colors.primary} />;
  };

  if (loading) {
    return <Loading />;
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Ionicons name="arrow-back" size={24} color={theme.colors.text} />
        </TouchableOpacity>
        <Text style={styles.title}>Passenger Entertainment</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Quick Games Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Quick Games</Text>
          {entertainment?.options?.filter((opt: EntertainmentOption) => opt.type === 'game').map((game: EntertainmentOption) => (
            <Card key={game.id} style={styles.card}>
              <TouchableOpacity style={styles.activityButton} onPress={() => startActivity(game)}>
                {getActivityIcon(game.type, game.id)}
                <View style={styles.activityInfo}>
                  <Text style={styles.activityTitle}>{game.name}</Text>
                  <Text style={styles.activityDuration}>{game.duration}</Text>
                  <Text style={styles.activityDescription}>{game.description}</Text>
                </View>
                <Ionicons name="play-circle" size={40} color={theme.colors.primary} />
              </TouchableOpacity>
            </Card>
          ))}
        </View>

        {/* Stories Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Short Stories</Text>
          {entertainment?.options?.filter((opt: EntertainmentOption) => opt.type === 'story').map((story: EntertainmentOption) => (
            <Card key={story.id} style={styles.card}>
              <TouchableOpacity style={styles.activityButton} onPress={() => startActivity(story)}>
                {getActivityIcon(story.type, story.id)}
                <View style={styles.activityInfo}>
                  <Text style={styles.activityTitle}>{story.name}</Text>
                  <Text style={styles.activityDuration}>{story.duration}</Text>
                  <Text style={styles.activityDescription}>{story.description}</Text>
                </View>
                <Ionicons name="play-circle" size={40} color={theme.colors.primary} />
              </TouchableOpacity>
            </Card>
          ))}
        </View>

        {/* Music Section */}
        <Card style={styles.musicCard}>
          <TouchableOpacity style={styles.musicButton} onPress={startMusic}>
            <Ionicons name="musical-notes" size={48} color={theme.colors.primary} />
            <Text style={styles.musicTitle}>Music Player</Text>
            <Text style={styles.musicDescription}>
              Curated playlists for your ride
            </Text>
          </TouchableOpacity>
        </Card>

        {/* Local Info */}
        <Card style={styles.infoCard}>
          <TouchableOpacity style={styles.infoButton} onPress={() => {
            api.post('/rideshare/voice/command', {
              voice_input: 'tell me about this area',
              mode: 'passenger',
              context: {}
            }).then(res => {
              Alert.alert('Local Facts', res.data.response);
            });
          }}>
            <Ionicons name="information-circle" size={32} color={theme.colors.primary} />
            <Text style={styles.infoText}>Learn About This Area</Text>
          </TouchableOpacity>
        </Card>

        {/* Exit Button */}
        <Button
          title="End Entertainment Mode"
          onPress={async () => {
            await api.delete('/rideshare/mode');
            navigation.navigate('RideshareScreen' as never);
          }}
          variant="secondary"
          style={styles.exitButton}
        />
      </ScrollView>

      {/* Trivia Modal */}
      <Modal
        visible={showTrivia}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowTrivia(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            <Text style={styles.triviaQuestion}>
              {triviaData?.question || 'Loading question...'}
            </Text>
            
            <View style={styles.triviaOptions}>
              {triviaData?.options?.map((option: string, index: number) => (
                <TouchableOpacity
                  key={index}
                  style={styles.triviaButton}
                  onPress={() => handleTriviaAnswer(String.fromCharCode(65 + index))}
                >
                  <Text style={styles.triviaButtonText}>
                    {String.fromCharCode(65 + index)}. {option}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <TouchableOpacity
              style={styles.skipButton}
              onPress={() => setShowTrivia(false)}
            >
              <Text style={styles.skipText}>Skip Question</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: theme.spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  content: {
    flex: 1,
    padding: theme.spacing.md,
  },
  section: {
    marginBottom: theme.spacing.xl,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: theme.spacing.md,
  },
  card: {
    marginBottom: theme.spacing.md,
  },
  activityButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: theme.spacing.lg,
  },
  activityInfo: {
    flex: 1,
    marginLeft: theme.spacing.md,
    marginRight: theme.spacing.md,
  },
  activityTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text,
  },
  activityDuration: {
    fontSize: 14,
    color: theme.colors.primary,
    marginTop: theme.spacing.xs,
  },
  activityDescription: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.xs,
  },
  musicCard: {
    marginBottom: theme.spacing.lg,
  },
  musicButton: {
    alignItems: 'center',
    padding: theme.spacing.xl,
  },
  musicTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginTop: theme.spacing.md,
  },
  musicDescription: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.xs,
  },
  infoCard: {
    marginBottom: theme.spacing.lg,
  },
  infoButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: theme.spacing.lg,
  },
  infoText: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text,
    marginLeft: theme.spacing.md,
  },
  exitButton: {
    marginTop: theme.spacing.lg,
    marginBottom: theme.spacing.xl,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.xl,
    margin: theme.spacing.lg,
    width: '90%',
  },
  triviaQuestion: {
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.colors.text,
    textAlign: 'center',
    marginBottom: theme.spacing.xl,
  },
  triviaOptions: {
    marginBottom: theme.spacing.lg,
  },
  triviaButton: {
    backgroundColor: theme.colors.primary,
    padding: theme.spacing.lg,
    borderRadius: theme.borderRadius.md,
    marginBottom: theme.spacing.md,
  },
  triviaButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  skipButton: {
    alignItems: 'center',
    padding: theme.spacing.md,
  },
  skipText: {
    color: theme.colors.textSecondary,
    fontSize: 14,
  },
});