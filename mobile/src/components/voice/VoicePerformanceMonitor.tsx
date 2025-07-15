/**
 * Voice Performance Monitor Component
 * Real-time visualization of voice system performance metrics
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Dimensions,
  ActivityIndicator
} from 'react-native';
import { LineChart, BarChart } from 'react-native-chart-kit';
import { voicePerformanceOptimizer } from '../../services/voice/voicePerformanceOptimizer';
import apiClient from '../../services/apiClient';

interface PerformanceMetrics {
  real_time: {
    requests_per_minute: number;
    response_time: {
      p50: number;
      p95: number;
      p99: number;
    };
    error_rate: number;
    cache_hit_rate: number;
    system_status: 'healthy' | 'degraded' | 'critical';
  };
  circuit_breakers: {
    stt: string;
    tts: string;
    ai: string;
    booking: string;
  };
}

const VoicePerformanceMonitor: React.FC = () => {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [localMetrics, setLocalMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load initial metrics
    loadMetrics();
    
    // Set up refresh interval
    const interval = setInterval(loadMetrics, 10000); // Refresh every 10 seconds
    
    // Listen for local performance events
    const performanceListener = () => {
      const report = voicePerformanceOptimizer.getPerformanceReport();
      setLocalMetrics(report);
    };
    
    voicePerformanceOptimizer.on('performanceMetric', performanceListener);
    
    return () => {
      clearInterval(interval);
      voicePerformanceOptimizer.off('performanceMetric', performanceListener);
    };
  }, []);

  const loadMetrics = async () => {
    try {
      const response = await apiClient.get<PerformanceMetrics>('/api/voice/metrics');
      setMetrics(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load metrics:', error);
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return '#4CAF50';
      case 'degraded': return '#FF9800';
      case 'critical': return '#F44336';
      default: return '#757575';
    }
  };

  const getCircuitBreakerColor = (state: string) => {
    switch (state) {
      case 'closed': return '#4CAF50';
      case 'open': return '#F44336';
      case 'half-open': return '#FF9800';
      default: return '#757575';
    }
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#2196F3" />
      </View>
    );
  }

  if (!metrics) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>Unable to load performance metrics</Text>
      </View>
    );
  }

  const chartConfig = {
    backgroundColor: '#ffffff',
    backgroundGradientFrom: '#ffffff',
    backgroundGradientTo: '#ffffff',
    decimalPlaces: 1,
    color: (opacity = 1) => `rgba(33, 150, 243, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(0, 0, 0, ${opacity})`,
    style: {
      borderRadius: 16
    },
    propsForDots: {
      r: '6',
      strokeWidth: '2',
      stroke: '#2196F3'
    }
  };

  const screenWidth = Dimensions.get('window').width;

  return (
    <ScrollView style={styles.container}>
      {/* System Status */}
      <View style={styles.statusCard}>
        <Text style={styles.sectionTitle}>System Status</Text>
        <View style={[
          styles.statusIndicator,
          { backgroundColor: getStatusColor(metrics.real_time.system_status) }
        ]}>
          <Text style={styles.statusText}>
            {metrics.real_time.system_status.toUpperCase()}
          </Text>
        </View>
      </View>

      {/* Key Metrics */}
      <View style={styles.metricsGrid}>
        <View style={styles.metricCard}>
          <Text style={styles.metricValue}>
            {metrics.real_time.requests_per_minute}
          </Text>
          <Text style={styles.metricLabel}>Requests/min</Text>
        </View>
        
        <View style={styles.metricCard}>
          <Text style={styles.metricValue}>
            {metrics.real_time.response_time.p95.toFixed(1)}s
          </Text>
          <Text style={styles.metricLabel}>P95 Response</Text>
        </View>
        
        <View style={styles.metricCard}>
          <Text style={styles.metricValue}>
            {(metrics.real_time.error_rate * 100).toFixed(1)}%
          </Text>
          <Text style={styles.metricLabel}>Error Rate</Text>
        </View>
        
        <View style={styles.metricCard}>
          <Text style={styles.metricValue}>
            {(metrics.real_time.cache_hit_rate * 100).toFixed(0)}%
          </Text>
          <Text style={styles.metricLabel}>Cache Hits</Text>
        </View>
      </View>

      {/* Response Time Chart */}
      <View style={styles.chartCard}>
        <Text style={styles.sectionTitle}>Response Time Distribution</Text>
        <BarChart
          data={{
            labels: ['P50', 'P95', 'P99'],
            datasets: [{
              data: [
                metrics.real_time.response_time.p50,
                metrics.real_time.response_time.p95,
                metrics.real_time.response_time.p99
              ]
            }]
          }}
          width={screenWidth - 40}
          height={200}
          chartConfig={chartConfig}
          style={styles.chart}
        />
      </View>

      {/* Circuit Breakers */}
      <View style={styles.circuitBreakersCard}>
        <Text style={styles.sectionTitle}>Circuit Breakers</Text>
        <View style={styles.circuitBreakersGrid}>
          {Object.entries(metrics.circuit_breakers).map(([service, state]) => (
            <View key={service} style={styles.circuitBreaker}>
              <View style={[
                styles.circuitBreakerIndicator,
                { backgroundColor: getCircuitBreakerColor(state) }
              ]} />
              <Text style={styles.circuitBreakerLabel}>
                {service.toUpperCase()}: {state}
              </Text>
            </View>
          ))}
        </View>
      </View>

      {/* Local Performance Metrics */}
      {localMetrics && (
        <View style={styles.localMetricsCard}>
          <Text style={styles.sectionTitle}>Device Performance</Text>
          {localMetrics.recommendations.map((rec: string, index: number) => (
            <Text key={index} style={styles.recommendation}>
              • {rec}
            </Text>
          ))}
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  statusCard: {
    backgroundColor: 'white',
    margin: 20,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  statusIndicator: {
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  statusText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
  },
  metricCard: {
    backgroundColor: 'white',
    width: '48%',
    padding: 16,
    marginBottom: 12,
    borderRadius: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  metricValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2196F3',
  },
  metricLabel: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
  chartCard: {
    backgroundColor: 'white',
    margin: 20,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  chart: {
    marginVertical: 8,
    borderRadius: 16,
  },
  circuitBreakersCard: {
    backgroundColor: 'white',
    margin: 20,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  circuitBreakersGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  circuitBreaker: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '50%',
    marginBottom: 8,
  },
  circuitBreakerIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 8,
  },
  circuitBreakerLabel: {
    fontSize: 14,
    color: '#333',
  },
  localMetricsCard: {
    backgroundColor: 'white',
    margin: 20,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  recommendation: {
    fontSize: 14,
    color: '#666',
    marginTop: 8,
  },
  errorText: {
    fontSize: 16,
    color: '#F44336',
    textAlign: 'center',
    marginTop: 50,
  },
});

export default VoicePerformanceMonitor;