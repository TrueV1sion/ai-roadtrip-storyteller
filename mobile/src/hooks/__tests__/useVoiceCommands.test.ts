import { renderHook, act } from '@testing-library/react-hooks';
import { useVoiceCommands } from '../useVoiceCommands';
import * as Speech from 'expo-speech';
import Voice from '@react-native-voice/voice';

jest.mock('expo-speech');
jest.mock('@react-native-voice/voice', () => ({
  onSpeechStart: jest.fn(),
  onSpeechEnd: jest.fn(),
  onSpeechResults: jest.fn(),
  onSpeechError: jest.fn(),
  start: jest.fn(),
  stop: jest.fn(),
  cancel: jest.fn(),
  destroy: jest.fn(),
  isAvailable: jest.fn().mockResolvedValue(true),
  isRecognizing: jest.fn().mockResolvedValue(false),
}));

describe('useVoiceCommands', () => {
  let mockCallbacks: any = {};

  beforeEach(() => {
    jest.clearAllMocks();
    mockCallbacks = {};

    // Setup Voice event listeners
    (Voice.onSpeechStart as jest.Mock).mockImplementation((callback) => {
      mockCallbacks.onSpeechStart = callback;
    });
    (Voice.onSpeechEnd as jest.Mock).mockImplementation((callback) => {
      mockCallbacks.onSpeechEnd = callback;
    });
    (Voice.onSpeechResults as jest.Mock).mockImplementation((callback) => {
      mockCallbacks.onSpeechResults = callback;
    });
    (Voice.onSpeechError as jest.Mock).mockImplementation((callback) => {
      mockCallbacks.onSpeechError = callback;
    });
  });

  it('initializes with default state', () => {
    const { result } = renderHook(() => useVoiceCommands());

    expect(result.current.isListening).toBe(false);
    expect(result.current.transcript).toBe('');
    expect(result.current.error).toBeNull();
    expect(result.current.command).toBeNull();
  });

  it('starts listening', async () => {
    const { result } = renderHook(() => useVoiceCommands());

    await act(async () => {
      await result.current.startListening();
    });

    expect(Voice.start).toHaveBeenCalledWith('en-US');
    expect(result.current.isListening).toBe(true);
  });

  it('stops listening', async () => {
    const { result } = renderHook(() => useVoiceCommands());

    // Start listening first
    await act(async () => {
      await result.current.startListening();
    });

    await act(async () => {
      await result.current.stopListening();
    });

    expect(Voice.stop).toHaveBeenCalled();
    expect(result.current.isListening).toBe(false);
  });

  it('handles speech results', async () => {
    const onCommand = jest.fn();
    const { result } = renderHook(() => 
      useVoiceCommands({ onCommand })
    );

    await act(async () => {
      await result.current.startListening();
    });

    // Simulate speech results
    act(() => {
      mockCallbacks.onSpeechResults({
        value: ['navigate to Los Angeles'],
      });
    });

    expect(result.current.transcript).toBe('navigate to Los Angeles');
    expect(result.current.command).toEqual({
      type: 'navigation',
      action: 'navigate',
      params: {
        destination: 'Los Angeles',
      },
    });
    expect(onCommand).toHaveBeenCalledWith({
      type: 'navigation',
      action: 'navigate',
      params: {
        destination: 'Los Angeles',
      },
    });
  });

  it('handles booking commands', async () => {
    const onCommand = jest.fn();
    const { result } = renderHook(() => 
      useVoiceCommands({ onCommand })
    );

    await act(async () => {
      await result.current.startListening();
    });

    act(() => {
      mockCallbacks.onSpeechResults({
        value: ['book a table for 4 people tonight'],
      });
    });

    expect(result.current.command).toEqual({
      type: 'booking',
      action: 'restaurant',
      params: {
        partySize: 4,
        time: 'tonight',
      },
    });
  });

  it('handles music commands', async () => {
    const onCommand = jest.fn();
    const { result } = renderHook(() => 
      useVoiceCommands({ onCommand })
    );

    await act(async () => {
      await result.current.startListening();
    });

    act(() => {
      mockCallbacks.onSpeechResults({
        value: ['play jazz music'],
      });
    });

    expect(result.current.command).toEqual({
      type: 'music',
      action: 'play',
      params: {
        genre: 'jazz',
      },
    });
  });

  it('handles information queries', async () => {
    const onCommand = jest.fn();
    const { result } = renderHook(() => 
      useVoiceCommands({ onCommand })
    );

    await act(async () => {
      await result.current.startListening();
    });

    act(() => {
      mockCallbacks.onSpeechResults({
        value: ['what is the weather'],
      });
    });

    expect(result.current.command).toEqual({
      type: 'query',
      action: 'weather',
      params: {},
    });
  });

  it('handles speech errors', async () => {
    const onError = jest.fn();
    const { result } = renderHook(() => 
      useVoiceCommands({ onError })
    );

    await act(async () => {
      await result.current.startListening();
    });

    const error = { code: 'no-speech', message: 'No speech detected' };
    act(() => {
      mockCallbacks.onSpeechError(error);
    });

    expect(result.current.error).toBe('No speech detected');
    expect(result.current.isListening).toBe(false);
    expect(onError).toHaveBeenCalledWith(error);
  });

  it('provides speech feedback', async () => {
    const { result } = renderHook(() => useVoiceCommands());

    await act(async () => {
      await result.current.speak('Hello, how can I help you?');
    });

    expect(Speech.speak).toHaveBeenCalledWith('Hello, how can I help you?', {
      language: 'en-US',
      pitch: 1.0,
      rate: 1.0,
    });
  });

  it('cancels speech', async () => {
    const { result } = renderHook(() => useVoiceCommands());

    await act(async () => {
      await result.current.cancelSpeech();
    });

    expect(Speech.stop).toHaveBeenCalled();
  });

  it('handles custom wake word', async () => {
    const onWakeWord = jest.fn();
    const { result } = renderHook(() => 
      useVoiceCommands({ 
        wakeWord: 'hey roadtrip',
        onWakeWord,
      })
    );

    await act(async () => {
      await result.current.startListening();
    });

    act(() => {
      mockCallbacks.onSpeechResults({
        value: ['hey roadtrip'],
      });
    });

    expect(onWakeWord).toHaveBeenCalled();
    expect(result.current.isListening).toBe(true);
  });

  it('filters background noise', async () => {
    const onCommand = jest.fn();
    const { result } = renderHook(() => 
      useVoiceCommands({ 
        onCommand,
        confidenceThreshold: 0.7,
      })
    );

    await act(async () => {
      await result.current.startListening();
    });

    // Low confidence result (should be filtered)
    act(() => {
      mockCallbacks.onSpeechResults({
        value: ['mumble mumble'],
        confidence: [0.3],
      });
    });

    expect(onCommand).not.toHaveBeenCalled();

    // High confidence result (should be processed)
    act(() => {
      mockCallbacks.onSpeechResults({
        value: ['navigate home'],
        confidence: [0.9],
      });
    });

    expect(onCommand).toHaveBeenCalled();
  });

  it('handles continuous listening mode', async () => {
    const { result } = renderHook(() => 
      useVoiceCommands({ continuous: true })
    );

    await act(async () => {
      await result.current.startListening();
    });

    // Simulate speech end
    act(() => {
      mockCallbacks.onSpeechEnd();
    });

    // Should restart listening in continuous mode
    expect(Voice.start).toHaveBeenCalledTimes(2);
  });

  it('cleans up on unmount', () => {
    const { unmount } = renderHook(() => useVoiceCommands());

    unmount();

    expect(Voice.destroy).toHaveBeenCalled();
  });
});