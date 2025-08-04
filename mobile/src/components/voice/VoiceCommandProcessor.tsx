import React, { useEffect, useRef } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import Voice from '@react-native-voice/voice';
import { voiceService } from '../../services/voice/voiceService';
import { navigationService } from '../../services/navigation/navigationService';
import { api } from '../../services/api/ApiClient';

import { logger } from '@/services/logger';
interface Command {
  type: 'navigation' | 'booking' | 'story' | 'settings' | 'query' | 'control';
  action: string;
  parameters: any;
  confidence: number;
}

interface VoiceCommandProcessorProps {
  onCommandProcessed?: (command: Command) => void;
  onError?: (error: Error) => void;
  continuousListening?: boolean;
}

export const VoiceCommandProcessor: React.FC<VoiceCommandProcessorProps> = ({
  onCommandProcessed,
  onError,
  continuousListening = false,
}) => {
  const appState = useRef(AppState.currentState);
  const isProcessing = useRef(false);
  const commandQueue = useRef<string[]>([]);
  
  useEffect(() => {
    // Setup voice recognition handlers
    Voice.onSpeechResults = handleSpeechResults;
    Voice.onSpeechError = handleSpeechError;
    Voice.onSpeechPartialResults = handlePartialResults;
    
    // Handle app state changes
    const subscription = AppState.addEventListener('change', handleAppStateChange);
    
    // Start continuous listening if enabled
    if (continuousListening) {
      startContinuousListening();
    }
    
    return () => {
      subscription.remove();
      Voice.destroy().then(Voice.removeAllListeners);
    };
  }, [continuousListening]);
  
  const handleAppStateChange = (nextAppState: AppStateStatus) => {
    if (appState.current.match(/inactive|background/) && nextAppState === 'active') {
      // Resume listening when app comes to foreground
      if (continuousListening) {
        startContinuousListening();
      }
    } else if (nextAppState.match(/inactive|background/)) {
      // Stop listening when app goes to background
      Voice.stop();
    }
    appState.current = nextAppState;
  };
  
  const startContinuousListening = async () => {
    try {
      await Voice.start('en-US');
    } catch (error) {
      logger.error('Error starting continuous listening:', error);
    }
  };
  
  const handleSpeechResults = async (e: any) => {
    if (e.value && e.value[0] && !isProcessing.current) {
      const speechText = e.value[0];
      commandQueue.current.push(speechText);
      processCommandQueue();
    }
    
    // Restart continuous listening
    if (continuousListening) {
      setTimeout(() => startContinuousListening(), 100);
    }
  };
  
  const handlePartialResults = (e: any) => {
    // Use partial results for real-time feedback
    if (e.value && e.value[0]) {
      // Could show partial recognition in UI
    }
  };
  
  const handleSpeechError = (e: any) => {
    logger.error('Speech recognition error:', e);
    if (onError) {
      onError(new Error(e.error?.message || 'Speech recognition failed'));
    }
    
    // Restart continuous listening after error
    if (continuousListening) {
      setTimeout(() => startContinuousListening(), 1000);
    }
  };
  
  const processCommandQueue = async () => {
    if (isProcessing.current || commandQueue.current.length === 0) {
      return;
    }
    
    isProcessing.current = true;
    const commandText = commandQueue.current.shift()!;
    
    try {
      const command = await parseCommand(commandText);
      
      if (command.confidence > 0.7) {
        await executeCommand(command);
        
        if (onCommandProcessed) {
          onCommandProcessed(command);
        }
      } else {
        // Low confidence - ask for clarification
        await voiceService.speak('I\'m not sure I understood. Could you please repeat that?');
      }
    } catch (error) {
      logger.error('Error processing command:', error);
      if (onError) {
        onError(error as Error);
      }
    } finally {
      isProcessing.current = false;
      // Process next command in queue
      if (commandQueue.current.length > 0) {
        processCommandQueue();
      }
    }
  };
  
  const parseCommand = async (text: string): Promise<Command> => {
    const lowerText = text.toLowerCase();
    
    // Navigation commands
    if (lowerText.includes('navigate to') || lowerText.includes('take me to') || lowerText.includes('directions to')) {
      const destination = extractDestination(text);
      return {
        type: 'navigation',
        action: 'start',
        parameters: { destination },
        confidence: destination ? 0.9 : 0.5,
      };
    }
    
    if (lowerText.includes('stop navigation') || lowerText.includes('cancel navigation')) {
      return {
        type: 'navigation',
        action: 'stop',
        parameters: {},
        confidence: 0.95,
      };
    }
    
    if (lowerText.includes('how long') || lowerText.includes('how far') || lowerText.includes('when will')) {
      return {
        type: 'navigation',
        action: 'info',
        parameters: {},
        confidence: 0.9,
      };
    }
    
    // Booking commands
    if (lowerText.includes('book') || lowerText.includes('reserve') || lowerText.includes('reservation')) {
      const bookingType = extractBookingType(lowerText);
      const venue = extractVenue(text);
      
      return {
        type: 'booking',
        action: 'create',
        parameters: { bookingType, venue },
        confidence: venue ? 0.85 : 0.6,
      };
    }
    
    // Story commands
    if (lowerText.includes('tell me about') || lowerText.includes('what is') || lowerText.includes('story about')) {
      return {
        type: 'story',
        action: 'play',
        parameters: { topic: extractTopic(text) },
        confidence: 0.8,
      };
    }
    
    if (lowerText.includes('pause') || lowerText.includes('stop story') || lowerText.includes('quiet')) {
      return {
        type: 'story',
        action: 'pause',
        parameters: {},
        confidence: 0.95,
      };
    }
    
    if (lowerText.includes('resume') || lowerText.includes('continue') || lowerText.includes('keep going')) {
      return {
        type: 'story',
        action: 'resume',
        parameters: {},
        confidence: 0.95,
      };
    }
    
    // Settings commands
    if (lowerText.includes('volume up') || lowerText.includes('louder')) {
      return {
        type: 'settings',
        action: 'volume_up',
        parameters: {},
        confidence: 0.95,
      };
    }
    
    if (lowerText.includes('volume down') || lowerText.includes('quieter')) {
      return {
        type: 'settings',
        action: 'volume_down',
        parameters: {},
        confidence: 0.95,
      };
    }
    
    if (lowerText.includes('mute') || lowerText.includes('silence')) {
      return {
        type: 'settings',
        action: 'mute',
        parameters: {},
        confidence: 0.95,
      };
    }
    
    // Control commands
    if (lowerText.includes('help') || lowerText.includes('what can you do')) {
      return {
        type: 'control',
        action: 'help',
        parameters: {},
        confidence: 0.95,
      };
    }
    
    if (lowerText.includes('cancel') || lowerText.includes('never mind')) {
      return {
        type: 'control',
        action: 'cancel',
        parameters: {},
        confidence: 0.9,
      };
    }
    
    // Default to query if no specific command matched
    return {
      type: 'query',
      action: 'general',
      parameters: { query: text },
      confidence: 0.7,
    };
  };
  
  const executeCommand = async (command: Command) => {
    switch (command.type) {
      case 'navigation':
        await handleNavigationCommand(command);
        break;
      case 'booking':
        await handleBookingCommand(command);
        break;
      case 'story':
        await handleStoryCommand(command);
        break;
      case 'settings':
        await handleSettingsCommand(command);
        break;
      case 'control':
        await handleControlCommand(command);
        break;
      case 'query':
        await handleQueryCommand(command);
        break;
    }
  };
  
  const handleNavigationCommand = async (command: Command) => {
    switch (command.action) {
      case 'start':
        if (command.parameters.destination) {
          await navigationService.startNavigation(command.parameters.destination);
          await voiceService.speak(`Starting navigation to ${command.parameters.destination}`);
        }
        break;
      case 'stop':
        await navigationService.stopNavigation();
        await voiceService.speak('Navigation stopped');
        break;
      case 'info':
        const info = await navigationService.getCurrentRouteInfo();
        await voiceService.speak(`You have ${info.duration} remaining, ${info.distance} to go`);
        break;
    }
  };
  
  const handleBookingCommand = async (command: Command) => {
    if (command.action === 'create' && command.parameters.venue) {
      await voiceService.speak(`I'll help you book ${command.parameters.venue}. Let me check availability.`);
      // Trigger booking flow
    }
  };
  
  const handleStoryCommand = async (command: Command) => {
    switch (command.action) {
      case 'play':
        if (command.parameters.topic) {
          const story = await api.get(`/api/stories/topic/${command.parameters.topic}`);
          await voiceService.playStory(story.data.id);
        }
        break;
      case 'pause':
        await voiceService.pauseStory();
        break;
      case 'resume':
        await voiceService.resumeStory();
        break;
    }
  };
  
  const handleSettingsCommand = async (command: Command) => {
    switch (command.action) {
      case 'volume_up':
        await voiceService.increaseVolume();
        break;
      case 'volume_down':
        await voiceService.decreaseVolume();
        break;
      case 'mute':
        await voiceService.toggleMute();
        break;
    }
  };
  
  const handleControlCommand = async (command: Command) => {
    switch (command.action) {
      case 'help':
        await voiceService.speak(
          'I can help you navigate, book restaurants and attractions, tell stories about places, ' +
          'and control playback. Just tell me what you need!'
        );
        break;
      case 'cancel':
        await voiceService.speak('Okay, cancelled');
        break;
    }
  };
  
  const handleQueryCommand = async (command: Command) => {
    // Send general queries to AI for processing
    const response = await api.post('/api/ai/query', { query: command.parameters.query });
    await voiceService.speak(response.data.answer);
  };
  
  // Helper functions for extracting information from commands
  const extractDestination = (text: string): string => {
    const patterns = [
      /navigate to (.+)/i,
      /take me to (.+)/i,
      /directions to (.+)/i,
      /go to (.+)/i,
    ];
    
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match && match[1]) {
        return match[1].trim();
      }
    }
    
    return '';
  };
  
  const extractBookingType = (text: string): string => {
    if (text.includes('restaurant') || text.includes('dinner') || text.includes('lunch')) {
      return 'restaurant';
    }
    if (text.includes('hotel') || text.includes('room')) {
      return 'hotel';
    }
    if (text.includes('attraction') || text.includes('ticket')) {
      return 'attraction';
    }
    return 'restaurant'; // default
  };
  
  const extractVenue = (text: string): string => {
    const patterns = [
      /book (?:a table at |a reservation at )?(.+)/i,
      /reserve (?:a table at )?(.+)/i,
    ];
    
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match && match[1]) {
        // Clean up common words
        return match[1]
          .replace(/\b(restaurant|hotel|attraction|nearby|close|around here)\b/gi, '')
          .trim();
      }
    }
    
    return '';
  };
  
  const extractTopic = (text: string): string => {
    const patterns = [
      /tell me about (.+)/i,
      /what is (.+)/i,
      /story about (.+)/i,
    ];
    
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match && match[1]) {
        return match[1].trim();
      }
    }
    
    return 'this area';
  };
  
  // Component doesn't render anything - it's a pure logic component
  return null;
};

export const useVoiceCommandProcessor = (options?: Partial<VoiceCommandProcessorProps>) => {
  const [lastCommand, setLastCommand] = React.useState<Command | null>(null);
  const [error, setError] = React.useState<Error | null>(null);
  
  const handleCommandProcessed = (command: Command) => {
    setLastCommand(command);
    if (options?.onCommandProcessed) {
      options.onCommandProcessed(command);
    }
  };
  
  const handleError = (err: Error) => {
    setError(err);
    if (options?.onError) {
      options.onError(err);
    }
  };
  
  return {
    lastCommand,
    error,
    VoiceProcessor: () => (
      <VoiceCommandProcessor
        {...options}
        onCommandProcessed={handleCommandProcessed}
        onError={handleError}
      />
    ),
  };
};