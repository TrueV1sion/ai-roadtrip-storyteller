import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  ScrollView,
  Alert,
  Dimensions,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { api } from '../services/api/ApiClient';
import { theme } from '../theme';
import { Card } from '../components/Card';
import { VoiceAssistant } from '../components/VoiceAssistant';
import { useLocation } from '../hooks/useLocation';

const { width } = Dimensions.get('window');
const BUTTON_SIZE = (width - 60) / 2; // 2 columns with spacing

interface QuickAction {
  id: string;
  label: string;
  icon: string;
  voice_command: string;
  priority: number;
}

interface DriverStats {
  total_earnings: number;
  trips_completed: number;
  hourly_rate: number;
  session_duration?: number;
}

export const RideshareDriverModeScreen = () => {
  const navigation = useNavigation();
  const location = useLocation();
  const [quickActions, setQuickActions] = useState<QuickAction[]>([]);
  const [stats, setStats] = useState<DriverStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [voiceActive, setVoiceActive] = useState(false);

  useEffect(() => {
    loadDriverData();
  }, [location]);

  const loadDriverData = async () => {
    try {
      // Load quick actions
      if (location) {
        const actionsResponse = await api.get('/rideshare/driver/quick-actions', {
          params: { lat: location.latitude, lng: location.longitude }
        });
        setQuickActions(actionsResponse.data);
      }

      // Load stats
      const statsResponse = await api.get('/rideshare/driver/stats');
      setStats(statsResponse.data);
    } catch (error) {
      console.error('Error loading driver data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickAction = async (action: QuickAction) => {
    try {
      const response = await api.post('/rideshare/driver/quick-action', {
        action_id: action.id,
        location: location ? {
          lat: location.latitude,
          lng: location.longitude
        } : null
      });

      if (response.data.voice_response) {
        // Would trigger TTS here
        Alert.alert('Quick Action', response.data.voice_response);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to execute action');
    }
  };

  const handleVoiceCommand = async (command: string) => {
    try {
      const response = await api.post('/rideshare/voice/command', {
        voice_input: command,
        mode: 'driver',
        context: {
          location: location ? {
            lat: location.latitude,
            lng: location.longitude
          } : null,
          vehicle_speed: 0, // Would get from device sensors
          is_moving: false
        }
      });

      if (response.data.response) {
        Alert.alert('Voice Response', response.data.response);
      }
    } catch (error) {
      Alert.alert('Error', 'Voice command failed');
    }
  };

  const getIconComponent = (iconName: string) => {
    const iconMap: { [key: string]: JSX.Element } = {
      'gas-pump': <MaterialCommunityIcons name="gas-station" size={48} color={theme.colors.primary} />,
      'food': <Ionicons name="fast-food" size={48} color={theme.colors.primary} />,
      'coffee': <Ionicons name="cafe" size={48} color={theme.colors.primary} />,
      'location': <Ionicons name="location" size={48} color={theme.colors.primary} />,
    };
    return iconMap[iconName] || <Ionicons name="help-circle" size={48} color={theme.colors.primary} />;
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header with earnings */}
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => navigation.goBack()}
        >
          <Ionicons name="arrow-back" size={24} color={theme.colors.text} />
        </TouchableOpacity>
        
        <View style={styles.statsContainer}>
          <Text style={styles.earningsText}>
            ${stats?.total_earnings.toFixed(2) || '0.00'}
          </Text>
          <Text style={styles.statsSubtext}>
            {stats?.trips_completed || 0} trips • ${stats?.hourly_rate.toFixed(2) || '0.00'}/hr
          </Text>
        </View>
      </View>

      {/* Quick Actions Grid */}
      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        
        <View style={styles.actionGrid}>
          {quickActions.map((action) => (
            <TouchableOpacity
              key={action.id}
              style={styles.actionButton}
              onPress={() => handleQuickAction(action)}
              activeOpacity={0.8}
            >
              {getIconComponent(action.icon)}
              <Text style={styles.actionLabel}>{action.label}</Text>
              <Text style={styles.voiceHint}>"{action.voice_command}"</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Additional Actions */}
        <Card style={styles.card}>
          <TouchableOpacity style={styles.wideButton} onPress={() => {}}>
            <Ionicons name="trending-up" size={32} color={theme.colors.primary} />
            <View style={styles.wideButtonText}>
              <Text style={styles.wideButtonTitle}>View Best Areas</Text>
              <Text style={styles.wideButtonSubtitle}>Find high-demand zones</Text>
            </View>
            <Ionicons name="chevron-forward" size={24} color={theme.colors.textSecondary} />
          </TouchableOpacity>
        </Card>

        <Card style={styles.card}>
          <TouchableOpacity style={styles.wideButton} onPress={() => {}}>
            <Ionicons name="time" size={32} color={theme.colors.primary} />
            <View style={styles.wideButtonText}>
              <Text style={styles.wideButtonTitle}>Trip History</Text>
              <Text style={styles.wideButtonSubtitle}>View today's trips</Text>
            </View>
            <Ionicons name="chevron-forward" size={24} color={theme.colors.textSecondary} />
          </TouchableOpacity>
        </Card>

        {/* End Shift Button */}
        <TouchableOpacity style={styles.endShiftButton} onPress={() => {
          Alert.alert(
            'End Shift?',
            'This will end your driving session and show your earnings summary.',
            [
              { text: 'Cancel', style: 'cancel' },
              { text: 'End Shift', style: 'destructive', onPress: async () => {
                await api.delete('/rideshare/mode');
                navigation.navigate('RideshareScreen' as never);
              }}
            ]
          );
        }}>
          <Text style={styles.endShiftText}>End Shift</Text>
        </TouchableOpacity>
      </ScrollView>

      {/* Voice Assistant Button */}
      <TouchableOpacity
        style={styles.voiceButton}
        onPress={() => setVoiceActive(!voiceActive)}
        activeOpacity={0.8}
      >
        <Ionicons 
          name={voiceActive ? "mic" : "mic-outline"} 
          size={32} 
          color="white" 
        />
      </TouchableOpacity>

      {/* Voice Assistant Modal */}
      {voiceActive && (
        <VoiceAssistant
          isVisible={voiceActive}
          onClose={() => setVoiceActive(false)}
          onCommand={handleVoiceCommand}
          mode="driver"
        />
      )}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: theme.spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  backButton: {
    marginRight: theme.spacing.md,
  },
  statsContainer: {
    flex: 1,
  },
  earningsText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: theme.colors.primary,
  },
  statsSubtext: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.xs,
  },
  content: {
    flex: 1,
    padding: theme.spacing.md,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: theme.spacing.md,
  },
  actionGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.xl,
  },
  actionButton: {
    width: BUTTON_SIZE,
    height: BUTTON_SIZE,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.md,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  actionLabel: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text,
    marginTop: theme.spacing.md,
    textAlign: 'center',
  },
  voiceHint: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.xs,
    fontStyle: 'italic',
  },
  card: {
    marginBottom: theme.spacing.md,
  },
  wideButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: theme.spacing.lg,
  },
  wideButtonText: {
    flex: 1,
    marginLeft: theme.spacing.md,
  },
  wideButtonTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text,
  },
  wideButtonSubtitle: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.xs,
  },
  endShiftButton: {
    backgroundColor: theme.colors.error,
    padding: theme.spacing.lg,
    borderRadius: theme.borderRadius.lg,
    alignItems: 'center',
    marginTop: theme.spacing.xl,
    marginBottom: theme.spacing.xl,
  },
  endShiftText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: 'white',
  },
  voiceButton: {
    position: 'absolute',
    bottom: theme.spacing.xl,
    right: theme.spacing.lg,
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: theme.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
});