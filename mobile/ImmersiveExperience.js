import React, { useState, useEffect } from 'react';
import { View, Text, Button, StyleSheet, ScrollView } from 'react-native';
import { Audio } from 'expo-av';

const ImmersiveExperience = () => {
  const [experience, setExperience] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sound, setSound] = useState(null);

  const fetchExperience = async () => {
    setLoading(true);
    try {
      // Replace URL with your production endpoint
      const response = await fetch('https://api.example.com/immersive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: 'test123',
          location: { latitude: 12.34, longitude: 56.78 },
          interests: ['history', 'nature'],
          context: {
            time_of_day: 'morning',
            weather: 'sunny',
            mood: 'happy'
          }
        })
      });
      const data = await response.json();
      setExperience(data);
    } catch (error) {
      console.error('Error fetching immersive experience:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExperience();
  }, []);

  const playTTS = async () => {
    if (!experience || !experience.tts_audio) return;
    // Create a data URI for the audio
    const audioUri = 'data:audio/mpeg;base64,' + experience.tts_audio;
    try {
      const { sound } = await Audio.Sound.createAsync({ uri: audioUri });
      setSound(sound);
      await sound.playAsync();
    } catch (error) {
      console.error('Error playing TTS audio:', error);
    }
  };

  useEffect(() => {
    return sound ? () => { sound.unloadAsync(); } : undefined;
  }, [sound]);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Immersive Experience</Text>
      {loading && <Text style={styles.info}>Loading...</Text>}
      {experience && (
        <View style={styles.content}>
          <Text style={styles.subtitle}>Story:</Text>
          <Text style={styles.story}>{experience.story}</Text>
          <Text style={styles.subtitle}>Playlist:</Text>
          <Text style={styles.playlistName}>{experience.playlist.playlist_name}</Text>
          {experience.playlist.tracks && experience.playlist.tracks.map((track, index) => (
            <Text key={index} style={styles.track}>
              {track.title} - {track.artist}
            </Text>
          ))}
          <Button title="Play TTS Audio" onPress={playTTS} />
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: '#fff',
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  subtitle: {
    fontSize: 20,
    fontWeight: '600',
    marginTop: 10,
  },
  story: {
    fontSize: 16,
    marginBottom: 20,
    textAlign: 'justify',
  },
  playlistName: {
    fontSize: 18,
    fontWeight: '500',
    marginBottom: 10,
  },
  track: {
    fontSize: 16,
    marginBottom: 5,
  },
  info: {
    fontSize: 16,
    marginBottom: 20,
  },
  content: {
    width: '100%',
  },
});

export default ImmersiveExperience; 