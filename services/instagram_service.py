import os
import instaloader
import requests
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from database.database import db_manager
from database.models import User, DownloadHistory
from utils.security import security_manager
import logging

class InstagramService:
    def __init__(self):
        """
        Initialize Instagram service with logging and configuration
        """
        self.logger = logging.getLogger(__name__)
        self.loader = instaloader.Instaloader()
        self.temp_download_dir = "downloads/instagram"
        
        # Ensure download directory exists
        os.makedirs(self.temp_download_dir, exist_ok=True)

    def login(self, username: str, password: str) -> bool:
        """
        Login to Instagram account
        
        :param username: Instagram username
        :param password: Instagram password
        :return: Login status
        """
        try:
            # Encrypt credentials before storage
            encrypted_username = security_manager.encrypt_data(username)
            encrypted_password = security_manager.encrypt_data(password)

            # Attempt login
            self.loader.login(username, password)
            
            # Save credentials securely
            self._save_credentials(
                username, 
                encrypted_username['encrypted_data'], 
                encrypted_password['encrypted_data']
            )
            
            return True
        except Exception as e:
            self.logger.error(f"Instagram login failed: {e}")
            return False

    def _save_credentials(self, username: str, enc_username: str, enc_password: str):
        """
        Save encrypted Instagram credentials
        
        :param username: Instagram username
        :param enc_username: Encrypted username
        :param enc_password: Encrypted password
        """
        try:
            with db_manager.get_session() as session:
                # Find or create user
                user = session.query(User).filter_by(instagram_username=username).first()
                if not user:
                    user = User(instagram_username=username)
                    session.add(user)
                
                # Create or update credentials
                credential = user.credentials[0] if user.credentials else None
                if credential:
                    credential.encrypted_username = enc_username
                    credential.encrypted_password = enc_password
                else:
                    # Create new credential
                    credential = InstagramCredential(
                        user_id=user.id,
                        encrypted_username=enc_username,
                        encrypted_password=enc_password
                    )
                    session.add(credential)
                
                session.commit()
        except Exception as e:
            self.logger.error(f"Credential saving error: {e}")

    def download_profile_picture(self, username: str) -> Optional[str]:
        """
        Download Instagram profile picture
        
        :param username: Instagram username
        :return: Path to downloaded profile picture
        """
        try:
            # Create profile-specific download directory
            profile_dir = os.path.join(self.temp_download_dir, username)
            os.makedirs(profile_dir, exist_ok=True)

            # Download profile picture
            profile = instaloader.Profile.from_username(self.loader.context, username)
            profile_pic_filename = f"{username}_profile_pic.jpg"
            profile_pic_path = os.path.join(profile_dir, profile_pic_filename)

            # Save profile picture
            with open(profile_pic_path, 'wb') as f:
                f.write(requests.get(profile.profile_pic_url).content)

            # Log download history
            self._log_download_history(username, profile_pic_path, 'profile_picture')

            return profile_pic_path
        except Exception as e:
            self.logger.error(f"Profile picture download failed: {e}")
            return None

    def get_user_posts(self, username: str, limit: int = 10) -> List[Dict]:
        """
        Retrieve recent posts from a user's profile
        
        :param username: Instagram username
        :param limit: Number of posts to retrieve
        :return: List of post details
        """
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            
            posts = []
            for index, post in enumerate(profile.get_posts(), 1):
                if index > limit:
                    break
                
                post_details = {
                    'shortcode': post.shortcode,
                    'likes_count': post.likes,
                    'comments_count': post.comments,
                    'caption': post.caption or '',
                    'timestamp': post.date_utc,
                    'media_type': 'image' if post.is_image else 'video',
                    'url': post.url
                }
                posts.append(post_details)
            
            return posts
        except Exception as e:
            self.logger.error(f"Post retrieval failed: {e}")
            return []

    def download_post(self, post_url: str) -> Optional[str]:
        """
        Download a specific Instagram post
        
        :param post_url: URL of the Instagram post
        :return: Path to downloaded media
        """
        try:
            # Extract post shortcode from URL
            shortcode = self._extract_shortcode(post_url)
            
            # Download post
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            
            # Create download directory
            download_dir = os.path.join(self.temp_download_dir, 'posts', shortcode)
            os.makedirs(download_dir, exist_ok=True)
            
            # Download media
            filename = f"{shortcode}_media{'.mp4' if post.is_video else '.jpg'}"
            file_path = os.path.join(download_dir, filename)
            
            self.loader.download_post(post, target=download_dir)
            
            # Log download history
            self._log_download_history(
                post.owner_username, 
                file_path, 
                'video' if post.is_video else 'image'
            )
            
            return file_path
        except Exception as e:
            self.logger.error(f"Post download failed: {e}")
            return None

    def _extract_shortcode(self, url: str) -> Optional[str]:
        """
        Extract Instagram post shortcode from URL
        
        :param url: Instagram post URL
        :return: Post shortcode
        """
        match = re.search(r'/p/([^/]+)', url)
        return match.group(1) if match else None

    def _log_download_history(self, username: str, file_path: str, media_type: str):
        """
        Log download history in database
        
        :param username: Instagram username
        :param file_path: Path of downloaded media
        :param media_type: Type of media downloaded
        """
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(instagram_username=username).first()
                
                if user:
                    download_history = DownloadHistory(
                        user_id=user.id,
                        media_type=media_type,
                        media_url=file_path
                    )
                    session.add(download_history)
                    session.commit()
        except Exception as e:
            self.logger.error(f"Download history logging failed: {e}")

    def cleanup_old_downloads(self, days: int = 7):
        """
        Clean up old downloaded files
        
        :param days: Number of days to retain files
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for root, dirs, files in os.walk(self.temp_download_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                                        if file_modified_time < cutoff_date:
                        try:
                            os.remove(file_path)
                            self.logger.info(f"Deleted old file: {file_path}")
                        except Exception as e:
                            self.logger.error(f"Failed to delete file {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Download cleanup failed: {e}")

    def validate_username(self, username: str) -> bool:
        """
        Validate Instagram username
        
        :param username: Username to validate
        :return: Validity of username
        """
        try:
            # Username regex pattern
            username_pattern = r'^[a-zA-Z0-9._]+$'
            
            # Check username length and pattern
            if not re.match(username_pattern, username):
                return False
            
            if len(username) < 3 or len(username) > 30:
                return False
            
            return True
        except Exception as e:
            self.logger.error(f"Username validation error: {e}")
            return False

    def check_profile_exists(self, username: str) -> bool:
        """
        Check if an Instagram profile exists
        
        :param username: Instagram username
        :return: Profile existence status
        """
        try:
            # Attempt to load profile
            instaloader.Profile.from_username(self.loader.context, username)
            return True
        except instaloader.exceptions.ProfileNotFoundError:
            return False
        except Exception as e:
            self.logger.error(f"Profile check failed: {e}")
            return False

    def get_profile_metadata(self, username: str) -> Optional[Dict]:
        """
        Retrieve detailed profile metadata
        
        :param username: Instagram username
        :return: Profile metadata dictionary
        """
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            
            metadata = {
                'username': profile.username,
                'full_name': profile.full_name,
                'biography': profile.biography,
                'followers_count': profile.followers,
                'following_count': profile.followees,
                'posts_count': profile.mediacount,
                'is_private': profile.is_private,
                'is_verified': profile.is_verified,
                'external_url': profile.external_url,
                'profile_pic_url': profile.profile_pic_url
            }
            
            return metadata
        except Exception as e:
            self.logger.error(f"Profile metadata retrieval failed: {e}")
            return None

# Create a singleton instance
instagram_service = InstagramService()
