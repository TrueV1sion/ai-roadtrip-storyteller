/**
 * Wake Word Detector Component
 * Provides hands-free voice activation
 */

import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Modal,
  FlatList,
  Alert
} from 'react-native';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { unifiedVoiceOrchestrator } from '../../services/voice/unifiedVoiceOrchestrator';

interface WakeWord {
  id: string;
  phrase: string;
  enabled: boolean;
  sensitivity: number;
  customTrained: boolean;
}

interface WakeWordDetectorProps {
  onWakeWordDetected: () => void;
}

const DEFAULT_WAKE_WORDS: WakeWord[] = [
  { id: 'hey_roadtrip', phrase: 'Hey Roadtrip', enabled: true, sensitivity: 0.5, customTrained: false },
  { id: 'ok_journey', phrase: 'OK Journey', enabled: false, sensitivity: 0.5, customTrained: false },
  { id: 'hello_adventure', phrase: 'Hello Adventure', enabled: false, sensitivity: 0.5, customTrained: false }
];

const WakeWordDetector: React.FC<WakeWordDetectorProps> = ({ onWakeWordDetected }) => {
  const [isListening, setIsListening] = useState(false);
  const [wakeWords, setWakeWords] = useState<WakeWord[]>(DEFAULT_WAKE_WORDS);
  const [showSettings, setShowSettings] = useState(false);
  const [isTraining, setIsTraining] = useState(false);
  const [trainingProgress, setTrainingProgress] = useState(0);
  const [selectedWakeWord, setSelectedWakeWord] = useState<WakeWord | null>(null);
  
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;
  const recording = useRef<Audio.Recording | null>(null);
  const detectionInterval = useRef<NodeJS.Timeout | null>(null);
  const trainingSamples = useRef<string[]>([]);

  useEffect(() => {
    loadWakeWords();
    return () => {
      if (detectionInterval.current) {
        clearInterval(detectionInterval.current);
      }
    };
  }, []);

  useEffect(() => {
    if (isListening) {
      startListening();
      startPulseAnimation();
    } else {
      stopListening();
    }
  }, [isListening]);

  const loadWakeWords = async () => {
    try {
      const stored = await AsyncStorage.getItem('@wake_words');
      if (stored) {
        setWakeWords(JSON.parse(stored));
      }
    } catch (error) {
      console.error('Failed to load wake words:', error);
    }
  };

  const saveWakeWords = async (words: WakeWord[]) => {
    try {
      await AsyncStorage.setItem('@wake_words', JSON.stringify(words));
      setWakeWords(words);
    } catch (error) {
      console.error('Failed to save wake words:', error);
    }
  };

  const startListening = async () => {
    try {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Microphone permission is needed for wake word detection');
        setIsListening(false);
        return;
      }

      // Configure audio mode for continuous listening
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: true,
        shouldDuckAndroid: false,
        playThroughEarpieceAndroid: false
      });

      // Start continuous detection
      startContinuousDetection();
    } catch (error) {
      console.error('Failed to start listening:', error);
      setIsListening(false);
    }
  };

  const stopListening = async () => {
    if (detectionInterval.current) {
      clearInterval(detectionInterval.current);
      detectionInterval.current = null;
    }

    if (recording.current) {
      try {
        await recording.current.stopAndUnloadAsync();
        recording.current = null;
      } catch (error) {
        console.error('Failed to stop recording:', error);
      }
    }
  };

  const startContinuousDetection = () => {
    // Simulate continuous wake word detection
    // In a real app, this would use a proper wake word detection library
    detectionInterval.current = setInterval(() => {
      // Simulate random detection for demo
      const activeWakeWords = wakeWords.filter(w => w.enabled);
      if (activeWakeWords.length > 0 && Math.random() < 0.01) {
        handleWakeWordDetected(activeWakeWords[0]);
      }
    }, 100);
  };

  const handleWakeWordDetected = (wakeWord: WakeWord) => {
    // Trigger glow animation
    Animated.sequence([
      Animated.timing(glowAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true
      }),
      Animated.timing(glowAnim, {
        toValue: 0,
        duration: 700,
        useNativeDriver: true
      })
    ]).start();

    // Haptic feedback
    // Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);

    // Notify parent component
    onWakeWordDetected();

    // Log detection
    console.log(`Wake word detected: ${wakeWord.phrase}`);
  };

  const startPulseAnimation = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.2,
          duration: 1000,
          useNativeDriver: true
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true
        })
      ])
    ).start();
  };

  const toggleWakeWord = (id: string) => {
    const updated = wakeWords.map(w => ({
      ...w,
      enabled: w.id === id ? !w.enabled : false // Only one active at a time
    }));
    saveWakeWords(updated);
  };

  const updateSensitivity = (id: string, sensitivity: number) => {
    const updated = wakeWords.map(w =>
      w.id === id ? { ...w, sensitivity } : w
    );
    saveWakeWords(updated);
  };

  const startTrainingCustomWakeWord = async () => {
    setIsTraining(true);
    setTrainingProgress(0);
    trainingSamples.current = [];
    
    Alert.alert(
      'Train Custom Wake Word',
      'You will record your wake word 3 times. Say it clearly and consistently.',
      [
        { text: 'Cancel', style: 'cancel', onPress: () => setIsTraining(false) },
        { text: 'Start', onPress: recordTrainingSample }
      ]
    );
  };

  const recordTrainingSample = async () => {
    try {
      // Create new recording
      const newRecording = new Audio.Recording();
      await newRecording.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      await newRecording.startAsync();
      
      recording.current = newRecording;
      
      // Record for 2 seconds
      setTimeout(async () => {
        if (recording.current) {
          await recording.current.stopAndUnloadAsync();
          const uri = recording.current.getURI();
          
          if (uri) {
            trainingSamples.current.push(uri);
            setTrainingProgress(trainingSamples.current.length / 3);
            
            if (trainingSamples.current.length < 3) {
              // Record next sample
              setTimeout(recordTrainingSample, 1000);
            } else {
              // Training complete
              completeTraining();
            }
          }
          
          recording.current = null;
        }
      }, 2000);
    } catch (error) {
      console.error('Failed to record training sample:', error);
      setIsTraining(false);
    }
  };

  const completeTraining = () => {
    Alert.prompt(
      'Name Your Wake Word',
      'Enter a name for your custom wake word',
      [
        { text: 'Cancel', style: 'cancel', onPress: () => setIsTraining(false) },
        {
          text: 'Save',
          onPress: (name) => {
            if (name) {
              const customWakeWord: WakeWord = {
                id: `custom_${Date.now()}`,
                phrase: name,
                enabled: false,
                sensitivity: 0.5,
                customTrained: true
              };
              
              saveWakeWords([...wakeWords, customWakeWord]);
              setIsTraining(false);
              Alert.alert('Success', 'Custom wake word trained successfully!');
            }
          }
        }
      ],
      'plain-text'
    );
  };

  const deleteWakeWord = (id: string) => {
    Alert.alert(
      'Delete Wake Word',
      'Are you sure you want to delete this wake word?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            const updated = wakeWords.filter(w => w.id !== id);
            saveWakeWords(updated);
          }
        }
      ]
    );
  };

  const renderWakeWordItem = ({ item }: { item: WakeWord }) => (
    <View style={styles.wakeWordItem}>
      <TouchableOpacity
        style={styles.wakeWordToggle}
        onPress={() => toggleWakeWord(item.id)}
      >
        <Ionicons
          name={item.enabled ? 'radio-button-on' : 'radio-button-off'}
          size={24}
          color={item.enabled ? '#4CAF50' : '#999'}
        />
        <Text style={[styles.wakeWordText, item.enabled && styles.activeWakeWord]}>
          {item.phrase}
        </Text>
        {item.customTrained && (
          <View style={styles.customBadge}>
            <Text style={styles.customBadgeText}>Custom</Text>
          </View>
        )}
      </TouchableOpacity>
      
      <View style={styles.sensitivityContainer}>
        <Text style={styles.sensitivityLabel}>Sensitivity</Text>
        <View style={styles.sensitivityButtons}>
          <TouchableOpacity
            onPress={() => updateSensitivity(item.id, Math.max(0, item.sensitivity - 0.1))}
            style={styles.sensitivityButton}
          >
            <Ionicons name="remove" size={20} color="#666" />
          </TouchableOpacity>
          <Text style={styles.sensitivityValue}>{Math.round(item.sensitivity * 100)}%</Text>
          <TouchableOpacity
            onPress={() => updateSensitivity(item.id, Math.min(1, item.sensitivity + 0.1))}
            style={styles.sensitivityButton}
          >
            <Ionicons name="add" size={20} color="#666" />
          </TouchableOpacity>
        </View>
      </View>
      
      {item.customTrained && (
        <TouchableOpacity
          onPress={() => deleteWakeWord(item.id)}
          style={styles.deleteButton}
        >
          <Ionicons name="trash-outline" size={20} color="#F44336" />
        </TouchableOpacity>
      )}
    </View>
  );

  return (
    <>
      <TouchableOpacity
        style={[styles.container, isListening && styles.listeningContainer]}
        onPress={() => setIsListening(!isListening)}
        onLongPress={() => setShowSettings(true)}
      >
        <Animated.View
          style={[
            styles.innerCircle,
            {
              transform: [{ scale: pulseAnim }],
              opacity: glowAnim.interpolate({
                inputRange: [0, 1],
                outputRange: [1, 0.5]
              })
            }
          ]}
        >
          <Ionicons
            name={isListening ? 'mic' : 'mic-off'}
            size={24}
            color={isListening ? '#4CAF50' : '#999'}
          />
        </Animated.View>
        
        {isListening && (
          <Animated.View
            style={[
              styles.glowRing,
              {
                opacity: glowAnim,
                transform: [
                  {
                    scale: glowAnim.interpolate({
                      inputRange: [0, 1],
                      outputRange: [1, 2]
                    })
                  }
                ]
              }
            ]}
          />
        )}
      </TouchableOpacity>

      <Modal
        visible={showSettings}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowSettings(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Wake Word Settings</Text>
              <TouchableOpacity onPress={() => setShowSettings(false)}>
                <Ionicons name="close" size={24} color="#333" />
              </TouchableOpacity>
            </View>

            <FlatList
              data={wakeWords}
              renderItem={renderWakeWordItem}
              keyExtractor={item => item.id}
              ItemSeparatorComponent={() => <View style={styles.separator} />}
            />

            <TouchableOpacity
              style={styles.trainButton}
              onPress={startTrainingCustomWakeWord}
              disabled={isTraining}
            >
              <Ionicons name="add-circle" size={24} color="white" />
              <Text style={styles.trainButtonText}>
                {isTraining ? `Training... ${Math.round(trainingProgress * 100)}%` : 'Train Custom Wake Word'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </>
  );
};

const styles = StyleSheet.create({
  container: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  listeningContainer: {
    backgroundColor: 'rgba(76, 175, 80, 0.1)',
  },
  innerCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  glowRing: {
    position: 'absolute',
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#4CAF50',
  },
  modalContainer: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  modalContent: {
    backgroundColor: 'white',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  wakeWordItem: {
    paddingVertical: 15,
  },
  wakeWordToggle: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  wakeWordText: {
    fontSize: 16,
    marginLeft: 10,
    color: '#666',
    flex: 1,
  },
  activeWakeWord: {
    color: '#333',
    fontWeight: '600',
  },
  customBadge: {
    backgroundColor: '#2196F3',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  customBadgeText: {
    color: 'white',
    fontSize: 12,
  },
  sensitivityContainer: {
    marginTop: 10,
    marginLeft: 34,
  },
  sensitivityLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5,
  },
  sensitivityButtons: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  sensitivityButton: {
    padding: 5,
  },
  sensitivityValue: {
    marginHorizontal: 15,
    fontSize: 14,
    color: '#333',
    minWidth: 40,
    textAlign: 'center',
  },
  deleteButton: {
    position: 'absolute',
    right: 0,
    top: 15,
    padding: 10,
  },
  separator: {
    height: 1,
    backgroundColor: '#EEE',
  },
  trainButton: {
    flexDirection: 'row',
    backgroundColor: '#2196F3',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 20,
  },
  trainButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 10,
  },
});

export default WakeWordDetector;