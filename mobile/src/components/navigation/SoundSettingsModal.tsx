import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  Platform,
  TouchableOpacity,
} from 'react-native';
import {
  Surface,
  Text,
  Portal,
  Modal,
  Button,
  Slider,
  Chip,
  IconButton,
} from 'react-native-paper';
import { MaterialIcons } from '@expo/vector-icons';
import { AudioMixConfig } from '../../types/audio';
import { COLORS, SPACING } from '../../theme';
import { Audio } from 'expo-av';
import { MusicVisualizer } from '../immersive/MusicVisualizer';
import Animated, { withSpring, useAnimatedStyle, interpolateColor, useSharedValue, withRepeat, withTiming, interpolate } from 'react-native-reanimated';
import { ParticleSystem } from '../common/ParticleSystem';

interface SoundSettingsModalProps {
  visible: boolean;
  onDismiss: () => void;
  audioConfig: AudioMixConfig;
  onUpdateConfig: (config: AudioMixConfig) => void;
}

const AUDIO_PRESETS = {
  balanced: {
    name: 'Balanced',
    icon: 'tune',
    config: {
      storyVolume: 1,
      musicVolume: 0.3,
      ambientVolume: 0.2,
      duckingAmount: 0.5,
      equalizerSettings: { bass: 0, mid: 0, treble: 0 },
    },
  },
  story: {
    name: 'Story Focus',
    icon: 'record-voice-over',
    config: {
      storyVolume: 1,
      musicVolume: 0.1,
      ambientVolume: 0.1,
      duckingAmount: 0.8,
      equalizerSettings: { bass: -3, mid: 3, treble: 2 },
    },
  },
  immersive: {
    name: 'Immersive',
    icon: 'surround-sound',
    config: {
      storyVolume: 0.8,
      musicVolume: 0.4,
      ambientVolume: 0.4,
      duckingAmount: 0.3,
      equalizerSettings: { bass: 3, mid: 0, treble: 1 },
    },
  },
  night: {
    name: 'Night Mode',
    icon: 'nights-stay',
    config: {
      storyVolume: 0.7,
      musicVolume: 0.2,
      ambientVolume: 0.1,
      duckingAmount: 0.6,
      equalizerSettings: { bass: 2, mid: -1, treble: -2 },
    },
  },
  cinematic: {
    name: 'Cinematic',
    icon: 'movie',
    config: {
      storyVolume: 0.9,
      musicVolume: 0.6,
      ambientVolume: 0.3,
      duckingAmount: 0.4,
      equalizerSettings: { bass: 4, mid: 1, treble: 2 },
    },
  },
  meditation: {
    name: 'Meditation',
    icon: 'self-improvement',
    config: {
      storyVolume: 0.6,
      musicVolume: 0.3,
      ambientVolume: 0.5,
      duckingAmount: 0.3,
      equalizerSettings: { bass: 1, mid: -2, treble: -1 },
    },
  },
};

export const SoundSettingsModal: React.FC<SoundSettingsModalProps> = ({
  visible,
  onDismiss,
  audioConfig,
  onUpdateConfig,
}) => {
  const [previewSound, setPreviewSound] = useState<Audio.Sound>();
  const [isPreviewPlaying, setIsPreviewPlaying] = useState(false);
  const [activePreset, setActivePreset] = useState<keyof typeof AUDIO_PRESETS | null>(null);
  const [showPreviewVisualizer, setShowPreviewVisualizer] = useState(false);
  const [ambientSounds] = useState({
    tap: new Audio.Sound(),
    switch: new Audio.Sound(),
    success: new Audio.Sound(),
  });
  const [showParticles, setShowParticles] = useState(false);
  const particleColors = [COLORS.primary, COLORS.success, COLORS.warning];

  const presetScale = useSharedValue(1);
  const eqGlow = useSharedValue(0);

  useEffect(() => {
    loadPreviewSounds();
    loadAmbientSounds();
    return () => {
      cleanupPreviewSounds();
      cleanupAmbientSounds();
    };
  }, []);

  const loadPreviewSounds = async () => {
    try {
      const sound = new Audio.Sound();
      await sound.loadAsync(require('../../../assets/sounds/audio_preview.mp3'));
      setPreviewSound(sound);
    } catch (error) {
      console.error('Error loading preview sounds:', error);
    }
  };

  const cleanupPreviewSounds = async () => {
    if (previewSound) {
      await previewSound.unloadAsync();
    }
  };

  const loadAmbientSounds = async () => {
    try {
      await ambientSounds.tap.loadAsync(
        require('../../../assets/sounds/tap.mp3')
      );
      await ambientSounds.switch.loadAsync(
        require('../../../assets/sounds/switch.mp3')
      );
      await ambientSounds.success.loadAsync(
        require('../../../assets/sounds/success.mp3')
      );
    } catch (error) {
      console.error('Error loading ambient sounds:', error);
    }
  };

  const cleanupAmbientSounds = async () => {
    try {
      await Promise.all(
        Object.values(ambientSounds).map(sound => sound.unloadAsync())
      );
    } catch (error) {
      console.error('Error cleaning up ambient sounds:', error);
    }
  };

  const playPreviewSound = async () => {
    try {
      if (previewSound) {
        setIsPreviewPlaying(true);
        setShowPreviewVisualizer(true);
        await previewSound.setVolumeAsync(audioConfig.musicVolume);
        await previewSound.playAsync();
        setTimeout(async () => {
          await previewSound.stopAsync();
          setIsPreviewPlaying(false);
          setShowPreviewVisualizer(false);
        }, 5000);
      }
    } catch (error) {
      console.error('Error playing preview:', error);
    }
  };

  const playAmbientSound = async (type: keyof typeof ambientSounds) => {
    try {
      const sound = ambientSounds[type];
      await sound.setPositionAsync(0);
      await sound.playAsync();
    } catch (error) {
      console.error('Error playing ambient sound:', error);
    }
  };

  const applyPreset = (preset: keyof typeof AUDIO_PRESETS) => {
    setActivePreset(preset);
    presetScale.value = withSpring(1.1, {}, () => {
      presetScale.value = withSpring(1);
    });
    setShowParticles(true);
    setTimeout(() => setShowParticles(false), 2000);

    const newConfig = {
      ...audioConfig,
      ...AUDIO_PRESETS[preset].config,
    };
    onUpdateConfig(newConfig);
    playPreviewSound();
  };

  const presetCardStyle = useAnimatedStyle(() => ({
    transform: [{ scale: presetScale.value }],
  }));

  const eqGlowStyle = useAnimatedStyle(() => ({
    backgroundColor: interpolateColor(
      eqGlow.value,
      [0, 1],
      [COLORS.background, COLORS.primary + '20']
    ),
  }));

  const presetHoverStyle = useAnimatedStyle(() => {
    const scale = withSpring(showParticles ? 1.05 : 1);
    const rotate = withSpring(showParticles ? '5deg' : '0deg');
    return {
      transform: [{ scale }, { rotate }],
    };
  });

  const Shimmer: React.FC = () => {
    const shimmerAnim = useSharedValue(0);

    useEffect(() => {
      shimmerAnim.value = withRepeat(
        withTiming(1, { duration: 2000 }),
        -1,
        false
      );
    }, []);

    const shimmerStyle = useAnimatedStyle(() => ({
      transform: [
        {
          translateX: interpolate(
            shimmerAnim.value,
            [0, 1],
            [-100, 100]
          ),
        },
      ],
      opacity: interpolate(
        shimmerAnim.value,
        [0, 0.5, 1],
        [0, 1, 0]
      ),
    }));

    return (
      <Animated.View
        style={[
          {
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: COLORS.primary + '20',
          },
          shimmerStyle,
        ]}
      />
    );
  };

  return (
    <Portal>
      <Modal
        visible={visible}
        onDismiss={onDismiss}
        contentContainerStyle={styles.modal}
      >
        <View style={styles.header}>
          <Text style={styles.title}>Sound Settings</Text>
          <IconButton
            icon="close"
            size={24}
            onPress={onDismiss}
          />
        </View>

        {showParticles && (
          <ParticleSystem
            colors={particleColors}
            count={20}
            duration={2000}
            spread={1}
            origin={{ x: 0.5, y: 0.5 }}
          />
        )}

        {/* Enhanced Audio Presets */}
        <Animated.View style={[styles.presets, presetCardStyle]}>
          <View style={styles.presetsHeader}>
            <Text style={styles.sectionTitle}>Sound Presets</Text>
            {activePreset && (
              <Chip
                icon={AUDIO_PRESETS[activePreset].icon}
                style={styles.activePresetChip}
              >
                {AUDIO_PRESETS[activePreset].name}
              </Chip>
            )}
          </View>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.presetsScroll}
          >
            {Object.entries(AUDIO_PRESETS).map(([key, preset]) => (
              <Surface
                key={key}
                style={[
                  styles.presetCard,
                  key === activePreset && styles.activePresetCard,
                  presetHoverStyle,
                ]}
              >
                <TouchableOpacity
                  onPress={() => applyPreset(key as keyof typeof AUDIO_PRESETS)}
                  style={styles.presetButton}
                >
                  <MaterialIcons
                    name={preset.icon}
                    size={32}
                    color={key === activePreset ? COLORS.primary : COLORS.text}
                  />
                  <Text style={[
                    styles.presetName,
                    key === activePreset && styles.activePresetName,
                  ]}>
                    {preset.name}
                  </Text>
                </TouchableOpacity>
                {activePreset === key && <Shimmer />}
              </Surface>
            ))}
          </ScrollView>
        </Animated.View>

        {/* Preview Visualizer */}
        {showPreviewVisualizer && (
          <View style={styles.previewContainer}>
            <MusicVisualizer
              isPlaying={isPreviewPlaying}
              style={styles.previewVisualizer}
            />
          </View>
        )}

        {/* Enhanced Volume Controls */}
        <Animated.View style={[styles.section, eqGlowStyle]}>
          <Text style={styles.sectionTitle}>Volume Levels</Text>
          <View style={styles.volumeControl}>
            <MaterialIcons name="record-voice-over" size={24} color={COLORS.primary} />
            <View style={styles.sliderContainer}>
              <Text style={styles.sliderLabel}>Story Volume</Text>
              <Slider
                value={audioConfig.storyVolume}
                onValueChange={value =>
                  onUpdateConfig({ ...audioConfig, storyVolume: value })
                }
                style={styles.slider}
              />
            </View>
          </View>

          <View style={styles.volumeControl}>
            <MaterialIcons name="music-note" size={24} color={COLORS.primary} />
            <View style={styles.sliderContainer}>
              <Text style={styles.sliderLabel}>Music Volume</Text>
              <Slider
                value={audioConfig.musicVolume}
                onValueChange={value =>
                  onUpdateConfig({ ...audioConfig, musicVolume: value })
                }
                style={styles.slider}
              />
            </View>
          </View>

          <View style={styles.volumeControl}>
            <MaterialIcons name="waves" size={24} color={COLORS.primary} />
            <View style={styles.sliderContainer}>
              <Text style={styles.sliderLabel}>Ambient Volume</Text>
              <Slider
                value={audioConfig.ambientVolume}
                onValueChange={value =>
                  onUpdateConfig({ ...audioConfig, ambientVolume: value })
                }
                style={styles.slider}
              />
            </View>
          </View>
        </Animated.View>

        {/* Equalizer */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Equalizer</Text>
          <View style={styles.equalizer}>
            {['bass', 'mid', 'treble'].map(band => (
              <View key={band} style={styles.eqBand}>
                <Text style={styles.eqLabel}>
                  {band.charAt(0).toUpperCase() + band.slice(1)}
                </Text>
                <Slider
                  value={audioConfig.equalizerSettings[band]}
                  minimumValue={-12}
                  maximumValue={12}
                  onValueChange={value =>
                    onUpdateConfig({
                      ...audioConfig,
                      equalizerSettings: {
                        ...audioConfig.equalizerSettings,
                        [band]: value,
                      },
                    })
                  }
                  style={styles.eqSlider}
                />
                <Text style={styles.eqValue}>
                  {audioConfig.equalizerSettings[band] > 0 && '+'}
                  {audioConfig.equalizerSettings[band]}dB
                </Text>
              </View>
            ))}
          </View>
        </View>

        {/* Advanced Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Advanced Settings</Text>
          <View style={styles.advancedSetting}>
            <View style={styles.settingHeader}>
              <Text style={styles.settingLabel}>Ducking Amount</Text>
              <Text style={styles.settingValue}>
                {Math.round(audioConfig.duckingAmount * 100)}%
              </Text>
            </View>
            <Slider
              value={audioConfig.duckingAmount}
              onValueChange={value =>
                onUpdateConfig({ ...audioConfig, duckingAmount: value })
              }
              style={styles.slider}
            />
          </View>

          <View style={styles.advancedSetting}>
            <View style={styles.settingHeader}>
              <Text style={styles.settingLabel}>Crossfade Duration</Text>
              <Text style={styles.settingValue}>
                {audioConfig.crossfadeDuration.toFixed(1)}s
              </Text>
            </View>
            <Slider
              value={audioConfig.crossfadeDuration}
              minimumValue={0.5}
              maximumValue={5}
              onValueChange={value =>
                onUpdateConfig({ ...audioConfig, crossfadeDuration: value })
              }
              style={styles.slider}
            />
          </View>
        </View>

        <Button
          mode="contained"
          onPress={onDismiss}
          style={styles.doneButton}
        >
          Done
        </Button>
      </Modal>
    </Portal>
  );
};

const styles = StyleSheet.create({
  modal: {
    backgroundColor: COLORS.background,
    margin: SPACING.medium,
    padding: SPACING.medium,
    borderRadius: 12,
    maxHeight: '90%',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.medium,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  presets: {
    marginBottom: SPACING.medium,
  },
  presetsScroll: {
    marginHorizontal: -SPACING.medium,
    paddingHorizontal: SPACING.medium,
  },
  presetsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.small,
  },
  presetCard: {
    padding: SPACING.small,
    borderRadius: 12,
    marginRight: SPACING.small,
    alignItems: 'center',
    elevation: 2,
  },
  presetName: {
    marginTop: SPACING.xsmall,
    fontSize: 12,
  },
  section: {
    marginBottom: SPACING.medium,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: SPACING.small,
  },
  volumeControl: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.small,
  },
  sliderContainer: {
    flex: 1,
    marginLeft: SPACING.small,
  },
  sliderLabel: {
    fontSize: 14,
    marginBottom: SPACING.xsmall,
  },
  slider: {
    height: 40,
  },
  equalizer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: SPACING.small,
  },
  eqBand: {
    flex: 1,
    alignItems: 'center',
  },
  eqLabel: {
    fontSize: 12,
    marginBottom: SPACING.xsmall,
  },
  eqSlider: {
    height: 120,
    width: 40,
  },
  eqValue: {
    fontSize: 12,
    marginTop: SPACING.xsmall,
  },
  advancedSetting: {
    marginBottom: SPACING.medium,
  },
  settingHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.xsmall,
  },
  settingLabel: {
    fontSize: 14,
  },
  settingValue: {
    fontSize: 12,
    color: COLORS.textSecondary,
  },
  doneButton: {
    marginTop: SPACING.small,
  },
  activePresetChip: {
    backgroundColor: COLORS.primary + '20',
  },
  presetButton: {
    padding: SPACING.small,
    alignItems: 'center',
  },
  activePresetCard: {
    borderColor: COLORS.primary,
    borderWidth: 2,
    backgroundColor: COLORS.primary + '10',
  },
  activePresetName: {
    color: COLORS.primary,
    fontWeight: 'bold',
  },
  previewContainer: {
    height: 60,
    marginVertical: SPACING.medium,
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    overflow: 'hidden',
    padding: SPACING.small,
  },
  previewVisualizer: {
    height: '100%',
  },
});

export default SoundSettingsModal; 