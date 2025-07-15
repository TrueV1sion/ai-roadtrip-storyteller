import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Animated,
  Image,
  Platform
} from 'react-native';
import { NarrativeNodeType, NarrativeChoiceType } from '../../types/narrative';
import { FontAwesome5 } from '@expo/vector-icons';

interface StoryNodeProps {
  node: NarrativeNodeType;
  personalizedContent: Record<string, any>;
  choices: NarrativeChoiceType[];
  onChoiceSelected: (choiceId: string) => void;
  loading?: boolean;
}

const StoryNode: React.FC<StoryNodeProps> = ({
  node,
  personalizedContent,
  choices,
  onChoiceSelected,
  loading = false
}) => {
  const [fadeAnim] = useState(new Animated.Value(0));
  const [choicesFadeAnim] = useState(new Animated.Value(0));
  
  useEffect(() => {
    // Fade in content
    Animated.sequence([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true
      }),
      Animated.timing(choicesFadeAnim, {
        toValue: 1,
        duration: 300,
        delay: 800,
        useNativeDriver: true
      })
    ]).start();
  }, [node.id]);
  
  // Get displayed content (prefer personalized if available)
  const displayContent = personalizedContent?.content || node.content;
  
  return (
    <View style={styles.container}>
      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#4A90E2" />
          <Text style={styles.loadingText}>Loading story...</Text>
        </View>
      ) : (
        <>
          <Animated.View style={{ opacity: fadeAnim }}>
            <Text style={styles.title}>{node.title}</Text>
            
            {/* Optional image if available */}
            {personalizedContent?.image_url && (
              <Image 
                source={{ uri: personalizedContent.image_url }} 
                style={styles.storyImage}
                resizeMode="cover"
              />
            )}
            
            <ScrollView style={styles.contentContainer}>
              <Text style={styles.content}>{displayContent}</Text>
            </ScrollView>
          </Animated.View>
          
          <Animated.View 
            style={[
              styles.choicesContainer, 
              { opacity: choicesFadeAnim }
            ]}
          >
            <Text style={styles.choicesHeader}>What will you do?</Text>
            
            {choices.map((choice) => (
              <TouchableOpacity
                key={choice.id}
                style={styles.choiceButton}
                onPress={() => onChoiceSelected(choice.id)}
                activeOpacity={0.7}
              >
                <Text style={styles.choiceText}>{choice.text}</Text>
                <Text style={styles.choiceDescription}>{choice.description}</Text>
                <FontAwesome5 
                  name="chevron-right" 
                  size={16} 
                  color="#4A90E2" 
                  style={styles.choiceIcon}
                />
              </TouchableOpacity>
            ))}
          </Animated.View>
        </>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#fff'
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center'
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666'
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 15,
    color: '#333',
    fontFamily: Platform.OS === 'ios' ? 'Georgia' : 'serif'
  },
  storyImage: {
    width: '100%',
    height: 200,
    borderRadius: 10,
    marginBottom: 15
  },
  contentContainer: {
    maxHeight: '50%',
    marginBottom: 20
  },
  content: {
    fontSize: 16,
    lineHeight: 24,
    color: '#444',
    fontFamily: Platform.OS === 'ios' ? 'Avenir' : 'sans-serif',
    marginBottom: 20
  },
  choicesContainer: {
    marginTop: 10
  },
  choicesHeader: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#555',
    textAlign: 'center'
  },
  choiceButton: {
    backgroundColor: '#f8f8f8',
    borderRadius: 8,
    padding: 15,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    flexDirection: 'column'
  },
  choiceText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 5
  },
  choiceDescription: {
    fontSize: 14,
    color: '#666',
    paddingRight: 20
  },
  choiceIcon: {
    position: 'absolute',
    right: 15,
    top: '50%',
    marginTop: -8
  }
});

export default StoryNode;