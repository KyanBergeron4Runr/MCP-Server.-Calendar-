from typing import Dict, Any, Callable, Awaitable
from pydantic import BaseModel, Field
from datetime import datetime

class AvailabilityInput(BaseModel):
    start_time: str = Field(
        ...,
        description="Start time in ISO format (e.g., 2025-05-10T14:00:00Z)",
        example="2025-05-10T14:00:00Z"
    )
    end_time: str = Field(
        ...,
        description="End time in ISO format (e.g., 2025-05-10T15:00:00Z)",
        example="2025-05-10T15:00:00Z"
    )

    def validate_times(self):
        try:
            datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {str(e)}")

class CreateMeetingInput(BaseModel):
    title: str = Field(
        ...,
        description="Title of the meeting",
        example="Team Sync Meeting"
    )
    start_time: str = Field(
        ...,
        description="Start time in ISO format (e.g., 2025-05-10T14:00:00Z)",
        example="2025-05-10T14:00:00Z"
    )
    end_time: str = Field(
        ...,
        description="End time in ISO format (e.g., 2025-05-10T15:00:00Z)",
        example="2025-05-10T15:00:00Z"
    )
    description: str = Field(
        "",
        description="Optional description of the meeting",
        example="Weekly team sync to discuss project progress"
    )

    def validate_times(self):
        try:
            datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {str(e)}")

class UpdateMeetingInput(BaseModel):
    event_id: str = Field(
        ...,
        description="ID of the event to update",
        example="event_123"
    )
    title: str = Field(
        ...,
        description="New title of the meeting",
        example="Updated Team Sync"
    )
    start_time: str = Field(
        ...,
        description="New start time in ISO format",
        example="2025-05-10T15:00:00Z"
    )
    end_time: str = Field(
        ...,
        description="New end time in ISO format",
        example="2025-05-10T16:00:00Z"
    )
    description: str = Field(
        "",
        description="New description of the meeting",
        example="Updated weekly team sync with new agenda"
    )

    def validate_times(self):
        try:
            datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
            datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
        except ValueError as e:
            raise ValueError(f"Invalid datetime format: {str(e)}")

class DeleteMeetingInput(BaseModel):
    event_id: str = Field(
        ...,
        description="ID of the event to delete",
        example="event_123"
    )

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, input_schema: type, handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]):
        """Register a new tool in the registry."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "input_schema": input_schema,
            "handler": handler,
            "examples": self._get_examples(input_schema)
        }

    def _get_examples(self, schema: type) -> Dict[str, Any]:
        """Generate example values from the schema."""
        if not hasattr(schema, "schema"):
            return {}
        
        examples = {}
        for field_name, field in schema.__fields__.items():
            if hasattr(field, "field_info") and hasattr(field.field_info, "example"):
                examples[field_name] = field.field_info.example
        return examples

    def get_tool(self, name: str) -> Dict[str, Any]:
        """Get a tool by name."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        return self._tools[name]

    def get_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered tools."""
        # Return name, description, and examples for tool discovery
        return {
            name: {
                "name": tool["name"],
                "description": tool["description"],
                "examples": tool["examples"]
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
    description="Checks if the calendar has availability in a specified time range. Returns available time slots.",
    input_schema=AvailabilityInput,
    handler=calendar_client.check_availability
)

tool_registry.register(
    name="create_meeting",
    description="Creates a new meeting in the calendar. Requires title, start time, end time, and optional description.",
    input_schema=CreateMeetingInput,
    handler=calendar_client.add_event
)

tool_registry.register(
    name="update_meeting",
    description="Updates an existing meeting in the calendar. Requires event ID and new meeting details.",
    input_schema=UpdateMeetingInput,
    handler=calendar_client.update_event
)

tool_registry.register(
    name="delete_meeting",
    description="Deletes a meeting from the calendar. Requires the event ID.",
    input_schema=DeleteMeetingInput,
    handler=calendar_client.delete_event
) 