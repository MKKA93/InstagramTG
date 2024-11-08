"""
Services Initialization Module

This module provides centralized service initialization, 
configuration, and management for the application.
"""

import logging
from typing import Dict, Any, Optional
from config.settings import settings

class ServiceManager:
    """
    Centralized service management and initialization
    """
    
    def __init__(self):
        """
        Initialize service manager
        """
        self.logger = logging.getLogger(__name__)
        self.services: Dict[str, Any] = {}
        self.service_configs: Dict[str, Dict[str, Any]] = {}

    def register_service(
        self, 
        name: str, 
        service: Any, 
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Register a service with optional configuration
        
        :param name: Service name
        :param service: Service instance
        :param config: Service-specific configuration
        """
        try:
            # Validate service registration
            if not hasattr(service, 'initialize'):
                self.logger.warning(
                    f"Service {name} does not have an initialize method"
                )
            
            # Store service and configuration
            self.services[name] = service
            self.service_configs[name] = config or {}
            
            self.logger.info(f"Service {name} registered successfully")
        
        except Exception as e:
            self.logger.error(f"Service registration error: {e}")
            raise

    def initialize_services(self):
        """
        Initialize all registered services
        """
        try:
            for name, service in self.services.items():
                config = self.service_configs.get(name, {})
                
                # Call service initialization
                service.initialize(**config)
                
                self.logger.info(f"Service {name} initialized")
        
        except Exception as e:
            self.logger.error(f"Services initialization error: {e}")
            raise

    def get_service(self, name: str) -> Any:
        """
        Retrieve a registered service
        
        :param name: Service name
        :return: Service instance
        """
        service = self.services.get(name)
        
        if not service:
            raise ValueError(f"Service {name} not found")
        
        return service

    def health_check(self) -> Dict[str, bool]:
        """
        Perform health checks on registered services
        
        :return: Service health status dictionary
        """
        health_status = {}
        
        for name, service in self.services.items():
            try:
                # Check if service has health_check method
                if hasattr(service, 'health_check'):
                    health_status[name] = service.health_check()
                else:
                    # Default to True if no specific health check
                    health_status[name] = True
            
            except Exception as e:
                self.logger.error(f"Health check failed for {name}: {e}")
                health_status[name] = False
        
        return health_status

    def shutdown_services(self):
        """
        Gracefully shutdown all registered services
        """
        try:
            for name, service in self.services.items():
                # Call service shutdown if method exists
                if hasattr(service, 'shutdown'):
                    service.shutdown()
                    self.logger.info(f"Service {name} shutdown completed")
        
        except Exception as e:
            self.logger.error(f"Service shutdown error: {e}")

class ServiceConfig:
    """
    Service configuration and dependency injection
    """
    
    @staticmethod
    def configure_dependencies(service_manager: ServiceManager):
        """
        Configure and register application services
        
        :param service_manager: Service manager instance
        """
        from services.user_service import user_service
        from services.instagram_service import instagram_service
        from services.auth_service import auth_service
        from services.notification_service import notification_service
        from database.database import db_manager
        
        # Register core services
        service_dependencies = [
            {
                'name': 'database',
                'service': db_manager,
                'config': {
                    'pool_size': settings.DATABASE_CONFIG['pool_size'],
                    'debug': settings.DEBUG
                }
            },
            {
                'name': 'user_service',
                'service': user_service,
                'config': {
                    'rate_limit': settings.RATE_LIMIT,
                    'features': settings.FEATURES
                }
            },
            {
                'name': 'instagram_service',
                'service': instagram_service,
                'config': {
                    'download_directory': settings.DOWNLOAD_CONFIG['directory'],
                    'max_download_size': settings.DOWNLOAD_CONFIG['max_size']
                }
            },
            {
                'name': 'auth_service',
                'service': auth_service,
                'config': {
                    'secret_key': settings.SECRET_KEY,
                    'jwt_config': settings.JWT_CONFIG
                }
            },
            {
                'name': 'notification_service',
                'service': notification_service,
                'config': {
                    'telegram_token': settings.TELEGRAM_BOT_TOKEN,
                    'log_channel_id': settings.TELEGRAM_LOG_CHANNEL_ID
                }
            }
        ]
        
        # Register services
        for service_info in service_dependencies:
            service_manager.register_service(
                name=service_info['name'],
                service=service_info['service'],
                config=service_info['config']
            )

# Create singleton instances
service_manager = ServiceManager()

def initialize_application_services():
    """
    Initialize all application services
    """
    try:
        # Configure service dependencies
        ServiceConfig.configure_dependencies(service_manager)
        
        # Initialize services
        service_manager.initialize_services()
        
        # Perform health checks
        health_status = service_manager.health_check()
        
        # Log health status
        for service, status in health_status.items():
            logging.getLogger(__name__).info(
                f"Service {service} health status: {'✅ Healthy' if status else '❌ Unhealthy'}"
            )
    
    except Exception as e:
        logging.getLogger(__name__).critical(
            f"Services initialization failed: {e}"
        )
        raise

def shutdown_application_services():
    """
    Gracefully shutdown all application services
    """
    service_manager.shutdown_services()

# Cleanup function for application exit
def cleanup_services():
    """
    Perform final cleanup of services
    """
    shutdown_application_services()

# Export key components
__all__ = [
    'service_manager',
    'initialize_application_services',
    'shutdown_application_services',
    'cleanup_services'
      ]
