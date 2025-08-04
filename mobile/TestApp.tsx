/**
 * Standalone Test App for Voice Personalities
 * Run this to test the voice personality system
 */

import React from 'react';
import { SafeAreaView, StatusBar } from 'react-native';
import { VoicePersonalityTestScreen } from './src/screens/VoicePersonalityTest';

export default function TestApp() {
  return (
    <>
      <StatusBar barStyle="dark-content" />
      <SafeAreaView style={{ flex: 1 }}>
        <VoicePersonalityTestScreen />
      </SafeAreaView>
    </>
  );
}