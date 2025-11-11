import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Application settings
    app_name: str = "Audio2MidiFlow"
    debug: bool = False
    version: str = "1.0.0"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # File handling settings
    max_file_size: int = 50 * 1024 * 1024  # 50MB in bytes
    upload_dir: str = "storage/uploads"
    output_dir: str = "storage/processed"
    temp_dir: str = "storage/temp"

    # Processing settings
    max_concurrent_tasks: int = 3
    processing_timeout: int = 300  # 5 minutes in seconds
    cleanup_after_hours: int = 24

    # Database settings
    database_url: str = "sqlite:///./audio2midi.db"

    # CORS settings
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: List[str] = ["*"]

    # WebSocket settings
    websocket_enabled: bool = True
    websocket_ping_interval: int = 20
    websocket_ping_timeout: int = 10

    # Audio processing settings
    sample_rate: int = 22050
    hop_length: int = 512
    n_fft: int = 2048
    min_duration: int = 10  # seconds
    max_duration: int = 600  # seconds
    quality_threshold: float = 0.5

    # Logging settings
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_max_bytes: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def create_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        settings.upload_dir,
        settings.output_dir,
        settings.temp_dir,
        os.path.dirname(settings.log_file),
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
