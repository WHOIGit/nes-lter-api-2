from typing import List
from datetime import datetime
from ninja import Router

from .services import EventService, EventOutput, FilterEventInput, EditEventInput

router = Router()

@router.get("get/{cruise_name}")
def get_events(request, cruise_name: str):
    return EventService.get_events(cruise_name)


@router.post("filter/{cruise_name}", response=List[EventOutput])
def filter_events(request, cruise_name: str, input: FilterEventInput):
    return EventService.filter_events(cruise_name, input)

@router.put("edit/{cruise_name}/{message_id}", response=EventOutput)
def edit_events(request, cruise_name: str, message_id: int, input: EditEventInput):
    return EventService.edit_events(cruise_name, message_id, input)


@router.get("history/{cruise_name}", response=str)
def history_events(request, cruise_name: str):
    return EventService.history_events(cruise_name)


@router.delete('delete/{cruise_name}')
def delete_events(request, cruise_name: str):
    try:
        result = EventService.delete_events(cruise_name)
        return result
    except ValueError as e:
        return {"status": "error", "message": str(e)}

    


