import { APIClient } from '@utils/apiUtils';
import StorageManager from '@utils/storage';

import { logger } from '@/services/logger';
// Custom EventEmitter implementation
class EventEmitter {
  private listeners: Map<string, Array<(data: any) => void>> = new Map();

  emit(event: string, data: any): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.forEach(listener => listener(data));
    }
  }

  on(event: string, listener: (data: any) => void): void {
    const eventListeners = this.listeners.get(event) || [];
    eventListeners.push(listener);
    this.listeners.set(event, eventListeners);
  }

  off(event: string, listener: (data: any) => void): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      const index = eventListeners.indexOf(listener);
      if (index > -1) {
        eventListeners.splice(index, 1);
      }
    }
  }
}

interface RetryConfig {
  maxAttempts: number;
  baseDelay: number;
  maxDelay: number;
  retryableStatuses: number[];
}

interface APIConfig {
  name: string;
  baseURL: string;
  version: string;
  timeout: number;
  rateLimit: {
    maxRequests: number;
    windowMs: number;
    costPerRequest?: number;
  };
  fallback?: {
    service: string;
    endpoint: string;
  };
  cacheTTL?: number;  // in seconds
  retryConfig?: {
    maxAttempts: number;
    baseDelay: number;
    maxDelay: number;
    retryableStatuses: number[];
  };
}

interface APIUsage {
  service: string;
  endpoint: string;
  timestamp: number;
  cost: number;
  success: boolean;
  latency: number;
  cached: boolean;
}

interface APIQuota {
  service: string;
  dailyLimit: number;
  monthlyLimit: number;
  currentDailyUsage: number;
  currentMonthlyUsage: number;
  resetDate: number;
}

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

interface APIError extends Error {
  code: string;
  status?: number;
  retryable: boolean;
  service: string;
  endpoint: string;
  context?: unknown;
}

interface APIFeedback {
  type: 'success' | 'error' | 'warning' | 'info';
  service: string;
  endpoint: string;
  message: string;
  timestamp: number;
  context?: unknown;
  userAction?: string;
  resolution?: string;
}

interface APIHealthCheck {
  service: string;
  status: 'healthy' | 'degraded' | 'down';
  lastCheck: number;
  responseTime: number;
  errorRate: number;
  availableEndpoints: string[];
}

class APIManager {
  private clients: Map<string, APIClient> = new Map();
  private quotas: Map<string, APIQuota> = new Map();
  private usageHistory: APIUsage[] = [];
  private cache: Map<string, CacheEntry<unknown>> = new Map();
  private healthChecks: Map<string, APIHealthCheck> = new Map();
  private feedbackHistory: APIFeedback[] = [];
  private readonly ERROR_THRESHOLD = 0.1; // 10% error rate threshold
  private readonly HEALTH_CHECK_INTERVAL = 5 * 60 * 1000; // 5 minutes
  private eventEmitter = new EventEmitter();

  private readonly DEFAULT_RETRY_CONFIG: RetryConfig = {
    maxAttempts: 3,
    baseDelay: 1000,
    maxDelay: 10000,
    retryableStatuses: [408, 429, 500, 502, 503, 504],
  };

  constructor() {
    void this.initialize();
  }

  private async initialize(): Promise<void> {
    await this.loadQuotas();
    await this.loadUsageHistory();
    await this.loadFeedbackHistory();
    this.setupClients();
    this.startHealthChecks();
  }

  private setupClients(): void {
    // OpenAI Client
    this.registerAPI({
      name: 'openai',
      baseURL: 'https://api.openai.com/v1',
      version: '2024-02',
      timeout: 30000,
      rateLimit: {
        maxRequests: 100,
        windowMs: 60000,
        costPerRequest: 0.002,  // $0.002 per 1K tokens
      },
      fallback: {
        service: 'google-ai',  // Updated fallback to Google AI
        endpoint: '/generate',
      },
      cacheTTL: 3600,  // 1 hour
      retryConfig: {
        maxAttempts: 3,
        baseDelay: 1000,
        maxDelay: 10000,
        retryableStatuses: [408, 429, 500, 502, 503, 504],
      },
    });

    // Google AI Studio Client
    this.registerAPI({
      name: 'google-ai',
      baseURL: `https://${settings.GOOGLE_AI_LOCATION}-aiplatform.googleapis.com/v1/projects/${settings.GOOGLE_AI_PROJECT_ID}/locations/${settings.GOOGLE_AI_LOCATION}/publishers/google/models/${settings.GOOGLE_AI_MODEL}`,
      version: 'v1',
      timeout: 30000,
      rateLimit: {
        maxRequests: 100,
        windowMs: 60000,
        costPerRequest: 0.0005,  // $0.0005 per 1K tokens (Gemini Pro rate)
      },
      fallback: {
        service: 'anthropic',
        endpoint: '/complete',
      },
      cacheTTL: 3600,  // 1 hour
      retryConfig: {
        maxAttempts: 3,
        baseDelay: 1000,
        maxDelay: 10000,
        retryableStatuses: [408, 429, 500, 502, 503, 504],
      },
    });

    // Azure TTS Client
    this.registerAPI({
      name: 'azure-tts',
      baseURL: 'https://eastus.tts.speech.microsoft.com/cognitiveservices/v1',
      version: '1.0',
      timeout: 10000,
      rateLimit: {
        maxRequests: 100,
        windowMs: 60000,
        costPerRequest: 0.0004,  // $0.0004 per 1K characters
      },
      fallback: {
        service: 'google-tts',
        endpoint: '/synthesize',
      },
      cacheTTL: 86400,  // 24 hours
    });

    // Anthropic (Claude) Client - Fallback for OpenAI
    this.registerAPI({
      name: 'anthropic',
      baseURL: 'https://api.anthropic.com/v1',
      version: '2024-02',
      timeout: 30000,
      rateLimit: {
        maxRequests: 50,
        windowMs: 60000,
        costPerRequest: 0.003,
      },
    });

    // Google TTS Client - Fallback for Azure TTS
    this.registerAPI({
      name: 'google-tts',
      baseURL: 'https://texttospeech.googleapis.com/v1',
      version: 'v1',
      timeout: 10000,
      rateLimit: {
        maxRequests: 100,
        windowMs: 60000,
        costPerRequest: 0.0006,
      },
    });
  }

  registerAPI(config: APIConfig): void {
    const client = new APIClient({
      baseURL: config.baseURL,
      timeout: config.timeout,
      rateLimit: {
        maxRequests: config.rateLimit.maxRequests,
        windowMs: config.rateLimit.windowMs,
      },
      retry: {
        ...this.DEFAULT_RETRY_CONFIG,
        ...config.retryConfig,
      },
      headers: {
        'API-Version': config.version,
      },
    });

    this.clients.set(config.name, client);

    // Initialize quota tracking
    this.quotas.set(config.name, {
      service: config.name,
      dailyLimit: config.rateLimit.maxRequests * (86400000 / config.rateLimit.windowMs),
      monthlyLimit: config.rateLimit.maxRequests * (2592000000 / config.rateLimit.windowMs),
      currentDailyUsage: 0,
      currentMonthlyUsage: 0,
      resetDate: this.getNextResetDate(),
    });
  }

  async makeRequest<T>(
    service: string,
    endpoint: string,
    method: 'get' | 'post' | 'put' | 'delete',
    data?: unknown,
    options: {
      forceBypass?: boolean;
      priority?: 'high' | 'normal' | 'low';
      timeout?: number;
      retryStrategy?: 'aggressive' | 'conservative' | 'none';
    } = {}
  ): Promise<T> {
    const client = this.clients.get(service);
    if (!client) {
      await this.recordFeedback({
        type: 'error',
        service,
        endpoint,
        message: `Service ${service} not registered`,
        timestamp: Date.now(),
      });
      throw new Error(`Service ${service} not registered`);
    }

    const startTime = Date.now();
    const cacheKey = this.generateCacheKey(service, endpoint, method, data);

    try {
      // Check service health
      const health = await this.checkServiceHealth(service);
      if (health.status === 'down') {
        return this.handleServiceDown<T>(service, endpoint, method, data, options);
      }

      // Apply retry strategy
      const retryConfig = this.getRetryConfig(service, options.retryStrategy);

      // Check cache if not forcing bypass
      if (!options.forceBypass) {
        const cached = await this.getCached<T>(cacheKey);
        if (cached) {
          await this.trackUsage({
            service,
            endpoint,
            timestamp: startTime,
            cost: 0,
            success: true,
            latency: 0,
            cached: true,
          });
          return cached;
        }
      }

      // Check and enforce quotas
      await this.checkQuota(service);

      // Make request with timeout and priority
      const response = await this.makeAPIRequest<T>(
        client,
        method,
        endpoint,
        data,
        {
          timeout: options.timeout,
          priority: options.priority,
          retryConfig,
        }
      );

      // Cache response if applicable
      await this.cacheResponse(service, cacheKey, response);

      // Track successful usage
      await this.trackUsage({
        service,
        endpoint,
        timestamp: startTime,
        cost: this.calculateCost(service, response),
        success: true,
        latency: Date.now() - startTime,
        cached: false,
      });

      // Record positive feedback
      await this.recordFeedback({
        type: 'success',
        service,
        endpoint,
        message: 'Request completed successfully',
        timestamp: Date.now(),
        context: { latency: Date.now() - startTime },
      });

      return response;
    } catch (error) {
      const apiError = this.normalizeError(error, service, endpoint);
      
      // Record error feedback
      await this.recordFeedback({
        type: 'error',
        service,
        endpoint,
        message: apiError.message,
        timestamp: Date.now(),
        context: apiError.context,
      });

      // Update service health
      await this.updateServiceHealth(service, false);

      // Handle error and try fallback if available
      const fallbackResponse = await this.handleErrorAndFallback<T>(
        service,
        endpoint,
        method,
        data,
        apiError,
        options
      );

      if (fallbackResponse) {
        return fallbackResponse;
      }

      throw apiError;
    }
  }

  private async makeAPIRequest<T>(
    client: APIClient,
    method: string,
    endpoint: string,
    data?: unknown,
    options?: {
      timeout?: number;
      priority?: 'high' | 'normal' | 'low';
      retryConfig?: RetryConfig;
    }
  ): Promise<T> {
    const config = {
      timeout: options?.timeout,
      headers: options?.priority ? { 'X-Priority': options.priority } : undefined,
      retry: options?.retryConfig,
    };

    switch (method) {
      case 'get':
        return client.get<T>(endpoint, config);
      case 'post':
        return client.post<T>(endpoint, data, config);
      case 'put':
        return client.put<T>(endpoint, data, config);
      case 'delete':
        return client.delete<T>(endpoint, config);
      default:
        throw new Error(`Unsupported method: ${method}`);
    }
  }

  private async handleServiceDown<T>(
    service: string,
    endpoint: string,
    method: string,
    data: unknown,
    options: Record<string, unknown>
  ): Promise<T> {
    // Try fallback immediately if service is down
    const config = this.getAPIConfig(service);
    if (config?.fallback) {
      return this.makeRequest<T>(
        config.fallback.service,
        config.fallback.endpoint,
        method as 'get' | 'post' | 'put' | 'delete',
        data,
        { ...options, forceBypass: true }
      );
    }

    throw new Error(`Service ${service} is down and no fallback is available`);
  }

  private normalizeError(
    error: unknown,
    service: string,
    endpoint: string
  ): APIError {
    const apiError: APIError = {
      name: 'APIError',
      message: error instanceof Error ? error.message : 'Unknown error occurred',
      code: 'UNKNOWN_ERROR',
      retryable: false,
      service,
      endpoint,
    };

    if (error instanceof Error) {
      apiError.code = this.getErrorCode(error);
      apiError.retryable = this.isRetryableError(error);
      apiError.status = this.getErrorStatus(error);
      apiError.context = error;
    }

    return apiError;
  }

  private getErrorCode(error: Error): string {
    // Implement error code mapping logic
    return 'UNKNOWN_ERROR';
  }

  private isRetryableError(error: Error): boolean {
    // Implement retry decision logic
    return false;
  }

  private getErrorStatus(error: Error): number | undefined {
    // Implement status code extraction logic
    return undefined;
  }

  private async checkServiceHealth(service: string): Promise<APIHealthCheck> {
    const health = this.healthChecks.get(service);
    if (!health) {
      return this.initializeHealthCheck(service);
    }
    return health;
  }

  private async updateServiceHealth(
    service: string,
    success: boolean,
    responseTime?: number
  ): Promise<void> {
    const health = await this.checkServiceHealth(service);
    const usage = this.usageHistory.filter(u => 
      u.service === service &&
      u.timestamp > Date.now() - this.HEALTH_CHECK_INTERVAL
    );

    const errorRate = usage.length > 0 
      ? usage.filter(u => !u.success).length / usage.length
      : 0;

    health.status = this.determineHealthStatus(errorRate);
    health.lastCheck = Date.now();
    if (responseTime) {
      health.responseTime = responseTime;
    }
    health.errorRate = errorRate;

    this.healthChecks.set(service, health);
    this.eventEmitter.emit('healthUpdate', health);
  }

  private determineHealthStatus(errorRate: number): 'healthy' | 'degraded' | 'down' {
    if (errorRate >= this.ERROR_THRESHOLD * 2) return 'down';
    if (errorRate >= this.ERROR_THRESHOLD) return 'degraded';
    return 'healthy';
  }

  private initializeHealthCheck(service: string): APIHealthCheck {
    const health: APIHealthCheck = {
      service,
      status: 'healthy',
      lastCheck: Date.now(),
      responseTime: 0,
      errorRate: 0,
      availableEndpoints: [],
    };
    this.healthChecks.set(service, health);
    return health;
  }

  private startHealthChecks(): void {
    setInterval(() => {
      Array.from(this.clients.keys()).forEach(service => {
        void this.performHealthCheck(service);
      });
    }, this.HEALTH_CHECK_INTERVAL);
  }

  private async performHealthCheck(service: string): Promise<void> {
    try {
      const startTime = Date.now();
      const config = this.getAPIConfig(service);
      if (!config) return;

      await this.makeRequest(
        service,
        '/health',
        'get',
        undefined,
        { priority: 'low', retryStrategy: 'none' }
      );

      await this.updateServiceHealth(service, true, Date.now() - startTime);
    } catch (error) {
      await this.updateServiceHealth(service, false);
    }
  }

  private async recordFeedback(feedback: APIFeedback): Promise<void> {
    this.feedbackHistory.push(feedback);
    this.eventEmitter.emit('feedback', feedback);
    await this.saveFeedbackHistory();

    // Clean up old feedback
    const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
    this.feedbackHistory = this.feedbackHistory.filter(
      f => f.timestamp >= thirtyDaysAgo
    );
  }

  private async loadFeedbackHistory(): Promise<void> {
    const stored = await StorageManager.getItem<APIFeedback[]>('@api_feedback');
    if (stored) {
      this.feedbackHistory = stored;
    }
  }

  private async saveFeedbackHistory(): Promise<void> {
    await StorageManager.setItem('@api_feedback', this.feedbackHistory);
  }

  // Analytics and Monitoring
  getServiceHealth(service: string): APIHealthCheck | undefined {
    return this.healthChecks.get(service);
  }

  getFeedbackStats(service: string): {
    totalFeedback: number;
    errorRate: number;
    commonIssues: Array<{ message: string; count: number }>;
    averageResponseTime: number;
    userActions: Array<{ action: string; count: number }>;
  } {
    const feedback = this.feedbackHistory.filter(f => f.service === service);
    const total = feedback.length;
    if (total === 0) {
      return {
        totalFeedback: 0,
        errorRate: 0,
        commonIssues: [],
        averageResponseTime: 0,
        userActions: [],
      };
    }

    const errors = feedback.filter(f => f.type === 'error');
    const issues = this.aggregateCommonIssues(errors);
    const actions = this.aggregateUserActions(feedback);
    const responseTime = this.calculateAverageResponseTime(feedback);

    return {
      totalFeedback: total,
      errorRate: errors.length / total,
      commonIssues: issues,
      averageResponseTime: responseTime,
      userActions: actions,
    };
  }

  private aggregateCommonIssues(errors: APIFeedback[]): Array<{ message: string; count: number }> {
    const issues = new Map<string, number>();
    for (const error of errors) {
      const count = issues.get(error.message) || 0;
      issues.set(error.message, count + 1);
    }
    return Array.from(issues.entries())
      .map(([message, count]) => ({ message, count }))
      .sort((a, b) => b.count - a.count);
  }

  private aggregateUserActions(feedback: APIFeedback[]): Array<{ action: string; count: number }> {
    const actions = new Map<string, number>();
    for (const f of feedback) {
      if (f.userAction) {
        const count = actions.get(f.userAction) || 0;
        actions.set(f.userAction, count + 1);
      }
    }
    return Array.from(actions.entries())
      .map(([action, count]) => ({ action, count }))
      .sort((a, b) => b.count - a.count);
  }

  private calculateAverageResponseTime(feedback: APIFeedback[]): number {
    const responseTimes = feedback
      .map(f => (f.context as { latency?: number })?.latency || 0)
      .filter(t => t > 0);
    if (responseTimes.length === 0) return 0;
    return responseTimes.reduce((sum, t) => sum + t, 0) / responseTimes.length;
  }

  private async checkQuota(service: string): Promise<void> {
    const quota = this.quotas.get(service);
    if (!quota) return;

    // Reset if needed
    if (Date.now() >= quota.resetDate) {
      quota.currentDailyUsage = 0;
      quota.currentMonthlyUsage = 0;
      quota.resetDate = this.getNextResetDate();
      await this.saveQuotas();
    }

    // Check limits
    if (quota.currentDailyUsage >= quota.dailyLimit) {
      throw new Error(`Daily quota exceeded for ${service}`);
    }
    if (quota.currentMonthlyUsage >= quota.monthlyLimit) {
      throw new Error(`Monthly quota exceeded for ${service}`);
    }
  }

  private async trackUsage(usage: APIUsage): Promise<void> {
    this.usageHistory.push(usage);
    
    // Update quotas
    const quota = this.quotas.get(usage.service);
    if (quota && usage.success) {
      quota.currentDailyUsage++;
      quota.currentMonthlyUsage++;
      await this.saveQuotas();
    }

    // Trim history to last 30 days
    const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
    this.usageHistory = this.usageHistory.filter(u => u.timestamp >= thirtyDaysAgo);
    
    await this.saveUsageHistory();
  }

  private calculateCost(service: string, response: unknown): number {
    const config = this.getAPIConfig(service);
    if (!config?.rateLimit.costPerRequest) return 0;

    // Implement service-specific cost calculation
    // For example, for OpenAI, calculate based on token count
    return config.rateLimit.costPerRequest;
  }

  private async getCached<T>(key: string): Promise<T | null> {
    const cached = this.cache.get(key);
    if (!cached) return null;

    if (Date.now() - cached.timestamp > cached.ttl * 1000) {
      this.cache.delete(key);
      return null;
    }

    return cached.data as T;
  }

  private async cacheResponse<T>(
    service: string,
    key: string,
    data: T
  ): Promise<void> {
    const config = this.getAPIConfig(service);
    if (!config?.cacheTTL) return;

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl: config.cacheTTL,
    });
  }

  getAPIConfig(service: string): APIConfig | undefined {
    // Implementation to get API config
    return undefined;
  }

  private generateCacheKey(
    service: string,
    endpoint: string,
    method: string,
    data?: unknown
  ): string {
    return `${service}:${endpoint}:${method}:${JSON.stringify(data)}`;
  }

  private getNextResetDate(): number {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth() + 1, 1).getTime();
  }

  private async loadQuotas(): Promise<void> {
    const stored = await StorageManager.getItem<Map<string, APIQuota>>('@api_quotas');
    if (stored) {
      this.quotas = stored;
    }
  }

  private async saveQuotas(): Promise<void> {
    await StorageManager.setItem('@api_quotas', this.quotas);
  }

  private async loadUsageHistory(): Promise<void> {
    const stored = await StorageManager.getItem<APIUsage[]>('@api_usage');
    if (stored) {
      this.usageHistory = stored;
    }
  }

  private async saveUsageHistory(): Promise<void> {
    await StorageManager.setItem('@api_usage', this.usageHistory);
  }

  private getRetryConfig(
    service: string,
    strategy?: 'aggressive' | 'conservative' | 'none'
  ): RetryConfig {
    const baseConfig = this.DEFAULT_RETRY_CONFIG;
    
    if (strategy === 'none') {
      return {
        ...baseConfig,
        maxAttempts: 1,
        retryableStatuses: [],
      };
    }

    if (strategy === 'aggressive') {
      return {
        ...baseConfig,
        maxAttempts: 5,
        baseDelay: 500,
        retryableStatuses: [408, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
      };
    }

    return baseConfig;
  }

  private async handleErrorAndFallback<T>(
    service: string,
    endpoint: string,
    method: string,
    data: unknown,
    error: APIError,
    options: Record<string, unknown>
  ): Promise<T | null> {
    // Track failed request
    await this.trackUsage({
      service,
      endpoint,
      timestamp: Date.now(),
      cost: 0,
      success: false,
      latency: 0,
      cached: false,
    });

    // Check if fallback is available
    const config = this.getAPIConfig(service);
    if (!config?.fallback) {
      return null;
    }

    try {
      // Try fallback service
      return await this.makeRequest<T>(
        config.fallback.service,
        config.fallback.endpoint,
        method as 'get' | 'post' | 'put' | 'delete',
        data,
        { ...options, forceBypass: true }
      );
    } catch (fallbackError) {
      logger.error('Fallback request failed:', fallbackError);
      return null;
    }
  }
}

export default new APIManager(); 