import React, { useState, useEffect } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../services/api/ApiClient';
import { theme } from '../theme';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Loading } from '../components/Loading';

type RideshareMode = 'driver' | 'passenger' | 'none';

export const RideshareScreen = () => {
  const navigation = useNavigation();
  const [currentMode, setCurrentMode] = useState<RideshareMode>('none');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkCurrentMode();
  }, []);

  const checkCurrentMode = async () => {
    try {
      const response = await api.get('/rideshare/mode');
      setCurrentMode(response.data.mode);
    } catch (error) {
      logger.error('Error checking rideshare mode:', error);
    } finally {
      setLoading(false);
    }
  };

  const selectMode = async (mode: RideshareMode) => {
    if (mode === 'none') {
      try {
        await api.delete('/rideshare/mode');
        setCurrentMode('none');
        Alert.alert('Success', 'Rideshare mode ended');
      } catch (error) {
        Alert.alert('Error', 'Failed to end rideshare mode');
      }
      return;
    }

    try {
      setLoading(true);
      await api.post('/rideshare/mode', { mode });
      setCurrentMode(mode);
      
      // Navigate to appropriate screen
      if (mode === 'driver') {
        navigation.navigate('RideshareDriverMode' as never);
      } else {
        navigation.navigate('RidesharePassengerMode' as never);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to set rideshare mode');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loading />;
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Rideshare Mode</Text>
        {currentMode !== 'none' && (
          <Text style={styles.currentMode}>
            Current: {currentMode.charAt(0).toUpperCase() + currentMode.slice(1)}
          </Text>
        )}
      </View>

      <View style={styles.content}>
        <Card style={styles.modeCard}>
          <TouchableOpacity
            style={[styles.modeButton, currentMode === 'driver' && styles.activeMode]}
            onPress={() => selectMode('driver')}
          >
            <Ionicons 
              name="car" 
              size={48} 
              color={currentMode === 'driver' ? theme.colors.primary : theme.colors.text} 
            />
            <Text style={styles.modeTitle}>Driver Mode</Text>
            <Text style={styles.modeDescription}>
              Optimized for rideshare drivers with quick actions, earnings tracking, and safety features
            </Text>
            <View style={styles.features}>
              <Text style={styles.feature}>• Find gas & food quickly</Text>
              <Text style={styles.feature}>• Track earnings</Text>
              <Text style={styles.feature}>• Optimal pickup spots</Text>
              <Text style={styles.feature}>• Voice commands</Text>
            </View>
          </TouchableOpacity>
        </Card>

        <Card style={styles.modeCard}>
          <TouchableOpacity
            style={[styles.modeButton, currentMode === 'passenger' && styles.activeMode]}
            onPress={() => selectMode('passenger')}
          >
            <Ionicons 
              name="person" 
              size={48} 
              color={currentMode === 'passenger' ? theme.colors.primary : theme.colors.text} 
            />
            <Text style={styles.modeTitle}>Passenger Mode</Text>
            <Text style={styles.modeDescription}>
              Entertainment and engagement for rideshare passengers
            </Text>
            <View style={styles.features}>
              <Text style={styles.feature}>• Quick games & trivia</Text>
              <Text style={styles.feature}>• Short stories</Text>
              <Text style={styles.feature}>• Music recommendations</Text>
              <Text style={styles.feature}>• Local facts</Text>
            </View>
          </TouchableOpacity>
        </Card>

        {currentMode !== 'none' && (
          <Button
            title="End Rideshare Mode"
            onPress={() => selectMode('none')}
            variant="secondary"
            style={styles.endButton}
          />
        )}
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Rideshare mode automatically adapts the app for your needs
        </Text>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    padding: theme.spacing.lg,
    alignItems: 'center',
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  currentMode: {
    fontSize: 16,
    color: theme.colors.primary,
  },
  content: {
    flex: 1,
    padding: theme.spacing.md,
  },
  modeCard: {
    marginBottom: theme.spacing.lg,
  },
  modeButton: {
    padding: theme.spacing.lg,
    alignItems: 'center',
  },
  activeMode: {
    backgroundColor: theme.colors.primaryLight,
  },
  modeTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginTop: theme.spacing.md,
    marginBottom: theme.spacing.sm,
  },
  modeDescription: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    marginBottom: theme.spacing.md,
  },
  features: {
    marginTop: theme.spacing.sm,
  },
  feature: {
    fontSize: 14,
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  endButton: {
    marginTop: theme.spacing.xl,
  },
  footer: {
    padding: theme.spacing.lg,
    alignItems: 'center',
  },
  footerText: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    textAlign: 'center',
  },
});