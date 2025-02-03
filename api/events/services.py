import csv
import os
import glob
import pandas as pd
from django.conf import settings
from typing import Optional, List, Tuple
from datetime import datetime
from django.contrib.gis.db.models import PointField
from django.contrib.gis.geos import Point, point
from django.http import JsonResponse
from django.http import HttpResponse

from pydantic import BaseModel

from core.models import Cruise, Event

from django.db import IntegrityError
from django.http import FileResponse, Http404
from ninja.errors import HttpError

from storage.fs import FilesystemStore
from storage.mediastore import MediaStore
import io
from storage.utils import PrefixStore
import dotenv

class EventOutput(BaseModel):
    message_id: int
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

    dotenv.load_dotenv()
    URL = os.getenv("URL")
    TOKEN = os.getenv("TOKEN")

    FILE_SUFFIX = '_elog.csv'
    
    @staticmethod
    def serialize_event(event: Event) -> EventOutput:
        return EventOutput(
                message_id=event.message_id,
                instrument=event.instrument,
                action=event.action,
                station=event.station,
                cast=event.cast,
                latitude=event.geolocation.y,
                longitude=event.geolocation.x,
                comment=event.comment,
                datetime=event.datetime
        )

    @classmethod
    def store_csv_file(cls, cruise_name, csv_data):
        df = pd.DataFrame(csv_data)
        df['dateTime8601'] = pd.to_datetime(df['dateTime8601'])
        df = df.sort_values(by='dateTime8601')
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_binary = csv_buffer.getvalue().encode("utf-8")
        # Use the put method to store the CSV in the vast media store
        object_key = f"{cruise_name}{cls.FILE_SUFFIX}"
        with MediaStore(cls.URL, token=cls.TOKEN) as store:
            prefix = PrefixStore(store, settings.MEDIASTORE_PREFIX)
            try:
                prefix.put(object_key, csv_binary)
            except Exception as e:
                print(e, flush=True)
                raise

    @classmethod
    def read_events(cls, cruise_name: str):
        csv_data = []
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            #temporary local mount until can access vast nfs mount on a vm
            directory = f'/vast/raw/{cruise_name}/elog/'
            file_pattern = os.path.join(directory, 'R2R_ELOG*')
            matching_files = glob.glob(file_pattern)
            if matching_files:
                file_path = matching_files[0]
                df = pd.read_csv(file_path, parse_dates=['dateTime8601'], dtype={'Station': str, 'Cast': str})
                df['Comment'] = df['Comment'].fillna('')

                for _, row in df.iterrows():
                    longitude = row['Longitude']
                    latitude = row['Latitude']
                    if longitude == "NaN" or latitude == "NaN" or longitude == "NO_GPS" or latitude == "NO_GPS":
                        geolocation = Point(0.0, 0.0, srid=4326)
                    else:
                        geolocation = Point(float(longitude), float(latitude), srid=4326)                    
                    event = Event.objects.create(
                            cruise=cruise,
                            message_id=row['Message ID'],
                            instrument=row['Instrument'],
                            action=row['Action'],
                            station=row['Station'],
                            cast=row['Cast'],
                            comment=row['Comment'],
                            geolocation=geolocation,
                            datetime=row['dateTime8601']
                        )

                    csv_data.append({
                        "Message ID": event.message_id,
                        "dateTime8601": event.datetime,
                        "Instrument": event.instrument,
                        "Action": event.action,
                        "Station": event.station,
                        "Cast": event.cast,
                        "Latitude": latitude,
                        "Longitude": longitude,
                        "Comment": event.comment,
                    })

                cls.store_csv_file(cruise_name, csv_data)

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
    def get_events(cls, cruise_name: str) -> FileResponse:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            if Event.objects.filter(cruise=cruise).exists():
                object_key = f"{cruise_name}{cls.FILE_SUFFIX}"
                with MediaStore(cls.URL, token=cls.TOKEN) as store:
                    prefix = PrefixStore(store, settings.MEDIASTORE_PREFIX)
                    try:
                        data = prefix.get(object_key)
                    except Exception as e:
                        print(e, flush=True)
                        raise
                csv_buffer = io.BytesIO(data)
                response = HttpResponse(csv_buffer, content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{object_key}"'
                return response
            else:
                raise Http404(f"Underway data not imported.")    
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
    def edit_events(cls, cruise_name: str, message_id: int, input: EditEventInput) -> EventOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            event = Event.objects.get(cruise=cruise, message_id=message_id)
            if input.instrument:
                event.instrument = input.instrument
            if input.action:
                event.action = input.action
            if input.station:
                event.station = input.station
            if input.cast:
                event.cast = input.cast
            if input.latitude and input.longitude:
                event.geolocation = Point(float(input.longitude), float(input.latitude), srid=4326)    
            if input.comment:
                event.comment = input.comment
            if input.datetime:
                event.datetime = input.datetime
            event.save()

            # get all the events
            events = Event.objects.filter(cruise=cruise)
            data = [
                {
                    "Message ID": e.message_id,
                    "dateTime8601": e.datetime,
                    "Instrument": e.instrument,
                    "Action": e.action,
                    "Station": e.station,
                    "Cast": e.cast,
                    "Latitude": e.geolocation.y,
                    "Longitude": e.geolocation.x,
                    "Comment": e.comment
                }
                for e in events
            ]

            cls.store_csv_file(cruise_name, data)
            
            return cls.serialize_event(event)
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")  
        except Event.DoesNotExist:
            raise Http404(f"Event {message_id} not found for {cruise_name} .")

    @classmethod
    def history_events(cls, cruise_name: str) -> str:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            events = Event.objects.filter(cruise=cruise)
            history_data = []
            for event in events:
                for record in event.history.all():
                    history_data.append({
                    'message_id': event.message_id,
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
