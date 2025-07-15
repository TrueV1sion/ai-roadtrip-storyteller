import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import { Animated } from 'react-native';
import InteractiveFeatureButton from '../InteractiveFeatureButton';
import { useVoiceCommands } from '@/hooks/useVoiceCommands';

// Mock dependencies
jest.mock('@/hooks/useVoiceCommands');
jest.mock('@expo/vector-icons', () => ({
  Ionicons: 'Icon',
}));
jest.mock('../games/GameLauncher', () => 'GameLauncher');
jest.mock('../VoiceCommandListener', () => 'VoiceCommandListener');

// Mock Animated to run immediately
jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  return {
    ...RN,
    Animated: {
      ...RN.Animated,
      timing: (value: any, config: any) => ({
        start: (callback?: any) => {
          value.setValue(config.toValue);
          callback?.();
        },
      }),
      parallel: (animations: any[]) => ({
        start: (callback?: any) => {
          animations.forEach(anim => anim.start());
          callback?.();
        },
      }),
    },
  };
});

describe('InteractiveFeatureButton', () => {
  const mockStartListening = jest.fn();
  const mockStopListening = jest.fn();
  const mockOnImmersiveExperienceRequest = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useVoiceCommands as jest.Mock).mockReturnValue({
      isListening: false,
      startListening: mockStartListening,
      stopListening: mockStopListening,
    });
  });

  it('renders main FAB button', () => {
    const { getByTestId } = render(<InteractiveFeatureButton />);
    
    expect(getByTestId('main-fab')).toBeTruthy();
  });

  it('expands to show feature options when pressed', async () => {
    const { getByTestId, getAllByTestId } = render(<InteractiveFeatureButton />);
    
    const mainFab = getByTestId('main-fab');
    fireEvent.press(mainFab);
    
    await waitFor(() => {
      const options = getAllByTestId(/feature-option-/);
      expect(options).toHaveLength(3); // Games, Voice, Story
    });
  });

  it('collapses when pressed again', async () => {
    const { getByTestId, queryAllByTestId } = render(<InteractiveFeatureButton />);
    
    const mainFab = getByTestId('main-fab');
    
    // Expand
    fireEvent.press(mainFab);
    await waitFor(() => {
      expect(queryAllByTestId(/feature-option-/)).toHaveLength(3);
    });
    
    // Collapse
    fireEvent.press(mainFab);
    await waitFor(() => {
      const options = queryAllByTestId(/feature-option-/);
      // Options still exist but should be animated out
      expect(options).toHaveLength(3);
    });
  });

  it('opens game launcher when games option is pressed', async () => {
    const { getByTestId, UNSAFE_getByType } = render(<InteractiveFeatureButton />);
    
    // Expand menu
    fireEvent.press(getByTestId('main-fab'));
    
    await waitFor(() => {
      const gamesOption = getByTestId('feature-option-game');
      fireEvent.press(gamesOption);
    });
    
    await waitFor(() => {
      const gameLauncher = UNSAFE_getByType('GameLauncher' as any);
      expect(gameLauncher.props.visible).toBe(true);
    });
  });

  it('toggles voice command listener when voice option is pressed', async () => {
    const { getByTestId, queryByType } = render(<InteractiveFeatureButton />);
    
    // Expand menu
    fireEvent.press(getByTestId('main-fab'));
    
    await waitFor(() => {
      const voiceOption = getByTestId('feature-option-voice');
      fireEvent.press(voiceOption);
    });
    
    await waitFor(() => {
      expect(mockStartListening).toHaveBeenCalled();
      expect(queryByType('VoiceCommandListener' as any)).toBeTruthy();
    });
  });

  it('calls onImmersiveExperienceRequest when story option is pressed', async () => {
    const { getByTestId } = render(
      <InteractiveFeatureButton onImmersiveExperienceRequest={mockOnImmersiveExperienceRequest} />
    );
    
    // Expand menu
    fireEvent.press(getByTestId('main-fab'));
    
    await waitFor(() => {
      const storyOption = getByTestId('feature-option-story');
      fireEvent.press(storyOption);
    });
    
    await waitFor(() => {
      expect(mockOnImmersiveExperienceRequest).toHaveBeenCalled();
    });
  });

  it('shows listening indicator when voice is active', () => {
    (useVoiceCommands as jest.Mock).mockReturnValue({
      isListening: true,
      startListening: mockStartListening,
      stopListening: mockStopListening,
    });
    
    const { getByTestId } = render(<InteractiveFeatureButton />);
    
    expect(getByTestId('listening-indicator')).toBeTruthy();
  });

  it('closes expanded menu when backdrop is pressed', async () => {
    const { getByTestId, queryByTestId } = render(<InteractiveFeatureButton />);
    
    // Expand menu
    fireEvent.press(getByTestId('main-fab'));
    
    await waitFor(() => {
      expect(getByTestId('backdrop')).toBeTruthy();
    });
    
    // Press backdrop
    fireEvent.press(getByTestId('backdrop'));
    
    await waitFor(() => {
      expect(queryByTestId('backdrop')).toBeNull();
    });
  });

  it('handles playback command to start immersive experience', async () => {
    const { getByTestId, UNSAFE_getByType } = render(
      <InteractiveFeatureButton onImmersiveExperienceRequest={mockOnImmersiveExperienceRequest} />
    );
    
    // Open voice command listener
    fireEvent.press(getByTestId('main-fab'));
    await waitFor(() => {
      fireEvent.press(getByTestId('feature-option-voice'));
    });
    
    // Get voice command listener component
    const voiceListener = UNSAFE_getByType('VoiceCommandListener' as any);
    
    // Simulate playback command
    voiceListener.props.onPlaybackCommand('play', []);
    
    await waitFor(() => {
      expect(mockOnImmersiveExperienceRequest).toHaveBeenCalled();
    });
  });

  it('closes game launcher when onClose is called', async () => {
    const { getByTestId, UNSAFE_getByType } = render(<InteractiveFeatureButton />);
    
    // Open game launcher
    fireEvent.press(getByTestId('main-fab'));
    await waitFor(() => {
      fireEvent.press(getByTestId('feature-option-game'));
    });
    
    const gameLauncher = UNSAFE_getByType('GameLauncher' as any);
    
    // Close game launcher
    gameLauncher.props.onClose();
    
    await waitFor(() => {
      const updatedGameLauncher = UNSAFE_getByType('GameLauncher' as any);
      expect(updatedGameLauncher.props.visible).toBe(false);
    });
  });

  it('stops listening when voice UI is closed', async () => {
    const { getByTestId, queryByType } = render(<InteractiveFeatureButton />);
    
    // Open voice command listener
    fireEvent.press(getByTestId('main-fab'));
    await waitFor(() => {
      fireEvent.press(getByTestId('feature-option-voice'));
    });
    
    expect(mockStartListening).toHaveBeenCalled();
    
    // Open menu again
    fireEvent.press(getByTestId('main-fab'));
    
    // Press voice option again to close
    await waitFor(() => {
      fireEvent.press(getByTestId('feature-option-voice'));
    });
    
    await waitFor(() => {
      expect(mockStopListening).toHaveBeenCalled();
      expect(queryByType('VoiceCommandListener' as any)).toBeNull();
    });
  });

  it('renders feature options with correct styles', async () => {
    const { getByTestId } = render(<InteractiveFeatureButton />);
    
    // Expand menu
    fireEvent.press(getByTestId('main-fab'));
    
    await waitFor(() => {
      const gameOption = getByTestId('feature-option-game');
      const voiceOption = getByTestId('feature-option-voice');
      const storyOption = getByTestId('feature-option-story');
      
      // Check background colors
      expect(gameOption.props.style).toMatchObject({ backgroundColor: '#f4511e' });
      expect(voiceOption.props.style).toMatchObject({ backgroundColor: '#4CAF50' });
      expect(storyOption.props.style).toMatchObject({ backgroundColor: '#2196F3' });
    });
  });
});