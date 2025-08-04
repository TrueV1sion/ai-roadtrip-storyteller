/**
 * Voice Safety Service
 * 
 * Manages safety validation and monitoring for voice interactions
 * while driving. Ensures compliance with hands-free regulations
 * and minimizes driver distraction.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

import { logger } from '@/services/logger';
export enum SafetyLevel {
  PARKED = 'parked',
  LOW_SPEED = 'low_speed',
  MODERATE = 'moderate',
  HIGHWAY = 'highway',
  CRITICAL = 'critical'
}

export interface SafetyContext {
  speed: number; // mph
  isNavigating: boolean;
  trafficCondition: 'light' | 'normal' | 'heavy';
  weatherCondition: 'clear' | 'rain' | 'snow' | 'fog';
  upcomingManeuver?: string;
  maneuverDistance?: number; // miles
}

export interface CommandValidation {
  isAllowed: boolean;
  reason?: string;
  warnings: string[];
  requiresConfirmation?: boolean;
  alternativeCommand?: string;
}

export interface SafetyEvent {
  type: 'command_blocked' | 'emergency_stop' | 'auto_pause' | 'safety_violation';
  timestamp: Date;
  command?: string;
  reason: string;
  safetyLevel: SafetyLevel;
  context?: any;
}

export interface InteractionMetrics {
  command: string;
  duration: number; // ms
  safetyLevel: SafetyLevel;
  completed: boolean;
  errors?: number;
}

interface SafetyThresholds {
  maxInteractionDuration: { [key in SafetyLevel]: number };
  maxInteractionsPerMinute: number;
  criticalManeuverDistance: number; // miles
  complexityByLevel: { [key in SafetyLevel]: string[] };
}

class VoiceSafetyService {
  private currentContext: SafetyContext | null = null;
  private currentSafetyLevel: SafetyLevel = SafetyLevel.PARKED;
  private safetyEvents: SafetyEvent[] = [];
  private interactionHistory: InteractionMetrics[] = [];
  private lastInteractionTime: Date | null = null;
  private emergencyStopActive = false;
  
  // Safety thresholds
  private thresholds: SafetyThresholds = {
    maxInteractionDuration: {
      [SafetyLevel.PARKED]: 60000, // 60s
      [SafetyLevel.LOW_SPEED]: 10000, // 10s
      [SafetyLevel.MODERATE]: 5000, // 5s
      [SafetyLevel.HIGHWAY]: 3000, // 3s
      [SafetyLevel.CRITICAL]: 0 // Not allowed
    },
    maxInteractionsPerMinute: 3,
    criticalManeuverDistance: 0.25, // miles
    complexityByLevel: {
      [SafetyLevel.PARKED]: ['all'], // All commands allowed
      [SafetyLevel.LOW_SPEED]: ['simple', 'moderate'],
      [SafetyLevel.MODERATE]: ['simple'],
      [SafetyLevel.HIGHWAY]: ['simple', 'emergency'],
      [SafetyLevel.CRITICAL]: ['emergency'] // Only emergency commands
    }
  };

  // Command complexity mapping
  private commandComplexity: { [command: string]: 'simple' | 'moderate' | 'complex' | 'emergency' } = {
    // Emergency commands
    'stop': 'emergency',
    'pause': 'emergency',
    'quiet': 'emergency',
    'emergency': 'emergency',
    'help': 'emergency',
    'cancel': 'emergency',
    
    // Simple commands
    'yes': 'simple',
    'no': 'simple',
    'next': 'simple',
    'previous': 'simple',
    'louder': 'simple',
    'quieter': 'simple',
    'repeat': 'simple',
    'play': 'simple',
    'resume': 'simple',
    
    // Moderate commands
    'skip': 'moderate',
    'volume': 'moderate',
    'music': 'moderate',
    
    // Complex commands
    'navigate': 'complex',
    'book': 'complex',
    'reserve': 'complex',
    'topic': 'complex',
    'search': 'complex',
    'find': 'complex'
  };

  constructor() {
    this.loadSafetyHistory();
  }

  /**
   * Update the current driving context
   */
  updateContext(context: SafetyContext): void {
    this.currentContext = context;
    this.currentSafetyLevel = this.calculateSafetyLevel(context);
    
    // Check for critical conditions
    if (context.upcomingManeuver && context.maneuverDistance) {
      if (context.maneuverDistance < this.thresholds.criticalManeuverDistance) {
        this.currentSafetyLevel = SafetyLevel.CRITICAL;
      }
    }
  }

  /**
   * Validate if a command can be executed safely
   */
  async validateCommand(command: string, isDriving: boolean): Promise<CommandValidation> {
    // Emergency stop override
    if (this.emergencyStopActive && !this.isEmergencyCommand(command)) {
      return {
        isAllowed: false,
        reason: 'Emergency stop active',
        warnings: []
      };
    }

    // Always allow emergency commands
    if (this.isEmergencyCommand(command)) {
      return {
        isAllowed: true,
        warnings: []
      };
    }

    // Not driving - all commands allowed
    if (!isDriving || this.currentSafetyLevel === SafetyLevel.PARKED) {
      return {
        isAllowed: true,
        warnings: []
      };
    }

    const warnings: string[] = [];
    
    // Check command complexity
    const complexity = this.getCommandComplexity(command);
    const allowedComplexity = this.thresholds.complexityByLevel[this.currentSafetyLevel];
    
    if (!allowedComplexity.includes('all') && !allowedComplexity.includes(complexity)) {
      return {
        isAllowed: false,
        reason: `${complexity} commands not allowed at ${this.currentSafetyLevel} speed`,
        warnings,
        alternativeCommand: this.suggestAlternative(command)
      };
    }

    // Check interaction frequency
    const recentInteractions = this.getRecentInteractions(60); // Last minute
    if (recentInteractions.length >= this.thresholds.maxInteractionsPerMinute) {
      warnings.push('High interaction frequency');
      
      if (this.currentSafetyLevel !== SafetyLevel.LOW_SPEED) {
        return {
          isAllowed: false,
          reason: 'Too many recent voice commands',
          warnings
        };
      }
    }

    // Check for critical maneuvers
    if (this.currentContext?.upcomingManeuver) {
      const distance = this.currentContext.maneuverDistance || 0;
      if (distance < this.thresholds.criticalManeuverDistance) {
        return {
          isAllowed: false,
          reason: 'Critical maneuver approaching',
          warnings
        };
      } else if (distance < 0.5) {
        warnings.push('Maneuver approaching');
      }
    }

    // Weather conditions
    if (this.currentContext?.weatherCondition !== 'clear') {
      warnings.push(`Caution: ${this.currentContext.weatherCondition} conditions`);
      
      // Restrict complex commands in bad weather
      if (complexity === 'complex' && this.currentSafetyLevel === SafetyLevel.HIGHWAY) {
        return {
          isAllowed: false,
          reason: 'Complex commands restricted in poor weather at high speed',
          warnings
        };
      }
    }

    // Navigation commands require confirmation while driving
    if (command === 'navigate' && this.currentSafetyLevel !== SafetyLevel.LOW_SPEED) {
      return {
        isAllowed: true,
        warnings,
        requiresConfirmation: true
      };
    }

    return {
      isAllowed: true,
      warnings
    };
  }

  /**
   * Check if auto-pause should be activated
   */
  shouldAutoPause(): { shouldPause: boolean; reason?: string } {
    if (!this.currentContext) {
      return { shouldPause: false };
    }

    // Critical safety level
    if (this.currentSafetyLevel === SafetyLevel.CRITICAL) {
      return {
        shouldPause: true,
        reason: 'Critical driving conditions'
      };
    }

    // Upcoming critical maneuver
    if (this.currentContext.upcomingManeuver && 
        this.currentContext.maneuverDistance && 
        this.currentContext.maneuverDistance < 0.1) {
      return {
        shouldPause: true,
        reason: 'Maneuver imminent'
      };
    }

    // Heavy traffic at high speed
    if (this.currentContext.trafficCondition === 'heavy' && 
        this.currentSafetyLevel === SafetyLevel.HIGHWAY) {
      return {
        shouldPause: true,
        reason: 'Heavy traffic at high speed'
      };
    }

    return { shouldPause: false };
  }

  /**
   * Get available commands for current safety level
   */
  getAvailableCommands(isDriving: boolean): string[] {
    if (!isDriving || this.currentSafetyLevel === SafetyLevel.PARKED) {
      return Object.keys(this.commandComplexity);
    }

    const allowedComplexity = this.thresholds.complexityByLevel[this.currentSafetyLevel];
    
    return Object.entries(this.commandComplexity)
      .filter(([_, complexity]) => 
        allowedComplexity.includes('all') || 
        allowedComplexity.includes(complexity) ||
        complexity === 'emergency'
      )
      .map(([command]) => command);
  }

  /**
   * Record a safety event
   */
  logSafetyEvent(event: Omit<SafetyEvent, 'timestamp'>): void {
    const fullEvent: SafetyEvent = {
      ...event,
      timestamp: new Date()
    };
    
    this.safetyEvents.push(fullEvent);
    
    // Keep only last 100 events
    if (this.safetyEvents.length > 100) {
      this.safetyEvents = this.safetyEvents.slice(-100);
    }
    
    // Persist events
    this.saveSafetyHistory();
    
    // Log critical events
    if (event.type === 'emergency_stop' || event.type === 'safety_violation') {
      logger.warn('Safety event:', event);
    }
  }

  /**
   * Record interaction metrics
   */
  recordInteraction(metrics: InteractionMetrics): void {
    this.interactionHistory.push(metrics);
    this.lastInteractionTime = new Date();
    
    // Keep only last hour of history
    const oneHourAgo = new Date(Date.now() - 3600000);
    this.interactionHistory = this.interactionHistory.filter(
      m => new Date().getTime() - oneHourAgo.getTime() < 3600000
    );
  }

  /**
   * Activate emergency stop
   */
  activateEmergencyStop(): void {
    this.emergencyStopActive = true;
    this.logSafetyEvent({
      type: 'emergency_stop',
      reason: 'Manual activation',
      safetyLevel: this.currentSafetyLevel
    });
    
    // Auto-clear after 30 seconds
    setTimeout(() => {
      this.emergencyStopActive = false;
    }, 30000);
  }

  /**
   * Get current safety level
   */
  getCurrentSafetyLevel(): SafetyLevel {
    return this.currentSafetyLevel;
  }

  /**
   * Get safety metrics for reporting
   */
  getSafetyMetrics(): {
    recentEvents: SafetyEvent[];
    interactionCount: number;
    averageInteractionDuration: number;
    safetyScore: number;
  } {
    const recentEvents = this.safetyEvents.slice(-10);
    const recentInteractions = this.getRecentInteractions(300); // Last 5 minutes
    
    const avgDuration = recentInteractions.length > 0
      ? recentInteractions.reduce((sum, i) => sum + i.duration, 0) / recentInteractions.length
      : 0;
    
    // Calculate safety score (0-100)
    let safetyScore = 100;
    
    // Deduct for violations
    const violations = recentEvents.filter(e => e.type === 'safety_violation').length;
    safetyScore -= violations * 10;
    
    // Deduct for emergency stops
    const emergencyStops = recentEvents.filter(e => e.type === 'emergency_stop').length;
    safetyScore -= emergencyStops * 5;
    
    // Deduct for high interaction frequency
    if (recentInteractions.length > 15) { // More than 3 per minute average
      safetyScore -= 10;
    }
    
    return {
      recentEvents,
      interactionCount: recentInteractions.length,
      averageInteractionDuration: avgDuration,
      safetyScore: Math.max(0, safetyScore)
    };
  }

  // Private methods

  private calculateSafetyLevel(context: SafetyContext): SafetyLevel {
    const { speed } = context;
    
    if (speed === 0) return SafetyLevel.PARKED;
    if (speed < 25) return SafetyLevel.LOW_SPEED;
    if (speed < 55) return SafetyLevel.MODERATE;
    return SafetyLevel.HIGHWAY;
  }

  private getCommandComplexity(command: string): 'simple' | 'moderate' | 'complex' | 'emergency' {
    const lowerCommand = command.toLowerCase();
    
    // Check exact matches first
    if (this.commandComplexity[lowerCommand]) {
      return this.commandComplexity[lowerCommand];
    }
    
    // Check partial matches
    for (const [key, complexity] of Object.entries(this.commandComplexity)) {
      if (lowerCommand.includes(key)) {
        return complexity;
      }
    }
    
    // Default to moderate
    return 'moderate';
  }

  private isEmergencyCommand(command: string): boolean {
    const emergencyCommands = ['stop', 'pause', 'quiet', 'emergency', 'help', 'cancel'];
    return emergencyCommands.includes(command.toLowerCase());
  }

  private suggestAlternative(command: string): string | undefined {
    const alternatives: { [key: string]: string } = {
      'navigate': 'Say "navigate" when stopped',
      'book': 'Booking available when parked',
      'topic': 'Topic selection available at lower speeds',
      'search': 'Search when stopped'
    };
    
    return alternatives[command.toLowerCase()];
  }

  private getRecentInteractions(seconds: number): InteractionMetrics[] {
    const cutoff = Date.now() - (seconds * 1000);
    return this.interactionHistory.filter(() => {
      // Since we don't store timestamp in metrics, use array order
      // In production, add timestamp to InteractionMetrics
      return true; // Simplified for now
    });
  }

  private async loadSafetyHistory(): Promise<void> {
    try {
      const events = await AsyncStorage.getItem('voiceSafetyEvents');
      if (events) {
        this.safetyEvents = JSON.parse(events);
      }
    } catch (error) {
      logger.error('Failed to load safety history:', error);
    }
  }

  private async saveSafetyHistory(): Promise<void> {
    try {
      await AsyncStorage.setItem('voiceSafetyEvents', JSON.stringify(this.safetyEvents));
    } catch (error) {
      logger.error('Failed to save safety history:', error);
    }
  }
}

// Export singleton instance
export const voiceSafetyService = new VoiceSafetyService();