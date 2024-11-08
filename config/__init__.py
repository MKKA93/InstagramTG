import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

class Config:
    # Base Directory Configuration
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_LOG_CHANNEL_ID = os.getenv('TELEGRAM_LOG_CHANNEL_ID', '')

    # Instagram Configuration
    INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME', '')
    INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD', '')

    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///instagram_bot.db')
    
    # Security Settings
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(32))
    ENCRYPTION_SALT = os.getenv('ENCRYPTION_SALT', os.urandom(16))

    # Application Environment
    ENV = os.getenv('ENV', 'development')
    DEBUG = ENV == 'development'

    # Logging Configuration
    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'detailed': {
                'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s'
            }
        },
        'handlers': {
            'default': {
                'level': 'INFO',
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
            },
            'file_handler': {
                'level': 'ERROR',
                'formatter': 'detailed',
                'class': 'logging.FileHandler',
                'filename': BASE_DIR / 'logs' / 'app.log',
                'mode': 'a',
            },
            'telegram_handler': {
                'level': 'WARNING',
                'formatter': 'detailed',
                'class': 'logging.handlers.TelegramHandler',
                'bot_token': TELEGRAM_BOT_TOKEN,
                'chat_id': TELEGRAM_LOG_CHANNEL_ID
            }
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['default', 'file_handler'],
                'level': 'INFO',
                'propagate': True
            },
            'telegram': {
                'handlers': ['default', 'file_handler', 'telegram_handler'],
                'level': 'WARNING',
                'propagate': False
            },
            'instagram': {
                'handlers': ['default', 'file_handler'],
                'level': 'ERROR',
                'propagate': False
            }
        }
    }

    # Download Configuration
    DOWNLOAD_DIRECTORY = BASE_DIR / 'downloads'
    MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
    ALLOWED_MEDIA_TYPES = ['jpg', 'png', 'mp4', 'jpeg']

    # Rate Limiting Configuration
    RATE_LIMIT = {
        'requests': 10,  # Maximum requests
        'window': 60,    # Per minute
        'block_duration': 300  # Block for 5 minutes after exceeding limit
    }

    # Feature Flags
    FEATURES = {
        'PROFILE_DOWNLOAD': True,
        'POST_DOWNLOAD': True,
        'STORY_DOWNLOAD': False,
        'REEL_DOWNLOAD': True
    }

    # Error Messages
    ERROR_MESSAGES = {
        'UNAUTHORIZED': 'You are not authorized to use this bot.',
        'INVALID_USERNAME': 'Invalid Instagram username.',
        'DOWNLOAD_FAILED': 'Failed to download the requested content.',
        'RATE_LIMIT_EXCEEDED': 'Too many requests. Please try again later.',
        'FILE_TOO_LARGE': 'File size exceeds maximum limit.'
    }

    @classmethod
    def is_production(cls):
        """
        Check if the application is running in production environment
        """
        return cls.ENV.lower() == 'production'

    @classmethod
    def create_directories(cls):
        """
        Create necessary directories for the application
        """
        directories = [
            cls.DOWNLOAD_DIRECTORY,
            cls.BASE_DIR / 'logs',
            cls.BASE_DIR / 'temp'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate_config(cls):
        """
        Validate critical configuration settings
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
    def get_database_config(cls):
        """
        Get database configuration based on environment
        """
        if cls.is_production():
            return {
                'pool_size': 20,
                'max_overflow': 0,
                'pool_timeout': 30,
                'pool_recycle': 3600
            }
        return {
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 10,
            'pool_recycle': 1800
        }

# Initialize directories and validate config
Config.create_directories()
Config.validate_config()

# Export configuration
config = Config
