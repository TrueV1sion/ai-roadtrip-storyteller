import { api } from './api/ApiClient';

export type RideshareMode = 'driver' | 'passenger' | 'none';

export interface DriverStats {
  total_earnings: number;
  trips_completed: number;
  hourly_rate: number;
  session_duration?: number;
}

export interface QuickAction {
  id: string;
  label: string;
  icon: string;
  voice_command: string;
  priority: number;
}

export interface EntertainmentOption {
  id: string;
  name: string;
  type: 'game' | 'story' | 'music';
  duration: string;
  description: string;
}

export interface TripData {
  trip_id: string;
  earnings: number;
  distance: number;
  duration: number;
  pickup_location: { lat: number; lng: number };
  dropoff_location: { lat: number; lng: number };
}

class RideshareService {
  /**
   * Set the current rideshare mode
   */
  async setMode(mode: RideshareMode, preferences?: any) {
    if (mode === 'none') {
      return api.delete('/rideshare/mode');
    }
    
    return api.post('/rideshare/mode', {
      mode,
      preferences: preferences || {}
    });
  }

  /**
   * Get the current rideshare mode
   */
  async getCurrentMode(): Promise<{ mode: RideshareMode; active: boolean }> {
    const response = await api.get('/rideshare/mode');
    return response.data;
  }

  /**
   * Driver-specific methods
   */
  async getDriverQuickActions(location: { lat: number; lng: number }): Promise<QuickAction[]> {
    const response = await api.get('/rideshare/driver/quick-actions', {
      params: location
    });
    return response.data;
  }

  async executeQuickAction(actionId: string, location?: { lat: number; lng: number }) {
    return api.post('/rideshare/driver/quick-action', {
      action_id: actionId,
      location: location || null
    });
  }

  async getDriverStats(period: string = 'today'): Promise<DriverStats> {
    const response = await api.get('/rideshare/driver/stats', {
      params: { period }
    });
    return response.data;
  }

  async recordTrip(tripData: TripData): Promise<DriverStats> {
    const response = await api.post('/rideshare/driver/trip', tripData);
    return response.data;
  }

  async getOptimalRoutes(location: { lat: number; lng: number }) {
    const response = await api.get('/rideshare/driver/optimal-routes', {
      params: location
    });
    return response.data;
  }

  /**
   * Passenger-specific methods
   */
  async getEntertainmentOptions(maxDuration?: number) {
    const response = await api.post('/rideshare/passenger/entertainment', {
      max_duration: maxDuration
    });
    return response.data;
  }

  /**
   * Voice command processing
   */
  async processVoiceCommand(
    voiceInput: string,
    mode: RideshareMode,
    context?: any
  ) {
    return api.post('/rideshare/voice/command', {
      voice_input: voiceInput,
      mode,
      context: context || {},
      location: context?.location,
      vehicle_speed: context?.vehicle_speed || 0,
      is_moving: context?.is_moving || false
    });
  }

  /**
   * Get voice prompts for the current mode
   */
  async getVoicePrompts(mode: RideshareMode) {
    const response = await api.get('/rideshare/voice/prompts', {
      params: { mode }
    });
    return response.data;
  }

  /**
   * Location-based services
   */
  async findNearbyGasStations(location: { lat: number; lng: number }) {
    return this.executeQuickAction('find_gas', location);
  }

  async findQuickFood(location: { lat: number; lng: number }) {
    return this.executeQuickAction('quick_food', location);
  }

  async findBreakSpots(location: { lat: number; lng: number }) {
    return this.executeQuickAction('take_break', location);
  }

  /**
   * Entertainment services
   */
  async startTrivia() {
    return this.processVoiceCommand('play trivia', 'passenger');
  }

  async getLocalFacts(location: { lat: number; lng: number }) {
    return this.processVoiceCommand('tell me about this area', 'passenger', {
      location
    });
  }

  /**
   * Analytics and tracking
   */
  async getEarningsReport(period: 'today' | 'week' | 'month') {
    const response = await api.get('/rideshare/driver/earnings-report', {
      params: { period }
    });
    return response.data;
  }

  /**
   * Safety features
   */
  async checkCommandSafety(
    command: string,
    vehicleSpeed: number,
    isMoving: boolean
  ): Promise<boolean> {
    // Client-side safety check
    if (vehicleSpeed > 5 || isMoving) {
      // Only allow very simple commands while moving
      const safeCommands = ['pause', 'stop', 'help', 'emergency'];
      return safeCommands.some(safe => command.toLowerCase().includes(safe));
    }
    return true;
  }

  /**
   * Mock trip simulation for testing
   */
  async simulateTrip(duration: number = 15): Promise<TripData> {
    // Simulate a trip for demo purposes
    const baseEarnings = 8.50;
    const perMinute = 0.60;
    const perMile = 0.90;
    
    const distance = duration * 0.5; // Avg 30mph
    const earnings = baseEarnings + (duration * perMinute) + (distance * perMile);
    
    return {
      trip_id: `TRIP-${Date.now()}`,
      earnings: parseFloat(earnings.toFixed(2)),
      distance: parseFloat(distance.toFixed(1)),
      duration,
      pickup_location: { lat: 37.7749, lng: -122.4194 },
      dropoff_location: { lat: 37.7849, lng: -122.4094 }
    };
  }
}

export const rideshareService = new RideshareService();