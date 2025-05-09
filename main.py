from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import json
import asyncio
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Calendar Tool Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock tool registry - will be replaced with actual tool registry
TOOLS = {
    "calendar.check_availability": {
        "name": "check_availability",
        "description": "Check calendar availability for a given time range",
        "parameters": {
            "type": "object",
            "properties": {
                "start_time": {"type": "string", "format": "date-time"},
                "end_time": {"type": "string", "format": "date-time"}
            },
            "required": ["start_time", "end_time"]
        }
    },
    "calendar.add_event": {
        "name": "add_event",
        "description": "Add a new calendar event",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start_time": {"type": "string", "format": "date-time"},
                "end_time": {"type": "string", "format": "date-time"},
                "description": {"type": "string"}
            },
            "required": ["title", "start_time", "end_time"]
        }
    },
    "calendar.update_event": {
        "name": "update_event",
        "description": "Update an existing calendar event",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string"},
                "title": {"type": "string"},
                "start_time": {"type": "string", "format": "date-time"},
                "end_time": {"type": "string", "format": "date-time"},
                "description": {"type": "string"}
            },
            "required": ["event_id"]
        }
    },
    "calendar.delete_event": {
        "name": "delete_event",
        "description": "Delete a calendar event",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string"}
            },
            "required": ["event_id"]
        }
    }
}

async def event_generator():
    """Generate SSE events for tool availability."""
    while True:
        # Send all tools as a single event
        yield {
            "event": "tools",
            "data": json.dumps({"tools": list(TOOLS.values())})
        }
        await asyncio.sleep(30)  # Update every 30 seconds

@app.get("/mcp-events")
async def mcp_events():
    """SSE endpoint for tool discovery."""
    return EventSourceResponse(event_generator())

@app.post("/mcp/message")
async def handle_message(request: Request):
    """Handle tool execution requests."""
    try:
        data = await request.json()
        tool_name = data.get("name")
        parameters = data.get("parameters", {})

        if not tool_name or tool_name not in TOOLS:
            raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

        # Mock responses for now
        if tool_name == "calendar.check_availability":
            return {"available": True, "slots": ["2024-01-01T10:00:00Z", "2024-01-01T11:00:00Z"]}
        elif tool_name == "calendar.add_event":
            return {"event_id": "mock_event_123", "status": "created"}
        elif tool_name == "calendar.update_event":
            return {"event_id": parameters.get("event_id"), "status": "updated"}
        elif tool_name == "calendar.delete_event":
            return {"event_id": parameters.get("event_id"), "status": "deleted"}
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000) 