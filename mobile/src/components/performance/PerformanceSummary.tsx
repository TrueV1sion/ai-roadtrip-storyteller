import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, RefreshControl, Platform } from 'react-native';
import { getStartupMetrics } from '@/utils/appStartupOptimizer';
import { getConnectionMetrics, getConnectionStatus } from '@/utils/connectionManager';
import { useApp } from '@/contexts/AppContext';
import { formatBytes, formatDuration } from '@/utils/formatters';
import { Stopwatch } from '@/utils/performance';

import { logger } from '@/services/logger';
// Types for the component props
interface PerformanceSummaryProps {
  onClose?: () => void;
}

const PerformanceSummary: React.FC<PerformanceSummaryProps> = ({ onClose }) => {
  // Get app context
  const { performanceMetrics, clearImageCache, clearApiCache, connectionStatus } = useApp();
  
  // State
  const [refreshing, setRefreshing] = useState(false);
  const [renderTime, setRenderTime] = useState(0);
  const [expandedSections, setExpandedSections] = useState<string[]>([]);
  
  // Ref for render timing
  const stopwatch = React.useRef<Stopwatch | null>(null);
  
  // Initialize render timing on mount
  useEffect(() => {
    stopwatch.current = new Stopwatch('render', 'PerformanceSummary');
    
    return () => {
      if (stopwatch.current) {
        const time = stopwatch.current.stop();
        logger.debug(`PerformanceSummary unmounted after ${time}ms`);
      }
    };
  }, []);
  
  // Measure first render time
  useEffect(() => {
    if (stopwatch.current) {
      const time = stopwatch.current.stop();
      setRenderTime(time);
    }
  }, []);
  
  // Handle refresh
  const onRefresh = async () => {
    setRefreshing(true);
    
    // Simulate a delay to show the refresh indicator
    await new Promise(resolve => setTimeout(resolve, 500));
    
    setRefreshing(false);
  };
  
  // Toggle section expansion
  const toggleSection = (section: string) => {
    setExpandedSections(prev => 
      prev.includes(section) 
        ? prev.filter(s => s !== section) 
        : [...prev, section]
    );
  };
  
  // Check if section is expanded
  const isSectionExpanded = (section: string) => expandedSections.includes(section);
  
  // Handle cache clear
  const handleClearCaches = async () => {
    const imgResult = await clearImageCache();
    await clearApiCache();
    alert(`Caches cleared ${imgResult ? 'successfully' : 'with some errors'}`);
  };
  
  // Get additional metrics
  const startupMetrics = getStartupMetrics();
  const connectionMetrics = getConnectionMetrics();
  
  // Format cache sizes
  const apiCacheSize = formatBytes(performanceMetrics.cacheStats.apiCacheSize);
  const imageCacheSize = formatBytes(performanceMetrics.cacheStats.imageCacheSize);
  const totalCacheSize = formatBytes(
    performanceMetrics.cacheStats.apiCacheSize + 
    performanceMetrics.cacheStats.imageCacheSize
  );
  
  // Render
  return (
    <ScrollView 
      style={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
        />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Performance Metrics</Text>
        {onClose && (
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Text style={styles.closeButtonText}>Close</Text>
          </TouchableOpacity>
        )}
      </View>
      
      {/* Summary Overview */}
      <View style={styles.summaryContainer}>
        <Text style={styles.summaryTitle}>Overview</Text>
        <View style={styles.metricsGrid}>
          <View style={styles.metricItem}>
            <Text style={styles.metricLabel}>App Startup</Text>
            <Text style={styles.metricValue}>
              {formatDuration(startupMetrics.startupDuration)}
            </Text>
          </View>
          
          <View style={styles.metricItem}>
            <Text style={styles.metricLabel}>Memory Usage</Text>
            <Text style={styles.metricValue}>
              {formatBytes(performanceMetrics.memoryUsage || 0)}
            </Text>
          </View>
          
          <View style={styles.metricItem}>
            <Text style={styles.metricLabel}>Cache Size</Text>
            <Text style={styles.metricValue}>{totalCacheSize}</Text>
          </View>
          
          <View style={styles.metricItem}>
            <Text style={styles.metricLabel}>Render Time</Text>
            <Text style={styles.metricValue}>{renderTime.toFixed(2)}ms</Text>
          </View>
        </View>
      </View>
      
      {/* Connection Section */}
      <TouchableOpacity 
        style={styles.sectionHeader} 
        onPress={() => toggleSection('connection')}
      >
        <Text style={styles.sectionTitle}>Connection Status</Text>
        <Text style={styles.expandIcon}>
          {isSectionExpanded('connection') ? '▼' : '▶'}
        </Text>
      </TouchableOpacity>
      
      {isSectionExpanded('connection') && (
        <View style={styles.sectionContent}>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Status:</Text>
            <Text style={[
              styles.infoValue, 
              connectionStatus.isOffline ? styles.statusOffline : styles.statusOnline
            ]}>
              {connectionStatus.isOffline ? 'Offline' : 'Online'}
            </Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Connection Type:</Text>
            <Text style={styles.infoValue}>
              {connectionStatus.connectionType || 'unknown'}
            </Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Connection Quality:</Text>
            <Text style={styles.infoValue}>
              {connectionStatus.connectionQuality}
            </Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Manual Offline Mode:</Text>
            <Text style={styles.infoValue}>
              {connectionStatus.isManualOfflineMode ? 'Enabled' : 'Disabled'}
            </Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Offline Activations:</Text>
            <Text style={styles.infoValue}>
              {connectionMetrics.offlineModeActivations}
            </Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Unreliable Connections:</Text>
            <Text style={styles.infoValue}>
              {connectionMetrics.unreliableConnectionCount}
            </Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Average Latency:</Text>
            <Text style={styles.infoValue}>
              {connectionMetrics.avgLatency.toFixed(2)}ms
            </Text>
          </View>
        </View>
      )}
      
      {/* Cache Section */}
      <TouchableOpacity 
        style={styles.sectionHeader} 
        onPress={() => toggleSection('cache')}
      >
        <Text style={styles.sectionTitle}>Cache Information</Text>
        <Text style={styles.expandIcon}>
          {isSectionExpanded('cache') ? '▼' : '▶'}
        </Text>
      </TouchableOpacity>
      
      {isSectionExpanded('cache') && (
        <View style={styles.sectionContent}>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>API Cache Size:</Text>
            <Text style={styles.infoValue}>{apiCacheSize}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Image Cache Size:</Text>
            <Text style={styles.infoValue}>{imageCacheSize}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Total Cache Size:</Text>
            <Text style={styles.infoValue}>{totalCacheSize}</Text>
          </View>
          
          <TouchableOpacity 
            style={styles.actionButton}
            onPress={handleClearCaches}
          >
            <Text style={styles.actionButtonText}>Clear All Caches</Text>
          </TouchableOpacity>
        </View>
      )}
      
      {/* Startup Section */}
      <TouchableOpacity 
        style={styles.sectionHeader} 
        onPress={() => toggleSection('startup')}
      >
        <Text style={styles.sectionTitle}>Startup Performance</Text>
        <Text style={styles.expandIcon}>
          {isSectionExpanded('startup') ? '▼' : '▶'}
        </Text>
      </TouchableOpacity>
      
      {isSectionExpanded('startup') && (
        <View style={styles.sectionContent}>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Startup Time:</Text>
            <Text style={styles.infoValue}>
              {formatDuration(startupMetrics.startupDuration)}
            </Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Cold Start:</Text>
            <Text style={styles.infoValue}>
              {startupMetrics.isColdStart ? 'Yes' : 'No'}
            </Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Startup Phase:</Text>
            <Text style={styles.infoValue}>{startupMetrics.startupPhase}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Assets Progress:</Text>
            <Text style={styles.infoValue}>
              {Math.round(startupMetrics.initialAssetsProgress * 100)}%
            </Text>
          </View>
        </View>
      )}
      
      {/* Device Section */}
      <TouchableOpacity 
        style={styles.sectionHeader} 
        onPress={() => toggleSection('device')}
      >
        <Text style={styles.sectionTitle}>Device Information</Text>
        <Text style={styles.expandIcon}>
          {isSectionExpanded('device') ? '▼' : '▶'}
        </Text>
      </TouchableOpacity>
      
      {isSectionExpanded('device') && (
        <View style={styles.sectionContent}>
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Platform:</Text>
            <Text style={styles.infoValue}>{Platform.OS}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>OS Version:</Text>
            <Text style={styles.infoValue}>{Platform.Version}</Text>
          </View>
          
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Memory Usage:</Text>
            <Text style={styles.infoValue}>
              {formatBytes(performanceMetrics.memoryUsage || 0)}
            </Text>
          </View>
          
          {performanceMetrics.batteryLevel !== undefined && (
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Battery Level:</Text>
              <Text style={styles.infoValue}>
                {Math.round(performanceMetrics.batteryLevel * 100)}%
              </Text>
            </View>
          )}
        </View>
      )}
      
      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Performance data last updated: {new Date().toLocaleTimeString()}
        </Text>
      </View>
    </ScrollView>
  );
};

// Styles
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9f9f9',
    padding: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#333',
  },
  closeButton: {
    padding: 8,
    backgroundColor: '#e0e0e0',
    borderRadius: 4,
  },
  closeButtonText: {
    fontSize: 14,
    color: '#333',
  },
  summaryContainer: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
    elevation: 2,
  },
  summaryTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 12,
    color: '#333',
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  metricItem: {
    width: '48%',
    marginBottom: 16,
  },
  metricLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  metricValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#e7f0ff',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#0056b3',
  },
  expandIcon: {
    fontSize: 14,
    color: '#0056b3',
  },
  sectionContent: {
    backgroundColor: 'white',
    borderRadius: 8,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
    elevation: 1,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  infoLabel: {
    fontSize: 14,
    color: '#666',
  },
  infoValue: {
    fontSize: 14,
    color: '#333',
    fontWeight: '500',
  },
  statusOnline: {
    color: '#2e7d32',
  },
  statusOffline: {
    color: '#c62828',
  },
  actionButton: {
    backgroundColor: '#0056b3',
    padding: 10,
    borderRadius: 4,
    alignItems: 'center',
    marginTop: 16,
  },
  actionButtonText: {
    color: 'white',
    fontWeight: '600',
  },
  footer: {
    marginTop: 8,
    marginBottom: 20,
    alignItems: 'center',
  },
  footerText: {
    fontSize: 12,
    color: '#666',
  },
});

export default PerformanceSummary;