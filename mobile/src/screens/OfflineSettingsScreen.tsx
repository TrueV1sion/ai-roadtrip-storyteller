import React, { useState, useEffect } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  ToastAndroid,
  Platform,
} from 'react-native';
import {
  Text,
  Surface,
  Button,
  List,
  Divider,
  Slider,
  Switch,
  IconButton,
  Banner,
} from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import { format } from 'date-fns';

import { COLORS, SPACING } from '../theme';
import OfflineManager from '../services/OfflineManager';
import { formatBytes } from '../utils/formatters';

const OfflineSettingsScreen: React.FC = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [storageStats, setStorageStats] = useState<any>(null);
  const [downloadedRegions, setDownloadedRegions] = useState<any[]>([]);
  const [downloadedRoutes, setDownloadedRoutes] = useState<any[]>([]);
  const [maxStorage, setMaxStorage] = useState(500);
  const [autoDownloadEnabled, setAutoDownloadEnabled] = useState(false);
  const [wifiOnlyEnabled, setWifiOnlyEnabled] = useState(true);
  const [deletingItem, setDeletingItem] = useState<string | null>(null);
  const [showBanner, setShowBanner] = useState(false);
  
  const navigation = useNavigation();
  
  // Load data on mount
  useEffect(() => {
    loadData();
  }, []);
  
  const loadData = async () => {
    try {
      setIsLoading(true);
      
      // Initialize OfflineManager
      await OfflineManager.initialize();
      
      // Load storage stats
      const stats = await OfflineManager.getStorageStats();
      setStorageStats(stats);
      setMaxStorage(Math.floor(stats.maxStorage / (1024 * 1024)));
      
      // Load downloaded regions
      const regions = await OfflineManager.getDownloadedRegions();
      setDownloadedRegions(regions);
      
      // Load downloaded routes
      const routes = await OfflineManager.getDownloadedRoutes();
      setDownloadedRoutes(routes);
      
      // Load preferences
      const autoDownload = await getPreference('offline_auto_download', 'false');
      setAutoDownloadEnabled(autoDownload === 'true');
      
      const wifiOnly = await getPreference('offline_wifi_only', 'true');
      setWifiOnlyEnabled(wifiOnly === 'true');
      
      // Show banner if storage is almost full
      if (stats.percentUsed > 85) {
        setShowBanner(true);
      }
    } catch (error) {
      logger.error('Error loading offline data:', error);
      showToast('Failed to load offline data');
    } finally {
      setIsLoading(false);
    }
  };
  
  const getPreference = async (key: string, defaultValue: string): Promise<string> => {
    try {
      // In a real app, this would use AsyncStorage
      return defaultValue; // Placeholder
    } catch (error) {
      logger.error(`Error getting preference ${key}:`, error);
      return defaultValue;
    }
  };
  
  const handleMaxStorageChange = async (value: number) => {
    try {
      const newMaxStorage = value * 1024 * 1024; // Convert MB to bytes
      await OfflineManager.setMaxStorage(newMaxStorage);
      
      // Refresh stats
      const stats = await OfflineManager.getStorageStats();
      setStorageStats(stats);
      
      showToast(`Max storage set to ${value}MB`);
    } catch (error) {
      logger.error('Error setting max storage:', error);
      showToast('Failed to update storage limit');
    }
  };
  
  const handleAutoDownloadToggle = async () => {
    const newValue = !autoDownloadEnabled;
    setAutoDownloadEnabled(newValue);
    
    // In a real app, save to AsyncStorage
    showToast(`Auto-download ${newValue ? 'enabled' : 'disabled'}`);
  };
  
  const handleWifiOnlyToggle = async () => {
    const newValue = !wifiOnlyEnabled;
    setWifiOnlyEnabled(newValue);
    
    // In a real app, save to AsyncStorage
    showToast(`WiFi-only ${newValue ? 'enabled' : 'disabled'}`);
  };
  
  const handleDeleteRegion = async (regionId: string) => {
    try {
      setDeletingItem(regionId);
      await OfflineManager.deleteRegion(regionId);
      
      // Refresh data
      const regions = await OfflineManager.getDownloadedRegions();
      setDownloadedRegions(regions);
      
      const stats = await OfflineManager.getStorageStats();
      setStorageStats(stats);
      
      showToast('Map region deleted');
    } catch (error) {
      logger.error('Error deleting region:', error);
      showToast('Failed to delete map region');
    } finally {
      setDeletingItem(null);
    }
  };
  
  const handleDeleteRoute = async (routeId: string) => {
    try {
      setDeletingItem(routeId);
      await OfflineManager.deleteRoute(routeId);
      
      // Refresh data
      const routes = await OfflineManager.getDownloadedRoutes();
      setDownloadedRoutes(routes);
      
      const stats = await OfflineManager.getStorageStats();
      setStorageStats(stats);
      
      showToast('Route deleted');
    } catch (error) {
      logger.error('Error deleting route:', error);
      showToast('Failed to delete route');
    } finally {
      setDeletingItem(null);
    }
  };
  
  const handleDownloadNewArea = () => {
    // Navigate to map selection screen
    navigation.navigate('MapDownload' as never);
  };
  
  const showToast = (message: string) => {
    if (Platform.OS === 'android') {
      ToastAndroid.show(message, ToastAndroid.SHORT);
    }
    // On iOS, you might use Alert or a custom component
  };
  
  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>Loading offline data...</Text>
      </View>
    );
  }
  
  return (
    <ScrollView style={styles.container}>
      {/* Storage warning banner */}
      {showBanner && (
        <Banner
          visible={showBanner}
          icon={({ size }) => (
            <MaterialIcons name="storage" size={size} color={COLORS.warning} />
          )}
          actions={[
            {
              label: 'Free Up Space',
              onPress: () => setShowBanner(false),
            },
            {
              label: 'Dismiss',
              onPress: () => setShowBanner(false),
            },
          ]}
        >
          Your offline storage is almost full. Consider deleting some offline content.
        </Banner>
      )}
      
      {/* Storage usage */}
      <Surface style={styles.section}>
        <Text style={styles.sectionTitle}>Storage Usage</Text>
        
        {storageStats && (
          <>
            <View style={styles.storageBarContainer}>
              <View 
                style={[
                  styles.storageBar, 
                  { width: `${storageStats.percentUsed}%` },
                  storageStats.percentUsed > 85 ? styles.storageBarWarning : null
                ]} 
              />
            </View>
            
            <Text style={styles.storageText}>
              {formatBytes(storageStats.totalStorageUsed)} used of {formatBytes(storageStats.maxStorage)}
              {' '}({Math.round(storageStats.percentUsed)}%)
            </Text>
            
            <View style={styles.storageBreakdown}>
              <View style={styles.storageItem}>
                <MaterialIcons name="map" size={24} color={COLORS.primary} />
                <Text style={styles.storageItemText}>
                  Maps: {formatBytes(storageStats.maps.sizeBytes)}
                </Text>
              </View>
              
              <View style={styles.storageItem}>
                <MaterialIcons name="directions" size={24} color={COLORS.primary} />
                <Text style={styles.storageItemText}>
                  Routes: {formatBytes(storageStats.routes.sizeBytes)}
                </Text>
              </View>
            </View>
          </>
        )}
        
        <Text style={styles.settingLabel}>Maximum Storage Limit</Text>
        <Text style={styles.settingValue}>{maxStorage} MB</Text>
        <Slider
          value={maxStorage}
          minimumValue={100}
          maximumValue={2000}
          step={100}
          onValueChange={setMaxStorage}
          onSlidingComplete={handleMaxStorageChange}
          minimumTrackTintColor={COLORS.primary}
          maximumTrackTintColor={COLORS.border}
          thumbTintColor={COLORS.primary}
          style={styles.slider}
        />
      </Surface>
      
      {/* Offline settings */}
      <Surface style={styles.section}>
        <Text style={styles.sectionTitle}>Offline Settings</Text>
        
        <View style={styles.settingRow}>
          <View style={styles.settingLabelContainer}>
            <MaterialIcons name="cloud-download" size={24} color={COLORS.text} />
            <Text style={styles.settingRowLabel}>Auto-download trip routes</Text>
          </View>
          <Switch
            value={autoDownloadEnabled}
            onValueChange={handleAutoDownloadToggle}
            color={COLORS.primary}
          />
        </View>
        
        <Text style={styles.settingDescription}>
          Automatically download routes when you plan a trip
        </Text>
        
        <Divider style={styles.divider} />
        
        <View style={styles.settingRow}>
          <View style={styles.settingLabelContainer}>
            <MaterialIcons name="wifi" size={24} color={COLORS.text} />
            <Text style={styles.settingRowLabel}>Download on Wi-Fi only</Text>
          </View>
          <Switch
            value={wifiOnlyEnabled}
            onValueChange={handleWifiOnlyToggle}
            color={COLORS.primary}
          />
        </View>
        
        <Text style={styles.settingDescription}>
          Prevent downloading maps and routes over cellular data
        </Text>
      </Surface>
      
      {/* Downloaded maps */}
      <Surface style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Downloaded Maps</Text>
          <Text style={styles.itemCount}>{downloadedRegions.length} maps</Text>
        </View>
        
        {downloadedRegions.length === 0 ? (
          <View style={styles.emptyState}>
            <MaterialIcons name="map" size={48} color={COLORS.border} />
            <Text style={styles.emptyStateText}>No offline maps downloaded</Text>
          </View>
        ) : (
          downloadedRegions.map((region: any) => (
            <List.Item
              key={region.id || Math.random().toString()}
              title={`Map Area ${region.region.latitude.toFixed(2)}, ${region.region.longitude.toFixed(2)}`}
              description={`${formatBytes(region.sizeBytes)} • Downloaded ${format(new Date(region.timeStamp), 'MMM d, yyyy')}`}
              left={props => <List.Icon {...props} icon="map" />}
              right={props => (
                deletingItem === region.id ? (
                  <ActivityIndicator size="small" color={COLORS.primary} />
                ) : (
                  <IconButton
                    {...props}
                    icon="delete"
                    onPress={() => handleDeleteRegion(region.id)}
                  />
                )
              )}
            />
          ))
        )}
        
        <Button
          mode="outlined"
          icon="map-plus"
          onPress={handleDownloadNewArea}
          style={styles.button}
        >
          Download New Map Area
        </Button>
      </Surface>
      
      {/* Downloaded routes */}
      <Surface style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Downloaded Routes</Text>
          <Text style={styles.itemCount}>{downloadedRoutes.length} routes</Text>
        </View>
        
        {downloadedRoutes.length === 0 ? (
          <View style={styles.emptyState}>
            <MaterialIcons name="directions" size={48} color={COLORS.border} />
            <Text style={styles.emptyStateText}>No offline routes downloaded</Text>
          </View>
        ) : (
          downloadedRoutes.map((route: any) => (
            <List.Item
              key={route.id || Math.random().toString()}
              title={`${route.originName} to ${route.destinationName}`}
              description={`${formatBytes(route.sizeBytes)} • Downloaded ${format(new Date(route.timeStamp), 'MMM d, yyyy')}`}
              left={props => <List.Icon {...props} icon="directions" />}
              right={props => (
                deletingItem === route.id ? (
                  <ActivityIndicator size="small" color={COLORS.primary} />
                ) : (
                  <IconButton
                    {...props}
                    icon="delete"
                    onPress={() => handleDeleteRoute(route.id)}
                  />
                )
              )}
            />
          ))
        )}
      </Surface>
      
      {/* Maintenance */}
      <Surface style={styles.section}>
        <Text style={styles.sectionTitle}>Maintenance</Text>
        
        <Button
          mode="outlined"
          icon="broom"
          onPress={() => {/* Clear cache */}}
          style={styles.button}
        >
          Clear Cache
        </Button>
        
        <Button
          mode="outlined"
          icon="refresh"
          onPress={() => loadData()}
          style={[styles.button, styles.refreshButton]}
        >
          Refresh Storage Stats
        </Button>
      </Surface>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.background,
  },
  loadingText: {
    marginTop: SPACING.small,
    fontSize: 16,
  },
  section: {
    margin: SPACING.medium,
    padding: SPACING.medium,
    borderRadius: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: SPACING.medium,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.medium,
  },
  itemCount: {
    fontSize: 14,
    color: COLORS.textSecondary,
  },
  storageBarContainer: {
    height: 12,
    backgroundColor: COLORS.surface,
    borderRadius: 6,
    overflow: 'hidden',
    marginBottom: SPACING.small,
  },
  storageBar: {
    height: '100%',
    backgroundColor: COLORS.primary,
    borderRadius: 6,
  },
  storageBarWarning: {
    backgroundColor: COLORS.warning,
  },
  storageText: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginBottom: SPACING.medium,
  },
  storageBreakdown: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: SPACING.medium,
  },
  storageItem: {
    alignItems: 'center',
  },
  storageItemText: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginTop: SPACING.xsmall,
  },
  settingLabel: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginBottom: SPACING.xsmall,
  },
  settingValue: {
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  slider: {
    marginTop: SPACING.small,
    marginBottom: SPACING.small,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: SPACING.small,
  },
  settingLabelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  settingRowLabel: {
    fontSize: 16,
    marginLeft: SPACING.small,
  },
  settingDescription: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginBottom: SPACING.medium,
    marginLeft: SPACING.large + SPACING.small,
  },
  divider: {
    marginVertical: SPACING.small,
  },
  emptyState: {
    alignItems: 'center',
    padding: SPACING.large,
  },
  emptyStateText: {
    marginTop: SPACING.medium,
    fontSize: 16,
    color: COLORS.textSecondary,
    textAlign: 'center',
  },
  button: {
    marginTop: SPACING.medium,
  },
  refreshButton: {
    marginTop: SPACING.small,
  },
});

export default OfflineSettingsScreen; 