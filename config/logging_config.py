import os
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import colorlog  # Optional: For colored console logging

class LoggingConfig:
    """
    Comprehensive Logging Configuration Class
    Supports multiple logging handlers and advanced logging features
    """
    
    def __init__(self, log_dir=None, log_level=logging.INFO):
        """
        Initialize logging configuration
        
        :param log_dir: Directory for log files
        :param log_level: Logging level
        """
        # Set default log directory
        self.log_dir = log_dir or Path(__file__).parent.parent / 'logs'
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set logging level
        self.log_level = log_level
        
        # Initialize loggers
        self.loggers = {}

    def _create_console_handler(self, colored=True):
        """
        Create console logging handler
        
        :param colored: Use colored logging
        :return: Console handler
        """
        if colored and colorlog:
            # Colored console handler
            console_handler = colorlog.StreamHandler()
            console_formatter = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            # Standard console handler
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(console_formatter)
        return console_handler

    def _create_file_handler(self, logger_name):
        """
        Create file logging handler
        
        :param logger_name: Name of the logger
        :return: File handler
        """
        # Create daily log files
        log_file = self.log_dir / f'{logger_name}_{datetime.now().strftime("%Y-%m-%d")}.log'
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5  # Keep 5 backup files
        )
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(file_formatter)
        return file_handler

    def _create_telegram_handler(self, bot_token, chat_id):
        """
        Create Telegram logging handler
        
        :param bot_token: Telegram Bot Token
        :param chat_id: Telegram Chat ID for logging
        :return: Telegram handler
        """
        class TelegramHandler(logging.Handler):
            def __init__(self, bot_token, chat_id):
                super().__init__()
                self.bot_token = bot_token
                self.chat_id = chat_id

            def emit(self, record):
                try:
                    import requests
                    msg = self.format(record)
                    url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
                    payload = {
                        'chat_id': self.chat_id,
                        'text': msg,
                        'parse_mode': 'Markdown'
                    }
                    requests.post(url, json=payload)
                except Exception:
                    self.handleError(record)

        telegram_handler = TelegramHandler(bot_token, chat_id)
        telegram_formatter = logging.Formatter(
            '*%(levelname)s*: %(message)s\n'
            'Logger: `%(name)s`\n'
            'Time: `%(asctime)s`',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        telegram_handler.setLevel(logging.WARNING)
        telegram_handler.setFormatter(telegram_formatter)
        return telegram_handler

    def get_logger(self, name, 
                   console=True, 
                   file=True, 
                   telegram=False, 
                   bot_token=None, 
                   chat_id=None):
        """
        Get or create a logger with specified handlers
        
        :param name: Logger name
        :param console: Enable console logging
        :param file: Enable file logging
        :param telegram: Enable Telegram logging
        :param bot_token: Telegram Bot Token
        :param chat_id: Telegram Chat ID
        :return: Configured logger
        """
        # Check if logger already exists
        if name in self.loggers:
            return self.loggers[name]
        
        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        
        # Prevent log message propagation
        logger.propagate = False
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Add console handler
        if console:
            logger.addHandler(self._create_console_handler())
        
        # Add file handler
        if file:
            logger.addHandler(self._create_file_handler(name))
        
        # Add Telegram handler
        if telegram and bot_token and chat_id:
            try:
                logger.addHandler(self._create_telegram_handler(bot_token, chat_id))
            except Exception as e:
                logger.error(f"Failed to create Telegram handler: {e}")
        
        # Store logger
        self.loggers[name] = logger
        
        return logger

    @staticmethod
    def log_exception(logger, message=None, exc_info=True):
        """
        Log exceptions with optional custom message
        
        :param logger: Logger instance
        :param message: Custom error message
        :param exc_info: Include exception info
        """
        if message:
            logger.exception(message)
        else:
            logger.exception("An unexpected error occurred")

    def configure_global_logging(self, bot_token=None, chat_id=None):
        """
        Configure global logging settings
        
        :param bot_token: Telegram Bot Token for global logging
        :param chat_id: Telegram Chat ID for global logging
        """
        logging.basicConfig(
            level=self.log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                self._create_console_handler(),
                self._create_file_handler('global')
            ]
        )

        # Optional Telegram global logging
        if bot_token and chat_id:
            telegram_handler = self._create_telegram_handler(bot_token, chat_id)
            logging.getLogger().addHandler(telegram_handler)

# Create a singleton instance
logging_config = LoggingConfig()

# Example Usage
def main():
    # Get logger for a specific module
    logger = logging_config.get_logger(
        'instagram_service', 
        console=True, 
        file=True, 
        telegram=True,
        bot_token='your_telegram_bot_token',
        chat_id='your_chat_id'
    )

    try:
        # Some code that might raise an exception
        result = 10 / 0
    except Exception:
        # Log the exception with custom handling
        logging_config.log_exception(
            logger, 
            message="Division by zero error occurred in main function"
        )

    # Different log levels demonstration
    logger.debug("This is a debug message")
    logger.info("This is an informational message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

if __name__ == "__main__":
    main()
