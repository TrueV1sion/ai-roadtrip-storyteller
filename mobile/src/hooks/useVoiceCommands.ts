import { useState, useEffect, useCallback } from 'react';
import voiceCommandService, { 
  VoiceCommand, 
  RecognizedCommand 
} from '../services/voiceCommandService';

// Define the return type for the hook
export interface VoiceCommandResult {
  isListening: boolean;
  commands: VoiceCommand[];
  startListening: () => void;
  stopListening: () => void;
  processCommand: (text: string) => boolean;
  addCommand: (command: VoiceCommand) => void;
}

/**
 * Hook for using voice commands in React components
 */
export interface UseVoiceCommandsOptions {
  continuous?: boolean;
  autoStart?: boolean;
}

export const useVoiceCommands = (
  // Allow the component to process commands
  onCommand?: (command: RecognizedCommand) => void,
  // Custom commands to add
  customCommands?: VoiceCommand[],
  // Options
  options?: UseVoiceCommandsOptions
): VoiceCommandResult => {
  const { continuous = false, autoStart = false } = options || {};
  // Track listening state
  const [isListening, setIsListening] = useState(false);
  // Track available commands
  const [commands, setCommands] = useState<VoiceCommand[]>([]);

  // Initialize on mount
  useEffect(() => {
    const initVoiceCommands = async () => {
      await voiceCommandService.initialize();
      
      // Add custom commands if provided
      if (customCommands) {
        customCommands.forEach(command => {
          voiceCommandService.addCommand(command);
        });
      }
      
      // Update commands list
      setCommands(voiceCommandService.getAvailableCommands());
      
      // Set up command callback
      if (onCommand) {
        voiceCommandService.addCommandCallback(onCommand);
      }
      
      // Configure continuous mode
      if (continuous) {
        voiceCommandService.setContinuousMode(true);
      }
      
      // Auto start if requested
      if (autoStart) {
        voiceCommandService.startListening();
        setIsListening(voiceCommandService.isActive());
      }
    };
    
    initVoiceCommands();
    
    // Cleanup on unmount
    return () => {
      if (onCommand) {
        voiceCommandService.removeCommandCallback(onCommand);
      }
      
      if (voiceCommandService.isActive()) {
        voiceCommandService.stopListening();
      }
    };
  }, [continuous, autoStart]);

  // Start listening
  const startListening = useCallback(() => {
    voiceCommandService.startListening();
    setIsListening(voiceCommandService.isActive());
  }, []);

  // Stop listening
  const stopListening = useCallback(() => {
    voiceCommandService.stopListening();
    setIsListening(false);
  }, []);

  // Process a command (for testing)
  const processCommand = useCallback((text: string) => {
    return voiceCommandService.processCommand(text);
  }, []);

  // Add a command
  const addCommand = useCallback((command: VoiceCommand) => {
    voiceCommandService.addCommand(command);
    setCommands(voiceCommandService.getAvailableCommands());
  }, []);

  return {
    isListening,
    commands,
    startListening,
    stopListening,
    processCommand,
    addCommand
  };
};

export default useVoiceCommands;
