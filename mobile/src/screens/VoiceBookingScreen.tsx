import React from 'react';
import { View, StyleSheet } from 'react-native';
import { StackNavigationProp } from '@react-navigation/stack';
import { RouteProp } from '@react-navigation/native';
import { SafeArea } from '@/components/SafeArea';
import { VoiceBookingConfirmation } from '@/components/voice/VoiceBookingConfirmation';
import { RootStackParamList } from '../navigation/types';

type VoiceBookingScreenNavigationProp = StackNavigationProp<
  RootStackParamList,
  'VoiceBooking'
>;

type VoiceBookingScreenRouteProp = RouteProp<RootStackParamList, 'VoiceBooking'>;

type Props = {
  navigation: VoiceBookingScreenNavigationProp;
  route: VoiceBookingScreenRouteProp;
};

export const VoiceBookingScreen: React.FC<Props> = ({ navigation, route }) => {
  const { venue, type = 'restaurant', isDriving = false } = route.params || {};
  
  const handleConfirm = (booking: any) => {
    // Navigate to confirmation or back to main screen
    navigation.navigate('ImmersiveExperience');
  };
  
  const handleCancel = () => {
    navigation.goBack();
  };
  
  return (
    <View style={styles.container}>
      <VoiceBookingConfirmation
        bookingData={{
          type: type as 'restaurant' | 'attraction' | 'hotel',
          venue: venue || 'Nearby Restaurant',
          date: new Date().toLocaleDateString(),
          time: 'Next available',
          partySize: 2,
        }}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
        isDriving={isDriving}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});

export default VoiceBookingScreen;