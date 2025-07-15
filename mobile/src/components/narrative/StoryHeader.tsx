import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Platform
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons, FontAwesome5 } from '@expo/vector-icons';

interface StoryHeaderProps {
  title: string;
  progress: number;
  onMenuPress?: () => void;
  onInfoPress?: () => void;
  theme?: string;
}

const StoryHeader: React.FC<StoryHeaderProps> = ({
  title,
  progress,
  onMenuPress,
  onInfoPress,
  theme = 'adventure'
}) => {
  const navigation = useNavigation();
  
  // Get theme color based on story theme
  const getThemeColor = () => {
    switch (theme.toLowerCase()) {
      case 'historical':
        return '#8C6D46';
      case 'mystery':
        return '#673AB7';
      case 'adventure':
        return '#FF9800';
      case 'nature':
        return '#4CAF50';
      case 'cultural':
        return '#E91E63';
      default:
        return '#2196F3';
    }
  };
  
  const themeColor = getThemeColor();
  
  const handleBackPress = () => {
    navigation.goBack();
  };
  
  return (
    <View style={styles.container}>
      <TouchableOpacity 
        style={styles.backButton}
        onPress={handleBackPress}
      >
        <Ionicons name="arrow-back" size={24} color="#333" />
      </TouchableOpacity>
      
      <View style={styles.titleContainer}>
        <Text style={styles.title} numberOfLines={1} ellipsizeMode="tail">
          {title}
        </Text>
      </View>
      
      <View style={styles.progressContainer}>
        <View style={styles.progressBarBackground}>
          <View 
            style={[
              styles.progressBarFill,
              { width: `${progress}%`, backgroundColor: themeColor }
            ]} 
          />
        </View>
        <Text style={styles.progressText}>{Math.round(progress)}%</Text>
      </View>
      
      <View style={styles.actionButtons}>
        {onInfoPress && (
          <TouchableOpacity 
            style={styles.actionButton}
            onPress={onInfoPress}
          >
            <FontAwesome5 name="info-circle" size={20} color="#333" />
          </TouchableOpacity>
        )}
        
        {onMenuPress && (
          <TouchableOpacity 
            style={styles.actionButton}
            onPress={onMenuPress}
          >
            <Ionicons name="menu" size={24} color="#333" />
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    height: 80,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    flexDirection: 'column',
    paddingTop: Platform.OS === 'ios' ? 40 : 10,
    paddingBottom: 5,
    paddingHorizontal: 10,
  },
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 5,
  },
  backButton: {
    position: 'absolute',
    left: 10,
    top: Platform.OS === 'ios' ? 40 : 15,
    zIndex: 10,
  },
  titleContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: Platform.OS === 'ios' ? 0 : 5,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    textAlign: 'center',
    maxWidth: '70%',
  },
  progressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 5,
  },
  progressBarBackground: {
    height: 6,
    backgroundColor: '#e0e0e0',
    borderRadius: 3,
    flex: 1,
    overflow: 'hidden',
  },
  progressBarFill: {
    height: 6,
    borderRadius: 3,
  },
  progressText: {
    fontSize: 12,
    fontWeight: 'bold',
    marginLeft: 8,
    minWidth: 35,
  },
  actionButtons: {
    position: 'absolute',
    right: 10,
    top: Platform.OS === 'ios' ? 40 : 15,
    flexDirection: 'row',
  },
  actionButton: {
    marginLeft: 15,
  },
});

export default StoryHeader;