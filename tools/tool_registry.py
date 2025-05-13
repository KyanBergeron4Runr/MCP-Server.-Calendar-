from typing import Dict, Any, Callable, Awaitable
from pydantic import BaseModel, Field
from datetime import datetime

class AvailabilityInput(BaseModel):
    start_time: str = Field(..., description="Start time in ISO format (e.g., 2025-05-10T14:00:00Z)")
    end_time: str = Field(..., description="End time in ISO format (e.g., 2025-05-10T15:00:00Z)")

    def validate_times(self):
        try:
            datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {str(e)}")

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, input_schema: type, handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        """Register a new tool in the registry."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "handler": handler
        }

    def get_tool(self, name: str) -> Dict[str, Any]:
        """Get a tool by name."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        return self._tools[name]

    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered tools."""
        # Return only the name and description for tool discovery
        return {
            name: {
                "name": tool["name"],
                "description": tool["description"]
            }
            for name, tool in self._tools.items()
        }

# Create a singleton instance
tool_registry = ToolRegistry()

# Import and register tools
from tools.microsoft_calendar import calendar_client

# Register the check_availability tool
tool_registry.register(
    name="check_availability",
    description="Checks if the calendar has availability in a specified time range.",
    input_schema=AvailabilityInput,
    handler=calendar_client.check_availability
) 