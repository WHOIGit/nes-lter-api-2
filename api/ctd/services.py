from typing import Optional, List
from datetime import datetime

from django.contrib.gis.geos import Point

from pydantic import BaseModel

from core.models import Vessel, Cruise, Cast, Niskin


class CastInput(BaseModel):
    cruise_name: str
    number: str
    latitude: float
    longitude: float
    depth: float
    start_time: datetime
    end_time: Optional[datetime] = None


class NiskinInput(BaseModel):
    cruise_name: str
    cast_number: str
    number: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    depth: float
    start_time: datetime
    end_time: Optional[datetime] = None


class CtdService:
    @staticmethod
    def create_cast(cast_input: CastInput) -> Cast:
        cruise = Cruise.objects.get(name=cast_input.cruise_name)
        cast = Cast.objects.create(
            cruise=cruise,
            number=cast_input.number,
            geolocation=Point(cast_input.longitude, cast_input.latitude, srid=4326),
            depth=cast_input.depth,
            start_time=cast_input.start_time,
            end_time=cast_input.end_time
        )
        return cast

    @staticmethod
    def create_niskin(niskin_input: NiskinInput) -> Niskin:
        cruise = Cruise.objects.get(name=niskin_input.cruise_name)
        cast = Cast.objects.get(cruise=cruise, number=niskin_input.cast_number)
        location = None
        if niskin_input.latitude is not None and niskin_input.longitude is not None:
            location = Point(niskin_input.longitude, niskin_input.latitude, srid=4326)
        niskin = Niskin.objects.create(
            cast=cast,
            number=niskin_input.number,
            geolocation=location,
            depth=niskin_input.depth,
            start_time=niskin_input.start_time,
            end_time=niskin_input.end_time
        )
        return niskin
    
    @staticmethod
    def get_niskin(cruise_name: str, cast_number: str, niskin_number: str) -> Niskin:
        cruise = Cruise.objects.get(name=cruise_name)
        cast = Cast.objects.get(cruise=cruise, number=cast_number)
        niskin = Niskin.objects.get(cast=cast, number=niskin_number)
        return niskin
