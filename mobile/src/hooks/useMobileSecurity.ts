/**
 * Mobile Security Hook
 * React hook for mobile security features
 */

import { useState, useEffect, useCallback } from 'react';
import { DeviceEventEmitter, Alert, Platform } from 'react-native';
import mobileSecurityService, {
  SecurityStatus,
  SecurityRisk,
  SecurityRiskType,
  SecurityConfig
} from '../services/mobileSecurityService';
import { logger } from '../services/logger';

interface UseMobileSecurityOptions {
  enableAutoCheck?: boolean;
  checkInterval?: number;
  showAlerts?: boolean;
  config?: Partial<SecurityConfig>;
}

interface UseMobileSecurityReturn {
  securityStatus: SecurityStatus | null;
  isSecure: boolean;
  isChecking: boolean;
  risks: SecurityRisk[];
  checkSecurity: () => Promise<void>;
  enableHardening: () => Promise<void>;
  acknowledgeRisk: (riskType: SecurityRiskType) => void;
}

const DEFAULT_OPTIONS: UseMobileSecurityOptions = {
  enableAutoCheck: true,
  checkInterval: 300000, // 5 minutes
  showAlerts: true
};

export function useMobileSecurity(options: UseMobileSecurityOptions = {}): UseMobileSecurityReturn {
  const mergedOptions = { ...DEFAULT_OPTIONS, ...options };
  
  const [securityStatus, setSecurityStatus] = useState<SecurityStatus | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const [acknowledgedRisks, setAcknowledgedRisks] = useState<Set<SecurityRiskType>>(new Set());

  // Initialize security service
  useEffect(() => {
    const initializeSecurity = async () => {
      try {
        await mobileSecurityService.initialize(mergedOptions.config);
        
        // Load last security status
        const lastStatus = await mobileSecurityService.getLastSecurityStatus();
        if (lastStatus) {
          setSecurityStatus(lastStatus);
        }
        
        // Perform initial check if enabled
        if (mergedOptions.enableAutoCheck) {
          await checkSecurity();
        }
      } catch (error) {
        logger.error('Failed to initialize mobile security', error);
      }
    };

    initializeSecurity();

    // Cleanup
    return () => {
      mobileSecurityService.cleanup();
    };
  }, []);

  // Subscribe to security events
  useEffect(() => {
    const subscription = DeviceEventEmitter.addListener('securityStatusChanged', (status: SecurityStatus) => {
      setSecurityStatus(status);
      
      // Show alerts for new critical risks
      if (mergedOptions.showAlerts) {
        const criticalRisks = status.risks.filter(
          risk => risk.severity === 'critical' && !acknowledgedRisks.has(risk.type)
        );
        
        if (criticalRisks.length > 0) {
          showSecurityAlert(criticalRisks[0]);
        }
      }
    });

    const highRiskSubscription = DeviceEventEmitter.addListener('highRiskDevice', (status: SecurityStatus) => {
      if (mergedOptions.showAlerts) {
        Alert.alert(
          '⚠️ Security Warning',
          'Your device has been identified as high risk. Some features may be restricted for your protection.',
          [
            {
              text: 'View Details',
              onPress: () => showSecurityDetails(status)
            },
            {
              text: 'OK',
              style: 'cancel'
            }
          ]
        );
      }
    });

    return () => {
      subscription.remove();
      highRiskSubscription.remove();
    };
  }, [acknowledgedRisks, mergedOptions.showAlerts]);

  // Auto-check timer
  useEffect(() => {
    if (!mergedOptions.enableAutoCheck || !mergedOptions.checkInterval) {
      return;
    }

    const interval = setInterval(() => {
      checkSecurity().catch(error => {
        logger.error('Auto security check failed', error);
      });
    }, mergedOptions.checkInterval);

    return () => clearInterval(interval);
  }, [mergedOptions.enableAutoCheck, mergedOptions.checkInterval]);

  // Check security
  const checkSecurity = useCallback(async () => {
    if (isChecking) return;

    setIsChecking(true);
    try {
      const status = await mobileSecurityService.performSecurityCheck();
      setSecurityStatus(status);
    } catch (error) {
      logger.error('Security check failed', error);
    } finally {
      setIsChecking(false);
    }
  }, [isChecking]);

  // Enable security hardening
  const enableHardening = useCallback(async () => {
    try {
      await mobileSecurityService.enableSecurityHardening();
      
      if (mergedOptions.showAlerts) {
        Alert.alert(
          '✅ Security Hardening',
          'Additional security features have been enabled.',
          [{ text: 'OK' }]
        );
      }
    } catch (error) {
      logger.error('Failed to enable hardening', error);
      
      if (mergedOptions.showAlerts) {
        Alert.alert(
          '❌ Error',
          'Failed to enable security hardening. Some features may not be available.',
          [{ text: 'OK' }]
        );
      }
    }
  }, [mergedOptions.showAlerts]);

  // Acknowledge a risk
  const acknowledgeRisk = useCallback((riskType: SecurityRiskType) => {
    setAcknowledgedRisks(prev => new Set([...prev, riskType]));
  }, []);

  // Show security alert
  const showSecurityAlert = (risk: SecurityRisk) => {
    const titles: Record<SecurityRiskType, string> = {
      [SecurityRiskType.JAILBREAK]: '🚨 Jailbreak Detected',
      [SecurityRiskType.ROOT]: '🚨 Root Detected',
      [SecurityRiskType.DEBUGGING]: '⚠️ Debugging Enabled',
      [SecurityRiskType.EMULATOR]: '⚠️ Emulator Detected',
      [SecurityRiskType.TAMPERING]: '🚨 App Tampering Detected',
      [SecurityRiskType.VPN]: 'ℹ️ VPN Detected',
      [SecurityRiskType.NETWORK]: '⚠️ Network Security Issue',
      [SecurityRiskType.OUTDATED_OS]: '⚠️ Outdated OS',
      [SecurityRiskType.UNKNOWN_SOURCE]: '⚠️ Unknown Installation Source'
    };

    Alert.alert(
      titles[risk.type] || 'Security Risk',
      `${risk.description}\n\nRecommendation: ${risk.mitigation}`,
      [
        {
          text: 'Acknowledge',
          onPress: () => acknowledgeRisk(risk.type)
        },
        {
          text: 'Learn More',
          onPress: () => showRiskDetails(risk)
        }
      ]
    );
  };

  // Show security details
  const showSecurityDetails = (status: SecurityStatus) => {
    const details = [
      `Security Score: ${status.securityScore}/100`,
      `Risks Detected: ${status.risks.length}`,
      '',
      'Risk Summary:'
    ];

    status.risks.forEach(risk => {
      details.push(`• ${risk.description} (${risk.severity})`);
    });

    Alert.alert('Security Status', details.join('\n'), [{ text: 'OK' }]);
  };

  // Show risk details
  const showRiskDetails = (risk: SecurityRisk) => {
    const details: Record<SecurityRiskType, string> = {
      [SecurityRiskType.JAILBREAK]: 'Jailbreaking removes iOS security restrictions, making your device vulnerable to malware and data theft.',
      [SecurityRiskType.ROOT]: 'Root access removes Android security restrictions, exposing your device to security threats.',
      [SecurityRiskType.DEBUGGING]: 'Debug mode can expose sensitive information and should be disabled in production.',
      [SecurityRiskType.EMULATOR]: 'Emulators may not have the same security features as physical devices.',
      [SecurityRiskType.TAMPERING]: 'The app has been modified from its original version, which may compromise security.',
      [SecurityRiskType.VPN]: 'VPN connections can interfere with location-based features and network security.',
      [SecurityRiskType.NETWORK]: 'Network security issues can expose your data to interception.',
      [SecurityRiskType.OUTDATED_OS]: 'Older operating systems lack important security updates and features.',
      [SecurityRiskType.UNKNOWN_SOURCE]: 'Apps from unknown sources may contain malware or security vulnerabilities.'
    };

    Alert.alert(
      'About This Risk',
      details[risk.type] || 'This security risk may affect app functionality and data protection.',
      [{ text: 'OK' }]
    );
  };

  return {
    securityStatus,
    isSecure: securityStatus ? securityStatus.securityScore >= 70 : false,
    isChecking,
    risks: securityStatus?.risks || [],
    checkSecurity,
    enableHardening,
    acknowledgeRisk
  };
}

// Security indicator component helper
export interface SecurityIndicatorProps {
  status: SecurityStatus | null;
  compact?: boolean;
}

export function getSecurityIndicator(props: SecurityIndicatorProps): {
  color: string;
  icon: string;
  text: string;
} {
  const { status, compact = false } = props;

  if (!status) {
    return {
      color: '#999',
      icon: '🔍',
      text: compact ? 'Checking...' : 'Checking security...'
    };
  }

  if (status.securityScore >= 90) {
    return {
      color: '#4CAF50',
      icon: '🛡️',
      text: compact ? 'Secure' : 'Device is secure'
    };
  } else if (status.securityScore >= 70) {
    return {
      color: '#FF9800',
      icon: '⚠️',
      text: compact ? 'Caution' : 'Minor security risks'
    };
  } else {
    return {
      color: '#F44336',
      icon: '🚨',
      text: compact ? 'At Risk' : 'Security risks detected'
    };
  }
}