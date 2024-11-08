import os
import sys
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from dotenv import load_dotenv

# Import necessary handlers and services
from handlers.auth_handler import auth_handler
from handlers.instagram_handler import instagram_handler
from handlers.user_handler import user_handler
from services.instagram_service import instagram_service
from services.user_service import user_service
from database.database import db_manager
from utils.error_handler import error_handler
from utils.security import security_manager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class InstagramTelegramBot:
    def __init__(self):
        """
        Initialize the Telegram bot
        """
        # Load environment variables
        load_dotenv()

        # Essential configurations
        self.TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
        self.WEBHOOK_URL = os.getenv('WEBHOOK_URL', None)
        self.PORT = int(os.getenv('PORT', 5000))
        self.HOST = os.getenv('HOST', '0.0.0.0')

        # Validate essential configurations
        self._validate_config()

        # Initialize bot updater
        self.updater = Updater(token=self.TELEGRAM_TOKEN, use_context=True)
        self.dispatcher = self.updater.dispatcher

    def _validate_config(self):
        """
        Validate essential bot configurations
        """
        if not self.TELEGRAM_TOKEN:
            logger.error("TELEGRAM_TOKEN is missing!")
            sys.exit(1)

    def setup_handlers(self):
        """
        Set up all bot command and message handlers
        """
        # Authentication Handlers
        self.dispatcher.add_handler(CommandHandler('start', auth_handler.start))
        self.dispatcher.add_handler(CommandHandler('register', auth_handler.register))
        self.dispatcher.add_handler(CommandHandler('login', auth_handler.login))
        self.dispatcher.add_handler(CommandHandler('logout', auth_handler.logout))
        self.dispatcher.add_handler(CommandHandler('reset_password', auth_handler.reset_password))

        # Instagram Handlers
        self.dispatcher.add_handler(CommandHandler('download_profile', instagram_handler.download_profile))
        self.dispatcher.add_handler(CommandHandler('get_posts', instagram_handler.get_posts))
        self.dispatcher.add_handler(CommandHandler('download_post', instagram_handler.download_post))

        # User Management Handlers
        self.dispatcher.add_handler(CommandHandler('profile', user_handler.get_user_profile))
        self.dispatcher.add_handler(CommandHandler('settings', user_handler.manage_settings))

        # Message Handlers for Multi-step Processes
        self.dispatcher.add_handler(MessageHandler(
            Filters.text & ~Filters.command, 
            self._handle_message_flow
        ))

        # Error Handler
        self.dispatcher.add_error_handler(error_handler.handle_error)

    def _handle_message_flow(self, update, context):
        """
        Handle various message flows based on current state
        """
        try:
            user_id = update.effective_user.id

            # Check authentication flow states
            if auth_handler.auth_states.get(user_id, {}).get('stage'):
                if 'instagram_username' in auth_handler.auth_states[user_id].get('stage', ''):
                    auth_handler.handle_registration_flow(update, context)
                elif 'username' in auth_handler.auth_states[user_id].get('stage', ''):
                    auth_handler.handle_login_flow(update, context)
                elif 'reset_token' in auth_handler.auth_states[user_id].get('stage', ''):
                    auth_handler.handle_password_reset_flow(update, context)
        except Exception as e:
            logger.error(f"Message flow error: {e}")

    def start_bot(self):
        """
        Start the Telegram bot
        """
        try:
            # Initialize database connection
            db_manager.initialize()

            # Setup all handlers
            self.setup_handlers()

            # Start bot based on deployment mode
            if self.WEBHOOK_URL:
                self._start_webhook()
            else:
                self._start_polling()

        except Exception as e:
            logger.error(f"Bot startup error: {e}")
            sys.exit(1)

    def _start_webhook(self):
        """
        Start bot with webhook
        """
        logger.info(f"Starting webhook on {self.HOST}:{self.PORT}")
        self.updater.start_webhook(
            listen=self.HOST,
            port=self.PORT,
            url_path=self.TELEGRAM_TOKEN,
            webhook_url=f"{self.WEBHOOK_URL}/{self.TELEGRAM_TOKEN}"
        )
        self.updater.idle()

    def _start_polling(self):
        """
        Start bot with polling
        """
        logger.info("Starting bot in polling mode")
        self.updater.start_polling()
        self.updater.idle()

    def stop_bot(self):
        """
        Gracefully stop the bot
        """
        try:
            # Close database connections
            db_manager.close()

            # Stop bot
            self.updater.stop()
            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

def main():
    """
    Main entry point for the Telegram bot
    """
    try:
        # Initialize security manager
        security_manager.initialize()

        # Initialize Instagram service
        instagram_service.initialize()

        # Create and start bot instance
        bot = InstagramTelegramBot()
        bot.start_bot()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
    finally:
        # Ensure clean exit
        sys.exit(0)

if __name__ == '__main__':
    main()
