import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import {
  View,
  StyleSheet,
  Dimensions,
  Platform,
} from 'react-native';
import {
  Canvas,
  useCanvasRef,
  Circle,
  Path,
  Skia,
  LinearGradient,
  vec,
  Group,
  Box,
  RoundedRect,
  Shadow,
  Blur,
  Paint,
  useValue,
  useComputedValue,
  useClockValue,
  useTouchHandler,
  useValueEffect,
  mix,
  useLoop,
  BlendMode,
  Text,
  useFont,
  matchFont,
} from '@shopify/react-native-skia';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withTiming,
  interpolate,
  Extrapolate,
  withRepeat,
  withSequence,
  Easing,
  useDerivedValue,
  runOnJS,
  useAnimatedGestureHandler,
} from 'react-native-reanimated';
import {
  GestureHandlerRootView,
  PanGestureHandler,
  PinchGestureHandler,
  RotationGestureHandler,
  State,
} from 'react-native-gesture-handler';
import { PersonalityColorSystem } from '../../theme/PersonalityColorSystem';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Type definitions for 3D spatial audio
interface AudioSource3D {
  id: string;
  x: number;
  y: number;
  z: number;
  volume: number;
  frequency: number;
  label: string;
  type: 'voice' | 'music' | 'effect' | 'ambient';
  color: string;
  active: boolean;
}

interface SpatialField {
  dimensions: { width: number; height: number; depth: number };
  sources: AudioSource3D[];
  listenerPosition: { x: number; y: number; z: number };
  listenerRotation: { x: number; y: number; z: number };
  reverbLevel: number;
  acousticProperties: AcousticProperties;
}

interface AcousticProperties {
  absorption: number;
  diffusion: number;
  roomSize: 'small' | 'medium' | 'large' | 'outdoor';
  material: 'concrete' | 'wood' | 'carpet' | 'glass';
}

interface WaveformPath3D {
  path: string;
  depth: number;
  color: string;
  opacity: number;
}

interface Spatial3DAudioVisualizerProps {
  audioSources: AudioSource3D[];
  isActive: boolean;
  personality: string;
  onSourceSelect?: (source: AudioSource3D) => void;
  onPositionChange?: (position: { x: number; y: number; z: number }) => void;
  showGrid?: boolean;
  showLabels?: boolean;
  enableGestures?: boolean;
}

// Constants for 3D projection
const PERSPECTIVE = 800;
const GRID_SIZE = 50;
const MAX_DEPTH = 500;

export const Spatial3DAudioVisualizer: React.FC<Spatial3DAudioVisualizerProps> = ({
  audioSources,
  isActive,
  personality,
  onSourceSelect,
  onPositionChange,
  showGrid = true,
  showLabels = true,
  enableGestures = true,
}) => {
  const canvasRef = useCanvasRef();
  const colorSystem = useMemo(() => new PersonalityColorSystem(personality), [personality]);
  const clock = useClockValue();
  
  // 3D camera controls
  const cameraX = useSharedValue(0);
  const cameraY = useSharedValue(0);
  const cameraZ = useSharedValue(-300);
  const rotationX = useSharedValue(0);
  const rotationY = useSharedValue(0);
  const zoom = useSharedValue(1);
  
  // Animation values
  const pulsePhase = useLoop({ duration: 2000 });
  const wavePhase = useLoop({ duration: 3000 });
  const glowIntensity = useSharedValue(0.8);
  
  // Spatial field state
  const [spatialField, setSpatialField] = useState<SpatialField>({
    dimensions: { width: 800, height: 600, depth: 400 },
    sources: audioSources,
    listenerPosition: { x: 0, y: 0, z: 0 },
    listenerRotation: { x: 0, y: 0, z: 0 },
    reverbLevel: 0.3,
    acousticProperties: {
      absorption: 0.5,
      diffusion: 0.7,
      roomSize: 'medium',
      material: 'wood',
    },
  });
  
  // Font for labels
  const font = useFont(
    Platform.select({
      ios: require('../../assets/fonts/Inter-Medium.ttf'),
      android: require('../../assets/fonts/Inter-Medium.ttf'),
      default: null,
    }),
    16
  );
  
  /**
   * Convert 3D coordinates to 2D screen position with perspective
   */
  const project3DTo2D = useCallback((x: number, y: number, z: number) => {
    'worklet';
    
    // Apply camera transformations
    const translatedX = x - cameraX.value;
    const translatedY = y - cameraY.value;
    const translatedZ = z - cameraZ.value;
    
    // Apply rotations
    const cosX = Math.cos(rotationX.value);
    const sinX = Math.sin(rotationX.value);
    const cosY = Math.cos(rotationY.value);
    const sinY = Math.sin(rotationY.value);
    
    // Rotate around X axis
    const y1 = translatedY * cosX - translatedZ * sinX;
    const z1 = translatedY * sinX + translatedZ * cosX;
    
    // Rotate around Y axis
    const x2 = translatedX * cosY + z1 * sinY;
    const z2 = -translatedX * sinY + z1 * cosY;
    const y2 = y1;
    
    // Perspective projection
    const perspective = PERSPECTIVE / (PERSPECTIVE + z2);
    const screenX = SCREEN_WIDTH / 2 + x2 * perspective * zoom.value;
    const screenY = SCREEN_HEIGHT / 2 + y2 * perspective * zoom.value;
    
    return {
      x: screenX,
      y: screenY,
      scale: perspective,
      depth: z2,
    };
  }, [cameraX, cameraY, cameraZ, rotationX, rotationY, zoom]);
  
  /**
   * Generate 3D waveform path for audio source
   */
  const generate3DWaveform = useCallback((source: AudioSource3D, time: number): WaveformPath3D[] => {
    'worklet';
    
    const paths: WaveformPath3D[] = [];
    const frequency = source.frequency;
    const amplitude = source.volume * 50;
    const segments = 50;
    
    // Generate multiple layers for 3D effect
    for (let layer = 0; layer < 3; layer++) {
      const points: { x: number; y: number }[] = [];
      const depthOffset = layer * 20;
      
      for (let i = 0; i <= segments; i++) {
        const t = i / segments;
        const angle = t * Math.PI * 2;
        const radius = 100 + amplitude * Math.sin(angle * frequency + time * 0.001);
        
        const x = source.x + Math.cos(angle) * radius;
        const y = source.y + Math.sin(angle) * radius;
        const z = source.z + depthOffset + Math.sin(angle * 2 + time * 0.002) * 10;
        
        const projected = project3DTo2D(x, y, z);
        points.push({ x: projected.x, y: projected.y });
      }
      
      // Create path string
      const pathData = points.reduce((path, point, index) => {
        if (index === 0) return `M ${point.x} ${point.y}`;
        return `${path} L ${point.x} ${point.y}`;
      }, '');
      
      paths.push({
        path: pathData + ' Z',
        depth: source.z + depthOffset,
        color: source.color,
        opacity: 0.8 - layer * 0.2,
      });
    }
    
    return paths;
  }, [project3DTo2D]);
  
  /**
   * Generate 3D grid for spatial reference
   */
  const generate3DGrid = useCallback(() => {
    'worklet';
    
    const gridLines: { start: any; end: any; opacity: number }[] = [];
    const { width, height, depth } = spatialField.dimensions;
    
    // Floor grid
    for (let x = -width / 2; x <= width / 2; x += GRID_SIZE) {
      for (let z = -depth / 2; z <= depth / 2; z += GRID_SIZE) {
        // X-axis lines
        if (z % (GRID_SIZE * 2) === 0) {
          const start = project3DTo2D(x, height / 2, -depth / 2);
          const end = project3DTo2D(x, height / 2, depth / 2);
          gridLines.push({
            start,
            end,
            opacity: 0.2 * start.scale,
          });
        }
        
        // Z-axis lines
        if (x % (GRID_SIZE * 2) === 0) {
          const start = project3DTo2D(-width / 2, height / 2, z);
          const end = project3DTo2D(width / 2, height / 2, z);
          gridLines.push({
            start,
            end,
            opacity: 0.2 * start.scale,
          });
        }
      }
    }
    
    return gridLines;
  }, [spatialField, project3DTo2D]);
  
  /**
   * Calculate spatial audio properties (distance, panning, reverb)
   */
  const calculateSpatialAudio = useCallback((source: AudioSource3D) => {
    'worklet';
    
    const { listenerPosition } = spatialField;
    
    // Calculate 3D distance
    const dx = source.x - listenerPosition.x;
    const dy = source.y - listenerPosition.y;
    const dz = source.z - listenerPosition.z;
    const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);
    
    // Calculate volume based on distance (inverse square law)
    const maxDistance = 500;
    const volumeMultiplier = Math.max(0, 1 - (distance / maxDistance) ** 2);
    
    // Calculate stereo panning based on horizontal position
    const pan = Math.max(-1, Math.min(1, dx / 200));
    
    // Calculate reverb based on room acoustics and distance
    const reverb = spatialField.reverbLevel * (distance / maxDistance);
    
    // Height-based frequency filtering (higher = brighter)
    const heightFilter = 0.5 + (dy / 400) * 0.5;
    
    return {
      volume: source.volume * volumeMultiplier,
      pan,
      reverb,
      filter: heightFilter,
      distance,
    };
  }, [spatialField]);
  
  /**
   * Render audio source as 3D sphere with effects
   */
  const renderAudioSource = useCallback((source: AudioSource3D, index: number) => {
    const projected = project3DTo2D(source.x, source.y, source.z);
    const spatialAudio = calculateSpatialAudio(source);
    const palette = colorSystem.getDynamicPalette();
    
    // Scale based on depth and volume
    const baseSize = 30;
    const size = baseSize * projected.scale * (0.5 + spatialAudio.volume * 0.5);
    
    // Pulsing animation
    const pulseScale = mix(pulsePhase, 0.9, 1.1);
    const glowSize = size * 1.5 * pulseScale;
    
    return (
      <Group key={source.id}>
        {/* Glow effect */}
        <Circle
          cx={projected.x}
          cy={projected.y}
          r={glowSize}
          opacity={spatialAudio.volume * 0.4 * glowIntensity.value}
        >
          <Blur blur={20} />
          <LinearGradient
            start={vec(projected.x - glowSize, projected.y - glowSize)}
            end={vec(projected.x + glowSize, projected.y + glowSize)}
            colors={[source.color, 'transparent']}
          />
        </Circle>
        
        {/* Main sphere */}
        <Circle
          cx={projected.x}
          cy={projected.y}
          r={size}
          opacity={0.9}
        >
          <LinearGradient
            start={vec(projected.x - size, projected.y - size)}
            end={vec(projected.x + size, projected.y + size)}
            colors={[
              source.color,
              colorSystem.interpolateColor(source.color, '#000000', 0.3),
            ]}
          />
          <Shadow dx={2} dy={2} blur={5} color="rgba(0,0,0,0.3)" />
        </Circle>
        
        {/* Inner highlight for 3D effect */}
        <Circle
          cx={projected.x - size * 0.3}
          cy={projected.y - size * 0.3}
          r={size * 0.3}
          color="rgba(255,255,255,0.4)"
          blendMode={BlendMode.Screen}
        />
        
        {/* Waveform visualization */}
        {source.active && (
          <Group>
            {generate3DWaveform(source, clock.current).map((waveform, wIndex) => (
              <Path
                key={wIndex}
                path={waveform.path}
                style="stroke"
                strokeWidth={2}
                color={waveform.color}
                opacity={waveform.opacity}
                blendMode={BlendMode.Screen}
              />
            ))}
          </Group>
        )}
        
        {/* Label */}
        {showLabels && font && (
          <Text
            x={projected.x}
            y={projected.y + size + 20}
            text={source.label}
            font={font}
            color="rgba(255,255,255,0.8)"
            origin={{ x: projected.x, y: projected.y + size + 20 }}
          />
        )}
        
        {/* Distance indicator */}
        <Text
          x={projected.x}
          y={projected.y + size + 35}
          text={`${Math.round(spatialAudio.distance)}m`}
          font={font}
          color="rgba(255,255,255,0.5)"
          origin={{ x: projected.x, y: projected.y + size + 35 }}
        />
      </Group>
    );
  }, [project3DTo2D, calculateSpatialAudio, colorSystem, pulsePhase, glowIntensity, clock, showLabels, font]);
  
  /**
   * Render spatial field boundaries
   */
  const renderSpatialBounds = useCallback(() => {
    const { dimensions } = spatialField;
    const corners = [
      { x: -dimensions.width / 2, y: -dimensions.height / 2, z: -dimensions.depth / 2 },
      { x: dimensions.width / 2, y: -dimensions.height / 2, z: -dimensions.depth / 2 },
      { x: dimensions.width / 2, y: dimensions.height / 2, z: -dimensions.depth / 2 },
      { x: -dimensions.width / 2, y: dimensions.height / 2, z: -dimensions.depth / 2 },
      { x: -dimensions.width / 2, y: -dimensions.height / 2, z: dimensions.depth / 2 },
      { x: dimensions.width / 2, y: -dimensions.height / 2, z: dimensions.depth / 2 },
      { x: dimensions.width / 2, y: dimensions.height / 2, z: dimensions.depth / 2 },
      { x: -dimensions.width / 2, y: dimensions.height / 2, z: dimensions.depth / 2 },
    ];
    
    const projectedCorners = corners.map(corner => project3DTo2D(corner.x, corner.y, corner.z));
    
    // Define edges
    const edges = [
      [0, 1], [1, 2], [2, 3], [3, 0], // Front face
      [4, 5], [5, 6], [6, 7], [7, 4], // Back face
      [0, 4], [1, 5], [2, 6], [3, 7], // Connecting edges
    ];
    
    return (
      <Group opacity={0.3}>
        {edges.map(([start, end], index) => {
          const startPoint = projectedCorners[start];
          const endPoint = projectedCorners[end];
          
          return (
            <Path
              key={`edge-${index}`}
              path={`M ${startPoint.x} ${startPoint.y} L ${endPoint.x} ${endPoint.y}`}
              style="stroke"
              strokeWidth={1}
              color="rgba(255,255,255,0.3)"
            />
          );
        })}
      </Group>
    );
  }, [spatialField, project3DTo2D]);
  
  /**
   * Render listener position indicator
   */
  const renderListener = useCallback(() => {
    const { listenerPosition } = spatialField;
    const projected = project3DTo2D(listenerPosition.x, listenerPosition.y, listenerPosition.z);
    const size = 20 * projected.scale;
    
    return (
      <Group>
        {/* Listener icon (ear shape) */}
        <Circle
          cx={projected.x}
          cy={projected.y}
          r={size}
          color="#FFD700"
          opacity={0.8}
        >
          <Shadow dx={2} dy={2} blur={5} color="rgba(0,0,0,0.5)" />
        </Circle>
        
        {/* Direction indicator */}
        <Path
          path={`M ${projected.x} ${projected.y - size} L ${projected.x - size * 0.5} ${projected.y + size * 0.5} L ${projected.x + size * 0.5} ${projected.y + size * 0.5} Z`}
          color="#FFD700"
          opacity={0.6}
        />
        
        {/* Listening range */}
        <Circle
          cx={projected.x}
          cy={projected.y}
          r={100 * projected.scale}
          style="stroke"
          strokeWidth={1}
          color="rgba(255,215,0,0.2)"
        />
      </Group>
    );
  }, [spatialField, project3DTo2D]);
  
  /**
   * Gesture handlers for 3D navigation
   */
  const panGestureHandler = useAnimatedGestureHandler({
    onStart: (event, ctx: any) => {
      ctx.startX = cameraX.value;
      ctx.startY = cameraY.value;
    },
    onActive: (event, ctx) => {
      if (event.numberOfPointers === 1) {
        // Rotate view
        rotationY.value = ctx.startY + event.translationX * 0.01;
        rotationX.value = ctx.startX - event.translationY * 0.01;
      } else if (event.numberOfPointers === 2) {
        // Pan camera
        cameraX.value = ctx.startX - event.translationX;
        cameraY.value = ctx.startY - event.translationY;
      }
    },
  });
  
  const pinchGestureHandler = useAnimatedGestureHandler({
    onActive: (event) => {
      zoom.value = Math.max(0.5, Math.min(3, event.scale));
    },
  });
  
  /**
   * Touch handler for source selection
   */
  const touchHandler = useTouchHandler({
    onStart: ({ x, y }) => {
      'worklet';
      
      // Find closest audio source
      let closestSource: AudioSource3D | null = null;
      let minDistance = Infinity;
      
      audioSources.forEach(source => {
        const projected = project3DTo2D(source.x, source.y, source.z);
        const distance = Math.sqrt(
          (x - projected.x) ** 2 + (y - projected.y) ** 2
        );
        
        if (distance < 50 && distance < minDistance) {
          minDistance = distance;
          closestSource = source;
        }
      });
      
      if (closestSource && onSourceSelect) {
        runOnJS(onSourceSelect)(closestSource);
      }
    },
  });
  
  // Auto-rotate when active
  useEffect(() => {
    if (isActive) {
      rotationY.value = withRepeat(
        withTiming(Math.PI * 2, { duration: 20000, easing: Easing.linear }),
        -1
      );
    } else {
      rotationY.value = withTiming(0, { duration: 1000 });
    }
  }, [isActive, rotationY]);
  
  // Update spatial field
  useEffect(() => {
    setSpatialField(prev => ({
      ...prev,
      sources: audioSources,
    }));
  }, [audioSources]);
  
  // Render the 3D visualization
  return (
    <GestureHandlerRootView style={styles.container}>
      <PanGestureHandler onGestureEvent={panGestureHandler} enabled={enableGestures}>
        <Animated.View style={StyleSheet.absoluteFillObject}>
          <PinchGestureHandler onGestureEvent={pinchGestureHandler} enabled={enableGestures}>
            <Animated.View style={StyleSheet.absoluteFillObject}>
              <Canvas
                ref={canvasRef}
                style={StyleSheet.absoluteFillObject}
                onTouch={enableGestures ? touchHandler : undefined}
              >
                {/* Background gradient */}
                <Group>
                  <LinearGradient
                    start={vec(0, 0)}
                    end={vec(SCREEN_WIDTH, SCREEN_HEIGHT)}
                    colors={['#0a0a1a', '#1a1a3a']}
                  />
                </Group>
                
                {/* 3D Grid */}
                {showGrid && (
                  <Group>
                    {generate3DGrid().map((line, index) => (
                      <Path
                        key={`grid-${index}`}
                        path={`M ${line.start.x} ${line.start.y} L ${line.end.x} ${line.end.y}`}
                        style="stroke"
                        strokeWidth={1}
                        color="rgba(255,255,255,0.1)"
                        opacity={line.opacity}
                      />
                    ))}
                  </Group>
                )}
                
                {/* Spatial bounds */}
                {renderSpatialBounds()}
                
                {/* Audio sources (sorted by depth for proper rendering order) */}
                <Group>
                  {audioSources
                    .sort((a, b) => {
                      const projA = project3DTo2D(a.x, a.y, a.z);
                      const projB = project3DTo2D(b.x, b.y, b.z);
                      return projB.depth - projA.depth;
                    })
                    .map((source, index) => renderAudioSource(source, index))}
                </Group>
                
                {/* Listener position */}
                {renderListener()}
                
                {/* HUD overlay */}
                <Group>
                  {/* Compass */}
                  <Circle
                    cx={SCREEN_WIDTH - 60}
                    cy={60}
                    r={40}
                    style="stroke"
                    strokeWidth={2}
                    color="rgba(255,255,255,0.3)"
                  />
                  <Path
                    path={`M ${SCREEN_WIDTH - 60} ${30} L ${SCREEN_WIDTH - 65} ${40} L ${SCREEN_WIDTH - 55} ${40} Z`}
                    color="#FF0000"
                    transform={[{ rotate: rotationY.value }]}
                    origin={vec(SCREEN_WIDTH - 60, 60)}
                  />
                  
                  {/* Room info */}
                  {font && (
                    <Group>
                      <Text
                        x={20}
                        y={30}
                        text={`Room: ${spatialField.acousticProperties.roomSize}`}
                        font={font}
                        color="rgba(255,255,255,0.6)"
                      />
                      <Text
                        x={20}
                        y={50}
                        text={`Reverb: ${Math.round(spatialField.reverbLevel * 100)}%`}
                        font={font}
                        color="rgba(255,255,255,0.6)"
                      />
                      <Text
                        x={20}
                        y={70}
                        text={`Sources: ${audioSources.filter(s => s.active).length}/${audioSources.length}`}
                        font={font}
                        color="rgba(255,255,255,0.6)"
                      />
                    </Group>
                  )}
                </Group>
              </Canvas>
            </Animated.View>
          </PinchGestureHandler>
        </Animated.View>
      </PanGestureHandler>
    </GestureHandlerRootView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0a0a1a',
  },
});

export default Spatial3DAudioVisualizer;