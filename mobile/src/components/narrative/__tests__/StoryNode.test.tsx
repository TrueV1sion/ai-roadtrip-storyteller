import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Animated } from 'react-native';

import StoryNode from '../StoryNode';

// Mock Animated for testing
jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  const mockAnimated = {
    ...RN.Animated,
    timing: jest.fn(() => ({
      start: jest.fn((callback) => callback && callback({ finished: true })),
    })),
    sequence: jest.fn(() => ({
      start: jest.fn((callback) => callback && callback({ finished: true })),
    })),
    parallel: jest.fn(() => ({
      start: jest.fn((callback) => callback && callback({ finished: true })),
    })),
  };
  return {
    ...RN,
    Animated: mockAnimated,
  };
});

const mockStoryNode = {
  id: '1',
  title: 'The Journey Begins',
  content: 'You stand at the crossroads of adventure...',
  image: 'https://example.com/journey.jpg',
  choices: [
    {
      id: 'choice1',
      text: 'Take the mountain path',
      consequence: 'brave',
      nextNodeId: '2',
    },
    {
      id: 'choice2',
      text: 'Follow the river trail',
      consequence: 'cautious',
      nextNodeId: '3',
    },
  ],
  metadata: {
    location: 'Starting Point',
    timeOfDay: 'morning',
    weather: 'clear',
  },
};

describe('StoryNode Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders story content correctly', () => {
    const { getByText } = render(
      <StoryNode node={mockStoryNode} onChoice={jest.fn()} />
    );
    
    expect(getByText('The Journey Begins')).toBeTruthy();
    expect(getByText('You stand at the crossroads of adventure...')).toBeTruthy();
  });

  it('displays choice buttons', () => {
    const { getByText } = render(
      <StoryNode node={mockStoryNode} onChoice={jest.fn()} />
    );
    
    expect(getByText('Take the mountain path')).toBeTruthy();
    expect(getByText('Follow the river trail')).toBeTruthy();
  });

  it('calls onChoice when a choice is selected', () => {
    const onChoice = jest.fn();
    const { getByText } = render(
      <StoryNode node={mockStoryNode} onChoice={onChoice} />
    );
    
    fireEvent.press(getByText('Take the mountain path'));
    
    expect(onChoice).toHaveBeenCalledWith(mockStoryNode.choices[0]);
  });

  it('animates content appearance', async () => {
    render(<StoryNode node={mockStoryNode} onChoice={jest.fn()} />);
    
    await waitFor(() => {
      expect(Animated.timing).toHaveBeenCalled();
    });
  });

  it('shows loading state for images', () => {
    const { getByTestId } = render(
      <StoryNode node={mockStoryNode} onChoice={jest.fn()} />
    );
    
    expect(getByTestId('image-loading')).toBeTruthy();
  });

  it('displays metadata information', () => {
    const { getByText } = render(
      <StoryNode node={mockStoryNode} onChoice={jest.fn()} showMetadata={true} />
    );
    
    expect(getByText('Starting Point')).toBeTruthy();
    expect(getByText('Morning')).toBeTruthy();
    expect(getByText('Clear')).toBeTruthy();
  });

  it('supports typewriter effect for content', async () => {
    const { getByText, queryByText } = render(
      <StoryNode 
        node={mockStoryNode} 
        onChoice={jest.fn()} 
        enableTypewriter={true}
      />
    );
    
    // Initially, full text shouldn't be visible
    expect(queryByText('You stand at the crossroads of adventure...')).toBeNull();
    
    // After animation completes
    await waitFor(() => {
      expect(getByText('You stand at the crossroads of adventure...')).toBeTruthy();
    });
  });

  it('disables choices until content is fully displayed', async () => {
    const onChoice = jest.fn();
    const { getByText } = render(
      <StoryNode 
        node={mockStoryNode} 
        onChoice={onChoice} 
        enableTypewriter={true}
      />
    );
    
    const choiceButton = getByText('Take the mountain path');
    
    // Initially disabled
    fireEvent.press(choiceButton);
    expect(onChoice).not.toHaveBeenCalled();
    
    // Wait for content to finish
    await waitFor(() => {
      fireEvent.press(choiceButton);
      expect(onChoice).toHaveBeenCalled();
    });
  });

  it('shows consequence hints on long press', async () => {
    const { getByText } = render(
      <StoryNode node={mockStoryNode} onChoice={jest.fn()} />
    );
    
    fireEvent.longPress(getByText('Take the mountain path'));
    
    await waitFor(() => {
      expect(getByText('This choice shows bravery')).toBeTruthy();
    });
  });

  it('handles nodes without choices (end nodes)', () => {
    const endNode = {
      ...mockStoryNode,
      choices: [],
      isEnd: true,
    };
    
    const { queryByTestId, getByText } = render(
      <StoryNode node={endNode} onChoice={jest.fn()} />
    );
    
    expect(queryByTestId('choice-button')).toBeNull();
    expect(getByText('The End')).toBeTruthy();
  });

  it('supports custom styling', () => {
    const customStyle = {
      backgroundColor: '#f0f0f0',
      padding: 20,
    };
    
    const { getByTestId } = render(
      <StoryNode 
        node={mockStoryNode} 
        onChoice={jest.fn()} 
        style={customStyle}
      />
    );
    
    const container = getByTestId('story-node-container');
    expect(container.props.style).toMatchObject(customStyle);
  });

  it('tracks reading time', async () => {
    const onReadingComplete = jest.fn();
    const { getByText } = render(
      <StoryNode 
        node={mockStoryNode} 
        onChoice={jest.fn()}
        onReadingComplete={onReadingComplete}
      />
    );
    
    // Simulate reading time based on content length
    await waitFor(() => {
      expect(onReadingComplete).toHaveBeenCalledWith({
        nodeId: mockStoryNode.id,
        timeSpent: expect.any(Number),
      });
    }, { timeout: 5000 });
  });

  it('shows audio narration button when available', () => {
    const nodeWithAudio = {
      ...mockStoryNode,
      audioUrl: 'https://example.com/narration.mp3',
    };
    
    const { getByTestId } = render(
      <StoryNode node={nodeWithAudio} onChoice={jest.fn()} />
    );
    
    expect(getByTestId('play-narration-button')).toBeTruthy();
  });

  it('highlights important words in content', () => {
    const nodeWithHighlights = {
      ...mockStoryNode,
      content: 'You stand at the *crossroads* of adventure...',
      highlights: ['crossroads'],
    };
    
    const { getByTestId } = render(
      <StoryNode node={nodeWithHighlights} onChoice={jest.fn()} />
    );
    
    const highlightedWord = getByTestId('highlighted-word-crossroads');
    expect(highlightedWord.props.style.fontWeight).toBe('bold');
  });
});