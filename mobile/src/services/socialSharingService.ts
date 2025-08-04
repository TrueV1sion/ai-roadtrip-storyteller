import { apiManager } from './api/apiManager';

import { logger } from '@/services/logger';
interface VideoOptions {
  duration?: number;
  includeMap?: boolean;
  includePhotos?: boolean;
  includeStats?: boolean;
  musicStyle?: string;
}

interface VideoData {
  video_url: string;
  thumbnail_url: string;
  duration: number;
  title: string;
  description: string;
  hashtags: string[];
  share_links: Record<string, string>;
}

interface ShareContent {
  platform: string;
  text?: string;
  caption?: string;
  message?: string;
  hashtags?: string[];
  media_type?: string;
  video_url?: string;
  thumbnail_url?: string;
}

class SocialSharingService {
  async createJourneyVideo(
    tripId: string,
    options?: VideoOptions
  ): Promise<{ status: string; message?: string; status_url?: string }> {
    try {
      const response = await apiManager.post('/api/social/journey-video/create', {
        trip_id: tripId,
        options
      });
      return response.data;
    } catch (error) {
      logger.error('Error creating journey video:', error);
      throw error;
    }
  }

  async getVideoStatus(
    tripId: string
  ): Promise<{ status: string; video?: VideoData; message?: string }> {
    try {
      const response = await apiManager.get(`/api/social/journey-video/status/${tripId}`);
      return response.data;
    } catch (error) {
      logger.error('Error getting video status:', error);
      throw error;
    }
  }

  async prepareShareContent(
    tripId: string,
    platform: string,
    includeVideo: boolean = true
  ): Promise<ShareContent> {
    try {
      const response = await apiManager.post('/api/social/share/prepare', {
        trip_id: tripId,
        platform,
        include_video: includeVideo
      });
      return response.data;
    } catch (error) {
      logger.error('Error preparing share content:', error);
      throw error;
    }
  }

  async trackShare(
    tripId: string,
    platform: string,
    shared: boolean = true
  ): Promise<{ status: string; message: string }> {
    try {
      const response = await apiManager.post('/api/social/share/track', {
        trip_id: tripId,
        platform,
        shared
      });
      return response.data;
    } catch (error) {
      logger.error('Error tracking share:', error);
      // Don't throw - tracking shouldn't break sharing
      return { status: 'error', message: 'Tracking failed' };
    }
  }

  async getShareTemplates(): Promise<any> {
    try {
      const response = await apiManager.get('/api/social/templates');
      return response.data.templates;
    } catch (error) {
      logger.error('Error getting share templates:', error);
      throw error;
    }
  }

  async getTrendingContent(): Promise<any> {
    try {
      const response = await apiManager.get('/api/social/trending');
      return response.data;
    } catch (error) {
      logger.error('Error getting trending content:', error);
      throw error;
    }
  }

  // Helper method to format share text based on platform limits
  formatShareText(text: string, platform: string): string {
    const limits: Record<string, number> = {
      twitter: 280,
      facebook: 63206,
      instagram: 2200,
      tiktok: 150
    };

    const limit = limits[platform] || 500;
    
    if (text.length <= limit) {
      return text;
    }

    // Truncate with ellipsis
    return text.substring(0, limit - 3) + '...';
  }

  // Generate platform-specific share URL
  generateShareUrl(platform: string, content: ShareContent): string {
    const baseUrl = 'https://app.roadtripstoryteller.com';
    const videoUrl = content.video_url ? `${baseUrl}${content.video_url}` : '';

    switch (platform) {
      case 'twitter':
        const twitterParams = new URLSearchParams({
          text: content.text || '',
          url: videoUrl,
          hashtags: content.hashtags?.join(',') || ''
        });
        return `https://twitter.com/intent/tweet?${twitterParams}`;

      case 'facebook':
        return `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(videoUrl)}`;

      case 'whatsapp':
        const whatsappText = `${content.message || ''} ${videoUrl}`;
        return `whatsapp://send?text=${encodeURIComponent(whatsappText)}`;

      default:
        return videoUrl;
    }
  }

  // Download video to device
  async downloadVideo(videoUrl: string): Promise<string> {
    // This would be implemented with expo-file-system
    // For now, return mock path
    return '/path/to/downloaded/video.mp4';
  }

  // Share to Instagram Stories (requires special handling)
  async shareToInstagramStories(videoPath: string, stickerImage?: string): Promise<void> {
    // This would use Instagram's sharing SDK
    // Requires native module implementation
    logger.debug('Sharing to Instagram Stories:', videoPath);
  }

  // Share to TikTok (requires special handling)
  async shareToTikTok(videoPath: string): Promise<void> {
    // This would use TikTok's sharing SDK
    // Requires native module implementation
    logger.debug('Sharing to TikTok:', videoPath);
  }
}

export const socialSharingService = new SocialSharingService();