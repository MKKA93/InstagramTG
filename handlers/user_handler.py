import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters
from services.user_service import user_service
from services.instagram_service import instagram_service
from config.settings import settings
from utils.security import security_manager
import logging

class UserHandler:
    def __init__(self):
        """
        Initialize user handler with logging
        """
        self.logger = logging.getLogger(__name__)
        self.user_states = {}  # Track user interaction states

    def get_user_profile(self, update: Update, context: CallbackContext):
        """
        Retrieve and display user profile information
        
        :param update: Telegram update object
        :param context: Callback context
        """
        try:
            user = update.effective_user
            
            # Fetch user from database
            db_user = user_service.get_user_by_telegram_id(user.id)
            
            if not db_user:
                update.message.reply_text(
                    "You are not registered. Please use /start to register."
                )
                return
            
            # Fetch Instagram profile metadata
            if db_user.instagram_username:
                instagram_profile = instagram_service.get_profile_metadata(
                    db_user.instagram_username
                )
            else:
                instagram_profile = None
            
            # Construct profile message
            profile_message = f"👤 Telegram Profile:\n" \
                              f"ID: {user.id}\n" \
                              f"Username: {user.username or 'N/A'}\n" \
                              f"First Name: {user.first_name}\n" \
                              f"Last Name: {user.last_name or 'N/A'}\n\n"
            
            if instagram_profile:
                profile_message += "📸 Instagram Profile:\n" \
                                   f"Username: @{instagram_profile['username']}\n" \
                                   f"Full Name: {instagram_profile['full_name']}\n" \
                                   f"Followers: {instagram_profile['followers_count']}\n" \
                                   f"Following: {instagram_profile['following_count']}\n" \
                                   f"Posts: {instagram_profile['posts_count']}\n"
            
            # Add bot-specific stats
            profile_message += f"\n📊 Bot Usage:\n" \
                               f"Download Count: {db_user.download_count}\n" \
                               f"Last Login: {db_user.last_login}"
            
            update.message.reply_text(profile_message)
        
        except Exception as e:
            self.logger.error(f"Profile retrieval error: {e}")
            update.message.reply_text(
                "Failed to retrieve profile. Please try again."
            )

    def manage_settings(self, update: Update, context: CallbackContext):
        """
        User settings management interface
        
        :param update: Telegram update object
        :param context: Callback context
        """
        try:
            user = update.effective_user
            
            # Create settings keyboard
            settings_keyboard = [
                [
                    KeyboardButton("🔐 Change Password"),
                    KeyboardButton("🔔 Notifications")
                ],
                [
                    KeyboardButton("🌐 Language"),
                    KeyboardButton("🛡️ Privacy")
                ],
                [KeyboardButton("❌ Cancel")]
            ]
            
            reply_markup = ReplyKeyboardMarkup(
                settings_keyboard, 
                resize_keyboard=True, 
                one_time_keyboard=True
            )
            
            update.message.reply_text(
                "⚙️ User Settings\nSelect an option:",
                reply_markup=reply_markup
            )
            
            # Set user state for settings flow
            self.user_states[user.id] = {
                'stage': 'settings_menu',
                'attempts': 0
            }
        
        except Exception as e:
            self.logger.error(f"Settings management error: {e}")
            update.message.reply_text(
                "Failed to open settings. Please try again."
            )

    def handle_settings_flow(self, update: Update, context: CallbackContext):
        """
        Handle multi-step settings management
        
        :param update: Telegram update object
        :param context: Callback context
        """
        user = update.effective_user
        text = update.message.text
        
        try:
            # Get current user state
            state = self.user_states.get(user.id, {})
            
            if state.get('stage') == 'settings_menu':
                if text == "🔐 Change Password":
                    update.message.reply_text(
                        "Enter your current Instagram password:"
                    )
                    self.user_states[user.id]['stage'] = 'current_password'
                
                elif text == "🔔 Notifications":
                    notification_keyboard = [
                        [KeyboardButton("📬 Email"), KeyboardButton("💬 Telegram")],
                        [KeyboardButton("❌ Cancel")]
                    ]
                    reply_markup = ReplyKeyboardMarkup(
                        notification_keyboard, 
                        resize_keyboard=True
                    )
                    update.message.reply_text(
                        "Select notification preferences:",
                        reply_markup=reply_markup
                    )
                    self.user_states[user.id]['stage'] = 'notification_preferences'
            
            elif state.get('stage') == 'current_password':
                # Validate current password
                if instagram_service.verify_password(text):
                    update.message.reply_text(
                        "Enter new Instagram password:"
                    )
                    self.user_states[user.id]['stage'] = 'new_password'
                else:
                    update.message.reply_text(
                        "Incorrect password. Please try again."
                    )
            
            elif state.get('stage') == 'new_password':
                # Password complexity validation
                if len(text) < 8:
                    update.message.reply_text(
                        "Password must be at least 8 characters long."
                    )
                    return
                
                # Update Instagram password
                user_service.update_instagram_password(user.id, text)
                
                update.message.reply_text(
                    "🎉 Password updated successfully!"
                )
                
                # Clear user state
                del self.user_states[user.id]
        
        except Exception as e:
            self.logger.error(f"Settings flow error: {e}")
            update.message.reply_text(
                "Settings update failed. Please try again."
            )

    def export_user_data(self, update: Update, context: CallbackContext):
        """
        Export user's personal and download data
        
        :param update: Telegram update object
        :param context: Callback context
        """
        try:
            user = update.effective_user
            
            # Retrieve user data
            user_data = user_service.export_user_data(user.id)
            
            # Generate export file
            export_path = user_service.generate_user_data_export(user_data)
            
            # Send export file
            with open(export_path, 'rb') as export_file:
                update.message.reply_document(
                    document=export_file,
                    filename=f"user_data_export_{user.id}.json"
                )
            
            # Clean up export file
            os.remove(export_path)
        
        except Exception as e:
            self.logger.error(f"User data export error: {e}")
            update.message.reply_text(
                "Failed to export user data. Please try again."
            )

        def delete_account(self, update: Update, context: CallbackContext):
        """
        Handle user account deletion process
        
        :param update: Telegram update object
        :param context: Callback context
        """
        try:
            user = update.effective_user

            # Confirmation keyboard
            delete_keyboard = [
                [
                    KeyboardButton("✅ Confirm Delete"),
                    KeyboardButton("❌ Cancel")
                ]
            ]
            
            reply_markup = ReplyKeyboardMarkup(
                delete_keyboard, 
                resize_keyboard=True, 
                one_time_keyboard=True
            )

            # Send confirmation message
            update.message.reply_text(
                "⚠️ Account Deletion Warning\n\n"
                "This action will permanently delete your account and all associated data. "
                "Are you sure you want to proceed?\n\n"
                "Select an option below:",
                reply_markup=reply_markup
            )

            # Set user state for deletion confirmation
            self.user_states[user.id] = {
                'stage': 'account_deletion_confirmation',
                'attempts': 0
            }

        except Exception as e:
            self.logger.error(f"Account deletion initialization error: {e}")
            update.message.reply_text(
                "Failed to process account deletion. Please try again."
            )

    def handle_account_deletion_flow(self, update: Update, context: CallbackContext):
        """
        Handle account deletion confirmation and process
        
        :param update: Telegram update object
        :param context: Callback context
        """
        try:
            user = update.effective_user
            text = update.message.text

            # Get current user state
            state = self.user_states.get(user.id, {})

            if state.get('stage') == 'account_deletion_confirmation':
                if text == "✅ Confirm Delete":
                    # Perform account deletion
                    deletion_result = user_service.delete_user_account(user.id)

                    if deletion_result:
                        update.message.reply_text(
                            "🗑️ Your account has been successfully deleted. "
                            "We're sorry to see you go!"
                        )

                        # Clear user state
                        del self.user_states[user.id]
                    else:
                        update.message.reply_text(
                            "Account deletion failed. Please contact support."
                        )
                
                elif text == "❌ Cancel":
                    update.message.reply_text(
                        "Account deletion cancelled.",
                        reply_markup=ReplyKeyboardRemove()
                    )
                    
                    # Clear user state
                    del self.user_states[user.id]

        except Exception as e:
            self.logger.error(f"Account deletion flow error: {e}")
            update.message.reply_text(
                "An error occurred during account deletion. Please try again."
            )

    def reset_download_history(self, update: Update, context: CallbackContext):
        """
        Reset user's download history
        
        :param update: Telegram update object
        :param context: Callback context
        """
        try:
            user = update.effective_user

            # Reset download history
            reset_result = user_service.reset_user_download_history(user.id)

            if reset_result:
                update.message.reply_text(
                    "🔄 Your download history has been reset successfully."
                )
            else:
                update.message.reply_text(
                    "Failed to reset download history. Please try again."
                )

        except Exception as e:
            self.logger.error(f"Download history reset error: {e}")
            update.message.reply_text(
                "An error occurred while resetting download history."
            )

# Instantiate the user handler
user_handler = UserHandler()

# Optional: Additional setup for message handlers
def setup_user_handlers(dispatcher):
    """
    Setup user-related message handlers
    
    :param dispatcher: Telegram bot dispatcher
    """
    # User profile and settings commands
    dispatcher.add_handler(CommandHandler('profile', user_handler.get_user_profile))
    dispatcher.add_handler(CommandHandler('settings', user_handler.manage_settings))
    dispatcher.add_handler(CommandHandler('export_data', user_handler.export_user_data))
    dispatcher.add_handler(CommandHandler('delete_account', user_handler.delete_account))
    dispatcher.add_handler(CommandHandler('reset_history', user_handler.reset_download_history))

    # Message handler for settings and account management flow
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command, 
        user_handler.handle_settings_flow
    ))
