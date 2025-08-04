/**
 * Security Warning Modal Component
 * Six Sigma DMAIC - IMPROVE Phase Implementation
 * 
 * User-friendly security warning display with different severity levels
 */

import React, { useEffect, useState } from 'react';
import { logger } from '@/services/logger';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  DeviceEventEmitter,
  Platform
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import EnhancedMobileSecurityService, { 
  SecurityLevel, 
  SecurityRisk,
  SecurityRiskType 
} from '@/services/security/EnhancedMobileSecurityService';
import { useTheme } from '@/contexts/ThemeContext';

interface SecurityWarningProps {
  visible?: boolean;
  onDismiss?: () => void;
  onSecuritySettings?: () => void;
  allowDismiss?: boolean;
}

interface SecurityWarningData {
  title: string;
  message: string;
  risks: SecurityRisk[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  recommendations?: string[];
}

export const SecurityWarningModal: React.FC<SecurityWarningProps> = ({
  visible: propVisible,
  onDismiss,
  onSecuritySettings,
  allowDismiss = true
}) => {
  const theme = useTheme();
  const [visible, setVisible] = useState(propVisible || false);
  const [warningData, setWarningData] = useState<SecurityWarningData | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // Listen for security warnings
    const warningListener = DeviceEventEmitter.addListener(
      'securityWarning',
      (data: any) => {
        if (!dismissed) {
          setWarningData(data);
          setVisible(true);
        }
      }
    );

    // Listen for access blocked events
    const blockedListener = DeviceEventEmitter.addListener(
      'accessBlocked',
      (data: any) => {
        setWarningData({
          title: 'Access Blocked',
          message: data.reason || 'Your device does not meet minimum security requirements',
          risks: [],
          severity: 'critical',
          recommendations: ['Please address security issues before continuing']
        });
        setVisible(true);
        setDismissed(false); // Can't dismiss critical blocks
      }
    );

    // Listen for feature restrictions
    const restrictionListener = DeviceEventEmitter.addListener(
      'featuresRestricted',
      (data: any) => {
        const features = data.restrictedFeatures || [];
        if (features.length > 0) {
          setWarningData({
            title: 'Features Restricted',
            message: `Some features are unavailable due to security concerns: ${features.join(', ')}`,
            risks: [],
            severity: 'medium',
            recommendations: ['Improve device security to access all features']
          });
          setVisible(true);
        }
      }
    );

    return () => {
      warningListener.remove();
      blockedListener.remove();
      restrictionListener.remove();
    };
  }, [dismissed]);

  useEffect(() => {
    if (propVisible !== undefined) {
      setVisible(propVisible);
    }
  }, [propVisible]);

  const handleDismiss = () => {
    if (allowDismiss && warningData?.severity !== 'critical') {
      setVisible(false);
      setDismissed(true);
      onDismiss?.();
    }
  };

  const handleSecuritySettings = () => {
    setVisible(false);
    onSecuritySettings?.();
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return '#DC2626'; // Red
      case 'high':
        return '#EA580C'; // Orange
      case 'medium':
        return '#F59E0B'; // Yellow
      case 'low':
        return '#3B82F6'; // Blue
      default:
        return '#6B7280'; // Gray
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'shield-off';
      case 'high':
        return 'warning';
      case 'medium':
        return 'alert-circle';
      case 'low':
        return 'information-circle';
      default:
        return 'help-circle';
    }
  };

  const getRiskIcon = (riskType: SecurityRiskType) => {
    switch (riskType) {
      case SecurityRiskType.JAILBREAK:
      case SecurityRiskType.ROOT:
        return 'phone-portrait-outline';
      case SecurityRiskType.DEBUGGING:
        return 'bug-outline';
      case SecurityRiskType.EMULATOR:
        return 'desktop-outline';
      case SecurityRiskType.VPN:
      case SecurityRiskType.PROXY:
        return 'globe-outline';
      case SecurityRiskType.TAMPERING:
        return 'shield-checkmark-outline';
      case SecurityRiskType.CERTIFICATE:
        return 'lock-open-outline';
      default:
        return 'alert-circle-outline';
    }
  };

  if (!visible || !warningData) {
    return null;
  }

  const severityColor = getSeverityColor(warningData.severity);
  const canDismiss = allowDismiss && warningData.severity !== 'critical';

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={handleDismiss}
    >
      <View style={styles.overlay}>
        {Platform.OS === 'ios' ? (
          <BlurView intensity={90} style={StyleSheet.absoluteFill} />
        ) : (
          <View style={[StyleSheet.absoluteFill, styles.androidOverlay]} />
        )}
        
        <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
          {/* Header */}
          <View style={[styles.header, { borderBottomColor: severityColor }]}>
            <View style={styles.headerContent}>
              <Ionicons
                name={getSeverityIcon(warningData.severity)}
                size={28}
                color={severityColor}
                style={styles.headerIcon}
              />
              <Text style={[styles.title, { color: theme.colors.text }]}>
                {warningData.title}
              </Text>
            </View>
            {canDismiss && (
              <TouchableOpacity onPress={handleDismiss} style={styles.closeButton}>
                <Ionicons name="close" size={24} color={theme.colors.textSecondary} />
              </TouchableOpacity>
            )}
          </View>

          <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
            {/* Main Message */}
            <Text style={[styles.message, { color: theme.colors.text }]}>
              {warningData.message}
            </Text>

            {/* Risk Details */}
            {warningData.risks.length > 0 && (
              <View style={styles.risksContainer}>
                <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
                  Security Risks Detected:
                </Text>
                {warningData.risks.map((risk, index) => (
                  <View key={index} style={[styles.riskItem, { 
                    backgroundColor: theme.colors.surface,
                    borderLeftColor: getSeverityColor(risk.severity)
                  }]}>
                    <Ionicons
                      name={getRiskIcon(risk.type)}
                      size={20}
                      color={getSeverityColor(risk.severity)}
                      style={styles.riskIcon}
                    />
                    <View style={styles.riskContent}>
                      <Text style={[styles.riskDescription, { color: theme.colors.text }]}>
                        {risk.description}
                      </Text>
                      <Text style={[styles.riskMitigation, { color: theme.colors.textSecondary }]}>
                        {risk.mitigation}
                      </Text>
                      <View style={styles.riskMeta}>
                        <Text style={[styles.riskConfidence, { color: theme.colors.textSecondary }]}>
                          Confidence: {risk.confidence}%
                        </Text>
                        <View style={[styles.severityBadge, { 
                          backgroundColor: getSeverityColor(risk.severity) + '20'
                        }]}>
                          <Text style={[styles.severityText, { 
                            color: getSeverityColor(risk.severity) 
                          }]}>
                            {risk.severity.toUpperCase()}
                          </Text>
                        </View>
                      </View>
                    </View>
                  </View>
                ))}
              </View>
            )}

            {/* Recommendations */}
            {warningData.recommendations && warningData.recommendations.length > 0 && (
              <View style={styles.recommendationsContainer}>
                <Text style={[styles.sectionTitle, { color: theme.colors.text }]}>
                  Recommendations:
                </Text>
                {warningData.recommendations.map((recommendation, index) => (
                  <View key={index} style={styles.recommendationItem}>
                    <Ionicons 
                      name="checkmark-circle" 
                      size={16} 
                      color={theme.colors.primary} 
                      style={styles.recommendationIcon}
                    />
                    <Text style={[styles.recommendationText, { color: theme.colors.text }]}>
                      {recommendation}
                    </Text>
                  </View>
                ))}
              </View>
            )}

            {/* Security Score */}
            <View style={[styles.scoreContainer, { backgroundColor: theme.colors.surface }]}>
              <Text style={[styles.scoreLabel, { color: theme.colors.textSecondary }]}>
                Current Security Score:
              </Text>
              <SecurityScoreIndicator />
            </View>
          </ScrollView>

          {/* Actions */}
          <View style={styles.actions}>
            {onSecuritySettings && (
              <TouchableOpacity
                style={[styles.button, styles.primaryButton, { 
                  backgroundColor: theme.colors.primary 
                }]}
                onPress={handleSecuritySettings}
              >
                <Text style={[styles.buttonText, { color: '#FFFFFF' }]}>
                  Security Settings
                </Text>
              </TouchableOpacity>
            )}
            
            {canDismiss && (
              <TouchableOpacity
                style={[styles.button, styles.secondaryButton, { 
                  borderColor: theme.colors.border 
                }]}
                onPress={handleDismiss}
              >
                <Text style={[styles.buttonText, { color: theme.colors.text }]}>
                  {warningData.severity === 'low' ? 'Got it' : 'Continue Anyway'}
                </Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
      </View>
    </Modal>
  );
};

// Security Score Indicator Component
const SecurityScoreIndicator: React.FC = () => {
  const theme = useTheme();
  const [score, setScore] = useState<number>(0);
  const [level, setLevel] = useState<SecurityLevel>(SecurityLevel.NONE);

  useEffect(() => {
    loadSecurityScore();
  }, []);

  const loadSecurityScore = async () => {
    try {
      const status = await EnhancedMobileSecurityService.getLastSecurityStatus();
      if (status) {
        setScore(status.securityScore);
        setLevel(status.securityLevel);
      }
    } catch (error) {
      logger.error('Failed to load security score:', error);
    }
  };

  const getScoreColor = () => {
    if (score >= 80) return '#10B981'; // Green
    if (score >= 60) return '#F59E0B'; // Yellow
    if (score >= 40) return '#EA580C'; // Orange
    return '#DC2626'; // Red
  };

  return (
    <View style={styles.scoreIndicator}>
      <View style={[styles.scoreCircle, { borderColor: getScoreColor() }]}>
        <Text style={[styles.scoreText, { color: getScoreColor() }]}>
          {score}%
        </Text>
      </View>
      <Text style={[styles.levelText, { color: theme.colors.textSecondary }]}>
        Security Level: {level}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  androidOverlay: {
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  container: {
    width: '90%',
    maxWidth: 400,
    maxHeight: '80%',
    borderRadius: 16,
    overflow: 'hidden',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 2,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  headerIcon: {
    marginRight: 12,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
  },
  closeButton: {
    padding: 4,
  },
  content: {
    padding: 20,
  },
  message: {
    fontSize: 16,
    lineHeight: 24,
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  risksContainer: {
    marginBottom: 20,
  },
  riskItem: {
    flexDirection: 'row',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    borderLeftWidth: 3,
  },
  riskIcon: {
    marginRight: 12,
    marginTop: 2,
  },
  riskContent: {
    flex: 1,
  },
  riskDescription: {
    fontSize: 14,
    marginBottom: 4,
  },
  riskMitigation: {
    fontSize: 12,
    fontStyle: 'italic',
    marginBottom: 4,
  },
  riskMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  riskConfidence: {
    fontSize: 11,
  },
  severityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  severityText: {
    fontSize: 10,
    fontWeight: '600',
  },
  recommendationsContainer: {
    marginBottom: 20,
  },
  recommendationItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  recommendationIcon: {
    marginRight: 8,
    marginTop: 2,
  },
  recommendationText: {
    flex: 1,
    fontSize: 14,
  },
  scoreContainer: {
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
  },
  scoreLabel: {
    fontSize: 14,
    marginBottom: 8,
  },
  scoreIndicator: {
    alignItems: 'center',
  },
  scoreCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 4,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  scoreText: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  levelText: {
    fontSize: 12,
  },
  actions: {
    padding: 20,
    paddingTop: 0,
    gap: 12,
  },
  button: {
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
  },
  primaryButton: {
    // backgroundColor set dynamically
  },
  secondaryButton: {
    borderWidth: 1,
  },
  buttonText: {
    fontSize: 16,
    fontWeight: '600',
  },
});

export default SecurityWarningModal;