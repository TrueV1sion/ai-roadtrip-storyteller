/**
 * Voice Assistant Service - MVP Version
 * Simplified interface for voice interactions with the backend
 */

import { API_CONFIG, buildApiUrl } from '../config/api';

import { logger } from '@/services/logger';
// Types
export interface VoiceCommandContext {
  location?: {
    latitude: number;
    longitude: number;
  } | null;
  routeInfo?: any;
  timestamp?: string;
}

export interface VoiceAssistantResponse {
  success: boolean;
  text?: string;
  audioUrl?: string;
  routeInfo?: {
    origin: { latitude: number; longitude: number };
    destination: { latitude: number; longitude: number };
    polylinePoints: Array<{ latitude: number; longitude: number }>;
    duration: number;
    distance: number;
  };
  error?: string;
}

class VoiceAssistantServiceMVP {
  private abortController: AbortController | null = null;

  /**
   * Process a voice command and get response from backend
   */
  async processVoiceCommand(
    userInput: string,
    context: VoiceCommandContext = {}
  ): Promise<VoiceAssistantResponse> {
    try {
      // Cancel any pending request
      if (this.abortController) {
        this.abortController.abort();
      }

      // Create new abort controller for this request
      this.abortController = new AbortController();

      // Prepare request body
      const requestBody = {
        user_input: userInput,
        context: {
          ...(context.location && {
            origin: `${context.location.latitude},${context.location.longitude}`,
            current_location: {
              lat: context.location.latitude,
              lng: context.location.longitude,
            },
          }),
          timestamp: new Date().toISOString(),
        },
      };

      // Make API request
      const response = await fetch(buildApiUrl(API_CONFIG.ENDPOINTS.VOICE_INTERACT), {
        method: 'POST',
        headers: {
          ...API_CONFIG.HEADERS,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
        signal: this.abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      const data = await response.json();

      // Transform response to our format
      return {
        success: true,
        text: data.text || data.message || 'I understood your request.',
        audioUrl: data.audio_url,
        routeInfo: this.extractRouteInfo(data),
      };
    } catch (error: any) {
      // Handle abort
      if (error.name === 'AbortError') {
        return {
          success: false,
          error: 'Request cancelled',
        };
      }

      logger.error('Voice assistant error:', error);
      return {
        success: false,
        error: error.message || 'Failed to process voice command',
        text: "I'm sorry, I couldn't process your request. Please try again.",
      };
    } finally {
      this.abortController = null;
    }
  }

  /**
   * Extract route information from API response
   */
  private extractRouteInfo(data: any): VoiceAssistantResponse['routeInfo'] | undefined {
    // Check for route information in various possible locations
    if (data.route || data.routeInfo || data.navigation) {
      const route = data.route || data.routeInfo || data.navigation;
      
      // Convert to our expected format
      if (route.origin && route.destination) {
        return {
          origin: {
            latitude: route.origin.lat || route.origin.latitude,
            longitude: route.origin.lng || route.origin.longitude,
          },
          destination: {
            latitude: route.destination.lat || route.destination.latitude,
            longitude: route.destination.lng || route.destination.longitude,
          },
          polylinePoints: this.decodePolyline(route.polyline) || [],
          duration: route.duration || 0,
          distance: route.distance || 0,
        };
      }
    }

    // Check if the response contains navigation intent
    if (data.actions) {
      const navAction = data.actions.find((a: any) => a.type === 'navigate');
      if (navAction && navAction.destination) {
        // We have navigation intent but need to fetch actual route
        // For MVP, we'll just return destination marker
        return {
          origin: { latitude: 0, longitude: 0 }, // Will be updated by current location
          destination: navAction.destination,
          polylinePoints: [],
          duration: 0,
          distance: 0,
        };
      }
    }

    return undefined;
  }

  /**
   * Decode Google polyline string to coordinates
   * This is a simplified version for MVP
   */
  private decodePolyline(encoded: string): Array<{ latitude: number; longitude: number }> {
    if (!encoded) return [];

    // For MVP, return empty array - the backend should provide decoded points
    // Full polyline decoding can be added in Phase 2
    return [];
  }

  /**
   * Cancel any pending requests
   */
  cancelPendingRequests() {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }
}

// Export singleton instance
export const voiceAssistantService = new VoiceAssistantServiceMVP();