/**
 * Performance debugging screen for development
 */
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Button,
  Alert,
  Platform,
  Switch
} from 'react-native';
import { performanceMonitor } from '../utils/performanceMonitor';
import { useMemoryManagement } from '../hooks/usePerformanceOptimization';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface PerformanceMetric {
  component: string;
  avgRender: number;
  avgMount: number;
  slowRenders: number;
  totalRenders: number;
}

export const PerformanceDebugScreen: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetric[]>([]);
  const [isMonitoring, setIsMonitoring] = useState(__DEV__);
  const [refreshInterval, setRefreshInterval] = useState(5000);
  const memoryUsage = useMemoryManagement();

  useEffect(() => {
    if (!isMonitoring) return;

    const updateMetrics = () => {
      const summary = performanceMonitor.getSummary();
      const metricsArray: PerformanceMetric[] = [];

      summary.forEach((report, componentName) => {
        metricsArray.push({
          component: componentName,
          avgRender: report.averageRenderTime,
          avgMount: report.averageMountTime,
          slowRenders: report.slowRenders,
          totalRenders: report.totalRenders
        });
      });

      // Sort by slow renders descending
      metricsArray.sort((a, b) => b.slowRenders - a.slowRenders);
      setMetrics(metricsArray);
    };

    updateMetrics();
    const interval = setInterval(updateMetrics, refreshInterval);

    return () => clearInterval(interval);
  }, [isMonitoring, refreshInterval]);

  const exportMetrics = async () => {
    try {
      await performanceMonitor.exportMetrics();
      Alert.alert('Success', 'Performance metrics exported to storage');
    } catch (error) {
      Alert.alert('Error', 'Failed to export metrics');
    }
  };

  const clearMetrics = () => {
    Alert.alert(
      'Clear Metrics',
      'Are you sure you want to clear all performance metrics?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: () => {
            performanceMonitor.clearMetrics();
            setMetrics([]);
          }
        }
      ]
    );
  };

  const clearCache = async () => {
    try {
      await AsyncStorage.clear();
      Alert.alert('Success', 'Cache cleared successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to clear cache');
    }
  };

  const getPerformanceColor = (value: number, threshold: number): string => {
    if (value < threshold * 0.5) return '#4CAF50'; // Green
    if (value < threshold) return '#FF9800'; // Orange
    return '#F44336'; // Red
  };

  if (!__DEV__) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Performance Debug</Text>
        <Text style={styles.subtitle}>Only available in development mode</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Performance Debug</Text>
        <View style={styles.controls}>
          <View style={styles.controlRow}>
            <Text>Monitoring</Text>
            <Switch
              value={isMonitoring}
              onValueChange={setIsMonitoring}
            />
          </View>
        </View>
      </View>

      {memoryUsage && (
        <View style={styles.memoryCard}>
          <Text style={styles.sectionTitle}>Memory Usage</Text>
          <Text>Used: {(memoryUsage.used / 1024 / 1024).toFixed(2)} MB</Text>
          <Text>Total: {(memoryUsage.total / 1024 / 1024).toFixed(2)} MB</Text>
          <Text style={{ color: getPerformanceColor(memoryUsage.percentage, 80) }}>
            Usage: {memoryUsage.percentage.toFixed(1)}%
          </Text>
        </View>
      )}

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Component Performance</Text>
        {metrics.length === 0 ? (
          <Text style={styles.emptyText}>No performance data available</Text>
        ) : (
          metrics.map((metric, index) => (
            <View key={`${metric.component}-${index}`} style={styles.metricCard}>
              <Text style={styles.componentName}>{metric.component}</Text>
              <View style={styles.metricRow}>
                <Text>Avg Render: </Text>
                <Text style={{ color: getPerformanceColor(metric.avgRender, 16.67) }}>
                  {metric.avgRender.toFixed(2)}ms
                </Text>
              </View>
              <View style={styles.metricRow}>
                <Text>Avg Mount: </Text>
                <Text style={{ color: getPerformanceColor(metric.avgMount, 100) }}>
                  {metric.avgMount.toFixed(2)}ms
                </Text>
              </View>
              <View style={styles.metricRow}>
                <Text>Slow Renders: </Text>
                <Text style={{ color: metric.slowRenders > 0 ? '#F44336' : '#4CAF50' }}>
                  {metric.slowRenders}/{metric.totalRenders}
                </Text>
              </View>
            </View>
          ))
        )}
      </View>

      <View style={styles.actions}>
        <Button title="Export Metrics" onPress={exportMetrics} />
        <View style={{ height: 10 }} />
        <Button title="Clear Metrics" onPress={clearMetrics} color="#FF6B6B" />
        <View style={{ height: 10 }} />
        <Button title="Clear Cache" onPress={clearCache} color="#FF9800" />
      </View>

      <View style={styles.legend}>
        <Text style={styles.legendTitle}>Performance Indicators:</Text>
        <View style={styles.legendItem}>
          <View style={[styles.legendColor, { backgroundColor: '#4CAF50' }]} />
          <Text>Good</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendColor, { backgroundColor: '#FF9800' }]} />
          <Text>Warning</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendColor, { backgroundColor: '#F44336' }]} />
          <Text>Poor</Text>
        </View>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5'
  },
  header: {
    backgroundColor: '#fff',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0'
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 10
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginTop: 20
  },
  controls: {
    marginTop: 10
  },
  controlRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 5
  },
  memoryCard: {
    backgroundColor: '#fff',
    margin: 10,
    padding: 15,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3
  },
  section: {
    margin: 10
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 10
  },
  metricCard: {
    backgroundColor: '#fff',
    padding: 15,
    marginBottom: 10,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3
  },
  componentName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 10
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 2
  },
  emptyText: {
    textAlign: 'center',
    color: '#666',
    paddingVertical: 20
  },
  actions: {
    padding: 20
  },
  legend: {
    backgroundColor: '#fff',
    margin: 10,
    padding: 15,
    borderRadius: 8
  },
  legendTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 10
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 5
  },
  legendColor: {
    width: 20,
    height: 20,
    borderRadius: 4,
    marginRight: 10
  }
});