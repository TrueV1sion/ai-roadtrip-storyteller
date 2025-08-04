import Voice, { SpeechResultsEvent } from '@react-native-voice/voice';
import { useVoiceGuidance } from '../hooks/useVoiceGuidance';

import { logger } from '@/services/logger';
interface VoiceCommand {
  command: string;
  action: () => void;
  synonyms?: string[];
  requiresConfirmation?: boolean;
}

class VoiceInteractionManager {
  private static instance: VoiceInteractionManager;
  private isListening: boolean = false;
  private commands: VoiceCommand[] = [];
  private voiceGuidance = useVoiceGuidance();
  private confidenceThreshold: number = 0.7;

  private constructor() {
    this.setupVoiceRecognition();
  }

  static getInstance(): VoiceInteractionManager {
    if (!VoiceInteractionManager.instance) {
      VoiceInteractionManager.instance = new VoiceInteractionManager();
    }
    return VoiceInteractionManager.instance;
  }

  private async setupVoiceRecognition() {
    try {
      await Voice.isAvailable();
      Voice.onSpeechResults = this.handleSpeechResults.bind(this);
      Voice.onSpeechError = this.handleSpeechError.bind(this);
    } catch (error) {
      logger.error('Voice recognition not available:', error);
    }
  }

  private handleSpeechResults(event: SpeechResultsEvent) {
    if (!event.value || !event.value.length) return;

    const spokenText = event.value[0].toLowerCase();
    const matchedCommand = this.findMatchingCommand(spokenText);

    if (matchedCommand) {
      if (matchedCommand.requiresConfirmation) {
        this.voiceGuidance.speak(
          `Do you want to ${matchedCommand.command}? Say yes or no.`
        );
        // Set up confirmation listener
        this.listenForConfirmation(() => matchedCommand.action());
      } else {
        matchedCommand.action();
      }
    } else {
      this.voiceGuidance.speak(
        "I didn't understand that command. Please try again."
      );
    }
  }

  private findMatchingCommand(spokenText: string): VoiceCommand | null {
    return this.commands.find(cmd => {
      const variations = [
        cmd.command.toLowerCase(),
        ...(cmd.synonyms?.map(s => s.toLowerCase()) || [])
      ];
      return variations.some(v => spokenText.includes(v));
    }) || null;
  }

  private handleSpeechError(error: any) {
    logger.error('Speech recognition error:', error);
    this.voiceGuidance.speak(
      "I'm having trouble understanding. Please try again."
    );
  }

  private async listenForConfirmation(onConfirm: () => void) {
    try {
      await Voice.start('en-US');
      Voice.onSpeechResults = (event: SpeechResultsEvent) => {
        if (!event.value || !event.value.length) return;

        const response = event.value[0].toLowerCase();
        if (response.includes('yes')) {
          onConfirm();
        } else if (response.includes('no')) {
          this.voiceGuidance.speak('Command cancelled.');
        } else {
          this.voiceGuidance.speak(
            'Please say yes or no.'
          );
          this.listenForConfirmation(onConfirm);
        }
      };
    } catch (error) {
      logger.error('Error listening for confirmation:', error);
    }
  }

  async startListening(): Promise<void> {
    if (this.isListening) return;

    try {
      await Voice.start('en-US');
      this.isListening = true;
      this.voiceGuidance.speak('Listening for commands.');
    } catch (error) {
      logger.error('Error starting voice recognition:', error);
      this.voiceGuidance.speak(
        'Unable to start voice recognition. Please try again.'
      );
    }
  }

  async stopListening(): Promise<void> {
    if (!this.isListening) return;

    try {
      await Voice.stop();
      this.isListening = false;
      this.voiceGuidance.speak('Voice commands disabled.');
    } catch (error) {
      logger.error('Error stopping voice recognition:', error);
    }
  }

  registerCommand(command: VoiceCommand): void {
    this.commands.push(command);
  }

  registerCommands(commands: VoiceCommand[]): void {
    this.commands.push(...commands);
  }

  setConfidenceThreshold(threshold: number): void {
    this.confidenceThreshold = Math.max(0, Math.min(1, threshold));
  }

  // Default voice commands for navigation and playback
  registerDefaultCommands(
    onPlay: () => void,
    onPause: () => void,
    onNext: () => void,
    onPrevious: () => void,
    onStop: () => void
  ): void {
    this.registerCommands([
      {
        command: 'play',
        action: onPlay,
        synonyms: ['start', 'resume', 'continue'],
      },
      {
        command: 'pause',
        action: onPause,
        synonyms: ['hold', 'wait'],
      },
      {
        command: 'next',
        action: onNext,
        synonyms: ['skip', 'forward'],
      },
      {
        command: 'previous',
        action: onPrevious,
        synonyms: ['back', 'backward'],
      },
      {
        command: 'stop',
        action: onStop,
        synonyms: ['end', 'quit', 'exit'],
        requiresConfirmation: true,
      },
    ]);
  }
}

export default VoiceInteractionManager.getInstance(); 