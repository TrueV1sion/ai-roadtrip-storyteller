import * as Speech from 'expo-speech';
import Voice from '@react-native-voice/voice';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { matchVoiceCommand, VOICE_FEEDBACK, SAFETY_PROMPTS } from './voiceCommandMapping';
import { EventEmitter } from 'events';

export interface VoiceInteractionState {
  isListening: boolean;
  currentCommand: string | null;
  pendingConfirmation: boolean;
  lastAction: string | null;
  conversationContext: ConversationContext;
}

interface ConversationContext {
  previousCommands: string[];
  currentRoute: string | null;
  isPaused: boolean;
  volume: number;
  isDriving: boolean;
}

class VoiceInteractionManager extends EventEmitter {
  private state: VoiceInteractionState = {
    isListening: false,
    currentCommand: null,
    pendingConfirmation: false,
    lastAction: null,
    conversationContext: {
      previousCommands: [],
      currentRoute: null,
      isPaused: false,
      volume: 1.0,
      isDriving: true,
    },
  };

  private speechQueue: string[] = [];
  private isSpeaking = false;
  private interruptionEnabled = true;
  private safetyMode = true;

  constructor() {
    super();
    this.initializeVoice();
    this.loadUserPreferences();
  }

  private async initializeVoice() {
    try {
      // Initialize voice recognition
      Voice.onSpeechStart = this.onSpeechStart.bind(this);
      Voice.onSpeechEnd = this.onSpeechEnd.bind(this);
      Voice.onSpeechResults = this.onSpeechResults.bind(this);
      Voice.onSpeechError = this.onSpeechError.bind(this);
      Voice.onSpeechPartialResults = this.onSpeechPartialResults.bind(this);
      Voice.onSpeechVolumeChanged = this.onVolumeChanged.bind(this);

      // Check if voice recognition is available
      const isAvailable = await Voice.isAvailable();
      if (!isAvailable) {
        console.warn('Voice recognition not available');
      }
    } catch (error) {
      console.error('Failed to initialize voice:', error);
    }
  }

  private async loadUserPreferences() {
    try {
      const prefs = await AsyncStorage.getItem('voicePreferences');
      if (prefs) {
        const { safetyMode, volume } = JSON.parse(prefs);
        this.safetyMode = safetyMode ?? true;
        this.state.conversationContext.volume = volume ?? 1.0;
      }
    } catch (error) {
      console.error('Failed to load preferences:', error);
    }
  }

  // Start listening for voice commands
  public async startListening() {
    if (this.state.isListening) return;

    try {
      // Interrupt current speech if enabled
      if (this.interruptionEnabled && this.isSpeaking) {
        await this.stopSpeaking();
      }

      await Voice.start('en-US');
      this.state.isListening = true;
      this.emit('stateChange', this.state);
    } catch (error) {
      console.error('Failed to start listening:', error);
      this.speak('Sorry, I couldn\'t start listening. Please try again.');
    }
  }

  // Stop listening
  public async stopListening() {
    if (!this.state.isListening) return;

    try {
      await Voice.stop();
      this.state.isListening = false;
      this.emit('stateChange', this.state);
    } catch (error) {
      console.error('Failed to stop listening:', error);
    }
  }

  // Process speech results
  private async onSpeechResults(e: any) {
    if (!e.value || e.value.length === 0) return;

    const speechText = e.value[0];
    console.log('Speech recognized:', speechText);

    // Add to conversation history
    this.state.conversationContext.previousCommands.push(speechText);
    if (this.state.conversationContext.previousCommands.length > 10) {
      this.state.conversationContext.previousCommands.shift();
    }

    // Process the command
    await this.processVoiceCommand(speechText);
  }

  // Process voice command
  private async processVoiceCommand(input: string) {
    const result = matchVoiceCommand(input);

    if (!result) {
      this.speak(VOICE_FEEDBACK.ERROR);
      return;
    }

    const { command, params } = result;

    // Check if confirmation is needed
    if (command.requiresConfirmation && !this.state.pendingConfirmation) {
      this.state.pendingConfirmation = true;
      this.state.currentCommand = command.action;
      this.emit('confirmationNeeded', {
        action: command.action,
        params,
        message: this.formatConfirmationMessage(command.action, params),
      });
      return;
    }

    // Execute the command
    await this.executeCommand(command.action, params);
  }

  // Execute confirmed command
  private async executeCommand(action: string, params: Record<string, string>) {
    this.state.lastAction = action;
    this.state.pendingConfirmation = false;
    this.emit('stateChange', this.state);

    // Safety check for driving mode
    if (this.safetyMode && this.state.conversationContext.isDriving) {
      const requiresAttention = this.checkIfRequiresAttention(action);
      if (requiresAttention) {
        this.speak(SAFETY_PROMPTS.COMPLEX_ACTION);
        this.emit('safetyPrompt', { action, params });
        return;
      }
    }

    // Emit command event for handling by the app
    this.emit('command', { action, params });

    // Provide voice feedback
    const feedback = this.getActionFeedback(action, params);
    this.speak(feedback);
  }

  // Text-to-speech with queue management
  public async speak(text: string, options?: Speech.SpeechOptions) {
    // Add to queue
    this.speechQueue.push(text);

    // Process queue if not already speaking
    if (!this.isSpeaking) {
      await this.processSpeechQueue();
    }
  }

  // Process speech queue
  private async processSpeechQueue() {
    if (this.speechQueue.length === 0) {
      this.isSpeaking = false;
      return;
    }

    this.isSpeaking = true;
    const text = this.speechQueue.shift()!;

    try {
      await Speech.speak(text, {
        language: 'en-US',
        pitch: 1.0,
        rate: Platform.OS === 'ios' ? 0.5 : 0.75,
        volume: this.state.conversationContext.volume,
        onDone: () => this.processSpeechQueue(),
        onError: () => this.processSpeechQueue(),
      });
    } catch (error) {
      console.error('Speech error:', error);
      await this.processSpeechQueue();
    }
  }

  // Stop current speech
  public async stopSpeaking() {
    this.speechQueue = [];
    this.isSpeaking = false;
    await Speech.stop();
  }

  // Pause/Resume functionality
  public async pause() {
    this.state.conversationContext.isPaused = true;
    await this.stopSpeaking();
    await this.stopListening();
    this.emit('paused');
  }

  public async resume() {
    this.state.conversationContext.isPaused = false;
    this.emit('resumed');
    this.speak('Resumed. How can I help you?');
  }

  // Confirm pending action
  public async confirmAction() {
    if (!this.state.pendingConfirmation || !this.state.currentCommand) return;

    const action = this.state.currentCommand;
    this.state.pendingConfirmation = false;
    this.state.currentCommand = null;

    await this.executeCommand(action, {});
  }

  // Cancel pending action
  public cancelAction() {
    this.state.pendingConfirmation = false;
    this.state.currentCommand = null;
    this.emit('stateChange', this.state);
    this.speak(VOICE_FEEDBACK.ACTION_CANCELLED);
  }

  // Helper methods
  private formatConfirmationMessage(action: string, params: Record<string, string>): string {
    return VOICE_FEEDBACK.CONFIRMATION_NEEDED.replace('{action}', this.getActionDescription(action, params));
  }

  private getActionDescription(action: string, params: Record<string, string>): string {
    const descriptions: Record<string, string> = {
      NAVIGATE_TO: `navigate to ${params.destination || 'the destination'}`,
      STOP_NAVIGATION: 'stop navigation',
      BOOK_RESTAURANT: 'book a restaurant',
      BOOK_HOTEL: 'book a hotel',
      EMERGENCY: 'call emergency services',
    };

    return descriptions[action] || action.toLowerCase().replace(/_/g, ' ');
  }

  private getActionFeedback(action: string, params: Record<string, string>): string {
    const feedbackMap: Record<string, string> = {
      NAVIGATE_TO: VOICE_FEEDBACK.NAVIGATION_STARTED.replace('{destination}', params.destination || 'destination'),
      STOP_NAVIGATION: VOICE_FEEDBACK.NAVIGATION_STOPPED,
      PAUSE_NARRATION: VOICE_FEEDBACK.STORY_PAUSED,
      RESUME_NARRATION: VOICE_FEEDBACK.STORY_RESUMED,
      VOLUME_UP: VOICE_FEEDBACK.VOLUME_CHANGED.replace('{direction}', 'increased'),
      VOLUME_DOWN: VOICE_FEEDBACK.VOLUME_CHANGED.replace('{direction}', 'decreased'),
      FIND_GAS_STATION: VOICE_FEEDBACK.SEARCHING.replace('{query}', 'gas stations'),
      FIND_REST_STOP: VOICE_FEEDBACK.SEARCHING.replace('{query}', 'rest stops'),
    };

    return feedbackMap[action] || VOICE_FEEDBACK.ACTION_CONFIRMED.replace('{action}', this.getActionDescription(action, params));
  }

  private checkIfRequiresAttention(action: string): boolean {
    const attentionRequiredActions = [
      'BOOK_RESTAURANT',
      'BOOK_HOTEL',
      'BOOK_TICKETS',
      'OPEN_SETTINGS',
    ];

    return attentionRequiredActions.includes(action);
  }

  // Voice recognition callbacks
  private onSpeechStart() {
    console.log('Speech recognition started');
    this.emit('speechStart');
  }

  private onSpeechEnd() {
    console.log('Speech recognition ended');
    this.state.isListening = false;
    this.emit('speechEnd');
    this.emit('stateChange', this.state);
  }

  private onSpeechError(e: any) {
    console.error('Speech recognition error:', e);
    this.state.isListening = false;
    this.emit('speechError', e);
    this.emit('stateChange', this.state);
  }

  private onSpeechPartialResults(e: any) {
    if (e.value && e.value.length > 0) {
      this.emit('partialResults', e.value[0]);
    }
  }

  private onVolumeChanged(e: any) {
    if (e.value !== undefined) {
      this.emit('volumeChanged', e.value);
    }
  }

  // Cleanup
  public async destroy() {
    await this.stopListening();
    await this.stopSpeaking();
    Voice.destroy();
    this.removeAllListeners();
  }
}

// Export singleton instance
export const voiceInteractionManager = new VoiceInteractionManager();

// Export types
export type {
  ConversationContext,
};

export default voiceInteractionManager;