from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from msgraph import GraphServiceClient
from azure.identity import ClientSecretCredential
import os
# Environment variables are managed by Replit Secrets Manager. Do not use .env or load_dotenv().
import logging
from schemas.calendar_schemas import (
    TimeRange,
    AvailabilityResponse,
    EventCreate,
    EventUpdate,
    EventDelete,
    EventResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MicrosoftCalendarClient:
    def __init__(self):
        self.client = None
        self.user_id = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Microsoft Graph client with credentials."""
        try:
            # Get required environment variables
            required_vars = {
                "MS_CLIENT_ID": os.getenv("MS_CLIENT_ID"),
                "MS_CLIENT_SECRET": os.getenv("MS_CLIENT_SECRET"),
                "MS_TENANT_ID": os.getenv("MS_TENANT_ID"),
                "MS_USER_ID": os.getenv("MS_USER_ID")
            }
            
            # Check for missing variables
            missing_vars = [var for var, value in required_vars.items() if not value]
            if missing_vars:
                error_msg = f"Missing required Microsoft Graph API credentials: {', '.join(missing_vars)}"
                logger.error(error_msg)
                raise EnvironmentError(error_msg)

            # Store credentials
            self.client_id = required_vars["MS_CLIENT_ID"]
            self.client_secret = required_vars["MS_CLIENT_SECRET"]
            self.tenant_id = required_vars["MS_TENANT_ID"]
            self.user_id = required_vars["MS_USER_ID"]

            # Initialize the Graph client
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Initialize GraphClient with the credential
            self.client = GraphServiceClient(credentials=credential)
            logger.info("Microsoft Graph client initialized successfully")
            
        except Exception as e:
            error_msg = f"Failed to initialize Microsoft Graph client: {str(e)}"
            logger.error(error_msg)
            raise EnvironmentError(error_msg)

    def _check_client(self):
        """Check if the client is properly initialized."""
        if not self.client:
            raise EnvironmentError("Microsoft Graph client not initialized. Please check your credentials.")

    async def check_availability(self, data: dict) -> dict:
        """Check if there are any calendar conflicts for a given time range.
        
        Args:
            data (dict): Dictionary containing start_time and end_time in ISO format
            
        Returns:
            dict: Dictionary with availability status
        """
        try:
            self._check_client()
            
            # Extract time range from input data
            start_time = data.get("start_time")
            end_time = data.get("end_time")
            
            if not start_time or not end_time:
                raise ValueError("start_time and end_time are required")
            
            # Get calendar view for the specified time range
            endpoint = f'/users/{self.user_id}/calendarView'
            params = {
                'startDateTime': start_time,
                'endDateTime': end_time
            }
            
            response = await self.client.get(endpoint, params=params)
            
            if response:
                # If any events are returned, the time slot is not available
                events = response.json().get('value', [])
                return {
                    "available": len(events) == 0
                }
            else:
                raise Exception("Failed to check availability: No response received")
                
        except Exception as e:
            logger.error(f"Error checking availability: {str(e)}")
            raise

    async def add_event(self, event: EventCreate) -> EventResponse:
        """Create a new calendar event."""
        try:
            self._check_client()
            
            # Format the event data for Microsoft Graph API
            event_data = {
                "subject": event.title,
                "start": {
                    "dateTime": event.start_time.isoformat(),
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": event.end_time.isoformat(),
                    "timeZone": "UTC"
                },
                "body": {
                    "contentType": "text",
                    "content": event.description or ""
                }
            }

            # Create and send the request
            endpoint = f'/users/{self.user_id}/calendar/events'
            response = await self.client.post(endpoint, json=event_data)
            
            if response:
                data = response.json()
                return EventResponse(
                    event_id=data['id'],
                    status="created"
                )
            else:
                raise Exception("Failed to create event: No response received")
                
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            raise

    async def update_event(self, event: EventUpdate) -> EventResponse:
        """Update an existing calendar event."""
        try:
            self._check_client()
            
            # Format the event data for Microsoft Graph API
            event_data = {
                "subject": event.title,
                "start": {
                    "dateTime": event.start_time.isoformat(),
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": event.end_time.isoformat(),
                    "timeZone": "UTC"
                },
                "body": {
                    "contentType": "text",
                    "content": event.description or ""
                }
            }

            # Create and send the request
            endpoint = f'/users/{self.user_id}/calendar/events/{event.event_id}'
            response = await self.client.patch(endpoint, json=event_data)
            
            if response:
                return EventResponse(
                    event_id=event.event_id,
                    status="updated"
                )
            else:
                raise Exception("Failed to update event: No response received")
                
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}")
            raise

    async def delete_event(self, event: EventDelete) -> EventResponse:
        """Delete a calendar event."""
        try:
            self._check_client()
            
            # Create and send the request
            endpoint = f'/users/{self.user_id}/calendar/events/{event.event_id}'
            await self.client.delete(endpoint)
            
            return EventResponse(
                event_id=event.event_id,
                status="deleted"
            )
                
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            raise

# Create a singleton instance
calendar_client = MicrosoftCalendarClient()
