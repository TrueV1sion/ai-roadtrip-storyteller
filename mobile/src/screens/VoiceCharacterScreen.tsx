import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  SafeAreaView
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { MaterialIcons, FontAwesome5 } from '@expo/vector-icons';

import { CharacterSelector, SpeechControlPanel } from '../components/voice';
import { VoiceCharacterType, SpeechResultType, EmotionType } from '../types/voice';
import { voiceCharacterService } from '../services/voiceCharacterService';

const VoiceCharacterScreen: React.FC = () => {
  const navigation = useNavigation();
  
  // Characters state
  const [characters, setCharacters] = useState<VoiceCharacterType[]>([]);
  const [selectedCharacter, setSelectedCharacter] = useState<VoiceCharacterType | null>(null);
  const [loadingCharacters, setLoadingCharacters] = useState(true);
  
  // Speech state
  const [inputText, setInputText] = useState('');
  const [currentSpeech, setCurrentSpeech] = useState<SpeechResultType | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [playbackProgress, setPlaybackProgress] = useState(0);
  const [emotion, setEmotion] = useState<EmotionType>('neutral');
  
  // Timer for updating playback progress
  const [progressTimer, setProgressTimer] = useState<NodeJS.Timeout | null>(null);
  
  // Load characters
  useEffect(() => {
    const fetchCharacters = async () => {
      try {
        setLoadingCharacters(true);
        const charactersList = await voiceCharacterService.getAllCharacters();
        setCharacters(charactersList);
        
        // Select default character if available
        if (charactersList.length > 0 && !selectedCharacter) {
          setSelectedCharacter(charactersList[0]);
        }
        
        setLoadingCharacters(false);
      } catch (error) {
        console.error('Error fetching characters:', error);
        setLoadingCharacters(false);
        Alert.alert('Error', 'Failed to load voice characters');
      }
    };
    
    fetchCharacters();
  }, []);
  
  // Handle character selection
  const handleSelectCharacter = (character: VoiceCharacterType) => {
    setSelectedCharacter(character);
    
    // If this is a different character, stop any current playback
    if (selectedCharacter?.id !== character.id && isPlaying) {
      handleStopSpeech();
    }
    
    // Update emotion to match the character's base emotion
    setEmotion(character.base_emotion);
  };
  
  // Play a sample for a character
  const handlePlaySample = async (character: VoiceCharacterType) => {
    try {
      // Stop any current playback
      handleStopSpeech();
      
      setIsGenerating(true);
      
      // Generate sample speech
      const sampleText = character.speech_patterns.greeting || 
        `Hello! I'm ${character.name}, your voice assistant.`;
      
      const result = await voiceCharacterService.speakWithCharacter(
        sampleText,
        character.id,
        character.base_emotion
      );
      
      setCurrentSpeech(result);
      setIsPlaying(true);
      setIsPaused(false);
      setSelectedCharacter(character);
      setEmotion(character.base_emotion);
      
      // Start progress timer
      startProgressTimer();
      
      setIsGenerating(false);
    } catch (error) {
      console.error('Error playing sample:', error);
      setIsGenerating(false);
      Alert.alert('Error', 'Failed to play voice sample');
    }
  };
  
  // Generate and play speech
  const handleGenerateSpeech = async () => {
    if (!selectedCharacter || !inputText.trim()) {
      return;
    }
    
    try {
      // Stop any current playback
      handleStopSpeech();
      
      setIsGenerating(true);
      
      const result = await voiceCharacterService.speakWithCharacter(
        inputText,
        selectedCharacter.id,
        emotion
      );
      
      setCurrentSpeech(result);
      setIsPlaying(true);
      setIsPaused(false);
      
      // Start progress timer
      startProgressTimer();
      
      setIsGenerating(false);
    } catch (error) {
      console.error('Error generating speech:', error);
      setIsGenerating(false);
      Alert.alert('Error', 'Failed to generate speech');
    }
  };
  
  // Handle play/pause
  const handlePlayPause = async () => {
    if (!currentSpeech) return;
    
    if (isPlaying && !isPaused) {
      // Pause playback
      await voiceCharacterService.pauseSpeech();
      setIsPaused(true);
      stopProgressTimer();
    } else {
      // Resume or start playback
      try {
        if (isPaused) {
          // Resume from current position
          await voiceCharacterService.playSpeech(currentSpeech.audio_url);
          setIsPaused(false);
          startProgressTimer();
        } else {
          // Start from beginning
          await voiceCharacterService.playSpeech(currentSpeech.audio_url);
          setIsPlaying(true);
          setIsPaused(false);
          startProgressTimer();
        }
      } catch (error) {
        console.error('Error playing speech:', error);
        Alert.alert('Error', 'Failed to play speech');
      }
    }
  };
  
  // Handle stop
  const handleStopSpeech = async () => {
    await voiceCharacterService.stopSpeech();
    setIsPlaying(false);
    setIsPaused(false);
    setPlaybackProgress(0);
    stopProgressTimer();
  };
  
  // Handle seek
  const handleSeek = async (position: number) => {
    if (!currentSpeech) return;
    
    try {
      await voiceCharacterService.seekToPosition(position * 1000); // Convert to milliseconds
      setPlaybackProgress(position);
    } catch (error) {
      console.error('Error seeking:', error);
    }
  };
  
  // Start progress timer
  const startProgressTimer = () => {
    // Clear any existing timer
    if (progressTimer) {
      clearInterval(progressTimer);
    }
    
    // Create new timer that updates every 100ms
    const timer = setInterval(async () => {
      const status = await voiceCharacterService.getPlaybackStatus();
      
      if (status && status.isLoaded) {
        // Update progress
        setPlaybackProgress(status.positionMillis / 1000); // Convert to seconds
        
        // If playback is finished
        if (status.didJustFinish) {
          setIsPlaying(false);
          setIsPaused(false);
          setPlaybackProgress(0);
          stopProgressTimer();
        }
      }
    }, 100);
    
    setProgressTimer(timer);
  };
  
  // Stop progress timer
  const stopProgressTimer = () => {
    if (progressTimer) {
      clearInterval(progressTimer);
      setProgressTimer(null);
    }
  };
  
  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (progressTimer) {
        clearInterval(progressTimer);
      }
      voiceCharacterService.stopSpeech();
    };
  }, [progressTimer]);
  
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity 
          style={styles.backButton}
          onPress={() => navigation.goBack()}
        >
          <MaterialIcons name="arrow-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Voice Characters</Text>
      </View>
      
      <ScrollView style={styles.content}>
        <Text style={styles.sectionTitle}>Select a Character</Text>
        <CharacterSelector
          characters={characters}
          selectedCharacterId={selectedCharacter?.id}
          onSelectCharacter={handleSelectCharacter}
          onPlaySample={handlePlaySample}
          loading={loadingCharacters}
          onSearch={(query) => console.log('Search:', query)}
          onFilterByTheme={(theme) => console.log('Filter by theme:', theme)}
        />
      </ScrollView>
      
      <View style={styles.bottomPanel}>
        {selectedCharacter && (
          <>
            <View style={styles.inputContainer}>
              <TextInput
                style={styles.textInput}
                placeholder="Enter text to speak..."
                value={inputText}
                onChangeText={setInputText}
                multiline
                numberOfLines={3}
              />
              
              <TouchableOpacity
                style={[
                  styles.generateButton,
                  (!inputText.trim() || isGenerating) && styles.disabledButton
                ]}
                onPress={handleGenerateSpeech}
                disabled={!inputText.trim() || isGenerating}
              >
                {isGenerating ? (
                  <ActivityIndicator size="small" color="white" />
                ) : (
                  <MaterialIcons name="play-circle-filled" size={24} color="white" />
                )}
              </TouchableOpacity>
            </View>
            
            {currentSpeech && (
              <SpeechControlPanel
                isPlaying={isPlaying}
                isPaused={isPaused}
                isLoading={isGenerating}
                progress={playbackProgress}
                duration={currentSpeech.duration}
                characterName={selectedCharacter.name}
                emotion={emotion}
                onPlayPause={handlePlayPause}
                onStop={handleStopSpeech}
                onSeek={handleSeek}
                onEmotionChange={setEmotion}
                speakingText={currentSpeech.transformed_text}
              />
            )}
          </>
        )}
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  backButton: {
    marginRight: 16,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  content: {
    flex: 1,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginHorizontal: 16,
    marginTop: 16,
    marginBottom: 8,
  },
  bottomPanel: {
    backgroundColor: 'white',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    paddingBottom: 16,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  textInput: {
    flex: 1,
    height: 80,
    backgroundColor: '#f0f0f0',
    borderRadius: 8,
    padding: 12,
    marginRight: 10,
    fontSize: 14,
  },
  generateButton: {
    backgroundColor: '#2196F3',
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
  },
  disabledButton: {
    backgroundColor: '#B0BEC5',
  },
});

export default VoiceCharacterScreen;