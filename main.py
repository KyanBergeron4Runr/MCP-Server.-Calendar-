import os
import logging
# Environment variables are managed by Replit Secrets Manager
import json
import asyncio
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# Import auth module first
from auth import get_api_key

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_required_env_var(name: str, description: str) -> str:
    """Get a required environment variable from Replit Secrets."""
    value = os.environ.get(name)
    if not value:
        error_msg = f"Required environment variable '{name}' ({description}) is not set in Replit Secrets."
        logger.error(error_msg)
        raise EnvironmentError(error_msg)
    return value

# Initialize FastAPI app
app = FastAPI(
    title="MCP Calendar Tool Server",
    description="A FastAPI server that provides calendar management tools for AI agents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for environment and dependencies
tool_registry = None

@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    global tool_registry
    
    try:
        # Get required environment variables from Replit Secrets
        required_vars = {
            "API_KEY": os.environ.get("API_KEY"),
            "MS_CLIENT_ID": os.environ.get("MS_CLIENT_ID"),
            "MS_CLIENT_SECRET": os.environ.get("MS_CLIENT_SECRET"),
            "MS_TENANT_ID": os.environ.get("MS_TENANT_ID"),
            "MS_USER_ID": os.environ.get("MS_USER_ID")
        }

        # Check for missing secrets
        missing_vars = [key for key, value in required_vars.items() if not value]
        if missing_vars:
            error_msg = f"Missing required environment variables in Replit Secrets: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise EnvironmentError(error_msg)

        logger.info("Environment variables loaded successfully from Replit Secrets")
        
        # Import and initialize dependencies
        from tools.tool_registry import tool_registry as registry
        tool_registry = registry
        logger.info("Dependencies initialized successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise Exception(f"Startup failed: {str(e)}")

async def event_generator():
    """Generate SSE events for tool availability and keep connection alive with pings."""
    if not tool_registry:
        logger.error("Tool registry not initialized")
        yield {
            "event": "error",
            "data": json.dumps({"error": "Tool registry not initialized"})
        }
        return

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
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
            await asyncio.sleep(5)  # Wait a bit before retrying

@app.get("/mcp-events")
async def mcp_events():
    """SSE endpoint for tool discovery."""
    if not tool_registry:
        raise HTTPException(
            status_code=503,
            detail="Tool registry not initialized. Please check server logs."
        )
    return EventSourceResponse(event_generator())

@app.post("/mcp/message")
async def handle_message(request: Request, api_key: str = Depends(get_api_key)):
    """Handle tool execution requests."""
    if not tool_registry:
        raise HTTPException(
            status_code=503,
            detail="Tool registry not initialized. Please check server logs."
        )
        
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
    """Root endpoint to check if the server is running."""
    return {
        "message": "MCP Server is running 🚀",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/test")
def test():
    """Test endpoint to verify basic functionality."""
    return {
        "test": True,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    try:
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')
        log_level = os.environ.get('LOG_LEVEL', 'info').lower()
        
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
        raise Exception(f"Failed to start server: {str(e)}") 