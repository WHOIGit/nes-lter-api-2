import csv
import os
import glob

from io import BytesIO

from datetime import datetime, time, timedelta, timezone as dt_tz
from django.http import JsonResponse
from django.http import HttpResponse

from pydantic import BaseModel
from django.db.models import Q
import pandas as pd

from core.models import Cruise
from core.models import Underway

from django.http import FileResponse, Http404
from ninja.errors import HttpError

from core.utils import get_store, find_readme

class UnderwayOutput(BaseModel):
    file_name: str

class UnderwayService:
    FILE_SUFFIX = '_underway.csv'
    HEADER_SUFFIX = '_underway_column_def.csv'
    
    @classmethod
    def get_data(cls, cruise_name: str) -> FileResponse:
        URL = os.getenv("URL")
        TOKEN = os.getenv("TOKEN")
        MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            if Underway.objects.filter(cruise=cruise).exists():
                object_key = f"{cruise_name.lower()}{cls.FILE_SUFFIX}"
                with get_store(URL, TOKEN, MEDIASTORE_PREFIX) as store:
                   try:
                       data = store.get(object_key)
                   except Exception as e:
                       print(e, flush=True)
                       raise
                csv_buffer = BytesIO(data)
                response = HttpResponse(csv_buffer, content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{object_key}"'
                return response
            else:
                raise Http404(f"Underway data not imported. Import using manage.py importunderwaydata")    
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")   
       
    @classmethod
    def get_column_headers(cls, cruise_name: str) -> JsonResponse:
        URL = os.getenv("URL")
        TOKEN = os.getenv("TOKEN")
        MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            if Underway.objects.filter(cruise=cruise).exists(): 
                object_key = f"{cruise_name.lower()}{cls.FILE_SUFFIX}"
                with get_store(URL, TOKEN, MEDIASTORE_PREFIX) as store:
                    try:
                        data = store.get(object_key)
                    except Exception as e:
                        print(e, flush=True)
                        raise
                csv_buffer = BytesIO(data)
                df = pd.read_csv(csv_buffer)
                columns = df.columns.tolist()
                response = {
                    "metadata": {
                        "columns": columns,
                        "num_columns": len(columns),
                    },
                    "data": None
                }    
                return JsonResponse(response, safe=False)
            else:
               raise Http404(f"Underway data not imported.")    
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")   

    @classmethod
    def find_underway_files(cls, start_timestamp: str, end_timestamp: str) -> list[UnderwayOutput]:
        try:
            start_date = datetime.strptime(start_timestamp, "%Y-%m-%d")
            end_date = datetime.strptime(end_timestamp, "%Y-%m-%d")
        except ValueError:
            raise HttpError(400, "Invalid date format. Use yyyy-mm-dd")

        # datetime format yyyy-mm-dd hh:mm:ss
        if end_date < start_date:
            raise HttpError(500, f"end_timestamp must be greater than or equal to start_timestamp")

        UTC = dt_tz.utc
        start_dt = datetime.combine(start_date, time.min, tzinfo=UTC)
        end_dt = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)

        underway_objects = Underway.objects.filter(
            Q(start_datetime__lte=end_dt) & Q(end_datetime__gte=start_dt)
        )

        responses = []
        for underway in underway_objects:
            object_key = f"{underway.cruise.name}{cls.FILE_SUFFIX}"
            responses.append(UnderwayOutput(file_name=object_key))
        if not responses:
            raise Http404(f"Underway data files not found between start timestamp {start_timestamp} and {end_timestamp}.")   
        else:
            return responses

    @classmethod
    def get_readme(cls, cruise_name: str) -> str:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            path = find_readme(cruise_name, 'underway')
            with open(path, 'r') as fin:
                content = fin.read()
            return HttpResponse(content, content_type="text/plain")
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")

    @classmethod
    def get_column_definition(cls, cruise_name: str) -> FileResponse:
        URL = os.getenv("URL")
        TOKEN = os.getenv("TOKEN")
        MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            if Underway.objects.filter(cruise=cruise).exists():
                if cruise_name.lower().startswith("en"):
                    object_key = f"{cruise_name.lower()}{cls.HEADER_SUFFIX}"
                    with get_store(URL, TOKEN, MEDIASTORE_PREFIX) as store:
                       try:
                           data = store.get(object_key)
                       except Exception as e:
                           print(e, flush=True)
                           raise
                    csv_buffer = BytesIO(data)
                    response = HttpResponse(csv_buffer, content_type='text/csv')
                    response['Content-Disposition'] = f'attachment; filename="{object_key}"'
                    return response
                else:
                    raise Http404(f"Cruise {cruise_name} is not an Endeavor cruise.")   
            else:
                raise Http404(f"Underway data not imported. Import using manage.py importunderwaydata")    
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")   
