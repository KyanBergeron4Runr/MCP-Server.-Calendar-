from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from typing import Optional
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Environment variables are managed by Replit Secrets Manager. Do not use .env or load_dotenv().
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    logger.error("API_KEY environment variable is not set")
    raise EnvironmentError("API_KEY environment variable is not set. Please set it in Replit Secrets.")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    """
    Validate the API key from the request header.
    """
    if not api_key_header:
        raise HTTPException(
            status_code=403,
            detail="API Key header is missing"
        )
    
    if api_key_header == API_KEY:
        return api_key_header
        
    logger.warning("Invalid API key attempt")
    raise HTTPException(
        status_code=403,
        detail="Invalid API Key"
    )
