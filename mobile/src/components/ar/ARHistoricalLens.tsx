import React, { useRef, useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Image,
  PanResponder,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { BlurView } from 'expo-blur';
import { MaterialIcons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import Slider from '@react-native-community/slider';
import { LinearGradient } from 'expo-linear-gradient';

interface ARHistoricalLensProps {
  currentView: any; // Camera view ref
  historicalImageUrl: string;
  year: number;
  title: string;
  description?: string;
  onClose: () => void;
  onMoreInfo?: () => void;
}

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

const ARHistoricalLens: React.FC<ARHistoricalLensProps> = ({
  currentView,
  historicalImageUrl,
  year,
  title,
  description,
  onClose,
  onMoreInfo,
}) => {
  const [blendValue, setBlendValue] = useState(0.5);
  const [isLoading, setIsLoading] = useState(true);
  const [showInfo, setShowInfo] = useState(true);
  
  // Animation values
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(50)).current;
  const infoFadeAnim = useRef(new Animated.Value(1)).current;
  const sepiaIntensity = useRef(new Animated.Value(0.5)).current;

  // Pan responder for swipe gestures
  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: (evt, gestureState) => {
        return Math.abs(gestureState.dx) > 5;
      },
      onPanResponderMove: (evt, gestureState) => {
        // Update blend value based on horizontal swipe
        const newBlend = Math.max(0, Math.min(1, 0.5 + gestureState.dx / SCREEN_WIDTH));
        setBlendValue(newBlend);
        
        // Update sepia intensity based on blend
        Animated.timing(sepiaIntensity, {
          toValue: newBlend,
          duration: 0,
          useNativeDriver: false,
        }).start();
      },
      onPanResponderRelease: () => {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      },
    })
  ).current;

  // Entrance animation
  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true,
      }),
      Animated.spring(slideAnim, {
        toValue: 0,
        friction: 8,
        tension: 40,
        useNativeDriver: true,
      }),
    ]).start();
  }, []);

  // Auto-hide info after 5 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      Animated.timing(infoFadeAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }).start(() => setShowInfo(false));
    }, 5000);

    return () => clearTimeout(timer);
  }, []);

  const handleClose = () => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 50,
        duration: 300,
        useNativeDriver: true,
      }),
    ]).start(() => {
      onClose();
    });
  };

  const toggleInfo = () => {
    const newShowInfo = !showInfo;
    setShowInfo(newShowInfo);
    
    Animated.timing(infoFadeAnim, {
      toValue: newShowInfo ? 1 : 0,
      duration: 300,
      useNativeDriver: true,
    }).start();
  };

  const handleSliderChange = (value: number) => {
    setBlendValue(value);
    Haptics.selectionAsync();
    
    // Update sepia based on blend
    Animated.timing(sepiaIntensity, {
      toValue: value,
      duration: 100,
      useNativeDriver: false,
    }).start();
  };

  return (
    <Animated.View
      style={[
        styles.container,
        {
          opacity: fadeAnim,
        },
      ]}
      {...panResponder.panHandlers}
    >
      {/* Base camera view */}
      <View style={styles.cameraLayer}>
        {currentView}
      </View>

      {/* Historical image overlay */}
      <Animated.View
        style={[
          styles.historicalLayer,
          {
            opacity: blendValue,
          },
        ]}
      >
        {isLoading && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#FFFFFF" />
          </View>
        )}
        
        <Image
          source={{ uri: historicalImageUrl }}
          style={[
            styles.historicalImage,
            {
              // Apply sepia filter effect
              tintColor: `rgba(112, 66, 20, ${sepiaIntensity})`,
            },
          ]}
          onLoadEnd={() => setIsLoading(false)}
          resizeMode="cover"
        />
        
        {/* Vignette effect */}
        <LinearGradient
          colors={['transparent', 'rgba(0, 0, 0, 0.3)', 'rgba(0, 0, 0, 0.5)']}
          locations={[0.3, 0.8, 1]}
          style={styles.vignette}
        />
      </Animated.View>

      {/* Info overlay */}
      <Animated.View
        style={[
          styles.infoOverlay,
          {
            opacity: infoFadeAnim,
            transform: [{ translateY: slideAnim }],
          },
        ]}
      >
        <BlurView intensity={90} style={styles.infoCard}>
          <Text style={styles.yearText}>{year}</Text>
          <Text style={styles.titleText}>{title}</Text>
          {description && (
            <Text style={styles.descriptionText} numberOfLines={2}>
              {description}
            </Text>
          )}
          
          {/* Blend slider */}
          <View style={styles.sliderContainer}>
            <Text style={styles.sliderLabel}>Then</Text>
            <Slider
              style={styles.slider}
              minimumValue={0}
              maximumValue={1}
              value={blendValue}
              onValueChange={handleSliderChange}
              minimumTrackTintColor="#FFFFFF"
              maximumTrackTintColor="rgba(255, 255, 255, 0.3)"
              thumbTintColor="#FFFFFF"
            />
            <Text style={styles.sliderLabel}>Now</Text>
          </View>

          {onMoreInfo && (
            <TouchableOpacity
              style={styles.moreInfoButton}
              onPress={onMoreInfo}
              activeOpacity={0.8}
            >
              <Text style={styles.moreInfoText}>Learn More</Text>
              <MaterialIcons name="arrow-forward" size={16} color="#007AFF" />
            </TouchableOpacity>
          )}
        </BlurView>
      </Animated.View>

      {/* Control buttons */}
      <View style={styles.controls}>
        <TouchableOpacity
          style={styles.controlButton}
          onPress={toggleInfo}
          activeOpacity={0.8}
        >
          <MaterialIcons
            name={showInfo ? 'info' : 'info-outline'}
            size={28}
            color="#FFFFFF"
          />
        </TouchableOpacity>
        
        <TouchableOpacity
          style={styles.controlButton}
          onPress={handleClose}
          activeOpacity={0.8}
        >
          <MaterialIcons name="close" size={28} color="#FFFFFF" />
        </TouchableOpacity>
      </View>

      {/* Swipe hint */}
      <View style={styles.swipeHint}>
        <MaterialIcons name="swipe" size={24} color="#FFFFFF" />
        <Text style={styles.swipeHintText}>Swipe to blend views</Text>
      </View>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'black',
  },
  cameraLayer: {
    ...StyleSheet.absoluteFillObject,
  },
  historicalLayer: {
    ...StyleSheet.absoluteFillObject,
  },
  historicalImage: {
    width: '100%',
    height: '100%',
  },
  vignette: {
    ...StyleSheet.absoluteFillObject,
    pointerEvents: 'none',
  },
  loadingContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  infoOverlay: {
    position: 'absolute',
    bottom: 40,
    left: 20,
    right: 20,
  },
  infoCard: {
    borderRadius: 16,
    padding: 20,
    overflow: 'hidden',
  },
  yearText: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#FFFFFF',
    opacity: 0.9,
    marginBottom: 8,
    textShadowColor: 'rgba(0, 0, 0, 0.75)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 4,
  },
  titleText: {
    fontSize: 24,
    fontWeight: '600',
    color: '#FFFFFF',
    marginBottom: 8,
    textShadowColor: 'rgba(0, 0, 0, 0.75)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 3,
  },
  descriptionText: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.9)',
    marginBottom: 16,
    lineHeight: 22,
  },
  sliderContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    marginBottom: 16,
  },
  slider: {
    flex: 1,
    height: 40,
    marginHorizontal: 12,
  },
  sliderLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  moreInfoButton: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
  },
  moreInfoText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
    marginRight: 4,
  },
  controls: {
    position: 'absolute',
    top: 50,
    right: 20,
    flexDirection: 'column',
    gap: 12,
  },
  controlButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  swipeHint: {
    position: 'absolute',
    top: '50%',
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  swipeHintText: {
    color: '#FFFFFF',
    fontSize: 14,
    marginLeft: 8,
  },
});

export default ARHistoricalLens;