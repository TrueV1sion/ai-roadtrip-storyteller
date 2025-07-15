declare module 'axios' {
  interface AxiosRequestConfig {
    headers?: Record<string, string>;
    params?: Record<string, any>;
    timeout?: number;
  }

  interface AxiosResponse<T = any> {
    data: T;
    status: number;
    statusText: string;
    headers: Record<string, string>;
    config: AxiosRequestConfig;
  }

  interface AxiosInterceptorManager<V> {
    use(
      onFulfilled?: (value: V) => V | Promise<V>,
      onRejected?: (error: any) => any
    ): number;
    eject(id: number): void;
  }

  interface AxiosInstance {
    get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>;
    post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>;
    put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>;
    delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>;
    interceptors: {
      request: AxiosInterceptorManager<AxiosRequestConfig>;
      response: AxiosInterceptorManager<AxiosResponse>;
    };
  }

  interface AxiosStatic {
    create(config?: AxiosRequestConfig): AxiosInstance;
  }

  const axios: AxiosStatic;
  export default axios;
  export { 
    AxiosInstance,
    AxiosRequestConfig,
    AxiosResponse,
    AxiosInterceptorManager
  };
}

declare module '@react-native-async-storage/async-storage' {
  export * from '@react-native-async-storage/async-storage';
}

declare module 'expo-location' {
  export * from 'expo-location';
}

declare module 'expo-speech' {
  export * from 'expo-speech';
}

declare module 'react-native-vector-icons/*' {
  import { Component } from 'react';
  export default Component;
}

// Environment variables
declare module '@env' {
  export const EXPO_PUBLIC_CULTURAL_API_KEY: string;
  export const EXPO_PUBLIC_WIKIPEDIA_API_KEY: string;
} 