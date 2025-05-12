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

<<<<<<< HEAD
# Validate required environment variables
required_env_vars = {
    'API_KEY': 'API key for authentication',
    'MS_CLIENT_ID': 'Microsoft Graph API Client ID',
    'MS_CLIENT_SECRET': 'Microsoft Graph API Client Secret',
    'MS_TENANT_ID': 'Microsoft Graph API Tenant ID',
    'MS_USER_ID': 'Microsoft Graph API User ID'
}

missing_vars = [var for var, desc in required_env_vars.items() if not os.getenv(var)]
=======
# Set environment variables programmatically
os.environ['API_KEY'] = 'your-api-key-here'
os.environ['MS_CLIENT_ID'] = 'your-client-id'
os.environ['MS_CLIENT_SECRET'] = 'your-client-secret'
os.environ['MS_TENANT_ID'] = 'your-tenant-id'
os.environ['MS_USER_ID'] = 'your-user-id'

# Validate environment variables
required_env_vars = ['API_KEY', 'MS_CLIENT_ID', 'MS_CLIENT_SECRET', 'MS_TENANT_ID', 'MS_USER_ID']
missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
>>>>>>> 3232f363c8f86c54837ae7b2b56a72f72f78bc6e
if missing_vars:
    error_msg = "Missing required environment variables:\n"
    for var in missing_vars:
        error_msg += f"- {var}: {required_env_vars[var]}\n"
    logger.error(error_msg)
    raise EnvironmentError(error_msg)

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
    """Generate SSE events for tool availability."""
    while True:
        try:
            # Send all tools as a single event
            tools = tool_registry.get_all_tools()
            yield {
                "event": "tools",
                "data": json.dumps({"tools": list(tools.values())})
            }
            await asyncio.sleep(30)  # Update every 30 seconds
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