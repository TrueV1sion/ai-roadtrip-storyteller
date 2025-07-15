/**
 * AR Camera Service
 * Manages camera access and AR session lifecycle for the road trip app
 */

import {
  Camera,
  CameraDevice,
  CameraPermissionStatus,
  useCameraDevice,
  useCameraPermission,
  Frame,
  FrameProcessorPerformanceSuggestion,
} from 'react-native-vision-camera';
import { runOnJS, runOnUI } from 'react-native-reanimated';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { arService } from '../arService';
import { performanceMonitor } from '../performanceMonitor';

interface ARSessionConfig {
  quality: 'low' | 'medium' | 'high';
  targetFPS: 30 | 60;
  enableLandmarkDetection: boolean;
  enablePhotoCapture: boolean;
  enableGames: boolean;
  batteryMode: 'normal' | 'saving';
}

interface ARPerformanceMetrics {
  fps: number;
  frameDrops: number;
  processingTime: number;
  batteryDrain: number;
  temperature: number;
}

export class ARCameraService {
  private static instance: ARCameraService;
  private camera: Camera | null = null;
  private device: CameraDevice | null = null;
  private sessionConfig: ARSessionConfig;
  private isSessionActive: boolean = false;
  private performanceMetrics: ARPerformanceMetrics;
  private frameSkipCounter: number = 0;
  private lastFrameTime: number = 0;
  
  // Performance thresholds
  private readonly MAX_PROCESSING_TIME_MS = 33; // For 30 FPS
  private readonly BATTERY_SAVING_THRESHOLD = 20; // Battery percentage
  private readonly THERMAL_THROTTLE_TEMP = 45; // Celsius
  
  private constructor() {
    this.sessionConfig = {
      quality: 'medium',
      targetFPS: 30,
      enableLandmarkDetection: true,
      enablePhotoCapture: true,
      enableGames: true,
      batteryMode: 'normal',
    };
    
    this.performanceMetrics = {
      fps: 0,
      frameDrops: 0,
      processingTime: 0,
      batteryDrain: 0,
      temperature: 0,
    };
  }
  
  static getInstance(): ARCameraService {
    if (!ARCameraService.instance) {
      ARCameraService.instance = new ARCameraService();
    }
    return ARCameraService.instance;
  }
  
  /**
   * Initialize AR camera with safety checks
   */
  async initialize(): Promise<boolean> {
    try {
      // Check AR support
      const isSupported = await this.checkARSupport();
      if (!isSupported) {
        console.warn('AR not supported on this device');
        return false;
      }
      
      // Check permissions
      const hasPermission = await this.checkPermissions();
      if (!hasPermission) {
        console.warn('Camera permission not granted');
        return false;
      }
      
      // Get camera device
      this.device = await this.getOptimalCameraDevice();
      if (!this.device) {
        console.warn('No suitable camera device found');
        return false;
      }
      
      // Load saved preferences
      await this.loadUserPreferences();
      
      // Start performance monitoring
      this.startPerformanceMonitoring();
      
      return true;
    } catch (error) {
      console.error('AR initialization failed:', error);
      return false;
    }
  }
  
  /**
   * Check if device supports AR
   */
  private async checkARSupport(): Promise<boolean> {
    // Check platform
    if (Platform.OS === 'web') {
      return false;
    }
    
    // Check AR capabilities
    const hasARSupport = await arService.isARSupported();
    
    // Check minimum OS version
    const osVersion = Platform.Version;
    const minVersion = Platform.OS === 'ios' ? 11 : 24; // iOS 11+, Android 7.0+
    
    if (typeof osVersion === 'number' && osVersion < minVersion) {
      return false;
    }
    
    return hasARSupport;
  }
  
  /**
   * Check and request camera permissions
   */
  private async checkPermissions(): Promise<boolean> {
    const { hasPermission, requestPermission } = useCameraPermission();
    
    if (hasPermission) {
      return true;
    }
    
    const status = await requestPermission();
    return status === 'granted';
  }
  
  /**
   * Get optimal camera device based on capabilities
   */
  private async getOptimalCameraDevice(): Promise<CameraDevice | null> {
    const devices = await Camera.getAvailableCameraDevices();
    
    // Prefer back camera with wide angle
    const backCamera = devices.find(
      (d) => d.position === 'back' && d.hasWideAngleCamera
    );
    
    if (backCamera) {
      return backCamera;
    }
    
    // Fallback to any back camera
    return devices.find((d) => d.position === 'back') || null;
  }
  
  /**
   * Start AR session with configuration
   */
  async startSession(config?: Partial<ARSessionConfig>): Promise<void> {
    if (this.isSessionActive) {
      console.warn('AR session already active');
      return;
    }
    
    // Merge with existing config
    this.sessionConfig = { ...this.sessionConfig, ...config };
    
    // Apply battery saving mode if needed
    const batteryLevel = await this.getBatteryLevel();
    if (batteryLevel < this.BATTERY_SAVING_THRESHOLD) {
      this.enableBatterySavingMode();
    }
    
    // Configure camera format
    const format = this.getOptimalFormat();
    
    // Start AR tracking
    await arService.startTracking();
    
    this.isSessionActive = true;
    
    // Log session start
    performanceMonitor.logEvent('ar_session_started', {
      config: this.sessionConfig,
      device: this.device?.id,
    });
  }
  
  /**
   * Stop AR session and cleanup
   */
  async stopSession(): Promise<void> {
    if (!this.isSessionActive) {
      return;
    }
    
    // Stop AR tracking
    await arService.stopTracking();
    
    // Clear frame processor
    if (this.camera) {
      this.camera.frameProcessor = undefined;
    }
    
    this.isSessionActive = false;
    
    // Save performance metrics
    await this.savePerformanceMetrics();
    
    // Log session end
    performanceMonitor.logEvent('ar_session_ended', {
      duration: Date.now() - this.lastFrameTime,
      metrics: this.performanceMetrics,
    });
  }
  
  /**
   * Process camera frames for AR
   */
  processFrame = (frame: Frame): void => {
    'worklet';
    
    const now = Date.now();
    const deltaTime = now - this.lastFrameTime;
    
    // Skip frames if processing is too slow
    if (deltaTime < 16) { // 60 FPS = 16ms per frame
      return;
    }
    
    // Adaptive frame skipping based on performance
    if (this.shouldSkipFrame()) {
      this.frameSkipCounter++;
      return;
    }
    
    // Process frame on UI thread
    runOnUI(() => {
      const startTime = Date.now();
      
      // Detect landmarks if enabled
      if (this.sessionConfig.enableLandmarkDetection) {
        const landmarks = this.detectLandmarks(frame);
        runOnJS(this.onLandmarksDetected)(landmarks);
      }
      
      // Update performance metrics
      const processingTime = Date.now() - startTime;
      runOnJS(this.updatePerformanceMetrics)(processingTime, deltaTime);
    })();
    
    this.lastFrameTime = now;
  };
  
  /**
   * Detect landmarks in frame
   */
  private detectLandmarks(frame: Frame): any[] {
    'worklet';
    // This would integrate with ML Kit or custom model
    // For now, return empty array
    return [];
  }
  
  /**
   * Handle detected landmarks
   */
  private onLandmarksDetected = (landmarks: any[]): void => {
    // Process landmarks and update AR overlays
    if (landmarks.length > 0) {
      arService.updateARPoints(landmarks);
    }
  };
  
  /**
   * Should skip frame based on performance
   */
  private shouldSkipFrame(): boolean {
    'worklet';
    
    // Skip every other frame in battery saving mode
    if (this.sessionConfig.batteryMode === 'saving') {
      return this.frameSkipCounter % 2 === 0;
    }
    
    // Skip based on processing time
    if (this.performanceMetrics.processingTime > this.MAX_PROCESSING_TIME_MS) {
      return this.frameSkipCounter % 3 === 0; // Skip 1 in 3 frames
    }
    
    return false;
  }
  
  /**
   * Update performance metrics
   */
  private updatePerformanceMetrics = (
    processingTime: number,
    deltaTime: number
  ): void => {
    // Calculate FPS
    this.performanceMetrics.fps = Math.round(1000 / deltaTime);
    
    // Update processing time (moving average)
    this.performanceMetrics.processingTime =
      this.performanceMetrics.processingTime * 0.9 + processingTime * 0.1;
    
    // Check for thermal throttling
    if (this.performanceMetrics.temperature > this.THERMAL_THROTTLE_TEMP) {
      this.enableThermalThrottling();
    }
  };
  
  /**
   * Enable battery saving mode
   */
  private enableBatterySavingMode(): void {
    this.sessionConfig.batteryMode = 'saving';
    this.sessionConfig.targetFPS = 30;
    this.sessionConfig.quality = 'low';
    
    console.log('AR: Battery saving mode enabled');
  }
  
  /**
   * Enable thermal throttling
   */
  private enableThermalThrottling(): void {
    this.sessionConfig.quality = 'low';
    this.sessionConfig.targetFPS = 30;
    
    console.log('AR: Thermal throttling enabled');
  }
  
  /**
   * Get optimal camera format
   */
  private getOptimalFormat(): any {
    if (!this.device) return null;
    
    const formats = this.device.formats;
    
    // Find format based on quality setting
    const targetResolution = {
      low: { width: 640, height: 480 },
      medium: { width: 1280, height: 720 },
      high: { width: 1920, height: 1080 },
    }[this.sessionConfig.quality];
    
    return formats.find(
      (f) =>
        f.videoWidth >= targetResolution.width &&
        f.videoHeight >= targetResolution.height
    );
  }
  
  /**
   * Capture AR photo with overlays
   */
  async captureARPhoto(): Promise<string | null> {
    if (!this.camera || !this.sessionConfig.enablePhotoCapture) {
      return null;
    }
    
    try {
      const photo = await this.camera.takePhoto({
        flash: 'off',
        enableShutterSound: false,
      });
      
      // Process photo with AR overlays
      const processedPhoto = await this.processARPhoto(photo.path);
      
      return processedPhoto;
    } catch (error) {
      console.error('AR photo capture failed:', error);
      return null;
    }
  }
  
  /**
   * Process photo with AR overlays
   */
  private async processARPhoto(photoPath: string): Promise<string> {
    // This would add AR overlays to the photo
    // For now, return original path
    return photoPath;
  }
  
  /**
   * Get battery level
   */
  private async getBatteryLevel(): Promise<number> {
    // This would use a battery status library
    // For now, return mock value
    return 50;
  }
  
  /**
   * Load user preferences
   */
  private async loadUserPreferences(): Promise<void> {
    try {
      const prefs = await AsyncStorage.getItem('ar_preferences');
      if (prefs) {
        const parsed = JSON.parse(prefs);
        this.sessionConfig = { ...this.sessionConfig, ...parsed };
      }
    } catch (error) {
      console.error('Failed to load AR preferences:', error);
    }
  }
  
  /**
   * Save performance metrics
   */
  private async savePerformanceMetrics(): Promise<void> {
    try {
      await AsyncStorage.setItem(
        'ar_performance_metrics',
        JSON.stringify({
          ...this.performanceMetrics,
          timestamp: Date.now(),
        })
      );
    } catch (error) {
      console.error('Failed to save performance metrics:', error);
    }
  }
  
  /**
   * Start performance monitoring
   */
  private startPerformanceMonitoring(): void {
    // Monitor performance every 5 seconds
    setInterval(() => {
      if (this.isSessionActive) {
        performanceMonitor.logMetric('ar_fps', this.performanceMetrics.fps);
        performanceMonitor.logMetric(
          'ar_processing_time',
          this.performanceMetrics.processingTime
        );
        performanceMonitor.logMetric(
          'ar_frame_drops',
          this.performanceMetrics.frameDrops
        );
      }
    }, 5000);
  }
  
  /**
   * Set camera reference
   */
  setCameraRef(camera: Camera | null): void {
    this.camera = camera;
  }
  
  /**
   * Get current session config
   */
  getSessionConfig(): ARSessionConfig {
    return { ...this.sessionConfig };
  }
  
  /**
   * Update session config
   */
  updateSessionConfig(config: Partial<ARSessionConfig>): void {
    this.sessionConfig = { ...this.sessionConfig, ...config };
  }
  
  /**
   * Get performance metrics
   */
  getPerformanceMetrics(): ARPerformanceMetrics {
    return { ...this.performanceMetrics };
  }
}

// Export singleton instance
export const arCameraService = ARCameraService.getInstance();
