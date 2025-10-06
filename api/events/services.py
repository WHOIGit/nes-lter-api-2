import csv
import os
import glob
import pandas as pd
import numpy as np
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

FILE_SUFFIX = '_elog.csv'
DATETIME = 'dateTime8601'
MESSAGE_ID = 'Message ID'  

class EventOutput(BaseModel):
    r2r_event: str
    message_id: int
    instrument: str
    action: str
    station: str
    cast: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    comment: str
    datetime: datetime


class FilterEventInput(BaseModel):
    instrument: Optional[str] = None
    action: Optional[str] = None
    station: Optional[str] = ""
    cast: Optional[str] = ""
    comment: Optional[str] = ""

class EditEventInput(BaseModel):
    message_id: Optional[int] = None
    instrument: Optional[str] = None
    action: Optional[str] = None
    station: Optional[str] = ""
    cast: Optional[str] = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    comment: Optional[str] = ""
    datetime: Optional[datetime] = None

    
class EventService:
    FILE_SUFFIX = '_elog.csv'
    
    @staticmethod
    def serialize_event(event: Event) -> EventOutput:
        if event.geolocation and isinstance(event.geolocation, Point) and not event.geolocation.empty:
            latitude = event.geolocation.y
            longitude = event.geolocation.x
        else:
            latitude = None
            longitude = None

        return EventOutput(
                r2r_event=event.r2r_event,
                message_id=event.message_id,
                instrument=event.instrument,
                action=event.action,
                station=event.station,
                cast=event.cast,
                latitude = latitude,
                longitude = longitude,
                comment=event.comment,
                datetime=event.datetime
        )

    def store_csv_file(self, cruise_name, csv_data):
        URL = os.getenv("URL")
        TOKEN = os.getenv("TOKEN")
        MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")

        df = pd.DataFrame(csv_data)
        df[DATETIME] = pd.to_datetime(df[DATETIME])
        df = df.sort_values(by=DATETIME)
        df["Station"] = df["Station"].replace("nan", "")
        df["Cast"] = df["Cast"].replace("nan", "")
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_binary = csv_buffer.getvalue().encode("utf-8")
        # Use the put method to store the CSV in the vast media store
        object_key = f"{cruise_name}{FILE_SUFFIX}"
        with MediaStore(URL, token=TOKEN) as store:
            prefix = PrefixStore(store, MEDIASTORE_PREFIX)
            try:
                prefix.put(object_key, csv_binary)
            except Exception as e:
                print(e, flush=True)
                raise

    def apply_corrections(self, path):
        corr = pd.read_excel(path)
        corr[DATETIME] = pd.to_datetime(corr[DATETIME], utc=True)
        corr.pop('Instrument')
        corr.pop('Action')
        return corr

    def apply_additions(self, addns_path):
        addns = pd.read_excel(addns_path)
        addns[DATETIME] = pd.to_datetime(addns[DATETIME], utc=True, format="ISO8601")
        # add placeholder columns
        addns.insert(4, MESSAGE_ID, np.nan)
        addns.insert(4, 'Longitude', np.nan)
        addns.insert(4, 'Latitude', np.nan)
        addns.insert(4, 'Cast', np.nan)
        return addns
    
    @classmethod
    def get_events(cls, cruise_name: str) -> FileResponse:
        URL = os.getenv("URL")
        TOKEN = os.getenv("TOKEN")
        MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")

        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            if Event.objects.filter(cruise=cruise).exists():
                object_key = f"{cruise_name.lower()}{FILE_SUFFIX}"
                with MediaStore(URL, token=TOKEN) as store:
                    prefix = PrefixStore(store, MEDIASTORE_PREFIX)
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
                raise Http404(f"Event data not imported.")    
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")  
       
    @classmethod
    def get_instruments(cls, cruise_name: str) -> List[str]:
        URL = os.getenv("URL")
        TOKEN = os.getenv("TOKEN")
        MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")

        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            if Event.objects.filter(cruise=cruise).exists():
                events = Event.objects.filter(cruise=cruise)

                # Extract unique instruments, sorted alphabetically
                instruments = events.values_list('instrument', flat=True).distinct().order_by('instrument')
                return list(instruments)
            else:
                raise Http404("Event data not imported.")
                return []
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
            print(events.query, flush=True)
            print([e.id for e in events], flush=True)

            return [EventService.serialize_event(event) for event in events]
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")  

    @classmethod
    def edit_events(cls, cruise_name: str, r2r_event: str, input: EditEventInput) -> EventOutput:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            event = Event.objects.get(cruise=cruise, r2r_event=r2r_event)
            if input.message_id:
                event.message_id = input.message_id
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
                    "R2R_Event": e.r2r_event,
                    MESSAGE_ID: e.message_id,
                    DATETIME: e.datetime,
                    "Instrument": e.instrument,
                    "Action": e.action,
                    "Station": e.station,
                    "Cast": e.cast,
                    "Latitude": e.geolocation.y if not e.geolocation.empty else None,
                    "Longitude": e.geolocation.x if not e.geolocation.empty else None,
                    "Comment": e.comment
                }
                for e in events
            ]

            cls.store_csv_file(cls, cruise_name, data)
            
            return cls.serialize_event(event)
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")  
        except Event.DoesNotExist:
            raise Http404(f"Event {r2r_event} not found for {cruise_name} .")

    @classmethod
    def history_events(cls, cruise_name: str) -> str:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            events = Event.objects.filter(cruise=cruise)
            history_data = []
            for event in events:
                for record in event.history.all():
                    if record.prev_record:
                        diff = record.diff_against(record.prev_record)
                        if diff.changed_fields:
                            history_data.append({
                                'r2r_event': event.r2r_event,
                                'message_id': event.message_id,
                                'history_date': record.history_date,
                                'history_user': record.history_user,
                                'history_type': record.get_history_type_display(),
                                'changed_data': diff.changed_fields,
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
            if not events.exists():
                return {"status": "success", "message": f"No events on cruise {cruise_name} to delete."}   
            else:
                events.delete()
            return {"status": "success", "message": f"Events on cruise {cruise_name} deleted."}   
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
