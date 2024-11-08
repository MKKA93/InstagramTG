"""
Database Initialization and Management Module

This module provides centralized database configuration, 
connection management, and utility functions for the application.
"""

from typing import Any, Dict, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError

from config.settings import settings
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Create declarative base for ORM models
Base = declarative_base()

class DatabaseManager:
    """
    Centralized database management class
    Handles database connection, session management, and core database operations
    """
    
    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        """
        Singleton pattern implementation
        Ensures only one database manager instance exists
        """
        if not cls._instance:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        Initialize database engine and session factory
        Configures connection pooling and logging
        """
        try:
            # Get database configuration
            db_config = settings.get_database_config()
            database_url = settings.DATABASE_CONFIG['url']

            # Create SQLAlchemy engine with connection pooling
            self._engine = create_engine(
                database_url,
                pool_size=db_config.get('pool_size', 10),
                max_overflow=db_config.get('max_overflow', 20),
                pool_timeout=db_config.get('pool_timeout', 30),
                pool_recycle=db_config.get('pool_recycle', 1800),
                echo=settings.DEBUG  # Enable SQL logging in debug mode
            )

            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine, 
                autocommit=False, 
                autoflush=False
            )

            # Create scoped session for thread safety
            self.Session = scoped_session(self._session_factory)

            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for database sessions
        Ensures proper session management and error handling
        
        :yields: Database session
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def create_tables(self):
        """
        Create all database tables defined in models
        """
        try:
            Base.metadata.create_all(self._engine)
            logger.info("All database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    def drop_tables(self):
        """
        Drop all database tables
        Use with caution in production
        """
        try:
            Base.metadata.drop_all(self._engine)
            logger.info("All database tables dropped successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error dropping database tables: {e}")
            raise

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a specific table exists in the database
        
        :param table_name: Name of the table to check
        :return: Boolean indicating table existence
        """
        try:
            inspector = inspect(self._engine)
            return table_name in inspector.get_table_names()
        except SQLAlchemyError as e:
            logger.error(f"Error checking table existence: {e}")
            return False

    def get_table_columns(self, table_name: str) -> Optional[list]:
        """
        Retrieve column names for a specific table
        
        :param table_name: Name of the table
        :return: List of column names or None
        """
        try:
            inspector = inspect(self._engine)
            return [column['name'] for column in inspector.get_columns(table_name)]
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving table columns: {e}")
            return None

    def execute_raw_sql(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute raw SQL query
        
        :param query: SQL query to execute
        :param params: Optional query parameters
        :return: Query result
        """
        try:
            with self._engine.connect() as connection:
                result = connection.execute(query, params or {})
                return result
        except SQLAlchemyError as e:
            logger.error(f"Raw SQL execution error: {e}")
            raise

    def backup_database(self, backup_path: str):
        """
        Create database backup
        
        :param backup_path: Path to save database backup
        """
        try:
            # Implement database backup logic based on database type
            if 'sqlite' in str(self._engine.url):
                import shutil
                db_path = str(self._engine.url).replace('sqlite:///', '')
                shutil.copy2(db_path, backup_path)
                logger.info(f"Database backed up to {backup_path}")
            else:
                logger.warning("Backup not supported for this database type")
        except Exception as e:
            logger.error(f"Database backup failed: {e}")

    def dispose(self):
        """
        Dispose of database engine and close all connections
        """
        try:
            if self._engine:
                self._engine.dispose()
                logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

# Create singleton database manager instance
db_manager = DatabaseManager()

# Optional cleanup function
def cleanup_database():
    """
    Cleanup function to be called on application shutdown
    """
    db_manager.dispose()

# Export key components
__all__ = [
    'Base', 
    'db_manager', 
    'cleanup_database'
]
