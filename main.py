import os
import logging
# Environment variables are managed by Replit Secrets Manager. Do not use .env or load_dotenv().
import json
import asyncio
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_required_env_var(name: str, description: str) -> str:
    """Get a required environment variable with proper error handling."""
    value = os.getenv(name)
    if not value:
        error_msg = f"Required environment variable '{name}' ({description}) is not set. Please set it in Replit Secrets."
        logger.error(error_msg)
        raise EnvironmentError(error_msg)
    return value

# Get required environment variables
try:
    API_KEY = get_required_env_var("API_KEY", "API key for authentication")
    MS_CLIENT_ID = get_required_env_var("MS_CLIENT_ID", "Microsoft Graph API Client ID")
    MS_CLIENT_SECRET = get_required_env_var("MS_CLIENT_SECRET", "Microsoft Graph API Client Secret")
    MS_TENANT_ID = get_required_env_var("MS_TENANT_ID", "Microsoft Graph API Tenant ID")
    MS_USER_ID = get_required_env_var("MS_USER_ID", "Microsoft Graph API User ID")
    
    logger.info("All required environment variables are set")
except EnvironmentError as e:
    logger.error(f"Environment setup failed: {str(e)}")
    raise

try:
    from auth import get_api_key
    from tools.tool_registry import tool_registry
except Exception as e:
    logger.error(f"Error importing modules: {str(e)}")
    raise

app = FastAPI(title="MCP Calendar Tool Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def event_generator():
    """Generate SSE events for tool availability and keep connection alive with pings."""
    ping_interval = 10
    tools_interval = 30
    last_tools_sent = 0
    while True:
        now = datetime.utcnow().timestamp()
        try:
            # Send tools event every tools_interval seconds
            if now - last_tools_sent > tools_interval:
                tools = tool_registry.get_all_tools()
                logger.info(f"Sending tools event: {list(tools.keys())}")
                yield {
                    "event": "tools",
                    "data": json.dumps({"tools": list(tools.values())})
                }
                last_tools_sent = now
            # Always send a ping event every ping_interval seconds
            logger.info("Sending ping event")
            yield {
                "event": "ping",
                "data": datetime.utcnow().isoformat()
            }
            await asyncio.sleep(ping_interval)
        except Exception as e:
            logger.error(f"Error in event generator: {str(e)}")
            await asyncio.sleep(5)  # Wait a bit before retrying

@app.get("/mcp-events")
async def mcp_events():
    """SSE endpoint for tool discovery."""
    return EventSourceResponse(event_generator())

@app.post("/mcp/message")
async def handle_message(request: Request, api_key: str = Depends(get_api_key)):
    """Handle tool execution requests."""
    try:
        data = await request.json()
        tool_call = data.get("toolCall", {})
        tool_name = tool_call.get("toolName")
        parameters = tool_call.get("parameters", {})

        if not tool_name:
            raise HTTPException(status_code=400, detail="No tool name provided")

        try:
            tool = tool_registry.get_tool(tool_name)
            # Validate input using the tool's schema
            input_schema = tool["input_schema"]
            validated_params = input_schema(**parameters)
            validated_params.validate_times()  # Additional validation for datetime fields
            
            # Execute the tool
            result = await tool["handler"](parameters)
            return result
            
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "MCP Server is running 🚀"}

@app.get("/test")
def test():
    return {"test": True}

if __name__ == "__main__":
    import uvicorn
    try:
        port = int(os.getenv('PORT', 5000))
        host = os.getenv('HOST', '0.0.0.0')
        log_level = os.getenv('LOG_LEVEL', 'info').lower()
        
        logger.info(f"Starting server on {host}:{port}")
        logger.info("Environment variables loaded successfully")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=log_level
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise 