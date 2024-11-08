import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters
from services.instagram_service import instagram_service
from services.user_service import user_service
from utils.security import security_manager
from database.database import db_manager
from database.models import User
import logging
import re

class AuthHandler:
    def __init__(self):
        """
        Initialize authentication handler
        """
        self.logger = logging.getLogger(__name__)
        self.auth_states = {}  # Track user authentication states
    
    def start(self, update: Update, context: CallbackContext):
        """
        Handle bot start command
        
        :param update: Telegram update object
        :param context: Callback context
        """
        user = update.effective_user
        
        try:
            # Check if user exists in database
            db_user = user_service.get_user_by_telegram_id(user.id)
            
            if not db_user:
                # Create new user if not exists
                db_user = user_service.create_user(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
            
            # Create welcome keyboard
            keyboard = [
                [KeyboardButton("Login 🔐"), KeyboardButton("Register 📝")],
                [KeyboardButton("Help ℹ️"), KeyboardButton("About 🤖")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            # Send welcome message
            welcome_message = (
                f"👋 Welcome {user.first_name}!\n\n"
                "I'm an Instagram profile and media downloader bot. "
                "Please choose an option below:"
            )
            
            update.message.reply_text(
                welcome_message, 
                reply_markup=reply_markup
            )
        
        except Exception as e:
            self.logger.error(f"Start command error: {e}")
            update.message.reply_text("An error occurred. Please try again.")

    def register(self, update: Update, context: CallbackContext):
        """
        Handle user registration process
        
        :param update: Telegram update object
        :param context: Callback context
        """
        user = update.effective_user
        
        try:
            # Check if user already registered
            existing_user = user_service.get_user_by_telegram_id(user.id)
            if existing_user and existing_user.is_registered:
                update.message.reply_text("You are already registered!")
                return
            
            # Prompt for Instagram username
            update.message.reply_text(
                "Please enter your Instagram username to register:"
            )
            
            # Set registration state
            self.auth_states[user.id] = {
                'stage': 'instagram_username',
                'attempts': 0
            }
        
        except Exception as e:
            self.logger.error(f"Registration error: {e}")
            update.message.reply_text("Registration failed. Please try again.")

    def handle_registration_flow(self, update: Update, context: CallbackContext):
        """
        Handle multi-step registration process
        
        :param update: Telegram update object
        :param context: Callback context
        """
        user = update.effective_user
        text = update.message.text
        
        try:
            # Check user's current registration state
            state = self.auth_states.get(user.id, {})
            
            if state.get('stage') == 'instagram_username':
                # Validate Instagram username
                if not instagram_service.validate_username(text):
                    update.message.reply_text(
                        "Invalid Instagram username. Please try again:"
                    )
                    return
                
                # Check if profile exists
                if not instagram_service.check_profile_exists(text):
                    update.message.reply_text(
                        "This Instagram profile does not exist. Please check and try again:"
                    )
                    return
                
                # Update registration state
                self.auth_states[user.id].update({
                    'stage': 'confirm_username',
                    'instagram_username': text
                })
                
                # Confirm username
                update.message.reply_text(
                    f"Confirm Instagram username: {text}? (Yes/No)"
                )
            
            elif state.get('stage') == 'confirm_username':
                if text.lower() == 'yes':
                    # Complete registration
                    instagram_username = state.get('instagram_username')
                    user_service.complete_registration(
                        telegram_id=user.id,
                        instagram_username=instagram_username
                    )
                    
                    # Clear registration state
                    del self.auth_states[user.id]
                    
                    update.message.reply_text(
                        "🎉 Registration successful! "
                        "You can now use the bot's Instagram features."
                    )
                else:
                    # Restart registration
                    update.message.reply_text(
                        "Registration cancelled. Please start again."
                    )
                    del self.auth_states[user.id]
        
        except Exception as e:
            self.logger.error(f"Registration flow error: {e}")
            update.message.reply_text("Registration failed. Please try again.")

    def login(self, update: Update, context: CallbackContext):
        """
        Handle Instagram login process
        
        :param update: Telegram update object
        :param context: Callback context
        """
        user = update.effective_user
        
        try:
            # Check user registration
            db_user = user_service.get_user_by_telegram_id(user.id)
            if not db_user or not db_user.is_registered:
                update.message.reply_text(
                    "Please register first using /register"
                )
                return
            
            # Prompt for Instagram credentials
            update.message.reply_text(
                "Enter your Instagram username:"
            )
            
            # Set login state
            self.auth_states[user.id] = {
                'stage': 'username',
                'attempts': 0
            }
        
        except Exception as e:
            self.logger.error(f"Login initialization error: {e}")
            update.message.reply_text("Login failed. Please try again.")

    def handle_login_flow(self, update: Update, context: CallbackContext):
        """
        Handle multi-step login process
        
        :param update: Telegram update object
        :param context: Callback context
        """
        user = update.effective_user
        text = update.message.text
        
        try:
            # Get current login state
            state = self.auth_states.get(user.id, {})
            
            if state.get('stage') == 'username':
                # Validate username
                if not instagram_service.validate_username(text):
                    update.message.reply_text(
                        "Invalid username. Please try again:"
                    )
                    return
                
                # Update login state
                self.auth_states[user.id].update({
                    'stage': 'password',
                    'username': text
                })
                
                update.message.reply_text(
                    "Enter your Instagram password:"
                )
            
            elif state.get('stage') == 'password':
                username = state.get('username')
                
                # Attempt Instagram login
                if instagram_service.login(username, text):
                    # Save login credentials
                    user_service.update_instagram_credentials(
                        telegram_id=user.id,
                        username=username
                    )
                    
                    # Clear login state
                    del self.auth_states[user.id]
                    
                    update.message.reply_text(
                        "🎉 Login successful! "
                        "You can now use Instagram features."
                    )
                                else:
                    # Increment login attempts
                    attempts = state.get('attempts', 0) + 1
                    
                    if attempts >= 3:
                        # Block user after 3 failed attempts
                        user_service.block_user(user.id)
                        update.message.reply_text(
                            "🚫 Too many failed login attempts. "
                            "Your account has been temporarily blocked."
                        )
                        del self.auth_states[user.id]
                    else:
                        # Update login state with new attempts
                        self.auth_states[user.id]['attempts'] = attempts
                        update.message.reply_text(
                            f"Login failed. Attempt {attempts}/3. Please try again:"
                        )
        
        except Exception as e:
            self.logger.error(f"Login flow error: {e}")
            update.message.reply_text("Login process failed. Please try again.")

    def logout(self, update: Update, context: CallbackContext):
        """
        Handle Instagram logout process
        
        :param update: Telegram update object
        :param context: Callback context
        """
        user = update.effective_user
        
        try:
            # Remove Instagram credentials
            user_service.remove_instagram_credentials(user.id)
            
            update.message.reply_text(
                "🔓 You have been logged out successfully. "
                "Your Instagram credentials have been removed."
            )
        
        except Exception as e:
            self.logger.error(f"Logout error: {e}")
            update.message.reply_text("Logout failed. Please try again.")

    def reset_password(self, update: Update, context: CallbackContext):
        """
        Initiate password reset process
        
        :param update: Telegram update object
        :param context: Callback context
        """
        user = update.effective_user
        
        try:
            # Check user registration
            db_user = user_service.get_user_by_telegram_id(user.id)
            if not db_user or not db_user.is_registered:
                update.message.reply_text(
                    "Please register first using /register"
                )
                return
            
            # Generate password reset token
            reset_token = security_manager.generate_reset_token()
            
            # Save reset token with expiration
            user_service.save_reset_token(
                telegram_id=user.id, 
                reset_token=reset_token
            )
            
            # Send reset instructions
            update.message.reply_text(
                "🔐 Password Reset\n\n"
                "To reset your password, use the following token: "
                f"`{reset_token}`\n"
                "This token will expire in 15 minutes."
            )
            
            # Set reset state
            self.auth_states[user.id] = {
                'stage': 'reset_token',
                'attempts': 0
            }
        
        except Exception as e:
            self.logger.error(f"Password reset error: {e}")
            update.message.reply_text("Password reset failed. Please try again.")

    def handle_password_reset_flow(self, update: Update, context: CallbackContext):
        """
        Handle password reset process
        
        :param update: Telegram update object
        :param context: Callback context
        """
        user = update.effective_user
        text = update.message.text
        
        try:
            state = self.auth_states.get(user.id, {})
            
            if state.get('stage') == 'reset_token':
                # Verify reset token
                if user_service.verify_reset_token(user.id, text):
                    # Prompt for new password
                    update.message.reply_text(
                        "Enter your new Instagram password:"
                    )
                    self.auth_states[user.id]['stage'] = 'new_password'
                else:
                    update.message.reply_text(
                        "Invalid or expired reset token. Please try again."
                    )
            
            elif state.get('stage') == 'new_password':
                # Update Instagram password
                user_service.update_instagram_password(
                    telegram_id=user.id, 
                    new_password=text
                )
                
                update.message.reply_text(
                    "🎉 Password reset successful! "
                    "You can now login with your new password."
                )
                
                # Clear reset state
                del self.auth_states[user.id]
        
        except Exception as e:
            self.logger.error(f"Password reset flow error: {e}")
            update.message.reply_text("Password reset failed. Please try again.")

# Create a singleton instance
auth_handler = AuthHandler()
