import { renderHook, act } from '@testing-library/react-native';
import useLocation from '../useLocation';
import * as Location from 'expo-location';

jest.mock('expo-location');

describe('useLocation', () => {
  const mockLocation = {
    coords: {
      latitude: 40.7128,
      longitude: -74.0060,
      altitude: 0,
      accuracy: 5,
      altitudeAccuracy: 5,
      heading: 0,
      speed: 0,
    },
    timestamp: Date.now(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('requests permissions on mount', async () => {
    (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValueOnce({ 
      status: 'granted' 
    });
    
    const { result } = renderHook(() => useLocation());
    
    expect(Location.requestForegroundPermissionsAsync).toHaveBeenCalled();
    expect(result.current.permissionGranted).toBe(false); // Initially false
    
    // Wait for permission update
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
    
    expect(result.current.permissionGranted).toBe(true);
  });

  it('handles permission denial', async () => {
    (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValueOnce({ 
      status: 'denied' 
    });
    
    const { result } = renderHook(() => useLocation());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
    
    expect(result.current.permissionGranted).toBe(false);
    expect(result.current.error).toBe('Location permission denied');
  });

  it('gets current location after permission granted', async () => {
    (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValueOnce({ 
      status: 'granted' 
    });
    (Location.getCurrentPositionAsync as jest.Mock).mockResolvedValueOnce(mockLocation);
    
    const { result } = renderHook(() => useLocation());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
    
    expect(result.current.location).toEqual(mockLocation);
    expect(result.current.loading).toBe(false);
  });

  it('watches position updates when enabled', async () => {
    const mockRemove = jest.fn();
    (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValueOnce({ 
      status: 'granted' 
    });
    (Location.getCurrentPositionAsync as jest.Mock).mockResolvedValueOnce(mockLocation);
    (Location.watchPositionAsync as jest.Mock).mockImplementation((options, callback) => {
      // Simulate position update
      setTimeout(() => {
        callback({
          ...mockLocation,
          coords: { ...mockLocation.coords, latitude: 40.7130 }
        });
      }, 100);
      
      return Promise.resolve({ remove: mockRemove });
    });
    
    const { result } = renderHook(() => useLocation({ enableHighAccuracy: true }));
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 150));
    });
    
    expect(Location.watchPositionAsync).toHaveBeenCalledWith(
      expect.objectContaining({
        accuracy: Location.Accuracy.High,
        timeInterval: 1000,
        distanceInterval: 10,
      }),
      expect.any(Function)
    );
    
    expect(result.current.location?.coords.latitude).toBe(40.7130);
  });

  it('refreshes location on demand', async () => {
    (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValueOnce({ 
      status: 'granted' 
    });
    (Location.getCurrentPositionAsync as jest.Mock)
      .mockResolvedValueOnce(mockLocation)
      .mockResolvedValueOnce({
        ...mockLocation,
        coords: { ...mockLocation.coords, latitude: 40.7129 }
      });
    
    const { result } = renderHook(() => useLocation());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
    
    expect(result.current.location?.coords.latitude).toBe(40.7128);
    
    // Refresh location
    await act(async () => {
      await result.current.refreshLocation();
    });
    
    expect(result.current.location?.coords.latitude).toBe(40.7129);
  });

  it('handles location service errors', async () => {
    (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValueOnce({ 
      status: 'granted' 
    });
    (Location.getCurrentPositionAsync as jest.Mock).mockRejectedValueOnce(
      new Error('Location services disabled')
    );
    
    const { result } = renderHook(() => useLocation());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
    
    expect(result.current.error).toBe('Location services disabled');
    expect(result.current.location).toBeNull();
  });

  it('cleans up position watcher on unmount', async () => {
    const mockRemove = jest.fn();
    (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValueOnce({ 
      status: 'granted' 
    });
    (Location.watchPositionAsync as jest.Mock).mockResolvedValueOnce({ 
      remove: mockRemove 
    });
    
    const { unmount } = renderHook(() => useLocation({ enableHighAccuracy: true }));
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
    
    unmount();
    
    expect(mockRemove).toHaveBeenCalled();
  });

  it('respects skipPermissionRequest option', async () => {
    const { result } = renderHook(() => useLocation({ skipPermissionRequest: true }));
    
    expect(Location.requestForegroundPermissionsAsync).not.toHaveBeenCalled();
    expect(result.current.permissionGranted).toBe(false);
  });

  it('calculates distance between locations', async () => {
    (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValueOnce({ 
      status: 'granted' 
    });
    (Location.getCurrentPositionAsync as jest.Mock).mockResolvedValueOnce(mockLocation);
    
    const { result } = renderHook(() => useLocation());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 0));
    });
    
    const distance = result.current.getDistanceFrom({
      latitude: 40.7580,
      longitude: -73.9855
    });
    
    // Should calculate distance in kilometers
    expect(distance).toBeGreaterThan(0);
    expect(distance).toBeLessThan(10); // Manhattan distance
  });
});