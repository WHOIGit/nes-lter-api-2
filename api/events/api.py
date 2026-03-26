from typing import List
from datetime import datetime
from ninja import Router
from core.auth import TokenAuthenticator

from .services import EventService, EventOutput, FilterEventInput, EditEventInput

router = Router()

@router.get("/{cruise_name}.csv", tags=["Users"])
def get_events(request, cruise_name: str):
    return EventService.get_events(cruise_name)

@router.get("/instruments/{cruise_name}", response=List[str], tags=["Users"])
def get_instruments(request, cruise_name: str):
    return EventService.get_instruments(cruise_name)

@router.post("/filter/{cruise_name}", response=List[EventOutput], tags=["Users"], auth=TokenAuthenticator())
def filter_events(request, cruise_name: str, input: FilterEventInput):
    return EventService.filter_events(cruise_name, input)

@router.post("/edit/{cruise_name}/{r2r_event}", response=EventOutput, tags=["Admin"], auth=TokenAuthenticator())
def edit_events(request, cruise_name: str, r2r_event: str, input: EditEventInput):
    return EventService.edit_events(cruise_name, r2r_event, input)


@router.get("/history/{cruise_name}", response=str, tags=["Users"])
def history_events(request, cruise_name: str):
    return EventService.history_events(cruise_name)


@router.delete('/delete/{cruise_name}', tags=["Admin"], auth=TokenAuthenticator())
def delete_events(request, cruise_name: str):
    try:
        result = EventService.delete_events(cruise_name)
        return result
    except ValueError as e:
        return {"status": "error", "message": str(e)}

@router.get("/readme/{cruise_name}", response=str, tags=["Users"])
def get_readme(request, cruise_name: str):
    return EventService.get_readme(cruise_name)


