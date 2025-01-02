import csv
import os
import glob
from datetime import datetime
from django.http import JsonResponse
from django.http import HttpResponse

from pydantic import BaseModel
import pandas as pd

from core.models import Cruise

from django.db import IntegrityError
from django.http import FileResponse, Http404
from ninja.errors import HttpError

from storage.fs import FilesystemStore
import io
from core.models import Underway

class UnderwayOutput(BaseModel):
    file_name: str

class UnderwayService:

    UNDERWAY_DATA_DIR = '/data/underway'
    object_store = FilesystemStore(UNDERWAY_DATA_DIR)

    FILE_SUFFIX = '_underway.csv'

    def __init__(self):
        os.makedirs(self.UNDERWAY_DATA_DIR, exist_ok=True)

    @classmethod
    def read_data(cls, cruise_name: str):

        # do we want to store the column headers as metadata for every underway file?

        underway_metadata = {
           'ar': {'read_csv_args': {'skiprows': 1}, 'date_column': 'DATE_GMT', 'date_format': '%Y/%m/%d'},
           'at': {'read_csv_args': {'skiprows': 1}, 'date_column': 'DATE_GMT', 'date_format': '%Y/%m/%d'},
           'en': {'read_csv_args': {'comment': '#'}, 'date_column': 'DateTime_ISO8601', 'date_format': None},
           'hrs': {'read_csv_args': {'header': [0]}, 'date_column': 'date', 'date_format': '%Y-%m-%d %H:%M:%S%z'}
}
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            #temporary local mount until can access vast nfs mount on a vm
            directory = f'/vast/raw/{cruise_name}/underway/'
            file_pattern = os.path.join(directory, '*')
            files = glob.glob(file_pattern)
            underway_files = [f for f in files if "README" not in os.path.basename(f)]
            if not underway_files:
                raise Http404(f"Cruise {cruise_name} underway data not found.")

            # Concatenate the CSV files
            cruise_prefix = next((key for key in underway_metadata if cruise_name.startswith(key)), None)
            if cruise_prefix:
                metadata = underway_metadata[cruise_prefix]
                data_frames = []
                for file in underway_files:
                    df = pd.read_csv(file, **metadata['read_csv_args'])
                    data_frames.append(df)

                combined_data = pd.concat(data_frames, ignore_index=True)

                date_column = metadata['date_column']
                date_format = metadata['date_format']
                if date_format:
                    start_date = pd.to_datetime(combined_data[date_column].iloc[0], format=date_format)
                    end_date = pd.to_datetime(combined_data[date_column].iloc[-1], format=date_format)
                else:
                    start_date = pd.to_datetime(combined_data[date_column].iloc[0])
                    end_date = pd.to_datetime(combined_data[date_column].iloc[-1])
            else:
                raise ValueError(f"Unsupported cruise type for cruise_name: {cruise_name}")
 
            start_year = start_date.year
            start_month = start_date.month
            end_year = end_date.year
            end_month = end_date.month

            Underway.objects.create(
                    cruise=cruise,
                    start_month=start_month,
                    start_year=start_year,
                    end_month=end_month,
                    end_year=end_year
                    )       

            # Generate CSV content in memory
            csv_buffer = io.StringIO()
            combined_data.to_csv(csv_buffer, index=False)
            csv_binary = csv_buffer.getvalue().encode('utf-8')
            # Use the put method to store the CSV
            object_key = f"{cruise_name}{cls.FILE_SUFFIX}"
            cls.object_store.put(object_key, csv_binary)
            return {"status": "success", "message": "Underway Data successfully imported."}
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")
        except Exception as e:
            raise HttpError(500, f"An error occurred: {str(e)}")
 
    
    @classmethod
    def get_data(cls, cruise_name: str) -> FileResponse:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            object_key = f"{cruise_name}{cls.FILE_SUFFIX}"
            data = cls.object_store.get(object_key)
            response = HttpResponse(data, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{object_key}"'
            return response
        except FileNotFoundError:
           raise Http404(f"Underway data not imported.")    
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")   
       
    @classmethod
    def get_column_headers(cls, cruise_name: str) -> JsonResponse:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name) 
            object_key = f"{cruise_name}{cls.FILE_SUFFIX}"
            data = cls.object_store.get(object_key)
            csv_buffer = io.BytesIO(data)
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
        except FileNotFoundError:
           raise Http404(f"Underway data not imported.")    
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")   

    @classmethod
    def find_underway_files(cls, month: int, year: int) -> list[UnderwayOutput]:
        responses = []
        underway_objects = Underway.objects.all()
        for underway in underway_objects:
            if underway.start_month == month and underway.start_year == year \
              or underway.end_month == month and underway.end_year == year :
                object_key = f"{underway.cruise.name}{cls.FILE_SUFFIX}"
                data = cls.object_store.get(object_key)
                response = HttpResponse(data, content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{object_key}"'
                responses.append(response)
        if not responses:
            raise Http404(f"Underway data files not found for month {month } and year {year}.")   
        else:
            return response

    