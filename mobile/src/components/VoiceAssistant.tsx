/**
 * Voice Assistant Component
 * 
 * Main UI component for voice interactions with the AI assistant.
 * Handles voice recording, displays responses, and manages booking opportunities.
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Modal,
  FlatList,
  Alert,
  TextInput
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import * as Location from 'expo-location';

import voiceAssistantService, {
  VoiceAssistantResponse,
  BookingOpportunity,
  JourneyContext
} from '../services/voiceAssistantService';

interface VoiceAssistantProps {
  isVisible: boolean;
  onClose: () => void;
  journeyContext?: Partial<JourneyContext>;
}

export const VoiceAssistant: React.FC<VoiceAssistantProps> = ({
  isVisible,
  onClose,
  journeyContext
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentResponse, setCurrentResponse] = useState<VoiceAssistantResponse | null>(null);
  const [bookingOpportunities, setBookingOpportunities] = useState<BookingOpportunity[]>([]);
  const [conversationHistory, setConversationHistory] = useState<VoiceAssistantResponse[]>([]);
  const [textInput, setTextInput] = useState('');
  const [showTextInput, setShowTextInput] = useState(false);

  useEffect(() => {
    // Load conversation history when component mounts
    setConversationHistory(voiceAssistantService.getConversationHistory());
  }, []);

  const getCurrentLocation = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        throw new Error('Location permission denied');
      }

      const location = await Location.getCurrentPositionAsync({});
      return {
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
        name: 'Current Location'
      };
    } catch (error) {
      console.error('Failed to get location:', error);
      // Return default location
      return {
        latitude: 37.7749,
        longitude: -122.4194,
        name: 'San Francisco, CA'
      };
    }
  };

  const handleVoicePress = async () => {
    if (isRecording) {
      // Stop recording and process
      const recording = await voiceAssistantService.stopRecording();
      setIsRecording(false);
      
      if (recording) {
        await processVoiceInput(recording);
      }
    } else {
      // Start recording
      try {
        await voiceAssistantService.startRecording();
        setIsRecording(true);
      } catch (error) {
        Alert.alert('Recording Error', 'Failed to start recording. Please check microphone permissions.');
      }
    }
  };

  const processVoiceInput = async (recording: Audio.Recording) => {
    setIsProcessing(true);
    try {
      const currentLocation = await getCurrentLocation();
      const context: JourneyContext = {
        currentLocation,
        journeyStage: 'traveling',
        passengers: [],
        ...journeyContext
      };

      const response = await voiceAssistantService.sendMessage(
        recording,
        context
      );

      handleResponse(response);
    } catch (error) {
      Alert.alert('Error', 'Failed to process voice input. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleTextSubmit = async () => {
    if (!textInput.trim()) return;

    setIsProcessing(true);
    try {
      const currentLocation = await getCurrentLocation();
      const context: JourneyContext = {
        currentLocation,
        journeyStage: 'traveling',
        passengers: [],
        ...journeyContext
      };

      const response = await voiceAssistantService.sendMessage(
        textInput,
        context
      );

      handleResponse(response);
      setTextInput('');
      setShowTextInput(false);
    } catch (error) {
      Alert.alert('Error', 'Failed to send message. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleResponse = (response: VoiceAssistantResponse) => {
    setCurrentResponse(response);
    setBookingOpportunities(response.bookingOpportunities || []);
    setConversationHistory([...conversationHistory, response]);
  };

  const handleBookingAction = async (opportunity: BookingOpportunity, action: 'confirm' | 'details') => {
    if (action === 'details') {
      // Show booking details
      Alert.alert(
        opportunity.name,
        `${opportunity.description}\n\nPrice: ${opportunity.pricing.range}\nDistance: ${opportunity.location.distanceMiles} miles\nDuration: ${opportunity.timing.durationMinutes} minutes`,
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Book Now',
            onPress: () => handleBookingAction(opportunity, 'confirm')
          }
        ]
      );
    } else {
      // Confirm booking
      try {
        setIsProcessing(true);
        const result = await voiceAssistantService.processBookingAction(
          opportunity.id,
          'confirm',
          {
            partySize: journeyContext?.passengers?.length || 1,
            preferredTime: new Date().toISOString()
          }
        );

        Alert.alert(
          'Booking Confirmed!',
          `Your booking at ${opportunity.name} has been confirmed.\n\nConfirmation: ${result.confirmationNumber || 'PENDING'}`
        );

        // Clear booking opportunities after confirmation
        setBookingOpportunities([]);
      } catch (error) {
        Alert.alert('Booking Error', 'Failed to complete booking. Please try again.');
      } finally {
        setIsProcessing(false);
      }
    }
  };

  const renderBookingOpportunity = ({ item }: { item: BookingOpportunity }) => (
    <TouchableOpacity
      style={styles.bookingCard}
      onPress={() => handleBookingAction(item, 'details')}
    >
      <View style={styles.bookingHeader}>
        <Text style={styles.bookingName}>{item.name}</Text>
        <Text style={styles.bookingPrice}>{item.pricing.range}</Text>
      </View>
      <Text style={styles.bookingDescription} numberOfLines={2}>
        {item.description}
      </Text>
      <View style={styles.bookingDetails}>
        <Text style={styles.bookingDetailText}>
          <Ionicons name="location-outline" size={14} /> {item.location.distanceMiles} mi
        </Text>
        <Text style={styles.bookingDetailText}>
          <Ionicons name="time-outline" size={14} /> {item.timing.durationMinutes} min
        </Text>
        <TouchableOpacity
          style={styles.bookButton}
          onPress={() => handleBookingAction(item, 'confirm')}
        >
          <Text style={styles.bookButtonText}>Book</Text>
        </TouchableOpacity>
      </View>
    </TouchableOpacity>
  );

  return (
    <Modal
      visible={isVisible}
      animationType="slide"
      transparent={true}
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>AI Travel Assistant</Text>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Ionicons name="close" size={24} color="#333" />
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
          {currentResponse && (
            <View style={styles.responseContainer}>
              <Text style={styles.responseText}>{currentResponse.text}</Text>
            </View>
          )}

          {bookingOpportunities.length > 0 && (
            <View style={styles.bookingsSection}>
              <Text style={styles.sectionTitle}>Available Bookings</Text>
              <FlatList
                data={bookingOpportunities}
                renderItem={renderBookingOpportunity}
                keyExtractor={(item) => item.id}
                horizontal
                showsHorizontalScrollIndicator={false}
              />
            </View>
          )}

          {conversationHistory.length > 0 && (
            <View style={styles.historySection}>
              <Text style={styles.sectionTitle}>Recent Conversations</Text>
              {conversationHistory.slice(-3).map((item, index) => (
                <View key={index} style={styles.historyItem}>
                  <Text style={styles.historyText} numberOfLines={2}>
                    {item.text}
                  </Text>
                </View>
              ))}
            </View>
          )}
        </ScrollView>

        {showTextInput ? (
          <View style={styles.textInputContainer}>
            <TextInput
              style={styles.textInput}
              value={textInput}
              onChangeText={setTextInput}
              placeholder="Type your message..."
              onSubmitEditing={handleTextSubmit}
              returnKeyType="send"
            />
            <TouchableOpacity
              style={styles.sendButton}
              onPress={handleTextSubmit}
              disabled={!textInput.trim() || isProcessing}
            >
              <Ionicons name="send" size={20} color="#fff" />
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.controls}>
            <TouchableOpacity
              style={styles.textButton}
              onPress={() => setShowTextInput(true)}
            >
              <Ionicons name="text" size={24} color="#666" />
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.voiceButton,
                isRecording && styles.voiceButtonRecording,
                isProcessing && styles.voiceButtonProcessing
              ]}
              onPress={handleVoicePress}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <ActivityIndicator size="large" color="#fff" />
              ) : (
                <Ionicons
                  name={isRecording ? "stop" : "mic"}
                  size={32}
                  color="#fff"
                />
              )}
            </TouchableOpacity>

            <TouchableOpacity style={styles.quickAction}>
              <Ionicons name="restaurant" size={24} color="#666" />
            </TouchableOpacity>
          </View>
        )}
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    marginTop: 50,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 5,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  closeButton: {
    padding: 5,
  },
  content: {
    flex: 1,
    padding: 20,
  },
  responseContainer: {
    backgroundColor: '#f5f5f5',
    padding: 15,
    borderRadius: 10,
    marginBottom: 20,
  },
  responseText: {
    fontSize: 16,
    color: '#333',
    lineHeight: 24,
  },
  bookingsSection: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 10,
  },
  bookingCard: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 15,
    marginRight: 10,
    width: 280,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  bookingHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  bookingName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    flex: 1,
  },
  bookingPrice: {
    fontSize: 16,
    fontWeight: '600',
    color: '#4CAF50',
  },
  bookingDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 10,
  },
  bookingDetails: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  bookingDetailText: {
    fontSize: 12,
    color: '#999',
  },
  bookButton: {
    backgroundColor: '#2196F3',
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 20,
  },
  bookButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  historySection: {
    marginTop: 20,
  },
  historyItem: {
    backgroundColor: '#f9f9f9',
    padding: 10,
    borderRadius: 8,
    marginBottom: 8,
  },
  historyText: {
    fontSize: 14,
    color: '#666',
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  voiceButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#2196F3',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 5,
  },
  voiceButtonRecording: {
    backgroundColor: '#f44336',
  },
  voiceButtonProcessing: {
    backgroundColor: '#9E9E9E',
  },
  textButton: {
    padding: 10,
  },
  quickAction: {
    padding: 10,
  },
  textInputContainer: {
    flexDirection: 'row',
    padding: 15,
    borderTopWidth: 1,
    borderTopColor: '#eee',
  },
  textInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 25,
    paddingHorizontal: 15,
    paddingVertical: 10,
    fontSize: 16,
    marginRight: 10,
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#2196F3',
    justifyContent: 'center',
    alignItems: 'center',
  },
});