import csv
import os
import glob
from typing import Optional, List, Tuple
from datetime import datetime
from django.contrib.gis.db.models import PointField
from django.contrib.gis.geos import Point, point
from django.http import JsonResponse

from pydantic import BaseModel

from core.models import Cruise, Event

from django.db import IntegrityError
from django.http import Http404
from ninja.errors import HttpError

class EventOutput(BaseModel):
    number: int
    instrument: str
    action: str
    station: str
    cast: str
    latitude: float
    longitude: float
    comment: str
    datetime: datetime


class FilterEventInput(BaseModel):
    instrument: Optional[str] = None
    action: Optional[str] = None
    station: Optional[str] = None
    cast: Optional[str] = None
    comment: Optional[str] = None

class EditEventInput(BaseModel):
    instrument: Optional[str] = None
    action: Optional[str] = None
    station: Optional[str] = None
    cast: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    comment: Optional[str] = None
    datetime: Optional[datetime] = None

    
class EventService:
    
    @staticmethod
    def serialize_event(event: Event) -> EventOutput:
        return EventOutput(
                number=event.number,
                instrument=event.instrument,
                action=event.action,
                station=event.station,
                cast=event.cast,
                latitude=event.geolocation.y,
                longitude=event.geolocation.x,
                comment=event.comment,
                datetime=event.datetime
        )

    #temporary until upload implemented
    @classmethod
    def read_events(cls, cruise_name: str):
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            directory = f'events/data/{cruise_name}/'
            file_pattern = os.path.join(directory, 'R2R_ELOG*')
            matching_files = glob.glob(file_pattern)
            if matching_files:
                file_path = matching_files[0]    
                with open(file_path, 'r') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        longitude = row['Longitude']
                        latitude = row['Latitude']
                        if longitude == "NaN" or latitude == "NaN" or longitude == "NO_GPS" or latitude == "NO_GPS":
                            geolocation = Point(0.0, 0.0, srid=4326)
                        else:
                            geolocation = Point(float(longitude), float(latitude), srid=4326)                    
                        Event.objects.create(
                            cruise=cruise,
                            number=row['Message ID'],
                            instrument=row['Instrument'],
                            action=row['Action'],
                            station=row['Station'],
                            cast=row['Cast'],
                            comment=row['Comment'],
                            geolocation=geolocation,
                            datetime = datetime.strptime(row['Date'], '%a  %d %b %Y %H:%M:%S %z')
                        )
                    return {"status": "success", "message": "Events have been successfully imported."}
            else:
                raise Http404(f"Cruise {cruise_name} event log not found.")
        except IntegrityError:
            raise HttpError(409, f"error': f'Cruise with event id {row['Message ID']} already exists.")
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")
        except Exception as e:
            raise HttpError(500, f"An error occurred: {str(e)}")
 
    
    @classmethod
    def get_events(cls, cruise_name: str) -> List[EventOutput]:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            events = Event.objects.filter(cruise=cruise)
            return [EventService.serialize_event(event) for event in events]
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")    
        
       
    @classmethod
    def filter_events(cls, cruise_name: str, input: FilterEventInput) -> List[EventOutput]:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            events = Event.objects.filter(cruise=cruise)
            if input.instrument:
                events = events.filter(instrument__iexact=input.instrument)
            if input.action:
                events = events.filter(action__iexact=input.action)
            if input.station:
                events = events.filter(station__iexact=input.station)
            if input.cast:
                events = events.filter(cast__iexact=input.cast)
            if input.comment:
                events = events.filter(comment__icontains=input.comment)
            return [EventService.serialize_event(event) for event in events]
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")  

    @classmethod
    def edit_events(cls, cruise_name: str, event_number: int, input: EditEventInput) -> EventOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            event = Event.objects.get(cruise=cruise, number=event_number)
            if input.instrument:
                event.instrument = input.instrument
            if input.action:
                event.action = input.action
            if input.station:
                event.station = input.station
            if input.cast:
                event.cast = input.cast
            if input.latitude:
                event.latitude = input.latitude
            if input.longitude:
                event.longitude = input.longitude
            if input.comment:
                event.comment = input.comment
            if input.datetime:
                event.datetime = input.datetime
            event.save()
            return cls.serialize_event(event)
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")  
        except Event.DoesNotExist:
            raise Http404(f"Event {event_number} not found for {cruise_name} .")

    @classmethod
    def history_events(cls, cruise_name: str) -> str:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            events = Event.objects.filter(cruise=cruise)
            history_data = []
            for event in events:
                for record in event.history.all():
                    history_data.append({
                    'event_number': event.number,
                    'history_date': record.history_date,
                    'history_user': record.history_user,
                    'history_type': record.get_history_type_display(),
                    'changed_data': record.diff_against(record.prev_record).changed_fields if record.prev_record else 'N/A',
            })
            history_data = sorted(history_data, key=lambda x: x['history_date'], reverse=True)
            return JsonResponse(history_data, safe=False)
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")  
        

    @staticmethod
    def delete_events(cruise_name: str):
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            events = Event.objects.filter(cruise=cruise)
            events.delete()
            return {"status": "success", "message": f"Events on cruise {cruise_name} deleted."}   
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
