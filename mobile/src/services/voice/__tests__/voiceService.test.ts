import { VoiceService } from '../voiceService';
import VoicePersonalityManager from '../voicePersonalities';
import StorageManager from '@utils/storage';
import SessionManager from '../sessionManager';
import APIManager from '../../api/apiManager';
import { VoicePersonality, GuideTheme } from '../voicePersonalities';

// Mock dependencies
jest.mock('../voicePersonalities');
jest.mock('@utils/storage');
jest.mock('../sessionManager');
jest.mock('../../api/apiManager');
jest.mock('@react-native-voice/voice', () => ({
  start: jest.fn(),
  stop: jest.fn(),
  cancel: jest.fn(),
  destroy: jest.fn(),
  isAvailable: jest.fn(() => Promise.resolve(true)),
  isRecognizing: jest.fn(() => Promise.resolve(false)),
  removeAllListeners: jest.fn(),
  onSpeechStart: jest.fn(),
  onSpeechEnd: jest.fn(),
  onSpeechResults: jest.fn(),
  onSpeechError: jest.fn(),
}));

describe('VoiceService', () => {
  let voiceService: VoiceService;
  
  const mockPersonality: VoicePersonality = {
    id: 'test-personality',
    name: 'Test Personality',
    description: 'A test personality',
    voiceId: 'test-voice',
    provider: 'azure',
    ssmlVoice: 'en-US-TestNeural',
    pitch: 1.0,
    rate: 1.0,
    volume: 1.0,
    characterTraits: {
      humor: 0.5,
      knowledge: 0.8,
      enthusiasm: 0.7,
      formality: 0.3,
    },
    preferredTopics: ['history', 'nature'],
    backgroundMusic: {
      enabled: true,
      volume: 0.3,
      style: 'ambient',
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup default mocks
    (VoicePersonalityManager.initialize as jest.Mock).mockResolvedValue(undefined);
    (VoicePersonalityManager.getPersonalityById as jest.Mock).mockReturnValue(mockPersonality);
    (StorageManager.getItem as jest.Mock).mockResolvedValue(null);
    (SessionManager.startSession as jest.Mock).mockResolvedValue(undefined);
    
    voiceService = new VoiceService();
  });

  describe('Initialization', () => {
    it('should initialize voice personality manager', async () => {
      await new Promise(resolve => setTimeout(resolve, 100)); // Wait for async constructor
      
      expect(VoicePersonalityManager.initialize).toHaveBeenCalled();
    });

    it('should load saved personality from storage', async () => {
      (StorageManager.getItem as jest.Mock).mockResolvedValueOnce('test-personality');
      
      const service = new VoiceService();
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(StorageManager.getItem).toHaveBeenCalledWith('@selected_personality');
      expect(VoicePersonalityManager.getPersonalityById).toHaveBeenCalledWith('test-personality');
    });

    it('should start session with loaded personality', async () => {
      (StorageManager.getItem as jest.Mock).mockResolvedValueOnce('test-personality');
      
      const service = new VoiceService();
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(SessionManager.startSession).toHaveBeenCalledWith(mockPersonality);
    });

    it('should use default personality if none saved', async () => {
      (StorageManager.getItem as jest.Mock).mockResolvedValue(null);
      
      const service = new VoiceService();
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(VoicePersonalityManager.getPersonalityById).toHaveBeenCalledWith('adventurous-explorer');
    });
  });

  describe('Text-to-Speech', () => {
    it('should generate speech from text', async () => {
      const mockAudioUrl = 'https://example.com/audio.mp3';
      (APIManager.post as jest.Mock).mockResolvedValue({ 
        data: { audioUrl: mockAudioUrl } 
      });
      
      const result = await voiceService.textToSpeech('Hello world');
      
      expect(APIManager.post).toHaveBeenCalledWith(
        '/voice/tts',
        expect.objectContaining({
          text: 'Hello world',
          personality: expect.any(Object),
        })
      );
      expect(result).toBe(mockAudioUrl);
    });

    it('should handle TTS errors gracefully', async () => {
      (APIManager.post as jest.Mock).mockRejectedValue(new Error('TTS failed'));
      
      await expect(voiceService.textToSpeech('Hello')).rejects.toThrow('TTS failed');
    });

    it('should apply personality-specific voice settings', async () => {
      await voiceService.setPersonality('test-personality');
      
      (APIManager.post as jest.Mock).mockResolvedValue({ 
        data: { audioUrl: 'test.mp3' } 
      });
      
      await voiceService.textToSpeech('Test message');
      
      expect(APIManager.post).toHaveBeenCalledWith(
        '/voice/tts',
        expect.objectContaining({
          personality: expect.objectContaining({
            pitch: 1.0,
            rate: 1.0,
            volume: 1.0,
          }),
        })
      );
    });
  });

  describe('Speech Recognition', () => {
    it('should start voice recognition', async () => {
      const Voice = require('@react-native-voice/voice');
      
      await voiceService.startListening();
      
      expect(Voice.start).toHaveBeenCalledWith('en-US');
    });

    it('should stop voice recognition', async () => {
      const Voice = require('@react-native-voice/voice');
      
      await voiceService.stopListening();
      
      expect(Voice.stop).toHaveBeenCalled();
    });

    it('should handle speech recognition errors', async () => {
      const Voice = require('@react-native-voice/voice');
      Voice.start.mockRejectedValue(new Error('Microphone access denied'));
      
      await expect(voiceService.startListening()).rejects.toThrow('Microphone access denied');
    });

    it('should process speech results', async () => {
      const mockCallback = jest.fn();
      voiceService.onSpeechResults(mockCallback);
      
      // Simulate speech results
      const Voice = require('@react-native-voice/voice');
      const speechHandler = Voice.onSpeechResults.mock.calls[0][0];
      speechHandler({ value: ['hello world'] });
      
      expect(mockCallback).toHaveBeenCalledWith(['hello world']);
    });
  });

  describe('Personality Management', () => {
    it('should change voice personality', async () => {
      const newPersonality = { ...mockPersonality, id: 'new-personality' };
      (VoicePersonalityManager.getPersonalityById as jest.Mock).mockReturnValue(newPersonality);
      
      await voiceService.setPersonality('new-personality');
      
      expect(StorageManager.setItem).toHaveBeenCalledWith('@selected_personality', 'new-personality');
      expect(SessionManager.startSession).toHaveBeenCalledWith(newPersonality);
    });

    it('should get available personalities', () => {
      const mockPersonalities = [mockPersonality];
      (VoicePersonalityManager.getAllPersonalities as jest.Mock).mockReturnValue(mockPersonalities);
      
      const personalities = voiceService.getAvailablePersonalities();
      
      expect(personalities).toEqual(mockPersonalities);
    });

    it('should handle invalid personality ID', async () => {
      (VoicePersonalityManager.getPersonalityById as jest.Mock).mockReturnValue(null);
      
      await expect(voiceService.setPersonality('invalid-id')).rejects.toThrow('Personality not found');
    });
  });

  describe('Conversation State', () => {
    it('should save conversation state', async () => {
      const conversationState = {
        currentTopic: 'history',
        context: ['previous', 'messages'],
        timestamp: Date.now(),
      };
      
      await voiceService.saveConversationState(conversationState);
      
      expect(StorageManager.setItem).toHaveBeenCalledWith(
        '@conversation_state',
        conversationState
      );
    });

    it('should load conversation state', async () => {
      const savedState = {
        currentTopic: 'nature',
        context: ['saved', 'context'],
        timestamp: Date.now(),
      };
      
      (StorageManager.getItem as jest.Mock).mockResolvedValue(savedState);
      
      const state = await voiceService.getConversationState();
      
      expect(state).toEqual(savedState);
    });

    it('should clear conversation state', async () => {
      await voiceService.clearConversationState();
      
      expect(StorageManager.removeItem).toHaveBeenCalledWith('@conversation_state');
    });
  });

  describe('Audio Playback', () => {
    it('should play audio segment', async () => {
      const mockAudio = {
        play: jest.fn(),
        pause: jest.fn(),
        stop: jest.fn(),
      };
      
      (global as any).Audio = jest.fn(() => mockAudio);
      
      await voiceService.playAudio('https://example.com/audio.mp3');
      
      expect(mockAudio.play).toHaveBeenCalled();
    });

    it('should pause audio playback', async () => {
      const mockAudio = {
        play: jest.fn(),
        pause: jest.fn(),
        stop: jest.fn(),
      };
      
      (global as any).Audio = jest.fn(() => mockAudio);
      
      await voiceService.playAudio('https://example.com/audio.mp3');
      await voiceService.pauseAudio();
      
      expect(mockAudio.pause).toHaveBeenCalled();
    });

    it('should handle audio playback errors', async () => {
      const mockAudio = {
        play: jest.fn().mockRejectedValue(new Error('Audio load failed')),
      };
      
      (global as any).Audio = jest.fn(() => mockAudio);
      
      await expect(voiceService.playAudio('invalid-url')).rejects.toThrow('Audio load failed');
    });
  });

  describe('Voice Commands', () => {
    it('should process voice commands', async () => {
      const mockResponse = { 
        action: 'navigate',
        parameters: { destination: 'Times Square' }
      };
      
      (APIManager.post as jest.Mock).mockResolvedValue({ data: mockResponse });
      
      const result = await voiceService.processVoiceCommand('Take me to Times Square');
      
      expect(APIManager.post).toHaveBeenCalledWith(
        '/voice/process-command',
        { command: 'Take me to Times Square' }
      );
      expect(result).toEqual(mockResponse);
    });

    it('should handle command processing errors', async () => {
      (APIManager.post as jest.Mock).mockRejectedValue(new Error('Command processing failed'));
      
      await expect(voiceService.processVoiceCommand('Invalid command'))
        .rejects.toThrow('Command processing failed');
    });
  });

  describe('Safety Features', () => {
    it('should enable driving mode', async () => {
      await voiceService.enableDrivingMode();
      
      expect(voiceService.isDrivingMode()).toBe(true);
    });

    it('should disable non-essential features in driving mode', async () => {
      await voiceService.enableDrivingMode();
      
      // Verify that visual features are disabled
      expect(voiceService.isVisualFeedbackEnabled()).toBe(false);
    });

    it('should prioritize safety announcements', async () => {
      await voiceService.enableDrivingMode();
      
      const mockEmergencyAudio = 'emergency.mp3';
      (APIManager.post as jest.Mock).mockResolvedValue({ 
        data: { audioUrl: mockEmergencyAudio, priority: 'high' } 
      });
      
      await voiceService.textToSpeech('Road hazard ahead', { priority: 'high' });
      
      expect(APIManager.post).toHaveBeenCalledWith(
        '/voice/tts',
        expect.objectContaining({
          priority: 'high',
        })
      );
    });
  });

  describe('Offline Support', () => {
    it('should cache voice responses', async () => {
      const mockAudioUrl = 'cached-audio.mp3';
      (APIManager.post as jest.Mock).mockResolvedValue({ 
        data: { audioUrl: mockAudioUrl } 
      });
      
      // First call - should fetch from API
      await voiceService.textToSpeech('Cached message');
      
      // Second call - should use cache
      (APIManager.post as jest.Mock).mockClear();
      await voiceService.textToSpeech('Cached message');
      
      expect(APIManager.post).not.toHaveBeenCalled();
    });

    it('should handle offline mode gracefully', async () => {
      (APIManager.post as jest.Mock).mockRejectedValue(new Error('Network error'));
      
      // Should fall back to offline TTS or cached responses
      const result = await voiceService.textToSpeech('Offline message', { offline: true });
      
      expect(result).toBeDefined(); // Should provide some fallback
    });
  });

  describe('Memory Management', () => {
    it('should clean up resources on destroy', async () => {
      const Voice = require('@react-native-voice/voice');
      
      await voiceService.destroy();
      
      expect(Voice.destroy).toHaveBeenCalled();
      expect(Voice.removeAllListeners).toHaveBeenCalled();
      expect(SessionManager.endSession).toHaveBeenCalled();
    });

    it('should limit conversation history size', async () => {
      // Add many conversation items
      for (let i = 0; i < 100; i++) {
        await voiceService.addToConversationHistory(`Message ${i}`);
      }
      
      const history = await voiceService.getConversationHistory();
      
      // Should keep only recent items (e.g., last 50)
      expect(history.length).toBeLessThanOrEqual(50);
    });
  });
});