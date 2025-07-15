/**
 * Comprehensive test suite for UnifiedVoiceOrchestrator
 * Ensures world-class reliability and performance on mobile
 */

import { unifiedVoiceOrchestrator } from '../unifiedVoiceOrchestrator';
import apiClient from '../../apiClient';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio } from 'expo-av';
import * as Speech from 'expo-speech';
import * as Location from 'expo-location';
import * as Permissions from 'expo-permissions';

// Mock all dependencies
jest.mock('../../apiClient');
jest.mock('@react-native-async-storage/async-storage');
jest.mock('expo-av');
jest.mock('expo-speech');
jest.mock('expo-location');
jest.mock('expo-permissions');

describe('UnifiedVoiceOrchestrator', () => {
  const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;
  const mockAudio = Audio as jest.Mocked<typeof Audio>;
  const mockLocation = Location as jest.Mocked<typeof Location>;
  
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    
    // Setup default mocks
    mockAudio.requestPermissionsAsync = jest.fn().mockResolvedValue({ status: 'granted' });
    mockAudio.setAudioModeAsync = jest.fn().mockResolvedValue(undefined);
    mockLocation.requestForegroundPermissionsAsync = jest.fn().mockResolvedValue({ status: 'granted' });
    mockLocation.getCurrentPositionAsync = jest.fn().mockResolvedValue({
      coords: { latitude: 37.7749, longitude: -122.4194, heading: 45, speed: 65 }
    });
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  describe('Performance Tests', () => {
    it('should process voice input within 2 seconds', async () => {
      const startTime = Date.now();
      
      // Mock successful API response
      mockApiClient.post.mockResolvedValueOnce({
        data: {
          voice_audio: 'base64_audio',
          transcript: 'Found a great restaurant nearby',
          state: 'gathering_info'
        }
      });

      // Trigger voice interaction
      const promise = unifiedVoiceOrchestrator.startVoiceInteraction();
      
      // Simulate recording completion
      const mockRecording = {
        stopAndUnloadAsync: jest.fn().mockResolvedValue(undefined),
        getURI: jest.fn().mockReturnValue('file://mock-audio.wav')
      };
      
      // @ts-ignore - accessing private property for testing
      unifiedVoiceOrchestrator.recording = mockRecording;
      // @ts-ignore
      unifiedVoiceOrchestrator.isRecording = true;
      
      await unifiedVoiceOrchestrator.startVoiceInteraction(); // Stop recording
      
      const elapsedTime = Date.now() - startTime;
      expect(elapsedTime).toBeLessThan(2000);
    });

    it('should handle concurrent voice requests gracefully', async () => {
      const promises = [];
      
      // Start 5 concurrent voice interactions
      for (let i = 0; i < 5; i++) {
        promises.push(unifiedVoiceOrchestrator.startVoiceInteraction());
      }
      
      // All should complete without errors
      await expect(Promise.all(promises)).resolves.not.toThrow();
      
      // Should only have one active recording
      expect(mockAudio.Recording).toHaveBeenCalledTimes(1);
    });
  });

  describe('Reliability Tests', () => {
    it('should fall back to local TTS on network failure', async () => {
      // Mock network failure
      mockApiClient.post.mockRejectedValueOnce(new Error('Network error'));
      
      const speakSpy = jest.spyOn(Speech, 'speak');
      
      // Setup recording mock
      const mockRecording = {
        stopAndUnloadAsync: jest.fn().mockResolvedValue(undefined),
        getURI: jest.fn().mockReturnValue('file://mock-audio.wav'),
        prepareToRecordAsync: jest.fn().mockResolvedValue(undefined),
        startAsync: jest.fn().mockResolvedValue(undefined)
      };
      
      // @ts-ignore
      unifiedVoiceOrchestrator.recording = mockRecording;
      // @ts-ignore
      unifiedVoiceOrchestrator.isRecording = true;
      
      // Process voice input - should use fallback
      await unifiedVoiceOrchestrator.startVoiceInteraction();
      
      expect(speakSpy).toHaveBeenCalledWith(
        expect.stringContaining("having trouble connecting"),
        expect.any(Object)
      );
    });

    it('should auto-stop recording after 10 seconds', async () => {
      const mockRecording = {
        prepareToRecordAsync: jest.fn().mockResolvedValue(undefined),
        startAsync: jest.fn().mockResolvedValue(undefined),
        stopAndUnloadAsync: jest.fn().mockResolvedValue(undefined),
        getURI: jest.fn().mockReturnValue(null)
      };
      
      mockAudio.Recording = jest.fn().mockReturnValue(mockRecording);
      
      // Start recording
      await unifiedVoiceOrchestrator.startVoiceInteraction();
      
      // Fast-forward 10 seconds
      jest.advanceTimersByTime(10000);
      
      // Recording should be stopped
      expect(mockRecording.stopAndUnloadAsync).toHaveBeenCalled();
    });

    it('should handle permission denial gracefully', async () => {
      mockAudio.requestPermissionsAsync.mockResolvedValueOnce({ status: 'denied' });
      
      const errorHandler = jest.fn();
      unifiedVoiceOrchestrator.on('error', errorHandler);
      
      await unifiedVoiceOrchestrator.startVoiceInteraction();
      
      expect(errorHandler).toHaveBeenCalledWith('Microphone permission not granted');
    });
  });

  describe('Context Management', () => {
    it('should maintain conversation context across interactions', async () => {
      const testContext = {
        personality: 'enthusiastic_buddy',
        audio_priority: 'balanced',
        party_size: 4
      };
      
      await unifiedVoiceOrchestrator.updatePreferences(testContext);
      
      // Verify context is saved
      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        '@voice_preferences',
        JSON.stringify(testContext)
      );
      
      // Verify context is used in API calls
      mockApiClient.post.mockResolvedValueOnce({
        data: { voice_audio: 'test', transcript: 'test', state: 'idle' }
      });
      
      // @ts-ignore - accessing private method
      await unifiedVoiceOrchestrator.processVoiceInput('audio_base64');
      
      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/voice/process',
        expect.objectContaining({
          context_data: expect.objectContaining(testContext)
        })
      );
    });

    it('should track location updates', async () => {
      const locationUpdateHandler = jest.fn();
      unifiedVoiceOrchestrator.on('locationUpdated', locationUpdateHandler);
      
      // Simulate location update
      const mockWatchCallback = mockLocation.watchPositionAsync.mock.calls[0][1];
      mockWatchCallback({
        coords: {
          latitude: 37.7850,
          longitude: -122.4294,
          heading: 90,
          speed: 55
        }
      });
      
      expect(locationUpdateHandler).toHaveBeenCalledWith({
        lat: 37.7850,
        lng: -122.4294,
        heading: 90,
        speed: 55
      });
    });
  });

  describe('Proactive Suggestions', () => {
    it('should trigger meal time suggestions', async () => {
      // Mock current time as noon
      jest.spyOn(Date.prototype, 'getHours').mockReturnValue(12);
      
      mockApiClient.post.mockResolvedValueOnce({
        data: {
          voice_audio: 'lunch_suggestion_audio',
          transcript: 'Time for lunch! There\'s a great place nearby.',
          trigger: 'meal_time',
          can_dismiss: true
        }
      });
      
      const suggestionHandler = jest.fn();
      unifiedVoiceOrchestrator.on('proactiveSuggestion', suggestionHandler);
      
      // Fast-forward to trigger suggestion check
      jest.advanceTimersByTime(30000);
      
      // Wait for async operations
      await Promise.resolve();
      
      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/voice/proactive',
        expect.objectContaining({
          trigger: 'meal_time'
        })
      );
    });

    it('should respect rate limiting for suggestions', async () => {
      // @ts-ignore - accessing private property
      unifiedVoiceOrchestrator.lastProactiveSuggestion = Date.now() - 100000; // 100 seconds ago
      
      // First check should trigger
      jest.advanceTimersByTime(30000);
      await Promise.resolve();
      expect(mockApiClient.post).toHaveBeenCalledTimes(1);
      
      // Second check within 5 minutes should not trigger
      jest.advanceTimersByTime(30000);
      await Promise.resolve();
      expect(mockApiClient.post).toHaveBeenCalledTimes(1); // Still 1
    });
  });

  describe('Audio Processing', () => {
    it('should handle audio playback correctly', async () => {
      const mockSound = {
        setOnPlaybackStatusUpdate: jest.fn(),
        unloadAsync: jest.fn().mockResolvedValue(undefined)
      };
      
      mockAudio.Sound.createAsync = jest.fn().mockResolvedValue({ sound: mockSound });
      
      const playbackStartHandler = jest.fn();
      const playbackFinishHandler = jest.fn();
      unifiedVoiceOrchestrator.on('playbackStarted', playbackStartHandler);
      unifiedVoiceOrchestrator.on('playbackFinished', playbackFinishHandler);
      
      // @ts-ignore - accessing private method
      await unifiedVoiceOrchestrator.playVoiceResponse('base64_audio');
      
      expect(playbackStartHandler).toHaveBeenCalled();
      expect(mockAudio.Sound.createAsync).toHaveBeenCalledWith(
        { uri: 'data:audio/mp3;base64,base64_audio' },
        { shouldPlay: true }
      );
      
      // Simulate playback completion
      const statusCallback = mockSound.setOnPlaybackStatusUpdate.mock.calls[0][0];
      statusCallback({ isLoaded: true, didJustFinish: true });
      
      expect(playbackFinishHandler).toHaveBeenCalled();
      expect(mockSound.unloadAsync).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('should emit error events for all failure scenarios', async () => {
      const errorHandler = jest.fn();
      unifiedVoiceOrchestrator.on('error', errorHandler);
      
      // Test various error scenarios
      const errorScenarios = [
        { 
          setup: () => mockAudio.requestPermissionsAsync.mockResolvedValueOnce({ status: 'denied' }),
          expectedError: 'Microphone permission not granted'
        },
        {
          setup: () => {
            // @ts-ignore
            unifiedVoiceOrchestrator.recording = {
              stopAndUnloadAsync: jest.fn().mockResolvedValue(undefined),
              getURI: jest.fn().mockReturnValue(null)
            };
            // @ts-ignore
            unifiedVoiceOrchestrator.isRecording = true;
          },
          expectedError: 'No recording found'
        }
      ];
      
      for (const scenario of errorScenarios) {
        errorHandler.mockClear();
        scenario.setup();
        await unifiedVoiceOrchestrator.startVoiceInteraction();
        expect(errorHandler).toHaveBeenCalledWith(scenario.expectedError);
      }
    });
  });

  describe('Memory Management', () => {
    it('should clean up resources on cleanup()', async () => {
      // Setup some state
      const mockRecording = {
        stopAndUnloadAsync: jest.fn().mockResolvedValue(undefined)
      };
      const mockPlayback = {
        unloadAsync: jest.fn().mockResolvedValue(undefined)
      };
      const mockLocationSub = {
        remove: jest.fn()
      };
      
      // @ts-ignore
      unifiedVoiceOrchestrator.recording = mockRecording;
      // @ts-ignore
      unifiedVoiceOrchestrator.playback = mockPlayback;
      // @ts-ignore
      unifiedVoiceOrchestrator.locationSubscription = mockLocationSub;
      
      await unifiedVoiceOrchestrator.cleanup();
      
      expect(mockRecording.stopAndUnloadAsync).toHaveBeenCalled();
      expect(mockPlayback.unloadAsync).toHaveBeenCalled();
      expect(mockLocationSub.remove).toHaveBeenCalled();
    });
  });

  describe('Integration with Booking System', () => {
    it('should seamlessly transition voice booking to visual', async () => {
      const mockResponse = {
        data: {
          voice_audio: 'booking_audio',
          transcript: 'I found 3 restaurants nearby',
          visual_data: {
            restaurants: [
              { id: '1', name: 'Restaurant 1', rating: 4.5 },
              { id: '2', name: 'Restaurant 2', rating: 4.2 },
              { id: '3', name: 'Restaurant 3', rating: 4.8 }
            ]
          },
          state: 'awaiting_confirmation'
        }
      };
      
      mockApiClient.post.mockResolvedValueOnce(mockResponse);
      
      const visualDataHandler = jest.fn();
      unifiedVoiceOrchestrator.on('visualDataReceived', visualDataHandler);
      
      // @ts-ignore
      await unifiedVoiceOrchestrator.processVoiceInput('audio_base64');
      
      expect(visualDataHandler).toHaveBeenCalledWith(mockResponse.data.visual_data);
    });
  });
});

describe('UnifiedVoiceOrchestrator Performance Benchmarks', () => {
  it('should maintain sub-100ms event emission', () => {
    const iterations = 1000;
    const handler = jest.fn();
    
    unifiedVoiceOrchestrator.on('test', handler);
    
    const start = performance.now();
    for (let i = 0; i < iterations; i++) {
      unifiedVoiceOrchestrator.emit('test', { data: i });
    }
    const duration = performance.now() - start;
    
    expect(duration / iterations).toBeLessThan(0.1); // < 0.1ms per emission
    expect(handler).toHaveBeenCalledTimes(iterations);
  });
});