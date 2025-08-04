/**
 * Google Cloud Text-to-Speech Service
 * Implements TTS with personality support for AI Road Trip Storyteller
 */

import { Platform } from 'react-native';
import * as FileSystem from 'expo-file-system';
import { Audio } from 'expo-av';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_URL, ACCESS_TOKEN_KEY } from '../config';
import { toBackendPersonalityId } from '../constants/personalityMappings';

import { logger } from '@/services/logger';
interface TTSRequest {
  text: string;
  personalityId: string;
  voiceConfig?: VoiceConfig;
  ssml?: boolean;
}

interface VoiceConfig {
  languageCode?: string;
  name?: string;
  ssmlGender?: 'MALE' | 'FEMALE' | 'NEUTRAL';
  speakingRate?: number; // 0.25 to 4.0
  pitch?: number; // -20.0 to 20.0
  volumeGainDb?: number; // -96.0 to 16.0
}

interface AudioConfig {
  audioEncoding: 'MP3' | 'OGG_OPUS' | 'LINEAR16';
  speakingRate?: number;
  pitch?: number;
  volumeGainDb?: number;
  sampleRateHertz?: number;
  effectsProfileId?: string[];
}

// Personality to Google Voice mappings
const PERSONALITY_VOICE_MAP: Record<string, VoiceConfig> = {
  // Core personalities
  'navigator': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-J', // Professional male
    ssmlGender: 'MALE',
    speakingRate: 1.0,
    pitch: -2.0,
  },
  'friendly-guide': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-F', // Warm female
    ssmlGender: 'FEMALE',
    speakingRate: 0.95,
    pitch: 1.0,
  },
  'educational-expert': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-D', // Authoritative male
    ssmlGender: 'MALE',
    speakingRate: 0.9,
    pitch: -1.0,
  },
  
  // Event personalities
  'mickey-mouse': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-A', // Cheerful male
    ssmlGender: 'MALE',
    speakingRate: 1.1,
    pitch: 8.0, // Higher pitch for Mickey
  },
  'rock-dj': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-I', // Energetic male
    ssmlGender: 'MALE',
    speakingRate: 1.15,
    pitch: 0.0,
  },
  
  // Seasonal personalities
  'santa-claus': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-B', // Jolly male
    ssmlGender: 'MALE',
    speakingRate: 0.85,
    pitch: -4.0, // Deep voice
  },
  'halloween-narrator': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-C', // Mysterious female
    ssmlGender: 'FEMALE',
    speakingRate: 0.8,
    pitch: -3.0,
  },
  
  // Additional core personalities
  'adventurer': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-F', // Energetic voice
    ssmlGender: 'MALE',
    speakingRate: 1.15,
    pitch: 1.0,
  },
  'comedian': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-H', // Playful voice
    ssmlGender: 'MALE',
    speakingRate: 1.05,
    pitch: 0.5,
  },
  'local-expert': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-A', // Conversational voice
    ssmlGender: 'MALE',
    speakingRate: 0.95,
    pitch: -0.5,
  },
  
  // More seasonal personalities
  'cupid': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-G', // Romantic voice
    ssmlGender: 'FEMALE',
    speakingRate: 0.95,
    pitch: 3.0,
  },
  'leprechaun': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-H', // Irish-accented voice
    ssmlGender: 'MALE',
    speakingRate: 1.1,
    pitch: 2.0,
  },
  'patriot': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-D', // Strong voice
    ssmlGender: 'MALE',
    speakingRate: 0.95,
    pitch: -1.0,
  },
  'harvest-guide': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-F', // Warm voice
    ssmlGender: 'FEMALE',
    speakingRate: 0.9,
    pitch: 0.5,
  },
  
  // Specialty voice
  'inspirational': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-C', // Uplifting voice
    ssmlGender: 'FEMALE',
    speakingRate: 1.0,
    pitch: 1.5,
  },
  
  // Regional personalities
  'southern-charm': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-E', // Southern female
    ssmlGender: 'FEMALE',
    speakingRate: 0.9,
    pitch: 2.0,
  },
  'new-england-scholar': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-D', // Refined voice
    ssmlGender: 'MALE',
    speakingRate: 0.85,
    pitch: -0.5,
  },
  'midwest-neighbor': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-G', // Friendly voice
    ssmlGender: 'FEMALE',
    speakingRate: 0.95,
    pitch: 0.0,
  },
  'west-coast-cool': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-I', // Laid-back voice
    ssmlGender: 'MALE',
    speakingRate: 0.9,
    pitch: 0.0,
  },
  'mountain-sage': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-B', // Wise voice
    ssmlGender: 'MALE',
    speakingRate: 0.85,
    pitch: -2.0,
  },
  'texas-ranger': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-J', // Rugged male
    ssmlGender: 'MALE',
    speakingRate: 0.85,
    pitch: -3.0,
  },
  'jazz-storyteller': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-A', // Smooth voice
    ssmlGender: 'MALE',
    speakingRate: 0.9,
    pitch: -1.0,
  },
  'beach-vibes': {
    languageCode: 'en-US',
    name: 'en-US-Neural2-I', // Relaxed voice
    ssmlGender: 'MALE',
    speakingRate: 0.85,
    pitch: 0.5,
  },
};

class GoogleCloudTTSService {
  private audioCache: Map<string, string> = new Map();
  private cacheDirectory: string;
  private maxCacheSize: number = 50 * 1024 * 1024; // 50MB
  private currentCacheSize: number = 0;

  constructor() {
    this.cacheDirectory = `${FileSystem.documentDirectory}tts_cache/`;
    this.initializeCache();
  }

  private async initializeCache(): Promise<void> {
    try {
      // Create cache directory if it doesn't exist
      const dirInfo = await FileSystem.getInfoAsync(this.cacheDirectory);
      if (!dirInfo.exists) {
        await FileSystem.makeDirectoryAsync(this.cacheDirectory, { intermediates: true });
      }

      // Load cache index from AsyncStorage
      const cacheIndex = await AsyncStorage.getItem('tts_cache_index');
      if (cacheIndex) {
        const index = JSON.parse(cacheIndex);
        this.audioCache = new Map(Object.entries(index));
      }

      // Calculate current cache size
      await this.calculateCacheSize();
    } catch (error) {
      logger.error('Failed to initialize TTS cache:', error);
    }
  }

  async synthesizeSpeech(request: TTSRequest): Promise<string> {
    // Generate cache key
    const cacheKey = this.generateCacheKey(request);
    
    // Check cache first
    const cachedPath = this.audioCache.get(cacheKey);
    if (cachedPath) {
      const fileInfo = await FileSystem.getInfoAsync(cachedPath);
      if (fileInfo.exists) {
        return cachedPath;
      }
    }

    try {
      // Map frontend personality ID to backend format
      const backendPersonalityId = toBackendPersonalityId(request.personalityId);
      
      // Get voice config for personality
      const voiceConfig = PERSONALITY_VOICE_MAP[request.personalityId] || PERSONALITY_VOICE_MAP['navigator'];
      
      // Generate SSML if needed
      const input = request.ssml ? 
        { ssml: this.generateSSML(request.text, request.personalityId) } :
        { text: request.text };

      // Prepare TTS request
      const ttsRequest = {
        input,
        voice: {
          ...voiceConfig,
          ...request.voiceConfig, // Allow overrides
        },
        audioConfig: {
          audioEncoding: 'MP3',
          speakingRate: voiceConfig.speakingRate,
          pitch: voiceConfig.pitch,
          volumeGainDb: voiceConfig.volumeGainDb || 0,
          effectsProfileId: ['headphone-class-device'], // Optimize for headphones
        } as AudioConfig,
        personalityId: backendPersonalityId, // Include backend personality ID
      };

      // Call backend API (which will handle Google Cloud TTS)
      // Using test endpoint for now - change to /api/tts/google/synthesize in production
      const response = await fetch(`${API_URL}/api/tts/google/synthesize-test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Add auth header if available
          ...(await this.getAuthHeaders()),
        },
        body: JSON.stringify(ttsRequest),
      });

      if (!response.ok) {
        throw new Error(`TTS synthesis failed: ${response.statusText}`);
      }

      const data = await response.json();
      const audioContent = data.audioContent; // Base64 encoded audio

      // Save to file
      const fileName = `${Date.now()}_${request.personalityId}.mp3`;
      const filePath = `${this.cacheDirectory}${fileName}`;
      
      await FileSystem.writeAsStringAsync(filePath, audioContent, {
        encoding: FileSystem.EncodingType.Base64,
      });

      // Update cache
      await this.addToCache(cacheKey, filePath);

      return filePath;
    } catch (error) {
      logger.error('TTS synthesis error:', error);
      // Fallback to local generation if backend fails
      return this.generateFallbackAudio(request.text);
    }
  }

  private generateSSML(text: string, personalityId: string): string {
    const personality = PERSONALITY_VOICE_MAP[personalityId];
    if (!personality) return text;

    // Add personality-specific SSML markup
    let ssml = '<speak>';
    
    // Add emphasis and pauses based on personality
    switch (personalityId) {
      case 'mickey-mouse':
        ssml += `<prosody rate="fast" pitch="+8st">
          <emphasis level="strong">Oh boy!</emphasis>
          <break time="200ms"/>
          ${text}
        </prosody>`;
        break;
        
      case 'santa-claus':
        ssml += `<prosody rate="slow" pitch="-4st">
          <emphasis level="moderate">Ho ho ho!</emphasis>
          <break time="300ms"/>
          ${text}
        </prosody>`;
        break;
        
      case 'rock-dj':
        ssml += `<prosody rate="fast" volume="+2dB">
          <emphasis level="strong">${text}</emphasis>
        </prosody>`;
        break;
        
      case 'educational-expert':
        ssml += `<prosody rate="medium">
          ${this.addEducationalEmphasis(text)}
        </prosody>`;
        break;
        
      case 'adventurer':
        ssml += `<prosody rate="fast" pitch="+2st">
          <emphasis level="strong">${text}</emphasis>
        </prosody>`;
        break;
        
      case 'comedian':
        ssml += `<prosody rate="medium">
          ${this.addComedyTiming(text)}
        </prosody>`;
        break;
        
      case 'cupid':
        ssml += `<prosody rate="medium" pitch="+3st">
          <say-as interpret-as="expressive">${text}</say-as>
        </prosody>`;
        break;
        
      case 'leprechaun':
        ssml += `<prosody rate="fast" pitch="+2st">
          <emphasis level="moderate">Top o' the mornin'!</emphasis>
          <break time="200ms"/>
          ${text}
        </prosody>`;
        break;
        
      case 'patriot':
        ssml += `<prosody rate="medium" pitch="-1st" volume="+2dB">
          <emphasis level="strong">${text}</emphasis>
        </prosody>`;
        break;
        
      case 'inspirational':
        ssml += `<prosody rate="medium" pitch="+1st">
          ${this.addInspirationalEmphasis(text)}
        </prosody>`;
        break;
        
      case 'southern-charm':
        ssml += `<prosody rate="slow" pitch="+2st">
          <say-as interpret-as="expressive">${text}</say-as>
        </prosody>`;
        break;
        
      case 'jazz-storyteller':
        ssml += `<prosody rate="slow" pitch="-1st">
          <emphasis level="moderate">${text}</emphasis>
        </prosody>`;
        break;
        
      default:
        ssml += text;
    }
    
    ssml += '</speak>';
    return ssml;
  }

  private addEducationalEmphasis(text: string): string {
    // Add emphasis to key educational terms
    const educationalTerms = ['discover', 'learn', 'explore', 'history', 'science', 'nature'];
    let processedText = text;
    
    educationalTerms.forEach(term => {
      const regex = new RegExp(`\\b(${term})\\b`, 'gi');
      processedText = processedText.replace(regex, '<emphasis level="moderate">$1</emphasis>');
    });
    
    return processedText;
  }
  
  private addComedyTiming(text: string): string {
    // Add pauses for comedic timing
    let processedText = text;
    
    // Add pause before punchlines (after "...")
    processedText = processedText.replace(/\.\.\./g, '...<break time="500ms"/>');
    
    // Add slight pause after questions for effect
    processedText = processedText.replace(/\?/g, '?<break time="300ms"/>');
    
    return processedText;
  }
  
  private addInspirationalEmphasis(text: string): string {
    // Add emphasis to motivational keywords
    const inspirationalTerms = ['achieve', 'believe', 'dream', 'possible', 'journey', 'amazing', 'wonderful'];
    let processedText = text;
    
    inspirationalTerms.forEach(term => {
      const regex = new RegExp(`\\b(${term})\\b`, 'gi');
      processedText = processedText.replace(regex, '<emphasis level="strong">$1</emphasis>');
    });
    
    return processedText;
  }

  private generateCacheKey(request: TTSRequest): string {
    const content = request.text + request.personalityId + JSON.stringify(request.voiceConfig || {});
    // Simple hash function
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return `tts_${Math.abs(hash)}.mp3`;
  }

  private async addToCache(key: string, filePath: string): Promise<void> {
    // Check cache size
    const fileInfo = await FileSystem.getInfoAsync(filePath);
    const fileSize = fileInfo.size || 0;
    
    // Evict old files if necessary
    if (this.currentCacheSize + fileSize > this.maxCacheSize) {
      await this.evictOldestFiles(fileSize);
    }
    
    // Add to cache
    this.audioCache.set(key, filePath);
    this.currentCacheSize += fileSize;
    
    // Save cache index
    const cacheIndex = Object.fromEntries(this.audioCache);
    await AsyncStorage.setItem('tts_cache_index', JSON.stringify(cacheIndex));
  }

  private async evictOldestFiles(requiredSpace: number): Promise<void> {
    const files = await FileSystem.readDirectoryAsync(this.cacheDirectory);
    const fileStats = await Promise.all(
      files.map(async (file) => {
        const filePath = `${this.cacheDirectory}${file}`;
        const info = await FileSystem.getInfoAsync(filePath);
        return { path: filePath, modificationTime: info.modificationTime || 0, size: info.size || 0 };
      })
    );
    
    // Sort by modification time (oldest first)
    fileStats.sort((a, b) => a.modificationTime - b.modificationTime);
    
    let freedSpace = 0;
    for (const file of fileStats) {
      if (freedSpace >= requiredSpace) break;
      
      await FileSystem.deleteAsync(file.path, { idempotent: true });
      freedSpace += file.size;
      this.currentCacheSize -= file.size;
      
      // Remove from cache map
      for (const [key, path] of this.audioCache.entries()) {
        if (path === file.path) {
          this.audioCache.delete(key);
          break;
        }
      }
    }
  }

  private async calculateCacheSize(): Promise<void> {
    try {
      const files = await FileSystem.readDirectoryAsync(this.cacheDirectory);
      let totalSize = 0;
      
      for (const file of files) {
        const filePath = `${this.cacheDirectory}${file}`;
        const info = await FileSystem.getInfoAsync(filePath);
        totalSize += info.size || 0;
      }
      
      this.currentCacheSize = totalSize;
    } catch (error) {
      logger.error('Failed to calculate cache size:', error);
    }
  }

  private async generateFallbackAudio(text: string): Promise<string> {
    // This is a fallback - in production, always use server-side TTS
    logger.warn('Using fallback audio generation - no TTS available');
    
    // Create a silent audio file as placeholder
    const silentAudioBase64 = 'SUQzAwAAAAAAF1RJVDIAAAAFAAAAblVsbABUUEUxAAAABQAAAG5VbGwA//uSwAAAAAAAAAAAAAAAAAAAAAAA';
    const fileName = `fallback_${Date.now()}.mp3`;
    const filePath = `${this.cacheDirectory}${fileName}`;
    
    await FileSystem.writeAsStringAsync(filePath, silentAudioBase64, {
      encoding: FileSystem.EncodingType.Base64,
    });
    
    return filePath;
  }

  async clearCache(): Promise<void> {
    try {
      await FileSystem.deleteAsync(this.cacheDirectory, { idempotent: true });
      await FileSystem.makeDirectoryAsync(this.cacheDirectory, { intermediates: true });
      this.audioCache.clear();
      this.currentCacheSize = 0;
      await AsyncStorage.removeItem('tts_cache_index');
    } catch (error) {
      logger.error('Failed to clear TTS cache:', error);
    }
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    try {
      const token = await AsyncStorage.getItem(ACCESS_TOKEN_KEY);
      if (token) {
        return {
          'Authorization': `Bearer ${token}`,
        };
      }
    } catch (error) {
      logger.error('Failed to get auth token:', error);
    }
    return {};
  }

  getCacheSize(): number {
    return this.currentCacheSize;
  }

  async preloadPersonalityVoices(personalityIds: string[]): Promise<void> {
    // Preload common phrases for quick response
    const commonPhrases = [
      "Let's begin our journey",
      "Welcome aboard",
      "Here's an interesting fact",
      "We're approaching our destination",
    ];
    
    for (const personalityId of personalityIds) {
      for (const phrase of commonPhrases) {
        try {
          await this.synthesizeSpeech({
            text: phrase,
            personalityId,
            ssml: true,
          });
        } catch (error) {
          logger.error(`Failed to preload phrase for ${personalityId}:`, error);
        }
      }
    }
  }
}

export default new GoogleCloudTTSService();