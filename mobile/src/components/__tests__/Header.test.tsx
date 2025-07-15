import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import { Header } from '../Header';
import { useNavigation } from '@react-navigation/native';

// Mock react-navigation
jest.mock('@react-navigation/native', () => ({
  useNavigation: jest.fn(),
}));

// Mock react-native-vector-icons
jest.mock('react-native-vector-icons/MaterialCommunityIcons', () => 'Icon');

describe('Header', () => {
  const mockGoBack = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
    (useNavigation as jest.Mock).mockReturnValue({
      goBack: mockGoBack,
    });
  });

  it('renders with title', () => {
    const { getByText } = render(<Header title="Test Header" />);
    
    expect(getByText('Test Header')).toBeTruthy();
  });

  it('shows back button by default', () => {
    const { getByTestId } = render(
      <Header title="Test Header" />
    );
    
    const backButton = getByTestId('back-button');
    expect(backButton).toBeTruthy();
  });

  it('hides back button when showBack is false', () => {
    const { queryByTestId } = render(
      <Header title="Test Header" showBack={false} />
    );
    
    expect(queryByTestId('back-button')).toBeNull();
  });

  it('navigates back when back button is pressed', async () => {
    const { getByTestId } = render(<Header title="Test Header" />);
    
    const backButton = getByTestId('back-button');
    fireEvent.press(backButton);
    
    await waitFor(() => {
      expect(mockGoBack).toHaveBeenCalledTimes(1);
    });
  });

  it('renders action buttons', () => {
    const mockAction = jest.fn();
    const actions = [
      { icon: 'settings', onPress: mockAction },
      { icon: 'search', onPress: jest.fn() },
    ];
    
    const { getAllByTestId } = render(
      <Header title="Test Header" actions={actions} />
    );
    
    const actionButtons = getAllByTestId('action-button');
    expect(actionButtons).toHaveLength(2);
  });

  it('handles action button press', async () => {
    const mockAction = jest.fn();
    const actions = [{ icon: 'settings', onPress: mockAction }];
    
    const { getByTestId } = render(
      <Header title="Test Header" actions={actions} />
    );
    
    const actionButton = getByTestId('action-button');
    fireEvent.press(actionButton);
    
    await waitFor(() => {
      expect(mockAction).toHaveBeenCalledTimes(1);
    });
  });

  it('applies custom styles', () => {
    const customStyle = { paddingTop: 100 };
    const customTitleStyle = { fontSize: 20 };
    
    const { getByTestId } = render(
      <Header
        title="Test Header"
        style={customStyle}
        titleStyle={customTitleStyle}
      />
    );
    
    const container = getByTestId('header-container');
    expect(container.props.style).toContainEqual(customStyle);
  });

  it('sets custom colors', () => {
    const { getByTestId } = render(
      <Header
        title="Test Header"
        backgroundColor="#000000"
        textColor="#ffffff"
      />
    );
    
    const container = getByTestId('header-container');
    expect(container.props.style).toMatchObject({
      backgroundColor: '#000000',
    });
  });

  it('truncates long titles', () => {
    const longTitle = 'This is a very long title that should be truncated';
    const { getByText } = render(<Header title={longTitle} />);
    
    const titleElement = getByText(longTitle);
    expect(titleElement.props.numberOfLines).toBe(1);
  });

  it('applies elevation shadow styles', () => {
    const { getByTestId } = render(
      <Header title="Test Header" elevation={8} />
    );
    
    const container = getByTestId('header-container');
    expect(container.props.style).toMatchObject({
      elevation: 8,
      shadowOpacity: 0.4, // 8 * 0.05
      shadowRadius: 16, // 8 * 2
    });
  });

  it('renders action with custom color', () => {
    const actions = [
      { icon: 'star', onPress: jest.fn(), color: '#ff0000' },
    ];
    
    const { getByTestId } = render(
      <Header title="Test Header" actions={actions} />
    );
    
    const icon = getByTestId('action-icon');
    expect(icon.props.color).toBe('#ff0000');
  });
});