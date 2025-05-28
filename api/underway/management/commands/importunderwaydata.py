import csv
import os
import glob
from django.core.management.base import BaseCommand, CommandError
from io import BytesIO, StringIO
import pandas as pd
from core.models import Cruise
from core.models import Underway
from storage.fs import FilesystemStore
from storage.mediastore import MediaStore
from storage.utils import PrefixStore
from django.conf import settings
from pathlib import Path
from django.utils import timezone

class Command(BaseCommand):
    help = 'Import in Underway Data files for a given Cruise. If Cruise is not supplied, all Cruises will be imported.'

    def __init__(self):
        super().__init__()
        self.URL = os.getenv("URL")
        self.TOKEN = os.getenv("TOKEN")
        self.MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")

    FILE_SUFFIX = '_underway.csv'

    def add_arguments(self, parser):
        parser.add_argument('--cruise_name', type=str, help='Optional name of the cruise.', default=None)

    def make_aware_if_naive(self, dt):
        if dt is not None and dt.tzinfo is None:
            return timezone.make_aware(dt)
        return dt

    def handle(self, *args, **options):
        cruise_name = options['cruise_name']
        
        underway_metadata = {
           'ar': {'read_csv_args': {'skiprows': 1}, 'date_column': 'DATE_GMT', 'date_format': '%Y/%m/%d'},
           'at': {'read_csv_args': {'skiprows': 1}, 'date_column': 'DATE_GMT', 'date_format': '%Y/%m/%d'},
           'en': {'read_csv_args': {'comment': '#'}, 'date_column': 'DateTime_ISO8601', 'date_format': None},
           'hrs': {'read_csv_args': {'header': [0]}, 'date_column': 'date', 'date_format': '%Y-%m-%d %H:%M:%S%z'},
           'ae': {'read_csv_args': {'header': [0]}, 'date_column': 'YMD', 'date_format': '%Y%m%d'}
        }

        if cruise_name is None:
            parent_dir = Path('/vast/raw')
            cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
        else:
            cruises = [cruise_name]

        for cruise_name in cruises:
            try:
                cruise = Cruise.objects.get(name__iexact=cruise_name)
                #temporary local mount until can access vast nfs mount on a vm
                directory = f'/vast/raw/{cruise_name}/underway/'
                file_pattern = os.path.join(directory, '*')
                files = glob.glob(file_pattern)
                underway_files = [
                    f for f in files
                    if os.path.isfile(f) and "README" not in os.path.basename(f)
                ]
                if not underway_files:
                    raise CommandError(f'Cruise {cruise_name} underway data not found.')

                # Concatenate the CSV files
                cruise_prefix = next((key for key in underway_metadata if cruise.name.startswith(key)), None)
                if cruise_prefix:
                    metadata = underway_metadata[cruise_prefix]
                    data_frames = []
                    for file in underway_files:
                        df = pd.read_csv(file, **metadata['read_csv_args'])
                        data_frames.append(df)

                    combined_data = pd.concat(data_frames, ignore_index=True)
                    
                    # Select only numeric columns and fill NaN values with 'NaN'
                    combined_data[combined_data.select_dtypes(include=['number']).columns] = combined_data.select_dtypes(include=['number']).fillna('NaN')
                    if 'QSR - S/N 10367' in combined_data.columns:    #hrs2303
                        combined_data['QSR - S/N 10367'] = combined_data['QSR - S/N 10367'].fillna('NaN')

                    date_column = metadata['date_column']
                    date_format = metadata['date_format']
                    if date_format:
                        start_datetime = pd.to_datetime(combined_data[date_column].iloc[0], format=date_format)
                        end_datetime = pd.to_datetime(combined_data[date_column].iloc[-1], format=date_format)
                    else:
                        start_datetime = pd.to_datetime(combined_data[date_column].iloc[0])
                        end_datetime = pd.to_datetime(combined_data[date_column].iloc[-1])
                else:
                    raise ValueError(f"Unsupported cruise type for cruise_name: {cruise_name}")
                start_datetime = None if pd.isna(start_datetime) else self.make_aware_if_naive(start_datetime)
                end_datetime = None if pd.isna(end_datetime) else self.make_aware_if_naive(end_datetime)


                Underway.objects.update_or_create(
                        cruise=cruise,
                        start_datetime=start_datetime,
                        end_datetime=end_datetime,
                        )       
                
                csv_buffer = StringIO()
                combined_data.to_csv(csv_buffer, index=False)
                csv_binary = csv_buffer.getvalue().encode('utf-8')
                # Use the put method to store the CSV in the vast media store
                object_key = f"{cruise_name}{self.FILE_SUFFIX}"
                with MediaStore(self.URL, token=self.TOKEN) as store:
                    prefix = PrefixStore(store, self.MEDIASTORE_PREFIX)
                    try:
                        prefix.put(object_key, csv_binary)
                    except Exception as e:
                        print(e, flush=True)
                        raise
                self.stdout.write(self.style.SUCCESS(f'Underway Data for {cruise.name} successfully imported.'))
            except Cruise.DoesNotExist:
               raise CommandError(f'Cruise {cruise_name} not found.')
            except Exception as e:
                raise CommandError(f'An error occurred: {str(e)}')
