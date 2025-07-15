import React from 'react';
import { render } from '../../__tests__/utils/test-utils';
import { Loading } from '../Loading';

describe('Loading', () => {
  it('renders correctly with default props', () => {
    const { getByTestId, getByText } = render(<Loading />);
    
    expect(getByTestId('loading-container')).toBeTruthy();
    expect(getByTestId('loading-spinner')).toBeTruthy();
    expect(getByText('Loading...')).toBeTruthy();
  });

  it('renders with custom message', () => {
    const customMessage = 'Fetching your stories...';
    const { getByText } = render(<Loading message={customMessage} />);
    
    expect(getByText(customMessage)).toBeTruthy();
  });

  it('renders in fullscreen mode', () => {
    const { getByTestId } = render(<Loading fullscreen />);
    
    const container = getByTestId('loading-container');
    expect(container).toHaveStyle({
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
    });
  });

  it('renders with custom size', () => {
    const { getByTestId } = render(<Loading size="small" />);
    
    const spinner = getByTestId('loading-spinner');
    expect(spinner.props.size).toBe('small');
  });

  it('renders with custom color', () => {
    const customColor = '#FF6B6B';
    const { getByTestId } = render(<Loading color={customColor} />);
    
    const spinner = getByTestId('loading-spinner');
    expect(spinner.props.color).toBe(customColor);
  });

  it('hides message when showMessage is false', () => {
    const { queryByText } = render(<Loading showMessage={false} />);
    
    expect(queryByText('Loading...')).toBeNull();
  });

  it('applies custom styles', () => {
    const customStyle = { backgroundColor: 'rgba(0,0,0,0.8)' };
    const { getByTestId } = render(<Loading style={customStyle} />);
    
    const container = getByTestId('loading-container');
    expect(container).toHaveStyle(customStyle);
  });

  it('renders with overlay', () => {
    const { getByTestId } = render(<Loading overlay />);
    
    const overlay = getByTestId('loading-overlay');
    expect(overlay).toBeTruthy();
    expect(overlay).toHaveStyle({
      backgroundColor: 'rgba(0,0,0,0.5)',
    });
  });

  it('is accessible', () => {
    const { getByTestId } = render(<Loading />);
    
    const container = getByTestId('loading-container');
    expect(container.props.accessible).toBe(true);
    expect(container.props.accessibilityLabel).toBe('Loading');
    expect(container.props.accessibilityRole).toBe('progressbar');
  });
});