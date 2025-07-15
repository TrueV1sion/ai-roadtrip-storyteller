import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  Platform
} from 'react-native';
import { FontAwesome5, MaterialIcons } from '@expo/vector-icons';
import { VoiceCharacterType } from '../../types/voice';

interface CharacterCardProps {
  character: VoiceCharacterType;
  selected?: boolean;
  onSelect?: () => void;
  onPlaySample?: () => void;
}

const CharacterCard: React.FC<CharacterCardProps> = ({
  character,
  selected = false,
  onSelect,
  onPlaySample
}) => {
  // Get gender icon
  const getGenderIcon = () => {
    switch (character.gender) {
      case 'male':
        return <FontAwesome5 name="mars" size={14} color="#2196F3" />;
      case 'female':
        return <FontAwesome5 name="venus" size={14} color="#E91E63" />;
      default:
        return <FontAwesome5 name="genderless" size={14} color="#9C27B0" />;
    }
  };
  
  // Get age text
  const getAgeText = () => {
    switch (character.age) {
      case 'child':
        return 'Child';
      case 'young':
        return 'Young adult';
      case 'adult':
        return 'Adult';
      case 'senior':
        return 'Senior';
      default:
        return 'Adult';
    }
  };
  
  // Get accent display name
  const getAccentDisplay = () => {
    return character.accent.charAt(0).toUpperCase() + character.accent.slice(1);
  };
  
  // Get emotion icon
  const getEmotionIcon = () => {
    switch (character.base_emotion) {
      case 'happy':
        return <FontAwesome5 name="smile" size={14} color="#4CAF50" />;
      case 'sad':
        return <FontAwesome5 name="frown" size={14} color="#607D8B" />;
      case 'angry':
        return <FontAwesome5 name="angry" size={14} color="#F44336" />;
      case 'excited':
        return <FontAwesome5 name="grin-stars" size={14} color="#FF9800" />;
      case 'calm':
        return <FontAwesome5 name="meh" size={14} color="#03A9F4" />;
      case 'fearful':
        return <FontAwesome5 name="grimace" size={14} color="#9C27B0" />;
      case 'surprised':
        return <FontAwesome5 name="surprise" size={14} color="#FFEB3B" />;
      default:
        return <FontAwesome5 name="meh-blank" size={14} color="#9E9E9E" />;
    }
  };
  
  // Get character image
  const getCharacterImage = () => {
    if (character.character_image_url) {
      return { uri: character.character_image_url };
    }
    
    // Fallback image based on gender
    switch (character.gender) {
      case 'male':
        return require('../../../assets/images/default_male_avatar.png');
      case 'female':
        return require('../../../assets/images/default_female_avatar.png');
      default:
        return require('../../../assets/images/default_neutral_avatar.png');
    }
  };
  
  return (
    <TouchableOpacity 
      style={[styles.container, selected && styles.selectedContainer]}
      onPress={onSelect}
      activeOpacity={0.8}
    >
      <View style={styles.card}>
        <View style={styles.imageContainer}>
          <Image 
            source={getCharacterImage()}
            style={styles.characterImage}
            resizeMode="cover"
          />
          
          {selected && (
            <View style={styles.selectedBadge}>
              <MaterialIcons name="check-circle" size={24} color="#4CAF50" />
            </View>
          )}
        </View>
        
        <View style={styles.contentContainer}>
          <Text style={styles.nameText}>{character.name}</Text>
          <Text style={styles.descriptionText} numberOfLines={2}>{character.description}</Text>
          
          <View style={styles.attributesContainer}>
            <View style={styles.attributeItem}>
              {getGenderIcon()}
              <Text style={styles.attributeText}>{character.gender}</Text>
            </View>
            
            <View style={styles.attributeItem}>
              <FontAwesome5 name="user" size={12} color="#607D8B" />
              <Text style={styles.attributeText}>{getAgeText()}</Text>
            </View>
            
            <View style={styles.attributeItem}>
              <FontAwesome5 name="globe-americas" size={12} color="#FF9800" />
              <Text style={styles.attributeText}>{getAccentDisplay()}</Text>
            </View>
          </View>
          
          <View style={styles.emotionContainer}>
            {getEmotionIcon()}
            <Text style={styles.emotionText}>{character.base_emotion}</Text>
            
            {character.theme_affinity && character.theme_affinity.length > 0 && (
              <View style={styles.themeContainer}>
                <Text style={styles.themeText}>
                  {character.theme_affinity.slice(0, 2).join(', ')}
                  {character.theme_affinity.length > 2 ? '...' : ''}
                </Text>
              </View>
            )}
          </View>
        </View>
        
        {onPlaySample && (
          <TouchableOpacity 
            style={styles.playButton}
            onPress={onPlaySample}
          >
            <FontAwesome5 name="play" size={12} color="white" />
          </TouchableOpacity>
        )}
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 16,
    marginVertical: 8,
  },
  selectedContainer: {
    transform: [{ scale: 1.02 }],
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 12,
    overflow: 'hidden',
    flexDirection: 'row',
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
      },
      android: {
        elevation: 3,
      },
    }),
  },
  imageContainer: {
    width: 80,
    height: 120,
    position: 'relative',
  },
  characterImage: {
    width: '100%',
    height: '100%',
  },
  selectedBadge: {
    position: 'absolute',
    top: 5,
    right: 5,
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 2,
  },
  contentContainer: {
    flex: 1,
    padding: 12,
  },
  nameText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  descriptionText: {
    fontSize: 12,
    color: '#666',
    marginBottom: 8,
  },
  attributesContainer: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  attributeItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 10,
  },
  attributeText: {
    fontSize: 10,
    color: '#757575',
    marginLeft: 4,
    textTransform: 'capitalize',
  },
  emotionContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  emotionText: {
    fontSize: 10,
    color: '#757575',
    marginLeft: 4,
    textTransform: 'capitalize',
  },
  themeContainer: {
    backgroundColor: '#f0f0f0',
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 2,
    marginLeft: 8,
  },
  themeText: {
    fontSize: 9,
    color: '#757575',
  },
  playButton: {
    position: 'absolute',
    bottom: 12,
    right: 12,
    backgroundColor: '#2196F3',
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
});

export default CharacterCard;