/**
 * Spatial Audio Service - Client-side 3D audio processing
 * 
 * Integrates with backend spatial audio engine for immersive soundscapes
 */

import { Audio } from 'expo-av';
import * as THREE from 'three';
import { Platform } from 'react-native';
import apiClient from './apiClient';

export interface AudioPosition3D {
  x: number; // Left(-1) to Right(1)
  y: number; // Down(-1) to Up(1)
  z: number; // Behind(-1) to Front(1)
}

export interface SpatialAudioSource {
  id: string;
  type: 'narrator' | 'character' | 'ambient' | 'navigation' | 'effect';
  position: AudioPosition3D;
  volume: number;
  sound?: Audio.Sound;
  panner?: PannerNode;
}

export interface SoundscapeConfig {
  environment: string;
  sources: Array<{
    id: string;
    type: string;
    position: AudioPosition3D;
    volume: number;
    sound: string;
    movement_path?: AudioPosition3D[];
  }>;
}

class SpatialAudioService {
  private audioContext: AudioContext | null = null;
  private listener: AudioListener | null = null;
  private activeSources: Map<string, SpatialAudioSource> = new Map();
  private masterGain: GainNode | null = null;
  private currentEnvironment: string = 'rural';
  private isInitialized: boolean = false;

  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      // Set audio mode for spatial audio
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        staysActiveInBackground: true,
        interruptionModeIOS: Audio.INTERRUPTION_MODE_IOS_DO_NOT_MIX,
        playsInSilentModeIOS: true,
        shouldDuckAndroid: true,
        interruptionModeAndroid: Audio.INTERRUPTION_MODE_ANDROID_DO_NOT_MIX,
        playThroughEarpieceAndroid: false,
      });

      // Create Web Audio API context
      if (Platform.OS === 'web') {
        this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        this.listener = this.audioContext.listener;
        this.masterGain = this.audioContext.createGain();
        this.masterGain.connect(this.audioContext.destination);
      }

      this.isInitialized = true;
      console.log('Spatial audio service initialized');
    } catch (error) {
      console.error('Failed to initialize spatial audio:', error);
    }
  }

  async coordinateWithBackend(
    audioType: string,
    locationContext: any,
    audioMetadata: any
  ): Promise<SoundscapeConfig | null> {
    try {
      const response = await apiClient.post('/orchestration/spatial-audio', {
        audio_type: audioType,
        location_context: locationContext,
        audio_metadata: audioMetadata,
      });

      if (response.data.status === 'success') {
        // Update local environment
        this.currentEnvironment = response.data.environment;
        
        // Apply soundscape configuration
        await this.applySoundscape(response.data.soundscape);
        
        return response.data.soundscape;
      }
      
      return null;
    } catch (error) {
      console.error('Failed to coordinate spatial audio with backend:', error);
      return null;
    }
  }

  async applySoundscape(soundscape: SoundscapeConfig): Promise<void> {
    // Clear existing ambient sources (keep narrator and navigation)
    for (const [id, source] of this.activeSources) {
      if (source.type === 'ambient' || source.type === 'effect') {
        await this.removeSource(id);
      }
    }

    // Add new soundscape sources
    for (const sourceConfig of soundscape.sources) {
      if (sourceConfig.type !== 'narrator') { // Narrator handled separately
        await this.addSource({
          id: sourceConfig.id,
          type: sourceConfig.type as any,
          position: sourceConfig.position,
          volume: sourceConfig.volume,
        });
      }
    }
  }

  async addSource(source: SpatialAudioSource): Promise<void> {
    if (!this.isInitialized) await this.initialize();

    try {
      // Create audio source
      const { sound } = await Audio.Sound.createAsync(
        { uri: this.getAudioUrlForSource(source) },
        { 
          shouldPlay: true, 
          isLooping: source.type === 'ambient',
          volume: source.volume,
        }
      );

      source.sound = sound;

      // Apply 3D positioning if Web Audio API is available
      if (this.audioContext && Platform.OS === 'web') {
        source.panner = await this.create3DPanner(source.position);
      } else {
        // Fallback to stereo panning for mobile
        await this.applyStereopanning(sound, source.position);
      }

      this.activeSources.set(source.id, source);
      console.log(`Added spatial audio source: ${source.id}`);
    } catch (error) {
      console.error(`Failed to add spatial audio source ${source.id}:`, error);
    }
  }

  async removeSource(sourceId: string): Promise<void> {
    const source = this.activeSources.get(sourceId);
    if (source) {
      try {
        if (source.sound) {
          await source.sound.unloadAsync();
        }
        if (source.panner) {
          source.panner.disconnect();
        }
        this.activeSources.delete(sourceId);
        console.log(`Removed spatial audio source: ${sourceId}`);
      } catch (error) {
        console.error(`Failed to remove source ${sourceId}:`, error);
      }
    }
  }

  async updateSourcePosition(sourceId: string, newPosition: AudioPosition3D): Promise<void> {
    const source = this.activeSources.get(sourceId);
    if (source) {
      source.position = newPosition;

      if (source.panner && this.audioContext) {
        // Update Web Audio API panner position
        source.panner.positionX.setValueAtTime(newPosition.x, this.audioContext.currentTime);
        source.panner.positionY.setValueAtTime(newPosition.y, this.audioContext.currentTime);
        source.panner.positionZ.setValueAtTime(newPosition.z, this.audioContext.currentTime);
      } else if (source.sound) {
        // Update stereo panning
        await this.applyStereopanning(source.sound, newPosition);
      }
    }
  }

  async updateListenerPosition(position: AudioPosition3D, heading: number): Promise<void> {
    if (this.listener && this.audioContext) {
      // Update listener position
      this.listener.positionX.setValueAtTime(position.x, this.audioContext.currentTime);
      this.listener.positionY.setValueAtTime(position.y, this.audioContext.currentTime);
      this.listener.positionZ.setValueAtTime(position.z, this.audioContext.currentTime);

      // Update listener orientation based on heading
      const rad = (heading * Math.PI) / 180;
      this.listener.forwardX.setValueAtTime(Math.sin(rad), this.audioContext.currentTime);
      this.listener.forwardY.setValueAtTime(0, this.audioContext.currentTime);
      this.listener.forwardZ.setValueAtTime(-Math.cos(rad), this.audioContext.currentTime);
    }
  }

  private async create3DPanner(position: AudioPosition3D): Promise<PannerNode> {
    if (!this.audioContext || !this.masterGain) {
      throw new Error('Audio context not initialized');
    }

    const panner = this.audioContext.createPanner();
    panner.panningModel = 'HRTF';
    panner.distanceModel = 'inverse';
    panner.refDistance = 1;
    panner.maxDistance = 10;
    panner.rolloffFactor = 1;
    panner.coneInnerAngle = 360;
    panner.coneOuterAngle = 0;
    panner.coneOuterGain = 0;

    // Set position
    panner.positionX.setValueAtTime(position.x, this.audioContext.currentTime);
    panner.positionY.setValueAtTime(position.y, this.audioContext.currentTime);
    panner.positionZ.setValueAtTime(position.z, this.audioContext.currentTime);

    panner.connect(this.masterGain);

    return panner;
  }

  private async applyStereopanning(sound: Audio.Sound, position: AudioPosition3D): Promise<void> {
    // Calculate stereo pan based on X position
    // -1 = full left, 0 = center, 1 = full right
    const pan = Math.max(-1, Math.min(1, position.x));
    
    // Calculate volume based on distance
    const distance = Math.sqrt(position.x ** 2 + position.y ** 2 + position.z ** 2);
    const volume = Math.max(0, Math.min(1, 1 / Math.max(1, distance)));

    await sound.setStatusAsync({
      pan,
      volume,
    });
  }

  private getAudioUrlForSource(source: SpatialAudioSource): string {
    // Map source types to audio URLs
    // In production, these would come from backend
    const audioMap: Record<string, string> = {
      'forest_birds_1': 'https://storage.googleapis.com/roadtrip-audio/ambient/forest_birds_1.mp3',
      'ocean_waves': 'https://storage.googleapis.com/roadtrip-audio/ambient/ocean_waves.mp3',
      'rain_medium': 'https://storage.googleapis.com/roadtrip-audio/ambient/rain_medium.mp3',
      // Add more mappings as needed
    };

    return audioMap[source.id] || '';
  }

  async setMasterVolume(volume: number): Promise<void> {
    if (this.masterGain && this.audioContext) {
      this.masterGain.gain.setValueAtTime(volume, this.audioContext.currentTime);
    }

    // Also update all active sounds for mobile
    for (const source of this.activeSources.values()) {
      if (source.sound) {
        const status = await source.sound.getStatusAsync();
        if (status.isLoaded) {
          await source.sound.setVolumeAsync(source.volume * volume);
        }
      }
    }
  }

  async pauseAllAmbient(): Promise<void> {
    for (const source of this.activeSources.values()) {
      if ((source.type === 'ambient' || source.type === 'effect') && source.sound) {
        await source.sound.pauseAsync();
      }
    }
  }

  async resumeAllAmbient(): Promise<void> {
    for (const source of this.activeSources.values()) {
      if ((source.type === 'ambient' || source.type === 'effect') && source.sound) {
        await source.sound.playAsync();
      }
    }
  }

  getActiveSourcesInfo(): Array<{ id: string; type: string; position: AudioPosition3D }> {
    return Array.from(this.activeSources.values()).map(source => ({
      id: source.id,
      type: source.type,
      position: source.position,
    }));
  }

  getCurrentEnvironment(): string {
    return this.currentEnvironment;
  }

  async cleanup(): Promise<void> {
    // Unload all sounds
    for (const source of this.activeSources.values()) {
      if (source.sound) {
        await source.sound.unloadAsync();
      }
      if (source.panner) {
        source.panner.disconnect();
      }
    }

    this.activeSources.clear();

    // Close audio context
    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }

    this.isInitialized = false;
  }
}

export const spatialAudioService = new SpatialAudioService();
export default spatialAudioService;