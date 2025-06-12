"""
Configuration Management
Centralized configuration for the clean architecture application
"""

import os
from typing import List, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application settings
    APP_NAME: str = Field(
        default="Clean Architecture API", description="Application name"
    )
    APP_VERSION: str = Field(default="2.0.0", description="Application version")
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    DEBUG: bool = Field(default=True, description="Debug mode")

    # Server settings
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    RELOAD: bool = Field(default=True, description="Auto reload")

    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )

    # JWT/Authentication settings
    APIM_ONELOGIN_URL: Optional[str] = Field(
        default=None, description="OneLogin JWKS URL for JWT validation"
    )
    JWT_ALGORITHMS: List[str] = Field(default=["RS256"], description="JWT algorithms")
    JWT_AUDIENCE: Optional[str] = Field(default=None, description="JWT audience claim")
    JWT_ISSUER: Optional[str] = Field(default=None, description="JWT issuer claim")

    # External services
    AZURE_SEARCH_ENDPOINT: Optional[str] = Field(
        default=None, description="Azure Search endpoint"
    )
    AZURE_SEARCH_API_KEY: Optional[str] = Field(
        default=None, description="Azure Search API key"
    )
    AZURE_SEARCH_INDEX: Optional[str] = Field(
        default=None, description="Azure Search index name"
    )

    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4", description="OpenAI model name")
    OPENAI_BASE_URL: str = Field(
        default="https://api.openai.com/v1", description="OpenAI base URL"
    )

    # CORS settings
    CORS_ORIGINS: List[str] = Field(default=["*"], description="CORS allowed origins")
    CORS_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE"], description="CORS allowed methods"
    )
    CORS_HEADERS: List[str] = Field(default=["*"], description="CORS allowed headers")

    # Health check settings
    HEALTH_CHECK_TIMEOUT: int = Field(
        default=5, description="Health check timeout seconds"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True

    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT.lower() in ["development", "dev", "local"]

    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT.lower() in ["production", "prod"]

    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.ENVIRONMENT.lower() in ["testing", "test"]

    def get_jwt_config(self) -> dict:
        """Get JWT configuration as dictionary"""
        return {
            "jwks_url": self.APIM_ONELOGIN_URL,
            "algorithms": self.JWT_ALGORITHMS,
            "audience": self.JWT_AUDIENCE,
            "issuer": self.JWT_ISSUER,
        }

    def get_cors_config(self) -> dict:
        """Get CORS configuration as dictionary"""
        return {
            "allow_origins": self.CORS_ORIGINS,
            "allow_methods": self.CORS_METHODS,
            "allow_headers": self.CORS_HEADERS,
            "allow_credentials": True,
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Development defaults for JWT (when not configured)
class DevelopmentJWTSettings:
    """Default JWT settings for development environment"""

    JWKS_URL = None  # No JWKS in development
    ALGORITHMS = ["HS256", "RS256"]
    AUDIENCE = "development-audience"
    ISSUER = "development-issuer"
    SECRET_KEY = "development-secret-key-change-in-production"


def get_jwt_settings() -> dict:
    """Get JWT settings with development fallbacks"""
    settings = get_settings()

    if settings.is_development() and not settings.APIM_ONELOGIN_URL:
        return {
            "jwks_url": DevelopmentJWTSettings.JWKS_URL,
            "algorithms": DevelopmentJWTSettings.ALGORITHMS,
            "audience": DevelopmentJWTSettings.AUDIENCE,
            "issuer": DevelopmentJWTSettings.ISSUER,
            "secret_key": DevelopmentJWTSettings.SECRET_KEY,
        }

    return settings.get_jwt_config()
