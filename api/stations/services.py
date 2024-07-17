from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel

from core.models import Station, StationLocation


class StationInput(BaseModel):
    name: str
    full_name: str


class StationLocationInput(BaseModel):
    station_name: str
    latitude: float
    longitude: float
    start_time: datetime
    end_time: Optional[datetime] = None
    depth: Optional[float] = None
    comment: Optional[str] = ''


class StationQueryInput(BaseModel):
    station_name: str
    timestamp: datetime


class StationsQueryInput(BaseModel):
    timestamp: datetime


class StationQueryOutput(BaseModel):
    station_name: str
    latitude: float
    longitude: float
    start_time: datetime
    end_time: Optional[datetime] = None
    depth: Optional[float] = None
    comment: str


class NearestStationQueryInput(BaseModel):
    latitude: float
    longitude: float
    timestamp: Optional[datetime] = None


class NearestStationQueryOutput(BaseModel):
    station_name: str
    latitude: float
    longitude: float
    distance: float


class AddNearestStationInput(BaseModel):
    latitude: List[float]
    longitude: List[float]
    timestamp: List[datetime]


class AddNearestStationOutput(BaseModel):
    station: List[str]
    distance_km: List[float]


class StationService:
    @staticmethod
    def serialize_station_location(location: StationLocation) -> StationQueryOutput:
        return StationQueryOutput(
            station_name=location.content_object.name,
            latitude=location.geolocation.y,
            longitude=location.geolocation.x,
            start_time=location.start_time,
            end_time=location.end_time,
            depth=location.depth,
            comment=location.comment
        )
    
    @staticmethod
    def create_station(station_input: StationInput):
        station = Station.objects.create(
            name=station_input.name,
            full_name=station_input.full_name
        )

    @staticmethod
    def set_location(location: StationLocationInput):
        station = Station.objects.get(name=location.station_name)
        station.set_location(
            latitude=location.latitude,
            longitude=location.longitude,
            start_time=location.start_time,
            end_time=location.end_time,
            depth=location.depth,
            comment=location.comment
        )

    @staticmethod
    def get_nearest_station(query: NearestStationQueryInput) -> NearestStationQueryOutput:
        station_location = Station.nearest_location(
            latitude=query.latitude,
            longitude=query.longitude,
            timestamp=query.timestamp
        )
        return NearestStationQueryOutput(
            station_name=station_location.content_object.name,
            latitude=station_location.geolocation.y,
            longitude=station_location.geolocation.x,
            distance=station_location.distance.km
        )
    
    @classmethod
    def get_stations(cls, timestamp: datetime = None) -> list[StationQueryOutput]:
        station_locations = Station.get_locations(timestamp)
        return [cls.serialize_station_location(location) for location in station_locations]
    

    @staticmethod
    def add_nearest_station(latitude: List[float], longitude: List[float], timestamp: List[datetime]) -> AddNearestStationOutput:
        station_name, distance_km = Station.add_nearest_station(
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp
        )
        return AddNearestStationOutput(
            station=station_name,
            distance_km=distance_km
        )
