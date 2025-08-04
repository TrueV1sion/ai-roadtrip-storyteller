import React, { useState } from 'react';
import { View, StyleSheet, ScrollView, Switch } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { logger } from '@/services/logger';
import { 
  Text, 
  List, 
  Divider, 
  Surface,
  IconButton,
  Button,
  Dialog,
  Portal,
} from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';

import { COLORS, SPACING } from '../theme';
import SettingsService from '../services/SettingsService';
import AnalyticsService from '../services/AnalyticsService';

const SettingsScreen: React.FC = () => {
  const navigation = useNavigation();
  const [voiceGuidanceEnabled, setVoiceGuidanceEnabled] = useState(true);
  const [autoplayStoriesEnabled, setAutoplayStoriesEnabled] = useState(true);
  const [darkModeEnabled, setDarkModeEnabled] = useState(false);
  const [showLogoutDialog, setShowLogoutDialog] = useState(false);
  const [showClearDataDialog, setShowClearDataDialog] = useState(false);
  
  const handleVoiceGuidanceToggle = async () => {
    const newValue = !voiceGuidanceEnabled;
    setVoiceGuidanceEnabled(newValue);
    
    try {
      // Save setting using SettingsService
      await SettingsService.saveSetting('voiceGuidance', newValue);
      
      // Log analytics event
      AnalyticsService.logEvent('setting_changed', {
        setting: 'voiceGuidance',
        value: newValue
      });
    } catch (error) {
      logger.error('Failed to save voice guidance setting:', error);
    }
  };
  
  const handleAutoplayStoriesToggle = async () => {
    const newValue = !autoplayStoriesEnabled;
    setAutoplayStoriesEnabled(newValue);
    
    try {
      // Save setting using SettingsService
      await SettingsService.saveSetting('autoplayStories', newValue);
      
      // Log analytics event
      AnalyticsService.logEvent('setting_changed', {
        setting: 'autoplayStories',
        value: newValue
      });
    } catch (error) {
      logger.error('Failed to save autoplay stories setting:', error);
    }
  };
  
  const handleDarkModeToggle = async () => {
    const newValue = !darkModeEnabled;
    setDarkModeEnabled(newValue);
    
    try {
      // Save setting using SettingsService
      await SettingsService.saveSetting('darkMode', newValue);
      
      // Log analytics event
      AnalyticsService.logEvent('setting_changed', {
        setting: 'darkMode',
        value: newValue
      });
      
      // Theme would be updated through a context provider in a real app
    } catch (error) {
      logger.error('Failed to save dark mode setting:', error);
    }
  };
  
  const handleLogout = () => {
    setShowLogoutDialog(true);
  };
  
  const confirmLogout = async () => {
    try {
      // Perform logout
      // auth.signOut() or similar
      
      // Log analytics event
      AnalyticsService.logEvent('user_logout');
      
      setShowLogoutDialog(false);
      
      // Navigate to login screen
      // navigation.navigate('Auth');
    } catch (error) {
      logger.error('Failed to logout:', error);
    }
  };
  
  const handleClearData = () => {
    setShowClearDataDialog(true);
  };
  
  const confirmClearData = async () => {
    try {
      // Clear user data
      // await UserDataService.clearAllData();
      
      // Log analytics event
      AnalyticsService.logEvent('clear_user_data');
      
      setShowClearDataDialog(false);
    } catch (error) {
      logger.error('Failed to clear data:', error);
    }
  };
  
  return (
    <ScrollView style={styles.container}>
      <Surface style={styles.section}>
        <Text style={styles.sectionTitle}>App Settings</Text>
        
        <List.Item
          title="Voice Guidance"
          description="Enable voice instructions during navigation"
          left={props => <List.Icon {...props} icon="volume-high" />}
          right={() => (
            <Switch
              value={voiceGuidanceEnabled}
              onValueChange={handleVoiceGuidanceToggle}
              color={COLORS.primary}
            />
          )}
        />
        
        <Divider />
        
        <List.Item
          title="Autoplay Stories"
          description="Automatically play location stories when you arrive"
          left={props => <List.Icon {...props} icon="play-circle-outline" />}
          right={() => (
            <Switch
              value={autoplayStoriesEnabled}
              onValueChange={handleAutoplayStoriesToggle}
              color={COLORS.primary}
            />
          )}
        />
        
        <Divider />
        
        <List.Item
          title="Dark Mode"
          description="Use dark theme throughout the app"
          left={props => <List.Icon {...props} icon="brightness-4" />}
          right={() => (
            <Switch
              value={darkModeEnabled}
              onValueChange={handleDarkModeToggle}
              color={COLORS.primary}
            />
          )}
        />

        <Divider />
        
        <List.Item
          title="Offline Maps & Routes"
          description="Download areas for offline use"
          left={props => <List.Icon {...props} icon="map-outline" />}
          right={props => <IconButton {...props} icon="chevron-right" onPress={() => navigation.navigate('Offline' as never)} />}
          onPress={() => navigation.navigate('Offline' as never)}
        />
      </Surface>
      
      <Surface style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        
        <List.Item
          title="Profile"
          description="Manage your profile information"
          left={props => <List.Icon {...props} icon="account-circle-outline" />}
          right={props => <IconButton {...props} icon="chevron-right" onPress={() => navigation.navigate('Profile' as never)} />}
          onPress={() => navigation.navigate('Profile' as never)}
        />
        
        <Divider />
        
        <List.Item
          title="Notifications"
          description="Manage your notification preferences"
          left={props => <List.Icon {...props} icon="bell-outline" />}
          right={props => <IconButton {...props} icon="chevron-right" onPress={() => navigation.navigate('Notifications' as never)} />}
          onPress={() => navigation.navigate('Notifications' as never)}
        />
        
        <Divider />
        
        <List.Item
          title="Privacy"
          description="Manage your privacy settings"
          left={props => <List.Icon {...props} icon="shield-account-outline" />}
          right={props => <IconButton {...props} icon="chevron-right" onPress={() => navigation.navigate('Privacy' as never)} />}
          onPress={() => navigation.navigate('Privacy' as never)}
        />
      </Surface>
      
      <Surface style={styles.section}>
        <Text style={styles.sectionTitle}>Support</Text>
        
        <List.Item
          title="Help & Support"
          description="Get help with using the app"
          left={props => <List.Icon {...props} icon="help-circle-outline" />}
          right={props => <IconButton {...props} icon="chevron-right" onPress={() => navigation.navigate('Help' as never)} />}
          onPress={() => navigation.navigate('Help' as never)}
        />
        
        <Divider />
        
        <List.Item
          title="About"
          description="Learn more about this app"
          left={props => <List.Icon {...props} icon="information-outline" />}
          right={props => <IconButton {...props} icon="chevron-right" onPress={() => navigation.navigate('About' as never)} />}
          onPress={() => navigation.navigate('About' as never)}
        />
      </Surface>
      
      <Surface style={styles.section}>
        <Text style={styles.sectionTitle}>Data</Text>
        
        <List.Item
          title="Clear App Data"
          description="Remove all your saved data from this device"
          left={props => <List.Icon {...props} icon="delete-outline" color={COLORS.error} />}
          onPress={handleClearData}
        />
        
        <Divider />
        
        <List.Item
          title="Logout"
          description="Sign out of your account"
          left={props => <List.Icon {...props} icon="logout" color={COLORS.error} />}
          onPress={handleLogout}
        />
      </Surface>
      
      <View style={styles.versionContainer}>
        <Text style={styles.versionText}>Version 1.0.0</Text>
      </View>
      
      {/* Logout confirmation dialog */}
      <Portal>
        <Dialog
          visible={showLogoutDialog}
          onDismiss={() => setShowLogoutDialog(false)}
        >
          <Dialog.Title>Logout</Dialog.Title>
          <Dialog.Content>
            <Text>Are you sure you want to logout?</Text>
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setShowLogoutDialog(false)}>Cancel</Button>
            <Button onPress={confirmLogout}>Logout</Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
      
      {/* Clear data confirmation dialog */}
      <Portal>
        <Dialog
          visible={showClearDataDialog}
          onDismiss={() => setShowClearDataDialog(false)}
        >
          <Dialog.Title>Clear App Data</Dialog.Title>
          <Dialog.Content>
            <Text>
              This will remove all your saved routes, preferences, and cached data from this device.
              This action cannot be undone. Are you sure you want to continue?
            </Text>
          </Dialog.Content>
          <Dialog.Actions>
            <Button onPress={() => setShowClearDataDialog(false)}>Cancel</Button>
            <Button 
              color={COLORS.error}
              onPress={confirmClearData}
            >
              Clear Data
            </Button>
          </Dialog.Actions>
        </Dialog>
      </Portal>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  section: {
    margin: SPACING.medium,
    borderRadius: 8,
    overflow: 'hidden',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginHorizontal: SPACING.medium,
    marginVertical: SPACING.small,
  },
  versionContainer: {
    alignItems: 'center',
    padding: SPACING.medium,
  },
  versionText: {
    color: COLORS.textSecondary,
    fontSize: 14,
  },
});

export default SettingsScreen; 