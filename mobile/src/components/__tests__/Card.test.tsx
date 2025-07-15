import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Text, Platform, Dimensions } from 'react-native';
import { Card } from '../Card';
import { THEME } from '@/config';

describe('Card', () => {
  const mockOnPress = jest.fn();
  const mockAction = {
    icon: 'heart',
    onPress: jest.fn(),
    color: '#FF0000',
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Reset platform to iOS default
    Platform.OS = 'ios';
    // Reset dimensions to iPhone X
    Dimensions.set({ width: 375, height: 812 });
  });

  test('renders basic card with title and content', () => {
    const { getByText } = render(
      <Card
        title="Test Title"
        content="Test Content"
      />
    );

    expect(getByText('Test Title')).toBeTruthy();
    expect(getByText('Test Content')).toBeTruthy();
  });

  test('renders subtitle when provided', () => {
    const { getByText } = render(
      <Card
        title="Test Title"
        subtitle="Test Subtitle"
      />
    );

    expect(getByText('Test Subtitle')).toBeTruthy();
  });

  test('handles onPress event', () => {
    const { getByTestId } = render(
      <Card
        title="Test Title"
        onPress={mockOnPress}
      />
    );

    fireEvent.press(getByTestId('card-container'));
    expect(mockOnPress).toHaveBeenCalledTimes(1);
  });

  test('renders actions correctly', () => {
    const { getByTestId } = render(
      <Card
        title="Test Title"
        actions={[mockAction]}
      />
    );

    const actionButton = getByTestId('card-action-0');
    fireEvent.press(actionButton);
    expect(mockAction.onPress).toHaveBeenCalledTimes(1);
  });

  test('renders children when provided', () => {
    const { getByText } = render(
      <Card>
        <Text>Custom Child Content</Text>
      </Card>
    );

    expect(getByText('Custom Child Content')).toBeTruthy();
  });

  test('applies custom styles', () => {
    const customStyle = { marginTop: 20 };
    const customTitleStyle = { fontSize: 24 };
    const customSubtitleStyle = { color: 'red' };
    const customContentStyle = { lineHeight: 24 };

    const { getByTestId } = render(
      <Card
        title="Test Title"
        subtitle="Test Subtitle"
        content="Test Content"
        style={customStyle}
        titleStyle={customTitleStyle}
        subtitleStyle={customSubtitleStyle}
        contentStyle={customContentStyle}
      />
    );

    const container = getByTestId('card-container');
    const title = getByTestId('card-title');
    const subtitle = getByTestId('card-subtitle');
    const content = getByTestId('card-content');

    expect(container.props.style).toContainEqual(expect.objectContaining(customStyle));
    expect(title.props.style).toContainEqual(expect.objectContaining(customTitleStyle));
    expect(subtitle.props.style).toContainEqual(expect.objectContaining(customSubtitleStyle));
    expect(content.props.style).toContainEqual(expect.objectContaining(customContentStyle));
  });

  test('applies elevation correctly', () => {
    const { getByTestId } = render(
      <Card
        title="Test Title"
        elevation={4}
      />
    );

    const container = getByTestId('card-container');
    expect(container.props.style).toContainEqual(
      expect.objectContaining({
        elevation: 4,
        shadowOpacity: 0.2,
        shadowRadius: 8,
      })
    );
  });

  test('truncates text correctly', () => {
    const longTitle = 'A very long title that should be truncated at some point';
    const longContent = 'A very long content that should be truncated after three lines. '.repeat(5);

    const { getByTestId } = render(
      <Card
        title={longTitle}
        content={longContent}
      />
    );

    const title = getByTestId('card-title');
    const content = getByTestId('card-content');

    expect(title.props.numberOfLines).toBe(2);
    expect(content.props.numberOfLines).toBe(3);
  });

  test('renders multiple actions with correct colors', () => {
    const actions = [
      { icon: 'heart', onPress: jest.fn(), color: '#FF0000' },
      { icon: 'star', onPress: jest.fn(), color: '#FFD700' },
    ];

    const { getAllByTestId } = render(
      <Card
        title="Test Title"
        actions={actions}
      />
    );

    const actionIcons = getAllByTestId(/card-action-icon-/);
    expect(actionIcons).toHaveLength(2);
    expect(actionIcons[0].props.color).toBe('#FF0000');
    expect(actionIcons[1].props.color).toBe('#FFD700');
  });

  test('handles undefined optional props gracefully', () => {
    const { queryByTestId } = render(
      <Card />
    );

    expect(queryByTestId('card-title')).toBeNull();
    expect(queryByTestId('card-subtitle')).toBeNull();
    expect(queryByTestId('card-content')).toBeNull();
    expect(queryByTestId('card-actions')).toBeNull();
  });

  describe('Platform Specific Behavior', () => {
    test('applies correct shadow styles on iOS', () => {
      Platform.OS = 'ios';
      const { getByTestId } = render(
        <Card title="Test Title" elevation={4} />
      );

      const container = getByTestId('card-container');
      expect(container.props.style).toContainEqual(
        expect.objectContaining({
          shadowOpacity: 0.2,
          shadowRadius: 8,
        })
      );
    });

    test('applies correct elevation on Android', () => {
      Platform.OS = 'android';
      const { getByTestId } = render(
        <Card title="Test Title" elevation={4} />
      );

      const container = getByTestId('card-container');
      expect(container.props.style).toContainEqual(
        expect.objectContaining({
          elevation: 4,
        })
      );
    });
  });

  describe('Responsive Layout', () => {
    test('adapts to small screen size', () => {
      Dimensions.set({ width: 320, height: 568 }); // iPhone SE size
      const { getByTestId } = render(
        <Card
          title="Test Title"
          subtitle="Test Subtitle"
          content="Test Content"
        />
      );

      const title = getByTestId('card-title');
      const subtitle = getByTestId('card-subtitle');
      expect(title.props.numberOfLines).toBe(2);
      expect(subtitle.props.numberOfLines).toBe(1);
    });

    test('adapts to large screen size', () => {
      Dimensions.set({ width: 428, height: 926 }); // iPhone 12 Pro Max size
      const { getByTestId } = render(
        <Card
          title="Test Title"
          subtitle="Test Subtitle"
          content="Test Content"
        />
      );

      const container = getByTestId('card-container');
      expect(container.props.style).toContainEqual(
        expect.objectContaining({
          marginVertical: THEME.spacing.sm,
        })
      );
    });
  });

  describe('Accessibility', () => {
    test('provides correct accessibility props', () => {
      const { getByTestId } = render(
        <Card
          title="Test Title"
          content="Test Content"
          actions={[mockAction]}
        />
      );

      const container = getByTestId('card-container');
      const actionButton = getByTestId('card-action-0');

      expect(container.props.accessibilityRole).toBe('button');
      expect(actionButton.props.accessibilityRole).toBe('button');
      expect(actionButton.props.accessibilityLabel).toBe('heart action');
    });

    test('handles screen reader focus', () => {
      const { getByTestId } = render(
        <Card
          title="Test Title"
          content="Test Content"
          onPress={mockOnPress}
        />
      );

      const container = getByTestId('card-container');
      expect(container.props.accessible).toBe(true);
      expect(container.props.accessibilityHint).toBeTruthy();
    });
  });

  describe('Theme Context', () => {
    test('applies theme colors correctly', () => {
      const { getByTestId } = render(
        <Card
          title="Test Title"
          content="Test Content"
        />
      );

      const title = getByTestId('card-title');
      const content = getByTestId('card-content');

      expect(title.props.style).toContainEqual(
        expect.objectContaining({
          color: THEME.colors.text,
        })
      );
      expect(content.props.style).toContainEqual(
        expect.objectContaining({
          color: THEME.colors.text,
        })
      );
    });

    test('handles custom theme overrides', () => {
      const customTheme = {
        colors: {
          text: '#FF0000',
          primary: '#00FF00',
        },
      };

      const { getByTestId } = render(
        <Card
          title="Test Title"
          content="Test Content"
          titleStyle={{ color: customTheme.colors.text }}
          contentStyle={{ color: customTheme.colors.primary }}
        />
      );

      const title = getByTestId('card-title');
      const content = getByTestId('card-content');

      expect(title.props.style).toContainEqual(
        expect.objectContaining({
          color: customTheme.colors.text,
        })
      );
      expect(content.props.style).toContainEqual(
        expect.objectContaining({
          color: customTheme.colors.primary,
        })
      );
    });
  });

  describe('Error Handling', () => {
    test('handles undefined action handlers gracefully', () => {
      const { getByTestId } = render(
        <Card
          title="Test Title"
          actions={[{ ...mockAction, onPress: undefined }]}
        />
      );

      const actionButton = getByTestId('card-action-0');
      fireEvent.press(actionButton);
      // Should not throw
    });

    test('handles malformed content gracefully', () => {
      const { getByTestId } = render(
        <Card
          title={null as any}
          content={undefined as any}
          subtitle={0 as any}
        />
      );

      const container = getByTestId('card-container');
      expect(container).toBeTruthy();
      // Should render without crashing
    });
  });
}); 