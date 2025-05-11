import os
import logging
from dotenv import load_dotenv
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

# Load environment variables before importing other modules
load_dotenv()

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
    uvicorn.run(app, host="0.0.0.0", port=5000) 