from datetime import datetime, timedelta
from typing import List, Dict, Any
from schemas.calendar_schemas import (
    TimeRange,
    AvailabilityResponse,
    EventCreate,
    EventUpdate,
    EventDelete,
    EventResponse
)

# Mock storage for events
EVENTS: Dict[str, Dict[str, Any]] = {}

def check_availability(time_range: TimeRange) -> AvailabilityResponse:
    """
    Check availability for a given time range.
    Currently returns mock data.
    """
    # Mock implementation - in reality, would check against actual calendar
    available_slots = [
        time_range.start_time + timedelta(hours=i)
        for i in range(0, 8)  # Mock 8 available slots
    ]
    return AvailabilityResponse(
        available=True,
        slots=available_slots
    )

def add_event(event: EventCreate) -> EventResponse:
    """
    Add a new calendar event.
    Currently stores in mock storage.
    """
    event_id = f"event_{len(EVENTS) + 1}"
    event_data = event.dict()
    EVENTS[event_id] = event_data
    
    return EventResponse(
        event_id=event_id,
        status="created"
    )

def update_event(event: EventUpdate) -> EventResponse:
    """
    Update an existing calendar event.
    Currently updates mock storage.
    """
    if event.event_id not in EVENTS:
        raise ValueError(f"Event {event.event_id} not found")
    
    event_data = event.dict(exclude={'event_id'})
    EVENTS[event.event_id] = event_data
    
    return EventResponse(
        event_id=event.event_id,
        status="updated"
    )

def delete_event(event: EventDelete) -> EventResponse:
    """
    Delete a calendar event.
    Currently removes from mock storage.
    """
    if event.event_id not in EVENTS:
        raise ValueError(f"Event {event.event_id} not found")
    
    del EVENTS[event.event_id]
    
    return EventResponse(
        event_id=event.event_id,
        status="deleted"
    ) 