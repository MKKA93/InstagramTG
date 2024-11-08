from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    instagram_username = Column(String, nullable=True)
    is_authenticated = Column(Boolean, default=False)
    last_login = Column(DateTime, default=datetime.utcnow)
    download_count = Column(Integer, default=0)

    # Relationship with InstagramCredential
    credentials = relationship("InstagramCredential", back_populates="user")

    def __repr__(self):
        return f"<User (id={self.id}, telegram_id={self.telegram_id}, instagram_username='{self.instagram_username}')>"

class InstagramCredential(Base):
    __tablename__ = 'instagram_credentials'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    encrypted_username = Column(String, nullable=False)
    encrypted_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with User
    user = relationship("User ", back_populates="credentials")

    def __repr__(self):
        return f"<InstagramCredential(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"

class DownloadHistory(Base):
    __tablename__ = 'download_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    media_type = Column(String, nullable=False)  # e.g., 'image', 'video'
    media_url = Column(String, nullable=False)
    download_time = Column(DateTime, default=datetime.utcnow)

    # Relationship with User
    user = relationship("User ")

    def __repr__(self):
        return f"<DownloadHistory(id={self.id}, user_id={self.user_id}, media_type='{self.media_type}', download_time='{self.download_time}')>"

# Additional models can be defined here as needed
