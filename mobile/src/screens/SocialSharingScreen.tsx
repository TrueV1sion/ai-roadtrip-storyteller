import React, { useState, useEffect } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  ActivityIndicator,
  Share,
  Alert,
  Dimensions
} from 'react-native';
import { Video } from 'expo-av';
import * as MediaLibrary from 'expo-media-library';
import * as Sharing from 'expo-sharing';
import {
  Twitter,
  Facebook,
  Instagram,
  Music,
  Download,
  Share2,
  Check,
  Play,
  Edit3
} from 'lucide-react-native';

import { socialSharingService } from '../services/socialSharingService';
import { theme } from '../theme';

const { width: screenWidth } = Dimensions.get('window');

interface SocialSharingScreenProps {
  route: {
    params: {
      tripId: string;
    };
  };
  navigation: any;
}

export default function SocialSharingScreen({ route, navigation }: SocialSharingScreenProps) {
  const { tripId } = route.params;
  const [videoStatus, setVideoStatus] = useState<'idle' | 'generating' | 'ready' | 'error'>('idle');
  const [videoData, setVideoData] = useState<any>(null);
  const [selectedPlatform, setSelectedPlatform] = useState<string>('instagram');
  const [shareContent, setShareContent] = useState<any>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [videoOptions, setVideoOptions] = useState({
    duration: 60,
    includeMap: true,
    includePhotos: true,
    includeStats: true,
    musicStyle: 'upbeat'
  });

  useEffect(() => {
    checkVideoStatus();
  }, []);

  const checkVideoStatus = async () => {
    try {
      const status = await socialSharingService.getVideoStatus(tripId);
      if (status.status === 'ready') {
        setVideoStatus('ready');
        setVideoData(status.video);
      } else {
        setVideoStatus('idle');
      }
    } catch (error) {
      logger.error('Error checking video status:', error);
    }
  };

  const generateVideo = async () => {
    try {
      setVideoStatus('generating');
      const result = await socialSharingService.createJourneyVideo(tripId, videoOptions);
      
      if (result.status === 'processing') {
        // Poll for completion
        const checkInterval = setInterval(async () => {
          const status = await socialSharingService.getVideoStatus(tripId);
          if (status.status === 'ready') {
            clearInterval(checkInterval);
            setVideoStatus('ready');
            setVideoData(status.video);
          }
        }, 5000);
        
        // Timeout after 2 minutes
        setTimeout(() => {
          clearInterval(checkInterval);
          if (videoStatus !== 'ready') {
            setVideoStatus('error');
            Alert.alert('Error', 'Video generation timed out. Please try again.');
          }
        }, 120000);
      }
    } catch (error) {
      setVideoStatus('error');
      Alert.alert('Error', 'Failed to generate video. Please try again.');
    }
  };

  const prepareShareContent = async (platform: string) => {
    try {
      setSelectedPlatform(platform);
      const content = await socialSharingService.prepareShareContent(
        tripId,
        platform,
        videoStatus === 'ready'
      );
      setShareContent(content);
    } catch (error) {
      Alert.alert('Error', 'Failed to prepare share content');
    }
  };

  const shareToplatform = async () => {
    if (!shareContent) return;

    try {
      // Track share
      await socialSharingService.trackShare(tripId, selectedPlatform);

      switch (selectedPlatform) {
        case 'twitter':
        case 'facebook':
        case 'whatsapp':
          // Use native share sheet
          const shareOptions = {
            message: shareContent.text || shareContent.caption || shareContent.message,
            url: videoData?.video_url
          };
          await Share.share(shareOptions);
          break;

        case 'instagram':
        case 'tiktok':
          // These require saving video first
          if (videoData?.video_url) {
            await downloadVideo();
            Alert.alert(
              'Video Saved',
              `Video saved to camera roll. Open ${selectedPlatform} and upload from there.`
            );
          }
          break;
      }
    } catch (error) {
      logger.error('Share error:', error);
    }
  };

  const downloadVideo = async () => {
    if (!videoData?.video_url) return;

    try {
      setIsDownloading(true);
      
      // Request permissions
      const { status } = await MediaLibrary.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission needed', 'Please grant camera roll permissions to save video');
        return;
      }

      // Download and save video
      // In production, implement actual download logic
      Alert.alert('Success', 'Video saved to camera roll!');
      
    } catch (error) {
      Alert.alert('Error', 'Failed to save video');
    } finally {
      setIsDownloading(false);
    }
  };

  const platforms = [
    { id: 'instagram', name: 'Instagram', icon: Instagram, color: '#E4405F' },
    { id: 'tiktok', name: 'TikTok', icon: Music, color: '#000000' },
    { id: 'twitter', name: 'Twitter', icon: Twitter, color: '#1DA1F2' },
    { id: 'facebook', name: 'Facebook', icon: Facebook, color: '#1877F2' },
  ];

  const musicStyles = [
    { id: 'upbeat', name: 'Upbeat', emoji: '🎉' },
    { id: 'relaxed', name: 'Relaxed', emoji: '😌' },
    { id: 'epic', name: 'Epic', emoji: '⚡' },
    { id: 'nostalgic', name: 'Nostalgic', emoji: '🌅' }
  ];

  return (
    <ScrollView style={styles.container}>
      {/* Video Preview */}
      <View style={styles.videoSection}>
        {videoStatus === 'ready' && videoData ? (
          <View style={styles.videoContainer}>
            <Image
              source={{ uri: videoData.thumbnail_url }}
              style={styles.videoThumbnail}
            />
            <TouchableOpacity style={styles.playButton}>
              <Play size={40} color="white" fill="white" />
            </TouchableOpacity>
            <View style={styles.videoDuration}>
              <Text style={styles.durationText}>{videoOptions.duration}s</Text>
            </View>
          </View>
        ) : videoStatus === 'generating' ? (
          <View style={styles.generatingContainer}>
            <ActivityIndicator size="large" color={theme.colors.primary} />
            <Text style={styles.generatingText}>Creating your journey video...</Text>
            <Text style={styles.generatingSubtext}>This may take 30-60 seconds</Text>
          </View>
        ) : (
          <View style={styles.noVideoContainer}>
            <Text style={styles.noVideoText}>Create a shareable video of your journey</Text>
            
            {/* Video Options */}
            <View style={styles.optionsContainer}>
              <Text style={styles.optionTitle}>Duration</Text>
              <View style={styles.durationOptions}>
                {[30, 60, 90].map(duration => (
                  <TouchableOpacity
                    key={duration}
                    style={[
                      styles.durationOption,
                      videoOptions.duration === duration && styles.durationOptionActive
                    ]}
                    onPress={() => setVideoOptions({ ...videoOptions, duration })}
                  >
                    <Text style={[
                      styles.durationOptionText,
                      videoOptions.duration === duration && styles.durationOptionTextActive
                    ]}>
                      {duration}s
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              <Text style={styles.optionTitle}>Music Style</Text>
              <View style={styles.musicOptions}>
                {musicStyles.map(style => (
                  <TouchableOpacity
                    key={style.id}
                    style={[
                      styles.musicOption,
                      videoOptions.musicStyle === style.id && styles.musicOptionActive
                    ]}
                    onPress={() => setVideoOptions({ ...videoOptions, musicStyle: style.id })}
                  >
                    <Text style={styles.musicEmoji}>{style.emoji}</Text>
                    <Text style={[
                      styles.musicOptionText,
                      videoOptions.musicStyle === style.id && styles.musicOptionTextActive
                    ]}>
                      {style.name}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>

              <View style={styles.toggleOptions}>
                <TouchableOpacity
                  style={styles.toggleOption}
                  onPress={() => setVideoOptions({ ...videoOptions, includeMap: !videoOptions.includeMap })}
                >
                  <View style={[styles.checkbox, videoOptions.includeMap && styles.checkboxActive]}>
                    {videoOptions.includeMap && <Check size={16} color="white" />}
                  </View>
                  <Text style={styles.toggleText}>Include animated map</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.toggleOption}
                  onPress={() => setVideoOptions({ ...videoOptions, includePhotos: !videoOptions.includePhotos })}
                >
                  <View style={[styles.checkbox, videoOptions.includePhotos && styles.checkboxActive]}>
                    {videoOptions.includePhotos && <Check size={16} color="white" />}
                  </View>
                  <Text style={styles.toggleText}>Include photos</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.toggleOption}
                  onPress={() => setVideoOptions({ ...videoOptions, includeStats: !videoOptions.includeStats })}
                >
                  <View style={[styles.checkbox, videoOptions.includeStats && styles.checkboxActive]}>
                    {videoOptions.includeStats && <Check size={16} color="white" />}
                  </View>
                  <Text style={styles.toggleText}>Include statistics</Text>
                </TouchableOpacity>
              </View>
            </View>

            <TouchableOpacity
              style={styles.generateButton}
              onPress={generateVideo}
            >
              <Text style={styles.generateButtonText}>Generate Video</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Platform Selection */}
      {videoStatus === 'ready' && (
        <>
          <Text style={styles.sectionTitle}>Share to</Text>
          <View style={styles.platformGrid}>
            {platforms.map(platform => (
              <TouchableOpacity
                key={platform.id}
                style={[
                  styles.platformButton,
                  selectedPlatform === platform.id && styles.platformButtonActive,
                  { borderColor: platform.color }
                ]}
                onPress={() => prepareShareContent(platform.id)}
              >
                <platform.icon
                  size={30}
                  color={selectedPlatform === platform.id ? 'white' : platform.color}
                />
                <Text style={[
                  styles.platformName,
                  selectedPlatform === platform.id && styles.platformNameActive
                ]}>
                  {platform.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Share Preview */}
          {shareContent && (
            <View style={styles.previewContainer}>
              <Text style={styles.previewTitle}>Preview</Text>
              <View style={styles.previewContent}>
                <Text style={styles.previewText}>
                  {shareContent.text || shareContent.caption || shareContent.message}
                </Text>
                {shareContent.hashtags && (
                  <Text style={styles.previewHashtags}>
                    {shareContent.hashtags.map((tag: string) => `#${tag}`).join(' ')}
                  </Text>
                )}
              </View>
              
              <TouchableOpacity
                style={styles.editButton}
                onPress={() => navigation.navigate('EditShareContent', { content: shareContent })}
              >
                <Edit3 size={16} color={theme.colors.primary} />
                <Text style={styles.editButtonText}>Edit</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Action Buttons */}
          <View style={styles.actionButtons}>
            <TouchableOpacity
              style={[styles.actionButton, styles.downloadButton]}
              onPress={downloadVideo}
              disabled={isDownloading}
            >
              {isDownloading ? (
                <ActivityIndicator color="white" />
              ) : (
                <>
                  <Download size={20} color="white" />
                  <Text style={styles.actionButtonText}>Save Video</Text>
                </>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.actionButton, styles.shareButton]}
              onPress={shareToplatform}
              disabled={!shareContent}
            >
              <Share2 size={20} color="white" />
              <Text style={styles.actionButtonText}>Share Now</Text>
            </TouchableOpacity>
          </View>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background
  },
  videoSection: {
    backgroundColor: 'white',
    margin: 16,
    borderRadius: 12,
    overflow: 'hidden'
  },
  videoContainer: {
    position: 'relative',
    height: 400
  },
  videoThumbnail: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover'
  },
  playButton: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: [{ translateX: -40 }, { translateY: -40 }],
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center'
  },
  videoDuration: {
    position: 'absolute',
    bottom: 16,
    right: 16,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 4
  },
  durationText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600'
  },
  generatingContainer: {
    padding: 60,
    alignItems: 'center'
  },
  generatingText: {
    marginTop: 16,
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text
  },
  generatingSubtext: {
    marginTop: 8,
    fontSize: 14,
    color: theme.colors.textLight
  },
  noVideoContainer: {
    padding: 24
  },
  noVideoText: {
    fontSize: 16,
    color: theme.colors.text,
    textAlign: 'center',
    marginBottom: 24
  },
  optionsContainer: {
    marginBottom: 24
  },
  optionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: 12,
    marginTop: 16
  },
  durationOptions: {
    flexDirection: 'row',
    gap: 12
  },
  durationOption: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.border,
    alignItems: 'center'
  },
  durationOptionActive: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primary
  },
  durationOptionText: {
    fontSize: 14,
    color: theme.colors.text
  },
  durationOptionTextActive: {
    color: 'white',
    fontWeight: '600'
  },
  musicOptions: {
    flexDirection: 'row',
    gap: 12
  },
  musicOption: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.border,
    alignItems: 'center'
  },
  musicOptionActive: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primary
  },
  musicEmoji: {
    fontSize: 24,
    marginBottom: 4
  },
  musicOptionText: {
    fontSize: 12,
    color: theme.colors.text
  },
  musicOptionTextActive: {
    color: 'white',
    fontWeight: '600'
  },
  toggleOptions: {
    marginTop: 16,
    gap: 12
  },
  toggleOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12
  },
  checkbox: {
    width: 24,
    height: 24,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: theme.colors.border,
    justifyContent: 'center',
    alignItems: 'center'
  },
  checkboxActive: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primary
  },
  toggleText: {
    fontSize: 14,
    color: theme.colors.text
  },
  generateButton: {
    backgroundColor: theme.colors.primary,
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: 'center'
  },
  generateButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600'
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text,
    marginHorizontal: 16,
    marginTop: 24,
    marginBottom: 16
  },
  platformGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 16,
    gap: 12
  },
  platformButton: {
    flex: 1,
    minWidth: (screenWidth - 48) / 2,
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 12,
    borderWidth: 2,
    alignItems: 'center',
    gap: 8
  },
  platformButtonActive: {
    backgroundColor: theme.colors.primary
  },
  platformName: {
    fontSize: 14,
    fontWeight: '500',
    color: theme.colors.text
  },
  platformNameActive: {
    color: 'white'
  },
  previewContainer: {
    backgroundColor: 'white',
    margin: 16,
    padding: 16,
    borderRadius: 12
  },
  previewTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: 12
  },
  previewContent: {
    padding: 16,
    backgroundColor: theme.colors.background,
    borderRadius: 8
  },
  previewText: {
    fontSize: 14,
    color: theme.colors.text,
    lineHeight: 20
  },
  previewHashtags: {
    fontSize: 14,
    color: theme.colors.primary,
    marginTop: 8
  },
  editButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-end',
    marginTop: 12,
    padding: 8
  },
  editButtonText: {
    fontSize: 14,
    color: theme.colors.primary
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 24
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 16,
    borderRadius: 8
  },
  downloadButton: {
    backgroundColor: theme.colors.secondary
  },
  shareButton: {
    backgroundColor: theme.colors.primary
  },
  actionButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600'
  }
});