from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
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
    EventResponse,
    CheckMeetingAtTimeInput,
    CheckMeetingAtTimeResponse,
    MeetingEvent
)
import pytz
import dateutil.parser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
MS_CLIENT_ID = os.environ.get("MS_CLIENT_ID")
MS_CLIENT_SECRET = os.environ.get("MS_CLIENT_SECRET")
MS_TENANT_ID = os.environ.get("MS_TENANT_ID")
MS_USER_ID = os.environ.get("MS_USER_ID")

class MicrosoftCalendarClient:
    def __init__(self):
        self.credential = None
        self.user_id = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Microsoft Graph client with credentials from Replit Secrets."""
        try:
            # Check for missing environment variables
            missing_vars = []
            for var_name, var_value in [
                ("MS_CLIENT_ID", MS_CLIENT_ID),
                ("MS_CLIENT_SECRET", MS_CLIENT_SECRET),
                ("MS_TENANT_ID", MS_TENANT_ID),
                ("MS_USER_ID", MS_USER_ID)
            ]:
                if not var_value:
                    missing_vars.append(var_name)

            if missing_vars:
                env_keys = [k for k in os.environ.keys() if k.startswith('MS_') or k == 'API_KEY']
                error_msg = f"Missing required Microsoft Graph API credentials: {', '.join(missing_vars)}\nCurrent env: {env_keys}"
                logger.error(error_msg)
                raise EnvironmentError(error_msg)

            self.client_id = MS_CLIENT_ID
            self.client_secret = MS_CLIENT_SECRET
            self.tenant_id = MS_TENANT_ID
            self.user_id = MS_USER_ID
            self.credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            logger.info("Microsoft Graph client initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize Microsoft Graph client: {str(e)}"
            logger.error(error_msg)
            raise EnvironmentError(error_msg)

    def _check_client(self):
        """Check if the client is properly initialized."""
        if not self.credential:
            raise EnvironmentError("Microsoft Graph client not initialized. Please check your credentials.")

    async def check_availability(self, data: dict) -> dict:
        """Check if there are any calendar conflicts for a given time range.
        Returns both 'available' and a list of busy/taken time slots in the requested timezone.
        """
        try:
            self._check_client()
            # Extract time range from input data
            start_time = data.get("start_time")
            end_time = data.get("end_time")
            timezone = data.get("timezone") or "America/New_York"
            tz = pytz.timezone(timezone)
            if not start_time or not end_time:
                raise ValueError("start_time and end_time are required")
            token = self.credential.get_token("https://graph.microsoft.com/.default").token
            url = f"https://graph.microsoft.com/v1.0/users/{self.user_id}/calendarView"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            params = {
                "startDateTime": start_time,
                "endDateTime": end_time
            }
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                events = response.json().get('value', [])
                busy_times = []
                for event in events:
                    # Convert UTC or offset time to requested timezone
                    start_dt_utc = dateutil.parser.isoparse(event['start']['dateTime'])
                    end_dt_utc = dateutil.parser.isoparse(event['end']['dateTime'])
                    if start_dt_utc.tzinfo is None:
                        start_dt_utc = pytz.UTC.localize(start_dt_utc)
                    if end_dt_utc.tzinfo is None:
                        end_dt_utc = pytz.UTC.localize(end_dt_utc)
                    start_local = start_dt_utc.astimezone(tz).replace(tzinfo=None)
                    end_local = end_dt_utc.astimezone(tz).replace(tzinfo=None)
                    busy_times.append({
                        "start": start_local.isoformat(),
                        "end": end_local.isoformat(),
                        "subject": event.get('subject', '')
                    })
                return {
                    "available": len(events) == 0,
                    "busy_times": busy_times
                }
            else:
                logger.error(f"Graph API error: {response.status_code} {response.text}")
                logger.error(f"Troubleshooting info: user_id={self.user_id}, url={url}, params={params}, token_present={bool(token)}")
                raise Exception(f"Failed to check availability: {response.text}")
        except Exception as e:
            logger.exception("Failed to check availability")
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=f"Error checking availability: {str(e)}")

    async def add_event(self, event: dict) -> EventResponse:
        try:
            self._check_client()
            # Parse the datetime strings with timezone information
            start_time = dateutil.parser.isoparse(event['start_time'])
            end_time = dateutil.parser.isoparse(event['end_time'])
            
            # Convert to UTC for the API
            start_time_utc = start_time.astimezone(pytz.UTC)
            end_time_utc = end_time.astimezone(pytz.UTC)
            
            event_data = {
                "subject": event['title'],
                "start": {
                    "dateTime": start_time_utc.isoformat(),
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": end_time_utc.isoformat(),
                    "timeZone": "UTC"
                },
                "body": {
                    "contentType": "text",
                    "content": event.get('body') or event.get('description') or ""
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {
                            "method": "email",
                            "minutes": 30  # Always set to 30 minutes
                        }
                    ]
                }
            }
            
            # Set location to Online
            event_data["location"] = {"displayName": "Online"}

            endpoint = f'https://graph.microsoft.com/v1.0/users/{self.user_id}/calendar/events'
            token = self.credential.get_token("https://graph.microsoft.com/.default").token
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            response = requests.post(endpoint, headers=headers, json=event_data)
            if response.status_code == 201:
                data = response.json()
                return EventResponse(
                    event_id=data['id'],
                    status="created"
                )
            else:
                raise Exception(f"Failed to create event: {response.text}")
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            raise Exception(f"Error creating event: {str(e)}")

    async def update_event(self, event: dict) -> EventResponse:
        try:
            self._check_client()
            event_obj = EventUpdate(**event)
            event_data = {
                "subject": event_obj.title,
                "start": {
                    "dateTime": event_obj.start_time.isoformat(),
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": event_obj.end_time.isoformat(),
                    "timeZone": "UTC"
                },
                "body": {
                    "contentType": "text",
                    "content": event_obj.body or event_obj.description or ""
                }
            }
            if event_obj.location:
                event_data["location"] = {"displayName": event_obj.location}
            endpoint = f'https://graph.microsoft.com/v1.0/users/{self.user_id}/calendar/events/{event_obj.event_id}'
            token = self.credential.get_token("https://graph.microsoft.com/.default").token
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            response = requests.patch(endpoint, headers=headers, json=event_data)
            if response.status_code == 200:
                return EventResponse(
                    event_id=event_obj.event_id,
                    status="updated"
                )
            else:
                raise Exception(f"Failed to update event: {response.text}")
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}")
            raise Exception(f"Error updating event: {str(e)}")

    async def delete_event(self, event: EventDelete) -> EventResponse:
        """Delete a calendar event."""
        try:
            self._check_client()
            
            # Create and send the request
            endpoint = f'https://graph.microsoft.com/v1.0/users/{self.user_id}/calendar/events/{event.event_id}'
            token = self.credential.get_token("https://graph.microsoft.com/.default").token
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            response = requests.delete(endpoint, headers=headers)
            
            if response.status_code == 204:
                return EventResponse(
                    event_id=event.event_id,
                    status="deleted"
                )
            else:
                raise Exception(f"Failed to delete event: {response.text}")
                
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            raise Exception(f"Error deleting event: {str(e)}")

    async def find_meetings_near_time(self, data: dict) -> dict:
        try:
            self._check_client()
            input_data = CheckMeetingAtTimeInput(**data)
            # Parse date and time
            # Combine date and time
            dt_str = f"{input_data.date}T{input_data.time}:00"
            tz = pytz.timezone(input_data.timezone) if input_data.timezone else pytz.UTC
            dt = tz.localize(datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S"))
            window = timedelta(minutes=input_data.window_minutes or 15)
            start_dt = (dt - window).astimezone(pytz.UTC)
            end_dt = (dt + window).astimezone(pytz.UTC)
            # Query Microsoft Graph API
            token = self.credential.get_token("https://graph.microsoft.com/.default").token
            url = f"https://graph.microsoft.com/v1.0/users/{self.user_id}/calendarView"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            params = {
                "startDateTime": start_dt.isoformat(),
                "endDateTime": end_dt.isoformat()
            }
            response = requests.get(url, headers=headers, params=params)
            events = []
            has_meeting = False
            if response.status_code == 200:
                for event in response.json().get('value', []):
                    has_meeting = True
                    events.append(MeetingEvent(
                        subject=event.get('subject', ''),
                        start=event['start']['dateTime'],
                        end=event['end']['dateTime'],
                        location=event.get('location', {}).get('displayName', '')
                    ))
                return CheckMeetingAtTimeResponse(has_meeting=has_meeting, events=events)
            else:
                raise Exception(f"Failed to check meetings: {response.text}")
        except Exception as e:
            logger.error(f"Error in find_meetings_near_time: {str(e)}")
            raise Exception(f"Error in find_meetings_near_time: {str(e)}")

# Create a singleton instance
calendar_client = MicrosoftCalendarClient()
