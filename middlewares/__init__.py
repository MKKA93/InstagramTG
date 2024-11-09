"""
Middlewares Module Initialization

This module initializes the middleware components used in the InstagramTG bot.
Middlewares are used to process requests and responses, adding functionality such as
authentication checks and logging.
"""

from .auth_middleware import AuthMiddleware
from .logging_middleware import LoggingMiddleware

# List of all middleware classes to be exported
__all__ = ['AuthMiddleware', 'LoggingMiddleware']
