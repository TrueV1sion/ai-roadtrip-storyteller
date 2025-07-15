import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  Alert,
  Modal,
  Text,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  Platform
} from 'react-native';
import { RouteProp, useRoute, useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { FontAwesome5, Ionicons } from '@expo/vector-icons';

import { StoryNode, StoryHeader } from '../components/narrative';
import { ApiClient } from '../services/api/ApiClient';
import { 
  NarrativeGraphType, 
  NarrativeStateType, 
  NarrativeNodeType,
  NarrativeChoiceType,
  NodeContentResponse
} from '../types/narrative';

type InteractiveStoryScreenParams = {
  narrativeId: string;
  stateId?: string;
  theme?: string;
  locationName?: string;
};

type StoryScreenProps = {
  route: RouteProp<{ params: InteractiveStoryScreenParams }, 'params'>;
  navigation: StackNavigationProp<any>;
};

const InteractiveStoryScreen: React.FC = () => {
  const route = useRoute<RouteProp<{ params: InteractiveStoryScreenParams }, 'params'>>();
  const navigation = useNavigation();
  
  const { narrativeId, stateId: initialStateId, theme = 'adventure', locationName = 'Unknown Location' } = route.params;
  
  // State
  const [narrative, setNarrative] = useState<NarrativeGraphType | null>(null);
  const [state, setState] = useState<NarrativeStateType | null>(null);
  const [currentNode, setCurrentNode] = useState<NarrativeNodeType | null>(null);
  const [personalizedContent, setPersonalizedContent] = useState<Record<string, any>>({});
  const [choices, setChoices] = useState<NarrativeChoiceType[]>([]);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [showInventory, setShowInventory] = useState(false);
  
  // Load narrative and initialize state if needed
  useEffect(() => {
    const fetchNarrativeAndState = async () => {
      try {
        setLoading(true);
        
        // 1. Fetch narrative data
        let narrativeResponse;
        try {
          narrativeResponse = await ApiClient.get<NarrativeGraphType>(`/interactive-narrative/narratives/${narrativeId}`);
        } catch (error) {
          console.error('Failed to fetch narrative:', error);
          Alert.alert('Error', 'Failed to load the story. Please try again.');
          navigation.goBack();
          return;
        }
        
        setNarrative(narrativeResponse);
        
        // 2. Initialize or fetch existing state
        let stateResponse;
        if (initialStateId) {
          // Use existing state
          try {
            stateResponse = await ApiClient.get<NarrativeStateType>(`/interactive-narrative/states/${initialStateId}`);
          } catch (error) {
            console.error('Failed to fetch state, creating new one:', error);
            stateResponse = await ApiClient.post<NarrativeStateType>(`/interactive-narrative/initialize-state?narrative_id=${narrativeId}`);
          }
        } else {
          // Create new state
          stateResponse = await ApiClient.post<NarrativeStateType>(`/interactive-narrative/initialize-state?narrative_id=${narrativeId}`);
        }
        
        setState(stateResponse);
        
        // 3. Get current node content
        if (stateResponse) {
          await fetchCurrentNode(narrativeId, stateResponse.id);
        }
        
        setLoading(false);
      } catch (error) {
        console.error('Error initializing interactive story:', error);
        setLoading(false);
        Alert.alert('Error', 'Failed to load the story. Please try again.');
        navigation.goBack();
      }
    };
    
    fetchNarrativeAndState();
  }, [narrativeId, initialStateId]);
  
  // Fetch current node
  const fetchCurrentNode = async (narrativeId: string, stateId: string) => {
    try {
      const response = await ApiClient.get<NodeContentResponse>(`/interactive-narrative/current-node/${stateId}?narrative_id=${narrativeId}`);
      
      setCurrentNode(response.node);
      setPersonalizedContent(response.personalized_content);
      setChoices(response.available_choices);
      
      // Fetch progress
      fetchProgress(narrativeId, stateId);
    } catch (error) {
      console.error('Error fetching current node:', error);
      Alert.alert('Error', 'Failed to load story content. Please try again.');
    }
  };
  
  // Fetch narrative progress
  const fetchProgress = async (narrativeId: string, stateId: string) => {
    try {
      const response = await ApiClient.get<{ completion_percentage: number }>(`/interactive-narrative/progress/${stateId}?narrative_id=${narrativeId}`);
      setProgress(response.completion_percentage);
    } catch (error) {
      console.error('Error fetching progress:', error);
    }
  };
  
  // Handle choice selection
  const handleChoiceSelected = async (choiceId: string) => {
    if (!state || !narrative) return;
    
    try {
      setLoading(true);
      
      // Make the choice
      const updatedState = await ApiClient.post<NarrativeStateType>('/interactive-narrative/make-choice', {
        narrative_id: narrative.id,
        state_id: state.id,
        choice_id: choiceId
      });
      
      setState(updatedState);
      
      // Fetch the new node
      await fetchCurrentNode(narrative.id, updatedState.id);
      
      setLoading(false);
    } catch (error) {
      console.error('Error making choice:', error);
      setLoading(false);
      Alert.alert('Error', 'Failed to process your choice. Please try again.');
    }
  };
  
  // Render inventory modal
  const renderInventoryModal = () => {
    const inventory = state?.inventory || {};
    const hasItems = Object.keys(inventory).length > 0;
    
    return (
      <Modal
        animationType="slide"
        transparent={true}
        visible={showInventory}
        onRequestClose={() => setShowInventory(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Inventory</Text>
              <TouchableOpacity onPress={() => setShowInventory(false)}>
                <Ionicons name="close" size={24} color="#333" />
              </TouchableOpacity>
            </View>
            
            <ScrollView style={styles.inventoryList}>
              {hasItems ? (
                Object.entries(inventory).map(([item, quantity], index) => (
                  <View key={index} style={styles.inventoryItem}>
                    <FontAwesome5 name="archive" size={20} color="#4A90E2" style={styles.itemIcon} />
                    <View style={styles.itemDetails}>
                      <Text style={styles.itemName}>{item}</Text>
                      <Text style={styles.itemQuantity}>Quantity: {quantity}</Text>
                    </View>
                  </View>
                ))
              ) : (
                <Text style={styles.emptyInventory}>Your inventory is empty</Text>
              )}
            </ScrollView>
            
            <TouchableOpacity 
              style={styles.closeButton}
              onPress={() => setShowInventory(false)}
            >
              <Text style={styles.closeButtonText}>Close</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    );
  };
  
  // Get story title
  const getStoryTitle = () => {
    if (narrative?.metadata?.title) {
      return narrative.metadata.title;
    }
    return `Adventure in ${locationName}`;
  };
  
  return (
    <SafeAreaView style={styles.container}>
      <StoryHeader 
        title={getStoryTitle()}
        progress={progress}
        theme={theme}
        onMenuPress={() => setShowInventory(true)}
        onInfoPress={() => {
          // Show story info - could be expanded
          if (narrative?.metadata) {
            Alert.alert(
              narrative.metadata.title,
              narrative.metadata.description
            );
          }
        }}
      />
      
      {currentNode ? (
        <StoryNode
          node={currentNode}
          personalizedContent={personalizedContent}
          choices={choices}
          onChoiceSelected={handleChoiceSelected}
          loading={loading}
        />
      ) : loading ? (
        <View style={styles.loadingContainer}>
          <Text>Loading your adventure...</Text>
        </View>
      ) : (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>Failed to load story content.</Text>
          <TouchableOpacity 
            style={styles.retryButton}
            onPress={() => navigation.goBack()}
          >
            <Text style={styles.retryButtonText}>Go Back</Text>
          </TouchableOpacity>
        </View>
      )}
      
      {renderInventoryModal()}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: 20,
  },
  retryButton: {
    backgroundColor: '#4A90E2',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 5,
  },
  retryButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  modalContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  modalContent: {
    width: '85%',
    maxHeight: '70%',
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    paddingBottom: 10,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  inventoryList: {
    maxHeight: '80%',
  },
  inventoryItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  itemIcon: {
    marginRight: 15,
  },
  itemDetails: {
    flex: 1,
  },
  itemName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  itemQuantity: {
    fontSize: 14,
    color: '#666',
    marginTop: 3,
  },
  emptyInventory: {
    textAlign: 'center',
    fontSize: 16,
    color: '#666',
    marginTop: 20,
    fontStyle: 'italic',
  },
  closeButton: {
    backgroundColor: '#4A90E2',
    padding: 12,
    borderRadius: 5,
    alignItems: 'center',
    marginTop: 15,
  },
  closeButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default InteractiveStoryScreen;