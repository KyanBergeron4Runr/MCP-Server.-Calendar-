from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from msgraph import GraphServiceClient
from azure.identity import ClientSecretCredential
import os
from dotenv import load_dotenv
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

# Load environment variables
load_dotenv()

class MicrosoftCalendarClient:
    def __init__(self):
        self.client = None
        self.user_id = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Microsoft Graph client with credentials."""
        try:
            self.client_id = os.getenv("MS_CLIENT_ID")
            self.client_secret = os.getenv("MS_CLIENT_SECRET") 
            self.tenant_id = os.getenv("MS_TENANT_ID")
            self.user_id = os.getenv("MS_USER_ID")

            if not all([self.client_id, self.client_secret, self.tenant_id, self.user_id]):
                missing_vars = []
                if not self.client_id: missing_vars.append("MS_CLIENT_ID")
                if not self.client_secret: missing_vars.append("MS_CLIENT_SECRET")
                if not self.tenant_id: missing_vars.append("MS_TENANT_ID")
                if not self.user_id: missing_vars.append("MS_USER_ID")
                logger.error(f"Missing Microsoft Graph API credentials: {', '.join(missing_vars)}")
                return

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
            logger.error(f"Failed to initialize Microsoft Graph client: {str(e)}")
            self.client = None

    def _check_client(self):
        """Check if the client is properly initialized."""
        if not self.client:
            raise Exception("Microsoft Graph client not initialized. Please check your credentials.")

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
