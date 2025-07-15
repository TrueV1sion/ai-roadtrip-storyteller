import React from 'react';
import { 
  TouchableOpacity, 
  Text, 
  StyleSheet, 
  ViewStyle, 
  TextStyle,
  Animated,
  Platform
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { FontAwesome5 } from '@expo/vector-icons';

interface ARButtonProps {
  mode?: 'historical' | 'navigation' | 'nature' | 'all';
  style?: ViewStyle;
  textStyle?: TextStyle;
  iconSize?: number;
  buttonText?: string;
  pulsing?: boolean;
  disabled?: boolean;
  onPress?: () => void;
}

const ARButton: React.FC<ARButtonProps> = ({
  mode = 'all',
  style,
  textStyle,
  iconSize = 18,
  buttonText = 'AR View',
  pulsing = false,
  disabled = false,
  onPress
}) => {
  const navigation = useNavigation();
  const pulseAnim = React.useRef(new Animated.Value(1)).current;
  
  React.useEffect(() => {
    if (pulsing) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.1,
            duration: 800,
            useNativeDriver: true
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true
          })
        ])
      ).start();
    }
  }, [pulsing, pulseAnim]);
  
  const handlePress = () => {
    if (disabled) return;
    
    if (onPress) {
      onPress();
    } else {
      // @ts-ignore: navigation type
      navigation.navigate('ARScreen', { mode });
    }
  };
  
  // Choose icon based on mode
  const getIcon = () => {
    switch (mode) {
      case 'historical':
        return <FontAwesome5 name="landmark" size={iconSize} color="white" />;
      case 'navigation':
        return <FontAwesome5 name="directions" size={iconSize} color="white" />;
      case 'nature':
        return <FontAwesome5 name="tree" size={iconSize} color="white" />;
      case 'all':
      default:
        return <FontAwesome5 name="vr-cardboard" size={iconSize} color="white" />;
    }
  };
  
  // Choose button color based on mode
  const getButtonStyle = () => {
    switch (mode) {
      case 'historical':
        return { backgroundColor: '#8C6D46' };
      case 'navigation':
        return { backgroundColor: '#4A90E2' };
      case 'nature':
        return { backgroundColor: '#4CAF50' };
      case 'all':
      default:
        return { backgroundColor: '#9C27B0' };
    }
  };
  
  return (
    <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
      <TouchableOpacity
        style={[
          styles.button,
          getButtonStyle(),
          disabled && styles.disabledButton,
          style
        ]}
        onPress={handlePress}
        disabled={disabled}
        activeOpacity={0.7}
      >
        {getIcon()}
        <Text style={[styles.buttonText, textStyle]}>
          {buttonText}
        </Text>
      </TouchableOpacity>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    paddingHorizontal: 15,
    borderRadius: 20,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    marginLeft: 8,
    fontSize: 14,
  },
  disabledButton: {
    opacity: 0.5,
  },
});

export default ARButton;