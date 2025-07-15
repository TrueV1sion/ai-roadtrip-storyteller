import { ApiClient } from './api/ApiClient';
import {
  VoiceCharacterType,
  VoiceCharacterBase,
  SpeechPromptType,
  SpeechResultType,
  ThemeRequestType,
  ContextualCharacterRequestType,
  EmotionType
} from '../types/voice';
import { Audio } from 'expo-av';

class VoiceCharacterService {
  private sound: Audio.Sound | null = null;
  private currentAudioUrl: string | null = null;
  
  /**
   * Get all available voice characters
   */
  async getAllCharacters(): Promise<VoiceCharacterType[]> {
    try {
      return await ApiClient.get<VoiceCharacterType[]>('/voice-character');
    } catch (error) {
      console.error('Error getting voice characters:', error);
      throw error;
    }
  }
  
  /**
   * Get a specific voice character by ID
   */
  async getCharacter(characterId: string): Promise<VoiceCharacterType> {
    try {
      return await ApiClient.get<VoiceCharacterType>(`/voice-character/${characterId}`);
    } catch (error) {
      console.error(`Error getting voice character ${characterId}:`, error);
      throw error;
    }
  }
  
  /**
   * Create a new voice character
   */
  async createCharacter(character: VoiceCharacterBase): Promise<VoiceCharacterType> {
    try {
      return await ApiClient.post<VoiceCharacterType>('/voice-character', character);
    } catch (error) {
      console.error('Error creating voice character:', error);
      throw error;
    }
  }
  
  /**
   * Update an existing voice character
   */
  async updateCharacter(
    characterId: string, 
    updates: Partial<VoiceCharacterType>
  ): Promise<VoiceCharacterType> {
    try {
      return await ApiClient.patch<VoiceCharacterType>(`/voice-character/${characterId}`, updates);
    } catch (error) {
      console.error(`Error updating voice character ${characterId}:`, error);
      throw error;
    }
  }
  
  /**
   * Delete a voice character
   */
  async deleteCharacter(characterId: string): Promise<{ message: string }> {
    try {
      return await ApiClient.delete<{ message: string }>(`/voice-character/${characterId}`);
    } catch (error) {
      console.error(`Error deleting voice character ${characterId}:`, error);
      throw error;
    }
  }
  
  /**
   * Get voice characters that match a specific theme
   */
  async getCharactersByTheme(theme: string): Promise<VoiceCharacterType[]> {
    try {
      const request: ThemeRequestType = { theme };
      return await ApiClient.post<VoiceCharacterType[]>('/voice-character/theme', request);
    } catch (error) {
      console.error(`Error getting voice characters by theme ${theme}:`, error);
      throw error;
    }
  }
  
  /**
   * Get the most appropriate character for a theme and context
   */
  async getCharacterByContext(
    theme: string, 
    context: Record<string, any>
  ): Promise<VoiceCharacterType> {
    try {
      const request: ContextualCharacterRequestType = { theme, context };
      return await ApiClient.post<VoiceCharacterType>('/voice-character/contextual', request);
    } catch (error) {
      console.error(`Error getting contextual voice character:`, error);
      throw error;
    }
  }
  
  /**
   * Transform text based on character's personality and context
   */
  async transformText(prompt: SpeechPromptType): Promise<{ original_text: string; transformed_text: string }> {
    try {
      return await ApiClient.post<{ original_text: string; transformed_text: string }>(
        '/voice-character/transform',
        prompt
      );
    } catch (error) {
      console.error('Error transforming text:', error);
      throw error;
    }
  }
  
  /**
   * Generate speech audio for a character
   */
  async generateSpeech(prompt: SpeechPromptType): Promise<SpeechResultType> {
    try {
      return await ApiClient.post<SpeechResultType>('/voice-character/speech', prompt);
    } catch (error) {
      console.error('Error generating speech:', error);
      throw error;
    }
  }
  
  /**
   * Play speech audio
   */
  async playSpeech(audioUrl: string): Promise<void> {
    try {
      // If the same audio is already loaded, just play it
      if (this.sound && this.currentAudioUrl === audioUrl) {
        const status = await this.sound.getStatusAsync();
        if (status.isLoaded) {
          // If paused, resume
          if (status.positionMillis > 0 && !status.isPlaying) {
            await this.sound.playFromPositionAsync(status.positionMillis);
          } else {
            // Otherwise, play from beginning
            await this.sound.playFromPositionAsync(0);
          }
          return;
        }
      }
      
      // Stop any currently playing audio
      await this.stopSpeech();
      
      // Load and play the new audio
      this.sound = new Audio.Sound();
      await this.sound.loadAsync({ uri: audioUrl });
      this.currentAudioUrl = audioUrl;
      await this.sound.playAsync();
      
      // Set up completion callback
      this.sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          // Clean up after playback finishes
          this.unloadSpeech();
        }
      });
    } catch (error) {
      console.error('Error playing speech:', error);
      throw error;
    }
  }
  
  /**
   * Pause speech playback
   */
  async pauseSpeech(): Promise<void> {
    if (this.sound) {
      try {
        const status = await this.sound.getStatusAsync();
        if (status.isLoaded && status.isPlaying) {
          await this.sound.pauseAsync();
        }
      } catch (error) {
        console.error('Error pausing speech:', error);
      }
    }
  }
  
  /**
   * Stop speech playback
   */
  async stopSpeech(): Promise<void> {
    if (this.sound) {
      try {
        const status = await this.sound.getStatusAsync();
        if (status.isLoaded) {
          await this.sound.stopAsync();
          await this.unloadSpeech();
        }
      } catch (error) {
        console.error('Error stopping speech:', error);
      }
    }
  }
  
  /**
   * Unload speech from memory
   */
  private async unloadSpeech(): Promise<void> {
    if (this.sound) {
      try {
        await this.sound.unloadAsync();
        this.sound = null;
        this.currentAudioUrl = null;
      } catch (error) {
        console.error('Error unloading speech:', error);
      }
    }
  }
  
  /**
   * Get current playback status
   */
  async getPlaybackStatus(): Promise<Audio.PlaybackStatus | null> {
    if (this.sound) {
      try {
        return await this.sound.getStatusAsync();
      } catch (error) {
        console.error('Error getting playback status:', error);
        return null;
      }
    }
    return null;
  }
  
  /**
   * Seek to position
   */
  async seekToPosition(positionMillis: number): Promise<void> {
    if (this.sound) {
      try {
        const status = await this.sound.getStatusAsync();
        if (status.isLoaded) {
          await this.sound.setPositionAsync(positionMillis);
        }
      } catch (error) {
        console.error('Error seeking to position:', error);
      }
    }
  }
  
  /**
   * Generate and play speech in one step
   */
  async speakWithCharacter(
    text: string,
    characterId: string,
    emotion: EmotionType = 'neutral',
    context: Record<string, any> = {}
  ): Promise<SpeechResultType> {
    try {
      const prompt: SpeechPromptType = {
        text,
        character_id: characterId,
        emotion,
        context
      };
      
      const result = await this.generateSpeech(prompt);
      await this.playSpeech(result.audio_url);
      return result;
    } catch (error) {
      console.error('Error speaking with character:', error);
      throw error;
    }
  }
}

export const voiceCharacterService = new VoiceCharacterService();
export default voiceCharacterService;