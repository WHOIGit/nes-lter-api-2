import csv
import os
import glob
import dotenv
from django.core.management.base import BaseCommand, CommandError
from io import BytesIO, StringIO
import pandas as pd
from core.models import Cruise
from core.models import Underway
from storage.fs import FilesystemStore
from storage.mediastore import MediaStore
from storage.utils import PrefixStore
from django.conf import settings

class Command(BaseCommand):
    help = 'Import in Underway Data files for a given Cruise.'

    dotenv.load_dotenv()
    URL = os.getenv("URL")
    TOKEN = os.getenv("TOKEN")

    FILE_SUFFIX = '_underway.csv'

    def add_arguments(self, parser):
        parser.add_argument('cruise_name', type=str, help='Name of the cruise.')

    def handle(self, *args, **options):
        cruise_name = options['cruise_name']
        
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
                prefix = PrefixStore(store, settings.MEDIASTORE_PREFIX)
                try:
                    prefix.put(object_key, csv_binary)
                except Exception as e:
                    print(e, flush=True)
                    raise
            self.stdout.write(self.style.SUCCESS(f'Underway Data successfully imported.'))
        except Cruise.DoesNotExist:
           raise CommandError(f'Cruise {cruise_name} not found.')
        except Exception as e:
            raise CommandError(f'An error occurred: {str(e)}')
