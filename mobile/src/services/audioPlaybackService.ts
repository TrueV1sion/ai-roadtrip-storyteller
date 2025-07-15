/**
 * Audio Playback Service
 * Handles audio playback with queue management and ducking
 */

import { Audio, AVPlaybackStatus } from 'expo-av';
import { Platform } from 'react-native';
import spatialAudioService from './spatialAudioService';

interface AudioQueueItem {
  id: string;
  uri: string;
  type: 'story' | 'navigation' | 'alert' | 'music';
  volume: number;
  priority?: 'critical' | 'high' | 'medium' | 'low';
  fadeIn?: number;
  fadeOut?: number;
  onStart?: () => void;
  onComplete?: () => void;
  onError?: (error: Error) => void;
}

interface PlaybackState {
  isPlaying: boolean;
  currentItem: AudioQueueItem | null;
  position: number;
  duration: number;
  volume: number;
}

class AudioPlaybackService {
  private sound: Audio.Sound | null = null;
  private queue: AudioQueueItem[] = [];
  private currentItem: AudioQueueItem | null = null;
  private isPlaying: boolean = false;
  private playbackStateListeners: ((state: PlaybackState) => void)[] = [];
  private backgroundMusic: Audio.Sound | null = null;
  private isMusicDucked: boolean = false;
  private storySound: Audio.Sound | null = null;
  private navigationSound: Audio.Sound | null = null;
  private pausedStoryPosition: number = 0;
  private volumeLevels = {
    story: 1.0,
    navigation: 1.0,
    music: 0.3,
    ducked: 0.2
  };

  constructor() {
    this.initializeAudio();
  }

  private async initializeAudio(): Promise<void> {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        staysActiveInBackground: true,
        playsInSilentModeIOS: true,
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
        interruptionModeIOS: Audio.INTERRUPTION_MODE_IOS_DUCK_OTHERS,
        interruptionModeAndroid: Audio.INTERRUPTION_MODE_ANDROID_DUCK_OTHERS,
      });
    } catch (error) {
      console.error('Failed to initialize audio:', error);
    }
  }

  async play(item: AudioQueueItem): Promise<void> {
    // Add to queue
    this.queue.push(item);
    
    // If not currently playing, start playback
    if (!this.isPlaying) {
      await this.playNext();
    }
  }

  async playImmediate(item: AudioQueueItem): Promise<void> {
    // Stop current playback
    await this.stop();
    
    // Clear queue and add new item
    this.queue = [item];
    await this.playNext();
  }

  private async playNext(): Promise<void> {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      this.currentItem = null;
      this.notifyStateChange();
      return;
    }

    const item = this.queue.shift()!;
    this.currentItem = item;
    this.isPlaying = true;

    try {
      // Duck background music if needed
      if (item.type === 'navigation' || item.type === 'alert') {
        await this.duckBackgroundMusic();
      }

      // Unload previous sound
      if (this.sound) {
        await this.sound.unloadAsync();
        this.sound = null;
      }

      // Create and load new sound
      const { sound } = await Audio.Sound.createAsync(
        { uri: item.uri },
        {
          shouldPlay: true,
          volume: item.volume,
          progressUpdateIntervalMillis: 100,
        },
        this.onPlaybackStatusUpdate.bind(this)
      );

      this.sound = sound;

      // Apply fade in if specified
      if (item.fadeIn && item.fadeIn > 0) {
        await this.fadeIn(sound, item.volume, item.fadeIn);
      }

      // Call onStart callback
      item.onStart?.();

      // Coordinate spatial audio if applicable
      if (item.type === 'story' || item.type === 'navigation') {
        await this.setupSpatialAudio(item);
      }

      this.notifyStateChange();
    } catch (error) {
      console.error('Playback error:', error);
      item.onError?.(error as Error);
      
      // Try next item in queue
      await this.playNext();
    }
  }

  private onPlaybackStatusUpdate = async (status: AVPlaybackStatus): Promise<void> => {
    if (!status.isLoaded) return;

    // Update state
    this.notifyStateChange();

    // Check if playback finished
    if (status.didJustFinish) {
      const completedItem = this.currentItem;

      // Apply fade out if needed
      if (completedItem?.fadeOut && completedItem.fadeOut > 0 && this.sound) {
        await this.fadeOut(this.sound, completedItem.fadeOut);
      }

      // Restore background music volume
      if (this.isMusicDucked) {
        await this.restoreBackgroundMusic();
      }

      // Call completion callback
      completedItem?.onComplete?.();

      // Play next item
      await this.playNext();
    }
  };

  async pause(): Promise<void> {
    if (this.sound && this.isPlaying) {
      await this.sound.pauseAsync();
      this.isPlaying = false;
      this.notifyStateChange();
    }
  }

  async resume(): Promise<void> {
    if (this.sound && !this.isPlaying) {
      await this.sound.playAsync();
      this.isPlaying = true;
      this.notifyStateChange();
    }
  }

  async stop(): Promise<void> {
    if (this.sound) {
      await this.sound.stopAsync();
      await this.sound.unloadAsync();
      this.sound = null;
    }
    
    this.isPlaying = false;
    this.currentItem = null;
    this.queue = [];
    this.notifyStateChange();
  }

  async setVolume(volume: number): Promise<void> {
    if (this.sound) {
      await this.sound.setVolumeAsync(Math.max(0, Math.min(1, volume)));
      this.notifyStateChange();
    }
  }

  async seek(position: number): Promise<void> {
    if (this.sound) {
      await this.sound.setPositionAsync(position);
      this.notifyStateChange();
    }
  }

  // Background music management
  async playBackgroundMusic(uri: string, volume: number = 0.3): Promise<void> {
    try {
      if (this.backgroundMusic) {
        await this.backgroundMusic.unloadAsync();
      }

      const { sound } = await Audio.Sound.createAsync(
        { uri },
        {
          shouldPlay: true,
          isLooping: true,
          volume: volume,
        }
      );

      this.backgroundMusic = sound;
    } catch (error) {
      console.error('Failed to play background music:', error);
    }
  }

  async stopBackgroundMusic(): Promise<void> {
    if (this.backgroundMusic) {
      await this.backgroundMusic.stopAsync();
      await this.backgroundMusic.unloadAsync();
      this.backgroundMusic = null;
    }
  }

  private async duckBackgroundMusic(): Promise<void> {
    if (this.backgroundMusic && !this.isMusicDucked) {
      this.isMusicDucked = true;
      await this.fadeVolume(this.backgroundMusic, 0.3, 0.1, 200);
    }
  }

  private async restoreBackgroundMusic(): Promise<void> {
    if (this.backgroundMusic && this.isMusicDucked) {
      this.isMusicDucked = false;
      await this.fadeVolume(this.backgroundMusic, 0.1, 0.3, 500);
    }
  }

  // Fade effects
  private async fadeIn(sound: Audio.Sound, targetVolume: number, duration: number): Promise<void> {
    const steps = 20;
    const stepDuration = duration / steps;
    const volumeStep = targetVolume / steps;

    for (let i = 1; i <= steps; i++) {
      await sound.setVolumeAsync(volumeStep * i);
      await new Promise(resolve => setTimeout(resolve, stepDuration));
    }
  }

  private async fadeOut(sound: Audio.Sound, duration: number): Promise<void> {
    const status = await sound.getStatusAsync();
    if (!status.isLoaded) return;

    const currentVolume = status.volume || 1;
    const steps = 20;
    const stepDuration = duration / steps;
    const volumeStep = currentVolume / steps;

    for (let i = steps - 1; i >= 0; i--) {
      await sound.setVolumeAsync(volumeStep * i);
      await new Promise(resolve => setTimeout(resolve, stepDuration));
    }
  }

  private async fadeVolume(
    sound: Audio.Sound, 
    fromVolume: number, 
    toVolume: number, 
    duration: number
  ): Promise<void> {
    const steps = 20;
    const stepDuration = duration / steps;
    const volumeDiff = toVolume - fromVolume;
    const volumeStep = volumeDiff / steps;

    for (let i = 0; i <= steps; i++) {
      await sound.setVolumeAsync(fromVolume + (volumeStep * i));
      await new Promise(resolve => setTimeout(resolve, stepDuration));
    }
  }

  // State management
  addStateListener(listener: (state: PlaybackState) => void): () => void {
    this.playbackStateListeners.push(listener);
    
    // Return unsubscribe function
    return () => {
      const index = this.playbackStateListeners.indexOf(listener);
      if (index > -1) {
        this.playbackStateListeners.splice(index, 1);
      }
    };
  }

  private async notifyStateChange(): Promise<void> {
    const state = await this.getPlaybackState();
    this.playbackStateListeners.forEach(listener => listener(state));
  }

  private async getPlaybackState(): Promise<PlaybackState> {
    let position = 0;
    let duration = 0;
    let volume = 1;

    if (this.sound) {
      const status = await this.sound.getStatusAsync();
      if (status.isLoaded) {
        position = status.positionMillis || 0;
        duration = status.durationMillis || 0;
        volume = status.volume || 1;
      }
    }

    return {
      isPlaying: this.isPlaying,
      currentItem: this.currentItem,
      position,
      duration,
      volume,
    };
  }

  // Queue management
  getQueue(): AudioQueueItem[] {
    return [...this.queue];
  }

  clearQueue(): void {
    this.queue = [];
  }

  removeFromQueue(id: string): void {
    this.queue = this.queue.filter(item => item.id !== id);
  }

  // Utility methods
  async preloadAudio(uri: string): Promise<void> {
    try {
      const { sound } = await Audio.Sound.createAsync(
        { uri },
        { shouldPlay: false }
      );
      // Immediately unload - this just validates the file exists and can be loaded
      await sound.unloadAsync();
    } catch (error) {
      console.error('Failed to preload audio:', error);
    }
  }

  async getAudioDuration(uri: string): Promise<number> {
    try {
      const { sound, status } = await Audio.Sound.createAsync(
        { uri },
        { shouldPlay: false }
      );
      
      const duration = status.isLoaded ? (status.durationMillis || 0) : 0;
      await sound.unloadAsync();
      
      return duration;
    } catch (error) {
      console.error('Failed to get audio duration:', error);
      return 0;
    }
  }

  // Navigation orchestration methods
  async handleNavigationInstruction(audioUrl: string, orchestrationAction: any, duration: number): Promise<void> {
    switch (orchestrationAction.action) {
      case 'interrupt_all':
        await this.interruptAllForNavigation(audioUrl, duration, orchestrationAction);
        break;
      case 'pause_story':
        await this.pauseStoryForNavigation(audioUrl, duration, orchestrationAction);
        break;
      case 'duck_all':
        await this.duckAllForNavigation(audioUrl, duration, orchestrationAction);
        break;
      case 'wait_for_gap':
        await this.queueNavigationForGap(audioUrl, orchestrationAction);
        break;
    }
  }

  private async interruptAllForNavigation(audioUrl: string, duration: number, action: any): Promise<void> {
    // Stop all current audio
    await this.stopAll();
    
    // Play navigation immediately
    await this.playNavigationAudio(audioUrl, this.volumeLevels.navigation);
    
    // If restore after, set timer to resume
    if (action.restore_after) {
      setTimeout(() => this.resumeAfterNavigation(), duration * 1000);
    }
  }

  private async pauseStoryForNavigation(audioUrl: string, duration: number, action: any): Promise<void> {
    // Pause story if playing
    if (this.storySound) {
      const status = await this.storySound.getStatusAsync();
      if (status.isLoaded && status.isPlaying) {
        this.pausedStoryPosition = status.positionMillis || 0;
        await this.storySound.pauseAsync();
      }
    }
    
    // Duck music
    if (this.backgroundMusic) {
      await this.duckBackgroundMusic();
    }
    
    // Play navigation with fade
    const fadeMs = action.fade_duration_ms || 1000;
    await this.playNavigationAudio(audioUrl, this.volumeLevels.navigation, fadeMs);
    
    // Resume story after navigation if specified
    if (action.restore_after) {
      setTimeout(async () => {
        if (this.storySound && this.pausedStoryPosition > 0) {
          await this.storySound.setPositionAsync(this.pausedStoryPosition);
          await this.storySound.playAsync();
          this.pausedStoryPosition = 0;
        }
        await this.restoreBackgroundMusic();
      }, duration * 1000);
    }
  }

  private async duckAllForNavigation(audioUrl: string, duration: number, action: any): Promise<void> {
    const duckLevel = action.duck_level_db || -12;
    const duckVolume = this.dbToLinear(duckLevel);
    
    // Duck all playing audio
    if (this.storySound) {
      await this.fadeVolume(this.storySound, this.volumeLevels.story, duckVolume, 200);
    }
    if (this.backgroundMusic) {
      await this.fadeVolume(this.backgroundMusic, this.volumeLevels.music, duckVolume * 0.5, 200);
    }
    
    // Play navigation
    await this.playNavigationAudio(audioUrl, this.volumeLevels.navigation);
    
    // Restore volumes after navigation
    if (action.restore_after) {
      setTimeout(async () => {
        if (this.storySound) {
          await this.fadeVolume(this.storySound, duckVolume, this.volumeLevels.story, 500);
        }
        if (this.backgroundMusic) {
          await this.fadeVolume(this.backgroundMusic, duckVolume * 0.5, this.volumeLevels.music, 500);
        }
      }, duration * 1000);
    }
  }

  private async queueNavigationForGap(audioUrl: string, action: any): Promise<void> {
    const maxWait = (action.max_wait_seconds || 10) * 1000;
    
    // Add to priority queue
    this.queue.unshift({
      id: `nav-${Date.now()}`,
      uri: audioUrl,
      type: 'navigation',
      volume: this.volumeLevels.navigation,
      priority: 'low'
    });
    
    // Set timeout to play if no gap found
    setTimeout(() => {
      const navItem = this.queue.find(item => item.uri === audioUrl);
      if (navItem) {
        this.playImmediate(navItem);
      }
    }, maxWait);
  }

  async playNavigationAudio(audioUrl: string, volume: number = 1.0, fadeIn: number = 0): Promise<void> {
    try {
      if (this.navigationSound) {
        await this.navigationSound.unloadAsync();
      }
      
      const { sound } = await Audio.Sound.createAsync(
        { uri: audioUrl },
        { 
          shouldPlay: true, 
          volume: fadeIn > 0 ? 0 : volume,
          isLooping: false
        }
      );
      
      this.navigationSound = sound;
      
      if (fadeIn > 0) {
        await this.fadeIn(sound, volume, fadeIn);
      }
      
      // Auto cleanup after playback
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          sound.unloadAsync();
          this.navigationSound = null;
        }
      });
    } catch (error) {
      console.error('Failed to play navigation audio:', error);
    }
  }

  async stopAll(): Promise<void> {
    const promises = [];
    
    if (this.sound) {
      promises.push(this.sound.stopAsync());
    }
    if (this.storySound) {
      promises.push(this.storySound.stopAsync());
    }
    if (this.navigationSound) {
      promises.push(this.navigationSound.stopAsync());
    }
    if (this.backgroundMusic) {
      promises.push(this.backgroundMusic.pauseAsync());
    }
    
    await Promise.all(promises);
  }

  async pauseStory(): Promise<void> {
    if (this.storySound) {
      const status = await this.storySound.getStatusAsync();
      if (status.isLoaded && status.isPlaying) {
        this.pausedStoryPosition = status.positionMillis || 0;
        await this.storySound.pauseAsync();
      }
    }
  }

  async resumeStory(): Promise<void> {
    if (this.storySound && this.pausedStoryPosition > 0) {
      await this.storySound.setPositionAsync(this.pausedStoryPosition);
      await this.storySound.playAsync();
      this.pausedStoryPosition = 0;
    }
  }

  async duckVolume(level: number): Promise<void> {
    const duckVolume = Math.max(0, Math.min(1, level));
    
    if (this.storySound) {
      await this.storySound.setVolumeAsync(duckVolume);
    }
    if (this.backgroundMusic) {
      await this.backgroundMusic.setVolumeAsync(duckVolume * 0.5);
    }
  }

  async restoreVolume(): Promise<void> {
    if (this.storySound) {
      await this.fadeVolume(this.storySound, null, this.volumeLevels.story, 500);
    }
    if (this.backgroundMusic) {
      await this.fadeVolume(this.backgroundMusic, null, this.volumeLevels.music, 500);
    }
  }

  isStoryPlaying(): boolean {
    return this.currentItem?.type === 'story' && this.isPlaying;
  }

  async queueNavigationAudio(audioUrl: string): Promise<void> {
    this.queue.unshift({
      id: `nav-queued-${Date.now()}`,
      uri: audioUrl,
      type: 'navigation',
      volume: this.volumeLevels.navigation,
      priority: 'low'
    });
  }

  private async resumeAfterNavigation(): Promise<void> {
    // Resume story if it was playing
    if (this.storySound && this.pausedStoryPosition > 0) {
      await this.resumeStory();
    }
    
    // Restore music volume
    await this.restoreBackgroundMusic();
  }

  private dbToLinear(db: number): number {
    return Math.pow(10, db / 20);
  }

  // Spatial audio integration
  private async setupSpatialAudio(item: AudioQueueItem): Promise<void> {
    try {
      // Initialize spatial audio if needed
      await spatialAudioService.initialize();

      // Get current location context (would come from location service)
      const locationContext = await this.getCurrentLocationContext();

      // Coordinate with backend for spatial audio configuration
      const audioMetadata = {
        type: item.type,
        id: item.id,
        priority: item.priority,
        // Add story-specific metadata if available
        ...(item.type === 'story' && {
          characters: this.currentStoryCharacters || [],
          scene: this.currentStoryScene || 'default'
        })
      };

      const soundscape = await spatialAudioService.coordinateWithBackend(
        item.type,
        locationContext,
        audioMetadata
      );

      if (soundscape) {
        console.log(`Spatial audio configured: ${soundscape.environment} environment with ${soundscape.sources.length} sources`);
      }
    } catch (error) {
      console.error('Failed to setup spatial audio:', error);
      // Continue playback without spatial audio
    }
  }

  private async getCurrentLocationContext(): Promise<any> {
    // This would integrate with location service
    // For now, return mock data
    return {
      terrain: 'rural',
      road_type: 'highway',
      weather: { condition: 'clear' },
      speed: 65,
      heading: 45,
      landmarks: [],
      population_density: 'low'
    };
  }

  // Update listener position for spatial audio
  async updateSpatialListenerPosition(location: any): Promise<void> {
    if (this.currentItem && (this.currentItem.type === 'story' || this.currentItem.type === 'navigation')) {
      await spatialAudioService.updateListenerPosition(
        { x: 0, y: 0, z: 0 }, // Driver position
        location.heading || 0
      );
    }
  }

  // Story metadata for spatial audio
  private currentStoryCharacters: any[] = [];
  private currentStoryScene: string = 'default';

  setStoryMetadata(characters: any[], scene: string): void {
    this.currentStoryCharacters = characters;
    this.currentStoryScene = scene;
  }
}

export default new AudioPlaybackService();