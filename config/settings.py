import os
import secrets
from pathlib import Path
from typing import List, Dict, Union
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """
    Centralized application settings and configuration management
    """

    # Base Directory Configuration
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    # Application Environment
    ENV: str = os.getenv('ENV', 'development')
    DEBUG: bool = ENV == 'development'

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_LOG_CHANNEL_ID: str = os.getenv('TELEGRAM_LOG_CHANNEL_ID', '')
    TELEGRAM_ADMIN_IDS: List[int] = [
        int(admin_id) for admin_id in os.getenv('TELEGRAM_ADMIN_IDS', '').split(',') 
        if admin_id
    ]

    # Instagram Configuration
    INSTAGRAM_USERNAME: str = os.getenv('INSTAGRAM_USERNAME', '')
    INSTAGRAM_PASSWORD: str = os.getenv('INSTAGRAM_PASSWORD', '')

    # Database Configuration
    DATABASE_CONFIG: Dict[str, Union[str, int]] = {
        'url': os.getenv('DATABASE_URL', 'sqlite:///instagram_bot.db'),
        'pool_size': int(os.getenv('DB_POOL_SIZE', 10)),
        'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', 20)),
        'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', 30)),
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', 1800))
    }

    # Security Configuration
    SECRET_KEY: str = os.getenv('SECRET_KEY', secrets.token_hex(32))
    ENCRYPTION_SALT: str = os.getenv('ENCRYPTION_SALT', secrets.token_hex(16))
    
    # JWT Configuration
    JWT_CONFIG: Dict[str, Union[str, int]] = {
        'algorithm': 'HS256',
        'expiration_delta': int(os.getenv('JWT_EXPIRATION_MINUTES', 60))
    }

    # Rate Limiting Configuration
    RATE_LIMIT: Dict[str, int] = {
        'requests': int(os.getenv('RATE_LIMIT_REQUESTS', 10)),
        'window': int(os.getenv('RATE_LIMIT_WINDOW', 60)),
        'block_duration': int(os.getenv('RATE_LIMIT_BLOCK_DURATION', 300))
    }

    # Download Configuration
    DOWNLOAD_CONFIG: Dict[str, Union[Path, int, List[str]]] = {
        'directory': BASE_DIR / 'downloads',
        'max_size': int(os.getenv('MAX_DOWNLOAD_SIZE', 50 * 1024 * 1024)),  # 50 MB
        'allowed_media_types': os.getenv('ALLOWED_MEDIA_TYPES', 'jpg,png,mp4').split(',')
    }

    # Logging Configuration
    LOGGING_CONFIG: Dict[str, Union[str, Path]] = {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'log_dir': BASE_DIR / 'logs'
    }

    # Feature Flags
    FEATURES: Dict[str, bool] = {
        'PROFILE_DOWNLOAD': os.getenv('FEATURE_PROFILE_DOWNLOAD', 'true').lower() == 'true',
        'POST_DOWNLOAD': os.getenv('FEATURE_POST_DOWNLOAD', 'true').lower() == 'true',
        'STORY_DOWNLOAD': os.getenv('FEATURE_STORY_DOWNLOAD', 'false').lower() == 'true',
        'REEL_DOWNLOAD': os.getenv('FEATURE_REEL_DOWNLOAD', 'true').lower() == 'true'
    }

    # Error Messages
    ERROR_MESSAGES: Dict[str, str] = {
        'UNAUTHORIZED': 'You are not authorized to use this bot.',
        'INVALID_USERNAME': 'Invalid Instagram username.',
        'DOWNLOAD_FAILED': 'Failed to download the requested content.',
        'RATE_LIMIT_EXCEEDED': 'Too many requests. Please try again later.',
        'FILE_TOO_LARGE': 'File size exceeds maximum limit.'
    }

    # Telegram Bot Configuration
    TELEGRAM_BOT_CONFIG: Dict[str, Union[str, bool, int]] = {
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
        'timeout': 30
    }

    @classmethod
    def is_production(cls) -> bool:
        """
        Check if the application is running in production environment
        
        :return: Boolean indicating production environment
        """
        return cls.ENV.lower() == 'production'

    @classmethod
    def validate_config(cls) -> None:
        """
        Validate critical configuration settings
        
        :raises ValueError: If critical configurations are missing
        """
        critical_configs = [
            'TELEGRAM_BOT_TOKEN',
            'INSTAGRAM_USERNAME',
            'INSTAGRAM_PASSWORD',
            'SECRET_KEY'
        ]
        
        for config in critical_configs:
            if not getattr(cls, config):
                raise ValueError(f"Missing critical configuration: {config}")

    @classmethod
    def create_directories(cls) -> None:
        """
        Create necessary directories for the application
        """
        directories = [
            cls.DOWNLOAD_CONFIG['directory'],
            cls.LOGGING_CONFIG['log_dir'],
            cls.BASE_DIR / 'temp'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_database_config(cls) -> Dict[str, Union[str, int]]:
        """
        Get database configuration based on environment
        
        :return: Database configuration dictionary
        """
        if cls.is_production():
            return {
                'pool_size': 50,
                'max_overflow': 10,
                'pool_timeout': 60,
                'pool_recycle': 3600
            }
        return cls.DATABASE_CONFIG

    @classmethod
    def get_feature_flags(cls, feature_name: str = None) -> Union[Dict[str, bool], bool]:
        """
        Retrieve feature flags
        
        :param feature_name: Specific feature to retrieve
        :return: Feature flag or all flags
        """
        if feature_name:
            return cls.FEATURES.get(feature_name, False)
        return cls.FEATURES

    @classmethod
    def get_telegram_config(cls) -> Dict[str, Union[str, bool, int]]:
        """
        Get Telegram bot configuration
        
        :return: Telegram bot configuration dictionary
        """
        return {
            **cls.TELEGRAM_BOT_CONFIG,
            'token': cls.TELEGRAM_BOT_TOKEN
        }

    @classmethod
    def get_logging_config(cls) -> Dict[str, Union[str, Path]]:
        """
        Get logging configuration
        
        :return: Logging configuration dictionary
        """
        return {
            **cls.LOGGING_CONFIG,
            'log_file': cls.LOGGING_CONFIG['log_dir'] / 'app.log'
        }

# Initialize directories and validate config
Settings.create_directories()
Settings.validate_config()

# Singleton instance
settings = Settings
