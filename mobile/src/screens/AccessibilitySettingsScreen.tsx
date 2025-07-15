import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, Platform } from 'react-native';
import { Text, List, Switch, Button, Divider, Surface, Slider } from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';

import { COLORS, SPACING } from '../theme';
import { useTranslation } from '../i18n';
import { useAccessibility } from '../services/AccessibilityProvider';

const AccessibilitySettingsScreen: React.FC = () => {
  const { t } = useTranslation();
  const { preferences, updatePreferences, isScreenReaderEnabled } = useAccessibility();
  const [textSizeValue, setTextSizeValue] = useState(preferences.largeText ? 1.3 : 1.0);

  // Trigger haptic feedback when user interacts with a control
  const triggerHaptic = () => {
    if (preferences.hapticFeedback && Platform.OS !== 'web') {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
  };

  // Handle toggle of any boolean preference
  const handleTogglePreference = async (key: keyof typeof preferences) => {
    triggerHaptic();
    await updatePreferences({ [key]: !preferences[key] });
  };

  // Handle text size changes
  const handleTextSizeChange = async (value: number) => {
    setTextSizeValue(value);
    triggerHaptic();
    await updatePreferences({ largeText: value > 1.15 });
  };

  // Function to reset to default settings
  const handleResetToDefaults = async () => {
    triggerHaptic();
    await updatePreferences({
      highContrast: false,
      largeText: false,
      reduceMotion: false,
      screenReader: isScreenReaderEnabled, // Keep screen reader setting as is
      hapticFeedback: true,
    });
    setTextSizeValue(1.0);
  };

  return (
    <ScrollView 
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
      accessibilityRole="scrollable"
    >
      <Text style={styles.screenTitle} accessibilityRole="header">
        {t('accessibility.title')}
      </Text>
      
      {/* Visual Settings */}
      <Surface style={styles.section}>
        <Text style={styles.sectionTitle}>{t('accessibility.visual')}</Text>
        
        <View style={styles.settingGroup}>
          <Text style={styles.settingLabel}>{t('accessibility.textSize.title')}</Text>
          <Text style={styles.settingDescription}>{t('accessibility.textSize.description')}</Text>
          
          <View style={styles.sliderContainer}>
            <Text style={styles.sliderLabel}>A</Text>
            <Slider
              value={textSizeValue}
              onValueChange={setTextSizeValue}
              onSlidingComplete={handleTextSizeChange}
              minimumValue={1.0}
              maximumValue={1.5}
              step={0.1}
              minimumTrackTintColor={COLORS.primary}
              maximumTrackTintColor={COLORS.border}
              thumbTintColor={COLORS.primary}
              style={styles.slider}
              accessibilityLabel={t('accessibility.textSize.title')}
              accessibilityHint="Slide right to increase text size, slide left to decrease"
            />
            <Text style={styles.sliderLabelLarge}>A</Text>
          </View>
        </View>
        
        <Divider style={styles.divider} />
        
        <List.Item
          title={t('accessibility.highContrast.title')}
          description={t('accessibility.highContrast.description')}
          left={props => <List.Icon {...props} icon="contrast" />}
          right={() => (
            <Switch
              value={preferences.highContrast}
              onValueChange={() => handleTogglePreference('highContrast')}
              color={COLORS.primary}
              accessibilityLabel={`${t('accessibility.highContrast.title')} ${preferences.highContrast ? t('accessibility.highContrast.enabled') : t('accessibility.highContrast.disabled')}`}
            />
          )}
          accessibilityRole="switch"
        />
        
        <Divider style={styles.divider} />
        
        <List.Item
          title={t('accessibility.reduceMotion.title')}
          description={t('accessibility.reduceMotion.description')}
          left={props => <List.Icon {...props} icon="motion-outline" />}
          right={() => (
            <Switch
              value={preferences.reduceMotion}
              onValueChange={() => handleTogglePreference('reduceMotion')}
              color={COLORS.primary}
            />
          )}
          accessibilityRole="switch"
        />
      </Surface>
      
      {/* Interaction Settings */}
      <Surface style={styles.section}>
        <Text style={styles.sectionTitle}>{t('accessibility.interaction')}</Text>
        
        <List.Item
          title={t('accessibility.screenReader.title')}
          description={t('accessibility.screenReader.description')}
          left={props => <List.Icon {...props} icon="text-to-speech" />}
          right={() => (
            <Switch
              value={preferences.screenReader}
              onValueChange={() => handleTogglePreference('screenReader')}
              color={COLORS.primary}
              disabled={isScreenReaderEnabled} // Disabled if screen reader is already enabled
            />
          )}
          accessibilityRole="switch"
        />
        
        <Divider style={styles.divider} />
        
        <List.Item
          title={t('accessibility.hapticFeedback.title')}
          description={t('accessibility.hapticFeedback.description')}
          left={props => <List.Icon {...props} icon="vibrate" />}
          right={() => (
            <Switch
              value={preferences.hapticFeedback}
              onValueChange={() => handleTogglePreference('hapticFeedback')}
              color={COLORS.primary}
            />
          )}
          accessibilityRole="switch"
        />
      </Surface>
      
      {/* Help & Resources */}
      <Surface style={styles.section}>
        <Text style={styles.sectionTitle}>{t('accessibility.help')}</Text>
        
        <List.Item
          title={t('accessibility.tutorial.title')}
          description={t('accessibility.tutorial.description')}
          left={props => <List.Icon {...props} icon="help-circle" />}
          onPress={() => {/* Navigate to tutorial */}}
          accessibilityRole="button"
          accessibilityHint="Opens the accessibility tutorial"
        />
        
        <Divider style={styles.divider} />
        
        <List.Item
          title={t('accessibility.contact.title')}
          description={t('accessibility.contact.description')}
          left={props => <List.Icon {...props} icon="email" />}
          onPress={() => {/* Open support contact */}}
          accessibilityRole="button"
          accessibilityHint="Opens contact form for accessibility support"
        />
      </Surface>
      
      {/* Reset to Default Button */}
      <View style={styles.resetContainer}>
        <Button
          mode="outlined"
          onPress={handleResetToDefaults}
          accessibilityLabel={t('accessibility.reset')}
        >
          {t('accessibility.reset')}
        </Button>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  contentContainer: {
    padding: SPACING.medium,
  },
  screenTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: SPACING.medium,
  },
  section: {
    padding: SPACING.medium,
    marginBottom: SPACING.medium,
    borderRadius: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: SPACING.medium,
  },
  settingGroup: {
    marginBottom: SPACING.medium,
  },
  settingLabel: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  settingDescription: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginBottom: SPACING.small,
  },
  sliderContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: SPACING.small,
  },
  slider: {
    flex: 1,
    height: 40,
  },
  sliderLabel: {
    fontSize: 14,
    marginRight: SPACING.small,
  },
  sliderLabelLarge: {
    fontSize: 22,
    marginLeft: SPACING.small,
  },
  divider: {
    marginVertical: SPACING.small,
  },
  resetContainer: {
    alignItems: 'center',
    marginVertical: SPACING.medium,
  },
});

export default AccessibilitySettingsScreen; 