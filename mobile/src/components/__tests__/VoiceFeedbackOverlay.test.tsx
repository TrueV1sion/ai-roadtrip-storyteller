import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import { Animated } from 'react-native';
import VoiceFeedbackOverlay from '../voice/VoiceFeedbackOverlay';
import { voiceService } from '@/services/voiceService';
import { hapticFeedback } from '@/utils/hapticFeedback';

// Mock dependencies
jest.mock('@/services/voiceService');
jest.mock('@/utils/hapticFeedback');
jest.mock('@expo/vector-icons', () => ({
  MaterialIcons: 'Icon',
  MaterialCommunityIcons: 'Icon',
}));
jest.mock('react-native-svg', () => ({
  Svg: 'Svg',
  Circle: 'Circle',
  Path: 'Path',
  G: 'G',
  Defs: 'Defs',
  LinearGradient: 'LinearGradient',
  Stop: 'Stop',
}));

describe('VoiceFeedbackOverlay', () => {
  const mockOnDismiss = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('renders listening state', () => {
    const { getByText, getByTestId } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
      />
    );
    
    expect(getByText('Listening...')).toBeTruthy();
    expect(getByTestId('listening-animation')).toBeTruthy();
    expect(getByTestId('waveform-visualizer')).toBeTruthy();
  });

  it('renders processing state', () => {
    const { getByText, getByTestId } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="processing"
      />
    );
    
    expect(getByText('Processing...')).toBeTruthy();
    expect(getByTestId('processing-spinner')).toBeTruthy();
  });

  it('renders success state', () => {
    const { getByText, getByTestId } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="success"
        message="Command executed successfully"
      />
    );
    
    expect(getByText('Success')).toBeTruthy();
    expect(getByText('Command executed successfully')).toBeTruthy();
    expect(getByTestId('success-icon')).toBeTruthy();
  });

  it('renders error state', () => {
    const { getByText, getByTestId } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="error"
        message="Could not understand command"
      />
    );
    
    expect(getByText('Error')).toBeTruthy();
    expect(getByText('Could not understand command')).toBeTruthy();
    expect(getByTestId('error-icon')).toBeTruthy();
  });

  it('displays transcribed text', () => {
    const { getByText } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
        transcribedText="Navigate to San Francisco"
      />
    );
    
    expect(getByText('Navigate to San Francisco')).toBeTruthy();
  });

  it('shows confidence indicator', () => {
    const { getByTestId, getByText } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="processing"
        confidence={0.85}
      />
    );
    
    expect(getByTestId('confidence-bar')).toBeTruthy();
    expect(getByText('85% confident')).toBeTruthy();
  });

  it('auto-dismisses after timeout', async () => {
    render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="success"
        autoDismissDelay={3000}
        onDismiss={mockOnDismiss}
      />
    );
    
    jest.advanceTimersByTime(3000);
    
    await waitFor(() => {
      expect(mockOnDismiss).toHaveBeenCalled();
    });
  });

  it('handles manual dismiss', () => {
    const { getByTestId } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
        onDismiss={mockOnDismiss}
      />
    );
    
    const dismissButton = getByTestId('dismiss-button');
    fireEvent.press(dismissButton);
    
    expect(mockOnDismiss).toHaveBeenCalled();
  });

  it('shows cancel button in listening state', () => {
    const mockOnCancel = jest.fn();
    
    const { getByText } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
        onCancel={mockOnCancel}
      />
    );
    
    const cancelButton = getByText('Cancel');
    fireEvent.press(cancelButton);
    
    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('displays audio level visualization', () => {
    const { getByTestId } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
        audioLevel={0.7}
      />
    );
    
    const audioMeter = getByTestId('audio-level-meter');
    expect(audioMeter.props.style).toContainEqual(
      expect.objectContaining({ 
        height: expect.stringContaining('%')
      })
    );
  });

  it('shows retry option on error', () => {
    const mockOnRetry = jest.fn();
    
    const { getByText } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="error"
        onRetry={mockOnRetry}
      />
    );
    
    const retryButton = getByText('Try Again');
    fireEvent.press(retryButton);
    
    expect(mockOnRetry).toHaveBeenCalled();
  });

  it('displays command suggestions', () => {
    const suggestions = [
      'Navigate to [destination]',
      'Find nearby restaurants',
      'Play some music',
    ];
    
    const { getByText } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
        suggestions={suggestions}
      />
    );
    
    suggestions.forEach(suggestion => {
      expect(getByText(suggestion)).toBeTruthy();
    });
  });

  it('handles partial results', () => {
    const { getByText, rerender } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
        partialResult="Navigate to"
      />
    );
    
    expect(getByText('Navigate to')).toBeTruthy();
    
    rerender(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
        partialResult="Navigate to San"
      />
    );
    
    expect(getByText('Navigate to San')).toBeTruthy();
  });

  it('shows noise level warning', () => {
    const { getByText } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
        noiseLevel="high"
      />
    );
    
    expect(getByText(/High background noise detected/)).toBeTruthy();
  });

  it('triggers haptic feedback on state changes', () => {
    const { rerender } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
        enableHaptics={true}
      />
    );
    
    rerender(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="success"
        enableHaptics={true}
      />
    );
    
    expect(hapticFeedback.success).toHaveBeenCalled();
  });

  it('displays language indicator', () => {
    const { getByText } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
        language="es-ES"
      />
    );
    
    expect(getByText('Español')).toBeTruthy();
  });

  it('shows processing steps', () => {
    const { getByText } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="processing"
        processingStep="Analyzing intent..."
      />
    );
    
    expect(getByText('Analyzing intent...')).toBeTruthy();
  });

  it('handles multi-turn conversation', () => {
    const { getByText } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
        conversationContext={{
          previousCommand: 'Find restaurants',
          expectingResponse: 'location',
        }}
      />
    );
    
    expect(getByText(/Where would you like to search/)).toBeTruthy();
  });

  it('displays quick actions', () => {
    const mockOnQuickAction = jest.fn();
    
    const { getByTestId } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="success"
        quickActions={[
          { id: 'navigate', label: 'Start Navigation', icon: 'navigation' },
          { id: 'bookmark', label: 'Save Location', icon: 'bookmark' },
        ]}
        onQuickAction={mockOnQuickAction}
      />
    );
    
    const navigateAction = getByTestId('quick-action-navigate');
    fireEvent.press(navigateAction);
    
    expect(mockOnQuickAction).toHaveBeenCalledWith('navigate');
  });

  it('shows accessibility mode', () => {
    const { getByTestId } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="listening"
        accessibilityMode={true}
      />
    );
    
    expect(getByTestId('large-text-display')).toBeTruthy();
    expect(getByTestId('high-contrast-ui')).toBeTruthy();
  });

  it('handles animation completion', async () => {
    const mockOnAnimationComplete = jest.fn();
    
    render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="success"
        onAnimationComplete={mockOnAnimationComplete}
      />
    );
    
    // Simulate animation completion
    jest.advanceTimersByTime(1000);
    
    await waitFor(() => {
      expect(mockOnAnimationComplete).toHaveBeenCalled();
    });
  });

  it('displays error recovery suggestions', () => {
    const { getByText } = render(
      <VoiceFeedbackOverlay 
        isVisible={true}
        state="error"
        errorType="no-match"
        recoverySuggestions={[
          'Try speaking more slowly',
          'Move to a quieter location',
          'Check your internet connection',
        ]}
      />
    );
    
    expect(getByText('Try speaking more slowly')).toBeTruthy();
    expect(getByText('Move to a quieter location')).toBeTruthy();
  });
});