import { LocationData, locationService } from '../locationService'; // Import locationService
import { GameType, GameDifficulty } from './GameStateManager';
import { apiClient } from '../api/ApiClient'; // Import apiClient
import * as Location from 'expo-location'; // Keep for Accuracy enum if needed

export interface PointOfInterest {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  radius: number;  // in meters
  metadata?: any;
}

export interface TriggerConfig {
  pointOfInterestId: string;
  action: string;
  actionParams?: any;
  oneTime: boolean;
  triggered?: boolean; // Keep track of triggered status locally
  triggeredTimestamp?: number;
}

// Interface for the API response structure
interface LocationTriggersResponse {
    pointsOfInterest: PointOfInterest[];
    triggers: TriggerConfig[];
}


export interface TriggeredEvent {
  triggerId: string; // Use POI ID as trigger ID for simplicity? Or generate unique trigger IDs?
  pointOfInterestId: string;
  action: string;
  actionParams?: any;
  timestamp: number;
}

type TriggerCallback = (event: TriggeredEvent) => void;

/**
 * LocationBasedTriggers manages triggers that fire based on proximity to points of interest
 */
class LocationBasedTriggers {
  private pointsOfInterest: PointOfInterest[] = [];
  private triggers: TriggerConfig[] = [];
  private callbacks: TriggerCallback[] = [];
  private initialized: boolean = false;
  private isMonitoring: boolean = false;
  private currentLocation: LocationData | null = null;
  private locationWatchId: number | null = null; // Store ID for location watch
  private isLoading: boolean = false; // Prevent concurrent loads
  private lastLoadLocation: LocationData | null = null; // Track location of last load
  private loadRadius: number = 10000; // Default radius to load triggers (10km)

  /**
   * Initialize location-based triggers.
   * Ensures location service is initialized first.
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }
    console.log("Initializing LocationBasedTriggers...");
    // Ensure location service is ready and permissions are granted
    // Use the temporarily simulated location service
    const locationReady = await locationService.initialize();
    if (!locationReady) {
        console.warn("Location service failed to initialize or permissions denied. Cannot initialize triggers.");
        // Mark as initialized but without data/monitoring capability
        this.initialized = true;
        return;
    }

    // Initial load based on current location
    await this.loadTriggersForCurrentLocation();

    this.initialized = true;
    console.log("LocationBasedTriggers initialized.");
  }

  /**
   * Fetches triggers and POIs from the backend based on current location.
   */
  async loadTriggersForCurrentLocation(forceReload: boolean = false): Promise<void> {
      if (this.isLoading) {
          console.log("Trigger load already in progress.");
          return;
      }

      const currentLoc = await locationService.getCurrentLocation();
      if (!currentLoc) {
          console.warn("Cannot load triggers: Current location unknown.");
          return;
      }

      // Avoid reloading too frequently for the same area unless forced
      if (!forceReload && this.lastLoadLocation && locationService.calculateDistance(
          currentLoc.latitude, currentLoc.longitude,
          this.lastLoadLocation.latitude, this.lastLoadLocation.longitude
      ) < this.loadRadius / 2) { // e.g., don't reload if moved less than half the radius
          console.log("Skipping trigger reload: Still within the previous load radius.");
          return;
      }


      this.isLoading = true;
      console.log(`Loading triggers for location: ${currentLoc.latitude}, ${currentLoc.longitude}`);
      try {
          const params = {
              latitude: currentLoc.latitude,
              longitude: currentLoc.longitude,
              radius: this.loadRadius
          };
          const response: LocationTriggersResponse = await apiClient.get('/api/games/location-triggers', params);

          // Store fetched data (replace existing)
          this.pointsOfInterest = response.pointsOfInterest || [];
          // Important: Preserve triggered status for one-time triggers if they still exist in the new list
          const previousTriggers = new Map(this.triggers.map(t => [t.pointOfInterestId + t.action, t])); // Use a composite key
          this.triggers = (response.triggers || []).map(newTrigger => {
              const key = newTrigger.pointOfInterestId + newTrigger.action;
              const oldTrigger = previousTriggers.get(key);
              return {
                  ...newTrigger,
                  triggered: oldTrigger?.triggered ?? false, // Preserve status
                  triggeredTimestamp: oldTrigger?.triggeredTimestamp // Preserve timestamp
              };
          });

          this.lastLoadLocation = currentLoc; // Update location of last successful load
          console.log(`Loaded ${this.pointsOfInterest.length} POIs and ${this.triggers.length} triggers.`);

      } catch (error) {
          console.error("Error loading location triggers from API:", error);
          // Keep existing triggers on error? Or clear them? Decide based on desired behavior.
          // this.pointsOfInterest = [];
          // this.triggers = [];
      } finally {
          this.isLoading = false;
      }
  }


  /**
   * Start monitoring for location triggers.
   */
  async startMonitoring(): Promise<void> {
    if (!this.initialized) {
      console.warn('LocationBasedTriggers not initialized, initializing now...');
      await this.initialize();
      // If initialization failed or permissions denied, don't start monitoring
      if (!this.initialized || !locationService.hasPermission()) return;
    }
    if (this.isMonitoring) {
        console.log("Already monitoring location triggers.");
        return;
    }

    console.log("Starting location trigger monitoring...");
    // Start watching location updates via locationService
    // Use a higher frequency or lower distance interval for trigger checking if needed
    this.locationWatchId = await locationService.watchLocation(
        this.updateLocation.bind(this), // Call updateLocation when service gets update
        // Use numeric accuracy value if Location enum causes issues
        { accuracy: 3, distanceInterval: 50 } // Example: check every 50m
    );

    if (this.locationWatchId !== null && this.locationWatchId >= 0) {
        this.isMonitoring = true;
        console.log("Location trigger monitoring started.");
    } else {
         console.error("Failed to start location watch for triggers.");
         this.isMonitoring = false;
    }
  }

  /**
   * Stop monitoring for location triggers.
   */
  stopMonitoring(): void {
    if (!this.isMonitoring) return;

    console.log("Stopping location trigger monitoring...");
    if (this.locationWatchId !== null) {
        locationService.clearWatch(this.locationWatchId);
        this.locationWatchId = null;
    }
    this.isMonitoring = false;
    console.log("Location trigger monitoring stopped.");
  }

  // addCallback, removeCallback remain the same
   addCallback(callback: TriggerCallback): void { this.callbacks.push(callback); }
   removeCallback(callback: TriggerCallback): void {
       this.callbacks = this.callbacks.filter(cb => cb !== callback);
   }

  // Methods to manually add POIs/Triggers might be removed or kept for testing
  // addPointOfInterest(...)
  // removePointOfInterest(...)
  // addTrigger(...)
  // setupGameTrigger(...)

  /**
   * Update current location and check for triggers. Called by locationService watcher.
   */
  private updateLocation(location: LocationData): void {
    if (!this.isMonitoring) return; // Ensure we should be checking

    this.currentLocation = location;
    // console.log("Location update received for trigger check:", location.latitude, location.longitude); // Can be noisy

    // Potentially reload triggers if moved significantly far from last load point
    if (this.lastLoadLocation && locationService.calculateDistance(
        location.latitude, location.longitude,
        this.lastLoadLocation.latitude, this.lastLoadLocation.longitude
    ) > this.loadRadius) { // If moved outside load radius
        console.log("Moved significantly, reloading triggers...");
        this.loadTriggersForCurrentLocation(); // Async, runs in background
    }

    this.checkTriggers();
  }

  /**
   * Check if any triggers should fire based on current location.
   */
  private checkTriggers(): void {
    if (!this.currentLocation || this.pointsOfInterest.length === 0) {
      return;
    }

    // console.log(`Checking ${this.triggers.length} triggers against ${this.pointsOfInterest.length} POIs`);
    this.pointsOfInterest.forEach(poi => {
      const distance = locationService.calculateDistance( // Use locationService's method
        this.currentLocation!.latitude,
        this.currentLocation!.longitude,
        poi.latitude,
        poi.longitude
      );

      if (distance <= poi.radius) {
        // console.log(`Inside radius for POI: ${poi.name} (Dist: ${distance.toFixed(1)}m)`);
        const matchingTriggers = this.triggers.filter(
          trigger => trigger.pointOfInterestId === poi.id &&
                    (!trigger.oneTime || !trigger.triggered)
        );

        matchingTriggers.forEach(trigger => {
          console.log(`Firing trigger for POI ${poi.id}: Action=${trigger.action}`);
          // Mark as triggered *before* calling back
          trigger.triggered = true;
          trigger.triggeredTimestamp = Date.now();

          const event: TriggeredEvent = {
            triggerId: trigger.pointOfInterestId + "_" + trigger.action, // Create a more unique ID
            pointOfInterestId: poi.id,
            action: trigger.action,
            actionParams: trigger.actionParams,
            timestamp: Date.now()
          };

          // Notify callbacks
          this.callbacks.forEach(callback => {
            try {
              callback(event);
            } catch (error) {
              console.error('Error in trigger callback:', error);
            }
          });
        });
      }
    });
  }

  // calculateDistance can be removed as we use locationService's version
  // private calculateDistance(...)

  // --- Getters remain useful ---
  getPointsOfInterest(): PointOfInterest[] { return [...this.pointsOfInterest]; }
  getPointsOfInterestInRadius(location: LocationData, radius: number): PointOfInterest[] {
      return this.pointsOfInterest.filter(poi => {
          const distance = locationService.calculateDistance(
              location.latitude, location.longitude,
              poi.latitude, poi.longitude
          );
          return distance <= radius;
      });
  }
  getPointOfInterest(id: string): PointOfInterest | undefined { return this.pointsOfInterest.find(poi => poi.id === id); }
  resetOneTimeTriggers(): void {
      this.triggers.forEach(trigger => {
          if (trigger.oneTime) {
              trigger.triggered = false;
              trigger.triggeredTimestamp = undefined;
          }
      });
      console.log("Reset one-time triggers.");
  }
}

// Singleton instance
export const locationBasedTriggers = new LocationBasedTriggers();
export default locationBasedTriggers;
