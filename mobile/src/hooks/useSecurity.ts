/**
 * Security Hook
 * Six Sigma DMAIC - IMPROVE Phase Implementation
 * 
 * React hook for easy security integration in components
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { DeviceEventEmitter } from 'react-native';
import EnhancedMobileSecurityService, {
  ExtendedSecurityStatus,
  SecurityLevel,
  SecurityResponse,
  SecurityRisk
} from '@/services/security/EnhancedMobileSecurityService';
import { secureApiClient } from '@/services/api/SecureApiClient';
import { logger } from '@/services/logger';

interface SecurityState {
  isLoading: boolean;
  isSecure: boolean;
  securityLevel: SecurityLevel;
  securityScore: number;
  risks: SecurityRisk[];
  restrictedFeatures: string[];
  lastCheck: Date | null;
  error: Error | null;
}

interface SecurityActions {
  checkSecurity: () => Promise<void>;
  isFeatureAllowed: (feature: string) => boolean;
  getSecurityMessage: () => string;
  refreshSecurity: () => Promise<void>;
}

interface UseSecurityOptions {
  autoCheck?: boolean;
  checkInterval?: number;
  feature?: string;
  minimumLevel?: SecurityLevel;
  onSecurityChange?: (status: ExtendedSecurityStatus) => void;
  onSecurityWarning?: (warning: any) => void;
  onAccessBlocked?: (reason: any) => void;
}

export const useSecurity = (options: UseSecurityOptions = {}): [SecurityState, SecurityActions] => {
  const {
    autoCheck = true,
    checkInterval = 5 * 60 * 1000, // 5 minutes
    feature,
    minimumLevel = SecurityLevel.LOW,
    onSecurityChange,
    onSecurityWarning,
    onAccessBlocked
  } = options;

  const [state, setState] = useState<SecurityState>({
    isLoading: true,
    isSecure: false,
    securityLevel: SecurityLevel.NONE,
    securityScore: 0,
    risks: [],
    restrictedFeatures: [],
    lastCheck: null,
    error: null
  });

  const checkIntervalRef = useRef<NodeJS.Timer | null>(null);
  const listenersRef = useRef<(() => void)[]>([]);

  // Check security status
  const checkSecurity = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      const status = await EnhancedMobileSecurityService.performSecurityCheck();
      
      const levelValues = {
        [SecurityLevel.NONE]: 0,
        [SecurityLevel.LOW]: 1,
        [SecurityLevel.MEDIUM]: 2,
        [SecurityLevel.HIGH]: 3,
        [SecurityLevel.CRITICAL]: 4
      };

      const isSecure = levelValues[status.securityLevel] >= levelValues[minimumLevel];

      setState({
        isLoading: false,
        isSecure,
        securityLevel: status.securityLevel,
        securityScore: status.securityScore,
        risks: status.risks,
        restrictedFeatures: status.restrictedFeatures,
        lastCheck: new Date(),
        error: null
      });

      // Notify listeners
      onSecurityChange?.(status);

      // Check if current feature is restricted
      if (feature && status.restrictedFeatures.includes(feature)) {
        logger.warn(`Feature '${feature}' is restricted due to security`);
      }

      return status;
    } catch (error) {
      logger.error('Security check failed', error);
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error as Error
      }));
      throw error;
    }
  }, [feature, minimumLevel, onSecurityChange]);

  // Check if feature is allowed
  const isFeatureAllowed = useCallback((featureName: string): boolean => {
    return !state.restrictedFeatures.includes(featureName);
  }, [state.restrictedFeatures]);

  // Get user-friendly security message
  const getSecurityMessage = useCallback((): string => {
    if (state.isSecure) {
      return 'Your device meets security requirements';
    }

    const criticalRisks = state.risks.filter(r => r.severity === 'critical');
    if (criticalRisks.length > 0) {
      return `Critical security issue: ${criticalRisks[0].description}`;
    }

    const highRisks = state.risks.filter(r => r.severity === 'high');
    if (highRisks.length > 0) {
      return `Security concern: ${highRisks[0].description}`;
    }

    return `Device security score: ${state.securityScore}%`;
  }, [state]);

  // Force refresh security status
  const refreshSecurity = useCallback(async () => {
    await checkSecurity();
  }, [checkSecurity]);

  // Setup event listeners
  useEffect(() => {
    const listeners: (() => void)[] = [];

    // Security status change listener
    const statusListener = DeviceEventEmitter.addListener(
      'securityStatusChanged',
      (status: ExtendedSecurityStatus) => {
        const levelValues = {
          [SecurityLevel.NONE]: 0,
          [SecurityLevel.LOW]: 1,
          [SecurityLevel.MEDIUM]: 2,
          [SecurityLevel.HIGH]: 3,
          [SecurityLevel.CRITICAL]: 4
        };

        const isSecure = levelValues[status.securityLevel] >= levelValues[minimumLevel];

        setState({
          isLoading: false,
          isSecure,
          securityLevel: status.securityLevel,
          securityScore: status.securityScore,
          risks: status.risks,
          restrictedFeatures: status.restrictedFeatures,
          lastCheck: new Date(status.timestamp),
          error: null
        });

        onSecurityChange?.(status);
      }
    );
    listeners.push(() => statusListener.remove());

    // Security warning listener
    if (onSecurityWarning) {
      const warningListener = DeviceEventEmitter.addListener(
        'securityWarning',
        onSecurityWarning
      );
      listeners.push(() => warningListener.remove());
    }

    // Access blocked listener
    if (onAccessBlocked) {
      const blockedListener = DeviceEventEmitter.addListener(
        'accessBlocked',
        onAccessBlocked
      );
      listeners.push(() => blockedListener.remove());
    }

    // Feature restriction listener
    const restrictionListener = DeviceEventEmitter.addListener(
      'featuresRestricted',
      (data: any) => {
        setState(prev => ({
          ...prev,
          restrictedFeatures: data.restrictedFeatures || []
        }));
      }
    );
    listeners.push(() => restrictionListener.remove());

    listenersRef.current = listeners;

    return () => {
      listeners.forEach(cleanup => cleanup());
    };
  }, [minimumLevel, onSecurityChange, onSecurityWarning, onAccessBlocked]);

  // Auto-check on mount and interval
  useEffect(() => {
    if (autoCheck) {
      // Initial check
      checkSecurity();

      // Setup interval
      if (checkInterval > 0) {
        checkIntervalRef.current = setInterval(() => {
          checkSecurity();
        }, checkInterval);
      }
    }

    return () => {
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
        checkIntervalRef.current = null;
      }
    };
  }, [autoCheck, checkInterval, checkSecurity]);

  const actions: SecurityActions = {
    checkSecurity,
    isFeatureAllowed,
    getSecurityMessage,
    refreshSecurity
  };

  return [state, actions];
};

// Specialized hooks for common use cases

/**
 * Hook for payment features requiring high security
 */
export const usePaymentSecurity = () => {
  const [state, actions] = useSecurity({
    minimumLevel: SecurityLevel.HIGH,
    feature: 'payment'
  });

  return {
    canProcessPayment: state.isSecure && actions.isFeatureAllowed('payment'),
    securityState: state,
    ...actions
  };
};

/**
 * Hook for biometric authentication
 */
export const useBiometricSecurity = () => {
  const [state, actions] = useSecurity({
    minimumLevel: SecurityLevel.HIGH,
    feature: 'biometric_auth'
  });

  return {
    canUseBiometrics: state.isSecure && actions.isFeatureAllowed('biometric_auth'),
    securityState: state,
    ...actions
  };
};

/**
 * Hook for voice commands
 */
export const useVoiceSecurity = () => {
  const [state, actions] = useSecurity({
    minimumLevel: SecurityLevel.LOW,
    feature: 'voice_commands'
  });

  return {
    canUseVoice: actions.isFeatureAllowed('voice_commands'),
    isRestricted: !actions.isFeatureAllowed('voice_commands'),
    securityState: state,
    ...actions
  };
};

/**
 * Hook for checking API access
 */
export const useApiSecurity = (endpoint?: string) => {
  const [isAccessible, setIsAccessible] = useState(true);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkAccess = async () => {
      setIsChecking(true);
      try {
        const accessible = await secureApiClient.isApiAccessible(endpoint);
        setIsAccessible(accessible);
      } catch (error) {
        logger.error('API security check failed', error);
        setIsAccessible(false);
      } finally {
        setIsChecking(false);
      }
    };

    checkAccess();

    // Re-check on security status changes
    const listener = DeviceEventEmitter.addListener(
      'securityStatusChanged',
      () => {
        checkAccess();
      }
    );

    return () => listener.remove();
  }, [endpoint]);

  return { isAccessible, isChecking };
};

/**
 * Hook for security recommendations
 */
export const useSecurityRecommendations = () => {
  const [recommendations, setRecommendations] = useState<string[]>([]);
  const [state] = useSecurity();

  useEffect(() => {
    const loadRecommendations = async () => {
      try {
        const status = await EnhancedMobileSecurityService.getLastSecurityStatus();
        if (status) {
          const recs = EnhancedMobileSecurityService.getSecurityRecommendations(status);
          setRecommendations(recs);
        }
      } catch (error) {
        logger.error('Failed to load security recommendations', error);
      }
    };

    loadRecommendations();
  }, [state.lastCheck]);

  return recommendations;
};

export default useSecurity;