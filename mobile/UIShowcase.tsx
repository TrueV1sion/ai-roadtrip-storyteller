/**
 * UI Showcase - View All App Components
 * Displays all the main screens and components for preview
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  StatusBar,
} from 'react-native';

// Import your main components
import { VoiceButton, StoryCard, NavigationStatus } from './src/design/components';
import { DesignShowcaseScreen } from './src/screens/DesignShowcase';

// Import some key screens for preview
// Note: Some imports might fail due to dependencies, we'll handle that
const ComponentShowcase = () => {
  const [activeScreen, setActiveScreen] = useState('components');

  const renderScreen = () => {
    switch (activeScreen) {
      case 'design':
        return <DesignShowcaseScreen />;
      case 'components':
      default:
        return (
          <ScrollView style={styles.container}>
            <Text style={styles.title}>RoadTrip Mobile App - Component Showcase</Text>
            
            {/* Voice Button */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Voice Interaction</Text>
              <VoiceButton
                onPress={() => console.log('Voice button pressed')}
                listening={false}
                disabled={false}
                size="large"
              />
            </View>

            {/* Story Card */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Story Display</Text>
              <StoryCard
                title="The Mystery of Route 66"
                description="A fascinating tale of America's most iconic highway and the adventures that await..."
                imageUrl="https://images.unsplash.com/photo-1469474968028-56623f02e42e"
                duration="5 min"
                onPress={() => console.log('Story selected')}
              />
            </View>

            {/* Navigation Status */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Navigation Status</Text>
              <NavigationStatus
                isNavigating={true}
                currentStep="Turn right on Main Street"
                distance="0.3 miles"
                timeRemaining="12 min"
                progress={0.45}
              />
            </View>

            {/* Feature Overview */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>App Features</Text>
              <View style={styles.featureGrid}>
                <FeatureCard title="20+ Voice Personalities" icon="🎭" />
                <FeatureCard title="Real-time Booking" icon="🎫" />
                <FeatureCard title="AR Experiences" icon="🥽" />
                <FeatureCard title="Interactive Games" icon="🎮" />
                <FeatureCard title="Offline Discovery" icon="📍" />
                <FeatureCard title="Social Sharing" icon="📱" />
              </View>
            </View>

            {/* Screen Navigation */}
            <View style={styles.section}>
              <Text style={styles.sectionTitle}>Available Screens</Text>
              {screenList.map((screen) => (
                <TouchableOpacity key={screen} style={styles.screenButton}>
                  <Text style={styles.screenButtonText}>{screen}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </ScrollView>
        );
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="dark-content" backgroundColor="#f8f9fa" />
      
      {/* Tab Bar */}
      <View style={styles.tabBar}>
        <TouchableOpacity
          style={[styles.tab, activeScreen === 'components' && styles.activeTab]}
          onPress={() => setActiveScreen('components')}
        >
          <Text style={[styles.tabText, activeScreen === 'components' && styles.activeTabText]}>
            Components
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeScreen === 'design' && styles.activeTab]}
          onPress={() => setActiveScreen('design')}
        >
          <Text style={[styles.tabText, activeScreen === 'design' && styles.activeTabText]}>
            Design System
          </Text>
        </TouchableOpacity>
      </View>

      {renderScreen()}
    </SafeAreaView>
  );
};

const FeatureCard = ({ title, icon }: { title: string; icon: string }) => (
  <View style={styles.featureCard}>
    <Text style={styles.featureIcon}>{icon}</Text>
    <Text style={styles.featureTitle}>{title}</Text>
  </View>
);

const screenList = [
  'ImmersiveExperience - Main storytelling interface',
  'ActiveNavigationScreen - GPS navigation with stories',
  'VoicePersonalityScreen - 20+ voice personalities',
  'BookingScreen - Real-time reservations',
  'ARScreen - Augmented reality overlays',
  'TriviaGameScreen - Interactive travel games',
  'ScavengerHuntScreen - Location-based challenges',
  'SocialSharingScreen - Share discoveries',
  'RideshareDriverModeScreen - Driver optimization',
  'OfflineDiscoveryScreen - Works without internet',
  'AccessibilitySettingsScreen - Full accessibility',
  'SecurityScreen - Enterprise-grade security'
];

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  tab: {
    flex: 1,
    paddingVertical: 16,
    alignItems: 'center',
  },
  activeTab: {
    borderBottomWidth: 3,
    borderBottomColor: '#007bff',
  },
  tabText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#6c757d',
  },
  activeTabText: {
    color: '#007bff',
  },
  container: {
    flex: 1,
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#212529',
    marginBottom: 24,
    textAlign: 'center',
  },
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#495057',
    marginBottom: 16,
  },
  featureGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  featureCard: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    minWidth: '45%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  featureIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  featureTitle: {
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
    color: '#495057',
  },
  screenButton: {
    backgroundColor: '#e9ecef',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
  },
  screenButtonText: {
    fontSize: 16,
    color: '#495057',
  },
});

export default ComponentShowcase;