import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  StyleSheet,
  ActivityIndicator,
  Alert,
  ToastAndroid,
  Platform,
} from 'react-native';
import {
  Text,
  Button,
  Surface,
  Portal,
  Dialog,
  ProgressBar,
} from 'react-native-paper';
import MapView, { PROVIDER_GOOGLE, Region, Circle } from 'react-native-maps';
import { MaterialIcons } from '@expo/vector-icons';
import NetInfo from '@react-native-community/netinfo';
import { useNavigation } from '@react-navigation/native';

import { COLORS, SPACING } from '../theme';
import OfflineManager from '../services/OfflineManager';
import { formatBytes } from '../utils/formatters';

// Default region (USA centered)
const DEFAULT_REGION: Region = {
  latitude: 39.8283,
  longitude: -98.5795,
  latitudeDelta: 40,
  longitudeDelta: 40,
};

// Minimum download radius in km
const MIN_RADIUS_KM = 10;
// Maximum download radius in km
const MAX_RADIUS_KM = 100;
// Default radius
const DEFAULT_RADIUS_KM = 30;

const MapDownloadScreen: React.FC = () => {
  const [selectedRegion, setSelectedRegion] = useState<Region | null>(null);
  const [downloadRadius, setDownloadRadius] = useState(DEFAULT_RADIUS_KM);
  const [estimatedSize, setEstimatedSize] = useState<number | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [showDownloadDialog, setShowDownloadDialog] = useState(false);
  const [downloadComplete, setDownloadComplete] = useState(false);

  const mapRef = useRef<MapView>(null);
  const navigation = useNavigation();
  
  // Calculate size whenever region or radius changes
  useEffect(() => {
    if (selectedRegion) {
      calculateEstimatedSize();
    }
  }, [selectedRegion, downloadRadius]);

  const handleMapLongPress = (event: any) => {
    // Set the selected region based on the long press coordinates
    const { coordinate } = event.nativeEvent;
    setSelectedRegion({
      latitude: coordinate.latitude,
      longitude: coordinate.longitude,
      latitudeDelta: 0.1,
      longitudeDelta: 0.1,
    });
    
    // Move map to the selected location
    mapRef.current?.animateToRegion({
      latitude: coordinate.latitude,
      longitude: coordinate.longitude,
      latitudeDelta: 0.2,
      longitudeDelta: 0.2,
    }, 500);
  };
  
  const calculateEstimatedSize = async () => {
    if (!selectedRegion) return;
    
    setIsCalculating(true);
    try {
      // Use the OfflineManager to calculate size
      const radiusInMeters = downloadRadius * 1000;
      const size = await OfflineManager.estimateRegionSize({
        latitude: selectedRegion.latitude,
        longitude: selectedRegion.longitude,
        radius: radiusInMeters,
        zoom: 14, // Detail level
      });
      
      setEstimatedSize(size);
    } catch (error) {
      console.error('Error calculating size:', error);
      showToast('Failed to calculate download size');
    } finally {
      setIsCalculating(false);
    }
  };
  
  const handleDownload = async () => {
    // Check if we have a selected region
    if (!selectedRegion) {
      showToast('Please select a region first');
      return;
    }
    
    // Check network connection
    const netInfo = await NetInfo.fetch();
    
    if (!netInfo.isConnected) {
      Alert.alert(
        'No Connection',
        'Internet connection is required to download maps',
        [{ text: 'OK' }]
      );
      return;
    }
    
    // Check if cellular and if downloads are allowed on cellular
    if (netInfo.type === 'cellular') {
      const wifiOnly = true; // Should be fetched from settings in real app
      
      if (wifiOnly) {
        Alert.alert(
          'Cellular Connection',
          'You are on cellular data and your settings allow downloads only on Wi-Fi. Change settings?',
          [
            {
              text: 'Yes, Download Anyway',
              onPress: () => startDownload(),
            },
            {
              text: 'Cancel',
              style: 'cancel',
            },
          ]
        );
        return;
      }
    }
    
    // Show download confirmation
    setShowDownloadDialog(true);
  };
  
  const startDownload = async () => {
    if (!selectedRegion) return;
    
    setShowDownloadDialog(false);
    setIsDownloading(true);
    setDownloadComplete(false);
    
    try {
      const radiusInMeters = downloadRadius * 1000;
      
      await OfflineManager.downloadRegion({
        id: `region_${Date.now()}`,
        region: {
          latitude: selectedRegion.latitude,
          longitude: selectedRegion.longitude,
          radius: radiusInMeters,
        },
        minZoom: 10,
        maxZoom: 15,
        onProgress: (progress) => {
          setDownloadProgress(progress);
        },
      });
      
      setDownloadComplete(true);
      showToast('Map region downloaded successfully');
    } catch (error) {
      console.error('Error downloading region:', error);
      Alert.alert(
        'Download Failed',
        'Failed to download the map region. Please try again.',
        [{ text: 'OK' }]
      );
    } finally {
      setIsDownloading(false);
    }
  };
  
  const handleReturn = () => {
    navigation.goBack();
  };
  
  const handleCancelDownload = () => {
    // Cancel download if in progress
    if (isDownloading) {
      OfflineManager.cancelDownload();
    }
    setIsDownloading(false);
  };
  
  const showToast = (message: string) => {
    if (Platform.OS === 'android') {
      ToastAndroid.show(message, ToastAndroid.SHORT);
    }
    // On iOS, you might use Alert or a custom component
  };
  
  return (
    <View style={styles.container}>
      <MapView
        ref={mapRef}
        style={styles.map}
        provider={PROVIDER_GOOGLE}
        initialRegion={DEFAULT_REGION}
        onLongPress={handleMapLongPress}
      >
        {selectedRegion && (
          <Circle
            center={{
              latitude: selectedRegion.latitude,
              longitude: selectedRegion.longitude,
            }}
            radius={downloadRadius * 1000}
            strokeWidth={2}
            strokeColor="rgba(65, 105, 225, 0.5)"
            fillColor="rgba(65, 105, 225, 0.2)"
          />
        )}
      </MapView>
      
      <Surface style={styles.controlPanel}>
        <Text style={styles.title}>Download Map Area</Text>
        
        {!selectedRegion ? (
          <View style={styles.instructions}>
            <MaterialIcons name="touch-app" size={24} color={COLORS.primary} />
            <Text style={styles.instructionText}>
              Long press on the map to select an area to download
            </Text>
          </View>
        ) : (
          <>
            <Text style={styles.sectionTitle}>Download Radius</Text>
            <View style={styles.radiusControl}>
              <MaterialIcons name="zoom-out-map" size={20} color={COLORS.text} />
              <Text style={styles.radiusText}>{downloadRadius} km</Text>
              <MaterialIcons name="zoom-in-map" size={20} color={COLORS.text} />
            </View>
            <ProgressBar
              progress={downloadRadius / MAX_RADIUS_KM}
              color={COLORS.primary}
              style={styles.radiusBar}
            />
            <View style={styles.buttonRow}>
              <Button
                mode="outlined"
                onPress={() => setDownloadRadius(Math.max(MIN_RADIUS_KM, downloadRadius - 10))}
                disabled={downloadRadius <= MIN_RADIUS_KM || isDownloading}
                style={styles.radiusButton}
              >
                - 10 km
              </Button>
              <Button
                mode="outlined"
                onPress={() => setDownloadRadius(Math.min(MAX_RADIUS_KM, downloadRadius + 10))}
                disabled={downloadRadius >= MAX_RADIUS_KM || isDownloading}
                style={styles.radiusButton}
              >
                + 10 km
              </Button>
            </View>
            
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Estimated Size:</Text>
              {isCalculating ? (
                <ActivityIndicator size="small" color={COLORS.primary} />
              ) : (
                <Text style={styles.infoValue}>
                  {estimatedSize ? formatBytes(estimatedSize) : 'Unknown'}
                </Text>
              )}
            </View>
            
            {isDownloading ? (
              <>
                <Text style={styles.progressLabel}>
                  Downloading... {Math.round(downloadProgress * 100)}%
                </Text>
                <ProgressBar
                  progress={downloadProgress}
                  color={COLORS.primary}
                  style={styles.progressBar}
                />
                <Button
                  mode="contained"
                  color={COLORS.error}
                  onPress={handleCancelDownload}
                  style={styles.downloadButton}
                >
                  Cancel Download
                </Button>
              </>
            ) : downloadComplete ? (
              <>
                <View style={styles.successMessage}>
                  <MaterialIcons name="check-circle" size={24} color={COLORS.success} />
                  <Text style={[styles.successText, { color: COLORS.success }]}>
                    Download Complete
                  </Text>
                </View>
                <Button
                  mode="contained"
                  color={COLORS.primary}
                  onPress={handleReturn}
                  style={styles.downloadButton}
                >
                  Return to Settings
                </Button>
              </>
            ) : (
              <Button
                mode="contained"
                color={COLORS.primary}
                onPress={handleDownload}
                style={styles.downloadButton}
                disabled={!selectedRegion || isCalculating}
              >
                Download This Area
              </Button>
            )}
          </>
        )}
      </Surface>
      
      {/* Download confirmation dialog */}
      <Portal>
        <Dialog
          visible={showDownloadDialog}
          onDismiss={() => setShowDownloadDialog(false)}
        >
          <Dialog.Title>Download Map Area</Dialog.Title>
          <Dialog.Content>
            <Text>You are about to download:</Text>
            <Text style={styles.dialogHighlight}>
              {downloadRadius} km radius area
            </Text>
            <Text style={styles.dialogHighlight}>
              Estimated size: {estimatedSize ? formatBytes(estimatedSize) : 'Unknown'}
            </Text>
            <Text style={styles.dialogWarning}>
              Map downloads can consume a significant amount of storage space and data. Please ensure you have enough storage available.
            </Text>
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setShowDownloadDialog(false)}>Cancel</Button>
            <Button onPress={startDownload}>Download</Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    flex: 1,
  },
  controlPanel: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: SPACING.medium,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    elevation: 4,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: SPACING.medium,
    textAlign: 'center',
  },
  instructions: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: SPACING.medium,
  },
  instructionText: {
    marginLeft: SPACING.small,
    fontSize: 16,
    flex: 1,
  },
  sectionTitle: {
    fontSize: 16,
    marginTop: SPACING.small,
    marginBottom: SPACING.small,
  },
  radiusControl: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.small,
  },
  radiusText: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  radiusBar: {
    height: 8,
    borderRadius: 4,
    marginBottom: SPACING.medium,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.medium,
  },
  radiusButton: {
    flex: 1,
    marginHorizontal: SPACING.xsmall,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.medium,
    paddingVertical: SPACING.small,
    paddingHorizontal: SPACING.small,
    backgroundColor: COLORS.surface,
    borderRadius: 4,
  },
  infoLabel: {
    fontSize: 14,
  },
  infoValue: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  progressLabel: {
    textAlign: 'center',
    marginBottom: SPACING.small,
  },
  progressBar: {
    height: 10,
    borderRadius: 5,
    marginBottom: SPACING.medium,
  },
  downloadButton: {
    marginTop: SPACING.small,
  },
  successMessage: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.medium,
  },
  successText: {
    marginLeft: SPACING.small,
    fontSize: 16,
    fontWeight: 'bold',
  },
  dialogHighlight: {
    fontSize: 16,
    fontWeight: 'bold',
    marginVertical: SPACING.small,
  },
  dialogWarning: {
    marginTop: SPACING.medium,
    color: COLORS.warning,
  },
});

export default MapDownloadScreen; 