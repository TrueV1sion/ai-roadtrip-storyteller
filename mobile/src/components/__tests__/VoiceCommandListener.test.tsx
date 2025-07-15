import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import VoiceCommandListener from '../VoiceCommandListener';
import { useVoiceCommands } from '@/hooks/useVoiceCommands';

// Mock dependencies
jest.mock('@/hooks/useVoiceCommands');
jest.mock('@expo/vector-icons', () => ({
  Ionicons: 'Icon',
}));

// Mock window.speechSynthesis
global.speechSynthesis = {
  speak: jest.fn(),
} as any;

global.SpeechSynthesisUtterance = jest.fn() as any;

describe('VoiceCommandListener', () => {
  const mockStartListening = jest.fn();
  const mockStopListening = jest.fn();
  const mockProcessCommand = jest.fn();
  const mockOnStoryCommand = jest.fn();
  const mockOnNavigationCommand = jest.fn();
  const mockOnPlaybackCommand = jest.fn();
  const mockOnBookingCommand = jest.fn();

  const defaultVoiceCommandsReturn = {
    isListening: false,
    commands: [],
    startListening: mockStartListening,
    stopListening: mockStopListening,
    processCommand: mockProcessCommand,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useVoiceCommands as jest.Mock).mockReturnValue(defaultVoiceCommandsReturn);
  });

  it('renders voice button', () => {
    const { getByTestId } = render(<VoiceCommandListener />);
    
    expect(getByTestId('voice-button')).toBeTruthy();
  });

  it('toggles listening when voice button is pressed', async () => {
    const { getByTestId, rerender } = render(<VoiceCommandListener />);
    
    const voiceButton = getByTestId('voice-button');
    fireEvent.press(voiceButton);
    
    await waitFor(() => {
      expect(mockStartListening).toHaveBeenCalled();
    });
    
    // Update to listening state
    (useVoiceCommands as jest.Mock).mockReturnValue({
      ...defaultVoiceCommandsReturn,
      isListening: true,
    });
    
    rerender(<VoiceCommandListener />);
    
    fireEvent.press(voiceButton);
    
    await waitFor(() => {
      expect(mockStopListening).toHaveBeenCalled();
    });
  });

  it('shows feedback message when listening starts', async () => {
    const { getByTestId, getByText } = render(<VoiceCommandListener />);
    
    fireEvent.press(getByTestId('voice-button'));
    
    await waitFor(() => {
      expect(getByText('Listening...')).toBeTruthy();
    });
  });

  it('opens help modal when help button is pressed', async () => {
    const { getByTestId, getByText } = render(<VoiceCommandListener />);
    
    fireEvent.press(getByTestId('help-button'));
    
    await waitFor(() => {
      expect(getByText('Voice Commands')).toBeTruthy();
      expect(getByText('Say "App" or "Journey" before each command')).toBeTruthy();
    });
  });

  it('closes help modal when close button is pressed', async () => {
    const { getByTestId, getByText, queryByText } = render(<VoiceCommandListener />);
    
    fireEvent.press(getByTestId('help-button'));
    
    await waitFor(() => {
      expect(getByText('Voice Commands')).toBeTruthy();
    });
    
    fireEvent.press(getByText('Close'));
    
    await waitFor(() => {
      expect(queryByText('Voice Commands')).toBeNull();
    });
  });

  it('handles playback commands', async () => {
    const { rerender } = render(
      <VoiceCommandListener onPlaybackCommand={mockOnPlaybackCommand} />
    );
    
    // Simulate command recognition
    const commandHandler = (useVoiceCommands as jest.Mock).mock.calls[0][0];
    commandHandler({ action: 'play', params: [] });
    
    await waitFor(() => {
      expect(mockOnPlaybackCommand).toHaveBeenCalledWith('play', []);
    });
  });

  it('handles story commands', async () => {
    const { rerender } = render(
      <VoiceCommandListener onStoryCommand={mockOnStoryCommand} />
    );
    
    const commandHandler = (useVoiceCommands as jest.Mock).mock.calls[0][0];
    commandHandler({ action: 'next', params: [] });
    
    await waitFor(() => {
      expect(mockOnStoryCommand).toHaveBeenCalledWith('next', []);
    });
  });

  it('handles navigation commands', async () => {
    const { rerender } = render(
      <VoiceCommandListener onNavigationCommand={mockOnNavigationCommand} />
    );
    
    const commandHandler = (useVoiceCommands as jest.Mock).mock.calls[0][0];
    commandHandler({ action: 'navigate', params: ['New York'] });
    
    await waitFor(() => {
      expect(mockOnNavigationCommand).toHaveBeenCalledWith('navigate', ['New York']);
    });
  });

  it('handles booking commands', async () => {
    const { rerender } = render(
      <VoiceCommandListener onBookingCommand={mockOnBookingCommand} />
    );
    
    const commandHandler = (useVoiceCommands as jest.Mock).mock.calls[0][0];
    commandHandler({ action: 'book', params: ['restaurant'] });
    
    await waitFor(() => {
      expect(mockOnBookingCommand).toHaveBeenCalledWith('book', ['restaurant']);
    });
  });

  it('renders in voice-first mode', () => {
    const { getByTestId, getByText } = render(
      <VoiceCommandListener voiceFirst={true} />
    );
    
    const voiceButton = getByTestId('voice-button');
    expect(voiceButton.props.style).toContainEqual(
      expect.objectContaining({ width: 120, height: 120 })
    );
    expect(getByText('Tap to speak')).toBeTruthy();
  });

  it('auto-starts listening in voice-first mode', async () => {
    render(<VoiceCommandListener voiceFirst={true} />);
    
    await waitFor(() => {
      expect(mockStartListening).toHaveBeenCalled();
    });
  });

  it('speaks feedback in driving mode', async () => {
    render(<VoiceCommandListener isDriving={true} />);
    
    const commandHandler = (useVoiceCommands as jest.Mock).mock.calls[0][0];
    commandHandler({ action: 'play', params: [] });
    
    await waitFor(() => {
      expect(global.SpeechSynthesisUtterance).toHaveBeenCalledWith('Playback: play');
      expect(global.speechSynthesis.speak).toHaveBeenCalled();
    });
  });

  it('renders larger button in driving mode', () => {
    const { getByTestId } = render(
      <VoiceCommandListener isDriving={true} />
    );
    
    const voiceButton = getByTestId('voice-button');
    expect(voiceButton.props.style).toContainEqual(
      expect.objectContaining({ width: 160, height: 160 })
    );
  });

  it('shows development test buttons in dev mode', () => {
    const originalDev = global.__DEV__;
    global.__DEV__ = true;
    
    const { getByText } = render(<VoiceCommandListener />);
    
    expect(getByText('Test Play')).toBeTruthy();
    expect(getByText('Test Help')).toBeTruthy();
    
    global.__DEV__ = originalDev;
  });

  it('handles test command in development', async () => {
    const originalDev = global.__DEV__;
    global.__DEV__ = true;
    
    mockProcessCommand.mockReturnValue(true);
    
    const { getByText } = render(<VoiceCommandListener />);
    
    fireEvent.press(getByText('Test Play'));
    
    await waitFor(() => {
      expect(mockProcessCommand).toHaveBeenCalledWith('app play story');
    });
    
    global.__DEV__ = originalDev;
  });

  it('shows error for unrecognized command', async () => {
    const originalDev = global.__DEV__;
    global.__DEV__ = true;
    
    mockProcessCommand.mockReturnValue(false);
    
    const { getByText } = render(<VoiceCommandListener />);
    
    fireEvent.press(getByText('Test Play'));
    
    await waitFor(() => {
      expect(getByText('Command not recognized')).toBeTruthy();
    });
    
    global.__DEV__ = originalDev;
  });

  it('displays last command text', async () => {
    const { getByText } = render(<VoiceCommandListener />);
    
    const commandHandler = (useVoiceCommands as jest.Mock).mock.calls[0][0];
    commandHandler({ action: 'play', params: [] });
    
    await waitFor(() => {
      expect(getByText('Command: play')).toBeTruthy();
    });
  });

  it('handles help command', async () => {
    const { getByText } = render(<VoiceCommandListener />);
    
    const commandHandler = (useVoiceCommands as jest.Mock).mock.calls[0][0];
    commandHandler({ action: 'help', params: [] });
    
    await waitFor(() => {
      expect(getByText('Voice Commands')).toBeTruthy();
      expect(getByText('Showing help')).toBeTruthy();
    });
  });

  it('handles unknown command', async () => {
    const { getByText } = render(<VoiceCommandListener />);
    
    const commandHandler = (useVoiceCommands as jest.Mock).mock.calls[0][0];
    commandHandler({ action: 'unknown', params: [] });
    
    await waitFor(() => {
      expect(getByText("I didn't understand that command.")).toBeTruthy();
    });
  });
});