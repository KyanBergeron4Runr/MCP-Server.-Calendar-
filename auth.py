from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from typing import Optional
import os
# Environment variables are managed by Replit Secrets Manager. Do not use .env or load_dotenv().

# Get API key from environment variable
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise Exception("API_KEY environment variable is not set")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    """
    Validate the API key from the request header.
    """
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(
        status_code=403,
        detail="Invalid API Key"
    )
