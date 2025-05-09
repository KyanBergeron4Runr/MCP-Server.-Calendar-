from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from msgraph.core import GraphClient
from azure.identity import ClientSecretCredential
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
        self.user_id = os.getenv("MS_USER_ID")  # The user's email or ID
        
        if not all([self.client_id, self.client_secret, self.tenant_id, self.user_id]):
            raise ValueError("Missing required Microsoft Graph API credentials in environment variables")
        
        # Initialize the Graph client
        self.credential = ClientSecretCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        self.client = GraphClient(credential=self.credential)

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

            # Call the findMeetingTimes API
            response = await self.client.post(
                f"/users/{self.user_id}/findMeetingTimes",
                json=request_body
            )
            
            if response.status_code == 200:
                data = response.json()
                available_slots = []
                
                # Extract available time slots from the response
                for suggestion in data.get("meetingTimeSuggestions", []):
                    start_time = datetime.fromisoformat(suggestion["meetingTimeSlot"]["start"]["dateTime"].replace("Z", "+00:00"))
                    available_slots.append(start_time)
                
                return AvailabilityResponse(
                    available=len(available_slots) > 0,
                    slots=available_slots
                )
            else:
                raise Exception(f"Failed to check availability: {response.text}")
                
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

            # Create the event
            response = await self.client.post(
                f"/users/{self.user_id}/calendar/events",
                json=event_data
            )
            
            if response.status_code == 201:
                data = response.json()
                return EventResponse(
                    event_id=data["id"],
                    status="created"
                )
            else:
                raise Exception(f"Failed to create event: {response.text}")
                
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

            # Update the event
            response = await self.client.patch(
                f"/users/{self.user_id}/calendar/events/{event.event_id}",
                json=event_data
            )
            
            if response.status_code == 200:
                return EventResponse(
                    event_id=event.event_id,
                    status="updated"
                )
            else:
                raise Exception(f"Failed to update event: {response.text}")
                
        except Exception as e:
            raise Exception(f"Error updating event: {str(e)}")

    async def delete_event(self, event: EventDelete) -> EventResponse:
        """Delete a calendar event."""
        try:
            # Delete the event
            response = await self.client.delete(
                f"/users/{self.user_id}/calendar/events/{event.event_id}"
            )
            
            if response.status_code == 204:
                return EventResponse(
                    event_id=event.event_id,
                    status="deleted"
                )
            else:
                raise Exception(f"Failed to delete event: {response.text}")
                
        except Exception as e:
            raise Exception(f"Error deleting event: {str(e)}")

# Create a singleton instance
calendar_client = MicrosoftCalendarClient() 