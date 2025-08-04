import React, { useState } from 'react';
import { View, StyleSheet, Image, Platform } from 'react-native';
import { Text, Button, Surface, Divider } from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';
import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useTranslation } from '../i18n';

import { COLORS, SPACING } from '../theme';

import { logger } from '@/services/logger';
const PermissionsScreen: React.FC<{
  navigation: any;
}> = ({ navigation }) => {
  const { t } = useTranslation();
  const [locationPermissionGranted, setLocationPermissionGranted] = useState(false);
  const [notificationPermissionGranted, setNotificationPermissionGranted] = useState(false);

  const requestLocationPermission = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === 'granted') {
        setLocationPermissionGranted(true);
      }
    } catch (error) {
      logger.error('Error requesting location permission:', error);
    }
  };

  const requestNotificationPermission = async () => {
    try {
      if (Platform.OS === 'android') {
        // Android doesn't require permission for notifications
        setNotificationPermissionGranted(true);
        return;
      }
      
      const { status } = await Notifications.requestPermissionsAsync();
      if (status === 'granted') {
        setNotificationPermissionGranted(true);
      }
    } catch (error) {
      logger.error('Error requesting notification permission:', error);
    }
  };

  const handleContinue = async () => {
    try {
      await AsyncStorage.setItem('hasCompletedPermissions', 'true');
      navigation.replace('Main');
    } catch (error) {
      logger.error('Error saving permissions status:', error);
      navigation.replace('Main');
    }
  };

  const allPermissionsGranted = locationPermissionGranted;
  
  return (
    <SafeAreaView style={styles.container}>
      <Surface style={styles.card}>
        <Text style={styles.title}>{t('permissions.title')}</Text>
        <Text style={styles.subtitle}>
          {t('permissions.subtitle')}
        </Text>

        <Surface style={[
          styles.permissionCard, 
          locationPermissionGranted && styles.permissionGranted
        ]}>
          <View style={styles.permissionHeader}>
            <MaterialIcons 
              name="location-on" 
              size={24} 
              color={locationPermissionGranted ? COLORS.success : COLORS.primary} 
            />
            <Text style={styles.permissionTitle}>{t('permissions.location.title')}</Text>
            {locationPermissionGranted && (
              <MaterialIcons name="check-circle" size={24} color={COLORS.success} />
            )}
          </View>
          <Text style={styles.permissionDescription}>
            {t('permissions.location.description')}
          </Text>
          <Button
            mode={locationPermissionGranted ? "outlined" : "contained"}
            onPress={requestLocationPermission}
            disabled={locationPermissionGranted}
            style={styles.permissionButton}
            accessibilityLabel={t(locationPermissionGranted 
              ? 'permissions.location.granted' 
              : 'permissions.location.button')}
          >
            {t(locationPermissionGranted 
              ? 'permissions.location.granted' 
              : 'permissions.location.button')}
          </Button>
        </Surface>

        <Surface style={[
          styles.permissionCard,
          notificationPermissionGranted && styles.permissionGranted
        ]}>
          <View style={styles.permissionHeader}>
            <MaterialIcons 
              name="notifications" 
              size={24} 
              color={notificationPermissionGranted ? COLORS.success : COLORS.primary} 
            />
            <Text style={styles.permissionTitle}>{t('permissions.notifications.title')}</Text>
            {notificationPermissionGranted && (
              <MaterialIcons name="check-circle" size={24} color={COLORS.success} />
            )}
          </View>
          <Text style={styles.permissionDescription}>
            {t('permissions.notifications.description')}
          </Text>
          <Button
            mode={notificationPermissionGranted ? "outlined" : "contained"}
            onPress={requestNotificationPermission}
            disabled={notificationPermissionGranted}
            style={styles.permissionButton}
            accessibilityLabel={t(notificationPermissionGranted 
              ? 'permissions.notifications.granted' 
              : 'permissions.notifications.button')}
          >
            {t(notificationPermissionGranted 
              ? 'permissions.notifications.granted' 
              : 'permissions.notifications.button')}
          </Button>
        </Surface>

        <View style={styles.footer}>
          <Button
            mode="contained"
            onPress={handleContinue}
            style={styles.continueButton}
            accessibilityLabel={t('permissions.continue')}
          >
            {t('permissions.continue')}
          </Button>
          <Text style={styles.skipText} accessibilityLabel={t('permissions.skip')}>
            {t('permissions.skip')}
          </Text>
        </View>
      </Surface>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: SPACING.medium,
    backgroundColor: COLORS.background,
  },
  card: {
    padding: SPACING.large,
    borderRadius: 16,
    elevation: 4,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: SPACING.medium,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    marginBottom: SPACING.large,
    textAlign: 'center',
    color: COLORS.textSecondary,
  },
  permissionCard: {
    padding: SPACING.medium,
    marginBottom: SPACING.medium,
    borderRadius: 8,
    elevation: 2,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  permissionGranted: {
    borderColor: COLORS.success,
    backgroundColor: COLORS.success + '10',
  },
  permissionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.small,
  },
  permissionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginLeft: SPACING.small,
    flex: 1,
  },
  permissionDescription: {
    marginBottom: SPACING.medium,
    fontSize: 14,
    color: COLORS.textSecondary,
  },
  permissionButton: {
    alignSelf: 'flex-start',
  },
  footer: {
    marginTop: SPACING.large,
  },
  continueButton: {
    marginTop: SPACING.medium,
  },
  skipText: {
    textAlign: 'center',
    marginTop: SPACING.medium,
    fontSize: 14,
    color: COLORS.textSecondary,
  },
});

export default PermissionsScreen; 