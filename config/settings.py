"""
AI Quiz Platform - Configuration Settings
Version: 1.1.0
Changelog: Removed Gemini API integration, now using only Claude and GPT via Bedrock
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings from environment variables"""
    
    # AWS Bedrock
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    BEDROCK_LLM_ID_CLAUDE = os.getenv('BEDROCK_LLM_ID_CLAUDE')
    BEDROCK_LLM_ID_GPT = os.getenv('BEDROCK_LLM_ID_GPT')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Admin Credentials
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
    
    # Application
    APP_NAME = os.getenv('APP_NAME', 'AI Quiz Platform')
    APP_PORT = int(os.getenv('APP_PORT', 8501))
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
    
    # LLM Settings
    LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', 15))
    LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', 1000))
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.1))
    
    # Quiz Settings
    QUESTION_COUNTS = [5, 10, 15, 20, 25]
    DIFFICULTY_LEVELS = ['Easy', 'Medium', 'Hard']
    TARGET_LEVELS = ['Beginner', 'Intermediate', 'Advanced']
    
    # Difficulty Mix Ratios (for selected difficulty)
    DIFFICULTY_MIX = {
        'Easy': {'Easy': 0.7, 'Medium': 0.2, 'Hard': 0.1},
        'Medium': {'Easy': 0.2, 'Medium': 0.7, 'Hard': 0.1},
        'Hard': {'Easy': 0.1, 'Medium': 0.2, 'Hard': 0.7}
    }
    
    # Recent questions tracking
    RECENT_ATTEMPTS_TO_AVOID = 3
    
    @classmethod
    def validate(cls):
        """Validate required settings"""
        required = [
            ('AWS_ACCESS_KEY_ID', cls.AWS_ACCESS_KEY_ID),
            ('AWS_SECRET_ACCESS_KEY', cls.AWS_SECRET_ACCESS_KEY),
            ('BEDROCK_LLM_ID_CLAUDE', cls.BEDROCK_LLM_ID_CLAUDE),
            ('BEDROCK_LLM_ID_GPT', cls.BEDROCK_LLM_ID_GPT),
            ('DATABASE_URL', cls.DATABASE_URL),
        ]
        
        missing = [name for name, value in required if not value]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True

settings = Settings()