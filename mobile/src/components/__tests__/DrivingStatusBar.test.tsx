import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import DrivingStatusBar from '../driving/DrivingStatusBar';
import { drivingAssistantService } from '@/services/drivingAssistantService';
import { locationService } from '@/services/locationService';
import { navigationService } from '@/services/navigation/navigationService';

// Mock dependencies
jest.mock('@/services/drivingAssistantService');
jest.mock('@/services/locationService');
jest.mock('@/services/navigation/navigationService');
jest.mock('@expo/vector-icons', () => ({
  MaterialIcons: 'Icon',
  MaterialCommunityIcons: 'Icon',
  FontAwesome5: 'Icon',
}));

describe('DrivingStatusBar', () => {
  const mockOnAlert = jest.fn();
  const mockOnPause = jest.fn();
  
  const mockDrivingStatus = {
    speed: 65, // mph
    speedLimit: 70,
    isMoving: true,
    isDriving: true,
    safetyScore: 92,
    currentManeuver: 'Continue straight',
    distanceToManeuver: 0.5, // miles
    estimatedArrival: new Date(Date.now() + 3600000), // 1 hour from now
    routeProgress: 0.45, // 45%
    hazards: [],
    fuelLevel: 0.75,
    batteryLevel: 0.85,
  };

  const mockLocation = {
    latitude: 37.7749,
    longitude: -122.4194,
    speed: 29.0576, // 65 mph in m/s
    heading: 45,
    accuracy: 10,
    timestamp: Date.now(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (drivingAssistantService.getDrivingStatus as jest.Mock).mockReturnValue(mockDrivingStatus);
    (locationService.getCurrentLocation as jest.Mock).mockResolvedValue(mockLocation);
    (navigationService.isNavigating as jest.Mock).mockReturnValue(true);
  });

  it('renders driving status information', () => {
    const { getByText, getByTestId } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    expect(getByText('65')).toBeTruthy();
    expect(getByText('mph')).toBeTruthy();
    expect(getByTestId('speedometer')).toBeTruthy();
    expect(getByTestId('safety-score')).toBeTruthy();
  });

  it('displays speed limit and warnings', () => {
    const { getByText, getByTestId } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    expect(getByText('70')).toBeTruthy(); // speed limit
    expect(getByTestId('speed-limit-sign')).toBeTruthy();
  });

  it('shows speeding warning when over limit', () => {
    (drivingAssistantService.getDrivingStatus as jest.Mock).mockReturnValue({
      ...mockDrivingStatus,
      speed: 75,
      speedLimit: 70,
    });
    
    const { getByTestId, getByText } = render(
      <DrivingStatusBar isVisible={true} onAlert={mockOnAlert} />
    );
    
    expect(getByTestId('speeding-warning')).toBeTruthy();
    expect(getByText(/Slow down/)).toBeTruthy();
    expect(mockOnAlert).toHaveBeenCalledWith('speeding', expect.any(Object));
  });

  it('displays navigation instructions', () => {
    const { getByText, getByTestId } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    expect(getByText('Continue straight')).toBeTruthy();
    expect(getByText('0.5 mi')).toBeTruthy();
    expect(getByTestId('navigation-arrow')).toBeTruthy();
  });

  it('shows route progress', () => {
    const { getByTestId } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    const progressBar = getByTestId('route-progress');
    expect(progressBar.props.style).toContainEqual(
      expect.objectContaining({ width: '45%' })
    );
  });

  it('displays estimated arrival time', () => {
    const { getByText } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    const arrivalTime = new Date(Date.now() + 3600000).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
    expect(getByText(`ETA: ${arrivalTime}`)).toBeTruthy();
  });

  it('shows safety score with color coding', () => {
    const { getByText, getByTestId } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    expect(getByText('92')).toBeTruthy();
    const scoreIndicator = getByTestId('safety-score');
    expect(scoreIndicator.props.style).toContainEqual(
      expect.objectContaining({ backgroundColor: expect.stringContaining('green') })
    );
  });

  it('displays hazard alerts', async () => {
    (drivingAssistantService.getDrivingStatus as jest.Mock).mockReturnValue({
      ...mockDrivingStatus,
      hazards: [
        { type: 'traffic', severity: 'moderate', distance: 0.3 },
        { type: 'weather', severity: 'low', message: 'Light rain ahead' },
      ],
    });
    
    const { getByText, getByTestId } = render(
      <DrivingStatusBar isVisible={true} onAlert={mockOnAlert} />
    );
    
    expect(getByTestId('hazard-alert')).toBeTruthy();
    expect(getByText(/Traffic ahead/)).toBeTruthy();
    expect(getByText(/Light rain ahead/)).toBeTruthy();
  });

  it('shows fuel/battery level', () => {
    const { getByTestId } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    const fuelGauge = getByTestId('fuel-gauge');
    expect(fuelGauge.props.style).toContainEqual(
      expect.objectContaining({ width: '75%' })
    );
  });

  it('handles pause driving mode', () => {
    const { getByTestId } = render(
      <DrivingStatusBar isVisible={true} onPause={mockOnPause} />
    );
    
    const pauseButton = getByTestId('pause-driving');
    fireEvent.press(pauseButton);
    
    expect(mockOnPause).toHaveBeenCalled();
  });

  it('collapses to minimal mode', async () => {
    const { getByTestId, queryByText } = render(
      <DrivingStatusBar isVisible={true} collapsible={true} />
    );
    
    const collapseButton = getByTestId('collapse-button');
    fireEvent.press(collapseButton);
    
    await waitFor(() => {
      expect(queryByText('Continue straight')).toBeNull();
      expect(getByTestId('minimal-status')).toBeTruthy();
    });
  });

  it('shows low fuel warning', () => {
    (drivingAssistantService.getDrivingStatus as jest.Mock).mockReturnValue({
      ...mockDrivingStatus,
      fuelLevel: 0.15,
    });
    
    const { getByText, getByTestId } = render(
      <DrivingStatusBar isVisible={true} onAlert={mockOnAlert} />
    );
    
    expect(getByTestId('low-fuel-warning')).toBeTruthy();
    expect(getByText(/Low fuel/)).toBeTruthy();
    expect(mockOnAlert).toHaveBeenCalledWith('low-fuel', expect.any(Object));
  });

  it('displays rest break reminder', () => {
    (drivingAssistantService.getDrivingStatus as jest.Mock).mockReturnValue({
      ...mockDrivingStatus,
      drivingDuration: 7200000, // 2 hours
      lastBreak: Date.now() - 7200000,
    });
    
    const { getByText } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    expect(getByText(/Time for a break/)).toBeTruthy();
  });

  it('shows traffic conditions', () => {
    (drivingAssistantService.getDrivingStatus as jest.Mock).mockReturnValue({
      ...mockDrivingStatus,
      trafficCondition: 'heavy',
      trafficDelay: 15, // minutes
    });
    
    const { getByText, getByTestId } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    expect(getByTestId('traffic-indicator')).toBeTruthy();
    expect(getByText(/Heavy traffic/)).toBeTruthy();
    expect(getByText(/+15 min/)).toBeTruthy();
  });

  it('handles night mode automatically', () => {
    const nightTime = new Date();
    nightTime.setHours(22); // 10 PM
    jest.spyOn(global, 'Date').mockImplementation(() => nightTime);
    
    const { getByTestId } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    expect(getByTestId('night-mode-indicator')).toBeTruthy();
  });

  it('displays lane guidance', () => {
    (drivingAssistantService.getDrivingStatus as jest.Mock).mockReturnValue({
      ...mockDrivingStatus,
      laneGuidance: {
        currentLane: 2,
        recommendedLane: 3,
        lanes: [
          { type: 'straight', active: false },
          { type: 'straight', active: true },
          { type: 'right', active: false, recommended: true },
        ],
      },
    });
    
    const { getByTestId } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    expect(getByTestId('lane-guidance')).toBeTruthy();
    expect(getByTestId('lane-2-active')).toBeTruthy();
    expect(getByTestId('lane-3-recommended')).toBeTruthy();
  });

  it('shows speed trend indicator', () => {
    (drivingAssistantService.getDrivingStatus as jest.Mock).mockReturnValue({
      ...mockDrivingStatus,
      speedTrend: 'increasing',
      acceleration: 2.5, // m/s²
    });
    
    const { getByTestId } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    expect(getByTestId('speed-trend-up')).toBeTruthy();
  });

  it('displays weather conditions', () => {
    (drivingAssistantService.getDrivingStatus as jest.Mock).mockReturnValue({
      ...mockDrivingStatus,
      weather: {
        condition: 'rainy',
        visibility: 'moderate',
        temperature: 68,
      },
    });
    
    const { getByTestId, getByText } = render(
      <DrivingStatusBar isVisible={true} />
    );
    
    expect(getByTestId('weather-icon-rainy')).toBeTruthy();
    expect(getByText('68°F')).toBeTruthy();
  });

  it('handles emergency stop detection', () => {
    const mockOnEmergency = jest.fn();
    
    (drivingAssistantService.getDrivingStatus as jest.Mock).mockReturnValue({
      ...mockDrivingStatus,
      emergencyStop: true,
      deceleration: -9.8, // m/s²
    });
    
    const { getByTestId } = render(
      <DrivingStatusBar 
        isVisible={true} 
        onEmergency={mockOnEmergency}
      />
    );
    
    expect(getByTestId('emergency-indicator')).toBeTruthy();
    expect(mockOnEmergency).toHaveBeenCalledWith('emergency-stop');
  });

  it('shows eco-driving score', () => {
    (drivingAssistantService.getDrivingStatus as jest.Mock).mockReturnValue({
      ...mockDrivingStatus,
      ecoScore: 85,
      fuelEfficiency: 32.5, // mpg
    });
    
    const { getByText, getByTestId } = render(
      <DrivingStatusBar isVisible={true} showEcoInfo={true} />
    );
    
    expect(getByTestId('eco-score')).toBeTruthy();
    expect(getByText('85')).toBeTruthy();
    expect(getByText('32.5 mpg')).toBeTruthy();
  });

  it('integrates with voice feedback', async () => {
    const { getByTestId } = render(
      <DrivingStatusBar 
        isVisible={true} 
        voiceEnabled={true}
      />
    );
    
    const voiceButton = getByTestId('voice-status-button');
    fireEvent.press(voiceButton);
    
    await waitFor(() => {
      expect(drivingAssistantService.speakStatus).toHaveBeenCalled();
    });
  });
});