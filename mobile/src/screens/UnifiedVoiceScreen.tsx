/**
 * Unified Voice Screen
 * 
 * Demonstrates the "One Voice, Zero Friction" experience
 * This is the primary interface while driving
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  SafeAreaView,
  Modal,
  Text,
  TouchableOpacity,
  ScrollView,
  Dimensions,
} from 'react-native';
import { UnifiedVoiceInterface } from '../components/voice/UnifiedVoiceInterface';
import { MapView } from '../components/MapView';
import { BlurView } from 'expo-blur';
import { MaterialIcons } from '@expo/vector-icons';
import unifiedVoiceOrchestrator from '../services/voice/unifiedVoiceOrchestrator';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export const UnifiedVoiceScreen: React.FC = () => {
  const [isDriving, setIsDriving] = useState(true);
  const [showVisualData, setShowVisualData] = useState(false);
  const [visualData, setVisualData] = useState<any>(null);
  const [selectedPersonality, setSelectedPersonality] = useState('wise_narrator');

  useEffect(() => {
    // Update orchestrator preferences
    unifiedVoiceOrchestrator.updatePreferences({
      personality: selectedPersonality,
    });
  }, [selectedPersonality]);

  const handleVisualDataReceived = (data: any) => {
    setVisualData(data);
    // Only show visual data if not driving (car stopped)
    if (!isDriving) {
      setShowVisualData(true);
    }
  };

  const dismissVisualData = () => {
    setShowVisualData(false);
    setVisualData(null);
  };

  const personalities = [
    { id: 'wise_narrator', name: 'Wise Narrator', icon: 'auto-stories' },
    { id: 'enthusiastic_buddy', name: 'Enthusiastic Buddy', icon: 'sentiment-very-satisfied' },
    { id: 'local_expert', name: 'Local Expert', icon: 'location-city' },
  ];

  return (
    <SafeAreaView style={styles.container}>
      {/* Map Background */}
      <View style={styles.mapContainer}>
        <MapView
          style={styles.map}
          showsUserLocation
          followsUserLocation={isDriving}
        />
      </View>

      {/* Voice Interface Overlay */}
      <View style={styles.voiceOverlay}>
        <UnifiedVoiceInterface
          isDriving={isDriving}
          onVisualDataReceived={handleVisualDataReceived}
        />
      </View>

      {/* Minimal Controls */}
      <View style={styles.controlsContainer}>
        {/* Driving Mode Toggle */}
        <TouchableOpacity
          style={[styles.controlButton, isDriving && styles.controlButtonActive]}
          onPress={() => setIsDriving(!isDriving)}
          accessibilityLabel={isDriving ? "Driving mode on" : "Driving mode off"}
        >
          <MaterialIcons
            name={isDriving ? "directions-car" : "directions-walk"}
            size={28}
            color={isDriving ? "#FFFFFF" : "#666"}
          />
        </TouchableOpacity>

        {/* Personality Selector (only when stopped) */}
        {!isDriving && (
          <View style={styles.personalitySelector}>
            {personalities.map((personality) => (
              <TouchableOpacity
                key={personality.id}
                style={[
                  styles.personalityButton,
                  selectedPersonality === personality.id && styles.personalityButtonActive
                ]}
                onPress={() => setSelectedPersonality(personality.id)}
                accessibilityLabel={`Select ${personality.name} personality`}
              >
                <MaterialIcons
                  name={personality.icon as any}
                  size={24}
                  color={selectedPersonality === personality.id ? "#FFFFFF" : "#666"}
                />
              </TouchableOpacity>
            ))}
          </View>
        )}
      </View>

      {/* Visual Data Modal (only when stopped) */}
      <Modal
        visible={showVisualData && !isDriving}
        animationType="slide"
        transparent
        onRequestClose={dismissVisualData}
      >
        <BlurView intensity={95} style={styles.modalOverlay}>
          <View style={styles.visualDataContainer}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Details</Text>
              <TouchableOpacity
                onPress={dismissVisualData}
                style={styles.closeButton}
                accessibilityLabel="Close details"
              >
                <MaterialIcons name="close" size={28} color="#333" />
              </TouchableOpacity>
            </View>
            
            <ScrollView style={styles.visualDataContent}>
              {visualData?.hotels && (
                <DataSection
                  title="Hotels"
                  items={visualData.hotels}
                  renderItem={(hotel: any) => (
                    <View style={styles.dataItem}>
                      <Text style={styles.dataItemTitle}>{hotel.name}</Text>
                      <Text style={styles.dataItemSubtitle}>
                        ${hotel.price_per_night}/night • {hotel.rating}★
                      </Text>
                      <Text style={styles.dataItemDescription}>
                        {hotel.amenities.slice(0, 3).join(' • ')}
                      </Text>
                    </View>
                  )}
                />
              )}
              
              {visualData?.restaurants && (
                <DataSection
                  title="Restaurants"
                  items={visualData.restaurants}
                  renderItem={(restaurant: any) => (
                    <View style={styles.dataItem}>
                      <Text style={styles.dataItemTitle}>{restaurant.name}</Text>
                      <Text style={styles.dataItemSubtitle}>
                        {restaurant.cuisine} • {restaurant.distance_miles} miles
                      </Text>
                      <Text style={styles.dataItemDescription}>
                        Known for: {restaurant.specialty}
                      </Text>
                    </View>
                  )}
                />
              )}
              
              {visualData?.activities && (
                <DataSection
                  title="Activities"
                  items={visualData.activities}
                  renderItem={(activity: any) => (
                    <View style={styles.dataItem}>
                      <Text style={styles.dataItemTitle}>{activity.name}</Text>
                      <Text style={styles.dataItemSubtitle}>
                        {activity.duration_hours}h • ${activity.price}
                      </Text>
                      <Text style={styles.dataItemDescription}>
                        {activity.description}
                      </Text>
                    </View>
                  )}
                />
              )}
            </ScrollView>
          </View>
        </BlurView>
      </Modal>
    </SafeAreaView>
  );
};

interface DataSectionProps {
  title: string;
  items: any[];
  renderItem: (item: any) => React.ReactNode;
}

const DataSection: React.FC<DataSectionProps> = ({ title, items, renderItem }) => (
  <View style={styles.dataSection}>
    <Text style={styles.dataSectionTitle}>{title}</Text>
    {items.map((item, index) => (
      <View key={index}>{renderItem(item)}</View>
    ))}
  </View>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  mapContainer: {
    ...StyleSheet.absoluteFillObject,
  },
  map: {
    ...StyleSheet.absoluteFillObject,
  },
  voiceOverlay: {
    ...StyleSheet.absoluteFillObject,
  },
  controlsContainer: {
    position: 'absolute',
    top: 50,
    right: 20,
    alignItems: 'flex-end',
  },
  controlButton: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  controlButtonActive: {
    backgroundColor: '#007AFF',
  },
  personalitySelector: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 20,
    padding: 8,
    marginTop: 8,
  },
  personalityButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    marginVertical: 4,
  },
  personalityButtonActive: {
    backgroundColor: '#007AFF',
  },
  modalOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  visualDataContainer: {
    backgroundColor: 'white',
    borderRadius: 20,
    width: SCREEN_WIDTH * 0.9,
    maxHeight: '80%',
    overflow: 'hidden',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  closeButton: {
    padding: 4,
  },
  visualDataContent: {
    padding: 20,
  },
  dataSection: {
    marginBottom: 24,
  },
  dataSectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#007AFF',
    marginBottom: 12,
  },
  dataItem: {
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  dataItemTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  dataItemSubtitle: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  dataItemDescription: {
    fontSize: 14,
    color: '#999',
  },
});