from typing import Optional
from models import User, db

class AuthService:
    """Service for handling authentication-related operations."""
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password."""
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            return user
        
        return None
    
    @staticmethod
    def create_user(username: str, email: str, password: str, is_admin: bool = False) -> User:
        """Create a new user."""
        user = User(
            username=username,
            email=email,
            is_admin=is_admin
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return user
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get a user by their ID."""
        return User.query.get(user_id)
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Get a user by their username."""
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Get a user by their email."""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def update_user_password(user: User, new_password: str) -> bool:
        """Update a user's password."""
        try:
            user.set_password(new_password)
            user.updated_at = db.func.now()
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def update_user_profile(user: User, **kwargs) -> bool:
        """Update a user's profile information."""
        try:
            for key, value in kwargs.items():
                if hasattr(user, key) and key not in ['id', 'password_hash', 'created_at']:
                    setattr(user, key, value)
            
            user.updated_at = db.func.now()
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def toggle_user_status(user: User) -> bool:
        """Toggle a user's active status."""
        try:
            user.is_active = not user.is_active
            user.updated_at = db.func.now()
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def delete_user(user: User) -> bool:
        """Delete a user and all related data."""
        try:
            # Note: This will cascade delete conversations, messages, and custom instructions
            # due to the foreign key relationships defined in the models
            db.session.delete(user)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def get_all_users(include_inactive: bool = True) -> list:
        """Get all users, optionally including inactive ones."""
        query = User.query
        
        if not include_inactive:
            query = query.filter_by(is_active=True)
        
        return query.order_by(User.created_at.desc()).all()
    
    @staticmethod
    def get_admin_users() -> list:
        """Get all admin users."""
        return User.query.filter_by(is_admin=True, is_active=True).all()
    
    @staticmethod
    def promote_to_admin(user: User) -> bool:
        """Promote a user to admin status."""
        try:
            user.is_admin = True
            user.updated_at = db.func.now()
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def demote_from_admin(user: User) -> bool:
        """Remove admin status from a user."""
        try:
            user.is_admin = False
            user.updated_at = db.func.now()
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def validate_user_data(username: str, email: str, user_id: int = None) -> dict:
        """Validate user data and return any errors."""
        errors = {}
        
        # Check username uniqueness
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and (user_id is None or existing_user.id != user_id):
            errors['username'] = 'Username already exists'
        
        # Check email uniqueness
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and (user_id is None or existing_email.id != user_id):
            errors['email'] = 'Email already exists'
        
        # Validate username format
        if len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters long'
        
        if not username.replace('_', '').replace('-', '').isalnum():
            errors['username'] = 'Username can only contain letters, numbers, underscores, and hyphens'
        
        return errors
    
    @staticmethod
    def get_user_stats(user: User) -> dict:
        """Get statistics for a specific user."""
        from models import Conversation, Message, CustomInstruction
        
        # Count conversations
        conversation_count = Conversation.query.filter_by(user_id=user.id).count()
        
        # Count messages
        message_count = db.session.query(Message).join(Conversation)\
                                 .filter(Conversation.user_id == user.id).count()
        
        # Count custom instructions
        instruction_count = CustomInstruction.query.filter_by(user_id=user.id).count()
        
        # Get most recent conversation
        last_conversation = Conversation.query.filter_by(user_id=user.id)\
                                            .order_by(Conversation.updated_at.desc())\
                                            .first()
        
        return {
            'conversation_count': conversation_count,
            'message_count': message_count,
            'custom_instruction_count': instruction_count,
            'last_active': last_conversation.updated_at.isoformat() if last_conversation else None,
            'account_age_days': (db.func.now() - user.created_at).days if user.created_at else 0
        }
