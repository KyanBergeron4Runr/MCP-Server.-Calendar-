from typing import Dict, Any, Callable, Awaitable
from pydantic import BaseModel, Field
from datetime import datetime
from schemas.calendar_schemas import CheckMeetingAtTimeInput

class AvailabilityInput(BaseModel):
    start_time: str = Field(..., description="Start time in ISO format (e.g., 2025-05-10T14:00:00Z)")
    end_time: str = Field(..., description="End time in ISO format (e.g., 2025-05-10T15:00:00Z)")

    def validate_times(self):
        try:
            datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {str(e)}")

class CreateMeetingInput(BaseModel):
    title: str = Field(..., description="Title of the meeting")
    start_time: str = Field(..., description="Start time in ISO format (e.g., 2025-05-10T14:00:00Z)")
    end_time: str = Field(..., description="End time in ISO format (e.g., 2025-05-10T15:00:00Z)")
    description: str = Field("", description="Optional description of the meeting")
    location: str = Field("", description="Optional location of the meeting")
    body: str = Field("", description="Optional additional message or invitation content")

    def validate_times(self):
        try:
            datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {str(e)}")

class UpdateMeetingInput(BaseModel):
    event_id: str = Field(..., description="ID of the event to update")
    title: str = Field(..., description="New title of the meeting")
    start_time: str = Field(..., description="New start time in ISO format")
    end_time: str = Field(..., description="New end time in ISO format")
    description: str = Field("", description="New description of the meeting")
    location: str = Field("", description="New location of the meeting")
    body: str = Field("", description="New additional message or invitation content")

    def validate_times(self):
        try:
            datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {str(e)}")

class DeleteMeetingInput(BaseModel):
    event_id: str = Field(..., description="ID of the event to delete")

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

# Register all calendar tools
tool_registry.register(
    name="check_availability",
    description="Check if your calendar is free or busy during a specific time range. Returns 'available: true' if there are no events in the given period, otherwise 'available: false'. Parameters: start_time (ISO 8601, e.g. '2025-05-10T14:00:00Z'), end_time (ISO 8601, e.g. '2025-05-10T15:00:00Z').",
    input_schema=AvailabilityInput,
    handler=calendar_client.check_availability
)

tool_registry.register(
    name="create_meeting",
    description="Create a new meeting in your Outlook calendar. Parameters: title (string, required), start_time (ISO 8601, required), end_time (ISO 8601, required), description (string, optional), location (string, optional, e.g. meeting room, address, or online link), body (string, optional, additional message or invitation content). Returns the event ID and status.",
    input_schema=CreateMeetingInput,
    handler=calendar_client.add_event
)

tool_registry.register(
    name="update_meeting",
    description="Update an existing meeting in your Outlook calendar. Parameters: event_id (string, required), title (string, required), start_time (ISO 8601, required), end_time (ISO 8601, required), description (string, optional), location (string, optional), body (string, optional). Returns the event ID and status.",
    input_schema=UpdateMeetingInput,
    handler=calendar_client.update_event
)

tool_registry.register(
    name="delete_meeting",
    description="Delete a meeting from your Outlook calendar. Parameters: event_id (string, required). Returns the event ID and status.",
    input_schema=DeleteMeetingInput,
    handler=calendar_client.delete_event
)

tool_registry.register(
    name="find_meetings_near_time",
    description="Find all meetings or events in your Outlook calendar that overlap with a specific time window around a given date and time. Useful for checking if you have any meetings scheduled near a particular moment.\n\nParameters:\n- date: string, e.g. '2025-05-19' (required)\n- time: string, e.g. '12:00' (required, 24-hour format)\n- timezone: string, e.g. 'America/New_York' (optional, default: UTC)\n- window_minutes: integer, e.g. 15 (optional, default: 15). This is the number of minutes before and after the specified time to search for overlapping meetings.\n\nReturns a list of meetings (with subject, start, end, and location) that overlap with the window, and a boolean 'has_meeting'.\n\nExample usage:\n{ 'date': '2025-05-19', 'time': '12:00', 'timezone': 'America/New_York', 'window_minutes': 15 }\n\nNote: window_minutes must be an integer, not a string.",
    input_schema=CheckMeetingAtTimeInput,
    handler=calendar_client.find_meetings_near_time
) 