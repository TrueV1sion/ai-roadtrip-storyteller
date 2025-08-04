import React, { useState, useEffect } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Alert,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { LinearGradient } from 'expo-linear-gradient';

import { Card, Button, Header } from '../components';
import { gameApi } from '../services/api/gameApi';
import { useAuth } from '../contexts/AuthContext';
import { useLocation } from '../hooks/useLocation';

const { width } = Dimensions.get('window');

interface ScavengerItem {
  id: string;
  name: string;
  description: string;
  hint: string;
  points: number;
  location_clue?: string;
  photo_required: boolean;
  found: boolean;
  found_by?: string;
}

interface GameSession {
  session_id: string;
  players: Array<{ id: string; name: string; score: number }>;
}

export const ScavengerHuntScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { user } = useAuth();
  const { currentLocation } = useLocation();
  
  const [session, setSession] = useState<GameSession | null>(null);
  const [items, setItems] = useState<ScavengerItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<ScavengerItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [score, setScore] = useState(0);
  const [foundCount, setFoundCount] = useState(0);
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [showHint, setShowHint] = useState<{ [key: string]: boolean }>({});

  useEffect(() => {
    initializeHunt();
  }, []);

  const initializeHunt = async () => {
    try {
      setLoading(true);
      
      // Create game session
      const sessionData = await gameApi.createSession({
        game_type: 'scavenger_hunt',
        players: [{ id: user.id, name: user.name, age: user.age || 25 }],
        location: currentLocation || { lat: 0, lng: 0, name: 'Unknown' },
        theme: route.params?.theme,
      });
      
      setSession(sessionData);
      
      // Get hunt items
      const huntItems = await gameApi.getScavengerItems(sessionData.session_id);
      setItems(huntItems);
      
      // Calculate initial stats
      const found = huntItems.filter(item => item.found).length;
      setFoundCount(found);
    } catch (error) {
      logger.error('Error initializing hunt:', error);
      Alert.alert('Error', 'Failed to start scavenger hunt');
      navigation.goBack();
    } finally {
      setLoading(false);
    }
  };

  const handleItemPress = (item: ScavengerItem) => {
    if (item.found) {
      Alert.alert('Already Found', `This item was found by ${item.found_by}`);
      return;
    }
    setSelectedItem(item);
  };

  const handleTakePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    
    if (status !== 'granted') {
      Alert.alert('Permission Denied', 'Camera access is required to take photos');
      return;
    }
    
    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.7,
    });
    
    if (!result.canceled) {
      setPhotoUri(result.assets[0].uri);
    }
  };

  const handleSubmitFind = async () => {
    if (!selectedItem) return;
    
    if (selectedItem.photo_required && !photoUri) {
      Alert.alert('Photo Required', 'Please take a photo of this item');
      return;
    }
    
    setSubmitting(true);
    
    try {
      const result = await gameApi.markItemFound(session!.session_id, {
        item_id: selectedItem.id,
        photo_url: photoUri || undefined,
      });
      
      if (result.success) {
        // Update local state
        setItems(items.map(item => 
          item.id === selectedItem.id 
            ? { ...item, found: true, found_by: user.name }
            : item
        ));
        
        setScore(score + result.points_earned);
        setFoundCount(result.total_found);
        
        Alert.alert(
          '🎉 Item Found!',
          `You earned ${result.points_earned} points!\n\n${result.total_found}/${result.total_items} items found.`,
          [{ text: 'OK', onPress: () => closeItemModal() }]
        );
        
        // Check if all items found
        if (result.total_found === result.total_items) {
          setTimeout(() => endHunt(), 1000);
        }
      }
    } catch (error) {
      logger.error('Error submitting find:', error);
      Alert.alert('Error', 'Failed to submit find');
    } finally {
      setSubmitting(false);
    }
  };

  const closeItemModal = () => {
    setSelectedItem(null);
    setPhotoUri(null);
  };

  const endHunt = async () => {
    try {
      const results = await gameApi.endSession(session!.session_id);
      
      navigation.navigate('GameResults', {
        results,
        gameType: 'scavenger_hunt',
        score,
        itemsFound: foundCount,
        totalItems: items.length,
      });
    } catch (error) {
      logger.error('Error ending hunt:', error);
      navigation.goBack();
    }
  };

  const toggleHint = (itemId: string) => {
    setShowHint(prev => ({ ...prev, [itemId]: !prev[itemId] }));
  };

  const getDistanceFromClue = (clue?: string) => {
    // This would calculate actual distance based on location clue
    // For now, return a placeholder
    if (!clue) return null;
    return '~0.5 miles';
  };

  const renderItem = (item: ScavengerItem) => (
    <TouchableOpacity
      key={item.id}
      style={styles.itemCard}
      onPress={() => handleItemPress(item)}
      disabled={item.found}
    >
      <Card style={[styles.card, item.found && styles.foundCard]}>
        <View style={styles.itemHeader}>
          <View style={styles.itemInfo}>
            <Text style={[styles.itemName, item.found && styles.foundText]}>
              {item.name}
            </Text>
            <Text style={styles.pointsText}>{item.points} points</Text>
          </View>
          {item.found && (
            <Ionicons name="checkmark-circle" size={32} color="#4CAF50" />
          )}
        </View>
        
        <Text style={[styles.description, item.found && styles.foundText]}>
          {item.description}
        </Text>
        
        {!item.found && (
          <View style={styles.itemActions}>
            <TouchableOpacity
              style={styles.hintButton}
              onPress={() => toggleHint(item.id)}
            >
              <Ionicons name="help-circle-outline" size={20} color="#007AFF" />
              <Text style={styles.hintButtonText}>
                {showHint[item.id] ? 'Hide Hint' : 'Show Hint'}
              </Text>
            </TouchableOpacity>
            
            {item.location_clue && (
              <Text style={styles.distanceText}>
                {getDistanceFromClue(item.location_clue)}
              </Text>
            )}
          </View>
        )}
        
        {showHint[item.id] && !item.found && (
          <View style={styles.hintContainer}>
            <Text style={styles.hintText}>{item.hint}</Text>
            {item.location_clue && (
              <Text style={styles.locationClue}>
                <Ionicons name="location" size={14} color="#666" />
                {' '}{item.location_clue}
              </Text>
            )}
          </View>
        )}
        
        {item.photo_required && (
          <View style={styles.photoIndicator}>
            <Ionicons name="camera" size={16} color="#666" />
            <Text style={styles.photoText}>Photo required</Text>
          </View>
        )}
      </Card>
    </TouchableOpacity>
  );

  const renderItemModal = () => {
    if (!selectedItem) return null;
    
    return (
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>{selectedItem.name}</Text>
            <TouchableOpacity onPress={closeItemModal}>
              <Ionicons name="close" size={24} color="#333" />
            </TouchableOpacity>
          </View>
          
          <ScrollView style={styles.modalBody}>
            <Text style={styles.modalDescription}>{selectedItem.description}</Text>
            
            <View style={styles.modalSection}>
              <Text style={styles.sectionTitle}>Hint:</Text>
              <Text style={styles.modalHint}>{selectedItem.hint}</Text>
            </View>
            
            {selectedItem.location_clue && (
              <View style={styles.modalSection}>
                <Text style={styles.sectionTitle}>Location:</Text>
                <Text style={styles.modalLocationClue}>{selectedItem.location_clue}</Text>
              </View>
            )}
            
            {selectedItem.photo_required && (
              <View style={styles.photoSection}>
                <Text style={styles.sectionTitle}>Photo Evidence Required</Text>
                {photoUri ? (
                  <View style={styles.photoPreview}>
                    <Image source={{ uri: photoUri }} style={styles.photo} />
                    <TouchableOpacity
                      style={styles.retakeButton}
                      onPress={handleTakePhoto}
                    >
                      <Text style={styles.retakeText}>Retake Photo</Text>
                    </TouchableOpacity>
                  </View>
                ) : (
                  <TouchableOpacity
                    style={styles.cameraButton}
                    onPress={handleTakePhoto}
                  >
                    <Ionicons name="camera" size={48} color="#007AFF" />
                    <Text style={styles.cameraText}>Take Photo</Text>
                  </TouchableOpacity>
                )}
              </View>
            )}
          </ScrollView>
          
          <View style={styles.modalActions}>
            <Button
              title="I Found It!"
              onPress={handleSubmitFind}
              loading={submitting}
              disabled={submitting || (selectedItem.photo_required && !photoUri)}
              style={styles.foundButton}
            />
          </View>
        </View>
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading scavenger hunt...</Text>
      </View>
    );
  }

  return (
    <LinearGradient colors={['#E8F5E9', '#C8E6C9']} style={styles.container}>
      <Header
        title="Scavenger Hunt"
        leftAction={() => {
          Alert.alert(
            'Exit Hunt',
            'Are you sure you want to exit?',
            [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Exit', onPress: () => endHunt() },
            ]
          );
        }}
      />
      
      <View style={styles.statsContainer}>
        <View style={styles.statItem}>
          <MaterialCommunityIcons name="treasure-chest" size={24} color="#388E3C" />
          <Text style={styles.statValue}>{foundCount}/{items.length}</Text>
          <Text style={styles.statLabel}>Found</Text>
        </View>
        <View style={styles.statItem}>
          <Ionicons name="star" size={24} color="#FFC107" />
          <Text style={styles.statValue}>{score}</Text>
          <Text style={styles.statLabel}>Points</Text>
        </View>
        <View style={styles.statItem}>
          <Ionicons name="time" size={24} color="#2196F3" />
          <Text style={styles.statValue}>--:--</Text>
          <Text style={styles.statLabel}>Time</Text>
        </View>
      </View>
      
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {items.map(renderItem)}
      </ScrollView>
      
      {renderItemModal()}
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 16,
    paddingHorizontal: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 12,
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginVertical: 4,
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 16,
    paddingBottom: 20,
  },
  itemCard: {
    marginBottom: 16,
  },
  card: {
    padding: 0,
    overflow: 'hidden',
  },
  foundCard: {
    opacity: 0.7,
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    paddingBottom: 8,
  },
  itemInfo: {
    flex: 1,
  },
  itemName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  foundText: {
    color: '#999',
  },
  pointsText: {
    fontSize: 14,
    color: '#007AFF',
    fontWeight: '600',
  },
  description: {
    fontSize: 14,
    color: '#666',
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  itemActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingBottom: 8,
  },
  hintButton: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  hintButtonText: {
    marginLeft: 4,
    fontSize: 14,
    color: '#007AFF',
  },
  distanceText: {
    fontSize: 12,
    color: '#666',
  },
  hintContainer: {
    backgroundColor: '#F5F5F5',
    padding: 16,
    marginTop: 8,
  },
  hintText: {
    fontSize: 14,
    color: '#333',
    fontStyle: 'italic',
  },
  locationClue: {
    fontSize: 12,
    color: '#666',
    marginTop: 8,
  },
  photoIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F5F5F5',
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  photoText: {
    marginLeft: 8,
    fontSize: 12,
    color: '#666',
  },
  modalOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: 'white',
    width: width - 32,
    maxHeight: '80%',
    borderRadius: 16,
    overflow: 'hidden',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    flex: 1,
  },
  modalBody: {
    padding: 16,
  },
  modalDescription: {
    fontSize: 16,
    color: '#333',
    lineHeight: 24,
    marginBottom: 16,
  },
  modalSection: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#666',
    marginBottom: 8,
  },
  modalHint: {
    fontSize: 14,
    color: '#333',
    fontStyle: 'italic',
  },
  modalLocationClue: {
    fontSize: 14,
    color: '#333',
  },
  photoSection: {
    marginTop: 16,
  },
  cameraButton: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F5F5F5',
    paddingVertical: 40,
    borderRadius: 12,
    marginTop: 8,
  },
  cameraText: {
    marginTop: 8,
    fontSize: 16,
    color: '#007AFF',
  },
  photoPreview: {
    marginTop: 8,
  },
  photo: {
    width: '100%',
    height: 200,
    borderRadius: 12,
    marginBottom: 8,
  },
  retakeButton: {
    alignItems: 'center',
    paddingVertical: 8,
  },
  retakeText: {
    fontSize: 14,
    color: '#007AFF',
  },
  modalActions: {
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  foundButton: {
    backgroundColor: '#4CAF50',
  },
});