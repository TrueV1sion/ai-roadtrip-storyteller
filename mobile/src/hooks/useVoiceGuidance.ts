import { useCallback, useEffect, useRef } from 'react';
import * as Speech from 'expo-speech';
import { useNavigationPreferences } from './useNavigationPreferences';

import { logger } from '@/services/logger';
export const useVoiceGuidance = () => {
  const { preferences } = useNavigationPreferences();
  const isSpeakingRef = useRef(false);
  const queueRef = useRef<string[]>([]);

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      Speech.stop();
    };
  }, []);

  const speak = useCallback(async (text: string) => {
    if (!preferences.voiceSettings.enabled) return;

    // Add to queue if already speaking
    if (isSpeakingRef.current) {
      queueRef.current.push(text);
      return;
    }

    try {
      isSpeakingRef.current = true;
      await Speech.speak(text, {
        language: preferences.voiceSettings.language,
        pitch: 1.0,
        rate: 0.9,
        volume: preferences.voiceSettings.volume,
        onDone: () => {
          isSpeakingRef.current = false;
          // Process next in queue
          if (queueRef.current.length > 0) {
            const nextText = queueRef.current.shift();
            if (nextText) speak(nextText);
          }
        },
      });
    } catch (error) {
      logger.error('Voice guidance error:', error);
      isSpeakingRef.current = false;
    }
  }, [preferences.voiceSettings]);

  const stop = useCallback(() => {
    Speech.stop();
    queueRef.current = [];
    isSpeakingRef.current = false;
  }, []);

  return {
    speak,
    stop,
    isEnabled: preferences.voiceSettings.enabled,
  };
}; 