import os
import logging
# Environment variables are managed by Replit Secrets Manager. Do not use .env or load_dotenv().
import json
import asyncio
from datetime import datetime
from typing import Dict, Any
import sys
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_environment():
    """Validate all required environment variables are set."""
    required_vars = {
        "API_KEY": "API key for authentication",
        "MS_CLIENT_ID": "Microsoft Graph API Client ID",
        "MS_CLIENT_SECRET": "Microsoft Graph API Client Secret",
        "MS_TENANT_ID": "Microsoft Graph API Tenant ID",
        "MS_USER_ID": "Microsoft Graph API User ID"
    }
    
    missing_vars = []
    for var_name, description in required_vars.items():
        if not os.environ.get(var_name):
            missing_vars.append(f"{var_name} ({description})")
    
    if missing_vars:
        env_keys = [k for k in os.environ.keys() if k.startswith('MS_') or k == 'API_KEY']
        error_msg = (
            f"\n\nERROR: The following required environment variables are missing:\n"
            f"{chr(10).join(f'- {var}' for var in missing_vars)}\n"
            f"Set them in the Replit Secrets tab.\n"
            f"Current env: {env_keys}\n\n"
        )
        logger.critical(error_msg)
        raise EnvironmentError(error_msg)
    
    logger.info("All required environment variables are set")

def initialize_app():
    """Initialize the FastAPI application with proper error handling."""
    try:
        # Import required modules
        from auth import get_api_key
        from tools.tool_registry import tool_registry
        
        # Create FastAPI app
        app = FastAPI(title="MCP Calendar Tool Server")
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, replace with specific origins
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Configure FastAPI for better memory usage
        app.state.max_request_size = 1024 * 1024  # 1MB max request size
        app.state.max_response_size = 1024 * 1024  # 1MB max response size
        
        return app, tool_registry, get_api_key
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise

# Validate environment variables first
validate_environment()

# Initialize the application
try:
    app, tool_registry, get_api_key = initialize_app()
except Exception as e:
    logger.critical(f"Application initialization failed: {str(e)}")
    sys.exit(1)

async def event_generator():
    """Generate SSE events for tool availability and keep connection alive with pings."""
    ping_interval = 10
    tools_interval = 30
    last_tools_sent = 0
    
    while True:
        try:
            now = datetime.utcnow().timestamp()
            
            # Send tools event every tools_interval seconds
            if now - last_tools_sent > tools_interval:
                tools = tool_registry._tools
                tool_info = []
                
                for name, tool in tools.items():
                    try:
                        schema = tool["input_schema"].model_json_schema()
                        params = {}
                        
                        for prop, prop_info in schema.get("properties", {}).items():
                            param_info = {
                                "type": prop_info.get("type", "string"),
                                "description": prop_info.get("description", ""),
                                "required": prop in schema.get("required", [])
                            }
                            
                            if "format" in prop_info:
                                param_info["format"] = prop_info["format"]
                            if "enum" in prop_info:
                                param_info["enum"] = prop_info["enum"]
                            if "default" in prop_info:
                                param_info["default"] = prop_info["default"]
                                
                            params[prop] = param_info
                        
                        tool_info.append({
                            "name": name,
                            "description": tool.get("description", ""),
                            "parameters": params
                        })
                    except Exception as e:
                        logger.error(f"Error processing tool {name}: {str(e)}")
                        continue
                
                try:
                    tools_data = json.dumps({"tools": tool_info})
                    yield {
                        "event": "tools",
                        "data": tools_data,
                        "retry": 30000,
                        "id": str(int(now * 1000))
                    }
                    yield {"data": ""}
                    last_tools_sent = now
                except Exception as e:
                    logger.error(f"Error sending tools event: {str(e)}")
            
            # Send ping event
            try:
                yield {
                    "event": "ping",
                    "data": datetime.utcnow().isoformat(),
                    "retry": 30000,
                    "id": str(int(now * 1000))
                }
                yield {"data": ""}
            except Exception as e:
                logger.error(f"Error sending ping event: {str(e)}")
            
            await asyncio.sleep(ping_interval)
            
        except Exception as e:
            logger.error(f"Error in event generator: {str(e)}")
            await asyncio.sleep(5)

@app.get("/mcp-events")
async def mcp_events():
    """SSE endpoint for tool discovery."""
    return EventSourceResponse(
        event_generator(),
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*"
        }
    )

def to_serializable(obj):
    """Convert objects to JSON-serializable format."""
    try:
        if isinstance(obj, BaseModel):
            return obj.dict()
        elif isinstance(obj, dict):
            return {k: to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [to_serializable(i) for i in obj]
        else:
            return obj
    except Exception as e:
        logger.error(f"Error serializing object: {str(e)}")
        return str(obj)

@app.post("/mcp/message")
async def handle_message(request: Request, api_key: str = Depends(get_api_key)):
    """Handle tool execution requests."""
    try:
        body = await request.json()
        logger.info("📥 Received toolCall: %s", json.dumps(body, indent=2))
        
        tool_call = body.get("toolCall", {})
        tool_name = tool_call.get("toolName")
        parameters = tool_call.get("parameters", {})

        if not tool_name:
            logger.error("❌ No tool name provided in request")
            raise HTTPException(status_code=400, detail="No tool name provided")

        try:
            tool = tool_registry.get_tool(tool_name)
            logger.info("🔧 Executing tool: %s with parameters: %s", tool_name, json.dumps(parameters, indent=2))
            
            input_schema = tool["input_schema"]
            validated_params = input_schema(**parameters)
            
            if hasattr(validated_params, "validate_times"):
                validated_params.validate_times()
            
            result = await tool["handler"](validated_params.dict())
            result = to_serializable(result)
            
            response = {
                "toolResponse": {
                    "toolName": tool_name,
                    "output": result
                }
            }
            logger.info("✅ Tool executed: %s", json.dumps(response, indent=2))
            return response
            
        except KeyError as e:
            logger.error("❌ Tool not found: %s", str(e))
            raise HTTPException(status_code=404, detail=f"Tool not found: {str(e)}")
        except ValueError as e:
            logger.error("❌ Invalid parameters: %s", str(e))
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("❌ Tool failed: %s", str(e))
            raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")
        
    except json.JSONDecodeError as e:
        logger.error("❌ Invalid JSON in request: %s", str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON in request")
    except Exception as e:
        logger.error("❌ Error processing message: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    """Root endpoint to verify server is running."""
    return {"message": "MCP Server is running 🚀", "status": "healthy"}

@app.get("/test")
def test():
    """Test endpoint for basic connectivity."""
    return {"test": True, "timestamp": datetime.utcnow().isoformat()}

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
            log_level=log_level,
            workers=1,
            limit_concurrency=100,
            backlog=2048,
            timeout_keep_alive=30
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}")
        sys.exit(1) 