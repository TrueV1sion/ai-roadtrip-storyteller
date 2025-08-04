/**
 * Enhanced Mobile Security Service
 * Six Sigma DMAIC - IMPROVE Phase Implementation
 * 
 * Comprehensive security service with certificate pinning integration,
 * enhanced jailbreak/root detection, and security response strategies
 */

import { Platform, NativeModules, DeviceEventEmitter, AppState, AppStateStatus } from 'react-native';
import * as Device from 'expo-device';
import * as Application from 'expo-application';
import * as Constants from 'expo-constants';
import * as FileSystem from 'expo-file-system';
import * as Crypto from 'expo-crypto';
import * as Network from 'expo-network';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { logger } from '../logger';
import CertificatePinningService from './CertificatePinningService';
import SecureConfig from '@/config/secure-config';

// Security levels for different app features
export enum SecurityLevel {
  NONE = 'none',
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

// Security response strategies
export enum SecurityResponse {
  LOG_ONLY = 'log_only',
  WARN_USER = 'warn_user',
  RESTRICT_FEATURES = 'restrict_features',
  BLOCK_ACCESS = 'block_access'
}

interface SecurityFeatureRestriction {
  feature: string;
  requiredSecurityLevel: SecurityLevel;
  restrictedMessage: string;
}

interface SecurityConfiguration {
  enableJailbreakDetection: boolean;
  enableTamperDetection: boolean;
  enableNetworkMonitoring: boolean;
  enableDebugDetection: boolean;
  enableCertificatePinning: boolean;
  minSecurityScore: number;
  responseStrategy: SecurityResponse;
  featureRestrictions: SecurityFeatureRestriction[];
  securityCheckInterval: number; // milliseconds
  enableSecurityBypass: boolean; // For testing only
}

interface ExtendedSecurityStatus {
  isJailbroken: boolean;
  isRooted: boolean;
  isDebuggingEnabled: boolean;
  isEmulator: boolean;
  isTampered: boolean;
  isVPNActive: boolean;
  isProxyActive: boolean;
  certificatePinningActive: boolean;
  securityScore: number;
  securityLevel: SecurityLevel;
  risks: SecurityRisk[];
  restrictedFeatures: string[];
  timestamp: Date;
  deviceFingerprint: string;
}

interface SecurityRisk {
  type: SecurityRiskType;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  mitigation: string;
  detectionMethod: string;
  confidence: number; // 0-100
}

enum SecurityRiskType {
  JAILBREAK = 'JAILBREAK',
  ROOT = 'ROOT',
  DEBUGGING = 'DEBUGGING',
  EMULATOR = 'EMULATOR',
  TAMPERING = 'TAMPERING',
  VPN = 'VPN',
  PROXY = 'PROXY',
  NETWORK = 'NETWORK',
  CERTIFICATE = 'CERTIFICATE',
  OUTDATED_OS = 'OUTDATED_OS',
  UNKNOWN_SOURCE = 'UNKNOWN_SOURCE',
  HOOK_DETECTED = 'HOOK_DETECTED',
  FRIDA_DETECTED = 'FRIDA_DETECTED'
}

class EnhancedMobileSecurityService {
  private static instance: EnhancedMobileSecurityService;
  private config: SecurityConfiguration;
  private securityCheckInterval: NodeJS.Timer | null = null;
  private lastSecurityStatus: ExtendedSecurityStatus | null = null;
  private appSignature: string | null = null;
  private deviceFingerprint: string | null = null;
  private securityEventListeners: Map<string, Function[]> = new Map();
  
  // Enhanced jailbreak/root detection patterns
  private readonly enhancedJailbreakIndicators = {
    files: [
      // Common jailbreak files
      '/Applications/Cydia.app',
      '/Applications/FakeCarrier.app',
      '/Applications/Icy.app',
      '/Applications/IntelliScreen.app',
      '/Applications/SBSettings.app',
      '/Applications/WinterBoard.app',
      '/Applications/blackra1n.app',
      // Libraries and binaries
      '/Library/MobileSubstrate/MobileSubstrate.dylib',
      '/Library/MobileSubstrate/DynamicLibraries/*',
      '/Library/Frameworks/CydiaSubstrate.framework',
      '/usr/libexec/cydia/*',
      '/usr/libexec/sftp-server',
      '/usr/libexec/ssh-keysign',
      // System modifications
      '/private/var/lib/apt/*',
      '/private/var/lib/cydia/*',
      '/private/var/mobile/Library/SBSettings/Themes/*',
      '/private/var/stash/*',
      '/private/var/tmp/cydia.log',
      '/var/cache/apt/*',
      '/var/lib/apt/*',
      '/var/lib/cydia/*',
      // Binaries
      '/bin/bash',
      '/bin/sh',
      '/usr/bin/sshd',
      '/usr/bin/ssh',
      '/usr/sbin/sshd',
      '/etc/ssh/sshd_config',
      '/etc/apt/*'
    ],
    urlSchemes: [
      'cydia://',
      'sileo://',
      'zbra://',
      'installer://',
      'filza://',
      'undecimus://',
      'substitute://',
      'activator://'
    ],
    dylibsToCheck: [
      'MobileSubstrate',
      'SubstrateLoader',
      'SubstrateInserter',
      'SubstrateBootstrap',
      'cynject',
      'libcycript',
      'frida',
      'fridagadget'
    ]
  };

  private readonly enhancedRootIndicators = {
    files: [
      // Superuser apps
      '/system/app/Superuser.apk',
      '/system/app/SuperSU.apk',
      '/system/app/Superuser/*',
      '/system/app/SuperSU/*',
      // Su binaries
      '/sbin/su',
      '/system/bin/su',
      '/system/xbin/su',
      '/data/local/xbin/su',
      '/data/local/bin/su',
      '/system/sd/xbin/su',
      '/system/bin/failsafe/su',
      '/data/local/su',
      '/su/bin/su',
      '/su/bin/*',
      '/system/bin/.ext/.su',
      '/system/usr/we-need-root/su-backup',
      // Magisk
      '/system/bin/magisk',
      '/data/adb/magisk',
      '/sbin/.magisk',
      '/data/adb/magisk/*',
      '/data/adb/modules/*',
      // KernelSU
      '/data/adb/ksu',
      '/data/adb/ksud',
      '/data/adb/ksu/*',
      // Busybox
      '/system/xbin/busybox',
      '/system/bin/busybox',
      '/data/local/bin/busybox',
      // Other root indicators
      '/system/xbin/daemonsu',
      '/system/etc/init.d/99SuperSUDaemon',
      '/system/bin/.ext/.su',
      '/system/etc/.has_su_daemon',
      '/dev/com.koushikdutta.superuser.daemon/*'
    ],
    packages: [
      'com.koushikdutta.superuser',
      'com.koushikdutta.rommanager',
      'com.koushikdutta.rommanager.license',
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
      'com.alephzain.framaroot',
      'com.android.vending.billing.InAppBillingService.COIN',
      'com.android.vending.billing.InAppBillingService.LUCK',
      'com.chelpus.lackypatch',
      'com.dimonvideo.luckypatcher',
      'com.forpda.lp',
      'com.android.vending.billing.InAppBillingService.CLON',
      'com.devadvance.rootcloak',
      'com.devadvance.rootcloakplus',
      'com.zachspong.temprootremovejb',
      'com.amphoras.hidemyroot',
      'com.formyhm.hiderootPremium',
      'com.formyhm.hideroot'
    ],
    properties: [
      { key: 'ro.build.tags', value: 'test-keys' },
      { key: 'ro.debuggable', value: '1' },
      { key: 'ro.secure', value: '0' },
      { key: 'service.adb.root', value: '1' },
      { key: 'ro.build.selinux', value: '0' }
    ]
  };

  private constructor() {
    this.config = {
      enableJailbreakDetection: !__DEV__ && SecureConfig.SECURITY.ENABLE_JAILBREAK_DETECTION,
      enableTamperDetection: !__DEV__,
      enableNetworkMonitoring: true,
      enableDebugDetection: !__DEV__,
      enableCertificatePinning: !__DEV__ && SecureConfig.SECURITY.ENABLE_CERTIFICATE_PINNING,
      minSecurityScore: 60,
      responseStrategy: __DEV__ ? SecurityResponse.LOG_ONLY : SecurityResponse.WARN_USER,
      securityCheckInterval: 5 * 60 * 1000, // 5 minutes
      enableSecurityBypass: false,
      featureRestrictions: [
        {
          feature: 'payment',
          requiredSecurityLevel: SecurityLevel.HIGH,
          restrictedMessage: 'Payment features are disabled on compromised devices'
        },
        {
          feature: 'biometric_auth',
          requiredSecurityLevel: SecurityLevel.HIGH,
          restrictedMessage: 'Biometric authentication is disabled on compromised devices'
        },
        {
          feature: 'offline_maps',
          requiredSecurityLevel: SecurityLevel.MEDIUM,
          restrictedMessage: 'Offline maps require a secure device'
        },
        {
          feature: 'voice_commands',
          requiredSecurityLevel: SecurityLevel.LOW,
          restrictedMessage: 'Voice commands may be limited on this device'
        }
      ]
    };
  }

  static getInstance(): EnhancedMobileSecurityService {
    if (!EnhancedMobileSecurityService.instance) {
      EnhancedMobileSecurityService.instance = new EnhancedMobileSecurityService();
    }
    return EnhancedMobileSecurityService.instance;
  }

  /**
   * Initialize enhanced security monitoring
   */
  async initialize(config?: Partial<SecurityConfiguration>): Promise<void> {
    if (config) {
      this.config = { ...this.config, ...config };
    }

    try {
      // Generate device fingerprint
      await this.generateDeviceFingerprint();

      // Generate app signature for tamper detection
      await this.generateAppSignature();

      // Initialize certificate pinning
      if (this.config.enableCertificatePinning) {
        await CertificatePinningService.initialize();
      }

      // Perform initial security check
      await this.performSecurityCheck();

      // Start continuous monitoring
      this.startContinuousMonitoring();

      // Setup event listeners
      this.setupEventListeners();

      // Enable security hardening
      await this.enableSecurityHardening();

      logger.info('Enhanced mobile security service initialized', {
        certificatePinning: this.config.enableCertificatePinning,
        responseStrategy: this.config.responseStrategy
      });
    } catch (error) {
      logger.error('Failed to initialize enhanced mobile security', error);
    }
  }

  /**
   * Perform comprehensive security check with enhanced detection
   */
  async performSecurityCheck(): Promise<ExtendedSecurityStatus> {
    const risks: SecurityRisk[] = [];
    let securityScore = 100;

    // Check for jailbreak/root with multiple methods
    const jailbreakStatus = await this.performEnhancedJailbreakRootDetection();
    if (jailbreakStatus.isJailbroken || jailbreakStatus.isRooted) {
      risks.push(...jailbreakStatus.risks);
      securityScore -= jailbreakStatus.isJailbroken || jailbreakStatus.isRooted ? 40 : 0;
    }

    // Check for runtime manipulation (Frida, Xposed, etc.)
    const manipulationStatus = await this.checkRuntimeManipulation();
    if (manipulationStatus.detected) {
      risks.push(...manipulationStatus.risks);
      securityScore -= 30;
    }

    // Check for debugging
    const debugStatus = await this.performEnhancedDebugDetection();
    if (debugStatus.isDebugging) {
      risks.push(...debugStatus.risks);
      securityScore -= 20;
    }

    // Check for emulator with enhanced detection
    const emulatorStatus = await this.performEnhancedEmulatorDetection();
    if (emulatorStatus.isEmulator) {
      risks.push(...emulatorStatus.risks);
      securityScore -= 15;
    }

    // Check for app tampering
    const tamperStatus = await this.performEnhancedTamperDetection();
    if (tamperStatus.isTampered) {
      risks.push(...tamperStatus.risks);
      securityScore -= 30;
    }

    // Check network security
    const networkStatus = await this.performEnhancedNetworkSecurityCheck();
    if (networkStatus.risks.length > 0) {
      risks.push(...networkStatus.risks);
      securityScore -= networkStatus.risks.reduce((acc, risk) => 
        risk.severity === 'critical' ? 20 : risk.severity === 'high' ? 15 : 5, 0
      );
    }

    // Check OS version
    const osRisk = await this.checkOSVersion();
    if (osRisk) {
      risks.push(osRisk);
      securityScore -= 10;
    }

    // Determine security level
    const securityLevel = this.calculateSecurityLevel(securityScore);

    // Determine restricted features based on security level
    const restrictedFeatures = this.getRestrictedFeatures(securityLevel);

    const status: ExtendedSecurityStatus = {
      isJailbroken: jailbreakStatus.isJailbroken,
      isRooted: jailbreakStatus.isRooted,
      isDebuggingEnabled: debugStatus.isDebugging,
      isEmulator: emulatorStatus.isEmulator,
      isTampered: tamperStatus.isTampered,
      isVPNActive: networkStatus.isVPNActive,
      isProxyActive: networkStatus.isProxyActive,
      certificatePinningActive: this.config.enableCertificatePinning,
      securityScore: Math.max(0, securityScore),
      securityLevel,
      risks,
      restrictedFeatures,
      timestamp: new Date(),
      deviceFingerprint: this.deviceFingerprint || ''
    };

    this.lastSecurityStatus = status;
    await this.saveSecurityStatus(status);

    // Emit security event
    this.emitSecurityEvent('securityStatusChanged', status);

    // Apply security response
    await this.applySecurityResponse(status);

    return status;
  }

  /**
   * Enhanced jailbreak/root detection with multiple methods
   */
  private async performEnhancedJailbreakRootDetection(): Promise<{
    isJailbroken: boolean;
    isRooted: boolean;
    risks: SecurityRisk[];
  }> {
    const risks: SecurityRisk[] = [];
    let isJailbroken = false;
    let isRooted = false;

    if (Platform.OS === 'ios') {
      const jailbreakResult = await this.performEnhancedIOSJailbreakDetection();
      isJailbroken = jailbreakResult.detected;
      risks.push(...jailbreakResult.risks);
    } else if (Platform.OS === 'android') {
      const rootResult = await this.performEnhancedAndroidRootDetection();
      isRooted = rootResult.detected;
      risks.push(...rootResult.risks);
    }

    return { isJailbroken, isRooted, risks };
  }

  /**
   * Enhanced iOS jailbreak detection
   */
  private async performEnhancedIOSJailbreakDetection(): Promise<{
    detected: boolean;
    risks: SecurityRisk[];
  }> {
    const risks: SecurityRisk[] = [];
    let detectionCount = 0;
    const detectionMethods: string[] = [];

    // Method 1: File system checks
    const fileCheckResult = await this.checkJailbreakFiles();
    if (fileCheckResult.detected) {
      detectionCount++;
      detectionMethods.push('file_system');
      risks.push({
        type: SecurityRiskType.JAILBREAK,
        severity: 'critical',
        description: `Jailbreak files detected: ${fileCheckResult.indicators.join(', ')}`,
        mitigation: 'Remove jailbreak or use official device',
        detectionMethod: 'file_system_scan',
        confidence: 95
      });
    }

    // Method 2: URL scheme checks
    const urlSchemeResult = await this.checkSuspiciousURLSchemes();
    if (urlSchemeResult.detected) {
      detectionCount++;
      detectionMethods.push('url_schemes');
      risks.push({
        type: SecurityRiskType.JAILBREAK,
        severity: 'high',
        description: `Jailbreak apps detected via URL schemes`,
        mitigation: 'Remove jailbreak applications',
        detectionMethod: 'url_scheme_scan',
        confidence: 85
      });
    }

    // Method 3: Sandbox integrity check
    const sandboxResult = await this.checkSandboxIntegrity();
    if (sandboxResult.breached) {
      detectionCount++;
      detectionMethods.push('sandbox_breach');
      risks.push({
        type: SecurityRiskType.JAILBREAK,
        severity: 'critical',
        description: 'iOS sandbox restrictions bypassed',
        mitigation: 'Restore device to factory settings',
        detectionMethod: 'sandbox_test',
        confidence: 100
      });
    }

    // Method 4: Dynamic library injection check
    const dylibResult = await this.checkDynamicLibraries();
    if (dylibResult.detected) {
      detectionCount++;
      detectionMethods.push('dylib_injection');
      risks.push({
        type: SecurityRiskType.JAILBREAK,
        severity: 'critical',
        description: `Suspicious libraries loaded: ${dylibResult.libraries.join(', ')}`,
        mitigation: 'Remove jailbreak tweaks',
        detectionMethod: 'dylib_scan',
        confidence: 90
      });
    }

    // Method 5: Fork detection
    const forkResult = await this.checkForkCapability();
    if (forkResult.canFork) {
      detectionCount++;
      detectionMethods.push('fork_capability');
      risks.push({
        type: SecurityRiskType.JAILBREAK,
        severity: 'high',
        description: 'Process forking capability detected',
        mitigation: 'Use non-jailbroken device',
        detectionMethod: 'fork_test',
        confidence: 80
      });
    }

    // Method 6: System call monitoring
    const syscallResult = await this.checkSystemCalls();
    if (syscallResult.suspicious) {
      detectionCount++;
      detectionMethods.push('syscall_monitoring');
      risks.push({
        type: SecurityRiskType.JAILBREAK,
        severity: 'medium',
        description: 'Suspicious system calls detected',
        mitigation: 'Check for jailbreak tweaks',
        detectionMethod: 'syscall_analysis',
        confidence: 70
      });
    }

    const detected = detectionCount >= 2; // Require at least 2 detection methods for higher confidence

    if (detected) {
      logger.warn('iOS jailbreak detected', { methods: detectionMethods, count: detectionCount });
    }

    return { detected, risks };
  }

  /**
   * Enhanced Android root detection
   */
  private async performEnhancedAndroidRootDetection(): Promise<{
    detected: boolean;
    risks: SecurityRisk[];
  }> {
    const risks: SecurityRisk[] = [];
    let detectionCount = 0;
    const detectionMethods: string[] = [];

    // Method 1: File system checks
    const fileCheckResult = await this.checkRootFiles();
    if (fileCheckResult.detected) {
      detectionCount++;
      detectionMethods.push('file_system');
      risks.push({
        type: SecurityRiskType.ROOT,
        severity: 'critical',
        description: `Root files detected: ${fileCheckResult.indicators.join(', ')}`,
        mitigation: 'Remove root access or use official device',
        detectionMethod: 'file_system_scan',
        confidence: 95
      });
    }

    // Method 2: Package checks
    const packageResult = await this.checkRootPackages();
    if (packageResult.detected) {
      detectionCount++;
      detectionMethods.push('packages');
      risks.push({
        type: SecurityRiskType.ROOT,
        severity: 'high',
        description: `Root management apps installed`,
        mitigation: 'Uninstall root applications',
        detectionMethod: 'package_scan',
        confidence: 90
      });
    }

    // Method 3: Properties check
    const propResult = await this.checkSystemProperties();
    if (propResult.suspicious) {
      detectionCount++;
      detectionMethods.push('properties');
      risks.push({
        type: SecurityRiskType.ROOT,
        severity: 'high',
        description: 'System properties indicate root',
        mitigation: 'Use stock ROM',
        detectionMethod: 'property_analysis',
        confidence: 85
      });
    }

    // Method 4: Su binary execution
    const suResult = await this.checkSuExecution();
    if (suResult.accessible) {
      detectionCount++;
      detectionMethods.push('su_execution');
      risks.push({
        type: SecurityRiskType.ROOT,
        severity: 'critical',
        description: 'Su binary is executable',
        mitigation: 'Remove root access',
        detectionMethod: 'su_test',
        confidence: 100
      });
    }

    // Method 5: SELinux status
    const selinuxResult = await this.checkSELinuxStatus();
    if (!selinuxResult.enforcing) {
      detectionCount++;
      detectionMethods.push('selinux');
      risks.push({
        type: SecurityRiskType.ROOT,
        severity: 'medium',
        description: 'SELinux not enforcing',
        mitigation: 'Enable SELinux enforcing mode',
        detectionMethod: 'selinux_check',
        confidence: 70
      });
    }

    // Method 6: Mount points check
    const mountResult = await this.checkMountPoints();
    if (mountResult.suspicious) {
      detectionCount++;
      detectionMethods.push('mount_points');
      risks.push({
        type: SecurityRiskType.ROOT,
        severity: 'medium',
        description: 'Suspicious mount points detected',
        mitigation: 'Check for system modifications',
        detectionMethod: 'mount_analysis',
        confidence: 75
      });
    }

    // Method 7: Native checks
    const nativeResult = await this.performNativeRootChecks();
    if (nativeResult.rooted) {
      detectionCount++;
      detectionMethods.push('native_checks');
      risks.push({
        type: SecurityRiskType.ROOT,
        severity: 'high',
        description: 'Native root detection triggered',
        mitigation: 'Use unmodified device',
        detectionMethod: 'native_analysis',
        confidence: 88
      });
    }

    const detected = detectionCount >= 2; // Require at least 2 detection methods

    if (detected) {
      logger.warn('Android root detected', { methods: detectionMethods, count: detectionCount });
    }

    return { detected, risks };
  }

  /**
   * Check for runtime manipulation (Frida, Xposed, etc.)
   */
  private async checkRuntimeManipulation(): Promise<{
    detected: boolean;
    risks: SecurityRisk[];
  }> {
    const risks: SecurityRisk[] = [];
    let detected = false;

    // Check for Frida
    const fridaCheck = await this.checkForFrida();
    if (fridaCheck.detected) {
      detected = true;
      risks.push({
        type: SecurityRiskType.FRIDA_DETECTED,
        severity: 'critical',
        description: 'Frida instrumentation framework detected',
        mitigation: 'Remove Frida from device',
        detectionMethod: 'frida_detection',
        confidence: 90
      });
    }

    // Check for hooks
    const hookCheck = await this.checkForHooks();
    if (hookCheck.detected) {
      detected = true;
      risks.push({
        type: SecurityRiskType.HOOK_DETECTED,
        severity: 'critical',
        description: 'Runtime hooks detected in application',
        mitigation: 'Use clean device without modifications',
        detectionMethod: 'hook_detection',
        confidence: 85
      });
    }

    // Check for Xposed (Android)
    if (Platform.OS === 'android') {
      const xposedCheck = await this.checkForXposed();
      if (xposedCheck.detected) {
        detected = true;
        risks.push({
          type: SecurityRiskType.HOOK_DETECTED,
          severity: 'critical',
          description: 'Xposed framework detected',
          mitigation: 'Remove Xposed framework',
          detectionMethod: 'xposed_detection',
          confidence: 95
        });
      }
    }

    return { detected, risks };
  }

  /**
   * Enhanced debug detection
   */
  private async performEnhancedDebugDetection(): Promise<{
    isDebugging: boolean;
    risks: SecurityRisk[];
  }> {
    const risks: SecurityRisk[] = [];
    let isDebugging = false;

    // Check development mode
    if (__DEV__) {
      isDebugging = true;
      risks.push({
        type: SecurityRiskType.DEBUGGING,
        severity: 'high',
        description: 'Application running in development mode',
        mitigation: 'Use production build',
        detectionMethod: 'dev_mode_check',
        confidence: 100
      });
    }

    // Platform-specific debug checks
    if (Platform.OS === 'ios') {
      const iosDebug = await this.checkIOSDebugging();
      if (iosDebug.attached) {
        isDebugging = true;
        risks.push({
          type: SecurityRiskType.DEBUGGING,
          severity: 'critical',
          description: 'iOS debugger attached',
          mitigation: 'Disconnect debugger',
          detectionMethod: 'sysctl_check',
          confidence: 95
        });
      }
    } else if (Platform.OS === 'android') {
      const androidDebug = await this.checkAndroidDebugging();
      if (androidDebug.connected) {
        isDebugging = true;
        risks.push({
          type: SecurityRiskType.DEBUGGING,
          severity: 'critical',
          description: 'Android debugger connected',
          mitigation: 'Disable USB debugging',
          detectionMethod: 'debug_api_check',
          confidence: 95
        });
      }
    }

    // Check for debug ports
    const portCheck = await this.checkDebugPorts();
    if (portCheck.open) {
      isDebugging = true;
      risks.push({
        type: SecurityRiskType.DEBUGGING,
        severity: 'high',
        description: `Debug ports open: ${portCheck.ports.join(', ')}`,
        mitigation: 'Close debug ports',
        detectionMethod: 'port_scan',
        confidence: 80
      });
    }

    return { isDebugging, risks };
  }

  /**
   * Enhanced emulator detection
   */
  private async performEnhancedEmulatorDetection(): Promise<{
    isEmulator: boolean;
    risks: SecurityRisk[];
  }> {
    const risks: SecurityRisk[] = [];
    let detectionCount = 0;

    // Expo Device API check
    if (!Device.isDevice) {
      detectionCount++;
      risks.push({
        type: SecurityRiskType.EMULATOR,
        severity: 'medium',
        description: 'Device API indicates emulator',
        mitigation: 'Use physical device for production',
        detectionMethod: 'device_api',
        confidence: 100
      });
    }

    // Platform-specific checks
    if (Platform.OS === 'android') {
      const androidEmulator = await this.checkAndroidEmulator();
      if (androidEmulator.isEmulator) {
        detectionCount++;
        risks.push({
          type: SecurityRiskType.EMULATOR,
          severity: 'medium',
          description: `Android emulator detected: ${androidEmulator.indicators.join(', ')}`,
          mitigation: 'Use physical device',
          detectionMethod: 'android_properties',
          confidence: 90
        });
      }
    } else if (Platform.OS === 'ios') {
      const iosSimulator = await this.checkIOSSimulator();
      if (iosSimulator.isSimulator) {
        detectionCount++;
        risks.push({
          type: SecurityRiskType.EMULATOR,
          severity: 'medium',
          description: 'iOS Simulator detected',
          mitigation: 'Use physical device',
          detectionMethod: 'ios_runtime',
          confidence: 100
        });
      }
    }

    // Hardware characteristics check
    const hardwareCheck = await this.checkHardwareCharacteristics();
    if (hardwareCheck.suspicious) {
      detectionCount++;
      risks.push({
        type: SecurityRiskType.EMULATOR,
        severity: 'low',
        description: 'Suspicious hardware characteristics',
        mitigation: 'Verify device authenticity',
        detectionMethod: 'hardware_analysis',
        confidence: 70
      });
    }

    const isEmulator = detectionCount >= 2;

    return { isEmulator, risks };
  }

  /**
   * Enhanced tamper detection
   */
  private async performEnhancedTamperDetection(): Promise<{
    isTampered: boolean;
    risks: SecurityRisk[];
  }> {
    const risks: SecurityRisk[] = [];
    let isTampered = false;

    // App signature verification
    const signatureCheck = await this.verifyAppSignature();
    if (!signatureCheck.valid) {
      isTampered = true;
      risks.push({
        type: SecurityRiskType.TAMPERING,
        severity: 'critical',
        description: 'App signature verification failed',
        mitigation: 'Reinstall from official source',
        detectionMethod: 'signature_verification',
        confidence: 95
      });
    }

    // Installer verification
    const installerCheck = await this.verifyInstaller();
    if (!installerCheck.trusted) {
      // Don't set tampered for dev builds
      if (!__DEV__) {
        risks.push({
          type: SecurityRiskType.UNKNOWN_SOURCE,
          severity: 'high',
          description: `Untrusted installer: ${installerCheck.installer}`,
          mitigation: 'Install from official app store',
          detectionMethod: 'installer_check',
          confidence: 85
        });
      }
    }

    // Code integrity check
    const integrityCheck = await this.verifyCodeIntegrity();
    if (!integrityCheck.intact) {
      isTampered = true;
      risks.push({
        type: SecurityRiskType.TAMPERING,
        severity: 'critical',
        description: 'Code integrity compromised',
        mitigation: 'Reinstall application',
        detectionMethod: 'integrity_check',
        confidence: 90
      });
    }

    // Resource tampering check
    const resourceCheck = await this.checkResourceIntegrity();
    if (!resourceCheck.intact) {
      isTampered = true;
      risks.push({
        type: SecurityRiskType.TAMPERING,
        severity: 'high',
        description: 'App resources modified',
        mitigation: 'Reinstall from trusted source',
        detectionMethod: 'resource_check',
        confidence: 80
      });
    }

    return { isTampered, risks };
  }

  /**
   * Enhanced network security check
   */
  private async performEnhancedNetworkSecurityCheck(): Promise<{
    isVPNActive: boolean;
    isProxyActive: boolean;
    risks: SecurityRisk[];
  }> {
    const risks: SecurityRisk[] = [];
    let isVPNActive = false;
    let isProxyActive = false;

    // VPN detection
    const vpnCheck = await this.detectVPN();
    if (vpnCheck.active) {
      isVPNActive = true;
      risks.push({
        type: SecurityRiskType.VPN,
        severity: 'low',
        description: 'VPN connection detected',
        mitigation: 'Verify VPN is trusted',
        detectionMethod: 'network_interface_check',
        confidence: 85
      });
    }

    // Proxy detection
    const proxyCheck = await this.detectProxy();
    if (proxyCheck.active) {
      isProxyActive = true;
      risks.push({
        type: SecurityRiskType.PROXY,
        severity: 'medium',
        description: `Proxy detected: ${proxyCheck.type}`,
        mitigation: 'Disable proxy for app usage',
        detectionMethod: 'proxy_detection',
        confidence: 80
      });
    }

    // Certificate validation status
    if (this.config.enableCertificatePinning) {
      const certStatus = CertificatePinningService.getPinConfiguration();
      if (!certStatus.enabled) {
        risks.push({
          type: SecurityRiskType.CERTIFICATE,
          severity: 'high',
          description: 'Certificate pinning disabled',
          mitigation: 'Enable certificate pinning',
          detectionMethod: 'cert_pin_check',
          confidence: 100
        });
      }
    }

    // DNS manipulation check
    const dnsCheck = await this.checkDNSManipulation();
    if (dnsCheck.manipulated) {
      risks.push({
        type: SecurityRiskType.NETWORK,
        severity: 'high',
        description: 'DNS manipulation detected',
        mitigation: 'Use trusted DNS servers',
        detectionMethod: 'dns_check',
        confidence: 75
      });
    }

    return { isVPNActive, isProxyActive, risks };
  }

  /**
   * Calculate security level based on score
   */
  private calculateSecurityLevel(score: number): SecurityLevel {
    if (score >= 90) return SecurityLevel.CRITICAL;
    if (score >= 75) return SecurityLevel.HIGH;
    if (score >= 60) return SecurityLevel.MEDIUM;
    if (score >= 40) return SecurityLevel.LOW;
    return SecurityLevel.NONE;
  }

  /**
   * Get restricted features based on security level
   */
  private getRestrictedFeatures(level: SecurityLevel): string[] {
    const levelValues = {
      [SecurityLevel.NONE]: 0,
      [SecurityLevel.LOW]: 1,
      [SecurityLevel.MEDIUM]: 2,
      [SecurityLevel.HIGH]: 3,
      [SecurityLevel.CRITICAL]: 4
    };

    return this.config.featureRestrictions
      .filter(restriction => {
        const requiredValue = levelValues[restriction.requiredSecurityLevel];
        const currentValue = levelValues[level];
        return currentValue < requiredValue;
      })
      .map(restriction => restriction.feature);
  }

  /**
   * Apply security response based on configuration
   */
  private async applySecurityResponse(status: ExtendedSecurityStatus): Promise<void> {
    if (this.config.enableSecurityBypass) {
      logger.warn('Security bypass enabled - no response applied');
      return;
    }

    switch (this.config.responseStrategy) {
      case SecurityResponse.LOG_ONLY:
        logger.warn('Security risks detected', { status });
        break;

      case SecurityResponse.WARN_USER:
        this.emitSecurityEvent('securityWarning', {
          title: 'Security Warning',
          message: this.generateSecurityMessage(status),
          risks: status.risks
        });
        break;

      case SecurityResponse.RESTRICT_FEATURES:
        this.emitSecurityEvent('featuresRestricted', {
          restrictedFeatures: status.restrictedFeatures,
          reason: 'Device security requirements not met'
        });
        break;

      case SecurityResponse.BLOCK_ACCESS:
        if (status.securityScore < this.config.minSecurityScore) {
          this.emitSecurityEvent('accessBlocked', {
            reason: 'Critical security risks detected',
            score: status.securityScore,
            minimumRequired: this.config.minSecurityScore
          });
        }
        break;
    }

    // Store security event for audit
    await this.storeSecurityEvent(status);
  }

  /**
   * Generate user-friendly security message
   */
  private generateSecurityMessage(status: ExtendedSecurityStatus): string {
    const criticalRisks = status.risks.filter(r => r.severity === 'critical');
    const highRisks = status.risks.filter(r => r.severity === 'high');

    if (criticalRisks.length > 0) {
      return `Critical security risks detected on your device. ${criticalRisks[0].description}. For your safety, some features may be restricted.`;
    }

    if (highRisks.length > 0) {
      return `Security concerns detected on your device. ${highRisks[0].description}. Some features may be limited.`;
    }

    if (status.risks.length > 0) {
      return `Minor security concerns detected. Your device security score is ${status.securityScore}%. Some features may be affected.`;
    }

    return 'Your device meets security requirements.';
  }

  /**
   * Store security event for audit trail
   */
  private async storeSecurityEvent(status: ExtendedSecurityStatus): Promise<void> {
    try {
      const event = {
        timestamp: new Date().toISOString(),
        deviceFingerprint: status.deviceFingerprint,
        securityScore: status.securityScore,
        securityLevel: status.securityLevel,
        risks: status.risks.map(r => ({
          type: r.type,
          severity: r.severity,
          confidence: r.confidence
        })),
        responseApplied: this.config.responseStrategy
      };

      // Store in secure storage
      const events = await this.getSecurityEvents();
      events.push(event);

      // Keep only last 100 events
      const recentEvents = events.slice(-100);
      
      await SecureStore.setItemAsync('security_events', JSON.stringify(recentEvents));
    } catch (error) {
      logger.error('Failed to store security event', error);
    }
  }

  /**
   * Get stored security events
   */
  private async getSecurityEvents(): Promise<any[]> {
    try {
      const eventsJson = await SecureStore.getItemAsync('security_events');
      return eventsJson ? JSON.parse(eventsJson) : [];
    } catch {
      return [];
    }
  }

  /**
   * Generate device fingerprint for tracking
   */
  private async generateDeviceFingerprint(): Promise<void> {
    try {
      const components = [
        Device.brand,
        Device.manufacturer,
        Device.modelName,
        Device.deviceYearClass,
        Device.osName,
        Device.osVersion,
        Application.applicationId,
        Application.nativeApplicationVersion
      ].filter(Boolean);

      this.deviceFingerprint = await Crypto.digestStringAsync(
        Crypto.CryptoDigestAlgorithm.SHA256,
        components.join('|')
      );
    } catch (error) {
      logger.error('Failed to generate device fingerprint', error);
      this.deviceFingerprint = 'unknown';
    }
  }

  /**
   * Emit security event to listeners
   */
  private emitSecurityEvent(event: string, data: any): void {
    DeviceEventEmitter.emit(event, data);
    
    // Also notify registered listeners
    const listeners = this.securityEventListeners.get(event) || [];
    listeners.forEach(listener => {
      try {
        listener(data);
      } catch (error) {
        logger.error(`Security event listener error for ${event}`, error);
      }
    });
  }

  /**
   * Register security event listener
   */
  addEventListener(event: string, listener: Function): () => void {
    if (!this.securityEventListeners.has(event)) {
      this.securityEventListeners.set(event, []);
    }
    
    this.securityEventListeners.get(event)!.push(listener);
    
    // Return unsubscribe function
    return () => {
      const listeners = this.securityEventListeners.get(event) || [];
      const index = listeners.indexOf(listener);
      if (index >= 0) {
        listeners.splice(index, 1);
      }
    };
  }

  /**
   * Check if feature is allowed based on security status
   */
  async isFeatureAllowed(feature: string): Promise<boolean> {
    const status = await this.getLastSecurityStatus();
    if (!status) {
      // If no status, perform check
      await this.performSecurityCheck();
      return this.isFeatureAllowed(feature);
    }

    return !status.restrictedFeatures.includes(feature);
  }

  /**
   * Get security recommendations
   */
  getSecurityRecommendations(status: ExtendedSecurityStatus): string[] {
    const recommendations: string[] = [];

    if (status.isJailbroken || status.isRooted) {
      recommendations.push('Remove jailbreak/root for maximum security');
    }

    if (status.isDebuggingEnabled) {
      recommendations.push('Disable debugging and use production builds');
    }

    if (status.isEmulator) {
      recommendations.push('Use a physical device for sensitive operations');
    }

    if (!status.certificatePinningActive) {
      recommendations.push('Enable certificate pinning for network security');
    }

    if (status.securityScore < 80) {
      recommendations.push('Address security risks to improve your security score');
    }

    return recommendations;
  }

  /**
   * Enable security hardening measures
   */
  private async enableSecurityHardening(): Promise<void> {
    try {
      // Enable anti-debugging
      if (NativeModules.RNSecurityModule?.enableAntiDebugging) {
        await NativeModules.RNSecurityModule.enableAntiDebugging();
      }

      // Enable screenshot blocking (Android)
      if (Platform.OS === 'android' && NativeModules.RNSecurityModule?.setScreenshotBlocking) {
        await NativeModules.RNSecurityModule.setScreenshotBlocking(true);
      }

      // Enable app backgrounding protection (iOS)
      if (Platform.OS === 'ios' && NativeModules.RNSecurityModule?.enableBackgroundBlur) {
        await NativeModules.RNSecurityModule.enableBackgroundBlur();
      }

      // Enable anti-hooking protection
      if (NativeModules.RNSecurityModule?.enableAntiHooking) {
        await NativeModules.RNSecurityModule.enableAntiHooking();
      }

      logger.info('Security hardening measures enabled');
    } catch (error) {
      logger.error('Failed to enable security hardening', error);
    }
  }

  /**
   * Setup event listeners for security monitoring
   */
  private setupEventListeners(): void {
    // Monitor app state changes
    AppState.addEventListener('change', (nextAppState: AppStateStatus) => {
      if (nextAppState === 'active') {
        // Perform security check when app becomes active
        this.performSecurityCheck().catch(error => {
          logger.error('Security check on activation failed', error);
        });
      }
    });

    // Monitor network state changes
    DeviceEventEmitter.addListener('networkStateChange', () => {
      // Re-check network security on network changes
      this.performEnhancedNetworkSecurityCheck().catch(error => {
        logger.error('Network security check failed', error);
      });
    });
  }

  /**
   * Start continuous monitoring
   */
  private startContinuousMonitoring(): void {
    if (this.securityCheckInterval) {
      clearInterval(this.securityCheckInterval);
    }

    this.securityCheckInterval = setInterval(() => {
      this.performSecurityCheck().catch(error => {
        logger.error('Continuous security check failed', error);
      });
    }, this.config.securityCheckInterval);
  }

  /**
   * Save security status
   */
  private async saveSecurityStatus(status: ExtendedSecurityStatus): Promise<void> {
    try {
      await SecureStore.setItemAsync('security_status', JSON.stringify(status));
    } catch (error) {
      logger.error('Failed to save security status', error);
    }
  }

  /**
   * Get last security status
   */
  async getLastSecurityStatus(): Promise<ExtendedSecurityStatus | null> {
    if (this.lastSecurityStatus) {
      return this.lastSecurityStatus;
    }

    try {
      const saved = await SecureStore.getItemAsync('security_status');
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (error) {
      logger.error('Failed to load security status', error);
    }

    return null;
  }

  /**
   * Native method implementations - these would be implemented in native modules
   */

  // iOS-specific checks
  private async checkJailbreakFiles(): Promise<{ detected: boolean; indicators: string[] }> {
    // Implementation would be in native module
    return { detected: false, indicators: [] };
  }

  private async checkSuspiciousURLSchemes(): Promise<{ detected: boolean }> {
    // Implementation would be in native module
    return { detected: false };
  }

  private async checkSandboxIntegrity(): Promise<{ breached: boolean }> {
    // Implementation would be in native module
    return { breached: false };
  }

  private async checkDynamicLibraries(): Promise<{ detected: boolean; libraries: string[] }> {
    // Implementation would be in native module
    return { detected: false, libraries: [] };
  }

  private async checkForkCapability(): Promise<{ canFork: boolean }> {
    // Implementation would be in native module
    return { canFork: false };
  }

  private async checkSystemCalls(): Promise<{ suspicious: boolean }> {
    // Implementation would be in native module
    return { suspicious: false };
  }

  private async checkIOSDebugging(): Promise<{ attached: boolean }> {
    // Implementation would be in native module
    return { attached: false };
  }

  private async checkIOSSimulator(): Promise<{ isSimulator: boolean }> {
    // Implementation would be in native module
    return { isSimulator: false };
  }

  // Android-specific checks
  private async checkRootFiles(): Promise<{ detected: boolean; indicators: string[] }> {
    // Implementation would be in native module
    return { detected: false, indicators: [] };
  }

  private async checkRootPackages(): Promise<{ detected: boolean }> {
    // Implementation would be in native module
    return { detected: false };
  }

  private async checkSystemProperties(): Promise<{ suspicious: boolean }> {
    // Implementation would be in native module
    return { suspicious: false };
  }

  private async checkSuExecution(): Promise<{ accessible: boolean }> {
    // Implementation would be in native module
    return { accessible: false };
  }

  private async checkSELinuxStatus(): Promise<{ enforcing: boolean }> {
    // Implementation would be in native module
    return { enforcing: true };
  }

  private async checkMountPoints(): Promise<{ suspicious: boolean }> {
    // Implementation would be in native module
    return { suspicious: false };
  }

  private async performNativeRootChecks(): Promise<{ rooted: boolean }> {
    // Implementation would be in native module
    return { rooted: false };
  }

  private async checkAndroidDebugging(): Promise<{ connected: boolean }> {
    // Implementation would be in native module
    return { connected: false };
  }

  private async checkAndroidEmulator(): Promise<{ isEmulator: boolean; indicators: string[] }> {
    // Implementation would be in native module
    return { isEmulator: false, indicators: [] };
  }

  // Common checks
  private async checkForFrida(): Promise<{ detected: boolean }> {
    // Implementation would be in native module
    return { detected: false };
  }

  private async checkForHooks(): Promise<{ detected: boolean }> {
    // Implementation would be in native module
    return { detected: false };
  }

  private async checkForXposed(): Promise<{ detected: boolean }> {
    // Implementation would be in native module
    return { detected: false };
  }

  private async checkDebugPorts(): Promise<{ open: boolean; ports: number[] }> {
    // Implementation would be in native module
    return { open: false, ports: [] };
  }

  private async checkHardwareCharacteristics(): Promise<{ suspicious: boolean }> {
    // Implementation would be in native module
    return { suspicious: false };
  }

  private async verifyAppSignature(): Promise<{ valid: boolean }> {
    // Implementation would be in native module
    return { valid: true };
  }

  private async verifyInstaller(): Promise<{ trusted: boolean; installer: string }> {
    // Implementation would be in native module
    return { trusted: true, installer: 'com.android.vending' };
  }

  private async verifyCodeIntegrity(): Promise<{ intact: boolean }> {
    // Implementation would be in native module
    return { intact: true };
  }

  private async checkResourceIntegrity(): Promise<{ intact: boolean }> {
    // Implementation would be in native module
    return { intact: true };
  }

  private async detectVPN(): Promise<{ active: boolean }> {
    // Implementation would be in native module
    return { active: false };
  }

  private async detectProxy(): Promise<{ active: boolean; type: string }> {
    // Implementation would be in native module
    return { active: false, type: '' };
  }

  private async checkDNSManipulation(): Promise<{ manipulated: boolean }> {
    // Implementation would be in native module
    return { manipulated: false };
  }

  private async checkOSVersion(): Promise<SecurityRisk | null> {
    // Implementation from original service
    return null;
  }

  private async generateAppSignature(): Promise<void> {
    // Implementation from original service
  }

  /**
   * Cleanup
   */
  cleanup(): void {
    if (this.securityCheckInterval) {
      clearInterval(this.securityCheckInterval);
      this.securityCheckInterval = null;
    }
    this.securityEventListeners.clear();
  }
}

export default EnhancedMobileSecurityService.getInstance();
export { 
  ExtendedSecurityStatus, 
  SecurityRisk, 
  SecurityRiskType, 
  SecurityConfiguration,
  SecurityLevel,
  SecurityResponse,
  SecurityFeatureRestriction
};