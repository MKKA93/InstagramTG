import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
import logging
from contextlib import contextmanager
from config.settings import Config

# Configure logging
logger = logging.getLogger(__name__)

# Base class for declarative models
Base = declarative_base()

class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize database connection and session factory"""
        try:
            # Create engine with connection pooling and logging
            self.engine = create_engine(
                Config.DATABASE_URL,
                pool_size=10,  # Maximum number of connections in the pool
                max_overflow=20,  # Number of connections that can be created beyond pool_size
                pool_timeout=30,  # Timeout for getting a connection from the pool
                pool_recycle=1800,  # Recycle connections after 30 minutes
                echo=Config.is_production() == False  # Enable SQL logging in development
            )

            # Create session factory
            self.SessionLocal = sessionmaker(
                bind=self.engine, 
                autocommit=False, 
                autoflush=False
            )
            
            # Create scoped session for thread-local sessions
            self.Session = scoped_session(self.SessionLocal)

            # Create all tables defined in models
            self._create_tables()
            
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def _create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("All database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions
        Ensures proper session management and error handling
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def add(self, model):
        """
        Add a new record to the database
        
        :param model: SQLAlchemy model instance
        :return: Added model instance
        """
        try:
            with self.get_session() as session:
                session.add(model)
                session.commit()
                return model
        except SQLAlchemyError as e:
            logger.error(f"Error adding record: {e}")
            raise

    def update(self, model):
        """
        Update an existing record in the database
        
        :param model: SQLAlchemy model instance
        :return: Updated model instance
        """
        try:
            with self.get_session() as session:
                session.merge(model)
                session.commit()
                return model
        except SQLAlchemyError as e:
            logger.error(f"Error updating record: {e}")
            raise

    def delete(self, model):
        """
        Delete a record from the database
        
        :param model: SQLAlchemy model instance
        """
        try:
            with self.get_session() as session:
                session.delete(model)
                session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Error deleting record: {e}")
            raise

    def get_by_id(self, model_class, record_id):
        """
        Retrieve a record by its ID
        
        :param model_class: SQLAlchemy model class
        :param record_id: ID of the record
        :return: Model instance or None
        """
        try:
            with self.get_session() as session:
                return session.query(model_class).get(record_id)
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving record: {e}")
            raise

    def query(self, model_class):
        """
        Start a query for a specific model
        
        :param model_class: SQLAlchemy model class
        :return: Query object
        """
        try:
            session = self.Session()
            return session.query(model_class)
        except SQLAlchemyError as e:
            logger.error(f"Error creating query: {e}")
            raise

    def table_exists(self, table_name):
        """
        Check if a table exists in the database
        
        :param table_name: Name of the table
        :return: Boolean indicating table existence
        """
        try:
            inspector = inspect(self.engine)
            return table_name in inspector.get_table_names()
        except SQLAlchemyError as e:
            logger.error(f"Error checking table existence: {e}")
            raise

    def get_connection(self):
        """
        Get a raw database connection
        
        :return: Database connection
        """
        return self.engine.connect()

    def dispose(self):
        """
        Close all database connections
        """
        try:
            self.engine.dispose()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

# Singleton instance of DatabaseManager
db_manager = DatabaseManager()

# Optional: Cleanup function to be called on application shutdown
def cleanup_database():
    db_manager.dispose()
