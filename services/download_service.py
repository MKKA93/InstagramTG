import os
import uuid
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

import requests
import aiofiles
import aiohttp
from tqdm import tqdm

from config.settings import settings
from services.user_service import user_service
from utils.security import security_manager

class DownloadService:
    def __init__(self):
        """
        Initialize download service
        """
        self.logger = logging.getLogger(__name__)
        self.download_directory = settings.DOWNLOAD_CONFIG['directory']
        self.max_download_size = settings.DOWNLOAD_CONFIG['max_size']
        self.allowed_media_types = settings.DOWNLOAD_CONFIG['allowed_media_types']

    def initialize(self, **kwargs):
        """
        Initialize service with configuration
        
        :param kwargs: Configuration parameters
        """
        self.download_directory = kwargs.get(
            'download_directory', 
            self.download_directory
        )
        self.max_download_size = kwargs.get(
            'max_download_size', 
            self.max_download_size
        )
        self.logger.info("Download service initialized successfully")

    async def download_file(
        self, 
        url: str, 
        telegram_id: int, 
        media_type: str = 'unknown',
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Asynchronously download a file with progress tracking
        
        :param url: URL of the file to download
        :param telegram_id: Telegram user ID
        :param media_type: Type of media being downloaded
        :param filename: Optional custom filename
        :return: Path to downloaded file
        """
        try:
            # Validate URL
            if not self._validate_url(url):
                self.logger.warning(f"Invalid download URL: {url}")
                return None

            # Generate unique filename if not provided
            if not filename:
                filename = self._generate_filename(url, media_type)

            # Create download path
            download_path = self._create_download_path(telegram_id, filename)

            # Download file with progress tracking
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    # Check response status
                    if response.status != 200:
                        self.logger.error(f"Download failed. Status: {response.status}")
                        return None

                    # Check file size
                    content_length = int(response.headers.get('content-length', 0))
                    if content_length > self.max_download_size:
                        self.logger.warning(f"File too large: {content_length} bytes")
                        return None

                    # Download with progress
                    async with aiofiles.open(download_path, 'wb') as f:
                        downloaded = 0
                        async for chunk in response.content.iter_chunked(1024):
                            downloaded += len(chunk)
                            await f.write(chunk)

                            # Optional: Implement download progress tracking
                            # You could add a callback or logging here

            # Log download history
            user_service.log_download(
                telegram_id=telegram_id,
                media_type=media_type,
                media_url=download_path
            )

            self.logger.info(f"File downloaded: {download_path}")
            return download_path

        except Exception as e:
            self.logger.error(f"Download error: {e}")
            return None

    def download_file_sync(
        self, 
        url: str, 
        telegram_id: int, 
        media_type: str = 'unknown',
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Synchronous file download method
        
        :param url: URL of the file to download
        :param telegram_id: Telegram user ID
        :param media_type: Type of media being downloaded
        :param filename: Optional custom filename
        :return: Path to downloaded file
        """
        try:
            # Validate URL
            if not self._validate_url(url):
                self.logger.warning(f"Invalid download URL: {url}")
                return None

            # Generate unique filename if not provided
            if not filename:
                filename = self._generate_filename(url, media_type)

            # Create download path
            download_path = self._create_download_path(telegram_id, filename)

            # Download file with progress bar
            response = requests.get(url, stream=True)
            
            # Check response status
            if response.status_code != 200:
                self.logger.error(f"Download failed. Status: {response.status_code}")
                return None

            # Check file size
            content_length = int(response.headers.get('content-length', 0))
            if content_length > self.max_download_size:
                self.logger.warning(f"File too large: {content_length} bytes")
                return None

            # Download with progress bar
            with open(download_path, 'wb') as f:
                for chunk in tqdm(
                    response.iter_content(chunk_size=8192), 
                    total=int(content_length/8192), 
                    unit='KB', 
                    desc=filename
                ):
                    if chunk:
                        f.write(chunk)

            # Log download history
            user_service.log_download(
                telegram_id=telegram_id,
                media_type=media_type,
                media_url=download_path
            )

            self.logger.info(f"File downloaded: {download_path}")
            return download_path

        except Exception as e:
            self.logger.error(f"Download error: {e}")
            return None

    def _validate_url(self, url: str) -> bool:
        """
        Validate download URL
        
        :param url: URL to validate
        :return: Validation status
        """
        try:
            # Basic URL validation
            if not url.startswith(('http://', 'https://')):
                return False

            # Optional: Add more sophisticated URL validation
            parsed_url = requests.utils.urlparse(url)
            return all([parsed_url.scheme, parsed_url.netloc])

        except Exception as e:
            self.logger.error(f"URL validation error: {e}")
            return False

    def _generate_filename(self, url: str, media_type: str) -> str:
        """
        Generate a unique filename for download
        
        :param url: Source URL
        :param media_type: Type of media
        :return: Generated filename
        """
        # Get file extension from URL or use media type
        file_ext = self._get_file_extension(url, media_type)
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"{media_type}_{timestamp}_{unique_id}.{file_ext}"

    def _get_file_extension(self, url: str, media_type: str) -> str:
        """
        Determine file extension
        
        :param url: Source URL
        :param media_type: Media type
        :return: File extension
        """
        # Try to extract extension from URL
        parsed_url = requests.utils.urlparse(url)
        path = parsed_url.path
        
        # Check URL path for extension
        if '.' in path:
            ext = path.split('.')[-1]
            if ext.lower() in self.allowed_media_types:
                return ext.lower()
        
        # Fallback to media type mapping
        ext_mapping = {
            'image': 'jpg',
            'video': 'mp4',
            'audio': 'mp3'
        }
        
        return ext_mapping.get(media_type, 'bin')

        def _create_download_path(self, telegram_id: int, filename: str) -> str:
        """
        Create download directory and full file path
        
        :param telegram_id: Telegram user ID
        :param filename: Filename to use
        :return: Full path to download file
        """
        # Create user-specific download directory
        user_download_dir = self.download_directory / str(telegram_id)
        user_download_dir.mkdir(parents=True, exist_ok=True)

        # Generate full download path
        return str(user_download_dir / filename)

    def secure_file(self, file_path: str) -> Optional[str]:
        """
        Apply security measures to downloaded file
        
        :param file_path: Path to the file
        :return: Secured file path
        """
        try:
            # Encrypt file
            encrypted_file_path = self._encrypt_file(file_path)
            
            # Scan for malware (placeholder for actual implementation)
            if not self._scan_for_malware(encrypted_file_path):
                self.logger.warning(f"Potential malware detected in {file_path}")
                os.remove(encrypted_file_path)
                return None

            return encrypted_file_path

        except Exception as e:
            self.logger.error(f"File security error: {e}")
            return None

    def _encrypt_file(self, file_path: str) -> str:
        """
        Encrypt a file using Fernet symmetric encryption
        
        :param file_path: Path to the file
        :return: Path to encrypted file
        """
        try:
            # Generate encryption key
            encryption_key = security_manager.generate_encryption_key()
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Encrypt file content
            encrypted_content = security_manager.encrypt_data(
                file_content.decode('latin-1'), 
                key=encryption_key
            )
            
            # Generate encrypted file path
            encrypted_file_path = f"{file_path}.encrypted"
            
            # Write encrypted content
            with open(encrypted_file_path, 'wb') as f:
                f.write(encrypted_content['encrypted_data'].encode('latin-1'))
            
            # Optional: Store encryption key securely
            # In a real-world scenario, you'd use a secure key management system
            key_file_path = f"{file_path}.key"
            with open(key_file_path, 'wb') as f:
                f.write(encrypted_content['encryption_key'].encode())
            
            return encrypted_file_path

        except Exception as e:
            self.logger.error(f"File encryption error: {e}")
            raise

    def _scan_for_malware(self, file_path: str) -> bool:
        """
        Placeholder for malware scanning
        
        :param file_path: Path to the file
        :return: Malware scan result
        """
        # In a real implementation, integrate with antivirus/malware scanning services
        try:
            # Basic file type and size checks
            file_size = os.path.getsize(file_path)
            if file_size > self.max_download_size:
                return False

            # Optional: Add more sophisticated checks
            # - File type validation
            # - Virus scanning API integration
            # - Signature-based detection

            return True

        except Exception as e:
            self.logger.error(f"Malware scan error: {e}")
            return False

    def cleanup_old_downloads(self, days: int = 7) -> None:
        """
        Remove old downloaded files
        
        :param days: Number of days to retain files
        """
        try:
            current_time = datetime.now()
            
            # Iterate through all user download directories
            for user_dir in self.download_directory.iterdir():
                if user_dir.is_dir():
                    for file_path in user_dir.iterdir():
                        # Check file modification time
                        file_mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        # Remove files older than specified days
                        if (current_time - file_mod_time).days > days:
                            try:
                                file_path.unlink()
                                self.logger.info(f"Deleted old file: {file_path}")
                            except Exception as e:
                                self.logger.error(f"Error deleting file {file_path}: {e}")

        except Exception as e:
            self.logger.error(f"Download cleanup error: {e}")

    def get_download_stats(self, telegram_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve download statistics
        
        :param telegram_id: Optional user ID to get specific user stats
        :return: Download statistics
        """
        try:
            stats = {
                'total_downloads': 0,
                'total_size': 0,
                'media_type_breakdown': {},
                'user_downloads': {}
            }

            # If specific user is provided
            if telegram_id:
                user_download_dir = self.download_directory / str(telegram_id)
                if user_download_dir.exists():
                    for file_path in user_download_dir.iterdir():
                        stats['total_downloads'] += 1
                        stats['total_size'] += file_path.stat().st_size
                        
                        # Media type breakdown
                        media_type = file_path.stem.split('_')[0]
                        stats['media_type_breakdown'][media_type] = \
                            stats['media_type_breakdown'].get(media_type, 0) + 1
            
            # Global statistics for all users
            else:
                for user_dir in self.download_directory.iterdir():
                    if user_dir.is_dir():
                        user_stats = self.get_download_stats(int(user_dir.name))
                        stats['user_downloads'][user_dir.name] = user_stats

            return stats

        except Exception as e:
            self.logger.error(f"Download stats retrieval error: {e}")
            return {}

    def health_check(self) -> bool:
        """
        Perform service health check
        
        :return: Service health status
        """
        try:
            # Check download directory accessibility
            if not self.download_directory.exists():
                self.download_directory.mkdir(parents=True)
            
            # Check write permissions
            test_file = self.download_directory / f"health_check_{uuid.uuid4()}.tmp"
            test_file.write_text("health check")
            test_file.unlink()
            
            return True
        
        except Exception as e:
            self.logger.error(f"Download service health check failed: {e}")
            return False

    def shutdown(self):
        """
        Perform cleanup and shutdown for the service
        """
        self.logger.info("Download service shutting down")
        self.cleanup_old_downloads()

# Create a singleton instance
download_service = DownloadService()

# Export the service
__all__ = ['download_service']
