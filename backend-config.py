import os
from datetime import timedelta

# Base configuration class
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret_key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Groq API settings
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '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')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'meta-llama/characteristics')
    
    # Admin user initial password
    ADMIN_INITIAL_PASSWORD = os.getenv('ADMIN_INITIAL_PASSWORD', 'scubaadmin')
    
    # CORS settings
    CORS_ORIGIN = os.getenv('CORS_ORIGIN', '*')

# Development configuration
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///data/scubaai_dev.db')

# Testing configuration
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///data/scubaai_test.db')

# Production configuration
class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///data/scubaai.db')
    
    # Enhanced security settings for production
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_SAMESITE = 'Lax'

# Configuration dictionary
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}