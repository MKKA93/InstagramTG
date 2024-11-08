import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm.exc import NoResultFound
from database.database import db_manager
from database.models import User, InstagramCredential, DownloadHistory
from utils.security import security_manager
from config.settings import settings

class UserService:
    def __init__(self):
        """
        Initialize user service with logging
        """
        self.logger = logging.getLogger(__name__)
        self.max_login_attempts = 3
        self.block_duration = timedelta(minutes=30)

    def initialize(self, **kwargs):
        """
        Initialize service with configuration
        
        :param kwargs: Configuration parameters
        """
        self.rate_limit = kwargs.get('rate_limit', {})
        self.features = kwargs.get('features', {})
        self.logger.info("User service initialized successfully")

    def create_user(
        self, 
        telegram_id: int, 
        username: str = None, 
        first_name: str = None, 
        last_name: str = None
    ) -> User:
        """
        Create a new user in the database
        
        :param telegram_id: Telegram user ID
        :param username: Telegram username
        :param first_name: User's first name
        :param last_name: User's last name
        :return: Created user object
        """
        try:
            with db_manager.get_session() as session:
                # Check if user already exists
                existing_user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if existing_user:
                    return existing_user
                
                # Create new user
                new_user = User(
                    telegram_id=telegram_id,
                    instagram_username=None,
                    is_authenticated=False,
                    download_count=0
                )
                
                session.add(new_user)
                session.commit()
                
                self.logger.info(f"User created: {telegram_id}")
                return new_user
        
        except Exception as e:
            self.logger.error(f"User creation error: {e}")
            raise

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Retrieve user by Telegram ID
        
        :param telegram_id: Telegram user ID
        :return: User object or None
        """
        try:
            with db_manager.get_session() as session:
                return session.query(User).filter_by(telegram_id=telegram_id).first()
        
        except Exception as e:
            self.logger.error(f"User retrieval error: {e}")
            return None

    def update_instagram_credentials(
        self, 
        telegram_id: int, 
        username: str, 
        encrypted_username: str = None, 
        encrypted_password: str = None
    ) -> bool:
        """
        Update Instagram credentials for a user
        
        :param telegram_id: Telegram user ID
        :param username: Instagram username
        :param encrypted_username: Encrypted username
        :param encrypted_password: Encrypted password
        :return: Update status
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    self.logger.warning(f"User not found: {telegram_id}")
                    return False
                
                # Update Instagram username
                user.instagram_username = username
                user.is_authenticated = True
                user.last_login = datetime.utcnow()
                
                # Create or update credentials
                credential = session.query(InstagramCredential).filter_by(user_id=user.id).first()
                
                if credential:
                    if encrypted_username:
                        credential.encrypted_username = encrypted_username
                    if encrypted_password:
                        credential.encrypted_password = encrypted_password
                else:
                    credential = InstagramCredential(
                        user_id=user.id,
                        encrypted_username=encrypted_username or '',
                        encrypted_password=encrypted_password or ''
                    )
                    session.add(credential)
                
                session.commit()
                self.logger.info(f"Instagram credentials updated for user: {telegram_id}")
                return True
        
        except Exception as e:
            self.logger.error(f"Credential update error: {e}")
            return False

    def remove_instagram_credentials(self, telegram_id: int) -> bool:
        """
        Remove Instagram credentials for a user
        
        :param telegram_id: Telegram user ID
        :return: Removal status
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    return False
                
                # Remove credentials
                session.query(InstagramCredential).filter_by(user_id=user.id).delete()
                
                # Reset user authentication status
                user.instagram_username = None
                user.is_authenticated = False
                
                session.commit()
                self.logger.info(f"Instagram credentials removed for user: {telegram_id}")
                return True
        
        except Exception as e:
            self.logger.error(f"Credential removal error: {e}")
            return False

    def update_instagram_password(
        self, 
        telegram_id: int, 
        new_password: str
    ) -> bool:
        """
        Update Instagram account password
        
        :param telegram_id: Telegram user ID
        :param new_password: New password
        :return: Update status
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    return False
                
                # Find user credentials
                credential = session.query(InstagramCredential).filter_by(user_id=user.id).first()
                
                if not credential:
                    return False
                
                # Encrypt new password
                encrypted_password = security_manager.encrypt_data(new_password)
                
                # Update credential
                credential.encrypted_password = encrypted_password['encrypted_data']
                
                session.commit()
                self.logger.info(f"Password updated for user: {telegram_id}")
                return True
        
        except Exception as e:
            self.logger.error(f"Password update error: {e}")
            return False

    def log_download(
        self, 
        telegram_id: int, 
        media_type: str, 
        media_url: str
    ) -> bool:
        """
        Log user download activity
        
        :param telegram_id: Telegram user ID
        :param media_type: Type of media downloaded
        :param media_url: URL or path of downloaded media
        :return: Logging status
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    return False
                
                # Create download history entry
                download_history = DownloadHistory(
                    user_id=user.id,
                    media_type=media_type,
                    media_url=media_url
                )
                
                # Increment download count
                user.download_count += 1
                
                session.add(download_history)
                session.commit()
                
                return True
        
        except Exception as e:
            self.logger.error(f"Download logging error: {e}")
            return False

        def reset_user_download_history(self, telegram_id: int) -> bool:
        """
        Reset user's download history
        
        :param telegram_id: Telegram user ID
        :return: Reset status
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    return False
                
                # Delete all download history entries for the user
                session.query(DownloadHistory).filter_by(user_id=user.id).delete()
                
                # Reset download count
                user.download_count = 0
                
                session.commit()
                
                self.logger.info(f"Download history reset for user: {telegram_id}")
                return True
        
        except Exception as e:
            self.logger.error(f"Download history reset error: {e}")
            return False

    def export_user_data(self, telegram_id: int) -> Optional[str]:
        """
        Export user data to a JSON file
        
        :param telegram_id: Telegram user ID
        :return: Path to exported data file
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    return None
                
                # Collect user data
                user_data = {
                    'user_info': {
                        'telegram_id': user.telegram_id,
                        'instagram_username': user.instagram_username,
                        'is_authenticated': user.is_authenticated,
                        'last_login': user.last_login.isoformat() if user.last_login else None,
                        'download_count': user.download_count
                    },
                    'download_history': []
                }
                
                # Fetch download history
                download_history = session.query(DownloadHistory).filter_by(user_id=user.id).all()
                
                for entry in download_history:
                    user_data['download_history'].append({
                        'media_type': entry.media_type,
                        'media_url': entry.media_url,
                        'download_time': entry.download_time.isoformat()
                    })
                
                # Create export directory
                export_dir = settings.BASE_DIR / 'exports'
                export_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate export filename
                export_filename = f"user_data_{telegram_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                export_path = export_dir / export_filename
                
                # Write data to file
                with open(export_path, 'w') as f:
                    json.dump(user_data, f, indent=2)
                
                self.logger.info(f"User data exported: {export_path}")
                return str(export_path)
        
        except Exception as e:
            self.logger.error(f"User data export error: {e}")
            return None

    def delete_user_account(self, telegram_id: int) -> bool:
        """
        Permanently delete user account and associated data
        
        :param telegram_id: Telegram user ID
        :return: Deletion status
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    return False
                
                # Delete related records
                # 1. Delete download history
                session.query(DownloadHistory).filter_by(user_id=user.id).delete()
                
                # 2. Delete Instagram credentials
                session.query(InstagramCredential).filter_by(user_id=user.id).delete()
                
                # 3. Delete user
                session.delete(user)
                
                session.commit()
                
                self.logger.info(f"User account deleted: {telegram_id}")
                return True
        
        except Exception as e:
            self.logger.error(f"User account deletion error: {e}")
            return False

    def block_user(self, telegram_id: int, duration: Optional[timedelta] = None) -> bool:
        """
        Block user account temporarily
        
        :param telegram_id: Telegram user ID
        :param duration: Block duration (default: 30 minutes)
        :return: Blocking status
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    return False
                
                # Set block details
                user.is_blocked = True
                user.block_until = datetime.utcnow() + (duration or self.block_duration)
                
                session.commit()
                
                self.logger.warning(f"User blocked: {telegram_id}")
                return True
        
        except Exception as e:
            self.logger.error(f"User blocking error: {e}")
            return False

    def unblock_user(self, telegram_id: int) -> bool:
        """
        Unblock user account
        
        :param telegram_id: Telegram user ID
        :return: Unblocking status
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user:
                    return False
                
                # Remove block details
                user.is_blocked = False
                user.block_until = None
                
                session.commit()
                
                self.logger.info(f"User unblocked: {telegram_id}")
                return True
        
        except Exception as e:
            self.logger.error(f"User unblocking error: {e}")
            return False

    def is_user_blocked(self, telegram_id: int) -> bool:
        """
        Check if user is currently blocked
        
        :param telegram_id: Telegram user ID
        :return: Blocking status
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                
                if not user or not user.is_blocked:
                    return False
                
                # Check if block duration has expired
                if user.block_until and user.block_until < datetime.utcnow():
                    # Automatically unblock if duration has passed
                    user.is_blocked = False
                    user.block_until = None
                    session.commit()
                    return False
                
                return user.is_blocked
        
        except Exception as e:
            self.logger.error(f"User blocking status check error: {e}")
            return False

    def health_check(self) -> bool:
        """
        Perform service health check
        
        :return: Service health status
        """
        try:
            # Perform a simple database connection test
            with db_manager.get_session() as session:
                session.execute('SELECT 1')
            
            return True
        
        except Exception as e:
            self.logger.error(f"User service health check failed: {e}")
            return False

    def shutdown(self):
        """
        Perform cleanup and shutdown for the service
        """
        self.logger.info("User service shutting down")
        # Additional cleanup logic if needed

# Create a singleton instance
user_service = UserService()

# Export the service
__all__ = ['user_service']
