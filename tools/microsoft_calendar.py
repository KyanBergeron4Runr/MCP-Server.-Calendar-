from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from msgraph.core import GraphClient
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
                logger.warning("Missing Microsoft Graph API credentials. Calendar features will be disabled.")
                return

            # Initialize the Graph client
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Initialize GraphClient with the credential
            self.client = GraphClient(credential=credential)
            logger.info("Microsoft Graph client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Microsoft Graph client: {str(e)}")
            self.client = None

    def _check_client(self):
        """Check if the client is properly initialized."""
        if not self.client:
            raise Exception("Microsoft Graph client not initialized. Please check your credentials.")

    async def check_availability(self, time_range: TimeRange) -> AvailabilityResponse:
        """Check calendar availability for a given time range."""
        try:
            self._check_client()

            # Format the request body for the findMeetingTimes API
            request_body = {
                "attendees": [{"emailAddress": {"address": self.user_id}, "type": "required"}],
                "timeConstraint": {
                    "timeslots": [{
                        "start": {"dateTime": time_range.start_time.isoformat(), "timeZone": "UTC"},
                        "end": {"dateTime": time_range.end_time.isoformat(), "timeZone": "UTC"}
                    }]
                },
                "meetingDuration": "PT1H"  # 1 hour meeting duration
            }

            # Create and send the request
            endpoint = f'/users/{self.user_id}/findMeetingTimes'
            response = await self.client.post(endpoint, json=request_body)

            if response:
                available_slots = []
                data = response.json()

                # Extract available time slots from the response
                for suggestion in data.get('meetingTimeSuggestions', []):
                    start_time = datetime.fromisoformat(suggestion['meetingTimeSlot']['start']['dateTime'].replace('Z', '+00:00'))
                    available_slots.append(start_time)

                return AvailabilityResponse(
                    available=len(available_slots) > 0,
                    slots=available_slots
                )
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
