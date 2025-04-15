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
import dotenv

FILE_SUFFIX = '_elog.csv'
DATETIME = 'dateTime8601'
MESSAGE_ID = 'Message ID'  

class EventOutput(BaseModel):
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
        if event.geolocation and isinstance(event.geolocation, Point) and not event.geolocation.empty:
            latitude = event.geolocation.y
            longitude = event.geolocation.x
        else:
            latitude = None
            longitude = None

        return EventOutput(
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
        df = pd.DataFrame(csv_data)
        df[DATETIME] = pd.to_datetime(df[DATETIME])
        df = df.sort_values(by=DATETIME)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_binary = csv_buffer.getvalue().encode("utf-8")
        # Use the put method to store the CSV in the vast media store
        object_key = f"{cruise_name}{FILE_SUFFIX}"
        with MediaStore(self.URL, token=self.TOKEN) as store:
            prefix = PrefixStore(store, settings.MEDIASTORE_PREFIX)
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
    def read_events(cls, cruise_name: str):
        csv_data = []
        df = pd.DataFrame()
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            #temporary local mount until can access vast nfs mount on a vm
            directory = f'/vast/corrected/{cruise_name}/elog/'
            file_pattern = os.path.join(directory, '*_elog.csv')
            matching_file = glob.glob(file_pattern)
            if matching_file:
                file_path = matching_file[0]
                df = pd.read_csv(file_path, parse_dates=[DATETIME], dtype={'Station': str, 'Cast': str})
                df[MESSAGE_ID] = range(1, len(df) + 1)   # assign message ids
            else:
                directory = f'/vast/raw/{cruise_name}/elog/'
                file_pattern = os.path.join(directory, 'R2R_ELOG*FINAL*')
                matching_file = glob.glob(file_pattern)
                if matching_file:
                    file_path = matching_file[0]
                    df = pd.read_csv(file_path, parse_dates=[DATETIME], dtype={'Station': str, 'Cast': str})
                
                    file_pattern = os.path.join(directory, 'R2R_ELOG*corrections.xlsx')
                    matching_file = glob.glob(file_pattern)
                    if matching_file:
                        corr = cls.apply_corrections(cls, matching_file[0])
                        merged = df.merge(corr, on=MESSAGE_ID, how='left')
                        DATETIME_X = '{}_x'.format(DATETIME)
                        DATETIME_Y = '{}_y'.format(DATETIME)
                        merged[DATETIME] = pd.to_datetime(merged[DATETIME_Y].combine_first(merged[DATETIME_X]), utc=True)
                        df = merged
                
                    file_pattern = os.path.join(directory, 'R2R_ELOG*additions.xlsx')
                    matching_file = glob.glob(file_pattern)
                    if matching_file:
                        addns = cls.apply_additions(cls, matching_file[0])
                        df = pd.concat([df, addns])
                        max_message_id = int(df[MESSAGE_ID].max())
                        new_ids = range(max_message_id + 1, max_message_id + 1 + df[MESSAGE_ID].isna().sum())
                        df.loc[df[MESSAGE_ID].isna(), MESSAGE_ID] = new_ids
                        df = df.reset_index(drop=True)
                        df[MESSAGE_ID] = df[MESSAGE_ID].astype(pd.Int64Dtype())

            if not df.empty:
                df['Comment'] = df['Comment'].fillna('')

                for _, row in df.iterrows():
                    longitude = row['Longitude']
                    latitude = row['Latitude']
                    if longitude == "NaN" or latitude == "NaN" or longitude == "NO_GPS" or latitude == "NO_GPS":
                        geolocation = Point(0.0, 0.0, srid=4326)
                    else:
                        geolocation = Point(float(longitude), float(latitude), srid=4326) 

                    event, created = Event.objects.update_or_create(
                            cruise=cruise,
                            message_id=row[MESSAGE_ID],
                            instrument=row['Instrument'],
                            action=row['Action'],
                            station=row['Station'],
                            cast=row['Cast'],
                            comment=row['Comment'],
                            geolocation=geolocation,
                            datetime=row[DATETIME]
                        )

                    csv_data.append({
                        MESSAGE_ID: event.message_id,
                        DATETIME: event.datetime,
                        "Instrument": event.instrument,
                        "Action": event.action,
                        "Station": event.station,
                        "Cast": event.cast,
                        "Latitude": latitude,
                        "Longitude": longitude,
                        "Comment": event.comment,
                    })

                cls.store_csv_file(cls, cruise_name, csv_data)

                return {"status": "success", "message": "Events have been successfully imported."}
            else:
                raise Http404(f"Cruise {cruise_name} event log not found.")
        except IntegrityError:
            raise HttpError(409, f"error': f'Cruise with event id {row[MESSAGE_ID]} already exists.")
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")
        except Exception as e:
            raise HttpError(500, f"An error occurred: {str(e)}")
 
    
    @classmethod
    def get_events(cls, cruise_name: str) -> FileResponse:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            if Event.objects.filter(cruise=cruise).exists():
                object_key = f"{cruise_name}{FILE_SUFFIX}"
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
                raise Http404(f"Event data not imported.")    
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
            if not events.exists():
                return {"status": "success", "message": f"No events on cruise {cruise_name} to delete."}   
            else:
                events.delete()
            return {"status": "success", "message": f"Events on cruise {cruise_name} deleted."}   
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")
