/**
 * Security Screen Component
 * Displays device security status and allows security management
 */

import React, { useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Switch,
  RefreshControl,
  Platform
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useMobileSecurity, getSecurityIndicator } from '../hooks/useMobileSecurity';
import { SecurityRiskType } from '../services/mobileSecurityService';
import Icon from 'react-native-vector-icons/MaterialIcons';

const SecurityScreen: React.FC = () => {
  const {
    securityStatus,
    isSecure,
    isChecking,
    risks,
    checkSecurity,
    enableHardening
  } = useMobileSecurity({
    showAlerts: true,
    enableAutoCheck: true
  });

  const [hardeningEnabled, setHardeningEnabled] = React.useState(false);
  const [refreshing, setRefreshing] = React.useState(false);

  const indicator = getSecurityIndicator({ status: securityStatus });

  const handleRefresh = async () => {
    setRefreshing(true);
    await checkSecurity();
    setRefreshing(false);
  };

  const handleHardeningToggle = async (value: boolean) => {
    setHardeningEnabled(value);
    if (value) {
      await enableHardening();
    }
  };

  const getRiskIcon = (type: SecurityRiskType): string => {
    const icons: Record<SecurityRiskType, string> = {
      [SecurityRiskType.JAILBREAK]: 'phonelink-erase',
      [SecurityRiskType.ROOT]: 'phonelink-erase',
      [SecurityRiskType.DEBUGGING]: 'bug-report',
      [SecurityRiskType.EMULATOR]: 'computer',
      [SecurityRiskType.TAMPERING]: 'warning',
      [SecurityRiskType.VPN]: 'vpn-lock',
      [SecurityRiskType.NETWORK]: 'wifi-off',
      [SecurityRiskType.OUTDATED_OS]: 'system-update',
      [SecurityRiskType.UNKNOWN_SOURCE]: 'help-outline'
    };
    return icons[type] || 'error-outline';
  };

  const getRiskColor = (severity: string): string => {
    switch (severity) {
      case 'critical':
        return '#F44336';
      case 'high':
        return '#FF5722';
      case 'medium':
        return '#FF9800';
      case 'low':
        return '#FFC107';
      default:
        return '#9E9E9E';
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Security Status</Text>
          <TouchableOpacity onPress={checkSecurity} disabled={isChecking}>
            {isChecking ? (
              <ActivityIndicator size="small" color="#007AFF" />
            ) : (
              <Icon name="refresh" size={24} color="#007AFF" />
            )}
          </TouchableOpacity>
        </View>

        {/* Security Score */}
        <View style={[styles.scoreCard, { backgroundColor: indicator.color + '20' }]}>
          <Text style={styles.scoreIcon}>{indicator.icon}</Text>
          <View style={styles.scoreInfo}>
            <Text style={[styles.scoreText, { color: indicator.color }]}>
              {securityStatus ? `${securityStatus.securityScore}%` : '...'}
            </Text>
            <Text style={styles.scoreLabel}>{indicator.text}</Text>
          </View>
        </View>

        {/* Security Status Details */}
        {securityStatus && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Security Checks</Text>
            
            <SecurityCheckItem
              title="Jailbreak/Root Detection"
              status={!securityStatus.isJailbroken && !securityStatus.isRooted}
              detail={
                securityStatus.isJailbroken
                  ? 'Device is jailbroken'
                  : securityStatus.isRooted
                  ? 'Device is rooted'
                  : 'No modifications detected'
              }
            />
            
            <SecurityCheckItem
              title="Debug Mode"
              status={!securityStatus.isDebuggingEnabled}
              detail={
                securityStatus.isDebuggingEnabled
                  ? 'Debugging is enabled'
                  : 'Debug mode disabled'
              }
            />
            
            <SecurityCheckItem
              title="Device Type"
              status={!securityStatus.isEmulator}
              detail={
                securityStatus.isEmulator
                  ? 'Running on emulator'
                  : 'Physical device detected'
              }
            />
            
            <SecurityCheckItem
              title="App Integrity"
              status={!securityStatus.isTampered}
              detail={
                securityStatus.isTampered
                  ? 'App may be modified'
                  : 'App integrity verified'
              }
            />
            
            <SecurityCheckItem
              title="Network Security"
              status={!securityStatus.isVPNActive}
              detail={
                securityStatus.isVPNActive
                  ? 'VPN connection active'
                  : 'Direct network connection'
              }
            />
          </View>
        )}

        {/* Risks */}
        {risks.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Security Risks</Text>
            {risks.map((risk, index) => (
              <View key={index} style={styles.riskItem}>
                <Icon
                  name={getRiskIcon(risk.type)}
                  size={24}
                  color={getRiskColor(risk.severity)}
                  style={styles.riskIcon}
                />
                <View style={styles.riskInfo}>
                  <Text style={styles.riskTitle}>{risk.description}</Text>
                  <Text style={styles.riskMitigation}>{risk.mitigation}</Text>
                  <View style={styles.riskSeverity}>
                    <Text
                      style={[
                        styles.severityBadge,
                        { backgroundColor: getRiskColor(risk.severity) }
                      ]}
                    >
                      {risk.severity.toUpperCase()}
                    </Text>
                  </View>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Security Features */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Security Features</Text>
          
          <View style={styles.featureItem}>
            <View style={styles.featureInfo}>
              <Text style={styles.featureTitle}>Enhanced Security</Text>
              <Text style={styles.featureDescription}>
                Enable additional security hardening features
              </Text>
            </View>
            <Switch
              value={hardeningEnabled}
              onValueChange={handleHardeningToggle}
              trackColor={{ false: '#767577', true: '#81b0ff' }}
              thumbColor={hardeningEnabled ? '#007AFF' : '#f4f3f4'}
            />
          </View>

          {Platform.OS === 'android' && (
            <Text style={styles.featureNote}>
              • Screenshot blocking enabled in secure mode
            </Text>
          )}
          
          {Platform.OS === 'ios' && (
            <Text style={styles.featureNote}>
              • App preview blur enabled when backgrounded
            </Text>
          )}
          
          <Text style={styles.featureNote}>
            • Certificate pinning for secure connections
          </Text>
          
          <Text style={styles.featureNote}>
            • Anti-debugging protection
          </Text>
        </View>

        {/* Last Check */}
        {securityStatus && (
          <Text style={styles.lastCheck}>
            Last checked: {new Date(securityStatus.timestamp).toLocaleString()}
          </Text>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

interface SecurityCheckItemProps {
  title: string;
  status: boolean;
  detail: string;
}

const SecurityCheckItem: React.FC<SecurityCheckItemProps> = ({
  title,
  status,
  detail
}) => (
  <View style={styles.checkItem}>
    <Icon
      name={status ? 'check-circle' : 'cancel'}
      size={24}
      color={status ? '#4CAF50' : '#F44336'}
      style={styles.checkIcon}
    />
    <View style={styles.checkInfo}>
      <Text style={styles.checkTitle}>{title}</Text>
      <Text style={styles.checkDetail}>{detail}</Text>
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5'
  },
  scrollContent: {
    paddingBottom: 20
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#FFF'
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333'
  },
  scoreCard: {
    flexDirection: 'row',
    alignItems: 'center',
    margin: 20,
    padding: 20,
    borderRadius: 12,
    backgroundColor: '#FFF'
  },
  scoreIcon: {
    fontSize: 48,
    marginRight: 20
  },
  scoreInfo: {
    flex: 1
  },
  scoreText: {
    fontSize: 36,
    fontWeight: 'bold'
  },
  scoreLabel: {
    fontSize: 16,
    color: '#666',
    marginTop: 4
  },
  section: {
    backgroundColor: '#FFF',
    marginHorizontal: 20,
    marginBottom: 15,
    padding: 20,
    borderRadius: 12
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 15
  },
  checkItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0'
  },
  checkIcon: {
    marginRight: 15
  },
  checkInfo: {
    flex: 1
  },
  checkTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333'
  },
  checkDetail: {
    fontSize: 14,
    color: '#666',
    marginTop: 2
  },
  riskItem: {
    flexDirection: 'row',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0'
  },
  riskIcon: {
    marginRight: 15
  },
  riskInfo: {
    flex: 1
  },
  riskTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333'
  },
  riskMitigation: {
    fontSize: 14,
    color: '#666',
    marginTop: 4
  },
  riskSeverity: {
    flexDirection: 'row',
    marginTop: 8
  },
  severityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    color: '#FFF',
    fontSize: 12,
    fontWeight: '600',
    overflow: 'hidden'
  },
  featureItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12
  },
  featureInfo: {
    flex: 1,
    marginRight: 15
  },
  featureTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333'
  },
  featureDescription: {
    fontSize: 14,
    color: '#666',
    marginTop: 2
  },
  featureNote: {
    fontSize: 14,
    color: '#666',
    marginTop: 8,
    paddingLeft: 20
  },
  lastCheck: {
    textAlign: 'center',
    fontSize: 12,
    color: '#999',
    marginTop: 20,
    marginBottom: 10
  }
});

export default SecurityScreen;