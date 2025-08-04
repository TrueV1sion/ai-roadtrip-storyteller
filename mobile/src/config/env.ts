import Constants from 'expo-constants';

const ENV = {
  dev: {
    API_URL: 'http://localhost:8000/api/v1',
    ENVIRONMENT: 'development'
  },
  staging: {
    API_URL: 'https://staging-api.roadtrip.com/api/v1',
    ENVIRONMENT: 'staging'
  },
  prod: {
    API_URL: 'https://api.roadtrip.com/api/v1',
    ENVIRONMENT: 'production'
  }
};

const getEnvVars = (env = Constants.expoConfig?.extra?.ENVIRONMENT ?? 'dev') => {
  if (env === 'staging') return ENV.staging;
  if (env === 'prod') return ENV.prod;
  return ENV.dev;
};

export default getEnvVars();

// Environment variables configuration
// NOTE: All API keys should be handled by the backend proxy
// Never expose API keys in the mobile app
const extra = Constants.expoConfig?.extra || {};

// These should be empty - all TTS calls go through backend proxy
export const AZURE_TTS_KEY = ''; // Use backend proxy
export const AWS_POLLY_KEY = ''; // Use backend proxy 
export const GOOGLE_TTS_KEY = ''; // Use backend proxy 