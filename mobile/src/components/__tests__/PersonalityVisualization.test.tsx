import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import { Animated } from 'react-native';
import PersonalityVisualization from '../voice/PersonalityVisualization';
import { personalityEngine } from '@/services/personalityEngine';
import { VoicePersonality } from '@/types/voice';

// Mock dependencies
jest.mock('@/services/personalityEngine');
jest.mock('@expo/vector-icons', () => ({
  MaterialIcons: 'Icon',
  MaterialCommunityIcons: 'Icon',
  FontAwesome5: 'Icon',
}));
jest.mock('react-native-svg', () => ({
  Svg: 'Svg',
  Circle: 'Circle',
  Path: 'Path',
  G: 'G',
  Text: 'Text',
  Rect: 'Rect',
  Defs: 'Defs',
  RadialGradient: 'RadialGradient',
  Stop: 'Stop',
  Mask: 'Mask',
}));
jest.mock('react-native-reanimated', () => ({
  ...jest.requireActual('react-native-reanimated/mock'),
  useSharedValue: jest.fn(() => ({ value: 0 })),
  useAnimatedStyle: jest.fn(() => ({})),
  withSpring: jest.fn((value) => value),
  withTiming: jest.fn((value) => value),
}));

describe('PersonalityVisualization', () => {
  const mockOnPersonalityChange = jest.fn();
  
  const mockPersonality: VoicePersonality = {
    id: 'captain-adventure',
    name: 'Captain Adventure',
    voice: 'en-US-Wavenet-D',
    avatar: 'captain-avatar.png',
    traits: {
      enthusiasm: 0.9,
      formality: 0.3,
      humor: 0.7,
      empathy: 0.8,
      knowledge: 0.85,
    },
    specialties: ['exploration', 'history', 'adventure'],
    catchphrases: [
      "Let's explore!",
      "Adventure awaits!",
      "Fascinating history here!",
    ],
    backgroundColor: '#FF6B6B',
    accentColor: '#4ECDC4',
  };

  const mockAlternativePersonalities = [
    {
      id: 'professor-knowledge',
      name: 'Professor Knowledge',
      traits: {
        enthusiasm: 0.6,
        formality: 0.9,
        humor: 0.3,
        empathy: 0.7,
        knowledge: 0.95,
      },
    },
    {
      id: 'buddy-roadtrip',
      name: 'Buddy Roadtrip',
      traits: {
        enthusiasm: 0.8,
        formality: 0.2,
        humor: 0.9,
        empathy: 0.85,
        knowledge: 0.6,
      },
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    (personalityEngine.getCurrentPersonality as jest.Mock).mockReturnValue(mockPersonality);
    (personalityEngine.getAvailablePersonalities as jest.Mock).mockReturnValue(mockAlternativePersonalities);
    (personalityEngine.getPersonalityMatch as jest.Mock).mockReturnValue(0.85);
  });

  it('renders current personality visualization', () => {
    const { getByText, getByTestId } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
      />
    );
    
    expect(getByText('Captain Adventure')).toBeTruthy();
    expect(getByTestId('personality-avatar')).toBeTruthy();
    expect(getByTestId('traits-radar-chart')).toBeTruthy();
  });

  it('displays personality traits', () => {
    const { getByText } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
      />
    );
    
    expect(getByText('Enthusiasm: 90%')).toBeTruthy();
    expect(getByText('Formality: 30%')).toBeTruthy();
    expect(getByText('Humor: 70%')).toBeTruthy();
    expect(getByText('Empathy: 80%')).toBeTruthy();
    expect(getByText('Knowledge: 85%')).toBeTruthy();
  });

  it('shows specialties', () => {
    const { getByText } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
      />
    );
    
    expect(getByText('Exploration')).toBeTruthy();
    expect(getByText('History')).toBeTruthy();
    expect(getByText('Adventure')).toBeTruthy();
  });

  it('displays catchphrases', () => {
    const { getByText } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        showCatchphrases={true}
      />
    );
    
    mockPersonality.catchphrases.forEach(phrase => {
      expect(getByText(phrase)).toBeTruthy();
    });
  });

  it('renders radar chart for traits', () => {
    const { getByTestId } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
      />
    );
    
    const radarChart = getByTestId('traits-radar-chart');
    expect(radarChart).toBeTruthy();
    
    // Check for trait points
    Object.keys(mockPersonality.traits).forEach(trait => {
      expect(getByTestId(`trait-point-${trait}`)).toBeTruthy();
    });
  });

  it('handles personality switching', async () => {
    const { getByText } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        allowSwitching={true}
        onPersonalityChange={mockOnPersonalityChange}
      />
    );
    
    const switchButton = getByText('Switch Personality');
    fireEvent.press(switchButton);
    
    await waitFor(() => {
      expect(getByText('Professor Knowledge')).toBeTruthy();
      expect(getByText('Buddy Roadtrip')).toBeTruthy();
    });
    
    const professorOption = getByText('Professor Knowledge');
    fireEvent.press(professorOption);
    
    expect(mockOnPersonalityChange).toHaveBeenCalledWith('professor-knowledge');
  });

  it('shows personality match score', () => {
    const { getByText } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        showMatchScore={true}
      />
    );
    
    expect(getByText('85% Match')).toBeTruthy();
    expect(getByText(/Based on your preferences/)).toBeTruthy();
  });

  it('displays mood indicator', () => {
    const { getByTestId } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        currentMood="excited"
      />
    );
    
    expect(getByTestId('mood-indicator')).toBeTruthy();
    expect(getByTestId('mood-excited')).toBeTruthy();
  });

  it('animates personality transitions', async () => {
    const { rerender, getByTestId } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
      />
    );
    
    const newPersonality = {
      ...mockPersonality,
      id: 'professor-knowledge',
      name: 'Professor Knowledge',
    };
    
    rerender(
      <PersonalityVisualization 
        personality={newPersonality}
        isVisible={true}
      />
    );
    
    expect(getByTestId('personality-transition')).toBeTruthy();
  });

  it('shows personality comparison', async () => {
    const { getByText, getByTestId } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        compareMode={true}
      />
    );
    
    const compareButton = getByText('Compare');
    fireEvent.press(compareButton);
    
    await waitFor(() => {
      expect(getByTestId('comparison-view')).toBeTruthy();
      expect(getByTestId('traits-comparison-chart')).toBeTruthy();
    });
  });

  it('displays interaction style preview', () => {
    const { getByText, getByTestId } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        showInteractionPreview={true}
      />
    );
    
    expect(getByText('Interaction Style')).toBeTruthy();
    expect(getByTestId('sample-responses')).toBeTruthy();
  });

  it('handles personality customization', async () => {
    const mockOnCustomize = jest.fn();
    
    const { getByText, getByTestId } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        allowCustomization={true}
        onCustomize={mockOnCustomize}
      />
    );
    
    const customizeButton = getByText('Customize');
    fireEvent.press(customizeButton);
    
    await waitFor(() => {
      expect(getByText('Adjust Traits')).toBeTruthy();
    });
    
    const enthusiasmSlider = getByTestId('trait-slider-enthusiasm');
    fireEvent(enthusiasmSlider, 'onValueChange', 0.5);
    
    const saveButton = getByText('Save Changes');
    fireEvent.press(saveButton);
    
    expect(mockOnCustomize).toHaveBeenCalledWith({
      ...mockPersonality.traits,
      enthusiasm: 0.5,
    });
  });

  it('shows voice sample player', async () => {
    const { getByTestId } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        showVoiceSample={true}
      />
    );
    
    const playButton = getByTestId('play-voice-sample');
    fireEvent.press(playButton);
    
    await waitFor(() => {
      expect(personalityEngine.playVoiceSample).toHaveBeenCalledWith(mockPersonality.id);
    });
  });

  it('displays personality history', async () => {
    const mockHistory = [
      { personality: 'captain-adventure', timestamp: Date.now() - 3600000 },
      { personality: 'professor-knowledge', timestamp: Date.now() - 7200000 },
    ];
    
    (personalityEngine.getPersonalityHistory as jest.Mock).mockReturnValue(mockHistory);
    
    const { getByText } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        showHistory={true}
      />
    );
    
    const historyButton = getByText('View History');
    fireEvent.press(historyButton);
    
    await waitFor(() => {
      expect(getByText('Personality History')).toBeTruthy();
      expect(getByText(/Captain Adventure - 1 hour ago/)).toBeTruthy();
    });
  });

  it('shows contextual recommendations', () => {
    (personalityEngine.getRecommendedPersonality as jest.Mock).mockReturnValue({
      personality: 'professor-knowledge',
      reason: 'Historical landmark nearby',
      confidence: 0.9,
    });
    
    const { getByText } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        showRecommendations={true}
      />
    );
    
    expect(getByText(/Professor Knowledge recommended/)).toBeTruthy();
    expect(getByText('Historical landmark nearby')).toBeTruthy();
  });

  it('handles 3D visualization mode', async () => {
    const { getByTestId } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        enable3D={true}
      />
    );
    
    expect(getByTestId('3d-personality-model')).toBeTruthy();
    
    // Test rotation
    const model = getByTestId('3d-personality-model');
    fireEvent(model, 'onPanGesture', { translationX: 50 });
    
    await waitFor(() => {
      expect(getByTestId('rotation-indicator')).toBeTruthy();
    });
  });

  it('displays personality stats', () => {
    (personalityEngine.getPersonalityStats as jest.Mock).mockReturnValue({
      timesUsed: 42,
      averageRating: 4.5,
      favoriteTime: 'evening',
      commonPhrases: ['Adventure awaits!', "Let's explore!"],
    });
    
    const { getByText } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        showStats={true}
      />
    );
    
    expect(getByText('Used 42 times')).toBeTruthy();
    expect(getByText('4.5★ average rating')).toBeTruthy();
    expect(getByText('Most active: evening')).toBeTruthy();
  });

  it('handles export functionality', async () => {
    const { getByTestId } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        allowExport={true}
      />
    );
    
    const exportButton = getByTestId('export-personality');
    fireEvent.press(exportButton);
    
    await waitFor(() => {
      expect(personalityEngine.exportPersonality).toHaveBeenCalledWith(mockPersonality.id);
    });
  });

  it('shows accessibility descriptions', () => {
    const { getByLabelText } = render(
      <PersonalityVisualization 
        personality={mockPersonality}
        isVisible={true}
        accessibilityMode={true}
      />
    );
    
    expect(getByLabelText('Captain Adventure personality visualization')).toBeTruthy();
    expect(getByLabelText('Personality traits radar chart')).toBeTruthy();
    expect(getByLabelText('90 percent enthusiasm')).toBeTruthy();
  });
});