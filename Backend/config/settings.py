"""
Core settings module that defines application configuration using Pydantic.
Settings are loaded from environment variables and default values.
"""
import os
from typing import Dict, Any, Optional, Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LLMSettings(BaseSettings):
    """LLM provider settings."""
    default_provider: str = Field(
        default="openai", 
        description="Default LLM provider (openai, anthropic, azure, or ollama)"
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key"
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model to use"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key"
    )
    anthropic_model: str = Field(
        default="claude-3-sonnet-20240229",
        description="Anthropic model to use"
    )
    azure_openai_api_key: Optional[str] = Field(
        default=None,
        description="Azure OpenAI API key"
    )
    azure_openai_api_base: Optional[str] = Field(
        default=None,
        description="Azure OpenAI API base URL"
    )
    azure_openai_api_version: str = Field(
        default="2023-05-15",
        description="Azure OpenAI API version"
    )
    azure_openai_deployment: str = Field(
        default="gpt-4o-ms",
        description="Azure OpenAI deployment name"
    )
    azure_openai_model_deployment: Optional[str] = Field(
        default=None,
        description="Azure OpenAI model deployment name"
    )
    ollama_model: str = Field(
        default="llama3",
        description="Ollama model to use"
    )
    # 添加.env文件中可能存在的其他字段
    deepseek_api_key: Optional[str] = Field(
        default=None,
        description="DeepSeek API key"
    )
    google_api_key: Optional[str] = Field(
        default=None,
        description="Google API key"
    )
    siliconflow_api_key: Optional[str] = Field(
        default=None,
        description="SiliconFlow API key"
    )
    
    model_config = SettingsConfigDict(env_prefix="LLM_", case_sensitive=False)

class APISettings(BaseSettings):
    """API configuration settings."""
    host: str = Field(
        default="0.0.0.0",
        description="API host"
    )
    port: int = Field(
        default=8000,
        description="API port"
    )
    base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for internal API calls"
    )
    cors_origins: list = Field(
        default=["*"],
        description="CORS allowed origins"
    )
    
    model_config = SettingsConfigDict(env_prefix="API_", case_sensitive=False)

class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    level: str = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    file: Optional[str] = Field(
        default=None,
        description="Log file path (if None, logs to console only)"
    )
    
    model_config = SettingsConfigDict(env_prefix="LOG_", case_sensitive=False)

class Settings(BaseSettings):
    """Main application settings."""
    environment: Literal["development", "testing", "production"] = Field(
        default="development",
        description="Application environment"
    )
    debug: bool = Field(
        default=True,
        description="Debug mode"
    )
    llm: LLMSettings = LLMSettings()
    api: APISettings = APISettings()
    logging: LoggingSettings = LoggingSettings()
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

@lru_cache()
def get_settings() -> Settings:
    """
    Create cached instance of settings.
    Returns:
        Settings object with application configuration
    """
    return Settings()

# Create a singleton instance of Settings
settings = get_settings() 