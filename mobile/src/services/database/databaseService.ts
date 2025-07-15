import AsyncStorage from '@react-native-async-storage/async-storage';
import { APIClient } from '@utils/apiUtils';
import { Story } from '@/types/cultural';
import { ConversationTopic, UserFeedback } from '../voice/sessionManager';

interface SyncMetadata {
  lastSyncTimestamp: number;
  deviceId: string;
  version: number;
  conflictResolution?: 'server-wins' | 'client-wins' | 'manual';
}

interface SyncOperation {
  id: string;
  type: 'create' | 'update' | 'delete';
  collection: string;
  documentId: string;
  data: unknown;
  timestamp: number;
  deviceId: string;
  version: number;
  status: 'pending' | 'completed' | 'failed' | 'conflict';
}

interface DatabaseConfig {
  serverUrl: string;
  syncInterval: number;  // in milliseconds
  maxRetries: number;
  conflictResolution: 'server-wins' | 'client-wins' | 'manual';
}

type Timer = ReturnType<typeof setInterval>;

class DatabaseService {
  private readonly apiClient: APIClient;
  private readonly config: DatabaseConfig;
  private syncQueue: SyncOperation[] = [];
  private isOnline: boolean = true;
  private syncInterval: Timer | null = null;
  private metadata: SyncMetadata;

  constructor(config: DatabaseConfig) {
    this.config = config;
    this.apiClient = new APIClient({
      baseURL: config.serverUrl,
      timeout: 10000,
      retry: {
        maxAttempts: config.maxRetries,
        baseDelay: 1000,
        maxDelay: 10000,
        retryableStatuses: [408, 429, 500, 502, 503, 504],
      },
    });

    this.metadata = {
      lastSyncTimestamp: 0,
      deviceId: this.generateDeviceId(),
      version: 1,
      conflictResolution: config.conflictResolution,
    };

    void this.initialize();
  }

  private async initialize(): Promise<void> {
    await this.loadMetadata();
    await this.loadSyncQueue();
    this.startSync();
    this.setupConnectivityListener();
  }

  // Story Operations
  async saveStory(story: Story): Promise<void> {
    try {
      // Save locally first
      await AsyncStorage.setItem(`@story_${story.id}`, JSON.stringify(story));

      // Queue sync operation
      await this.queueSyncOperation({
        id: crypto.randomUUID(),
        type: 'create',
        collection: 'stories',
        documentId: story.id,
        data: story,
        timestamp: Date.now(),
        deviceId: this.metadata.deviceId,
        version: this.metadata.version,
        status: 'pending',
      });
    } catch (error) {
      console.error('Failed to save story:', error);
      throw error;
    }
  }

  async getStory(id: string): Promise<Story | null> {
    try {
      const localStory = await AsyncStorage.getItem(`@story_${id}`);
      if (localStory) {
        return JSON.parse(localStory);
      }

      // If not found locally and online, fetch from server
      if (this.isOnline) {
        const story = await this.apiClient.get<Story>(`/stories/${id}`);
        await AsyncStorage.setItem(`@story_${id}`, JSON.stringify(story));
        return story;
      }

      return null;
    } catch (error) {
      console.error('Failed to get story:', error);
      return null;
    }
  }

  // Conversation Topic Operations
  async saveConversationTopic(topic: ConversationTopic): Promise<void> {
    try {
      await AsyncStorage.setItem(`@topic_${topic.id}`, JSON.stringify(topic));
      await this.queueSyncOperation({
        id: crypto.randomUUID(),
        type: 'create',
        collection: 'conversation_topics',
        documentId: topic.id,
        data: topic,
        timestamp: Date.now(),
        deviceId: this.metadata.deviceId,
        version: this.metadata.version,
        status: 'pending',
      });
    } catch (error) {
      console.error('Failed to save conversation topic:', error);
      throw error;
    }
  }

  async getConversationTopic(id: string): Promise<ConversationTopic | null> {
    try {
      const localTopic = await AsyncStorage.getItem(`@topic_${id}`);
      if (localTopic) {
        return JSON.parse(localTopic);
      }

      if (this.isOnline) {
        const topic = await this.apiClient.get<ConversationTopic>(`/conversation_topics/${id}`);
        await AsyncStorage.setItem(`@topic_${id}`, JSON.stringify(topic));
        return topic;
      }

      return null;
    } catch (error) {
      console.error('Failed to get conversation topic:', error);
      return null;
    }
  }

  // User Feedback Operations
  async saveUserFeedback(feedback: UserFeedback & { id: string }): Promise<void> {
    try {
      await AsyncStorage.setItem(`@feedback_${feedback.id}`, JSON.stringify(feedback));
      await this.queueSyncOperation({
        id: crypto.randomUUID(),
        type: 'create',
        collection: 'user_feedback',
        documentId: feedback.id,
        data: feedback,
        timestamp: Date.now(),
        deviceId: this.metadata.deviceId,
        version: this.metadata.version,
        status: 'pending',
      });
    } catch (error) {
      console.error('Failed to save user feedback:', error);
      throw error;
    }
  }

  // Sync Operations
  private async queueSyncOperation(operation: SyncOperation): Promise<void> {
    this.syncQueue.push(operation);
    await AsyncStorage.setItem('@sync_queue', JSON.stringify(this.syncQueue));

    if (this.isOnline) {
      void this.processSyncQueue();
    }
  }

  private async processSyncQueue(): Promise<void> {
    if (!this.isOnline || this.syncQueue.length === 0) return;

    const operation = this.syncQueue[0];
    try {
      switch (operation.type) {
        case 'create':
          await this.apiClient.post(`/${operation.collection}`, operation.data);
          break;
        case 'update':
          await this.apiClient.put(
            `/${operation.collection}/${operation.documentId}`,
            operation.data
          );
          break;
        case 'delete':
          await this.apiClient.delete(`/${operation.collection}/${operation.documentId}`);
          break;
      }

      // Operation successful, remove from queue
      this.syncQueue.shift();
      await AsyncStorage.setItem('@sync_queue', JSON.stringify(this.syncQueue));
    } catch (error) {
      if (this.isConflictError(error)) {
        await this.handleConflict(operation);
      } else {
        console.error('Sync operation failed:', error);
        operation.status = 'failed';
        await AsyncStorage.setItem('@sync_queue', JSON.stringify(this.syncQueue));
      }
    }
  }

  private async handleConflict(operation: SyncOperation): Promise<void> {
    operation.status = 'conflict';

    switch (this.config.conflictResolution) {
      case 'server-wins':
        // Fetch server version and update local
        const serverData = await this.apiClient.get(
          `/${operation.collection}/${operation.documentId}`
        );
        await AsyncStorage.setItem(
          `@${operation.collection}_${operation.documentId}`,
          JSON.stringify(serverData)
        );
        this.syncQueue.shift(); // Remove conflicting operation
        break;

      case 'client-wins':
        // Force update server with client version
        await this.apiClient.put(
          `/${operation.collection}/${operation.documentId}`,
          operation.data,
          { headers: { 'Force-Update': 'true' } }
        );
        this.syncQueue.shift();
        break;

      case 'manual':
        // Store both versions and let UI handle resolution
        const conflict = {
          serverVersion: await this.apiClient.get(
            `/${operation.collection}/${operation.documentId}`
          ),
          clientVersion: operation.data,
          operationId: operation.id,
        };
        await AsyncStorage.setItem(
          `@conflict_${operation.id}`,
          JSON.stringify(conflict)
        );
        break;
    }

    await AsyncStorage.setItem('@sync_queue', JSON.stringify(this.syncQueue));
  }

  // Manual conflict resolution
  async resolveConflict(operationId: string, resolvedData: unknown): Promise<void> {
    const operation = this.syncQueue.find(op => op.id === operationId);
    if (!operation) return;

    try {
      await this.apiClient.put(
        `/${operation.collection}/${operation.documentId}`,
        resolvedData,
        { headers: { 'Force-Update': 'true' } }
      );

      // Update local data
      await AsyncStorage.setItem(
        `@${operation.collection}_${operation.documentId}`,
        JSON.stringify(resolvedData)
      );

      // Remove conflict and operation
      await AsyncStorage.removeItem(`@conflict_${operationId}`);
      this.syncQueue = this.syncQueue.filter(op => op.id !== operationId);
      await AsyncStorage.setItem('@sync_queue', JSON.stringify(this.syncQueue));
    } catch (error) {
      console.error('Failed to resolve conflict:', error);
      throw error;
    }
  }

  // Utility functions
  private startSync(): void {
    this.syncInterval = setInterval(
      () => void this.processSyncQueue(),
      this.config.syncInterval
    );
  }

  private stopSync(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  private setupConnectivityListener(): void {
    // Implementation depends on the platform (React Native NetInfo)
    // Add listeners for online/offline status
  }

  private async loadMetadata(): Promise<void> {
    const stored = await AsyncStorage.getItem('@sync_metadata');
    if (stored) {
      this.metadata = JSON.parse(stored);
    }
  }

  private async loadSyncQueue(): Promise<void> {
    const stored = await AsyncStorage.getItem('@sync_queue');
    if (stored) {
      this.syncQueue = JSON.parse(stored);
    }
  }

  private generateDeviceId(): string {
    // Implementation depends on the platform
    // Should generate a unique, persistent device identifier
    return 'device-id';
  }

  private isConflictError(error: unknown): boolean {
    return (
      error instanceof Error &&
      'statusCode' in error &&
      (error as { statusCode: number }).statusCode === 409
    );
  }
}

// Export singleton instance with default config
export default new DatabaseService({
  serverUrl: process.env.EXPO_PUBLIC_API_URL || 'https://api.roadtrip.com',
  syncInterval: 5 * 60 * 1000, // 5 minutes
  maxRetries: 3,
  conflictResolution: 'server-wins',
}); 