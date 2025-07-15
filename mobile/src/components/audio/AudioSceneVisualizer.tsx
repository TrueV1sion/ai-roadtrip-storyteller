import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Dimensions,
  TouchableOpacity,
} from 'react-native';
import Svg, { Circle, Path, G, Text as SvgText, Line } from 'react-native-svg';
import Icon from 'react-native-vector-icons/MaterialIcons';

const { width: screenWidth } = Dimensions.get('window');
const visualizerSize = screenWidth - 40;
const centerX = visualizerSize / 2;
const centerY = visualizerSize / 2;

interface AudioSource {
  id: string;
  name: string;
  category: string;
  position: { x: number; y: number; z: number };
  volume: number;
  isActive: boolean;
  color: string;
}

interface AudioSceneVisualizerProps {
  sources: AudioSource[];
  listenerOrientation: number; // In degrees
  onSourceSelect?: (source: AudioSource) => void;
}

export const AudioSceneVisualizer: React.FC<AudioSceneVisualizerProps> = ({
  sources,
  listenerOrientation,
  onSourceSelect,
}) => {
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const rotationAnim = useRef(new Animated.Value(0)).current;
  const pulseAnims = useRef<{ [key: string]: Animated.Value }>({});

  useEffect(() => {
    // Animate listener rotation
    Animated.timing(rotationAnim, {
      toValue: listenerOrientation,
      duration: 300,
      useNativeDriver: true,
    }).start();
  }, [listenerOrientation]);

  useEffect(() => {
    // Create pulse animations for active sources
    sources.forEach((source) => {
      if (!pulseAnims.current[source.id]) {
        pulseAnims.current[source.id] = new Animated.Value(1);
      }

      if (source.isActive) {
        // Create pulsing effect
        Animated.loop(
          Animated.sequence([
            Animated.timing(pulseAnims.current[source.id], {
              toValue: 1.2,
              duration: 1000,
              useNativeDriver: true,
            }),
            Animated.timing(pulseAnims.current[source.id], {
              toValue: 1,
              duration: 1000,
              useNativeDriver: true,
            }),
          ])
        ).start();
      } else {
        pulseAnims.current[source.id].setValue(1);
      }
    });
  }, [sources]);

  const handleSourcePress = (source: AudioSource) => {
    setSelectedSource(source.id);
    onSourceSelect?.(source);
  };

  const convertToScreenCoords = (position: { x: number; y: number; z: number }) => {
    // Convert 3D position to 2D screen coordinates
    // Assuming x/y are in meters, scale to fit visualizer
    const scale = 10; // 1 meter = 10 pixels
    const x = centerX + position.x * scale;
    const y = centerY - position.y * scale; // Invert Y for screen coordinates
    return { x, y };
  };

  const drawDistanceRings = () => {
    const rings = [5, 10, 20, 30]; // Distance in meters
    return rings.map((distance, index) => {
      const radius = distance * 10; // Scale factor
      return (
        <G key={`ring-${index}`}>
          <Circle
            cx={centerX}
            cy={centerY}
            r={radius}
            fill="none"
            stroke="#E0E0E0"
            strokeWidth={1}
            strokeDasharray="5,5"
          />
          <SvgText
            x={centerX + radius + 5}
            y={centerY}
            fill="#999"
            fontSize="10"
            textAnchor="start"
          >
            {distance}m
          </SvgText>
        </G>
      );
    });
  };

  const drawCompass = () => {
    const directions = [
      { angle: 0, label: 'N' },
      { angle: 90, label: 'E' },
      { angle: 180, label: 'S' },
      { angle: 270, label: 'W' },
    ];

    return directions.map((dir) => {
      const radians = (dir.angle * Math.PI) / 180;
      const x = centerX + Math.sin(radians) * (visualizerSize / 2 - 20);
      const y = centerY - Math.cos(radians) * (visualizerSize / 2 - 20);

      return (
        <SvgText
          key={dir.label}
          x={x}
          y={y}
          fill="#666"
          fontSize="14"
          fontWeight="bold"
          textAnchor="middle"
          alignmentBaseline="middle"
        >
          {dir.label}
        </SvgText>
      );
    });
  };

  const drawListener = () => {
    // Draw listener at center with orientation indicator
    const arrowLength = 30;
    const radians = ((listenerOrientation - 90) * Math.PI) / 180;
    const endX = centerX + Math.cos(radians) * arrowLength;
    const endY = centerY + Math.sin(radians) * arrowLength;

    return (
      <G>
        {/* Listener body */}
        <Circle cx={centerX} cy={centerY} r={15} fill="#007AFF" />
        
        {/* Orientation arrow */}
        <Line
          x1={centerX}
          y1={centerY}
          x2={endX}
          y2={endY}
          stroke="#007AFF"
          strokeWidth={3}
        />
        
        {/* Arrow head */}
        <Path
          d={`M ${endX} ${endY} L ${endX - 5} ${endY - 5} L ${endX - 5} ${endY + 5} Z`}
          fill="#007AFF"
          transform={`rotate(${listenerOrientation}, ${endX}, ${endY})`}
        />
      </G>
    );
  };

  const getCategoryIcon = (category: string) => {
    const iconMap: { [key: string]: string } = {
      music: 'music-note',
      ambient: 'nature',
      narration: 'record-voice-over',
      effect: 'audiotrack',
      vehicle: 'directions-car',
      weather: 'cloud',
    };
    return iconMap[category] || 'volume-up';
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>3D Audio Scene</Text>
      
      <View style={styles.visualizer}>
        <Svg width={visualizerSize} height={visualizerSize}>
          {/* Background */}
          <Circle
            cx={centerX}
            cy={centerY}
            r={visualizerSize / 2}
            fill="#F9F9F9"
          />
          
          {/* Distance rings */}
          {drawDistanceRings()}
          
          {/* Compass directions */}
          {drawCompass()}
          
          {/* Audio sources */}
          {sources.map((source) => {
            const coords = convertToScreenCoords(source.position);
            const scale = pulseAnims.current[source.id] || new Animated.Value(1);
            
            return (
              <G key={source.id}>
                {/* Source range indicator */}
                <Circle
                  cx={coords.x}
                  cy={coords.y}
                  r={source.volume * 30}
                  fill={source.color}
                  fillOpacity={0.1}
                />
                
                {/* Source point */}
                <Circle
                  cx={coords.x}
                  cy={coords.y}
                  r={8}
                  fill={source.color}
                  fillOpacity={source.isActive ? 1 : 0.5}
                />
                
                {/* Source label */}
                <SvgText
                  x={coords.x}
                  y={coords.y - 15}
                  fill={source.color}
                  fontSize="10"
                  textAnchor="middle"
                >
                  {source.name}
                </SvgText>
              </G>
            );
          })}
          
          {/* Listener */}
          {drawListener()}
        </Svg>
        
        {/* Touch overlay for source selection */}
        {sources.map((source) => {
          const coords = convertToScreenCoords(source.position);
          return (
            <TouchableOpacity
              key={`touch-${source.id}`}
              style={[
                styles.sourceTouch,
                {
                  left: coords.x - 20,
                  top: coords.y - 20,
                },
              ]}
              onPress={() => handleSourcePress(source)}
            >
              <Animated.View
                style={{
                  transform: [
                    { scale: pulseAnims.current[source.id] || 1 },
                  ],
                }}
              >
                <Icon
                  name={getCategoryIcon(source.category)}
                  size={16}
                  color={source.color}
                />
              </Animated.View>
            </TouchableOpacity>
          );
        })}
      </View>
      
      {/* Selected source info */}
      {selectedSource && (
        <View style={styles.sourceInfo}>
          {(() => {
            const source = sources.find((s) => s.id === selectedSource);
            if (!source) return null;
            
            return (
              <>
                <View style={styles.sourceInfoHeader}>
                  <Icon
                    name={getCategoryIcon(source.category)}
                    size={24}
                    color={source.color}
                  />
                  <Text style={styles.sourceInfoTitle}>{source.name}</Text>
                </View>
                <View style={styles.sourceInfoDetails}>
                  <Text style={styles.sourceInfoText}>
                    Volume: {Math.round(source.volume * 100)}%
                  </Text>
                  <Text style={styles.sourceInfoText}>
                    Distance: {Math.round(Math.sqrt(
                      source.position.x ** 2 + source.position.y ** 2
                    ))}m
                  </Text>
                  <Text style={styles.sourceInfoText}>
                    Status: {source.isActive ? 'Active' : 'Inactive'}
                  </Text>
                </View>
              </>
            );
          })()}
        </View>
      )}
      
      {/* Legend */}
      <View style={styles.legend}>
        <Text style={styles.legendTitle}>Audio Categories</Text>
        <View style={styles.legendItems}>
          {Array.from(new Set(sources.map((s) => s.category))).map((category) => {
            const sample = sources.find((s) => s.category === category);
            if (!sample) return null;
            
            return (
              <View key={category} style={styles.legendItem}>
                <View
                  style={[styles.legendColor, { backgroundColor: sample.color }]}
                />
                <Text style={styles.legendText}>{category}</Text>
              </View>
            );
          })}
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginVertical: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 16,
    textAlign: 'center',
  },
  visualizer: {
    width: visualizerSize,
    height: visualizerSize,
    alignSelf: 'center',
    position: 'relative',
  },
  sourceTouch: {
    position: 'absolute',
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sourceInfo: {
    marginTop: 16,
    padding: 12,
    backgroundColor: '#F5F5F5',
    borderRadius: 8,
  },
  sourceInfoHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  sourceInfoTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
    marginLeft: 8,
  },
  sourceInfoDetails: {
    marginLeft: 32,
  },
  sourceInfoText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  legend: {
    marginTop: 16,
  },
  legendTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
    marginBottom: 8,
  },
  legendItems: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
    marginBottom: 4,
  },
  legendColor: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 6,
  },
  legendText: {
    fontSize: 12,
    color: '#666',
  },
});