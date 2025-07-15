/**
 * Advanced Audio Manager for Mobile
 * Handles all audio streams with spatial positioning and intelligent mixing
 */

import { Audio, AVPlaybackStatus } from 'expo-av';
import { EventEmitter } from 'events';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

export enum AudioCategory {
  VOICE = 'voice',
  MUSIC = 'music',
  NAVIGATION = 'navigation',
  AMBIENT = 'ambient',
  EFFECT = 'effect'
}

export enum AudioPriority {
  CRITICAL = 5,
  HIGH = 4,
  MEDIUM = 3,
  LOW = 2,
  MINIMAL = 1
}

interface AudioStream {
  id: string;
  sound: Audio.Sound;
  category: AudioCategory;
  priority: AudioPriority;
  volume: number;
  isPlaying: boolean;
  isDucked: boolean;
  originalVolume?: number;
  metadata?: any;
}

interface DuckingConfig {
  targetVolume: number;
  fadeTime: number;
  categories: AudioCategory[];
}

class AudioManager extends EventEmitter {
  private streams: Map<string, AudioStream> = new Map();
  private categoryVolumes: Map<AudioCategory, number> = new Map();
  private masterVolume: number = 1.0;
  private isInitialized: boolean = false;
  
  // Ducking configurations
  private duckingRules: Map<AudioCategory, DuckingConfig> = new Map([
    [AudioCategory.NAVIGATION, {
      targetVolume: 0.2,
      fadeTime: 300,
      categories: [AudioCategory.MUSIC, AudioCategory.AMBIENT]
    }],
    [AudioCategory.VOICE, {
      targetVolume: 0.3,
      fadeTime: 500,
      categories: [AudioCategory.MUSIC, AudioCategory.AMBIENT, AudioCategory.EFFECT]
    }]
  ]);

  constructor() {
    super();
    this.initializeCategoryVolumes();
  }

  private initializeCategoryVolumes() {
    this.categoryVolumes.set(AudioCategory.VOICE, 1.0);
    this.categoryVolumes.set(AudioCategory.NAVIGATION, 1.0);
    this.categoryVolumes.set(AudioCategory.MUSIC, 0.3);
    this.categoryVolumes.set(AudioCategory.AMBIENT, 0.4);
    this.categoryVolumes.set(AudioCategory.EFFECT, 0.7);
  }

  async initialize() {
    if (this.isInitialized) return;

    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        staysActiveInBackground: true,
        playsInSilentModeIOS: true,
        shouldDuckAndroid: true,
        interruptionModeIOS: Audio.INTERRUPTION_MODE_IOS_MIX_WITH_OTHERS,
        interruptionModeAndroid: Audio.INTERRUPTION_MODE_ANDROID_DUCK_OTHERS,
      });

      // Load saved preferences
      await this.loadPreferences();
      
      this.isInitialized = true;
      this.emit('initialized');
    } catch (error) {
      console.error('Failed to initialize AudioManager:', error);
      this.emit('error', error);
    }
  }

  /**
   * Play audio with intelligent mixing and ducking
   */
  async playAudio(
    uri: string,
    category: AudioCategory,
    options: {
      priority?: AudioPriority;
      volume?: number;
      loop?: boolean;
      metadata?: any;
    } = {}
  ): Promise<string> {
    const streamId = `${category}_${Date.now()}`;
    const priority = options.priority || this.getDefaultPriority(category);
    
    try {
      // Create and load sound
      const { sound } = await Audio.Sound.createAsync(
        { uri },
        {
          shouldPlay: true,
          isLooping: options.loop || false,
          volume: (options.volume || 1.0) * this.getCategoryVolume(category) * this.masterVolume
        }
      );

      // Set up playback status updates
      sound.setOnPlaybackStatusUpdate((status) => {
        this.handlePlaybackStatusUpdate(streamId, status);
      });

      // Create stream
      const stream: AudioStream = {
        id: streamId,
        sound,
        category,
        priority,
        volume: options.volume || 1.0,
        isPlaying: true,
        isDucked: false,
        metadata: options.metadata
      };

      this.streams.set(streamId, stream);

      // Apply ducking if needed
      if (this.shouldDuckOthers(category)) {
        await this.applyDucking(streamId);
      }

      this.emit('streamStarted', { streamId, category, priority });
      
      return streamId;
    } catch (error) {
      console.error('Failed to play audio:', error);
      this.emit('error', error);
      throw error;
    }
  }

  /**
   * Stop audio stream with optional fade out
   */
  async stopAudio(streamId: string, fadeOut: number = 0) {
    const stream = this.streams.get(streamId);
    if (!stream) return;

    try {
      if (fadeOut > 0) {
        await this.fadeOut(streamId, fadeOut);
      }

      await stream.sound.stopAsync();
      await stream.sound.unloadAsync();
      
      this.streams.delete(streamId);

      // Restore ducked streams if this was ducking others
      if (this.shouldDuckOthers(stream.category)) {
        await this.restoreDuckedStreams();
      }

      this.emit('streamStopped', { streamId });
    } catch (error) {
      console.error('Failed to stop audio:', error);
      this.emit('error', error);
    }
  }

  /**
   * Update category volume
   */
  async setCategoryVolume(category: AudioCategory, volume: number) {
    this.categoryVolumes.set(category, Math.max(0, Math.min(1, volume)));
    
    // Update all streams in this category
    for (const [streamId, stream] of this.streams) {
      if (stream.category === category) {
        await this.updateStreamVolume(streamId);
      }
    }

    await this.savePreferences();
  }

  /**
   * Update master volume
   */
  async setMasterVolume(volume: number) {
    this.masterVolume = Math.max(0, Math.min(1, volume));
    
    // Update all streams
    for (const streamId of this.streams.keys()) {
      await this.updateStreamVolume(streamId);
    }

    await this.savePreferences();
  }

  /**
   * Handle driving mode changes
   */
  async setDrivingMode(enabled: boolean) {
    if (enabled) {
      // Boost voice and navigation for driving
      await this.setCategoryVolume(AudioCategory.VOICE, 1.2);
      await this.setCategoryVolume(AudioCategory.NAVIGATION, 1.2);
      await this.setCategoryVolume(AudioCategory.MUSIC, 0.2);
      await this.setCategoryVolume(AudioCategory.AMBIENT, 0.2);
    } else {
      // Restore normal volumes
      await this.setCategoryVolume(AudioCategory.VOICE, 1.0);
      await this.setCategoryVolume(AudioCategory.NAVIGATION, 1.0);
      await this.setCategoryVolume(AudioCategory.MUSIC, 0.3);
      await this.setCategoryVolume(AudioCategory.AMBIENT, 0.4);
    }
  }

  /**
   * Handle speed-based audio adjustments
   */
  async handleSpeedChange(speed: number) {
    if (speed > 70) {
      // Highway speeds - reduce ambient sounds
      await this.setCategoryVolume(AudioCategory.AMBIENT, 0.2);
      await this.setCategoryVolume(AudioCategory.MUSIC, 0.25);
    } else if (speed < 30) {
      // City speeds - normal ambient levels
      await this.setCategoryVolume(AudioCategory.AMBIENT, 0.4);
      await this.setCategoryVolume(AudioCategory.MUSIC, 0.3);
    }
  }

  /**
   * Get current audio state
   */
  getAudioState() {
    const activeStreams = Array.from(this.streams.entries()).map(([id, stream]) => ({
      id,
      category: stream.category,
      priority: stream.priority,
      volume: stream.volume,
      isPlaying: stream.isPlaying,
      isDucked: stream.isDucked
    }));

    return {
      masterVolume: this.masterVolume,
      categoryVolumes: Object.fromEntries(this.categoryVolumes),
      activeStreams,
      streamCount: this.streams.size
    };
  }

  // Private helper methods

  private getCategoryVolume(category: AudioCategory): number {
    return this.categoryVolumes.get(category) || 1.0;
  }

  private getDefaultPriority(category: AudioCategory): AudioPriority {
    const priorities = {
      [AudioCategory.NAVIGATION]: AudioPriority.CRITICAL,
      [AudioCategory.VOICE]: AudioPriority.HIGH,
      [AudioCategory.EFFECT]: AudioPriority.MEDIUM,
      [AudioCategory.MUSIC]: AudioPriority.LOW,
      [AudioCategory.AMBIENT]: AudioPriority.MINIMAL
    };
    return priorities[category] || AudioPriority.MEDIUM;
  }

  private shouldDuckOthers(category: AudioCategory): boolean {
    return this.duckingRules.has(category);
  }

  private async applyDucking(triggerStreamId: string) {
    const triggerStream = this.streams.get(triggerStreamId);
    if (!triggerStream) return;

    const duckingConfig = this.duckingRules.get(triggerStream.category);
    if (!duckingConfig) return;

    for (const [streamId, stream] of this.streams) {
      if (streamId === triggerStreamId) continue;
      
      // Duck streams in specified categories
      if (duckingConfig.categories.includes(stream.category)) {
        stream.originalVolume = stream.volume;
        stream.isDucked = true;
        
        await this.fadeVolume(
          streamId,
          stream.volume * duckingConfig.targetVolume,
          duckingConfig.fadeTime
        );
      }
    }
  }

  private async restoreDuckedStreams() {
    for (const [streamId, stream] of this.streams) {
      if (stream.isDucked && stream.originalVolume !== undefined) {
        stream.isDucked = false;
        await this.fadeVolume(streamId, stream.originalVolume, 800);
        stream.originalVolume = undefined;
      }
    }
  }

  private async updateStreamVolume(streamId: string) {
    const stream = this.streams.get(streamId);
    if (!stream) return;

    const finalVolume = stream.volume * 
                       this.getCategoryVolume(stream.category) * 
                       this.masterVolume;
    
    try {
      await stream.sound.setVolumeAsync(finalVolume);
    } catch (error) {
      console.error('Failed to update stream volume:', error);
    }
  }

  private async fadeVolume(streamId: string, targetVolume: number, duration: number) {
    const stream = this.streams.get(streamId);
    if (!stream) return;

    const startVolume = stream.volume;
    const startTime = Date.now();
    const volumeChange = targetVolume - startVolume;

    const fade = async () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      const currentVolume = startVolume + (volumeChange * progress);
      stream.volume = currentVolume;
      await this.updateStreamVolume(streamId);

      if (progress < 1 && this.streams.has(streamId)) {
        setTimeout(fade, 50);
      }
    };

    await fade();
  }

  private async fadeOut(streamId: string, duration: number) {
    await this.fadeVolume(streamId, 0, duration);
  }

  private handlePlaybackStatusUpdate(streamId: string, status: AVPlaybackStatus) {
    if (!status.isLoaded) return;

    const stream = this.streams.get(streamId);
    if (!stream) return;

    stream.isPlaying = status.isPlaying;

    if (status.didJustFinish && !status.isLooping) {
      this.stopAudio(streamId);
    }

    this.emit('playbackStatusUpdate', { streamId, status });
  }

  private async loadPreferences() {
    try {
      const stored = await AsyncStorage.getItem('@audio_preferences');
      if (stored) {
        const prefs = JSON.parse(stored);
        this.masterVolume = prefs.masterVolume || 1.0;
        
        if (prefs.categoryVolumes) {
          Object.entries(prefs.categoryVolumes).forEach(([category, volume]) => {
            this.categoryVolumes.set(category as AudioCategory, volume as number);
          });
        }
      }
    } catch (error) {
      console.error('Failed to load audio preferences:', error);
    }
  }

  private async savePreferences() {
    try {
      const prefs = {
        masterVolume: this.masterVolume,
        categoryVolumes: Object.fromEntries(this.categoryVolumes)
      };
      await AsyncStorage.setItem('@audio_preferences', JSON.stringify(prefs));
    } catch (error) {
      console.error('Failed to save audio preferences:', error);
    }
  }

  /**
   * Clean up all audio resources
   */
  async cleanup() {
    for (const streamId of Array.from(this.streams.keys())) {
      await this.stopAudio(streamId);
    }
    this.streams.clear();
    this.removeAllListeners();
  }
}

// Export singleton instance
export const audioManager = new AudioManager();
export default audioManager;