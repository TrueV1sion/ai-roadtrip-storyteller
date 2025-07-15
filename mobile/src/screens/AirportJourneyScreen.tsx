import React, { useState, useEffect } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  Alert,
  Image,
  TouchableOpacity,
} from 'react-native';
import {
  Text,
  Card,
  Button,
  Chip,
  List,
  Divider,
  IconButton,
  Surface,
  ProgressBar,
  FAB,
} from 'react-native-paper';
import * as ImagePicker from 'expo-image-picker';
import * as Location from 'expo-location';
import { MaterialIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';

import { SafeArea } from '../components/SafeArea';
import { VoiceAssistant } from '../components/VoiceAssistant';
import { MapView } from '../components/MapView';
import { apiClient } from '../services/api/ApiClient';
import { COLORS, SPACING } from '../theme';
import { formatDistance, formatDuration, formatCurrency } from '../utils/formatters';

interface ParkingOption {
  type: string;
  name: string;
  price_per_day: number;
  total_price: number;
  available_spots: number;
  shuttle_frequency: number;
  walk_time: number;
  features: string[];
}

interface FlightInfo {
  flight_number: string;
  departure_time: string;
  terminal?: string;
  gate?: string;
  status: string;
}

export const AirportJourneyScreen: React.FC = () => {
  const navigation = useNavigation();
  const [journeyType, setJourneyType] = useState<'parking' | 'pickup' | 'dropoff' | null>(null);
  const [airportCode, setAirportCode] = useState<string>('');
  const [flightInfo, setFlightInfo] = useState<FlightInfo | null>(null);
  const [parkingOptions, setParkingOptions] = useState<ParkingOption[]>([]);
  const [selectedParking, setSelectedParking] = useState<ParkingOption | null>(null);
  const [parkingPhoto, setParkingPhoto] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [voiceResponse, setVoiceResponse] = useState<string>('');
  const [departureTime, setDepartureTime] = useState<Date | null>(null);
  const [currentStep, setCurrentStep] = useState(0);

  // Journey steps
  const journeySteps = [
    'Detect Airport',
    'Flight Details',
    'Parking Options',
    'Book & Navigate',
    'Save Location',
  ];

  useEffect(() => {
    // Request location permissions
    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Location access is needed for navigation.');
      }
    })();
  }, []);

  const handleVoiceCommand = async (command: string) => {
    try {
      setIsLoading(true);
      
      // Get current location
      const location = await Location.getCurrentPositionAsync({});
      
      const response = await apiClient.post('/api/airport/journey/create', {
        user_input: command,
        context: {
          origin: `${location.coords.latitude},${location.coords.longitude}`,
          destination: command,
        },
      });

      if (response.journey_plan) {
        setVoiceResponse(response.voice_response);
        
        // Set journey details from response
        if (response.journey_plan.journey_type) {
          setJourneyType(response.journey_plan.journey_type);
        }
        
        if (response.journey_plan.airport?.code) {
          setAirportCode(response.journey_plan.airport.code);
        }
        
        if (response.journey_plan.parking_options) {
          setParkingOptions(response.journey_plan.parking_options.options);
        }
        
        setCurrentStep(1);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to process your request');
    } finally {
      setIsLoading(false);
    }
  };

  const searchParking = async () => {
    if (!flightInfo?.departure_time) return;

    try {
      setIsLoading(true);
      
      const response = await apiClient.post('/api/airport/parking/search', {
        airport_code: airportCode,
        start_date: flightInfo.departure_time,
        end_date: new Date(
          new Date(flightInfo.departure_time).getTime() + 3 * 24 * 60 * 60 * 1000
        ), // 3 days later
      });

      setParkingOptions(response.parking_options.options);
      setVoiceResponse(response.voice_response);
      setCurrentStep(2);
    } catch (error) {
      Alert.alert('Error', 'Failed to search parking options');
    } finally {
      setIsLoading(false);
    }
  };

  const bookParking = async () => {
    if (!selectedParking || !flightInfo) return;

    try {
      setIsLoading(true);
      
      const response = await apiClient.post('/api/airport/parking/book', {
        airport_code: airportCode,
        parking_type: selectedParking.type,
        start_date: flightInfo.departure_time,
        end_date: new Date(
          new Date(flightInfo.departure_time).getTime() + 3 * 24 * 60 * 60 * 1000
        ),
        flight_info: flightInfo,
      });

      setVoiceResponse(response.voice_confirmation);
      Alert.alert('Success', 'Parking booked successfully!');
      setCurrentStep(3);
      
      // Navigate to the airport
      navigation.navigate('Navigation', {
        destination: `${airportCode} Airport ${selectedParking.name}`,
      });
    } catch (error) {
      Alert.alert('Error', 'Failed to book parking');
    } finally {
      setIsLoading(false);
    }
  };

  const takeParkingPhoto = async () => {
    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: false,
      quality: 0.8,
    });

    if (!result.canceled && result.assets[0]) {
      setParkingPhoto(result.assets[0].uri);
      
      // Upload photo
      try {
        const formData = new FormData();
        formData.append('photo', {
          uri: result.assets[0].uri,
          type: 'image/jpeg',
          name: 'parking_location.jpg',
        } as any);
        formData.append('notes', `Parked at ${selectedParking?.name || 'airport'}`);

        await apiClient.post(
          `/api/airport/parking/photo?booking_id=${airportCode}_booking`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          }
        );

        Alert.alert('Success', 'Parking location saved!');
        setCurrentStep(4);
      } catch (error) {
        Alert.alert('Error', 'Failed to save parking photo');
      }
    }
  };

  const renderParkingOption = (option: ParkingOption) => (
    <Card
      key={option.type}
      style={[
        styles.parkingCard,
        selectedParking?.type === option.type && styles.selectedCard,
      ]}
      onPress={() => setSelectedParking(option)}
    >
      <Card.Content>
        <View style={styles.parkingHeader}>
          <View>
            <Text style={styles.parkingName}>{option.name}</Text>
            <Text style={styles.parkingPrice}>
              {formatCurrency(option.price_per_day)}/day
            </Text>
          </View>
          <Text style={styles.totalPrice}>
            Total: {formatCurrency(option.total_price)}
          </Text>
        </View>
        
        <View style={styles.parkingDetails}>
          <Chip icon="car" style={styles.chip}>
            {option.available_spots} spots
          </Chip>
          {option.shuttle_frequency > 0 && (
            <Chip icon="bus" style={styles.chip}>
              Shuttle every {option.shuttle_frequency}min
            </Chip>
          )}
          {option.walk_time > 0 && (
            <Chip icon="walk" style={styles.chip}>
              {option.walk_time}min walk
            </Chip>
          )}
        </View>
        
        <View style={styles.features}>
          {option.features.map((feature, index) => (
            <Text key={index} style={styles.feature}>
              • {feature}
            </Text>
          ))}
        </View>
      </Card.Content>
    </Card>
  );

  const renderJourneyProgress = () => (
    <Surface style={styles.progressContainer}>
      <View style={styles.progressSteps}>
        {journeySteps.map((step, index) => (
          <View key={index} style={styles.stepContainer}>
            <View
              style={[
                styles.stepCircle,
                index <= currentStep && styles.stepCircleActive,
              ]}
            >
              {index < currentStep ? (
                <MaterialIcons name="check" size={16} color="white" />
              ) : (
                <Text style={styles.stepNumber}>{index + 1}</Text>
              )}
            </View>
            <Text style={styles.stepLabel}>{step}</Text>
          </View>
        ))}
      </View>
      <ProgressBar
        progress={(currentStep + 1) / journeySteps.length}
        color={COLORS.primary}
        style={styles.progressBar}
      />
    </Surface>
  );

  return (
    <SafeArea>
      <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <IconButton
            icon="arrow-left"
            size={24}
            onPress={() => navigation.goBack()}
          />
          <Text style={styles.title}>Airport Journey</Text>
          <IconButton
            icon="airplane"
            size={24}
            onPress={() => {}}
          />
        </View>

        {/* Journey Progress */}
        {renderJourneyProgress()}

        {/* Voice Assistant */}
        <Card style={styles.voiceCard}>
          <Card.Content>
            <View style={styles.voiceHeader}>
              <MaterialIcons name="airline-seat-recline-normal" size={24} color={COLORS.primary} />
              <Text style={styles.voiceTitle}>Captain Anderson</Text>
            </View>
            {voiceResponse ? (
              <Text style={styles.voiceResponse}>{voiceResponse}</Text>
            ) : (
              <Text style={styles.voicePrompt}>
                Say "I'm flying out of LAX tomorrow at 8 AM" to get started
              </Text>
            )}
          </Card.Content>
        </Card>

        {/* Content based on journey type and step */}
        {currentStep === 0 && (
          <Card style={styles.contentCard}>
            <Card.Content>
              <Text style={styles.sectionTitle}>What can I help you with?</Text>
              <Button
                mode="contained"
                icon="airplane-takeoff"
                onPress={() => {
                  setJourneyType('parking');
                  setCurrentStep(1);
                }}
                style={styles.actionButton}
              >
                I need airport parking
              </Button>
              <Button
                mode="outlined"
                icon="account-group"
                onPress={() => {
                  setJourneyType('pickup');
                  setCurrentStep(1);
                }}
                style={styles.actionButton}
              >
                Pick someone up
              </Button>
              <Button
                mode="outlined"
                icon="car"
                onPress={() => {
                  setJourneyType('dropoff');
                  setCurrentStep(1);
                }}
                style={styles.actionButton}
              >
                Drop someone off
              </Button>
            </Card.Content>
          </Card>
        )}

        {/* Parking Options */}
        {currentStep === 2 && parkingOptions.length > 0 && (
          <View>
            <Text style={styles.sectionTitle}>Available Parking</Text>
            {parkingOptions.map(renderParkingOption)}
            
            <Button
              mode="contained"
              onPress={bookParking}
              disabled={!selectedParking}
              loading={isLoading}
              style={styles.bookButton}
            >
              Book {selectedParking?.name || 'Parking'}
            </Button>
          </View>
        )}

        {/* Parking Photo */}
        {currentStep >= 3 && journeyType === 'parking' && (
          <Card style={styles.contentCard}>
            <Card.Content>
              <Text style={styles.sectionTitle}>Save Your Parking Location</Text>
              {parkingPhoto ? (
                <View>
                  <Image source={{ uri: parkingPhoto }} style={styles.parkingImage} />
                  <Text style={styles.photoSaved}>
                    ✓ Location saved! I'll remind you when you return.
                  </Text>
                </View>
              ) : (
                <TouchableOpacity onPress={takeParkingPhoto} style={styles.photoButton}>
                  <MaterialIcons name="camera-alt" size={48} color={COLORS.primary} />
                  <Text style={styles.photoButtonText}>Take a photo of your parking spot</Text>
                </TouchableOpacity>
              )}
            </Card.Content>
          </Card>
        )}

        {/* Flight Status */}
        {flightInfo && (
          <Card style={styles.flightCard}>
            <Card.Content>
              <View style={styles.flightHeader}>
                <Text style={styles.flightNumber}>{flightInfo.flight_number}</Text>
                <Chip
                  icon="airplane"
                  style={[
                    styles.statusChip,
                    flightInfo.status === 'on_time' && styles.onTimeChip,
                    flightInfo.status === 'delayed' && styles.delayedChip,
                  ]}
                >
                  {flightInfo.status.replace('_', ' ').toUpperCase()}
                </Chip>
              </View>
              {flightInfo.terminal && (
                <Text style={styles.flightDetail}>
                  Terminal {flightInfo.terminal}
                  {flightInfo.gate && ` • Gate ${flightInfo.gate}`}
                </Text>
              )}
            </Card.Content>
          </Card>
        )}
      </ScrollView>

      {/* Voice Input FAB */}
      <FAB
        icon="microphone"
        style={styles.fab}
        onPress={() => {
          // Trigger voice input
        }}
      />

      {/* Voice Assistant Component */}
      <VoiceAssistant
        onCommand={handleVoiceCommand}
        personality="captain"
        isListening={false}
      />
    </SafeArea>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: SPACING.small,
    paddingVertical: SPACING.medium,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  progressContainer: {
    margin: SPACING.medium,
    padding: SPACING.medium,
    borderRadius: 12,
    elevation: 2,
  },
  progressSteps: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.medium,
  },
  stepContainer: {
    alignItems: 'center',
    flex: 1,
  },
  stepCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: COLORS.surface,
    borderWidth: 2,
    borderColor: COLORS.border,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: SPACING.xsmall,
  },
  stepCircleActive: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  stepNumber: {
    fontSize: 14,
    color: COLORS.textSecondary,
  },
  stepLabel: {
    fontSize: 10,
    color: COLORS.textSecondary,
    textAlign: 'center',
  },
  progressBar: {
    height: 4,
    borderRadius: 2,
  },
  voiceCard: {
    margin: SPACING.medium,
    elevation: 2,
  },
  voiceHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.small,
  },
  voiceTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: SPACING.small,
  },
  voiceResponse: {
    fontSize: 14,
    lineHeight: 20,
    color: COLORS.text,
  },
  voicePrompt: {
    fontSize: 14,
    lineHeight: 20,
    color: COLORS.textSecondary,
    fontStyle: 'italic',
  },
  contentCard: {
    margin: SPACING.medium,
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginHorizontal: SPACING.medium,
    marginTop: SPACING.medium,
    marginBottom: SPACING.small,
  },
  actionButton: {
    marginTop: SPACING.small,
  },
  parkingCard: {
    margin: SPACING.medium,
    elevation: 2,
  },
  selectedCard: {
    borderColor: COLORS.primary,
    borderWidth: 2,
  },
  parkingHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: SPACING.small,
  },
  parkingName: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  parkingPrice: {
    fontSize: 14,
    color: COLORS.textSecondary,
  },
  totalPrice: {
    fontSize: 18,
    fontWeight: 'bold',
    color: COLORS.primary,
  },
  parkingDetails: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginVertical: SPACING.small,
  },
  chip: {
    marginRight: SPACING.xsmall,
    marginBottom: SPACING.xsmall,
  },
  features: {
    marginTop: SPACING.small,
  },
  feature: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginTop: 2,
  },
  bookButton: {
    margin: SPACING.medium,
  },
  photoButton: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: SPACING.large,
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: COLORS.primary,
    borderStyle: 'dashed',
  },
  photoButtonText: {
    marginTop: SPACING.small,
    color: COLORS.primary,
    fontSize: 14,
  },
  parkingImage: {
    width: '100%',
    height: 200,
    borderRadius: 8,
    marginBottom: SPACING.small,
  },
  photoSaved: {
    fontSize: 14,
    color: COLORS.success,
    textAlign: 'center',
  },
  flightCard: {
    margin: SPACING.medium,
    elevation: 2,
  },
  flightHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  flightNumber: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  flightDetail: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginTop: SPACING.xsmall,
  },
  statusChip: {
    backgroundColor: COLORS.surface,
  },
  onTimeChip: {
    backgroundColor: COLORS.success + '20',
  },
  delayedChip: {
    backgroundColor: COLORS.error + '20',
  },
  fab: {
    position: 'absolute',
    margin: SPACING.medium,
    right: 0,
    bottom: 0,
    backgroundColor: COLORS.primary,
  },
});