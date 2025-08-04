import React, { useState, useEffect } from 'react';
import { View, Text, Button, StyleSheet } from 'react-native';
import { Audio } from 'expo-av';

const MusicPlayer = () => {
  const [sound, setSound] = useState();
  const [isPlaying, setIsPlaying] = useState(false);
  const [isTTSPlaying, setIsTTSPlaying] = useState(false);

  // Load sound on component mount
  useEffect(() => {
    let soundObject;
    async function loadSound() {
      const { sound } = await Audio.Sound.createAsync(
        require('./assets/sample-music.mp3'),
        { shouldPlay: false, volume: 1.0 }
      );
      soundObject = sound;
      setSound(sound);
    }
    loadSound();

    return () => {
      if (soundObject) {
        soundObject.unloadAsync();
      }
    };
  }, []);

  // Update volume based on TTS playback state
  useEffect(() => {
    if (sound) {
      const newVolume = isTTSPlaying ? 0.2 : 1.0;
      sound.setVolumeAsync(newVolume);
    }
  }, [isTTSPlaying, sound]);

  const toggleMusic = async () => {
    if (!sound) return;
    if (isPlaying) {
      await sound.pauseAsync();
      setIsPlaying(false);
    } else {
      await sound.playAsync();
      setIsPlaying(true);
    }
  };

  const toggleTTS = () => {
    // Simulate TTS playback; toggle state to trigger audio ducking.
    setIsTTSPlaying(!isTTSPlaying);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Music Player with Audio Ducking</Text>
      <Button
        title={isPlaying ? 'Pause Music' : 'Play Music'}
        onPress={toggleMusic}
      />
      <View style={styles.spacing} />
      <Button
        title={isTTSPlaying ? 'Stop TTS' : 'Start TTS'}
        onPress={toggleTTS}
      />
      <Text style={styles.info}>
        {isTTSPlaying
          ? 'TTS is playing, music volume reduced'
          : 'TTS is off, music at full volume'}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 20,
    marginBottom: 20,
    textAlign: 'center',
  },
  spacing: {
    marginVertical: 10,
  },
  info: {
    marginTop: 20,
    fontSize: 16,
    textAlign: 'center',
  },
});

export default MusicPlayer; 