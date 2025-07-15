import axios, { AxiosError } from 'axios';
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { sleep } from './async';

export class APIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string,
    public retryable?: boolean
  ) {
    super(message);
    this.name = 'APIError';
  }
}

interface RateLimitConfig {
  maxRequests: number;
  windowMs: number;
  retryAfterHeader?: string;
}

interface RetryConfig {
  maxAttempts: number;
  baseDelay: number;
  maxDelay: number;
  retryableStatuses: number[];
}

interface APIClientConfig {
  baseURL?: string;
  timeout?: number;
  rateLimit?: RateLimitConfig;
  retry?: RetryConfig;
  headers?: Record<string, string>;
}

export class APIClient {
  private axios: AxiosInstance;
  private rateLimit: RateLimitConfig;
  private retry: RetryConfig;
  private requestCount: number = 0;
  private windowStart: number = Date.now();
  private headers: Record<string, string> = {};

  constructor(config: APIClientConfig) {
    this.axios = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout || 10000,
      headers: config.headers || {},
    } as AxiosRequestConfig);

    this.rateLimit = {
      maxRequests: config.rateLimit?.maxRequests || 100,
      windowMs: config.rateLimit?.windowMs || 60000,
      retryAfterHeader: config.rateLimit?.retryAfterHeader || 'Retry-After',
    };

    this.retry = {
      maxAttempts: config.retry?.maxAttempts || 3,
      baseDelay: config.retry?.baseDelay || 1000,
      maxDelay: config.retry?.maxDelay || 10000,
      retryableStatuses: config.retry?.retryableStatuses || [408, 429, 500, 502, 503, 504],
    };

    this.setupInterceptors();
  }

  setHeaders(headers: Record<string, string>): void {
    this.headers = { ...this.headers, ...headers };
    this.axios.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      config.headers = { ...config.headers, ...this.headers };
      return config;
    });
  }

  private setupInterceptors(): void {
    // Request interceptor for rate limiting
    this.axios.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
      await this.checkRateLimit();
      config.headers = { ...config.headers, ...this.headers };
      return config;
    });

    // Response interceptor for error handling
    this.axios.interceptors.response.use(
      (response) => {
        this.updateRateLimitFromHeaders(response.headers);
        return response;
      },
      (error: unknown) => {
        if (error instanceof AxiosError) {
          throw this.enhanceError(error);
        }
        throw error;
      }
    );
  }

  private async checkRateLimit(): Promise<void> {
    const now = Date.now();
    if (now - this.windowStart >= this.rateLimit.windowMs) {
      this.requestCount = 0;
      this.windowStart = now;
    }

    if (this.requestCount >= this.rateLimit.maxRequests) {
      const waitTime = this.windowStart + this.rateLimit.windowMs - now;
      await sleep(waitTime);
      this.requestCount = 0;
      this.windowStart = Date.now();
    }

    this.requestCount++;
  }

  private updateRateLimitFromHeaders(headers: Record<string, string>): void {
    const remaining = headers['x-ratelimit-remaining'];
    const reset = headers['x-ratelimit-reset'];
    const retryAfter = headers[this.rateLimit.retryAfterHeader.toLowerCase()];

    if (remaining) {
      this.requestCount = this.rateLimit.maxRequests - parseInt(remaining, 10);
    }

    if (reset) {
      this.windowStart = parseInt(reset, 10) * 1000;
    }

    if (retryAfter) {
      this.rateLimit.windowMs = parseInt(retryAfter, 10) * 1000;
    }
  }

  private enhanceError(error: AxiosError): APIError {
    const statusCode = error.response?.status;
    const data = error.response?.data as Record<string, unknown>;

    return new APIError(
      (data?.message as string) || error.message,
      statusCode,
      (data?.code as string) || error.code,
      this.retry.retryableStatuses.includes(statusCode || 0)
    );
  }

  private async executeWithRetry<T>(
    operation: () => Promise<T>,
    customConfig?: Partial<RetryConfig>
  ): Promise<T> {
    const config = { ...this.retry, ...customConfig };
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= config.maxAttempts; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        
        if (
          error instanceof APIError &&
          (!error.retryable || attempt === config.maxAttempts)
        ) {
          throw error;
        }

        const delay = Math.min(
          config.baseDelay * Math.pow(2, attempt - 1),
          config.maxDelay
        );
        await sleep(delay);
      }
    }

    throw lastError;
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return this.executeWithRetry(() => 
      this.axios.get<T>(url, config).then((response) => response.data)
    );
  }

  async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return this.executeWithRetry(() =>
      this.axios.post<T>(url, data, config).then((response) => response.data)
    );
  }

  async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return this.executeWithRetry(() =>
      this.axios.put<T>(url, data, config).then((response) => response.data)
    );
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return this.executeWithRetry(() =>
      this.axios.delete<T>(url, config).then((response) => response.data)
    );
  }
} 