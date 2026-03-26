from typing import List
from datetime import datetime

from ninja import Router
from core.auth import TokenAuthenticator
from django.http import FileResponse

from .services import StationService, StationInput, StationLocationInput, StationQueryOutput, \
    NearestStationQueryInput, NearestStationQueryOutput, AddNearestStationInput, AddNearestStationOutput


router = Router()

#@router.get("/now", response=List[StationQueryOutput], tags=["Users"])
#def get_stations_now(request):
#    return StationService.get_stations()


#@router.get("/at/{timestamp}", response=List[StationQueryOutput], tags=["Users"])
#def get_stations(request, timestamp: datetime):
#    return StationService.get_stations(timestamp)

@router.get("/file.csv", tags=["Users"])
def get_stations_file(request):
    return StationService.get_station_file()

# @router.post('/nearest', response=NearestStationQueryOutput, tags=["Users"])
# def get_nearest_station(request, query: NearestStationQueryInput):
#    return StationService.get_nearest_station(query)


@router.post('/create', tags=["Admin"], auth=TokenAuthenticator())
def create_station(request, input: StationInput):
    StationService.create_station(input)
    return 204


@router.post('/set_location', tags=["Admin"], auth=TokenAuthenticator())
def set_location(request, input: StationLocationInput):
    StationService.set_location(input)
    return 204


@router.post('/add_nearest', response=AddNearestStationOutput, tags=["Users"], auth=TokenAuthenticator())
def add_nearest_station(request, input: AddNearestStationInput):
    return StationService.add_nearest_station(
        latitude=input.latitude,
        longitude=input.longitude,
        timestamp=input.timestamp
    )
