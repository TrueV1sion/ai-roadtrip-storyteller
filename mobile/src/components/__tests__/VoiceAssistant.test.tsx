"""Tests for voice assistant components."""

import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import Voice from '@react-native-voice/voice';

import VoiceAssistant from '../voice/VoiceAssistant';
import VoiceCommandProcessor from '../voice/VoiceCommandProcessor';
import VoiceVisualizer from '../voice/VoiceVisualizer';
import ConversationHistory from '../voice/ConversationHistory';
import { VoiceService } from '../../services/voiceService';
import { MasterOrchestrationService } from '../../services/masterOrchestrationService';

// Mock dependencies
jest.mock('@react-native-voice/voice', () => ({
  start: jest.fn(),
  stop: jest.fn(),
  cancel: jest.fn(),
  destroy: jest.fn(),
  removeAllListeners: jest.fn(),
  onSpeechStart: jest.fn(),
  onSpeechEnd: jest.fn(),
  onSpeechResults: jest.fn(),
  onSpeechError: jest.fn(),
  onSpeechPartialResults: jest.fn(),
  isAvailable: jest.fn().mockResolvedValue(true),
  isRecognizing: jest.fn().mockResolvedValue(false),
}));

jest.mock('../../services/voiceService');
jest.mock('../../services/masterOrchestrationService');

const mockVoiceService = VoiceService as jest.Mocked<typeof VoiceService>;
const mockOrchestrationService = MasterOrchestrationService as jest.Mocked<typeof MasterOrchestrationService>;

const mockStore = configureStore({
  reducer: {
    voice: (state = { 
      isListening: false, 
      conversation: [],
      settings: { language: 'en-US', speechRate: 1.0 }
    }) => state,
    user: (state = { preferences: {} }) => state,
    location: (state = { current: { lat: 37.7749, lng: -122.4194 } }) => state,
  },
});

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <Provider store={mockStore}>
      {component}
    </Provider>
  );
};

describe('VoiceAssistant Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders voice assistant interface', () => {
    const { getByTestId, getByText } = renderWithProviders(<VoiceAssistant />);
    
    expect(getByTestId('voice-button')).toBeTruthy();
    expect(getByText('Tap to speak')).toBeTruthy();
  });

  it('starts listening when voice button pressed', async () => {
    const { getByTestId } = renderWithProviders(<VoiceAssistant />);
    
    const voiceButton = getByTestId('voice-button');
    fireEvent.press(voiceButton);
    
    await waitFor(() => {
      expect(Voice.start).toHaveBeenCalledWith('en-US');
    });
  });

  it('stops listening when pressed again', async () => {
    const { getByTestId } = renderWithProviders(<VoiceAssistant />);
    
    const voiceButton = getByTestId('voice-button');
    
    // Start listening
    fireEvent.press(voiceButton);
    await waitFor(() => expect(Voice.start).toHaveBeenCalled());
    
    // Stop listening
    fireEvent.press(voiceButton);
    await waitFor(() => expect(Voice.stop).toHaveBeenCalled());
  });

  it('displays real-time transcription', async () => {
    const { getByTestId, getByText } = renderWithProviders(<VoiceAssistant />);
    
    // Start listening
    fireEvent.press(getByTestId('voice-button'));
    
    // Simulate partial results
    act(() => {
      const onPartialResults = Voice.onSpeechPartialResults.mock.calls[0][0];
      onPartialResults({ value: ['Navigate to'] });
    });
    
    await waitFor(() => {
      expect(getByText('Navigate to...')).toBeTruthy();
    });
    
    // Simulate final results
    act(() => {
      const onResults = Voice.onSpeechResults.mock.calls[0][0];
      onResults({ value: ['Navigate to San Francisco'] });
    });
    
    await waitFor(() => {
      expect(getByText('Navigate to San Francisco')).toBeTruthy();
    });
  });

  it('handles voice recognition errors', async () => {
    const { getByTestId, getByText } = renderWithProviders(<VoiceAssistant />);
    
    fireEvent.press(getByTestId('voice-button'));
    
    // Simulate error
    act(() => {
      const onError = Voice.onSpeechError.mock.calls[0][0];
      onError({ error: { message: 'No speech detected' } });
    });
    
    await waitFor(() => {
      expect(getByText('No speech detected. Please try again.')).toBeTruthy();
    });
  });

  it('processes voice commands through orchestration', async () => {
    mockOrchestrationService.processCommand.mockResolvedValue({
      intent: 'navigation',
      response: 'Starting navigation to San Francisco',
      actions: [{ type: 'navigate', destination: 'San Francisco' }],
    });

    const { getByTestId } = renderWithProviders(<VoiceAssistant />);
    
    fireEvent.press(getByTestId('voice-button'));
    
    // Simulate voice input
    act(() => {
      const onResults = Voice.onSpeechResults.mock.calls[0][0];
      onResults({ value: ['Navigate to San Francisco'] });
    });
    
    await waitFor(() => {
      expect(mockOrchestrationService.processCommand).toHaveBeenCalledWith({
        text: 'Navigate to San Francisco',
        context: expect.objectContaining({
          location: { lat: 37.7749, lng: -122.4194 },
        }),
      });
    });
  });

  it('shows voice visualizer when listening', async () => {
    const { getByTestId, queryByTestId } = renderWithProviders(<VoiceAssistant />);
    
    expect(queryByTestId('voice-visualizer')).toBeNull();
    
    fireEvent.press(getByTestId('voice-button'));
    
    await waitFor(() => {
      expect(getByTestId('voice-visualizer')).toBeTruthy();
    });
  });
});

describe('VoiceCommandProcessor Component', () => {
  it('identifies navigation commands', async () => {
    const onProcessed = jest.fn();
    const { rerender } = renderWithProviders(
      <VoiceCommandProcessor 
        command="Take me to the Golden Gate Bridge"
        onProcessed={onProcessed}
      />
    );
    
    await waitFor(() => {
      expect(onProcessed).toHaveBeenCalledWith({
        type: 'navigation',
        entities: { destination: 'Golden Gate Bridge' },
        confidence: expect.any(Number),
      });
    });
  });

  it('identifies booking commands', async () => {
    const onProcessed = jest.fn();
    renderWithProviders(
      <VoiceCommandProcessor 
        command="Book a table for 4 at 7pm"
        onProcessed={onProcessed}
      />
    );
    
    await waitFor(() => {
      expect(onProcessed).toHaveBeenCalledWith({
        type: 'booking',
        entities: {
          bookingType: 'restaurant',
          partySize: 4,
          time: '7:00 PM',
        },
        confidence: expect.any(Number),
      });
    });
  });

  it('identifies story requests', async () => {
    const onProcessed = jest.fn();
    renderWithProviders(
      <VoiceCommandProcessor 
        command="Tell me about the history of this place"
        onProcessed={onProcessed}
      />
    );
    
    await waitFor(() => {
      expect(onProcessed).toHaveBeenCalledWith({
        type: 'story',
        entities: { theme: 'history' },
        confidence: expect.any(Number),
      });
    });
  });

  it('handles multi-intent commands', async () => {
    const onProcessed = jest.fn();
    renderWithProviders(
      <VoiceCommandProcessor 
        command="Navigate to Napa Valley and book a wine tasting"
        onProcessed={onProcessed}
      />
    );
    
    await waitFor(() => {
      expect(onProcessed).toHaveBeenCalledWith({
        type: 'multi',
        intents: ['navigation', 'booking'],
        entities: {
          destination: 'Napa Valley',
          bookingType: 'experience',
          experienceType: 'wine tasting',
        },
        confidence: expect.any(Number),
      });
    });
  });
});

describe('VoiceVisualizer Component', () => {
  it('animates based on audio levels', () => {
    const { getByTestId } = renderWithProviders(
      <VoiceVisualizer isActive={true} audioLevel={0.5} />
    );
    
    const visualizer = getByTestId('voice-visualizer');
    expect(visualizer.props.style).toMatchObject({
      transform: expect.arrayContaining([
        { scale: expect.any(Number) }
      ]),
    });
  });

  it('shows inactive state when not listening', () => {
    const { getByTestId } = renderWithProviders(
      <VoiceVisualizer isActive={false} audioLevel={0} />
    );
    
    const visualizer = getByTestId('voice-visualizer');
    expect(visualizer.props.style.opacity).toBe(0.5);
  });

  it('pulses during active listening', async () => {
    const { getByTestId, rerender } = renderWithProviders(
      <VoiceVisualizer isActive={true} audioLevel={0.3} />
    );
    
    const visualizer = getByTestId('voice-visualizer');
    const initialScale = visualizer.props.style.transform[0].scale;
    
    // Simulate audio level change
    rerender(<VoiceVisualizer isActive={true} audioLevel={0.8} />);
    
    await waitFor(() => {
      const newScale = visualizer.props.style.transform[0].scale;
      expect(newScale).toBeGreaterThan(initialScale);
    });
  });
});

describe('ConversationHistory Component', () => {
  const mockConversation = [
    {
      id: '1',
      type: 'user',
      text: 'Navigate to San Francisco',
      timestamp: new Date('2024-01-20T10:00:00'),
    },
    {
      id: '2',
      type: 'assistant',
      text: 'Starting navigation to San Francisco. ETA is 45 minutes.',
      timestamp: new Date('2024-01-20T10:00:05'),
    },
    {
      id: '3',
      type: 'user',
      text: 'Find restaurants along the way',
      timestamp: new Date('2024-01-20T10:15:00'),
    },
    {
      id: '4',
      type: 'assistant',
      text: 'I found 3 Italian restaurants along your route.',
      timestamp: new Date('2024-01-20T10:15:03'),
    },
  ];

  it('displays conversation history', () => {
    const { getByText } = renderWithProviders(
      <ConversationHistory conversation={mockConversation} />
    );
    
    expect(getByText('Navigate to San Francisco')).toBeTruthy();
    expect(getByText('Starting navigation to San Francisco. ETA is 45 minutes.')).toBeTruthy();
    expect(getByText('Find restaurants along the way')).toBeTruthy();
    expect(getByText('I found 3 Italian restaurants along your route.')).toBeTruthy();
  });

  it('scrolls to latest message', async () => {
    const scrollToEnd = jest.fn();
    const { rerender } = renderWithProviders(
      <ConversationHistory conversation={mockConversation} />
    );
    
    // Add new message
    const newMessage = {
      id: '5',
      type: 'user',
      text: 'Book the first one',
      timestamp: new Date(),
    };
    
    rerender(
      <ConversationHistory 
        conversation={[...mockConversation, newMessage]} 
      />
    );
    
    // Should auto-scroll to show new message
    await waitFor(() => {
      const scrollView = screen.getByTestId('conversation-scroll');
      expect(scrollView.props.onContentSizeChange).toBeDefined();
    });
  });

  it('allows copying messages', () => {
    const { getByText, getAllByTestId } = renderWithProviders(
      <ConversationHistory conversation={mockConversation} />
    );
    
    const messages = getAllByTestId('conversation-message');
    fireEvent.longPress(messages[0]);
    
    // Should show copy option
    waitFor(() => {
      expect(getByText('Copy')).toBeTruthy();
    });
  });

  it('groups messages by time', () => {
    const { getByText } = renderWithProviders(
      <ConversationHistory conversation={mockConversation} groupByTime={true} />
    );
    
    // Should show time headers
    expect(getByText('10:00 AM')).toBeTruthy();
    expect(getByText('10:15 AM')).toBeTruthy();
  });
});

describe('Voice Settings Component', () => {
  it('allows changing voice language', async () => {
    const { getByText, getByTestId } = renderWithProviders(<VoiceSettings />);
    
    fireEvent.press(getByTestId('language-selector'));
    
    await waitFor(() => {
      expect(getByText('English (US)')).toBeTruthy();
      expect(getByText('Spanish (ES)')).toBeTruthy();
      expect(getByText('French (FR)')).toBeTruthy();
    });
    
    fireEvent.press(getByText('Spanish (ES)'));
    
    await waitFor(() => {
      expect(mockVoiceService.setLanguage).toHaveBeenCalledWith('es-ES');
    });
  });

  it('allows adjusting speech rate', () => {
    const { getByTestId } = renderWithProviders(<VoiceSettings />);
    
    const speechRateSlider = getByTestId('speech-rate-slider');
    fireEvent(speechRateSlider, 'valueChange', 0.8);
    
    expect(mockVoiceService.setSpeechRate).toHaveBeenCalledWith(0.8);
  });

  it('allows toggling voice activation', async () => {
    const { getByTestId } = renderWithProviders(<VoiceSettings />);
    
    const voiceActivationSwitch = getByTestId('voice-activation-switch');
    fireEvent(voiceActivationSwitch, 'valueChange', true);
    
    await waitFor(() => {
      expect(mockVoiceService.enableWakeWord).toHaveBeenCalledWith(true);
    });
  });

  it('allows selecting voice personality', async () => {
    const { getByText, getByTestId } = renderWithProviders(<VoiceSettings />);
    
    fireEvent.press(getByTestId('voice-personality-selector'));
    
    await waitFor(() => {
      expect(getByText('Friendly Guide')).toBeTruthy();
      expect(getByText('Professional')).toBeTruthy();
      expect(getByText('Storyteller')).toBeTruthy();
    });
    
    fireEvent.press(getByText('Storyteller'));
    
    expect(mockVoiceService.setPersonality).toHaveBeenCalledWith('storyteller');
  });
});