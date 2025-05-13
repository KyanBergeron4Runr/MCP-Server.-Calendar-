from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Environment variables are managed by Replit Secrets Manager. Do not use .env or load_dotenv().
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """Validate the API key from the request header."""
    if not api_key_header:
        raise HTTPException(
            status_code=401,
            detail="API key is missing"
        )
    
    # Get API key from environment variables
    api_key = os.environ.get("API_KEY")
    if not api_key:
        logger.error("API_KEY not found in environment variables")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error"
        )
    
    if api_key_header != api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return api_key_header

