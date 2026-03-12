"""
The Bible Catalog Platform Configuration Settings
"""
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# ==============================================================================
# 1. CORE CONSTANTS
# ==============================================================================

VALID_ENVS = ['dev', 'ua', 'prod']

# ==============================================================================
# 2. PATH RESOLUTION LOGIC
# ==============================================================================

def find_project_root() -> Path:
    """
    Find the project root by looking for common project indicators.
    Starts from current file location and searches upward.
    """
    current = Path(__file__).resolve().parent
    
    # Look for project indicators (customize these for your project)
    project_indicators = [
        "requirements.txt",
        "pyproject.toml", 
        "setup.py",
        ".git",
        "config/.env",
        "the-bible-catalog" # Your project folder name
    ]
    
    # Search upward for project root
    for parent in [current] + list(current.parents):
        for indicator in project_indicators:
            if (parent / indicator).exists():
                return parent
    
    # Fallback to current directory if no indicators found
    return current

# Get project root and construct config path
PROJECT_ROOT = find_project_root()
ENV_PATH = PROJECT_ROOT / "config" / ".env"

# ==============================================================================
# 3. ENVIRONMENT LOADING
# ==============================================================================

# Load environment variables from .env file (if it exists)
load_dotenv(dotenv_path=ENV_PATH)

# ==============================================================================
# 4. CORE ENVIRONMENT INITIALIZATION
# ==============================================================================

# Determine the final environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Set environment-dependent variables
if ENVIRONMENT == "dev":
    DEBUG = True
    
elif ENVIRONMENT == "ua":
    DEBUG = False
    
elif ENVIRONMENT == "prod":
    DEBUG = False

# ==============================================================================
# 5. CONFIGURATION VARIABLES
# ==============================================================================

# MotherDuck Database configuration
DATABASE_CONFIG = {
    "motherduck_token": os.getenv("MOTHERDUCK_TOKEN"),
    "connection_timeout": 30,
}

# External service configuration
EXTERNAL_SERVICES = {
    "discord_webhook": os.getenv("DISCORD_WEBHOOK"),
    "esv_api_token": os.getenv("ESV_API_TOKEN")
}

# External service configuration
MODEL = {
    "embedding_model": "nomic-embed-text:v1.5"
}

# ==============================================================================
# 6. UTILITY FUNCTIONS
# ==============================================================================

def validate_settings() -> bool:
    """Validate configuration settings"""
    
    # Detect if running in CI/CD environment
    is_cicd = os.getenv("CI") or os.getenv("GITHUB_ACTIONS")
    
    # Check if .env file exists (only required in local development)
    if not ENV_PATH.exists() and not is_cicd:
        print(f"Warning: .env file not found at {ENV_PATH}")
        print("Please create the .env file with required environment variables.")
        print(f"Expected location: {ENV_PATH}")
        # Don't return False - allow environment variables from CI/CD to work
    
    # Validate MotherDuck configuration
    if not DATABASE_CONFIG["motherduck_token"]:
        if is_cicd:
            print("Error: MOTHERDUCK_TOKEN not set in CI/CD environment variables.")
        else:
            print("Warning: MOTHERDUCK_TOKEN not set in environment variables or .env file.")
        return False
    
    # print("✅ Configuration validated successfully!")
    return True

# ==============================================================================
# 7. INITIALIZATION
# ==============================================================================

# Initialize settings validation
validate_settings()