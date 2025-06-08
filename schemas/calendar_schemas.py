from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TimeRange(BaseModel):
    start_time: datetime = Field(..., description="Start time of the range")
    end_time: datetime = Field(..., description="End time of the range")

class AvailabilityResponse(BaseModel):
    available: bool = Field(..., description="Whether the time range is available")
    slots: List[datetime] = Field(default_factory=list, description="Available time slots")

class EventBase(BaseModel):
    title: str = Field(..., description="Title of the event")
    start_time: datetime = Field(..., description="Start time of the event")
    end_time: datetime = Field(..., description="End time of the event")
    description: Optional[str] = Field(None, description="Description of the event")
    physical_location: Optional[str] = Field(None, description="Physical location of the event (e.g., meeting room, address)")
    virtual_meeting_link: Optional[str] = Field(None, description="Link for virtual meeting (e.g., Zoom, Teams)")
    reminder_minutes: Optional[int] = Field(30, description="Minutes before the event to send a reminder")
    body: Optional[str] = Field(None, description="Additional message or body content for the event invitation")

class EventCreate(EventBase):
    pass

class EventUpdate(EventBase):
    event_id: str = Field(..., description="ID of the event to update")

class EventDelete(BaseModel):
    event_id: str = Field(..., description="ID of the event to delete")

class EventResponse(BaseModel):
    event_id: str = Field(..., description="ID of the created/updated event")
    status: str = Field(..., description="Status of the operation")

class CheckMeetingAtTimeInput(BaseModel):
    date: str = Field(..., description="The date to check, in YYYY-MM-DD format.")
    time: str = Field(..., description="The time to check, in HH:MM 24-hour format.")
    timezone: Optional[str] = Field("UTC", description="User's timezone for accurate calendar matching. Default is UTC.")
    window_minutes: Optional[int] = Field(15, description="Time window (in minutes) before and after the specified time to check for overlapping meetings. Default is 15.")

class MeetingEvent(BaseModel):
    subject: str
    start: str
    end: str
    location: str

class CheckMeetingAtTimeResponse(BaseModel):
    has_meeting: bool
    events: List[MeetingEvent] = [] 