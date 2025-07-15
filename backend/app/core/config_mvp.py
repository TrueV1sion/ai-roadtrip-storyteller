"""Minimal configuration for MVP"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Basic app config
    APP_TITLE: str = "AI Road Trip Storyteller MVP"
    APP_DESCRIPTION: str = "Voice navigation and storytelling MVP"
    APP_VERSION: str = "1.0.0-mvp"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # API Keys from environment
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    # Google Cloud
    GOOGLE_AI_PROJECT_ID: str = os.getenv("GOOGLE_AI_PROJECT_ID", "")
    GOOGLE_AI_LOCATION: str = os.getenv("GOOGLE_AI_LOCATION", "us-central1")
    GOOGLE_AI_MODEL: str = os.getenv("GOOGLE_AI_MODEL", "gemini-1.5-flash")
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "")
    
    # Database URL (optional for MVP)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./mvp.db")
    
    # Redis URL (optional for MVP)
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"


settings = Settings()