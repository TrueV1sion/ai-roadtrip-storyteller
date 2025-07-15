import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import Button from '../Button';

describe('Button', () => {
  it('renders correctly', () => {
    const { getByText } = render(<Button title="Test Button" onPress={() => {}} />);
    expect(getByText('Test Button')).toBeTruthy();
  });

  it('calls onPress when pressed', () => {
    const onPressMock = jest.fn();
    const { getByText } = render(<Button title="Test Button" onPress={onPressMock} />);
    
    fireEvent.press(getByText('Test Button'));
    expect(onPressMock).toHaveBeenCalledTimes(1);
  });

  it('renders with primary variant by default', () => {
    const { getByTestId } = render(
      <Button title="Test Button" onPress={() => {}} testID="button" />
    );
    const button = getByTestId('button');
    expect(button.props.style).toBeTruthy();
  });

  it('renders with secondary variant', () => {
    const { getByTestId } = render(
      <Button title="Test Button" onPress={() => {}} variant="secondary" testID="button" />
    );
    const button = getByTestId('button');
    expect(button.props.style).toBeTruthy();
  });

  it('renders disabled state', () => {
    const onPressMock = jest.fn();
    const { getByTestId } = render(
      <Button title="Test Button" onPress={onPressMock} disabled testID="button" />
    );
    
    const button = getByTestId('button');
    fireEvent.press(button);
    expect(onPressMock).not.toHaveBeenCalled();
  });

  it('renders loading state', () => {
    const { getByTestId, queryByText } = render(
      <Button title="Test Button" onPress={() => {}} loading testID="button" />
    );
    
    expect(queryByText('Test Button')).toBeFalsy();
    expect(getByTestId('button')).toBeTruthy();
  });

  it('renders with custom style', () => {
    const customStyle = { backgroundColor: 'red' };
    const { getByTestId } = render(
      <Button title="Test Button" onPress={() => {}} style={customStyle} testID="button" />
    );
    
    const button = getByTestId('button');
    expect(button.props.style).toMatchObject(customStyle);
  });

  it('renders with icon', () => {
    const { getByTestId } = render(
      <Button title="Test Button" onPress={() => {}} icon="check" testID="button" />
    );
    
    expect(getByTestId('button')).toBeTruthy();
  });
});