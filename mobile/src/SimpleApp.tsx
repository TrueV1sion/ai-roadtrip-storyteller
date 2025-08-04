import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, Button, Alert } from 'react-native';
import { StatusBar } from 'expo-status-bar';

export default function SimpleApp() {
  const testBackend = async () => {
    try {
      const response = await fetch('https://roadtrip-mvp-792001900150.us-central1.run.app/health');
      const data = await response.json();
      Alert.alert('Backend Status', `Connected!\n${JSON.stringify(data, null, 2)}`);
    } catch (error) {
      Alert.alert('Error', 'Failed to connect to backend');
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="auto" />
      <View style={styles.content}>
        <Text style={styles.title}>🚗 AI Road Trip</Text>
        <Text style={styles.subtitle}>Expo SDK 53 Preview</Text>
        
        <View style={styles.info}>
          <Text style={styles.infoText}>✅ App is running on SDK 53!</Text>
          <Text style={styles.infoText}>✅ Production backend ready</Text>
        </View>

        <Button 
          title="Test Backend Connection" 
          onPress={testBackend}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 18,
    color: '#666',
    marginBottom: 30,
  },
  info: {
    marginBottom: 30,
  },
  infoText: {
    fontSize: 16,
    marginBottom: 5,
  },
});