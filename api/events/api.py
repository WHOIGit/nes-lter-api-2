from typing import List
from datetime import datetime

from ninja import Router

from .services import EventService, EventOutput, FilterEventInput, EditEventInput


router = Router()


@router.get("read/{cruise_name}")
def read_events(request, cruise_name: str):
    return EventService.read_events(cruise_name)



@router.get("get/{cruise_name}", response=List[EventOutput])
def get_events(request, cruise_name: str):
    return EventService.get_events(cruise_name)


@router.post("filter/{cruise_name}", response=List[EventOutput])
def filter_events(request, cruise_name: str, input: FilterEventInput):
    return EventService.filter_events(cruise_name, input)

@router.post("edit/{cruise_name}/{event_number}", response=EventOutput)
def edit_events(request, cruise_name: str, event_number: int, input: EditEventInput):
    return EventService.edit_events(cruise_name, event_number, input)


@router.post("history/{cruise_name}", response=str)
def history_events(request, cruise_name: str):
    return EventService.history_events(cruise_name)


@router.post('delete/{cruise_name}')
def delete_events(request, cruise_name: str):
    try:
        result = EventService.delete_events(cruise_name)
        return result
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    


