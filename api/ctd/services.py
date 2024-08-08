from typing import Optional, List, Tuple
from datetime import datetime
from django.contrib.gis.db.models import PointField

from django.contrib.gis.geos import Point, point

from pydantic import BaseModel

from core.models import Vessel, Cruise, Cast, Niskin

from django.db import IntegrityError
from django.http import Http404
from ninja.errors import HttpError

class VesselOutput(BaseModel):
    designation: str
    name: str
    short_name: str
    code: str


class AddVesselInput(BaseModel):
    designation: str
    name: str
    short_name: str
    code: str

    
class UpdateVesselInput(BaseModel):
    designation: str
    short_name: str
    code: str


class CruiseOutput(BaseModel):
    name: str
    vessel_name: str
    start_time: datetime
    end_time: datetime


class AddCruiseInput(BaseModel):
    name: str
    vessel_name: str
    start_time: datetime
    end_time: datetime


class UpdateCruiseInput(BaseModel):
    vessel_name: str
    start_time: datetime
    end_time: datetime

    
class CastInput(BaseModel):
    cruise_name: str
    number: str
    latitude: float
    longitude: float
    depth: float
    start_time: datetime
    end_time: Optional[datetime] = None
 
    
class CastOutput(BaseModel):
    cruise_name: str
    number: str
    geolocation: Tuple[float, float]
    depth: float
    start_time: datetime
    end_time: Optional[datetime] = None


class UpdateCastInput(BaseModel):
    latitude: float
    longitude: float
    depth: float
    start_time: datetime
    end_time: Optional[datetime] = None
    

class NiskinInput(BaseModel):
    cruise_name: str
    cast_number: str
    number: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    depth: float

    
class NiskinOutput(BaseModel):
    cruise_name: str
    cast_number: str
    number: int
    geolocation: Tuple[float, float]
    depth: float
    

class UpdateNiskinInput(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    depth: float

    
class CtdService:
    
    @staticmethod
    def serialize_vessel(vessel: Vessel) -> VesselOutput:
        return VesselOutput(
                designation=vessel.designation,
                name=vessel.name,
                short_name=vessel.short_name,
                code=vessel.code
        )


    @classmethod
    def get_vessels(cls) -> list[VesselOutput]:
        vessels = Vessel.objects.all()
        return [cls.serialize_vessel(vessel) for vessel in vessels]
 
    
    @classmethod
    def get_vessel(cls, vessel_name: str) -> VesselOutput:
        try:
            vessel = Vessel.objects.get(name__iexact=vessel_name)
            return cls.serialize_vessel(vessel)
        except Vessel.DoesNotExist:
            raise Http404(f"Vessel {vessel_name} not found.")


    @classmethod
    def create_vessel(cls, input: AddVesselInput) -> VesselOutput:
        try:
            existing_vessel = Vessel.objects.filter(name__iexact=input.name).exists()         
            if existing_vessel:
                raise HttpError(409, f"Vessel with name '{input.name}' already exists.")
            try:
                new_vessel = Vessel.objects.create(
                    designation=input.designation,
                    name=input.name,
                    short_name=input.short_name,
                    code=input.code
                )            
                return cls.serialize_vessel(new_vessel)
            except IntegrityError as e:
                if 'duplicate key value violates unique constraint' in str(e):
                    if 'vessel_short_name' in str(e):
                        raise HttpError(409, f"Vessel with short_name '{input.short_name}' already exists.")
                    if 'vessel_code' in str(e):
                        raise HttpError(409, f"Vessel with code '{input.code}' already exists.")
                else:
                    raise HttpError(500, "An unexpected error occurred while creating the vessel.")
        except Vessel.DoesNotExist:
            pass


    @classmethod
    def update_vessel(cls, vessel_name: str, input: UpdateVesselInput) -> VesselOutput:
        try:
            vessel = Vessel.objects.get(name__iexact=vessel_name)       
            try:
                vessel.designation=input.designation
                vessel.name=vessel_name
                vessel.short_name=input.short_name
                vessel.code=input.code
                vessel.save()
                return cls.serialize_vessel(vessel)
            except IntegrityError as e:
                if 'duplicate key value violates unique constraint' in str(e):
                    if 'vessel_short_name' in str(e):
                        raise HttpError(409, f"Vessel with short_name '{input.short_name}' already exists.")
                    if 'vessel_code' in str(e):
                        raise HttpError(409, f"Vessel with code '{input.code}' already exists.")
                else:
                    raise HttpError(500, "An unexpected error occurred while creating the vessel.")
        except Vessel.DoesNotExist:
            raise HttpError(404, f"Vessel {vessel_name} not found.")

        
    @staticmethod
    def serialize_cruise(cruise: Cruise) -> CruiseOutput:
        return CruiseOutput(
            name=cruise.name,
            vessel_name=cruise.vessel.name,
            start_time=cruise.start_time,
            end_time=cruise.end_time,
        )

    @classmethod
    def get_cruises(cls) -> list[CruiseOutput]:
        cruises = Cruise.objects.all()
        return [cls.serialize_cruise(cruise) for cruise in cruises]
    
    @classmethod
    def get_cruise(cls, cruise_name: str) -> CruiseOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)  # Case-insensitive search
            return cls.serialize_cruise(cruise)
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")

    @classmethod
    def create_cruise(cls, input: AddCruiseInput) -> CruiseOutput:
        try:
            vessel = Vessel.objects.get(name__iexact=input.vessel_name)
            new_cruise = Cruise.objects.create(
                name=input.name,
                vessel=vessel,
                start_time=input.start_time,
                end_time=input.end_time
            )            
            return cls.serialize_cruise(new_cruise)
        except IntegrityError:
            raise HttpError(409, f"error': f'Cruise with name {input.name} already exists.")
        except Vessel.DoesNotExist:
            raise Http404(f"Vessel with name {input.vessel_name} not found.")


    @classmethod
    def update_cruise(cls, cruise_name: str, input: UpdateCruiseInput) -> CruiseOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            try:
                vessel = Vessel.objects.get(name__iexact=input.vessel_name)
                cruise.name = cruise_name
                cruise.vessel = vessel
                cruise.start_time = input.start_time
                cruise.end_time = input.end_time
                cruise.save()
                return cls.serialize_cruise(cruise)
            except Vessel.DoesNotExist:
                raise Http404(f"Vessel with name {input.vessel_name} not found.")
        except Cruise.DoesNotExist:
            raise HttpError(404, f"Cruise {input.cruise_name} not found.")

    @classmethod
    def delete_cruise(cls, cruise_name: str):
        try:
           cruise = Cruise.objects.get(name__iexact=cruise_name)
           cruise.delete()
           return {"status": "success", "message": f"Cruise {cruise_name} deleted."}   
        except Cruise.DoesNotExist:
            raise HttpError(404, f"Cruise {cruise_name} not found.")

    
    @staticmethod
    def serialize_cast(cast: Cast) -> CastOutput:
        return CastOutput(
                cruise_name=cast.cruise.name,
                number=cast.number,
                depth=cast.depth,
                geolocation=cast.geolocation,
                start_time=cast.start_time,
                end_time=cast.end_time
        )


    @staticmethod
    def get_casts(cruise_name: str) -> List[CastOutput]:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            casts = Cast.objects.filter(cruise=cruise)
            return [CtdService.serialize_cast(cast) for cast in casts]
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for {cruise_name} .")

        
    @staticmethod
    def get_cast(cruise_name: str, cast_number: str) -> CastOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            cast = Cast.objects.get(cruise=cruise, number__iexact=cast_number)
            return CtdService.serialize_cast(cast)
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for {cruise_name} .")
        

    @classmethod
    def create_cast(cls, cast_input: CastInput) -> CastOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=cast_input.cruise_name)
            location = None
            if cast_input.latitude is not None and cast_input.longitude is not None:
                location = Point(cast_input.longitude, cast_input.latitude, srid=4326)
                try:
                    cast = Cast.objects.create(
                        cruise=cruise,
                        number=cast_input.number,
                        geolocation=location,
                        depth=cast_input.depth,
                        start_time=cast_input.start_time,
                        end_time=cast_input.end_time)
                    return cls.serialize_cast(cast)
                except IntegrityError as e:
                    if 'unique_cruise_cast_number' in str(e):
                        raise HttpError(409, f"Cast {cast_input.number} already exists.")
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cast_input.cruise_name} not found.")

        
    @classmethod
    def update_cast(cls, cruise_name: str, cast_number: str, cast_input: UpdateCastInput) -> CastOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            cast = Cast.objects.get(cruise=cruise, number=cast_number)
            location = None
            if cast_input.latitude is not None and cast_input.longitude is not None:
                location = Point(cast_input.longitude, cast_input.latitude, srid=4326)
                cast.geolocation=location
                cast.depth=cast_input.depth
                cast.start_time=cast_input.start_time
                cast.end_time=cast_input.end_time
                cast.save()
                return cls.serialize_cast(cast)
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cast_input.cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for {cruise_name} .")

    @staticmethod
    def delete_cast(cruise_name: str, cast_number: str):
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            cast = Cast.objects.get(cruise=cruise, number__iexact=cast_number)
            cast.delete()
            return {"status": "success", "message": f"Cast {cast_number} on cruise {cruise_name} deleted."}   
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for {cruise_name} .")


    @staticmethod
    def serialize_niskin(niskin: Niskin) -> NiskinOutput:
        return NiskinOutput(
                cruise_name=niskin.cast.cruise.name,
                cast_number=niskin.cast.number,
                number=niskin.number,
                depth=niskin.depth,
                geolocation=niskin.geolocation
        )


    @classmethod
    def create_niskin(cls, niskin_input: NiskinInput) -> NiskinOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=niskin_input.cruise_name)
            cast = Cast.objects.get(cruise=cruise, number__iexact=niskin_input.cast_number)
            location = None
            if niskin_input.latitude is not None and niskin_input.longitude is not None:
                location = Point(niskin_input.longitude, niskin_input.latitude, srid=4326)
                try:
                    niskin = Niskin.objects.create(
                        cast=cast,
                        number=niskin_input.number,
                        geolocation=location,
                        depth=niskin_input.depth)
                    return cls.serialize_niskin(niskin)
                except IntegrityError as e:
                    if 'unique_cast_niskin_number' in str(e):
                        raise HttpError(409, f"Niskin {niskin_input.number} already exists.")
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {niskin_input.cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for {niskin_input.cruise_name} .")
    

    @staticmethod
    def get_niskins(cruise_name: str, cast_number: str ) -> List[NiskinOutput]:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            cast = Cast.objects.get(cruise=cruise, number__iexact=cast_number)
            niskins = Niskin.objects.filter(cast=cast)
            return [CtdService.serialize_niskin(niskin) for niskin in niskins]
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for cruise {cruise_name} .")


    @staticmethod
    def get_niskin(cruise_name: str, cast_number: str, niskin_number: int) -> NiskinOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            cast = Cast.objects.get(cruise=cruise, number__iexact=cast_number)
            niskin = Niskin.objects.get(cast=cast, number=niskin_number)
            return CtdService.serialize_niskin(niskin)
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for cruise {cruise_name} .")
        except Niskin.DoesNotExist:
            raise Http404(f"Niskin not found for cruise {cruise_name} cast {cast_number} .")
    

    @classmethod
    def update_niskin(cls, cruise_name: str, cast_number: str, niskin_number: int, niskin_input: NiskinInput) -> NiskinOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            cast = Cast.objects.get(cruise=cruise, number__iexact=cast_number)
            niskin = Niskin.objects.get(cast=cast, number=niskin_number)
            location = None
            if niskin_input.latitude is not None and niskin_input.longitude is not None:
                location = Point(niskin_input.longitude, niskin_input.latitude, srid=4326)
                niskin.geolocation=location
                niskin.depth=niskin_input.depth
                niskin.save()
                return cls.serialize_niskin(niskin)
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for {cruise_name} .")
        except Niskin.DoesNotExist:
            raise Http404(f"Niskin not found for cruise {cruise_name} cast {cast_number} .")

    @staticmethod
    def delete_niskin(cruise_name: str, cast_number: str, niskin_number: int):
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            cast = Cast.objects.get(cruise=cruise, number__iexact=cast_number)
            niskin = Niskin.objects.get(cast=cast, number=niskin_number)
            niskin.delete()
            return {"status": "success", "message": f"Cast {cast_number} on cruise {cruise_name} deleted."}   
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for cruise {cruise_name} .")
        except Niskin.DoesNotExist:
            raise Http404(f"Niskin not found for cruise {cruise_name} cast {cast_number} .")
