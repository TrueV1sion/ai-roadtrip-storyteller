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
const extra = Constants.expoConfig?.extra || {};

export const AZURE_TTS_KEY = extra.AZURE_TTS_KEY as string || '';
export const AWS_POLLY_KEY = extra.AWS_POLLY_KEY as string || '';
export const GOOGLE_TTS_KEY = extra.GOOGLE_TTS_KEY as string || ''; 