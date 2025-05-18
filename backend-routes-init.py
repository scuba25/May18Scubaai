from flask import Blueprint

from .auth import auth_routes
from .chat import chat_routes
from .settings import settings_routes

def register_routes(app):
    """Register all API routes with the Flask application."""
    
    # Create a main API blueprint
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    
    # Register route blueprints
    api_bp.register_blueprint(auth_routes)
    api_bp.register_blueprint(chat_routes)
    api_bp.register_blueprint(settings_routes)
    
    # Register the main API blueprint with the app
    app.register_blueprint(api_bp)