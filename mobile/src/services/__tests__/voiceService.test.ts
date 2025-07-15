import * as Speech from 'expo-speech';
import { Platform } from 'react-native';
import { voiceService } from '../voiceService';

// Mock expo-speech
jest.mock('expo-speech', () => ({
  speak: jest.fn(),
  stop: jest.fn(),
  pause: jest.fn(),
  resume: jest.fn(),
  isSpeakingAsync: jest.fn(),
  getAvailableVoicesAsync: jest.fn(),
}));

describe('VoiceService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Platform.OS = 'ios';
  });

  describe('initialize', () => {
    test('sets default voice when available', async () => {
      const mockVoices = [
        { identifier: 'com.apple.ttsbundle.Samantha-compact' },
        { identifier: 'en-us-x-sfg' },
      ];

      (Speech.getAvailableVoicesAsync as jest.Mock).mockResolvedValue(mockVoices);

      await voiceService.initialize();

      expect(Speech.getAvailableVoicesAsync).toHaveBeenCalled();
    });

    test('handles errors gracefully', async () => {
      (Speech.getAvailableVoicesAsync as jest.Mock).mockRejectedValue(new Error('Voice error'));

      await expect(voiceService.initialize()).resolves.not.toThrow();
    });
  });

  describe('speak', () => {
    test('speaks text with default options', async () => {
      await voiceService.speak('Hello world');

      expect(Speech.speak).toHaveBeenCalledWith('Hello world', expect.objectContaining({
        language: 'en-US',
        pitch: 1.0,
        rate: 0.5,
      }));
    });

    test('handles custom options', async () => {
      const options = {
        language: 'es-ES',
        pitch: 1.5,
        rate: 0.8,
      };

      await voiceService.speak('Hola mundo', options);

      expect(Speech.speak).toHaveBeenCalledWith('Hola mundo', expect.objectContaining(options));
    });

    test('queues speech when already speaking', async () => {
      voiceService['isSpeaking'] = true;

      await voiceService.speak('First message');
      await voiceService.speak('Second message');

      expect(Speech.speak).toHaveBeenCalledTimes(1);
      expect(voiceService['queue']).toHaveLength(1);
      expect(voiceService['queue'][0].text).toBe('Second message');
    });

    test('processes queue after speech completion', async () => {
      voiceService['isSpeaking'] = true;
      await voiceService.speak('First message');
      await voiceService.speak('Second message');

      // Simulate speech completion
      const onDone = (Speech.speak as jest.Mock).mock.calls[0][1].onDone;
      onDone();

      expect(Speech.speak).toHaveBeenCalledTimes(2);
    });
  });

  describe('stop', () => {
    test('stops speech and clears queue', async () => {
      voiceService['queue'] = [
        { text: 'Queued message 1' },
        { text: 'Queued message 2' },
      ];

      await voiceService.stop();

      expect(Speech.stop).toHaveBeenCalled();
      expect(voiceService['queue']).toHaveLength(0);
      expect(voiceService['isSpeaking']).toBe(false);
    });

    test('handles errors gracefully', async () => {
      (Speech.stop as jest.Mock).mockRejectedValue(new Error('Stop error'));

      await expect(voiceService.stop()).resolves.not.toThrow();
    });
  });

  describe('pause and resume', () => {
    test('pauses speech', async () => {
      await voiceService.pause();
      expect(Speech.pause).toHaveBeenCalled();
    });

    test('resumes speech', async () => {
      await voiceService.resume();
      expect(Speech.resume).toHaveBeenCalled();
    });

    test('handles pause errors gracefully', async () => {
      (Speech.pause as jest.Mock).mockRejectedValue(new Error('Pause error'));
      await expect(voiceService.pause()).resolves.not.toThrow();
    });

    test('handles resume errors gracefully', async () => {
      (Speech.resume as jest.Mock).mockRejectedValue(new Error('Resume error'));
      await expect(voiceService.resume()).resolves.not.toThrow();
    });
  });

  describe('isSpeakingNow', () => {
    test('returns speaking status', async () => {
      (Speech.isSpeakingAsync as jest.Mock).mockResolvedValue(true);
      expect(await voiceService.isSpeakingNow()).toBe(true);

      (Speech.isSpeakingAsync as jest.Mock).mockResolvedValue(false);
      expect(await voiceService.isSpeakingNow()).toBe(false);
    });

    test('handles errors gracefully', async () => {
      (Speech.isSpeakingAsync as jest.Mock).mockRejectedValue(new Error('Status error'));
      expect(await voiceService.isSpeakingNow()).toBe(false);
    });
  });

  describe('tellStory', () => {
    test('speaks story without pauses', async () => {
      const story = 'Once upon a time in a land far away.';
      await voiceService.tellStory(story);

      expect(Speech.speak).toHaveBeenCalledWith(story, expect.any(Object));
    });

    test('speaks story with pauses between sentences', async () => {
      jest.useFakeTimers();
      const story = 'First sentence. Second sentence! Third sentence?';
      
      const promise = voiceService.tellStory(story, { addPauses: true });
      
      // Fast-forward through all timers
      jest.runAllTimers();
      await promise;

      expect(Speech.speak).toHaveBeenCalledTimes(3);
      expect(Speech.speak).toHaveBeenCalledWith('First sentence', expect.any(Object));
      expect(Speech.speak).toHaveBeenCalledWith('Second sentence', expect.any(Object));
      expect(Speech.speak).toHaveBeenCalledWith('Third sentence', expect.any(Object));
    });

    test('applies custom options to story', async () => {
      const story = 'Test story';
      const options = {
        pitch: 1.2,
        rate: 0.7,
        addPauses: false,
      };

      await voiceService.tellStory(story, options);

      expect(Speech.speak).toHaveBeenCalledWith(story, expect.objectContaining({
        pitch: 1.2,
        rate: 0.7,
      }));
    });
  });
}); 