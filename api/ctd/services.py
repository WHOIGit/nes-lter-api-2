import io, os, glob
from io import StringIO
import csv
import re
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from django.contrib.gis.geos import Point

from pydantic import BaseModel

from core.models import Vessel, Cruise, Cast, Niskin

from django.db import IntegrityError
from django.http import Http404
from ninja.errors import HttpError
from django.http import HttpResponse
from django.http import FileResponse
from django.http import JsonResponse
from core.utils import get_store, find_readme

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
    type: Cruise.CruiseType
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class AddCruiseInput(BaseModel):
    name: str
    vessel_name: str
    type: Cruise.CruiseType
    start_time: datetime
    end_time: datetime


class UpdateCruiseInput(BaseModel):
    vessel_name: str
    type: Cruise.CruiseType
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
    latitude: float
    longitude: float
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
    niskin_number: int
    latitude: float
    longitude: float
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
    def get_vessels(cls) -> HttpResponse:
        vessels = Vessel.objects.all()
        serialized_vessels = [cls.serialize_vessel(vessel) for vessel in vessels]
        headers = list(VesselOutput.model_fields.keys())
        data = [
            {header: getattr(vessel, header, "") for header in headers}
            for vessel in serialized_vessels
        ]
        return JsonResponse(data, safe=False)
 
    @classmethod
    def get_vessels_csv(cls) -> HttpResponse:
        vessels = Vessel.objects.all()
        serialized_vessels = [cls.serialize_vessel(vessel) for vessel in vessels]
        headers = list(VesselOutput.model_fields.keys())
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        for vessel in serialized_vessels:
            writer.writerow([getattr(vessel, header, "") for header in headers])
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="vessels.csv"'
        return response
 
    
    @classmethod
    def get_vessel(cls, vessel_name: str) -> VesselOutput:
        try:
            vessel = Vessel.objects.get(name__iexact=vessel_name)
            return cls.serialize_vessel(vessel)
        except Vessel.DoesNotExist:
            raise Http404(f"Vessel {vessel_name} not found.")


    @classmethod
    def create_vessel(cls, input: AddVesselInput) -> VesselOutput:
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

    @classmethod
    def delete_vessel(cls, vessel_name: str):
        vessel = Vessel.objects.filter(name__iexact=vessel_name)
        if not vessel.exists():
            raise HttpError(404, f"Vessel with name '{vessel_name}' does not exist.")
        try:
            vessel.delete()
            return {"message": f"Vessel '{vessel_name}' deleted"}
        except Exception as e:
            raise HttpError(500, f"Failed to delete vessel: {str(e)}")

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
            name=cruise.name.upper(),
            vessel_name=cruise.vessel.name,
            type=cruise.type,
            start_time=cruise.start_time,
            end_time=cruise.end_time,
        )

    @classmethod
    def get_cruises_csv(cls) -> HttpResponse:
        cruises = Cruise.objects.order_by("start_time")

        buffer = io.StringIO()
        writer = csv.writer(buffer)

        # Write header row
        writer.writerow(["name", "vessel", "type", "start_time", "end_time"])

        for cruise in cruises:
            writer.writerow([
                cruise.name.upper(),
                cruise.vessel.name,
                cruise.type,
                cruise.start_time,
                cruise.end_time
            ])

        # Convert to HttpResponse
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="cruises.csv"'
        return response

    @classmethod
    def get_cruises(cls) -> HttpResponse:
        cruises = Cruise.objects.order_by("start_time")
        serialized_cruises = [cls.serialize_cruise(cruise) for cruise in cruises]
        headers = list(CruiseOutput.model_fields.keys())
        data = [
            {header: getattr(cruise, header, "") for header in headers}
            for cruise in serialized_cruises
        ]
        return JsonResponse(data, safe=False)

    
    @classmethod
    def get_cruise(cls, cruise_name: str) -> CruiseOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            return cls.serialize_cruise(cruise)
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")

    @classmethod
    def update_cruise_type_file(cls, cruise_name: str, cruise_type: str):
        rows = []
        found = False
        file = Path('/vast/raw/all/metadata/NES-LTER_cruise_types.csv')
        with file.open("r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Cruise"].lower() == cruise_name:
                    row["Cruise Type"] = cruise_type
                    found = True
                rows.append(row)

        if not found:
            rows.append({
                "Cruise": cruise_name,
                "Cruise Type": cruise_type,
            })

        with file.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Cruise", "Cruise Type"])
            writer.writeheader()
            writer.writerows(rows)

    @classmethod
    def create_cruise(cls, input: AddCruiseInput) -> CruiseOutput:
        try:
            vessel = Vessel.objects.get(name__iexact=input.vessel_name)
            cruise_name = input.name.lower()
            new_cruise = Cruise.objects.create(
                name=cruise_name,
                vessel=vessel,
                type=input.type,
                start_time=input.start_time,
                end_time=input.end_time
            )  
            print(cruise_name, flush=True)
            cls.update_cruise_type_file(cruise_name, input.type)

            return cls.serialize_cruise(new_cruise)
        except IntegrityError:
            raise HttpError(409, f"Cruise with name {input.name} already exists.")
        except Vessel.DoesNotExist:
            raise Http404(f"Vessel with name {input.vessel_name} not found.")


    @classmethod
    def update_cruise(cls, cruise_name: str, input: UpdateCruiseInput) -> CruiseOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            try:
                vessel = Vessel.objects.get(name__iexact=input.vessel_name)
                cruise.name = cruise_name.lower()
                cruise.vessel = vessel
                cruise.type = input.type
                cruise.start_time = input.start_time
                cruise.end_time = input.end_time
                cruise.save()

                cls.update_cruise_type_file(cruise_name, input.type)

                return cls.serialize_cruise(cruise)
            except Vessel.DoesNotExist:
                raise Http404(f"Vessel with name {input.vessel_name} not found.")
        except Cruise.DoesNotExist:
            raise HttpError(404, f"Cruise {cruise_name} not found.")

    @classmethod
    def delete_cruise(cls, cruise_name: str):
        try:
           cruise = Cruise.objects.get(name__iexact=cruise_name)
           cruise.delete()
           return {"status": "success", "message": f"Cruise {cruise_name} deleted."}   
        except Cruise.DoesNotExist:
            raise HttpError(404, f"Cruise {cruise_name} not found.")

    @classmethod
    def get_cruise_readme(cls, cruise_name: str) -> str:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            path = find_readme(cruise_name, 'ctd')
            with open(path, 'r') as fin:
                content = fin.read()
            return HttpResponse(content, content_type="text/plain")
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")

    @classmethod
    def get_cruise_readme_all(cls) -> str:
        path = glob.glob(os.path.join(f'/vast/raw/', 'README*'))[0]
        with open(path, 'r') as fin:
            content = fin.read()
        return HttpResponse(content, content_type="text/plain")
    
    @staticmethod
    def serialize_cast(cast: Cast) -> CastOutput:
        return CastOutput(
                cruise_name=cast.cruise.name.upper(),
                number=cast.number,
                depth=cast.depth,
                latitude=cast.geolocation.y,
                longitude=cast.geolocation.x,
                start_time=cast.start_time,
                end_time=cast.end_time
        )


    @staticmethod
    def get_casts(cruise_name: str) -> List[CastOutput]:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            casts = list(Cast.objects.filter(cruise=cruise))
            casts.sort(
                key=lambda c: (
                    int(re.match(r"^(\d+)", c.number).group(1))
                    if re.match(r"^(\d+)", c.number) else 10**9,
                    re.search(r"[a-z]$", c.number.lower()).group()
                    if re.search(r"[a-z]$", c.number.lower()) else ""
                )
            )
            return [CtdService.serialize_cast(cast) for cast in casts]
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for {cruise_name} .")

    @staticmethod
    def get_casts_csv(cruise_name: str) -> FileResponse:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            casts = list(Cast.objects.filter(cruise=cruise))
            casts.sort(
                key=lambda c: (
                    int(re.match(r"^(\d+)", c.number).group(1))
                    if re.match(r"^(\d+)", c.number) else 10**9,
                    re.search(r"[a-z]$", c.number.lower()).group()
                    if re.search(r"[a-z]$", c.number.lower()) else ""
                )
            )
            serialized_casts = [CtdService.serialize_cast(cast) for cast in casts]
            headers = list(CastOutput.model_fields.keys())
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(headers)
            for cast in serialized_casts:
                writer.writerow([getattr(cast, header, "") for header in headers])
            response = HttpResponse(buffer.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{cruise_name}_ctd_casts.csv"'
            return response
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for {cruise_name} .")

        
    @classmethod
    def get_cast_csv(cls, cruise_name: str, cast_number: str) -> FileResponse:


        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            cruise_name = cruise.name.lower()
            cast_number = cast_number.lstrip("0")
            cast = Cast.objects.get(cruise=cruise, number__iexact=cast_number)
            object_key = f"{cruise_name}_ctd_cast_{cast.number}.csv"
            with get_store() as store:
                try:
                    data = store.get(object_key)
                except Exception as e:
                    print(e, flush=True)
                    raise
            csv_buffer = io.BytesIO(data)
            response = HttpResponse(csv_buffer, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{object_key}"'
            return response
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
            raise Http404(f"Cruise {cruise_name} not found.")
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
                cruise_name=niskin.cast.cruise.name.upper(),
                cast_number=niskin.cast.number,
                niskin_number=niskin.number,
                depth=niskin.depth,
                latitude=niskin.geolocation.y,
                longitude=niskin.geolocation.x
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
    def get_niskins_csv(cruise_name: str, cast_number: str ) -> FileResponse:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            cast = Cast.objects.get(cruise=cruise, number__iexact=cast_number)
            niskins = Niskin.objects.filter(cast=cast).order_by("number")
            serialized_niskins = [CtdService.serialize_niskin(niskin) for niskin in niskins]
            headers = list(NiskinOutput.model_fields.keys())
            buffer = StringIO()
            writer = csv.writer(buffer)
            writer.writerow(headers)
            for niskin in serialized_niskins:
                writer.writerow([getattr(niskin, header, "") for header in headers])
            response = HttpResponse(buffer.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{cruise_name}_ctd_cast_{cast_number}_niskins.csv"'
            return response

        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for cruise {cruise_name} .")

    @staticmethod
    def get_niskins(cruise_name: str, cast_number: str ) -> List[NiskinOutput]:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            cast = Cast.objects.get(cruise=cruise, number__iexact=cast_number)
            niskins = Niskin.objects.filter(cast=cast).order_by("number")
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
            return {"status": "success", "message": f"Niskin {niskin_number} on cruise {cruise_name} for cast {cast_number} deleted."}   
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
        except Cast.DoesNotExist:
            raise Http404(f"Cast not found for cruise {cruise_name} .")
        except Niskin.DoesNotExist:
            raise Http404(f"Niskin not found for cruise {cruise_name} cast {cast_number} .")

    @classmethod
    def get_bottles(cls, cruise_name: str) -> FileResponse:

        FILE_SUFFIX = '_ctd_bottles.csv'
        try:
            Cruise.objects.get(name__iexact=cruise_name) 
            object_key = f"{cruise_name.lower()}{FILE_SUFFIX}"
            with get_store() as store:
                try:
                    data = store.get(object_key)
                except Exception as e:
                    print(e, flush=True)
                    raise Http404(f"File {object_key} not found for cruise {cruise_name}.")
            csv_buffer = io.BytesIO(data)
            response = HttpResponse(csv_buffer, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{object_key}"'
            return response
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")    

    @classmethod
    def get_bottle_summary(cls, cruise_name: str) -> FileResponse:

        FILE_SUFFIX = '_ctd_bottle_summary.csv'
        try:
            Cruise.objects.get(name__iexact=cruise_name) 
            object_key = f"{cruise_name.lower()}{FILE_SUFFIX}"
            with get_store() as store:
                try:
                    data = store.get(object_key)
                except Exception as e:
                    print(e, flush=True)
                    return []
            csv_buffer = io.BytesIO(data)
            response = HttpResponse(csv_buffer, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{object_key}"'
            return response
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")    

    @classmethod
    def get_metadata(cls, cruise_name: str) -> FileResponse:

        FILE_SUFFIX = '_ctd_metadata.csv'
        try:
            Cruise.objects.get(name__iexact=cruise_name) 
            object_key = f"{cruise_name.lower()}{FILE_SUFFIX}"
            with get_store() as store:
                try:
                    data = store.get(object_key)
                except Exception as e:
                    print(e, flush=True)
                    raise
            csv_buffer = io.BytesIO(data)
            response = HttpResponse(csv_buffer, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{object_key}"'
            return response
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")    

    @classmethod
    def get_bathymetry(cls) -> FileResponse:
        filepath = '/vast/raw/all/bathymetry/neslter_bathymetry.csv'
        try:
            return FileResponse(open(filepath, 'rb'), as_attachment=True, filename='bathymetry.csv')
        except FileNotFoundError:
            raise Http404("Bathymetry file not found.")


