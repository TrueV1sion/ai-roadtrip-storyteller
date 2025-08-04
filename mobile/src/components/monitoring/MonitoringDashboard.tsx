/**
 * Monitoring Dashboard Component
 * Shows real-time app performance and health metrics
 */

import React, { useState, useEffect } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  Alert as RNAlert,
} from 'react-native';
import { monitoringService } from '../../services/monitoring/MonitoringService';
import { performanceMonitoring } from '../../services/sentry/PerformanceMonitoring';
import DeviceInfo from 'react-native-device-info';
import NetInfo from '@react-native-community/netinfo';

interface DashboardProps {
  onClose?: () => void;
}

export const MonitoringDashboard: React.FC<DashboardProps> = ({ onClose }) => {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>({});
  const [deviceInfo, setDeviceInfo] = useState<any>({});
  const [networkInfo, setNetworkInfo] = useState<any>({});
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      // Get alerts
      const currentAlerts = monitoringService.getAlerts();
      setAlerts(currentAlerts);

      // Get performance metrics
      const perfSummary = performanceMonitoring.getPerformanceSummary();
      setMetrics({
        screens: Array.from(perfSummary.screens.entries()),
        apis: Array.from(perfSummary.apis.entries()),
      });

      // Get device info
      const [
        batteryLevel,
        freeDiskStorage,
        totalDiskCapacity,
        usedMemory,
        totalMemory,
      ] = await Promise.all([
        DeviceInfo.getBatteryLevel(),
        DeviceInfo.getFreeDiskStorage(),
        DeviceInfo.getTotalDiskCapacity(),
        DeviceInfo.getUsedMemory().catch(() => 0),
        DeviceInfo.getTotalMemory().catch(() => 0),
      ]);

      setDeviceInfo({
        batteryLevel,
        diskUsage: 1 - (freeDiskStorage / totalDiskCapacity),
        memoryUsage: totalMemory > 0 ? usedMemory / totalMemory : 0,
        model: DeviceInfo.getModel(),
        os: `${DeviceInfo.getSystemName()} ${DeviceInfo.getSystemVersion()}`,
        appVersion: DeviceInfo.getVersion(),
      });

      // Get network info
      const netInfo = await NetInfo.fetch();
      setNetworkInfo(netInfo);
    } catch (error) {
      logger.error('Error loading monitoring data:', error);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const clearAlert = (alertId: string) => {
    // In a real implementation, you'd remove the specific alert
    RNAlert.alert('Clear Alert', 'Alert cleared from dashboard');
  };

  const getAlertColor = (type: string) => {
    switch (type) {
      case 'error': return '#FF6B6B';
      case 'warning': return '#FFD93D';
      case 'info': return '#4ECDC4';
      default: return '#95E1D3';
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      <View style={styles.header}>
        <Text style={styles.title}>Monitoring Dashboard</Text>
        {onClose && (
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Text style={styles.closeText}>✕</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Alerts Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Active Alerts ({alerts.length})</Text>
        {alerts.length === 0 ? (
          <Text style={styles.noData}>No active alerts</Text>
        ) : (
          alerts.map((alert) => (
            <TouchableOpacity
              key={alert.id}
              style={[styles.alert, { borderLeftColor: getAlertColor(alert.type) }]}
              onPress={() => clearAlert(alert.id)}
            >
              <View style={styles.alertHeader}>
                <Text style={[styles.alertType, { color: getAlertColor(alert.type) }]}>
                  {alert.type.toUpperCase()}
                </Text>
                <Text style={styles.alertTime}>
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </Text>
              </View>
              <Text style={styles.alertTitle}>{alert.title}</Text>
              <Text style={styles.alertMessage}>{alert.message}</Text>
            </TouchableOpacity>
          ))
        )}
      </View>

      {/* Device Status */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Device Status</Text>
        <View style={styles.statusGrid}>
          <View style={styles.statusItem}>
            <Text style={styles.statusLabel}>Battery</Text>
            <Text style={styles.statusValue}>
              {(deviceInfo.batteryLevel * 100).toFixed(0)}%
            </Text>
          </View>
          <View style={styles.statusItem}>
            <Text style={styles.statusLabel}>Memory</Text>
            <Text style={styles.statusValue}>
              {(deviceInfo.memoryUsage * 100).toFixed(0)}%
            </Text>
          </View>
          <View style={styles.statusItem}>
            <Text style={styles.statusLabel}>Disk</Text>
            <Text style={styles.statusValue}>
              {(deviceInfo.diskUsage * 100).toFixed(0)}%
            </Text>
          </View>
          <View style={styles.statusItem}>
            <Text style={styles.statusLabel}>Network</Text>
            <Text style={styles.statusValue}>
              {networkInfo.isConnected ? networkInfo.type : 'Offline'}
            </Text>
          </View>
        </View>
        <View style={styles.deviceDetails}>
          <Text style={styles.detailText}>Model: {deviceInfo.model}</Text>
          <Text style={styles.detailText}>OS: {deviceInfo.os}</Text>
          <Text style={styles.detailText}>App Version: {deviceInfo.appVersion}</Text>
        </View>
      </View>

      {/* Screen Performance */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Screen Performance</Text>
        {metrics.screens?.length === 0 ? (
          <Text style={styles.noData}>No screen metrics available</Text>
        ) : (
          metrics.screens?.map(([screenName, data]: [string, any]) => (
            <View key={screenName} style={styles.metricItem}>
              <Text style={styles.metricName}>{screenName}</Text>
              <View style={styles.metricDetails}>
                <Text style={styles.metricValue}>
                  Load: {data.loadTime.toFixed(0)}ms
                </Text>
                <Text style={styles.metricValue}>
                  Render: {data.renderTime.toFixed(0)}ms
                </Text>
                <Text style={styles.metricValue}>
                  API Calls: {data.apiCalls}
                </Text>
              </View>
            </View>
          ))
        )}
      </View>

      {/* API Performance */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>API Performance</Text>
        {metrics.apis?.length === 0 ? (
          <Text style={styles.noData}>No API metrics available</Text>
        ) : (
          metrics.apis?.map(([endpoint, data]: [string, any]) => (
            <View key={endpoint} style={styles.metricItem}>
              <Text style={styles.metricName} numberOfLines={1}>
                {endpoint.split('/').pop() || endpoint}
              </Text>
              <View style={styles.metricDetails}>
                <Text style={styles.metricValue}>
                  Calls: {data.count}
                </Text>
                <Text style={styles.metricValue}>
                  Avg: {data.avgTime.toFixed(0)}ms
                </Text>
              </View>
            </View>
          ))
        )}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333333',
  },
  closeButton: {
    padding: 8,
  },
  closeText: {
    fontSize: 24,
    color: '#666666',
  },
  section: {
    backgroundColor: '#FFFFFF',
    margin: 10,
    padding: 15,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 15,
    color: '#333333',
  },
  noData: {
    color: '#999999',
    fontStyle: 'italic',
    textAlign: 'center',
    paddingVertical: 20,
  },
  alert: {
    marginBottom: 10,
    padding: 12,
    backgroundColor: '#F9F9F9',
    borderRadius: 6,
    borderLeftWidth: 4,
  },
  alertHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 5,
  },
  alertType: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  alertTime: {
    fontSize: 12,
    color: '#666666',
  },
  alertTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
    color: '#333333',
  },
  alertMessage: {
    fontSize: 14,
    color: '#666666',
  },
  statusGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 15,
  },
  statusItem: {
    width: '50%',
    paddingVertical: 10,
  },
  statusLabel: {
    fontSize: 14,
    color: '#666666',
    marginBottom: 4,
  },
  statusValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333333',
  },
  deviceDetails: {
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
    paddingTop: 10,
  },
  detailText: {
    fontSize: 14,
    color: '#666666',
    marginBottom: 4,
  },
  metricItem: {
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  metricName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 5,
    color: '#333333',
  },
  metricDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  metricValue: {
    fontSize: 14,
    color: '#666666',
  },
});