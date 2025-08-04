/**
 * Anti-Tampering and Anti-Debugging Module
 * Six Sigma DMAIC - Code Obfuscation Implementation
 * 
 * Provides runtime protection against debugging and tampering
 */

import { NativeModules, Platform } from 'react-native';
import { logger } from '@/services/logger';

class AntiTamperingModule {
  private integrityCheckInterval: NodeJS.Timeout | null = null;
  private debuggerCheckInterval: NodeJS.Timeout | null = null;
  
  /**
   * Initialize anti-tampering protection
   */
  initialize(): void {
    if (__DEV__) {
      // Don't run in development
      return;
    }
    
    this.startIntegrityChecks();
    this.startDebuggerDetection();
    this.checkJailbreakRoot();
    this.verifyAppSignature();
  }
  
  /**
   * Start periodic integrity checks
   */
  private startIntegrityChecks(): void {
    // Initial check
    this.performIntegrityCheck();
    
    // Periodic checks every 30 seconds
    this.integrityCheckInterval = setInterval(() => {
      this.performIntegrityCheck();
    }, 30000);
  }
  
  /**
   * Perform integrity verification
   */
  private performIntegrityCheck(): void {
    try {
      // Check if critical modules exist
      const criticalModules = [
        'RNSecurityModule',
        'RNAndroidAutoModule',
      ];
      
      for (const moduleName of criticalModules) {
        if (NativeModules[moduleName] && !NativeModules[moduleName]._isValid) {
          this.handleTamperingDetected('Native module tampered');
        }
      }
      
      // Verify bundle integrity (simplified check)
      if (global.__fbBatchedBridge) {
        const bridge = global.__fbBatchedBridge;
        if (!bridge._remoteModuleTable || !bridge._remoteMethodTable) {
          this.handleTamperingDetected('Bridge tampered');
        }
      }
      
    } catch (error) {
      logger.error('Integrity check failed', error);
    }
  }
  
  /**
   * Detect debugger attachment
   */
  private startDebuggerDetection(): void {
    if (Platform.OS === 'ios') {
      this.detectIOSDebugger();
    } else if (Platform.OS === 'android') {
      this.detectAndroidDebugger();
    }
    
    // Check every 5 seconds
    this.debuggerCheckInterval = setInterval(() => {
      this.checkDebuggerStatus();
    }, 5000);
  }
  
  /**
   * iOS debugger detection
   */
  private detectIOSDebugger(): void {
    // Check for common debugger artifacts
    const suspiciousGlobals = [
      '__REACT_DEVTOOLS_GLOBAL_HOOK__',
      '__REACT_DEBUGGER__',
    ];
    
    for (const global of suspiciousGlobals) {
      if (window[global]) {
        this.handleDebuggerDetected();
      }
    }
  }
  
  /**
   * Android debugger detection
   */
  private detectAndroidDebugger(): void {
    // Check if app is debuggable
    if (NativeModules.RNSecurityModule?.isDebuggable) {
      NativeModules.RNSecurityModule.isDebuggable()
        .then((debuggable: boolean) => {
          if (debuggable) {
            this.handleDebuggerDetected();
          }
        })
        .catch(() => {
          // Ignore errors
        });
    }
  }
  
  /**
   * Check current debugger status
   */
  private checkDebuggerStatus(): void {
    // Performance-based debugger detection
    const start = performance.now();
    let counter = 0;
    
    // This loop should execute very quickly
    for (let i = 0; i < 1000000; i++) {
      counter++;
    }
    
    const elapsed = performance.now() - start;
    
    // If it takes too long, debugger might be attached
    if (elapsed > 100) {
      this.handleDebuggerDetected();
    }
  }
  
  /**
   * Check for jailbreak/root
   */
  private checkJailbreakRoot(): void {
    if (NativeModules.RNSecurityModule?.checkJailbreakRoot) {
      NativeModules.RNSecurityModule.checkJailbreakRoot()
        .then((isCompromised: boolean) => {
          if (isCompromised) {
            this.handleCompromisedDevice();
          }
        })
        .catch(() => {
          // Ignore errors
        });
    }
  }
  
  /**
   * Verify app signature
   */
  private verifyAppSignature(): void {
    if (NativeModules.RNSecurityModule?.verifySignature) {
      NativeModules.RNSecurityModule.verifySignature()
        .then((isValid: boolean) => {
          if (!isValid) {
            this.handleTamperingDetected('Invalid app signature');
          }
        })
        .catch(() => {
          // Ignore errors
        });
    }
  }
  
  /**
   * Handle tampering detection
   */
  private handleTamperingDetected(reason: string): void {
    logger.error('Tampering detected', { reason });
    
    // Clear sensitive data
    this.clearSensitiveData();
    
    // Optionally crash the app
    if (Platform.OS === 'android') {
      // Force close on Android
      NativeModules.RNSecurityModule?.forceClose?.();
    }
  }
  
  /**
   * Handle debugger detection
   */
  private handleDebuggerDetected(): void {
    logger.warn('Debugger detected');
    
    // Disable sensitive features
    this.disableSensitiveFeatures();
    
    // Clear intervals
    this.cleanup();
  }
  
  /**
   * Handle compromised device
   */
  private handleCompromisedDevice(): void {
    logger.error('Device compromised (jailbreak/root)');
    
    // Limit functionality
    this.disableSensitiveFeatures();
  }
  
  /**
   * Clear sensitive data from memory
   */
  private clearSensitiveData(): void {
    // Clear async storage
    if (NativeModules.RNSecurityModule?.clearSecureStorage) {
      NativeModules.RNSecurityModule.clearSecureStorage();
    }
  }
  
  /**
   * Disable sensitive features
   */
  private disableSensitiveFeatures(): void {
    // Set global flag
    global.__FEATURES_DISABLED__ = true;
  }
  
  /**
   * Cleanup intervals
   */
  cleanup(): void {
    if (this.integrityCheckInterval) {
      clearInterval(this.integrityCheckInterval);
    }
    if (this.debuggerCheckInterval) {
      clearInterval(this.debuggerCheckInterval);
    }
  }
}

// Export singleton instance
export const antiTampering = new AntiTamperingModule();

// Auto-initialize in production
if (!__DEV__) {
  antiTampering.initialize();
}

export default antiTampering;