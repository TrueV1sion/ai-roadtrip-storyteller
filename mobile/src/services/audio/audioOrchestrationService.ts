/**
 * Audio Orchestration Service
 * Manages the interplay between different audio sources:
 * - Navigation voice instructions
 * - Story narration
 * - Background music/ambient sounds
 * - Spatial audio effects
 */

import { Audio } from 'expo-av';
import { EventEmitter } from 'eventemitter3';

type AudioPriority = 'navigation' | 'story' | 'balanced';
type AudioSource = 'navigation' | 'story' | 'music' | 'ambient' | 'effect';

interface AudioLayer {
  source: AudioSource;
  sound: Audio.Sound | null;
  volume: number;
  targetVolume: number;
  priority: number;
  isDucked: boolean;
  isFading: boolean;
}

interface OrchestrationConfig {
  audioPriority: AudioPriority;
  duckingEnabled: boolean;
  crossfadeEnabled: boolean;
  fadeDuration: number;
  duckingLevel: number;
}

class AudioOrchestrationService extends EventEmitter {
  private audioLayers: Map<AudioSource, AudioLayer> = new Map();
  private config: OrchestrationConfig = {
    audioPriority: 'balanced',
    duckingEnabled: true,
    crossfadeEnabled: true,
    fadeDuration: 500, // ms
    duckingLevel: 0.3, // 30% volume when ducked
  };
  
  private fadeIntervals: Map<AudioSource, NodeJS.Timeout> = new Map();
  
  constructor() {
    super();
    this.initializeAudioLayers();
  }
  
  /**
   * Initialize audio layers with default settings
   */
  private initializeAudioLayers() {
    // Define audio layers with their default priorities
    const layers: Array<[AudioSource, number]> = [
      ['navigation', 100], // Highest priority
      ['story', 80],
      ['effect', 60],
      ['music', 40],
      ['ambient', 20], // Lowest priority
    ];
    
    layers.forEach(([source, priority]) => {
      this.audioLayers.set(source, {
        source,
        sound: null,
        volume: 1.0,
        targetVolume: 1.0,
        priority,
        isDucked: false,
        isFading: false,
      });
    });
  }
  
  /**
   * Register a sound with the orchestration service
   */
  async registerSound(source: AudioSource, sound: Audio.Sound, volume: number = 1.0): Promise<void> {
    const layer = this.audioLayers.get(source);
    if (!layer) {
      console.warn(`Unknown audio source: ${source}`);
      return;
    }
    
    layer.sound = sound;
    layer.volume = volume;
    layer.targetVolume = volume;
    
    // Set initial volume
    await sound.setVolumeAsync(volume);
    
    // Apply current orchestration state
    await this.applyOrchestration();
    
    this.emit('soundRegistered', { source, sound });
  }
  
  /**
   * Unregister a sound from the orchestration service
   */
  async unregisterSound(source: AudioSource): Promise<void> {
    const layer = this.audioLayers.get(source);
    if (!layer) return;
    
    // Clear any ongoing fades
    const fadeInterval = this.fadeIntervals.get(source);
    if (fadeInterval) {
      clearInterval(fadeInterval);
      this.fadeIntervals.delete(source);
    }
    
    layer.sound = null;
    layer.isDucked = false;
    layer.isFading = false;
    
    this.emit('soundUnregistered', { source });
  }
  
  /**
   * Pause story narration (for navigation instructions)
   */
  async pauseStory(): Promise<void> {
    const storyLayer = this.audioLayers.get('story');
    if (!storyLayer?.sound) return;
    
    if (this.config.crossfadeEnabled) {
      await this.fadeOut('story');
    }
    
    const status = await storyLayer.sound.getStatusAsync();
    if (status.isLoaded && status.isPlaying) {
      await storyLayer.sound.pauseAsync();
      this.emit('storyPaused');
    }
  }
  
  /**
   * Resume story narration
   */
  async resumeStory(): Promise<void> {
    const storyLayer = this.audioLayers.get('story');
    if (!storyLayer?.sound) return;
    
    const status = await storyLayer.sound.getStatusAsync();
    if (status.isLoaded && !status.isPlaying) {
      await storyLayer.sound.playAsync();
      
      if (this.config.crossfadeEnabled) {
        await this.fadeIn('story');
      }
      
      this.emit('storyResumed');
    }
  }
  
  /**
   * Duck audio layers based on priority
   */
  async duckAudio(prioritySource: AudioSource): Promise<void> {
    if (!this.config.duckingEnabled) return;
    
    const priorityLayer = this.audioLayers.get(prioritySource);
    if (!priorityLayer) return;
    
    // Duck all lower priority layers
    for (const [source, layer] of this.audioLayers) {
      if (source !== prioritySource && layer.priority < priorityLayer.priority && layer.sound) {
        layer.isDucked = true;
        await this.setLayerVolume(source, layer.volume * this.config.duckingLevel);
      }
    }
    
    this.emit('audioDucked', { source: prioritySource });
  }
  
  /**
   * Remove ducking from audio layers
   */
  async unduckAudio(): Promise<void> {
    for (const [source, layer] of this.audioLayers) {
      if (layer.isDucked && layer.sound) {
        layer.isDucked = false;
        await this.setLayerVolume(source, layer.targetVolume);
      }
    }
    
    this.emit('audioUndocked');
  }
  
  /**
   * Fade in audio source
   */
  private async fadeIn(source: AudioSource): Promise<void> {
    const layer = this.audioLayers.get(source);
    if (!layer?.sound || layer.isFading) return;
    
    layer.isFading = true;
    const startVolume = 0;
    const endVolume = layer.targetVolume;
    const steps = 20;
    const stepDuration = this.config.fadeDuration / steps;
    const volumeStep = (endVolume - startVolume) / steps;
    
    await layer.sound.setVolumeAsync(startVolume);
    let currentStep = 0;
    
    const fadeInterval = setInterval(async () => {
      currentStep++;
      const newVolume = startVolume + (volumeStep * currentStep);
      
      if (layer.sound) {
        await layer.sound.setVolumeAsync(Math.min(newVolume, endVolume));
      }
      
      if (currentStep >= steps) {
        clearInterval(fadeInterval);
        this.fadeIntervals.delete(source);
        layer.isFading = false;
        layer.volume = endVolume;
      }
    }, stepDuration);
    
    this.fadeIntervals.set(source, fadeInterval);
  }
  
  /**
   * Fade out audio source
   */
  private async fadeOut(source: AudioSource): Promise<void> {
    const layer = this.audioLayers.get(source);
    if (!layer?.sound || layer.isFading) return;
    
    layer.isFading = true;
    const startVolume = layer.volume;
    const endVolume = 0;
    const steps = 20;
    const stepDuration = this.config.fadeDuration / steps;
    const volumeStep = (endVolume - startVolume) / steps;
    
    let currentStep = 0;
    
    const fadeInterval = setInterval(async () => {
      currentStep++;
      const newVolume = startVolume + (volumeStep * currentStep);
      
      if (layer.sound) {
        await layer.sound.setVolumeAsync(Math.max(newVolume, 0));
      }
      
      if (currentStep >= steps) {
        clearInterval(fadeInterval);
        this.fadeIntervals.delete(source);
        layer.isFading = false;
        layer.volume = endVolume;
      }
    }, stepDuration);
    
    this.fadeIntervals.set(source, fadeInterval);
  }
  
  /**
   * Set volume for a specific layer
   */
  private async setLayerVolume(source: AudioSource, volume: number): Promise<void> {
    const layer = this.audioLayers.get(source);
    if (!layer?.sound) return;
    
    layer.volume = Math.max(0, Math.min(1, volume));
    await layer.sound.setVolumeAsync(layer.volume);
  }
  
  /**
   * Apply current orchestration rules
   */
  private async applyOrchestration(): Promise<void> {
    // Check for active high-priority sounds
    const activeSounds = Array.from(this.audioLayers.values())
      .filter(layer => layer.sound !== null)
      .sort((a, b) => b.priority - a.priority);
    
    if (activeSounds.length === 0) return;
    
    // Apply ducking based on priority
    const highestPriority = activeSounds[0];
    
    for (const layer of activeSounds) {
      if (layer !== highestPriority && this.config.duckingEnabled) {
        const shouldDuck = highestPriority.priority - layer.priority > 20;
        if (shouldDuck && !layer.isDucked) {
          layer.isDucked = true;
          await this.setLayerVolume(layer.source, layer.targetVolume * this.config.duckingLevel);
        }
      }
    }
  }
  
  /**
   * Update orchestration configuration
   */
  updateConfig(config: Partial<OrchestrationConfig>): void {
    this.config = { ...this.config, ...config };
    this.emit('configUpdated', this.config);
  }
  
  /**
   * Get current orchestration state
   */
  getOrchestrationState(): {
    config: OrchestrationConfig;
    layers: Array<{
      source: AudioSource;
      hasSound: boolean;
      volume: number;
      isDucked: boolean;
      isFading: boolean;
    }>;
  } {
    const layers = Array.from(this.audioLayers.values()).map(layer => ({
      source: layer.source,
      hasSound: layer.sound !== null,
      volume: layer.volume,
      isDucked: layer.isDucked,
      isFading: layer.isFading,
    }));
    
    return {
      config: this.config,
      layers,
    };
  }
  
  /**
   * Handle navigation instruction start
   */
  async onNavigationInstructionStart(): Promise<void> {
    await this.duckAudio('navigation');
    
    // Pause story if configured
    if (this.config.audioPriority === 'navigation') {
      await this.pauseStory();
    }
  }
  
  /**
   * Handle navigation instruction end
   */
  async onNavigationInstructionEnd(): Promise<void> {
    await this.unduckAudio();
    
    // Resume story if it was paused
    if (this.config.audioPriority === 'navigation') {
      await this.resumeStory();
    }
  }
  
  /**
   * Clean up all audio layers
   */
  async cleanup(): Promise<void> {
    // Clear all fade intervals
    for (const interval of this.fadeIntervals.values()) {
      clearInterval(interval);
    }
    this.fadeIntervals.clear();
    
    // Unregister all sounds
    for (const source of this.audioLayers.keys()) {
      await this.unregisterSound(source);
    }
    
    this.removeAllListeners();
  }
}

export const audioOrchestrationService = new AudioOrchestrationService();