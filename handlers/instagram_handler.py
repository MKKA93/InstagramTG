import os
from typing import List, Optional
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import CallbackContext, CommandHandler
from services.instagram_service import instagram_service
from services.user_service import user_service
from config.settings import settings
from utils.file_utils import FileUtils
import logging

class InstagramHandler:
    def __init__(self):
        """
        Initialize Instagram handler with logging and configuration
        """
        self.logger = logging.getLogger(__name__)
        self.file_utils = FileUtils()

    def download_profile(self, update: Update, context: CallbackContext):
        """
        Download Instagram profile picture
        
        :param update: Telegram update object
        :param context: Callback context
        """
        try:
            # Check command arguments
            if len(context.args) != 1:
                update.message.reply_text(
                    "Usage: /download_profile <instagram_username>"
                )
                return

            username = context.args[0]

            # Validate username
            if not instagram_service.validate_username(username):
                update.message.reply_text(
                    settings.ERROR_MESSAGES['INVALID_USERNAME']
                )
                return

            # Check profile existence
            if not instagram_service.check_profile_exists(username):
                update.message.reply_text(
                    f"Instagram profile '{username}' not found."
                )
                return

            # Send typing action
            update.message.reply_chat_action(chat_action='upload_photo')

            # Download profile picture
            profile_pic_path = instagram_service.download_profile_picture(username)

            if not profile_pic_path:
                update.message.reply_text(
                    settings.ERROR_MESSAGES['DOWNLOAD_FAILED']
                )
                return

            # Check file size
            if not self.file_utils.validate_file_size(profile_pic_path):
                update.message.reply_text(
                    settings.ERROR_MESSAGES['FILE_TOO_LARGE']
                )
                os.remove(profile_pic_path)
                return

            # Send profile picture
            with open(profile_pic_path, 'rb') as photo:
                update.message.reply_photo(
                    photo=photo, 
                    caption=f"Profile picture for @{username}"
                )

            # Log download history
            user_service.log_download_activity(
                update.effective_user.id, 
                'profile_picture'
            )

            # Clean up temporary file
            os.remove(profile_pic_path)

        except Exception as e:
            self.logger.error(f"Profile download error: {e}")
            update.message.reply_text(
                settings.ERROR_MESSAGES['DOWNLOAD_FAILED']
            )

    def get_posts(self, update: Update, context: CallbackContext):
        """
        Retrieve recent Instagram posts
        
        :param update: Telegram update object
        :param context: Callback context
        """
        try:
            # Check command arguments
            if len(context.args) < 1 or len(context.args) > 2:
                update.message.reply_text(
                    "Usage: /get_posts <instagram_username> [limit]"
                )
                return

            username = context.args[0]
            limit = int(context.args[1]) if len(context.args) == 2 else 5

            # Validate username and limit
            if not instagram_service.validate_username(username):
                update.message.reply_text(
                    settings.ERROR_MESSAGES['INVALID_USERNAME']
                )
                return

            if limit < 1 or limit > 10:
                update.message.reply_text(
                    "Limit must be between 1 and 10"
                )
                return

            # Send typing action
            update.message.reply_chat_action(chat_action='typing')

            # Get user posts
            posts = instagram_service.get_user_posts(username, limit)

            if not posts:
                update.message.reply_text(
                    f"No posts found for @{username}"
                )
                return

            # Format and send post details
            post_message = f"Recent posts for @{username}:\n\n"
            for index, post in enumerate(posts, 1):
                post_message += (
                    f"{index}. 📸 Post Details:\n"
                    f"   Likes: {post['likes_count']}\n"
                    f"   Comments: {post['comments_count']}\n"
                    f"   Date: {post['timestamp']}\n"
                    f"   URL: {post['url']}\n\n"
                )

            update.message.reply_text(post_message)

            # Log user activity
            user_service.log_download_activity(
                update.effective_user.id, 
                'post_list'
            )

        except Exception as e:
            self.logger.error(f"Post retrieval error: {e}")
            update.message.reply_text(
                settings.ERROR_MESSAGES['DOWNLOAD_FAILED']
            )

    def download_post(self, update: Update, context: CallbackContext):
        """
        Download specific Instagram post
        
        :param update: Telegram update object
        :param context: Callback context
        """
        try:
            # Check command arguments
            if len(context.args) != 1:
                update.message.reply_text(
                    "Usage: /download_post <post_url>"
                )
                return

            post_url = context.args[0]

            # Send typing action
            update.message.reply_chat_action(chat_action='upload_document')

            # Download post media
            media_path = instagram_service.download_post(post_url)

            if not media_path:
                update.message.reply_text(
                    settings.ERROR_MESSAGES['DOWNLOAD_FAILED']
                )
                return

            # Check file size
            if not self.file_utils.validate_file_size(media_path):
                update.message.reply_text(
                    settings.ERROR_MESSAGES['FILE_TOO_LARGE']
                )
                os.remove(media_path)
                return

            # Send media based on type
            with open(media_path, 'rb') as media:
                if media_path.endswith(('.jpg', '.png', '.jpeg')):
                    update.message.reply_photo(
                        photo=media, 
                        caption="Instagram Post Media"
                    )
                elif media_path.endswith('.mp4'):
                    update.message.reply_video(
                        video=media, 
                        caption="Instagram Post Video"
                    )

            # Log download activity
            user_service.log_download_activity(
                update.effective_user.id, 
                'post_download'
            )

            # Clean up temporary file
            os.remove(media_path)

        except Exception as e:
            self.logger.error(f"Post download error: {e}")
            update.message.reply_text(
                settings.ERROR_MESSAGES['DOWNLOAD_FAILED']
            )

        def download_multiple_posts(
        self, 
        update: Update, 
        context: CallbackContext
    ):
        """
        Download multiple Instagram posts
        
        :param update: Telegram update object
        :param context: Callback context
        """
        try:
            # Check command arguments
            if len(context.args) < 2:
                update.message.reply_text(
                    "Usage: /download_multiple <instagram_username> <post_count>"
                )
                return

            username = context.args[0]
            post_count = int(context.args[1])

            # Validate input
            if not instagram_service.validate_username(username):
                update.message.reply_text(
                    settings.ERROR_MESSAGES['INVALID_USERNAME']
                )
                return

            if post_count < 1 or post_count > 5:
                update.message.reply_text(
                    "Post count must be between 1 and 5"
                )
                return

            # Send typing action
            update.message.reply_chat_action(chat_action='upload_document')

            # Get user posts
            posts = instagram_service.get_user_posts(username, post_count)

            if not posts:
                update.message.reply_text(
                    f"No posts found for @{username}"
                )
                return

            # Prepare media group
            media_group = []
            downloaded_files = []

            for post in posts:
                # Download post media
                media_path = instagram_service.download_post(post['url'])

                if not media_path:
                    continue

                # Check file size
                if not self.file_utils.validate_file_size(media_path):
                    os.remove(media_path)
                    continue

                # Add to downloaded files for cleanup
                downloaded_files.append(media_path)

                # Prepare media for group
                if media_path.endswith(('.jpg', '.png', '.jpeg')):
                    media_group.append(
                        InputMediaPhoto(
                            media=open(media_path, 'rb'), 
                            caption=post.get('caption', '')
                        )
                    )
                elif media_path.endswith('.mp4'):
                    media_group.append(
                        InputMediaVideo(
                            media=open(media_path, 'rb'), 
                            caption=post.get('caption', '')
                        )
                    )

            # Send media group
            if media_group:
                update.message.reply_media_group(media=media_group)

                # Log download activity
                user_service.log_download_activity(
                    update.effective_user.id, 
                    'multiple_post_download'
                )
            else:
                update.message.reply_text(
                    "Could not download any posts"
                )

            # Clean up downloaded files
            for file_path in downloaded_files:
                try:
                    os.remove(file_path)
                except Exception as cleanup_error:
                    self.logger.error(f"File cleanup error: {cleanup_error}")

        except ValueError:
            update.message.reply_text(
                "Invalid post count. Please provide a number."
            )
        except Exception as e:
            self.logger.error(f"Multiple post download error: {e}")
            update.message.reply_text(
                settings.ERROR_MESSAGES['DOWNLOAD_FAILED']
            )

# Instantiate handler for use in bot setup
instagram_handler = InstagramHandler()
