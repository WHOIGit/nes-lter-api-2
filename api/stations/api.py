from typing import List
from datetime import datetime

from ninja import Router

from .services import StationService, StationInput, StationLocationInput, StationQueryOutput, \
    NearestStationQueryInput, NearestStationQueryOutput, AddNearestStationInput, AddNearestStationOutput


router = Router()

@router.get("/now", response=List[StationQueryOutput])
def get_stations_now(request):
    return StationService.get_stations()


@router.get("/at/{timestamp}", response=List[StationQueryOutput])
def get_stations(request, timestamp: datetime):
    return StationService.get_stations(timestamp)


@router.post('/nearest', response=NearestStationQueryOutput)
def get_nearest_station(request, query: NearestStationQueryInput):
    return StationService.get_nearest_station(query)


@router.post('/create')
def create_station(request, input: StationInput):
    StationService.create_station(input)
    return 204


@router.post('/set_location')
def set_location(request, input: StationLocationInput):
    StationService.set_location(input)
    return 204


@router.post('/add_nearest', response=AddNearestStationOutput)
def add_nearest_station(request, input: AddNearestStationInput):
    return StationService.add_nearest_station(
        latitude=input.latitude,
        longitude=input.longitude,
        timestamp=input.timestamp
    )