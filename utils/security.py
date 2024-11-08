import os
import hashlib
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import bcrypt
import jwt
from datetime import datetime, timedelta
import re
import ipaddress
import logging

class SecurityManager:
    def __init__(self, secret_key=None, salt=None):
        """
        Initialize security manager with optional secret key and salt
        
        :param secret_key: Custom secret key for encryption
        :param salt: Custom salt for key derivation
        """
        # Use environment variable or generate a secure random key
        self.secret_key = secret_key or os.getenv('SECRET_KEY', secrets.token_hex(32))
        self.salt = salt or os.getenv('ENCRYPTION_SALT', secrets.token_hex(16))
        
        # Configure logging
        self.logger = logging.getLogger(__name__)

    def generate_encryption_key(self, password, salt=None):
        """
        Generate a secure encryption key using PBKDF2
        
        :param password: Password to derive key from
        :param salt: Salt for key derivation
        :return: Base64 encoded encryption key
        """
        try:
            # Use provided salt or generate a new one
            salt = salt or os.urandom(16)
            
            # Key derivation function
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            
            # Derive key and encode
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return key, salt
        except Exception as e:
            self.logger.error(f"Key generation error: {e}")
            raise

    def encrypt_data(self, data, key=None):
        """
        Encrypt sensitive data using Fernet symmetric encryption
        
        :param data: Data to encrypt
        :param key: Optional encryption key
        :return: Encrypted data
        """
        try:
            # Use provided key or generate a new one
            encryption_key = key or Fernet.generate_key()
            cipher = Fernet(encryption_key)
            
            # Encrypt data
            encrypted_data = cipher.encrypt(data.encode())
            return {
                'encrypted_data': encrypted_data.decode(),
                'encryption_key': encryption_key.decode()
            }
        except Exception as e:
            self.logger.error(f"Encryption error: {e}")
            raise

    def decrypt_data(self, encrypted_data, encryption_key):
        """
        Decrypt sensitive data
        
        :param encrypted_data: Data to decrypt
        :param encryption_key: Key used for decryption
        :return: Decrypted data
        """
        try:
            cipher = Fernet(encryption_key.encode())
            decrypted_data = cipher.decrypt(encrypted_data.encode()).decode()
            return decrypted_data
        except Exception as e:
            self.logger.error(f"Decryption error: {e}")
            raise

    def hash_password(self, password):
        """
        Hash password using bcrypt
        
        :param password: Plain text password
        :return: Hashed password
        """
        try:
            # Generate salt and hash
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode(), salt)
            return hashed.decode()
        except Exception as e:
            self.logger.error(f"Password hashing error: {e}")
            raise

    def verify_password(self, plain_password, hashed_password):
        """
        Verify password against stored hash
        
        :param plain_password: Plain text password
        :param hashed_password: Stored hashed password
        :return: Boolean indicating password match
        """
        try:
            return bcrypt.checkpw(
                plain_password.encode(), 
                hashed_password.encode()
            )
        except Exception as e:
            self.logger.error(f"Password verification error: {e}")
            return False

    def generate_jwt_token(self, user_id, expiration=None):
        """
        Generate JWT token for authentication
        
        :param user_id: User identifier
        :param expiration: Token expiration time
        :return: JWT token
        """
        try:
            # Default expiration: 1 hour
            expiration = expiration or datetime.utcnow() + timedelta(hours=1)
            
            payload = {
                'user_id': user_id,
                'exp': expiration,
                'iat': datetime.utcnow()
            }
            
            return jwt.encode(payload, self.secret_key, algorithm='HS256')
        except Exception as e:
            self.logger.error(f"JWT token generation error: {e}")
            raise

    def validate_jwt_token(self, token):
        """
        Validate JWT token
        
        :param token: JWT token to validate
        :return: Decoded token payload
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid token")
            return None

    def validate_email(self, email):
        """
        Validate email format
        
        :param email: Email to validate
        :return: Boolean indicating valid email
        """
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_regex, email) is not None

    def validate_ip_address(self, ip):
        """
        Validate IP address
        
        :param ip: IP address to validate
        :return: Boolean indicating valid IP
        """
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def generate_secure_token(self, length=32):
        """
        Generate a cryptographically secure random token
        
        :param length: Length of the token
        :return: Secure random token
        """
        return secrets.token_hex(length)

    def sanitize_input(self, input_string):
        """
        Sanitize input to prevent injection
        
        :param input_string: Input to sanitize
        :return: Sanitized input
        """
        # Remove potentially dangerous characters
        return re.sub(r'[<>&\'"()]', '', input_string)

# Create a singleton instance
security_manager = SecurityManager()
