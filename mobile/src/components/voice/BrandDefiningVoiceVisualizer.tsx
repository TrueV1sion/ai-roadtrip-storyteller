import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import {
  View,
  StyleSheet,
  Dimensions,
  TouchableWithoutFeedback,
  Platform,
} from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withTiming,
  interpolate,
  Extrapolate,
  runOnJS,
  useAnimatedGestureHandler,
  withSequence,
  withRepeat,
  Easing,
  useDerivedValue,
  cancelAnimation,
} from 'react-native-reanimated';
import {
  Canvas,
  Circle,
  LinearGradient,
  vec,
  Group,
  Paint,
  Blur,
  useValue,
  useComputedValue,
  Path,
  Skia,
  useClockValue,
  useValueEffect,
  BlendMode,
} from '@shopify/react-native-skia';
import {
  GestureHandlerRootView,
  PanGestureHandler,
  TapGestureHandler,
  State,
} from 'react-native-gesture-handler';
import { Audio } from 'expo-av';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// FAANG-level type definitions
interface Particle {
  id: string;
  x: Animated.SharedValue<number>;
  y: Animated.SharedValue<number>;
  vx: Animated.SharedValue<number>;
  vy: Animated.SharedValue<number>;
  size: Animated.SharedValue<number>;
  opacity: Animated.SharedValue<number>;
  color: string;
  lifespan: number;
  birthTime: number;
  behavior: ParticleBehavior;
}

interface ParticleBehavior {
  type: 'orbit' | 'explode' | 'flow' | 'attract' | 'wave' | 'spiral';
  strength: number;
  frequency: number;
}

interface PersonalityConfig {
  name: string;
  primaryColors: string[];
  secondaryColors: string[];
  particleBehavior: ParticleBehavior;
  particleCount: number;
  glowIntensity: number;
  animationStyle: 'playful' | 'flowing' | 'majestic' | 'futuristic' | 'mysterious';
}

interface EmotionState {
  primary: 'joy' | 'excitement' | 'calm' | 'mystery' | 'wonder';
  intensity: number;
  confidence: number;
}

interface AudioFeatures {
  amplitude: number;
  frequency: number;
  tempo: number;
  spectralCentroid: number;
  zeroCrossingRate: number;
}

interface BrandDefiningVoiceVisualizerProps {
  isRecording: boolean;
  isPlaying: boolean;
  personality: string;
  onInteraction?: (gesture: string) => void;
  audioData?: Float32Array;
  emotion?: EmotionState;
  showProgress?: boolean;
  teamUpdates?: string[];
}

// Personality configurations with brand-defining characteristics
const PERSONALITY_CONFIGS: Record<string, PersonalityConfig> = {
  mickey: {
    name: 'Mickey Mouse',
    primaryColors: ['#FF0000', '#FFD700', '#1E90FF', '#FF69B4'],
    secondaryColors: ['#FFA500', '#9370DB', '#00CED1', '#FFB6C1'],
    particleBehavior: { type: 'spiral', strength: 0.8, frequency: 2.5 },
    particleCount: 150,
    glowIntensity: 0.9,
    animationStyle: 'playful',
  },
  surfer: {
    name: 'California Surfer',
    primaryColors: ['#00CED1', '#4682B4', '#F0E68C', '#48D1CC'],
    secondaryColors: ['#5F9EA0', '#FFA500', '#87CEEB', '#FFE4B5'],
    particleBehavior: { type: 'wave', strength: 0.6, frequency: 1.2 },
    particleCount: 100,
    glowIntensity: 0.7,
    animationStyle: 'flowing',
  },
  mountain: {
    name: 'Mountain Guide',
    primaryColors: ['#FFFFFF', '#87CEEB', '#2F4F4F', '#F0FFFF'],
    secondaryColors: ['#B0C4DE', '#696969', '#E0FFFF', '#4682B4'],
    particleBehavior: { type: 'flow', strength: 0.4, frequency: 0.8 },
    particleCount: 120,
    glowIntensity: 0.6,
    animationStyle: 'majestic',
  },
  scifi: {
    name: 'Sci-Fi Explorer',
    primaryColors: ['#00FFFF', '#FF00FF', '#7FFF00', '#FF1493'],
    secondaryColors: ['#8A2BE2', '#00FF7F', '#FF4500', '#9400D3'],
    particleBehavior: { type: 'orbit', strength: 1.0, frequency: 3.0 },
    particleCount: 200,
    glowIntensity: 1.0,
    animationStyle: 'futuristic',
  },
  mystic: {
    name: 'Mystic Storyteller',
    primaryColors: ['#9370DB', '#4B0082', '#8B008B', '#6A0DAD'],
    secondaryColors: ['#9932CC', '#8A2BE2', '#7B68EE', '#6495ED'],
    particleBehavior: { type: 'attract', strength: 0.7, frequency: 1.5 },
    particleCount: 130,
    glowIntensity: 0.8,
    animationStyle: 'mysterious',
  },
};

// Brand-defining signature animations
const SIGNATURE_ANIMATIONS = {
  appLaunch: 'cosmicBloom',
  voiceStart: 'personalityAwakening',
  storyClimax: 'narrativeExplosion',
  routeChange: 'dimensionalShift',
  emotionPeak: 'emotionalResonance',
};

export const BrandDefiningVoiceVisualizer: React.FC<BrandDefiningVoiceVisualizerProps> = ({
  isRecording,
  isPlaying,
  personality = 'mickey',
  onInteraction,
  audioData,
  emotion,
  showProgress,
  teamUpdates = [],
}) => {
  const canvasRef = useRef(null);
  const clock = useClockValue();
  const config = PERSONALITY_CONFIGS[personality] || PERSONALITY_CONFIGS.mickey;
  
  // Core animation values
  const centerX = useSharedValue(SCREEN_WIDTH / 2);
  const centerY = useSharedValue(SCREEN_HEIGHT / 3);
  const globalScale = useSharedValue(1);
  const rotationAngle = useSharedValue(0);
  const pulsePhase = useSharedValue(0);
  
  // Particle system state
  const [particles, setParticles] = useState<Particle[]>([]);
  const particlePool = useRef<Particle[]>([]);
  
  // Audio analysis values
  const audioAmplitude = useSharedValue(0);
  const audioFrequency = useSharedValue(440);
  const audioTempo = useSharedValue(120);
  
  // Emotion-driven values
  const emotionIntensity = useSharedValue(emotion?.intensity || 0.5);
  const emotionColor = useSharedValue(0);
  
  // Initialize particle system
  useEffect(() => {
    const initialParticles: Particle[] = [];
    
    for (let i = 0; i < config.particleCount; i++) {
      const particle: Particle = {
        id: `particle-${i}-${Date.now()}`,
        x: useSharedValue(centerX.value + (Math.random() - 0.5) * 100),
        y: useSharedValue(centerY.value + (Math.random() - 0.5) * 100),
        vx: useSharedValue((Math.random() - 0.5) * 2),
        vy: useSharedValue((Math.random() - 0.5) * 2),
        size: useSharedValue(Math.random() * 4 + 2),
        opacity: useSharedValue(Math.random() * 0.8 + 0.2),
        color: config.primaryColors[Math.floor(Math.random() * config.primaryColors.length)],
        lifespan: 3000 + Math.random() * 2000,
        birthTime: Date.now(),
        behavior: { ...config.particleBehavior },
      };
      
      initialParticles.push(particle);
    }
    
    setParticles(initialParticles);
    
    return () => {
      // Cleanup animations
      initialParticles.forEach(particle => {
        cancelAnimation(particle.x);
        cancelAnimation(particle.y);
        cancelAnimation(particle.vx);
        cancelAnimation(particle.vy);
        cancelAnimation(particle.size);
        cancelAnimation(particle.opacity);
      });
    };
  }, [personality]);
  
  // Signature animation: Cosmic Bloom (app launch)
  const performCosmicBloom = useCallback(() => {
    'worklet';
    
    particles.forEach((particle, index) => {
      const delay = index * 10;
      const angle = (index / particles.length) * Math.PI * 2;
      const distance = 200 + Math.random() * 100;
      
      particle.x.value = withDelay(
        delay,
        withSpring(centerX.value + Math.cos(angle) * distance, {
          damping: 15,
          stiffness: 80,
        })
      );
      
      particle.y.value = withDelay(
        delay,
        withSpring(centerY.value + Math.sin(angle) * distance, {
          damping: 15,
          stiffness: 80,
        })
      );
      
      particle.size.value = withDelay(
        delay,
        withSequence(
          withTiming(8, { duration: 300 }),
          withTiming(4, { duration: 700 })
        )
      );
      
      particle.opacity.value = withDelay(
        delay,
        withSequence(
          withTiming(1, { duration: 300 }),
          withTiming(0.6, { duration: 700 })
        )
      );
    });
    
    globalScale.value = withSequence(
      withTiming(1.5, { duration: 300, easing: Easing.out(Easing.cubic) }),
      withSpring(1, { damping: 12, stiffness: 100 })
    );
  }, [particles, centerX, centerY, globalScale]);
  
  // Signature animation: Personality Awakening (voice start)
  const performPersonalityAwakening = useCallback(() => {
    'worklet';
    
    const behaviorPatterns = {
      spiral: (particle: Particle, t: number) => {
        const radius = 100 + t * 50;
        const angle = t * Math.PI * 4;
        particle.x.value = withTiming(centerX.value + Math.cos(angle) * radius, { duration: 1000 });
        particle.y.value = withTiming(centerY.value + Math.sin(angle) * radius, { duration: 1000 });
      },
      wave: (particle: Particle, t: number) => {
        const waveHeight = Math.sin(t * Math.PI * 2) * 50;
        particle.x.value = withTiming(particle.x.value + (Math.random() - 0.5) * 100, { duration: 800 });
        particle.y.value = withTiming(centerY.value + waveHeight, { duration: 800 });
      },
      orbit: (particle: Particle, t: number) => {
        const orbitRadius = 80 + Math.random() * 40;
        const orbitSpeed = 0.5 + Math.random() * 0.5;
        const angle = t * Math.PI * 2 * orbitSpeed;
        particle.x.value = withTiming(centerX.value + Math.cos(angle) * orbitRadius, { duration: 1200 });
        particle.y.value = withTiming(centerY.value + Math.sin(angle) * orbitRadius, { duration: 1200 });
      },
    };
    
    particles.forEach((particle, index) => {
      const t = index / particles.length;
      const pattern = behaviorPatterns[config.particleBehavior.type];
      if (pattern) {
        pattern(particle, t);
      }
      
      // Personality-specific color transitions
      const targetColor = config.primaryColors[index % config.primaryColors.length];
      particle.color = targetColor;
      
      particle.opacity.value = withTiming(0.9, { duration: 800 });
      particle.size.value = withSpring(5 + Math.random() * 3, { damping: 10 });
    });
    
    pulsePhase.value = withRepeat(
      withTiming(1, { duration: 1000, easing: Easing.inOut(Easing.sin) }),
      -1,
      true
    );
  }, [particles, config, centerX, centerY, pulsePhase]);
  
  // Audio-reactive particle behavior
  const updateParticlesWithAudio = useCallback((features: AudioFeatures) => {
    'worklet';
    
    const { amplitude, frequency, tempo, spectralCentroid } = features;
    
    particles.forEach((particle, index) => {
      // Frequency-based movement
      const freqInfluence = interpolate(
        frequency,
        [100, 1000],
        [0.5, 2.0],
        Extrapolate.CLAMP
      );
      
      // Amplitude-based sizing
      const ampInfluence = interpolate(
        amplitude,
        [0, 1],
        [0.8, 1.5],
        Extrapolate.CLAMP
      );
      
      // Update particle physics based on audio
      particle.vx.value = withSpring(
        (Math.random() - 0.5) * freqInfluence * 5,
        { damping: 8 }
      );
      
      particle.vy.value = withSpring(
        (Math.random() - 0.5) * freqInfluence * 5 - amplitude * 2,
        { damping: 8 }
      );
      
      particle.size.value = withSpring(
        (4 + Math.random() * 4) * ampInfluence,
        { damping: 10 }
      );
      
      // Spectral centroid affects opacity
      const opacityTarget = interpolate(
        spectralCentroid,
        [0, 8000],
        [0.4, 1.0],
        Extrapolate.CLAMP
      );
      
      particle.opacity.value = withTiming(opacityTarget, { duration: 100 });
    });
    
    // Global effects based on tempo
    const tempoInfluence = tempo / 120; // Normalized to 120 BPM
    rotationAngle.value = withRepeat(
      withTiming(Math.PI * 2, { 
        duration: 60000 / tempo, // One rotation per beat
        easing: Easing.linear 
      }),
      -1
    );
  }, [particles, rotationAngle]);
  
  // Emotion-driven color and behavior modulation
  const applyEmotionEffects = useCallback((emotionState: EmotionState) => {
    'worklet';
    
    const emotionColors = {
      joy: ['#FFD700', '#FFA500', '#FF69B4', '#FFFF00'],
      excitement: ['#FF0000', '#FF4500', '#DC143C', '#FF1493'],
      calm: ['#87CEEB', '#4682B4', '#5F9EA0', '#00CED1'],
      mystery: ['#9370DB', '#8A2BE2', '#4B0082', '#6A0DAD'],
      wonder: ['#FFB6C1', '#DDA0DD', '#F0E68C', '#FFDEAD'],
    };
    
    const colors = emotionColors[emotionState.primary] || emotionColors.joy;
    const intensity = emotionState.intensity;
    
    particles.forEach((particle, index) => {
      // Emotion-based color shifting
      if (Math.random() < intensity) {
        particle.color = colors[index % colors.length];
      }
      
      // Emotion-based movement patterns
      const emotionMovement = {
        joy: () => {
          particle.vy.value = withSpring(-Math.abs(particle.vy.value) * 1.5, { damping: 5 });
        },
        excitement: () => {
          const burst = (Math.random() - 0.5) * 10 * intensity;
          particle.vx.value = withSpring(particle.vx.value + burst, { damping: 3 });
          particle.vy.value = withSpring(particle.vy.value + burst, { damping: 3 });
        },
        calm: () => {
          particle.vx.value = withTiming(particle.vx.value * 0.5, { duration: 2000 });
          particle.vy.value = withTiming(particle.vy.value * 0.5, { duration: 2000 });
        },
        mystery: () => {
          const spiral = index * 0.1;
          particle.x.value = withTiming(
            centerX.value + Math.cos(clock.value * 0.001 + spiral) * 100,
            { duration: 3000 }
          );
          particle.y.value = withTiming(
            centerY.value + Math.sin(clock.value * 0.001 + spiral) * 100,
            { duration: 3000 }
          );
        },
        wonder: () => {
          particle.size.value = withRepeat(
            withSequence(
              withTiming(8, { duration: 1000 }),
              withTiming(3, { duration: 1000 })
            ),
            -1,
            true
          );
        },
      };
      
      const movement = emotionMovement[emotionState.primary];
      if (movement) movement();
    });
    
    emotionIntensity.value = withTiming(intensity, { duration: 500 });
  }, [particles, emotionIntensity, centerX, centerY, clock]);
  
  // Gesture handlers for interactivity
  const panGestureHandler = useAnimatedGestureHandler({
    onStart: (event) => {
      'worklet';
      runOnJS(onInteraction)?.('pan-start');
    },
    onActive: (event) => {
      'worklet';
      centerX.value = event.x;
      centerY.value = event.y;
      
      // Particles follow touch with spring physics
      particles.forEach((particle, index) => {
        const delay = index * 2;
        particle.x.value = withDelay(
          delay,
          withSpring(event.x + (Math.random() - 0.5) * 50, {
            damping: 8,
            stiffness: 150,
          })
        );
        particle.y.value = withDelay(
          delay,
          withSpring(event.y + (Math.random() - 0.5) * 50, {
            damping: 8,
            stiffness: 150,
          })
        );
      });
    },
    onEnd: () => {
      'worklet';
      runOnJS(onInteraction)?.('pan-end');
      
      // Return to center with personality-specific animation
      centerX.value = withSpring(SCREEN_WIDTH / 2, { damping: 10 });
      centerY.value = withSpring(SCREEN_HEIGHT / 3, { damping: 10 });
    },
  });
  
  const tapGestureHandler = useAnimatedGestureHandler({
    onEnd: (event) => {
      'worklet';
      runOnJS(onInteraction)?.('tap');
      
      // Create explosion effect at tap location
      particles.forEach((particle) => {
        const dx = event.x - particle.x.value;
        const dy = event.y - particle.y.value;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const force = 500 / (distance + 1);
        
        particle.vx.value = withSpring(
          particle.vx.value - (dx / distance) * force,
          { damping: 5 }
        );
        particle.vy.value = withSpring(
          particle.vy.value - (dy / distance) * force,
          { damping: 5 }
        );
      });
      
      globalScale.value = withSequence(
        withTiming(1.2, { duration: 100 }),
        withSpring(1, { damping: 8 })
      );
    },
  });
  
  // Particle physics update loop
  useEffect(() => {
    const updateInterval = setInterval(() => {
      particles.forEach((particle) => {
        'worklet';
        
        // Update position based on velocity
        particle.x.value += particle.vx.value;
        particle.y.value += particle.vy.value;
        
        // Apply behavior-specific forces
        switch (particle.behavior.type) {
          case 'attract':
            const dx = centerX.value - particle.x.value;
            const dy = centerY.value - particle.y.value;
            const distance = Math.sqrt(dx * dx + dy * dy);
            const attraction = particle.behavior.strength * 0.1;
            
            particle.vx.value += (dx / distance) * attraction;
            particle.vy.value += (dy / distance) * attraction;
            break;
            
          case 'orbit':
            const angle = Math.atan2(
              particle.y.value - centerY.value,
              particle.x.value - centerX.value
            );
            const tangentX = -Math.sin(angle);
            const tangentY = Math.cos(angle);
            const orbitForce = particle.behavior.strength * 0.2;
            
            particle.vx.value += tangentX * orbitForce;
            particle.vy.value += tangentY * orbitForce;
            break;
            
          case 'wave':
            const wavePhase = clock.value * 0.001 * particle.behavior.frequency;
            particle.vy.value += Math.sin(wavePhase) * particle.behavior.strength * 0.1;
            break;
        }
        
        // Apply damping
        particle.vx.value *= 0.98;
        particle.vy.value *= 0.98;
        
        // Boundary collision with bounce
        if (particle.x.value < 0 || particle.x.value > SCREEN_WIDTH) {
          particle.vx.value *= -0.8;
          particle.x.value = Math.max(0, Math.min(SCREEN_WIDTH, particle.x.value));
        }
        
        if (particle.y.value < 0 || particle.y.value > SCREEN_HEIGHT) {
          particle.vy.value *= -0.8;
          particle.y.value = Math.max(0, Math.min(SCREEN_HEIGHT, particle.y.value));
        }
        
        // Lifecycle management
        const age = Date.now() - particle.birthTime;
        if (age > particle.lifespan) {
          // Respawn particle
          particle.birthTime = Date.now();
          particle.x.value = centerX.value + (Math.random() - 0.5) * 100;
          particle.y.value = centerY.value + (Math.random() - 0.5) * 100;
          particle.vx.value = (Math.random() - 0.5) * 2;
          particle.vy.value = (Math.random() - 0.5) * 2;
          particle.opacity.value = withTiming(0.8, { duration: 500 });
        }
      });
    }, 16); // 60 FPS
    
    return () => clearInterval(updateInterval);
  }, [particles, centerX, centerY, clock]);
  
  // Audio processing effect
  useEffect(() => {
    if (audioData && audioData.length > 0) {
      // Extract audio features
      const amplitude = Math.max(...audioData.map(Math.abs));
      const fft = performFFT(audioData);
      const frequency = getDominantFrequency(fft);
      const spectralCentroid = getSpectralCentroid(fft);
      const zeroCrossingRate = getZeroCrossingRate(audioData);
      const tempo = estimateTempo(audioData);
      
      const features: AudioFeatures = {
        amplitude,
        frequency,
        tempo,
        spectralCentroid,
        zeroCrossingRate,
      };
      
      updateParticlesWithAudio(features);
    }
  }, [audioData, updateParticlesWithAudio]);
  
  // Emotion effect
  useEffect(() => {
    if (emotion) {
      applyEmotionEffects(emotion);
    }
  }, [emotion, applyEmotionEffects]);
  
  // State change animations
  useEffect(() => {
    if (isRecording || isPlaying) {
      performPersonalityAwakening();
    } else {
      // Return to idle state
      pulsePhase.value = withRepeat(
        withTiming(1, { duration: 3000, easing: Easing.inOut(Easing.sin) }),
        -1,
        true
      );
    }
  }, [isRecording, isPlaying, performPersonalityAwakening, pulsePhase]);
  
  // Render the canvas with Skia
  const renderParticles = useMemo(() => {
    return (
      <Canvas style={StyleSheet.absoluteFillObject}>
        {/* Background gradient */}
        <Group>
          <LinearGradient
            start={vec(0, 0)}
            end={vec(SCREEN_WIDTH, SCREEN_HEIGHT)}
            colors={['#0f0f23', '#1a1a2e']}
          />
        </Group>
        
        {/* Glow effect layer */}
        <Group opacity={config.glowIntensity}>
          <Blur blur={20}>
            {particles.map((particle) => (
              <Circle
                key={particle.id}
                cx={particle.x}
                cy={particle.y}
                r={particle.size}
                opacity={particle.opacity}
                color={particle.color}
              />
            ))}
          </Blur>
        </Group>
        
        {/* Main particle layer */}
        <Group>
          {particles.map((particle) => (
            <Circle
              key={`main-${particle.id}`}
              cx={particle.x}
              cy={particle.y}
              r={particle.size}
              opacity={particle.opacity}
              color={particle.color}
              blendMode={BlendMode.Screen}
            />
          ))}
        </Group>
        
        {/* Center orb with personality-specific effects */}
        <Group transform={[{ scale: globalScale }]}>
          <Circle
            cx={centerX}
            cy={centerY}
            r={40}
            opacity={0.8}
          >
            <LinearGradient
              start={vec(centerX.value - 40, centerY.value - 40)}
              end={vec(centerX.value + 40, centerY.value + 40)}
              colors={config.primaryColors.slice(0, 2)}
            />
          </Circle>
          
          <Blur blur={30}>
            <Circle
              cx={centerX}
              cy={centerY}
              r={60}
              opacity={0.4}
              color={config.primaryColors[0]}
            />
          </Blur>
        </Group>
        
        {/* Progress indicator overlay */}
        {showProgress && teamUpdates.length > 0 && (
          <Group>
            {teamUpdates.slice(-3).map((update, index) => (
              <Text
                key={index}
                x={20}
                y={SCREEN_HEIGHT - 100 + index * 25}
                text={update}
                color="rgba(255, 255, 255, 0.6)"
                fontSize={14}
              />
            ))}
          </Group>
        )}
      </Canvas>
    );
  }, [particles, config, centerX, centerY, globalScale, showProgress, teamUpdates]);
  
  return (
    <GestureHandlerRootView style={styles.container}>
      <TapGestureHandler onGestureEvent={tapGestureHandler}>
        <Animated.View style={StyleSheet.absoluteFillObject}>
          <PanGestureHandler onGestureEvent={panGestureHandler}>
            <Animated.View style={StyleSheet.absoluteFillObject}>
              {renderParticles}
            </Animated.View>
          </PanGestureHandler>
        </Animated.View>
      </TapGestureHandler>
    </GestureHandlerRootView>
  );
};

// Helper functions for audio processing
function performFFT(audioData: Float32Array): Float32Array {
  // Simplified FFT implementation (in production, use a proper FFT library)
  const fftSize = 512;
  const fft = new Float32Array(fftSize);
  
  for (let k = 0; k < fftSize; k++) {
    let real = 0;
    let imag = 0;
    
    for (let n = 0; n < audioData.length; n++) {
      const angle = -2 * Math.PI * k * n / audioData.length;
      real += audioData[n] * Math.cos(angle);
      imag += audioData[n] * Math.sin(angle);
    }
    
    fft[k] = Math.sqrt(real * real + imag * imag);
  }
  
  return fft;
}

function getDominantFrequency(fft: Float32Array): number {
  let maxIndex = 0;
  let maxValue = 0;
  
  for (let i = 1; i < fft.length / 2; i++) {
    if (fft[i] > maxValue) {
      maxValue = fft[i];
      maxIndex = i;
    }
  }
  
  // Convert bin to frequency (assuming 44.1kHz sample rate)
  return (maxIndex * 44100) / fft.length;
}

function getSpectralCentroid(fft: Float32Array): number {
  let weightedSum = 0;
  let magnitudeSum = 0;
  
  for (let i = 0; i < fft.length / 2; i++) {
    const frequency = (i * 44100) / fft.length;
    weightedSum += frequency * fft[i];
    magnitudeSum += fft[i];
  }
  
  return magnitudeSum > 0 ? weightedSum / magnitudeSum : 0;
}

function getZeroCrossingRate(audioData: Float32Array): number {
  let crossings = 0;
  
  for (let i = 1; i < audioData.length; i++) {
    if ((audioData[i] >= 0) !== (audioData[i - 1] >= 0)) {
      crossings++;
    }
  }
  
  return crossings / audioData.length;
}

function estimateTempo(audioData: Float32Array): number {
  // Simplified tempo estimation (in production, use a proper beat detection algorithm)
  // This is a placeholder that returns a reasonable default
  return 120; // BPM
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f0f23',
  },
});

export default BrandDefiningVoiceVisualizer;