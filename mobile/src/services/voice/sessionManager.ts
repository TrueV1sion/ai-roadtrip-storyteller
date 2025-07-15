import { Story } from '@/types/cultural';
import StorageManager from '@utils/storage';
import { VoicePersonality } from './voicePersonalities';
import { SpeakingStyle } from './voiceTypes';

export interface UserFeedback {
  sentiment: number;  // -1 to 1
  engagement: number;  // 0 to 1
  confusion: number;  // 0 to 1
  timestamp: number;
}

export interface ConversationTopic {
  id: string;
  type: 'story' | 'location' | 'fact' | 'question';
  content: string;
  confidence: number;  // 0 to 1
  verificationStatus: 'verified' | 'unverified' | 'inferred';
  sources?: string[];
  relatedTopics: string[];  // IDs of related topics
  lastDiscussed: number;  // timestamp
  userFeedback: UserFeedback[];
}

interface ConversationMemory {
  shortTerm: ConversationTopic[];  // Recent topics (last 30 minutes)
  longTerm: ConversationTopic[];   // Important topics worth remembering
  userPreferences: {
    favoriteTopics: string[];
    avoidedTopics: string[];
    preferredStyle: Partial<SpeakingStyle>;
    interactionFrequency: number;  // Average interactions per minute
  };
}

interface SessionState {
  currentTopic?: ConversationTopic;
  activeStory?: Story;
  personality: VoicePersonality;
  contextStack: ConversationTopic[];
  recentFeedback: UserFeedback[];
  startTime: number;
  lastInteraction: number;
  interactionCount: number;
}

class SessionManager {
  private currentSession: SessionState | null = null;
  private memory: ConversationMemory = {
    shortTerm: [],
    longTerm: [],
    userPreferences: {
      favoriteTopics: [],
      avoidedTopics: [],
      preferredStyle: {},
      interactionFrequency: 0,
    },
  };

  private readonly SENTIMENT_THRESHOLD = 0.3;
  private readonly CONFUSION_THRESHOLD = 0.7;
  private readonly SHORT_TERM_MEMORY_DURATION = 30 * 60 * 1000; // 30 minutes
  private readonly MAX_SHORT_TERM_TOPICS = 50;
  private readonly MAX_LONG_TERM_TOPICS = 200;

  constructor() {
    void this.initialize();
  }

  private async initialize(): Promise<void> {
    await this.loadMemory();
  }

  async startSession(personality: VoicePersonality): Promise<void> {
    this.currentSession = {
      personality,
      contextStack: [],
      recentFeedback: [],
      startTime: Date.now(),
      lastInteraction: Date.now(),
      interactionCount: 0,
    };
    await this.saveSession();
  }

  async endSession(): Promise<void> {
    if (!this.currentSession) return;

    // Process session insights
    await this.processSessionInsights();
    
    // Clear session
    this.currentSession = null;
    await StorageManager.removeItem('@current_session');
  }

  async addTopic(topic: Omit<ConversationTopic, 'userFeedback' | 'lastDiscussed'>): Promise<void> {
    if (!this.currentSession) throw new Error('No active session');

    const newTopic: ConversationTopic = {
      ...topic,
      userFeedback: [],
      lastDiscussed: Date.now(),
    };

    // Add to session context
    this.currentSession.currentTopic = newTopic;
    this.currentSession.contextStack.push(newTopic);
    
    // Add to short-term memory
    this.memory.shortTerm.unshift(newTopic);
    if (this.memory.shortTerm.length > this.MAX_SHORT_TERM_TOPICS) {
      this.memory.shortTerm.pop();
    }

    await this.saveMemory();
    await this.saveSession();
  }

  async addUserFeedback(feedback: Omit<UserFeedback, 'timestamp'>): Promise<SpeakingStyle> {
    if (!this.currentSession) throw new Error('No active session');

    const feedbackWithTimestamp: UserFeedback = {
      ...feedback,
      timestamp: Date.now(),
    };

    // Add to current topic and recent feedback
    if (this.currentSession.currentTopic) {
      this.currentSession.currentTopic.userFeedback.push(feedbackWithTimestamp);
    }
    this.currentSession.recentFeedback.push(feedbackWithTimestamp);

    // Adjust speaking style based on feedback
    const adjustedStyle = this.computeAdjustedStyle(feedbackWithTimestamp);

    await this.saveSession();
    return adjustedStyle;
  }

  async getFallbackResponse(topic: ConversationTopic): Promise<string> {
    // Get related verified topics
    const relatedTopics = await this.findRelatedVerifiedTopics(topic);
    
    if (relatedTopics.length > 0) {
      // Use related verified information
      const bestTopic = relatedTopics[0];
      return this.generateFallbackFromVerified(topic, bestTopic);
    } else {
      // Generate a generic response that maintains engagement
      return this.generateGenericFallback(topic);
    }
  }

  getCurrentContext(): ConversationTopic[] {
    if (!this.currentSession) return [];
    return this.currentSession.contextStack;
  }

  getRelevantMemories(topic: ConversationTopic): ConversationTopic[] {
    // Search both short and long-term memory for relevant topics
    const allMemories = [...this.memory.shortTerm, ...this.memory.longTerm];
    return allMemories
      .filter(memory => this.isTopicRelevant(memory, topic))
      .sort((a, b) => b.lastDiscussed - a.lastDiscussed);
  }

  private async processSessionInsights(): Promise<void> {
    if (!this.currentSession) return;

    // Update user preferences
    const sessionFeedback = this.currentSession.recentFeedback;
    if (sessionFeedback.length > 0) {
      const avgSentiment = sessionFeedback.reduce((sum, f) => sum + f.sentiment, 0) / sessionFeedback.length;
      const avgEngagement = sessionFeedback.reduce((sum, f) => sum + f.engagement, 0) / sessionFeedback.length;

      // Update favorite topics if engagement was high
      if (avgEngagement > 0.7 && this.currentSession.currentTopic) {
        this.memory.userPreferences.favoriteTopics.push(this.currentSession.currentTopic.id);
      }

      // Update preferred style based on positive feedback
      if (avgSentiment > 0.5) {
        this.memory.userPreferences.preferredStyle = {
          ...this.memory.userPreferences.preferredStyle,
          ...this.currentSession.personality.defaultStyle,
        };
      }
    }

    // Update interaction frequency
    const sessionDuration = (Date.now() - this.currentSession.startTime) / 1000 / 60; // in minutes
    this.memory.userPreferences.interactionFrequency = 
      this.currentSession.interactionCount / sessionDuration;

    // Move important topics to long-term memory
    const importantTopics = this.currentSession.contextStack.filter(topic => 
      this.isTopicImportant(topic)
    );
    this.memory.longTerm.push(...importantTopics);
    if (this.memory.longTerm.length > this.MAX_LONG_TERM_TOPICS) {
      this.memory.longTerm = this.memory.longTerm.slice(-this.MAX_LONG_TERM_TOPICS);
    }

    await this.saveMemory();
  }

  private isTopicImportant(topic: ConversationTopic): boolean {
    const feedback = topic.userFeedback;
    if (feedback.length === 0) return false;

    const avgEngagement = feedback.reduce((sum, f) => sum + f.engagement, 0) / feedback.length;
    const avgSentiment = feedback.reduce((sum, f) => sum + f.sentiment, 0) / feedback.length;

    return (
      avgEngagement > 0.7 || // High engagement
      avgSentiment > 0.7 || // Very positive feedback
      topic.verificationStatus === 'verified' || // Verified information
      topic.confidence > 0.9 // High confidence information
    );
  }

  private isTopicRelevant(memory: ConversationTopic, currentTopic: ConversationTopic): boolean {
    return (
      memory.relatedTopics.includes(currentTopic.id) ||
      currentTopic.relatedTopics.includes(memory.id) ||
      memory.type === currentTopic.type
    );
  }

  private computeAdjustedStyle(feedback: UserFeedback): SpeakingStyle {
    if (!this.currentSession) throw new Error('No active session');

    const baseStyle = this.currentSession.personality.defaultStyle;
    const recentFeedback = this.currentSession.recentFeedback.slice(-3);

    // Calculate average recent sentiment and engagement
    const avgSentiment = recentFeedback.reduce((sum, f) => sum + f.sentiment, 0) / recentFeedback.length;
    const avgEngagement = recentFeedback.reduce((sum, f) => sum + f.engagement, 0) / recentFeedback.length;
    const avgConfusion = recentFeedback.reduce((sum, f) => sum + f.confusion, 0) / recentFeedback.length;

    // Adjust style based on feedback
    const adjustedStyle: SpeakingStyle = {
      type: baseStyle.type,
      intensity: baseStyle.intensity,
      emotion: baseStyle.emotion ? { ...baseStyle.emotion } : undefined,
    };

    // Adjust based on sentiment
    if (avgSentiment < -this.SENTIMENT_THRESHOLD) {
      // If negative sentiment, increase empathy and reduce intensity
      adjustedStyle.intensity = Math.max(0.5, baseStyle.intensity - 0.2);
      adjustedStyle.emotion = {
        type: 'happiness',
        level: 0.6,
      };
    } else if (avgSentiment > this.SENTIMENT_THRESHOLD) {
      // If positive sentiment, maintain or increase enthusiasm
      adjustedStyle.intensity = Math.min(1, baseStyle.intensity + 0.1);
      adjustedStyle.emotion = {
        type: 'excitement',
        level: 0.8,
      };
    }

    // Adjust based on confusion
    if (avgConfusion > this.CONFUSION_THRESHOLD) {
      // If user seems confused, slow down and be more clear
      adjustedStyle.type = 'conversational';
      adjustedStyle.intensity = 0.6;
    }

    // Adjust based on engagement
    if (avgEngagement < 0.3) {
      // If low engagement, try to be more exciting
      adjustedStyle.type = 'excited';
      adjustedStyle.intensity = 0.8;
      adjustedStyle.emotion = {
        type: 'excitement',
        level: 0.9,
      };
    }

    return adjustedStyle;
  }

  private async findRelatedVerifiedTopics(topic: ConversationTopic): Promise<ConversationTopic[]> {
    const allTopics = [...this.memory.shortTerm, ...this.memory.longTerm];
    return allTopics
      .filter(t => 
        t.verificationStatus === 'verified' &&
        this.isTopicRelevant(t, topic)
      )
      .sort((a, b) => b.confidence - a.confidence);
  }

  private generateFallbackFromVerified(
    originalTopic: ConversationTopic,
    verifiedTopic: ConversationTopic
  ): string {
    const transitions = [
      "While I'm not entirely certain about that specific detail,",
      "That's an interesting point, and while I'm verifying those specifics,",
      "Let me share something related that I know for sure:",
    ];

    const transition = transitions[Math.floor(Math.random() * transitions.length)];
    return `${transition} ${verifiedTopic.content}`;
  }

  private generateGenericFallback(topic: ConversationTopic): string {
    const responses = [
      "That's an intriguing aspect I'd love to explore more. While I verify the details, what interests you most about it?",
      "I want to be certain about the information I share. Let's focus on what makes this particularly interesting to you.",
      "While I double-check those specifics, perhaps you could share your thoughts on this?",
    ];

    return responses[Math.floor(Math.random() * responses.length)];
  }

  private async loadMemory(): Promise<void> {
    const stored = await StorageManager.getItem<ConversationMemory>('@conversation_memory');
    if (stored) {
      this.memory = stored;
      // Clean up expired short-term memories
      const now = Date.now();
      this.memory.shortTerm = this.memory.shortTerm.filter(
        topic => now - topic.lastDiscussed < this.SHORT_TERM_MEMORY_DURATION
      );
    }
  }

  private async saveMemory(): Promise<void> {
    await StorageManager.setItem('@conversation_memory', this.memory);
  }

  private async loadSession(): Promise<void> {
    this.currentSession = await StorageManager.getItem<SessionState>('@current_session');
  }

  private async saveSession(): Promise<void> {
    if (this.currentSession) {
      await StorageManager.setItem('@current_session', this.currentSession);
    }
  }
}

export default new SessionManager(); 