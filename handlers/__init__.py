"""
Handlers Module Initialization

This module provides centralized initialization and management 
of different handler classes for the Telegram bot.
"""

import logging
from typing import Dict, Any, Optional, Callable

from telegram import Update
from telegram.ext import CallbackContext, Handler

from config.settings import settings
from utils.error_handler import error_handler
from services.user_service import user_service

class HandlerManager:
    """
    Centralized handler management and routing
    Provides utility methods for handler registration and management
    """

    def __init__(self):
        """
        Initialize handler manager with logging and configuration
        """
        self.logger = logging.getLogger(__name__)
        self.handlers: Dict[str, Handler] = {}
        self.middleware_chain: list = []

    def register_handler(
        self, 
        name: str, 
        handler: Handler, 
        priority: int = 0
    ) -> None:
        """
        Register a new handler with optional priority
        
        :param name: Unique handler identifier
        :param handler: Telegram handler instance
        :param priority: Handler execution priority
        """
        try:
            if name in self.handlers:
                self.logger.warning(f"Handler {name} already exists. Overwriting.")
            
            self.handlers[name] = {
                'handler': handler,
                'priority': priority
            }
            self.logger.info(f"Registered handler: {name}")
        except Exception as e:
            self.logger.error(f"Handler registration failed: {e}")

    def add_middleware(
        self, 
        middleware: Callable[[Update, CallbackContext], bool]
    ) -> None:
        """
        Add middleware to handler processing chain
        
        :param middleware: Middleware function
        """
        try:
            self.middleware_chain.append(middleware)
            self.logger.info("Middleware added to processing chain")
        except Exception as e:
            self.logger.error(f"Middleware registration failed: {e}")

    def apply_middleware(
        self, 
        update: Update, 
        context: CallbackContext
    ) -> bool:
        """
        Apply middleware chain to incoming updates
        
        :param update: Telegram update object
        :param context: Callback context
        :return: Whether update should be processed
        """
        try:
            for middleware in self.middleware_chain:
                if not middleware(update, context):
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Middleware processing error: {e}")
            return False

    def authentication_middleware(
        self, 
        update: Update, 
        context: CallbackContext
    ) -> bool:
        """
        Default authentication middleware
        Checks user authentication status
        
        :param update: Telegram update object
        :param context: Callback context
        :return: Authentication status
        """
        try:
            user = update.effective_user
            if not user:
                return False

            # Check user authentication
            db_user = user_service.get_user_by_telegram_id(user.id)
            
            if not db_user:
                update.message.reply_text(
                    settings.ERROR_MESSAGES['UNAUTHORIZED']
                )
                return False

            # Additional authentication checks can be added here
            return True
        except Exception as e:
            self.logger.error(f"Authentication middleware error: {e}")
            return False

    def rate_limit_middleware(
        self, 
        update: Update, 
        context: CallbackContext
    ) -> bool:
        """
        Rate limiting middleware
        Prevents excessive bot usage
        
        :param update: Telegram update object
        :param context: Callback context
        :return: Whether request is allowed
        """
        try:
            user = update.effective_user
            if not user:
                return False

            # Check rate limit
            if user_service.is_rate_limited(user.id):
                update.message.reply_text(
                    settings.ERROR_MESSAGES['RATE_LIMIT_EXCEEDED']
                )
                return False

            return True
        except Exception as e:
            self.logger.error(f"Rate limit middleware error: {e}")
            return False

    def global_error_handler(
        self, 
        update: Update, 
        context: CallbackContext
    ) -> None:
        """
        Global error handler for unhandled exceptions
        
        :param update: Telegram update object
        :param context: Callback context
        """
        try:
            error_handler.handle_error(update, context)
        except Exception as e:
            self.logger.critical(f"Critical error handling failure: {e}")

    def configure_default_middleware(self) -> None:
        """
        Configure default middleware for bot handlers
        """
        try:
            # Add default middleware in order
            self.add_middleware(self.authentication_middleware)
            self.add_middleware(self.rate_limit_middleware)
            
            self.logger.info("Default middleware configured successfully")
        except Exception as e:
            self.logger.error(f"Middleware configuration failed: {e}")

    def get_sorted_handlers(self) -> list:
        """
        Retrieve handlers sorted by priority
        
        :return: Sorted list of handlers
        """
        return sorted(
            self.handlers.values(), 
            key=lambda x: x['priority'], 
            reverse=True
        )

    def reset(self) -> None:
        """
        Reset handler manager to initial state
        """
        self.handlers.clear()
        self.middleware_chain.clear()
        self.logger.info("Handler manager reset")

# Create singleton handler manager
handler_manager = HandlerManager()

# Configure default middleware
handler_manager.configure_default_middleware()

# Export key components
__all__ = [
    'handler_manager',
    'HandlerManager'
          ]
