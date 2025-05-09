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

class EventCreate(EventBase):
    pass

class EventUpdate(EventBase):
    event_id: str = Field(..., description="ID of the event to update")

class EventDelete(BaseModel):
    event_id: str = Field(..., description="ID of the event to delete")

class EventResponse(BaseModel):
    event_id: str = Field(..., description="ID of the created/updated event")
    status: str = Field(..., description="Status of the operation") 