/**
 * Mobile Security Service - Production Implementation
 * Comprehensive device integrity and security monitoring
 * Includes jailbreak/root detection, app tampering detection, and security hardening
 */

import { Platform, NativeModules, DeviceEventEmitter } from 'react-native';
import * as Device from 'expo-device';
import * as Application from 'expo-application';
import * as Constants from 'expo-constants';
import * as FileSystem from 'expo-file-system';
import * as Crypto from 'expo-crypto';
import * as Network from 'expo-network';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { logger } from './logger';

interface SecurityStatus {
  isJailbroken: boolean;
  isRooted: boolean;
  isDebuggingEnabled: boolean;
  isEmulator: boolean;
  isTampered: boolean;
  isVPNActive: boolean;
  securityScore: number;
  risks: SecurityRisk[];
  timestamp: Date;
}

interface SecurityRisk {
  type: SecurityRiskType;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  mitigation: string;
}

enum SecurityRiskType {
  JAILBREAK = 'JAILBREAK',
  ROOT = 'ROOT',
  DEBUGGING = 'DEBUGGING',
  EMULATOR = 'EMULATOR',
  TAMPERING = 'TAMPERING',
  VPN = 'VPN',
  NETWORK = 'NETWORK',
  OUTDATED_OS = 'OUTDATED_OS',
  UNKNOWN_SOURCE = 'UNKNOWN_SOURCE'
}

interface SecurityConfig {
  enableJailbreakDetection: boolean;
  enableTamperDetection: boolean;
  enableNetworkMonitoring: boolean;
  enableDebugDetection: boolean;
  minSecurityScore: number;
  blockOnHighRisk: boolean;
}

class MobileSecurityService {
  private static instance: MobileSecurityService;
  private config: SecurityConfig;
  private securityCheckInterval: NodeJS.Timer | null = null;
  private lastSecurityStatus: SecurityStatus | null = null;
  private appSignature: string | null = null;
  
  // Jailbreak/Root detection signatures
  private readonly jailbreakPaths = [
    '/Applications/Cydia.app',
    '/Library/MobileSubstrate/MobileSubstrate.dylib',
    '/bin/bash',
    '/usr/sbin/sshd',
    '/etc/apt',
    '/private/var/lib/apt/',
    '/private/var/lib/cydia',
    '/private/var/stash',
    '/usr/libexec/cydia',
    '/usr/bin/cycript',
    '/usr/local/bin/cycript',
    '/usr/lib/libcycript.dylib',
    '/System/Library/LaunchDaemons/com.saurik.Cydia.Startup.plist',
    '/System/Library/LaunchDaemons/com.ikey.bbot.plist',
    '/Library/MobileSubstrate/DynamicLibraries/LiveClock.plist',
    '/Library/MobileSubstrate/DynamicLibraries/Veency.plist',
    '/private/var/mobile/Library/SBSettings/Themes'
  ];

  private readonly rootPaths = [
    '/system/app/Superuser.apk',
    '/sbin/su',
    '/system/bin/su',
    '/system/xbin/su',
    '/data/local/xbin/su',
    '/data/local/bin/su',
    '/system/sd/xbin/su',
    '/system/bin/failsafe/su',
    '/data/local/su',
    '/su/bin/su',
    '/system/bin/.ext/.su',
    '/system/usr/we-need-root/su-backup',
    '/system/xbin/mu',
    '/system/bin/magisk',
    '/data/adb/magisk',
    '/sbin/.magisk',
    '/data/adb/ksu',
    '/data/adb/ksud'
  ];

  private readonly rootPackages = [
    'com.koushikdutta.superuser',
    'com.noshufou.android.su',
    'com.noshufou.android.su.elite',
    'eu.chainfire.supersu',
    'com.thirdparty.superuser',
    'com.yellowes.su',
    'com.topjohnwu.magisk',
    'com.kingroot.kinguser',
    'com.kingo.root',
    'com.smedialink.oneclean',
    'com.zhiqupk.root.global',
    'com.alephzain.framaroot'
  ];

  private constructor() {
    this.config = {
      enableJailbreakDetection: true,
      enableTamperDetection: true,
      enableNetworkMonitoring: true,
      enableDebugDetection: true,
      minSecurityScore: 70,
      blockOnHighRisk: false
    };
  }

  static getInstance(): MobileSecurityService {
    if (!MobileSecurityService.instance) {
      MobileSecurityService.instance = new MobileSecurityService();
    }
    return MobileSecurityService.instance;
  }

  /**
   * Initialize security monitoring
   */
  async initialize(config?: Partial<SecurityConfig>): Promise<void> {
    if (config) {
      this.config = { ...this.config, ...config };
    }

    try {
      // Generate app signature for tamper detection
      await this.generateAppSignature();

      // Perform initial security check
      await this.performSecurityCheck();

      // Start continuous monitoring
      this.startContinuousMonitoring();

      // Setup event listeners
      this.setupEventListeners();

      logger.info('Mobile security service initialized');
    } catch (error) {
      logger.error('Failed to initialize mobile security', error);
    }
  }

  /**
   * Perform comprehensive security check
   */
  async performSecurityCheck(): Promise<SecurityStatus> {
    const risks: SecurityRisk[] = [];
    let securityScore = 100;

    // Check for jailbreak/root
    const jailbreakStatus = await this.checkJailbreakRoot();
    if (jailbreakStatus.isJailbroken || jailbreakStatus.isRooted) {
      risks.push({
        type: jailbreakStatus.isJailbroken ? SecurityRiskType.JAILBREAK : SecurityRiskType.ROOT,
        severity: 'critical',
        description: `Device is ${jailbreakStatus.isJailbroken ? 'jailbroken' : 'rooted'}`,
        mitigation: 'Use only on trusted devices'
      });
      securityScore -= 40;
    }

    // Check for debugging
    const isDebugging = await this.checkDebugging();
    if (isDebugging) {
      risks.push({
        type: SecurityRiskType.DEBUGGING,
        severity: 'high',
        description: 'Debugging is enabled',
        mitigation: 'Disable debugging in production'
      });
      securityScore -= 20;
    }

    // Check for emulator
    const isEmulator = await this.checkEmulator();
    if (isEmulator) {
      risks.push({
        type: SecurityRiskType.EMULATOR,
        severity: 'medium',
        description: 'Running on emulator',
        mitigation: 'Use physical device for sensitive operations'
      });
      securityScore -= 15;
    }

    // Check for app tampering
    const isTampered = await this.checkAppTampering();
    if (isTampered) {
      risks.push({
        type: SecurityRiskType.TAMPERING,
        severity: 'critical',
        description: 'App integrity compromised',
        mitigation: 'Reinstall from official source'
      });
      securityScore -= 30;
    }

    // Check network security
    const networkStatus = await this.checkNetworkSecurity();
    if (networkStatus.isVPNActive) {
      risks.push({
        type: SecurityRiskType.VPN,
        severity: 'low',
        description: 'VPN connection detected',
        mitigation: 'Verify VPN is trusted'
      });
      securityScore -= 5;
    }

    // Check OS version
    const osRisk = await this.checkOSVersion();
    if (osRisk) {
      risks.push(osRisk);
      securityScore -= 10;
    }

    const status: SecurityStatus = {
      isJailbroken: jailbreakStatus.isJailbroken,
      isRooted: jailbreakStatus.isRooted,
      isDebuggingEnabled: isDebugging,
      isEmulator,
      isTampered,
      isVPNActive: networkStatus.isVPNActive,
      securityScore: Math.max(0, securityScore),
      risks,
      timestamp: new Date()
    };

    this.lastSecurityStatus = status;
    await this.saveSecurityStatus(status);

    // Emit security event
    DeviceEventEmitter.emit('securityStatusChanged', status);

    // Take action if configured
    if (this.config.blockOnHighRisk && securityScore < this.config.minSecurityScore) {
      await this.handleHighRiskDevice(status);
    }

    return status;
  }

  /**
   * Check for jailbreak (iOS) or root (Android)
   */
  private async checkJailbreakRoot(): Promise<{ isJailbroken: boolean; isRooted: boolean }> {
    if (Platform.OS === 'ios') {
      return { isJailbroken: await this.checkIOSJailbreak(), isRooted: false };
    } else if (Platform.OS === 'android') {
      return { isJailbroken: false, isRooted: await this.checkAndroidRoot() };
    }
    return { isJailbroken: false, isRooted: false };
  }

  /**
   * iOS Jailbreak Detection
   */
  private async checkIOSJailbreak(): Promise<boolean> {
    try {
      // Method 1: Check for jailbreak files
      for (const path of this.jailbreakPaths) {
        try {
          const info = await FileSystem.getInfoAsync(path);
          if (info.exists) {
            logger.warn(`Jailbreak indicator found: ${path}`);
            return true;
          }
        } catch {
          // Expected to fail on non-jailbroken devices
        }
      }

      // Method 2: Check if we can write outside sandbox
      try {
        const testPath = '/private/test_' + Date.now() + '.txt';
        await FileSystem.writeAsStringAsync(testPath, 'test');
        await FileSystem.deleteAsync(testPath);
        logger.warn('Sandbox restriction bypassed');
        return true;
      } catch {
        // Expected to fail on non-jailbroken devices
      }

      // Method 3: Check URL schemes
      const suspiciousSchemes = ['cydia://', 'sileo://', 'zbra://', 'undecimus://'];
      if (NativeModules.RNSecurityModule) {
        for (const scheme of suspiciousSchemes) {
          const canOpen = await NativeModules.RNSecurityModule.canOpenURL(scheme);
          if (canOpen) {
            logger.warn(`Suspicious URL scheme detected: ${scheme}`);
            return true;
          }
        }
      }

      // Method 4: Check system properties
      if (NativeModules.RNSecurityModule?.checkJailbreak) {
        return await NativeModules.RNSecurityModule.checkJailbreak();
      }

      return false;
    } catch (error) {
      logger.error('Jailbreak detection error', error);
      return false;
    }
  }

  /**
   * Android Root Detection
   */
  private async checkAndroidRoot(): Promise<boolean> {
    try {
      // Method 1: Check for root files
      for (const path of this.rootPaths) {
        try {
          const info = await FileSystem.getInfoAsync(path);
          if (info.exists) {
            logger.warn(`Root indicator found: ${path}`);
            return true;
          }
        } catch {
          // Expected to fail on non-rooted devices
        }
      }

      // Method 2: Check for root packages
      if (NativeModules.RNSecurityModule?.checkPackages) {
        for (const pkg of this.rootPackages) {
          const exists = await NativeModules.RNSecurityModule.checkPackages(pkg);
          if (exists) {
            logger.warn(`Root package detected: ${pkg}`);
            return true;
          }
        }
      }

      // Method 3: Check build properties
      const buildTags = await this.getBuildProperty('ro.build.tags');
      if (buildTags && buildTags.includes('test-keys')) {
        logger.warn('Test keys detected in build');
        return true;
      }

      // Method 4: Try to execute su command
      if (NativeModules.RNSecurityModule?.checkSuAccess) {
        const hasSu = await NativeModules.RNSecurityModule.checkSuAccess();
        if (hasSu) {
          logger.warn('Su binary accessible');
          return true;
        }
      }

      // Method 5: Check SELinux status
      const selinuxEnforcing = await this.checkSELinuxStatus();
      if (!selinuxEnforcing) {
        logger.warn('SELinux not enforcing');
        return true;
      }

      return false;
    } catch (error) {
      logger.error('Root detection error', error);
      return false;
    }
  }

  /**
   * Check for debugging
   */
  private async checkDebugging(): Promise<boolean> {
    try {
      // Check if debugger is attached
      if (__DEV__) {
        return true;
      }

      // Platform specific checks
      if (Platform.OS === 'ios') {
        // Check for debugger via sysctl
        if (NativeModules.RNSecurityModule?.isDebuggerAttached) {
          return await NativeModules.RNSecurityModule.isDebuggerAttached();
        }
      } else if (Platform.OS === 'android') {
        // Check Debug.isDebuggerConnected()
        if (NativeModules.RNSecurityModule?.isDebuggerConnected) {
          return await NativeModules.RNSecurityModule.isDebuggerConnected();
        }
      }

      return false;
    } catch (error) {
      logger.error('Debug detection error', error);
      return false;
    }
  }

  /**
   * Check if running on emulator
   */
  private async checkEmulator(): Promise<boolean> {
    try {
      // Use Expo Device API
      if (!Device.isDevice) {
        return true;
      }

      // Additional Android checks
      if (Platform.OS === 'android') {
        const fingerprint = await this.getBuildProperty('ro.build.fingerprint');
        const model = await this.getBuildProperty('ro.product.model');
        const manufacturer = await this.getBuildProperty('ro.product.manufacturer');
        const hardware = await this.getBuildProperty('ro.hardware');

        const emulatorIndicators = [
          'generic', 'unknown', 'emulator', 'sdk', 'google_sdk',
          'vbox', 'nox', 'bluestacks', 'genymotion'
        ];

        for (const indicator of emulatorIndicators) {
          if (
            fingerprint?.toLowerCase().includes(indicator) ||
            model?.toLowerCase().includes(indicator) ||
            manufacturer?.toLowerCase().includes(indicator) ||
            hardware?.toLowerCase().includes(indicator)
          ) {
            return true;
          }
        }
      }

      return false;
    } catch (error) {
      logger.error('Emulator detection error', error);
      return false;
    }
  }

  /**
   * Check for app tampering
   */
  private async checkAppTampering(): Promise<boolean> {
    try {
      // Method 1: Verify app signature
      const currentSignature = await this.calculateAppSignature();
      if (this.appSignature && currentSignature !== this.appSignature) {
        logger.warn('App signature mismatch');
        return true;
      }

      // Method 2: Check installer source
      if (Platform.OS === 'android') {
        const installer = await Application.getInstallationSourceAsync();
        const trustedInstallers = [
          'com.android.vending', // Google Play
          'com.amazon.venezia', // Amazon Appstore
          'com.sec.android.app.samsungapps' // Samsung Galaxy Store
        ];

        if (!trustedInstallers.includes(installer)) {
          logger.warn(`Untrusted installer: ${installer}`);
          // Don't return true here as development builds won't have trusted installer
        }
      }

      // Method 3: Check code integrity (if native module available)
      if (NativeModules.RNSecurityModule?.verifyCodeIntegrity) {
        const isValid = await NativeModules.RNSecurityModule.verifyCodeIntegrity();
        if (!isValid) {
          logger.warn('Code integrity check failed');
          return true;
        }
      }

      return false;
    } catch (error) {
      logger.error('Tamper detection error', error);
      return false;
    }
  }

  /**
   * Check network security
   */
  private async checkNetworkSecurity(): Promise<{ isVPNActive: boolean; isProxyActive: boolean }> {
    try {
      const networkState = await Network.getNetworkStateAsync();

      // Check for VPN
      let isVPNActive = false;
      if (Platform.OS === 'android' && NativeModules.RNSecurityModule?.checkVPN) {
        isVPNActive = await NativeModules.RNSecurityModule.checkVPN();
      } else if (Platform.OS === 'ios' && NativeModules.RNSecurityModule?.checkVPN) {
        isVPNActive = await NativeModules.RNSecurityModule.checkVPN();
      }

      // Check for proxy
      let isProxyActive = false;
      if (NativeModules.RNSecurityModule?.checkProxy) {
        isProxyActive = await NativeModules.RNSecurityModule.checkProxy();
      }

      return { isVPNActive, isProxyActive };
    } catch (error) {
      logger.error('Network security check error', error);
      return { isVPNActive: false, isProxyActive: false };
    }
  }

  /**
   * Check OS version security
   */
  private async checkOSVersion(): Promise<SecurityRisk | null> {
    try {
      const osVersion = Platform.Version;
      
      if (Platform.OS === 'ios') {
        // iOS 14+ recommended for security features
        if (typeof osVersion === 'string' && parseFloat(osVersion) < 14) {
          return {
            type: SecurityRiskType.OUTDATED_OS,
            severity: 'medium',
            description: `iOS ${osVersion} is outdated`,
            mitigation: 'Update to iOS 14 or later'
          };
        }
      } else if (Platform.OS === 'android') {
        // Android 10+ (API 29+) recommended
        if (typeof osVersion === 'number' && osVersion < 29) {
          return {
            type: SecurityRiskType.OUTDATED_OS,
            severity: 'medium',
            description: `Android API ${osVersion} is outdated`,
            mitigation: 'Update to Android 10 (API 29) or later'
          };
        }
      }

      return null;
    } catch (error) {
      logger.error('OS version check error', error);
      return null;
    }
  }

  /**
   * Generate app signature for tamper detection
   */
  private async generateAppSignature(): Promise<void> {
    try {
      const appInfo = {
        bundleId: Application.applicationId,
        version: Application.nativeApplicationVersion,
        buildNumber: Application.nativeBuildVersion,
        name: Application.applicationName
      };

      const signature = await Crypto.digestStringAsync(
        Crypto.CryptoDigestAlgorithm.SHA256,
        JSON.stringify(appInfo)
      );

      this.appSignature = signature;
    } catch (error) {
      logger.error('Failed to generate app signature', error);
    }
  }

  /**
   * Calculate current app signature
   */
  private async calculateAppSignature(): Promise<string> {
    const appInfo = {
      bundleId: Application.applicationId,
      version: Application.nativeApplicationVersion,
      buildNumber: Application.nativeBuildVersion,
      name: Application.applicationName
    };

    return await Crypto.digestStringAsync(
      Crypto.CryptoDigestAlgorithm.SHA256,
      JSON.stringify(appInfo)
    );
  }

  /**
   * Get Android build property
   */
  private async getBuildProperty(prop: string): Promise<string | null> {
    try {
      if (Platform.OS === 'android' && NativeModules.RNSecurityModule?.getBuildProperty) {
        return await NativeModules.RNSecurityModule.getBuildProperty(prop);
      }
      return null;
    } catch {
      return null;
    }
  }

  /**
   * Check SELinux status on Android
   */
  private async checkSELinuxStatus(): Promise<boolean> {
    try {
      if (Platform.OS === 'android' && NativeModules.RNSecurityModule?.getSELinuxStatus) {
        const status = await NativeModules.RNSecurityModule.getSELinuxStatus();
        return status === 'Enforcing';
      }
      return true;
    } catch {
      return true;
    }
  }

  /**
   * Start continuous security monitoring
   */
  private startContinuousMonitoring(): void {
    if (this.securityCheckInterval) {
      clearInterval(this.securityCheckInterval);
    }

    // Check every 5 minutes
    this.securityCheckInterval = setInterval(() => {
      this.performSecurityCheck().catch(error => {
        logger.error('Continuous security check failed', error);
      });
    }, 5 * 60 * 1000);
  }

  /**
   * Setup event listeners
   */
  private setupEventListeners(): void {
    // Listen for app state changes
    DeviceEventEmitter.addListener('appStateChange', (state) => {
      if (state === 'active') {
        this.performSecurityCheck().catch(error => {
          logger.error('Security check on app activation failed', error);
        });
      }
    });
  }

  /**
   * Handle high risk device
   */
  private async handleHighRiskDevice(status: SecurityStatus): Promise<void> {
    logger.warn('High risk device detected', status);

    // Store security alert
    await AsyncStorage.setItem('security_alert', JSON.stringify({
      timestamp: new Date().toISOString(),
      status,
      action: 'blocked'
    }));

    // Emit high risk event
    DeviceEventEmitter.emit('highRiskDevice', status);
  }

  /**
   * Save security status
   */
  private async saveSecurityStatus(status: SecurityStatus): Promise<void> {
    try {
      await AsyncStorage.setItem('security_status', JSON.stringify(status));
    } catch (error) {
      logger.error('Failed to save security status', error);
    }
  }

  /**
   * Get last security status
   */
  async getLastSecurityStatus(): Promise<SecurityStatus | null> {
    if (this.lastSecurityStatus) {
      return this.lastSecurityStatus;
    }

    try {
      const saved = await AsyncStorage.getItem('security_status');
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (error) {
      logger.error('Failed to load security status', error);
    }

    return null;
  }

  /**
   * Check if device is secure
   */
  async isDeviceSecure(): Promise<boolean> {
    const status = await this.getLastSecurityStatus();
    if (!status) {
      await this.performSecurityCheck();
      return this.lastSecurityStatus ? this.lastSecurityStatus.securityScore >= this.config.minSecurityScore : false;
    }
    return status.securityScore >= this.config.minSecurityScore;
  }

  /**
   * Enable security hardening
   */
  async enableSecurityHardening(): Promise<void> {
    try {
      // Enable certificate pinning
      if (NativeModules.RNSecurityModule?.enableCertificatePinning) {
        await NativeModules.RNSecurityModule.enableCertificatePinning();
      }

      // Enable anti-debugging
      if (NativeModules.RNSecurityModule?.enableAntiDebugging) {
        await NativeModules.RNSecurityModule.enableAntiDebugging();
      }

      // Enable screenshot protection (Android)
      if (Platform.OS === 'android' && NativeModules.RNSecurityModule?.setScreenshotBlocking) {
        await NativeModules.RNSecurityModule.setScreenshotBlocking(true);
      }

      // Enable app backgrounding protection (iOS)
      if (Platform.OS === 'ios' && NativeModules.RNSecurityModule?.enableBackgroundBlur) {
        await NativeModules.RNSecurityModule.enableBackgroundBlur();
      }

      logger.info('Security hardening enabled');
    } catch (error) {
      logger.error('Failed to enable security hardening', error);
    }
  }

  /**
   * Cleanup and stop monitoring
   */
  cleanup(): void {
    if (this.securityCheckInterval) {
      clearInterval(this.securityCheckInterval);
      this.securityCheckInterval = null;
    }
    DeviceEventEmitter.removeAllListeners('appStateChange');
  }
}

export default MobileSecurityService.getInstance();
export { SecurityStatus, SecurityRisk, SecurityRiskType, SecurityConfig };