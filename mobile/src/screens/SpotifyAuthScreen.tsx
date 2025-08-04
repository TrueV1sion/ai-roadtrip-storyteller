import React, { useState, useEffect } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  ActivityIndicator,
  Alert,
  Linking,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import * as WebBrowser from 'expo-web-browser';
import * as AuthSession from 'expo-auth-session';
import { Ionicons } from '@expo/vector-icons';

import { apiManager } from '../services/api/apiManager';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { SafeArea } from '../components/SafeArea';
import { ScrollContainer } from '../components/ScrollContainer';
import { COLORS, SPACING } from '../theme';

WebBrowser.maybeCompleteAuthSession();

const SpotifyAuthScreen: React.FC = () => {
  const navigation = useNavigation();
  const [isConnecting, setIsConnecting] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [spotifyProfile, setSpotifyProfile] = useState<any>(null);

  useEffect(() => {
    checkSpotifyConnection();
  }, []);

  const checkSpotifyConnection = async () => {
    try {
      const profile = await apiManager.get('/spotify/profile');
      if (profile.data) {
        setIsConnected(true);
        setSpotifyProfile(profile.data);
      }
    } catch (error) {
      // Not connected
      setIsConnected(false);
    }
  };

  const initiateSpotifyAuth = async () => {
    try {
      setIsConnecting(true);
      const response = await apiManager.get('/spotify/auth');
      const { auth_url } = response.data;
      
      // Use expo-auth-session for better OAuth flow handling
      const result = await WebBrowser.openAuthSessionAsync(
        auth_url,
        AuthSession.makeRedirectUri({ useProxy: true })
      );
      
      if (result.type === 'success') {
        // Auth successful, check connection
        await checkSpotifyConnection();
        Alert.alert('Success', 'Spotify connected successfully!');
      }
    } catch (error) {
      logger.error('Spotify auth error:', error);
      Alert.alert('Error', 'Failed to connect to Spotify');
    } finally {
      setIsConnecting(false);
    }
  };

  const disconnectSpotify = async () => {
    Alert.alert(
      'Disconnect Spotify',
      'Are you sure you want to disconnect your Spotify account?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Disconnect',
          style: 'destructive',
          onPress: async () => {
            try {
              // In a real app, you'd have an endpoint to revoke tokens
              setIsConnected(false);
              setSpotifyProfile(null);
              Alert.alert('Success', 'Spotify disconnected');
            } catch (error) {
              Alert.alert('Error', 'Failed to disconnect Spotify');
            }
          },
        },
      ]
    );
  };

  const renderConnectedState = () => (
    <View style={styles.connectedContainer}>
      <Card style={styles.profileCard}>
        <View style={styles.profileHeader}>
          <Ionicons name="musical-notes-outline" size={48} color="#1DB954" />
          <Text style={styles.connectedText}>Connected</Text>
        </View>

        {spotifyProfile && (
          <View style={styles.profileInfo}>
            <Text style={styles.profileName}>
              {spotifyProfile.display_name || spotifyProfile.email}
            </Text>
            <Text style={styles.profileEmail}>{spotifyProfile.email}</Text>
            {spotifyProfile.product === 'premium' && (
              <View style={styles.premiumBadge}>
                <Text style={styles.premiumText}>Premium</Text>
              </View>
            )}
          </View>
        )}

        <TouchableOpacity
          style={styles.disconnectButton}
          onPress={disconnectSpotify}
        >
          <Text style={styles.disconnectText}>Disconnect</Text>
        </TouchableOpacity>
      </Card>

      <Card style={styles.featuresCard}>
        <Text style={styles.featuresTitle}>Spotify Features Active</Text>
        <View style={styles.featureItem}>
          <Ionicons name="checkmark-circle" size={20} color="#1DB954" />
          <Text style={styles.featureText}>Journey-based playlists</Text>
        </View>
        <View style={styles.featureItem}>
          <Ionicons name="checkmark-circle" size={20} color="#1DB954" />
          <Text style={styles.featureText}>Location-aware music</Text>
        </View>
        <View style={styles.featureItem}>
          <Ionicons name="checkmark-circle" size={20} color="#1DB954" />
          <Text style={styles.featureText}>Mood-adaptive soundtracks</Text>
        </View>
        <View style={styles.featureItem}>
          <Ionicons name="checkmark-circle" size={20} color="#1DB954" />
          <Text style={styles.featureText}>Seamless narration integration</Text>
        </View>
      </Card>
    </View>
  );

  const renderDisconnectedState = () => (
    <View style={styles.disconnectedContainer}>
      <Card style={styles.heroCard}>
        <Ionicons name="musical-notes" size={64} color="#1DB954" />
        <Text style={styles.heroTitle}>Connect Spotify</Text>
        <Text style={styles.heroDescription}>
          Enhance your road trip with personalized music that adapts to your
          journey, location, and mood.
        </Text>

        <Button
          title={isConnecting ? 'Connecting...' : 'Connect Spotify'}
          onPress={initiateSpotifyAuth}
          disabled={isConnecting}
          style={[styles.connectButton, { backgroundColor: '#1DB954' }]}
        />

        {isConnecting && (
          <ActivityIndicator
            size="small"
            color="#1DB954"
            style={styles.loader}
          />
        )}
      </Card>

      <Card style={styles.benefitsCard}>
        <Text style={styles.benefitsTitle}>Why Connect Spotify?</Text>
        
        <View style={styles.benefitItem}>
          <View style={styles.benefitIcon}>
            <Ionicons name="musical-notes" size={24} color="#1DB954" />
          </View>
          <View style={styles.benefitContent}>
            <Text style={styles.benefitTitle}>Smart Playlists</Text>
            <Text style={styles.benefitDescription}>
              AI-generated playlists that match your route and travel time
            </Text>
          </View>
        </View>

        <View style={styles.benefitItem}>
          <View style={styles.benefitIcon}>
            <Ionicons name="location" size={24} color="#1DB954" />
          </View>
          <View style={styles.benefitContent}>
            <Text style={styles.benefitTitle}>Location Music</Text>
            <Text style={styles.benefitDescription}>
              Discover music connected to the places you're visiting
            </Text>
          </View>
        </View>

        <View style={styles.benefitItem}>
          <View style={styles.benefitIcon}>
            <Ionicons name="sunny" size={24} color="#1DB954" />
          </View>
          <View style={styles.benefitContent}>
            <Text style={styles.benefitTitle}>Adaptive Soundtracks</Text>
            <Text style={styles.benefitDescription}>
              Music that changes with weather, traffic, and time of day
            </Text>
          </View>
        </View>

        <View style={styles.benefitItem}>
          <View style={styles.benefitIcon}>
            <Ionicons name="volume-medium" size={24} color="#1DB954" />
          </View>
          <View style={styles.benefitContent}>
            <Text style={styles.benefitTitle}>Smart Volume</Text>
            <Text style={styles.benefitDescription}>
              Automatic volume adjustment during narration and conversations
            </Text>
          </View>
        </View>
      </Card>
    </View>
  );

  return (
    <SafeArea>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backButton}
        >
          <Ionicons name="arrow-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Music Settings</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollContainer>
        {isConnected ? renderConnectedState() : renderDisconnectedState()}
      </ScrollContainer>
    </SafeArea>
  );
};

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: SPACING.medium,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  backButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  connectedContainer: {
    padding: SPACING.medium,
  },
  disconnectedContainer: {
    padding: SPACING.medium,
  },
  profileCard: {
    marginBottom: SPACING.medium,
  },
  profileHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: SPACING.medium,
  },
  connectedText: {
    fontSize: 14,
    color: '#1DB954',
    fontWeight: '600',
  },
  profileInfo: {
    marginBottom: SPACING.medium,
  },
  profileName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  profileEmail: {
    fontSize: 14,
    color: '#666',
  },
  premiumBadge: {
    backgroundColor: '#1DB954',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    alignSelf: 'flex-start',
    marginTop: 8,
  },
  premiumText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
  },
  disconnectButton: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#E0E0E0',
    alignSelf: 'flex-start',
  },
  disconnectText: {
    fontSize: 14,
    color: '#666',
  },
  featuresCard: {
    marginBottom: SPACING.medium,
  },
  featuresTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: SPACING.medium,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  featureText: {
    marginLeft: 12,
    fontSize: 14,
    color: '#666',
  },
  heroCard: {
    alignItems: 'center',
    marginBottom: SPACING.medium,
  },
  heroTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#333',
    marginBottom: 8,
    marginTop: SPACING.medium,
  },
  heroDescription: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginBottom: SPACING.large,
    lineHeight: 22,
  },
  connectButton: {
    paddingHorizontal: 32,
  },
  loader: {
    marginTop: SPACING.medium,
  },
  benefitsCard: {},
  benefitsTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: SPACING.medium,
  },
  benefitItem: {
    flexDirection: 'row',
    marginBottom: 20,
  },
  benefitIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#F0F9F4',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SPACING.medium,
  },
  benefitContent: {
    flex: 1,
  },
  benefitTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  benefitDescription: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
});

export default SpotifyAuthScreen;