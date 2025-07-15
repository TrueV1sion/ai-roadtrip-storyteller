import React, { useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Image,
  Platform
} from 'react-native';
import { RenderableARElement } from '../../types/ar';
import { FontAwesome5, MaterialCommunityIcons } from '@expo/vector-icons';

interface ARElementProps {
  element: RenderableARElement;
  onPress: () => void;
}

const ARElement: React.FC<ARElementProps> = ({ element, onPress }) => {
  // Animation values
  const scale = useRef(new Animated.Value(0)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  
  useEffect(() => {
    // Entrance animation based on element's animation type
    const animationType = element.appearance.animation || 'fade_in';
    
    switch (animationType) {
      case 'fade_in':
        Animated.timing(opacity, {
          toValue: element.opacity,
          duration: 500,
          useNativeDriver: true
        }).start();
        Animated.timing(scale, {
          toValue: element.scale,
          duration: 500,
          useNativeDriver: true
        }).start();
        break;
        
      case 'bounce':
        Animated.sequence([
          Animated.timing(opacity, {
            toValue: element.opacity,
            duration: 300,
            useNativeDriver: true
          }),
          Animated.spring(scale, {
            toValue: element.scale,
            friction: 4,
            tension: 40,
            useNativeDriver: true
          })
        ]).start();
        break;
        
      case 'grow':
        Animated.parallel([
          Animated.timing(opacity, {
            toValue: element.opacity,
            duration: 400,
            useNativeDriver: true
          }),
          Animated.sequence([
            Animated.timing(scale, {
              toValue: element.scale * 1.2,
              duration: 300,
              useNativeDriver: true
            }),
            Animated.timing(scale, {
              toValue: element.scale,
              duration: 200,
              useNativeDriver: true
            })
          ])
        ]).start();
        break;
        
      default:
        Animated.parallel([
          Animated.timing(opacity, {
            toValue: element.opacity,
            duration: 300,
            useNativeDriver: true
          }),
          Animated.timing(scale, {
            toValue: element.scale,
            duration: 300,
            useNativeDriver: true
          })
        ]).start();
    }
    
    // Pulse effect for navigation elements
    if (element.appearance.pulse_effect) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(scale, {
            toValue: element.scale * 1.1,
            duration: 800,
            useNativeDriver: true
          }),
          Animated.timing(scale, {
            toValue: element.scale * 0.95,
            duration: 800,
            useNativeDriver: true
          })
        ])
      ).start();
    }
  }, [element]);
  
  // Choose icon based on element type
  const getIcon = () => {
    const iconName = element.appearance.icon || 'map-marker';
    const color = element.appearance.color || '#FFFFFF';
    
    switch (iconName) {
      case 'historical_marker':
        return <FontAwesome5 name="landmark" size={24} color={color} />;
      case 'navigation_arrow':
        return <FontAwesome5 name="directions" size={24} color={color} />;
      case 'nature_marker':
        return <MaterialCommunityIcons name="pine-tree" size={24} color={color} />;
      default:
        return <FontAwesome5 name="map-marker-alt" size={24} color={color} />;
    }
  };
  
  // Position styles based on element's view coordinates
  const positionStyle = {
    left: `${element.view_x * 100}%`,
    top: `${element.view_y * 100}%`,
    zIndex: Math.round((1 - element.view_z) * 1000)
  };
  
  // Get distance display
  const getDistanceDisplay = () => {
    if (!element.appearance.show_distance) return null;
    
    // Find distance from source_point if available
    const distance = element.source_point_id?.includes('nav_') 
      ? parseFloat(element.appearance.distance || '0')
      : 0;
      
    if (!distance) return null;
    
    let distanceText = '';
    if (distance < 1000) {
      distanceText = `${Math.round(distance)}m`;
    } else {
      distanceText = `${(distance / 1000).toFixed(1)}km`;
    }
    
    return (
      <View style={styles.distanceContainer}>
        <Text style={styles.distanceText}>{distanceText}</Text>
      </View>
    );
  };
  
  return (
    <Animated.View 
      style={[
        styles.container, 
        positionStyle,
        { transform: [{ scale }], opacity }
      ]}
    >
      <TouchableOpacity
        activeOpacity={0.8}
        style={[
          styles.elementContainer,
          { backgroundColor: element.appearance.color + '88' } // Add transparency
        ]}
        onPress={onPress}
      >
        <View style={styles.iconContainer}>
          {getIcon()}
        </View>
        
        {element.appearance.show_labels !== false && (
          <Text 
            style={[
              styles.label,
              element.appearance.text_style === 'serif' && styles.serifText
            ]}
            numberOfLines={2}
          >
            {element.title || ''}
          </Text>
        )}
        
        {element.appearance.show_year && (
          <Text style={styles.yearText}>
            {element.appearance.year || ''}
          </Text>
        )}
        
        {getDistanceDisplay()}
      </TouchableOpacity>
      
      {/* Direction arrow for navigation elements */}
      {element.appearance.show_arrows && element.appearance.arrow_type && (
        <View style={styles.arrowContainer}>
          <FontAwesome5 
            name={element.appearance.arrow_type === 'right' ? 'arrow-right' : 
                 element.appearance.arrow_type === 'left' ? 'arrow-left' : 'arrow-up'} 
            size={16} 
            color={element.appearance.color} 
          />
        </View>
      )}
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    width: 'auto',
    minWidth: 100,
    alignItems: 'center',
    justifyContent: 'center',
    transform: [{ translateX: -50 }, { translateY: -50 }]
  },
  elementContainer: {
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.5)',
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'column',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 3,
    },
    shadowOpacity: 0.29,
    shadowRadius: 4.65,
    elevation: 7,
  },
  iconContainer: {
    marginBottom: 5,
  },
  label: {
    color: 'white',
    fontSize: 14,
    fontWeight: 'bold',
    textAlign: 'center',
    textShadowColor: 'rgba(0, 0, 0, 0.75)',
    textShadowOffset: { width: -1, height: 1 },
    textShadowRadius: 10,
    maxWidth: 150,
  },
  serifText: {
    fontFamily: Platform.OS === 'ios' ? 'Georgia' : 'serif',
  },
  yearText: {
    color: 'white',
    fontSize: 12,
    opacity: 0.9,
    marginTop: 3,
    textShadowColor: 'rgba(0, 0, 0, 0.75)',
    textShadowOffset: { width: -1, height: 1 },
    textShadowRadius: 10,
  },
  distanceContainer: {
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    marginTop: 5,
  },
  distanceText: {
    color: 'white',
    fontSize: 12,
  },
  arrowContainer: {
    position: 'absolute',
    bottom: -20,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    padding: 5,
    borderRadius: 15,
  },
});

export default ARElement;