/**
 * Voice command service using expo-av for recording and backend for transcription.
 */
// import Voice, { SpeechResultsEvent, SpeechErrorEvent } from '@react-native-voice/voice'; // Removed
import { Platform, PermissionsAndroid, Alert } from 'react-native';
import { Audio } from 'expo-av'; // Import expo-av
import * as FileSystem from 'expo-file-system'; // To read the audio file
import { apiClient } from '@services/api/ApiClient'; // Import API client using path alias

// Interfaces remain the same
export interface VoiceCommandConfig {
  wake?: string[]; // Wake words might become less relevant if activation is manual
  commands: VoiceCommand[];
}

export interface VoiceCommand {
  patterns: string[];
  action: string;
  examples?: string[];
  description?: string;
  paramRegex?: RegExp;
}

export interface RecognizedCommand {
  action: string;
  params?: string[];
  rawText: string; // The final transcript from backend
}

// Type for the backend transcription response
interface TranscriptionResponse {
    transcript: string | null;
    error?: string | null;
}

class VoiceCommandService {
  private initialized: boolean = false;
  private isListening: boolean = false; // Indicates if actively recording
  // Wake words might be handled differently now, maybe client-side pre-filtering or backend ignores them
  private wakeWords: string[] = ['app', 'story', 'travel', 'journey'];
  private commands: VoiceCommand[] = [];
  private commandCallbacks: Array<(command: RecognizedCommand) => void> = [];
  // private partialResults: string = ''; // Partial results not available with this approach

  private recording: Audio.Recording | null = null;
  private recordingSettings: Audio.RecordingOptions;
  private audioPermissionGranted: boolean = false;
  private continuousMode: boolean = false;
  private continuousTimer: NodeJS.Timeout | null = null;

  constructor() {
    // Remove Voice event handlers

    // Define recording settings (adjust as needed for quality/backend compatibility)
    this.recordingSettings = Audio.RecordingOptionsPresets.HIGH_QUALITY;
    // Example for specific settings if needed:
    // this.recordingSettings = {
    //   android: {
    //     extension: '.m4a',
    //     outputFormat: Audio.AndroidOutputFormat.MPEG_4,
    //     audioEncoder: Audio.AndroidAudioEncoder.AAC,
    //     sampleRate: 44100,
    //     numberOfChannels: 1,
    //     bitRate: 128000,
    //   },
    //   ios: {
    //     extension: '.m4a',
    //     outputFormat: Audio.IOSOutputFormat.MPEG4AAC,
    //     audioQuality: Audio.IOSAudioQuality.HIGH,
    //     sampleRate: 44100,
    //     numberOfChannels: 1,
    //     bitRate: 128000,
    //     linearPCMBitDepth: 16,
    //     linearPCMIsBigEndian: false,
    //     linearPCMIsFloat: false,
    //   },
    //   web: {}, // Add web config if needed
    // };
  }

  /**
   * Initialize the voice command service and set up commands.
   */
  async initialize(config?: VoiceCommandConfig): Promise<boolean> {
    if (this.initialized) {
      return true;
    }
    console.log('Initializing Voice Command Service (Backend STT)...');
    try {
      // Set up commands
      if (config?.commands) {
        this.commands = config.commands;
      } else {
        this.setupDefaultCommands();
      }
      // Set up wake words (might be unused now)
      if (config?.wake) { this.wakeWords = config.wake; }

      // Request audio recording permission during initialization or before first use
      this.audioPermissionGranted = await this.requestPermission();

      this.initialized = true;
      console.log('Voice Command Service Initialized (Backend STT). Permission granted:', this.audioPermissionGranted);
      return true; // Initialization successful, even if permission denied initially
    } catch (error) {
      console.error('Error initializing voice command service:', error);
      this.initialized = false;
      return false;
    }
  }

  /**
   * Request microphone permission using expo-av.
   */
  async requestPermission(): Promise<boolean> {
      console.log("Requesting audio recording permissions...");
      try {
          const { status } = await Audio.requestPermissionsAsync();
          this.audioPermissionGranted = status === 'granted';
          if (!this.audioPermissionGranted) {
              Alert.alert('Permission Denied', 'Microphone permission is required for voice commands.');
              console.warn('Audio recording permission denied.');
          } else {
              console.log('Audio recording permission granted.');
          }
          return this.audioPermissionGranted;
      } catch (err) {
          console.warn('Error requesting audio permission:', err);
          return false;
      }
  }


  // --- Default Commands Setup (remains the same) ---
  private setupDefaultCommands(): void {
    this.commands = [
      { patterns: ['play story', 'start story', 'play'], action: 'play', description: 'Start playing the current story' },
      { patterns: ['pause story', 'pause', 'stop'], action: 'pause', description: 'Pause the current story' },
      { patterns: ['resume story', 'resume', 'continue'], action: 'resume', description: 'Resume the current story' },
      { patterns: ['next story', 'next', 'skip'], action: 'next', description: 'Go to the next story' },
      { patterns: ['tell me about (.*)', 'story about (.*)'], action: 'topic', paramRegex: /tell me about (.*)|story about (.*)/i, description: 'Get a story about a specific topic' },
      { patterns: ['show location', 'location info', 'show location info'], action: 'location', description: 'Display information about the current location' }
    ];
  }

  // --- Remove react-native-voice Event Handlers ---

  /**
   * Start recording audio for voice command.
   */
  async startListening(): Promise<boolean> {
    if (!this.initialized) {
      console.warn('Voice service not initialized.');
      await this.initialize(); // Attempt to initialize if not already
      if (!this.initialized) return false;
    }
    if (this.isListening) {
        console.warn('Already recording.');
        return true;
    }

    // Ensure permission is granted
    if (!this.audioPermissionGranted) {
        const granted = await this.requestPermission();
        if (!granted) return false; // Don't start if permission denied
    }

    try {
        // Set audio mode for recording
        await Audio.setAudioModeAsync({
            allowsRecordingIOS: true,
            playsInSilentModeIOS: true, // Optional: Allow recording even if device is silent
        });

        console.log('Starting audio recording...');
        const { recording } = await Audio.Recording.createAsync(this.recordingSettings);
        this.recording = recording;
        await this.recording.startAsync();
        this.isListening = true;
        console.log('Audio recording started.');
        return true;
    } catch (error) {
      console.error('Error starting audio recording:', error);
      this.isListening = false;
      // Clean up recording object if created but failed to start
      if (this.recording) {
          await this.recording.stopAndUnloadAsync().catch(e => console.error("Error unloading failed recording:", e));
          this.recording = null;
      }
      return false;
    }
  }

  /**
   * Stop recording audio and send for transcription.
   */
  async stopListening(): Promise<void> {
    if (!this.isListening || !this.recording) {
        console.log('Not currently recording.');
        return;
    }
    console.log('Stopping audio recording...');
    try {
      await this.recording.stopAndUnloadAsync();
      const uri = this.recording.getURI();
      this.isListening = false; // Mark as not listening anymore
      this.recording = null; // Clear recording object
      console.log('Audio recording stopped. URI:', uri);

      if (uri) {
        // Read file, encode, and send
        await this.processRecordedAudio(uri);
      } else {
          console.error('Recording URI is null after stopping.');
      }

    } catch (error) {
      console.error('Error stopping audio recording:', error);
      // Ensure state is reset even on error
      this.isListening = false;
      this.recording = null;
    }
  }

  /**
   * Process the recorded audio file: read, encode, transcribe.
   */
  private async processRecordedAudio(uri: string): Promise<void> {
      try {
          console.log('Reading audio file:', uri);
          const audioBase64 = await FileSystem.readAsStringAsync(uri, {
              encoding: FileSystem.EncodingType.Base64,
          });
          console.log('Audio file read and encoded to base64.');

          // Send for transcription
          await this.sendAudioForTranscription(audioBase64);

          // Optionally delete the local file after processing
          // await FileSystem.deleteAsync(uri);
          // console.log('Deleted local audio file:', uri);

      } catch (error) {
          console.error('Error processing recorded audio:', error);
          Alert.alert('Processing Error', 'Could not process recorded audio.');
      }
  }

  /**
   * Send base64 encoded audio to the backend for transcription.
   */
  private async sendAudioForTranscription(audioBase64: string): Promise<void> {
      console.log('Sending audio to backend for transcription...');
      try {
          const response: TranscriptionResponse = await apiClient.post('/api/stt/transcribe', {
              audio_base64: audioBase64,
              language_code: 'en-US' // Or make configurable
          });

          if (response.error) {
              console.error('Backend transcription error:', response.error);
              Alert.alert('Transcription Error', response.error);
          } else if (response.transcript) {
              console.log('Transcription received:', response.transcript);
              // Process the transcript using existing command logic
              this.processCommand(response.transcript);
              
              // If in continuous mode, restart listening after a short delay
              if (this.continuousMode) {
                  this.continuousTimer = setTimeout(() => {
                      this.startListening();
                  }, 500);
              }
          } else {
              console.warn('Backend returned no transcript and no error.');
              // Handle case with no transcript (e.g., silence)
              
              // Still restart in continuous mode
              if (this.continuousMode) {
                  this.continuousTimer = setTimeout(() => {
                      this.startListening();
                  }, 500);
              }
          }
      } catch (error: any) {
          console.error('Error sending audio for transcription:', error);
          Alert.alert('API Error', `Failed to get transcription: ${error.message}`);
      }
  }


  /**
   * Destroy the service, unload recordings, etc. (No Voice listeners to remove now)
   */
  async destroy(): Promise<void> {
      console.log('Destroying Voice Command Service...');
      if (this.isListening && this.recording) {
          console.log('Unloading active recording...');
          await this.recording.stopAndUnloadAsync().catch(e => console.error("Error unloading recording on destroy:", e));
      }
      // Reset state
      this.initialized = false;
      this.isListening = false;
      this.recording = null;
      this.commandCallbacks = [];
      console.log('Voice Command Service destroyed.');
  }


  // --- Command Processing Logic (Adjusted) ---
  private processCommand(transcript: string): boolean {
    console.log(`Processing transcript: "${transcript}"`);

    // Wake word check might be less relevant now, or handled differently
    // const containsWakeWord = this.wakeWords.some(word => ...);
    // if (!containsWakeWord) ...

    // Use the full transcript for matching
    const commandText = transcript.trim();

    for (const command of this.commands) {
      const patternToMatch = command.paramRegex ? command.paramRegex : new RegExp(command.patterns.join('|'), 'i');
      const match = commandText.match(patternToMatch);

      if (match) {
        console.log(`Matched command: ${command.action}`);
        let params: string[] | undefined;

        if (command.paramRegex && match) {
           params = match.slice(1).filter(m => m !== undefined).map(p => p.trim());
           console.log('Extracted params:', params);
        }

        const recognizedCommand: RecognizedCommand = {
          action: command.action,
          params,
          rawText: transcript // Store the final transcript
        };

        this.commandCallbacks.forEach(callback => {
          try { callback(recognizedCommand); } catch (error) { console.error('Error in command callback:', error); }
        });
        return true;
      }
    }
    console.log('No command matched.');
    return false;
  }

  // --- Callback Management and Command Getters/Setters (remain the same) ---
  addCommandCallback(callback: (command: RecognizedCommand) => void): void { this.commandCallbacks.push(callback); }
  removeCommandCallback(callback: (command: RecognizedCommand) => void): void { this.commandCallbacks = this.commandCallbacks.filter(cb => cb !== callback); }
  getAvailableCommands(): VoiceCommand[] { return [...this.commands]; }
  addCommand(command: VoiceCommand): void { this.commands.push(command); }
  removeCommand(action: string): boolean {
      const initialLength = this.commands.length;
      this.commands = this.commands.filter(cmd => cmd.action !== action);
      return this.commands.length < initialLength;
  }
  getWakeWords(): string[] { return [...this.wakeWords]; }
  setWakeWords(wakeWords: string[]): void { this.wakeWords = wakeWords; }
  isActive(): boolean { return this.isListening; } // Now indicates recording status
  
  /**
   * Set continuous listening mode
   */
  setContinuousMode(enabled: boolean): void {
    this.continuousMode = enabled;
    if (!enabled && this.continuousTimer) {
      clearTimeout(this.continuousTimer);
      this.continuousTimer = null;
    }
  }
}

// Singleton instance
export const voiceCommandService = new VoiceCommandService();
export default voiceCommandService;
