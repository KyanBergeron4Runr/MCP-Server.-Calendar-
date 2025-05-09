from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from msgraph.client import GraphServiceClient
from msgraph.api.users_api import UsersApi
from msgraph.api.calendar_api import CalendarApi
from azure.identity import ClientSecretCredential
from msgraph_core.authentication import AzureIdentityAuthenticationProvider
from msgraph_core import BaseGraphRequestAdapter
import os
from dotenv import load_dotenv
from schemas.calendar_schemas import (
    TimeRange,
    AvailabilityResponse,
    EventCreate,
    EventUpdate,
    EventDelete,
    EventResponse
)

# Load environment variables
load_dotenv()

class MicrosoftCalendarClient:
    def __init__(self):
        self.client_id = os.getenv("MS_CLIENT_ID")
        self.client_secret = os.getenv("MS_CLIENT_SECRET") 
        self.tenant_id = os.getenv("MS_TENANT_ID")
        self.user_id = os.getenv("MS_USER_ID")

        missing = []
        if not self.client_id: missing.append("MS_CLIENT_ID")
        if not self.client_secret: missing.append("MS_CLIENT_SECRET")
        if not self.tenant_id: missing.append("MS_TENANT_ID") 
        if not self.user_id: missing.append("MS_USER_ID")

        if missing:
            print(f"Warning: Missing Microsoft Graph API credentials: {', '.join(missing)}. Using mock implementation.")
            return
        
        # Initialize the Graph client
        self.credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        self.auth_provider = AzureIdentityAuthenticationProvider(self.credential)
        self.client = BaseGraphRequestAdapter(self.auth_provider)

    async def check_availability(self, time_range: TimeRange) -> AvailabilityResponse:
        """Check calendar availability for a given time range."""
        try:
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
            users = UsersRequestBuilder(self.client)
            response = await users.by_user_id(self.user_id).find_meeting_times.post(request_body)
            
            if response:
                available_slots = []
                
                # Extract available time slots from the response
                for suggestion in response.meeting_time_suggestions or []:
                    start_time = datetime.fromisoformat(suggestion.meeting_time_slot.start.date_time.replace("Z", "+00:00"))
                    available_slots.append(start_time)
                
                return AvailabilityResponse(
                    available=len(available_slots) > 0,
                    slots=available_slots
                )
            else:
                raise Exception("Failed to check availability: No response received")
                
        except Exception as e:
            raise Exception(f"Error checking availability: {str(e)}")

    async def add_event(self, event: EventCreate) -> EventResponse:
        """Create a new calendar event."""
        try:
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
            users = UsersRequestBuilder(self.client)
            events = users.by_user_id(self.user_id).calendar.events
            response = await events.post(event_data)
            
            if response:
                return EventResponse(
                    event_id=response.id,
                    status="created"
                )
            else:
                raise Exception("Failed to create event: No response received")
                
        except Exception as e:
            raise Exception(f"Error creating event: {str(e)}")

    async def update_event(self, event: EventUpdate) -> EventResponse:
        """Update an existing calendar event."""
        try:
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
            users = UsersRequestBuilder(self.client)
            events = users.by_user_id(self.user_id).calendar.events
            response = await events.by_event_id(event.event_id).patch(event_data)
            
            if response:
                return EventResponse(
                    event_id=event.event_id,
                    status="updated"
                )
            else:
                raise Exception("Failed to update event: No response received")
                
        except Exception as e:
            raise Exception(f"Error updating event: {str(e)}")

    async def delete_event(self, event: EventDelete) -> EventResponse:
        """Delete a calendar event."""
        try:
            # Create and send the request
            users = UsersRequestBuilder(self.client)
            events = users.by_user_id(self.user_id).calendar.events
            await events.by_event_id(event.event_id).delete()
            
            return EventResponse(
                event_id=event.event_id,
                status="deleted"
            )
                
        except Exception as e:
            raise Exception(f"Error deleting event: {str(e)}")

# Create a singleton instance
calendar_client = MicrosoftCalendarClient() 