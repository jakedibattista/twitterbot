"""Configuration management for Twitter DM organizer.

Handles environment variables, validation, and application settings
using Pydantic for robust configuration management.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with validation and environment variable support."""
    
    # X API Configuration
    x_api_key: str = Field(..., description="X API consumer key")
    x_api_secret: str = Field(..., description="X API consumer secret")
    x_access_token: str = Field(..., description="X API access token")
    x_access_token_secret: str = Field(..., description="X API access token secret")
    
    # Google Sheets Configuration
    google_sheets_credentials_path: Path = Field(
        default=Path("config/service_account.json"),
        description="Path to Google service account JSON file"
    )
    google_sheets_id: str = Field(..., description="Target Google Sheet ID")
    
    # Optional AI Summarization
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for conversation summarization"
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use for summarization"
    )
    
    # Optional LinkedIn Discovery
    google_ai_api_key: Optional[str] = Field(
        default=None,
        alias="google_api_key",  # Allow both GOOGLE_API_KEY and GOOGLE_AI_API_KEY
        description="Google AI API key for LinkedIn profile discovery"
    )
    # Optional Google Programmable Search (CSE) for reliable web results
    google_cse_api_key: Optional[str] = Field(
        default=None,
        description="Google Programmable Search API key (Custom Search JSON API)"
    )
    google_cse_cx: Optional[str] = Field(
        default=None,
        description="Google Programmable Search Engine ID (cx)"
    )
    
    # Application Settings
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment name")
    max_requests_per_window: int = Field(
        default=280,  # Leave some buffer under the 300 limit
        description="Maximum X API requests per 15-minute window"
    )
    
    class Config:
        env_file = ".env"
        env_prefix = ""
        case_sensitive = False
        
    def validate_x_credentials(self) -> bool:
        """Validate that all required X API credentials are present."""
        required_fields = [
            self.x_api_key,
            self.x_api_secret, 
            self.x_access_token,
            self.x_access_token_secret
        ]
        return all(field for field in required_fields)
    
    def validate_google_credentials(self) -> bool:
        """Validate that Google Sheets credentials file exists."""
        return (
            self.google_sheets_credentials_path.exists() 
            and self.google_sheets_id
        )


# Global settings instance
settings = Settings()


