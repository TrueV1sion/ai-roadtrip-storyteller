import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { theme } from '../../theme';
import { Card } from '../Card';

interface EntertainmentOption {
  id: string;
  title: string;
  subtitle: string;
  duration: string;
  icon: string;
  color?: string;
}

interface PassengerEntertainmentCardProps {
  option: EntertainmentOption;
  onPress: () => void;
  isActive?: boolean;
}

export const PassengerEntertainmentCard: React.FC<PassengerEntertainmentCardProps> = ({
  option,
  onPress,
  isActive = false,
}) => {
  const scaleAnim = React.useRef(new Animated.Value(1)).current;

  React.useEffect(() => {
    if (isActive) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(scaleAnim, {
            toValue: 1.05,
            duration: 1000,
            useNativeDriver: true,
          }),
          Animated.timing(scaleAnim, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: true,
          }),
        ])
      ).start();
    } else {
      scaleAnim.setValue(1);
    }
  }, [isActive]);

  const getIcon = () => {
    const iconProps = { 
      size: 48, 
      color: option.color || theme.colors.primary 
    };
    
    switch (option.icon) {
      case 'game':
        return <MaterialCommunityIcons name="gamepad-variant" {...iconProps} />;
      case 'story':
        return <Ionicons name="book" {...iconProps} />;
      case 'music':
        return <Ionicons name="musical-notes" {...iconProps} />;
      case 'trivia':
        return <MaterialCommunityIcons name="head-question" {...iconProps} />;
      case 'facts':
        return <Ionicons name="information-circle" {...iconProps} />;
      default:
        return <Ionicons name="star" {...iconProps} />;
    }
  };

  return (
    <Animated.View style={[{ transform: [{ scale: scaleAnim }] }]}>
      <Card style={[styles.card, isActive && styles.activeCard]}>
        <TouchableOpacity style={styles.content} onPress={onPress} activeOpacity={0.8}>
          <View style={styles.iconContainer}>
            {getIcon()}
          </View>
          
          <View style={styles.textContainer}>
            <Text style={styles.title}>{option.title}</Text>
            <Text style={styles.subtitle}>{option.subtitle}</Text>
            <View style={styles.durationContainer}>
              <Ionicons name="time-outline" size={14} color={theme.colors.textSecondary} />
              <Text style={styles.duration}>{option.duration}</Text>
            </View>
          </View>
          
          <View style={styles.playButton}>
            <Ionicons 
              name="play-circle" 
              size={50} 
              color={isActive ? theme.colors.success : theme.colors.primary} 
            />
          </View>
        </TouchableOpacity>
      </Card>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  card: {
    marginBottom: theme.spacing.md,
    overflow: 'hidden',
  },
  activeCard: {
    borderColor: theme.colors.primary,
    borderWidth: 2,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: theme.spacing.lg,
  },
  iconContainer: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: theme.colors.backgroundSecondary,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: theme.spacing.md,
  },
  textContainer: {
    flex: 1,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  subtitle: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.xs,
  },
  durationContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  duration: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginLeft: theme.spacing.xs,
  },
  playButton: {
    marginLeft: theme.spacing.md,
  },
});