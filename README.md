# MCP Calendar Tool Server

A FastAPI-based MCP (Model Context Protocol) server that provides calendar management tools for AI agents running in n8n.

## Features

- Server-Sent Events (SSE) for real-time tool discovery
- HTTP endpoints for tool execution
- Calendar management tools:
  - Check availability
  - Add events
  - Update events
  - Delete events
- API key authentication
- Mock implementations ready for real calendar API integration

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API key:
   ```
   API_KEY=your-secret-key-here
   ```

## Running the Server

```bash
uvicorn main:app --host 0.0.0.0 --port 5000
```

## API Endpoints

### Tool Discovery
- `GET /mcp-events`
  - SSE stream of available tools
  - Used by n8n MCP Client for tool discovery

### Tool Execution
- `POST /mcp/message`
  - Execute calendar tools
  - Requires `X-API-Key` header
  - Accepts JSON payload with tool name and parameters

## Available Tools

### Check Availability
```json
{
  "name": "calendar.check_availability",
  "parameters": {
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": "2024-01-01T11:00:00Z"
  }
}
```

### Add Event
```json
{
  "name": "calendar.add_event",
  "parameters": {
    "title": "Meeting",
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": "2024-01-01T11:00:00Z",
    "description": "Team meeting"
  }
}
```

### Update Event
```json
{
  "name": "calendar.update_event",
  "parameters": {
    "event_id": "event_123",
    "title": "Updated Meeting",
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": "2024-01-01T11:00:00Z",
    "description": "Updated team meeting"
  }
}
```

### Delete Event
```json
{
  "name": "calendar.delete_event",
  "parameters": {
    "event_id": "event_123"
  }
}
```

## Development

The project is structured as follows:

```
/my_mcp_server/
├── main.py              # FastAPI app and routes
├── auth.py             # API key authentication
├── tools/
│   └── calendar.py     # Calendar tool implementations
├── schemas/
│   └── calendar_schemas.py  # Pydantic models
└── requirements.txt    # Python dependencies
```

## Testing

1. Start the server
2. Use the n8n MCP Client node to connect to `http://localhost:8000/mcp-events`
3. Test tool execution using the `/mcp/message` endpoint

## Future Improvements

- Integration with real calendar APIs (Google Calendar, Cal.com, etc.)
- Enhanced error handling and validation
- Rate limiting and request throttling
- Additional calendar management features
- Webhook support for event notifications 