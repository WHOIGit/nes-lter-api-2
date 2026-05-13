import os
import glob
import logging
from django.core.management.base import BaseCommand, CommandError
from io import BytesIO, StringIO
import pandas as pd
from core.models import Cruise
from core.models import Underway
from core.utils import clean_column_names, get_store, date_time_to_datetime
from pathlib import Path
from django.utils import timezone
from django.utils.dateparse import parse_datetime

class Command(BaseCommand):
    help = 'Import in Underway Data files for a given Cruise. If Cruise is not supplied, all Cruises will be imported.'

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('management')

    FILE_SUFFIX = '_underway.csv'
    HEADER_SUFFIX = '_underway_column_def.csv'
    DATETIME = 'date'

    def add_arguments(self, parser):
        parser.add_argument('--cruise_name', type=str, help='Optional name of the cruise.', default=None)

    def make_aware_if_naive(self, dt):
        if dt is not None and dt.tzinfo is None:
            return timezone.make_aware(dt)
        return dt

    def read_comment_block(self, file_path):
        in_block = False
        kept_lines = []

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.rstrip("\n")

                if line.startswith("#COLUMNDEFINITIONSTART#"):
                    in_block = True
                    continue

                if in_block and line.startswith("#COLUMNDEFINITIONEND#"):
                    break

                if in_block:
                    # Strip leading '#' but preserve tabs
                    if line.startswith("#"):
                        line = line[1:]
                    kept_lines.append(line)

        # Nothing found → return empty DataFrame
        if not kept_lines:
            return pd.DataFrame()

        text = "\n".join(kept_lines)

        df = pd.read_csv(
            StringIO(text),
            sep=",",
            engine="python",
            dtype=str,
            keep_default_na=False,
        )

        # Clean column names
        #df.columns = [c.strip() for c in df.columns]

        return df

    def handle(self, *args, **options):
        cruise_name = options['cruise_name']
        
        underway_metadata = {
           'ar': {'read_csv_args': {'skiprows': 1}, 'date_format': '%Y/%m/%d', 'time_column': ' TIME_GMT'},
           'at': {'read_csv_args': {'skiprows': 1}, 'date_format': '%Y/%m/%d', 'time_column': ' TIME_GMT'},
           'en': {'read_csv_args': {'comment': '#'}, 'date_format': None, 'time_column': None},
           'hrs': {'read_csv_args': {'header': [0]}, 'date_format': '%Y-%m-%d %H:%M:%S%z', 'time_column': None},
           'ae': {'read_csv_args': {'header': [0]}, 'date_format': '%Y%m%d', 'time_column': 'HMS'}
        }

        if cruise_name is None:
            parent_dir = Path('/vast/raw')
            cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
        else:
            cruises = [cruise_name]

        for cruise_name in cruises:
            try:
                cruise = Cruise.objects.get(name__iexact=cruise_name)
                directory = f'/vast/raw/{cruise_name}/underway/'
                file_pattern = os.path.join(directory, '*')
                files = glob.glob(file_pattern)
                underway_files = [
                    f for f in files
                    if os.path.isfile(f) and "README" not in os.path.basename(f)
                ]
                if not underway_files:
                    self.stdout.write(self.style.WARNING(f'Cruise {cruise_name} underway data not found.'))
                    self.logger.warning(f'Cruise {cruise_name} underway data not found.')
                    return

                # Concatenate the CSV files
                cruise_prefix = next((key for key in underway_metadata if cruise.name.startswith(key)), None)
                if cruise_prefix:
                    metadata = underway_metadata[cruise_prefix]
                    definition_df = None
                    data_frames = []
                    for file in underway_files:
                        # read in the column definitions for endeavor cruises
                        if cruise_prefix == "en" and definition_df is None:
                            definition_df = self.read_comment_block(file)

                        # read in underway data for all cruises
                        df = pd.read_csv(file, **metadata['read_csv_args'])
                        data_frames.append(df)

                    combined_data = pd.concat(data_frames, ignore_index=True)

                    if cruise_prefix in ('ar', 'at'):
                        combined_data.insert(0, self.DATETIME, date_time_to_datetime(combined_data.pop('DATE_GMT'), combined_data.pop(' TIME_GMT')))
                        combined_data.index = combined_data[self.DATETIME]
                    elif cruise_prefix in ('ae'):
                        ymd = pd.to_datetime(combined_data['YMD'], format=metadata['date_format'])
                        hms_padded = combined_data[metadata['time_column']].apply(lambda x: f"{x:06}")
                        hms = hms_padded.str[:2] + ':' + hms_padded.str[2:4] + ':' + hms_padded.str[4:6]
                        combined_data = combined_data.drop(columns=['YMD', 'HMS'])
                        combined_data.insert(0, self.DATETIME, date_time_to_datetime(ymd.dt.strftime('%Y-%m-%d'), hms))
                        combined_data.index = combined_data[self.DATETIME]
                    elif cruise_prefix in ('en'):
                        combined_data = combined_data.rename(columns={"DateTime_ISO8601": "date"})
                        combined_data[self.DATETIME] = pd.to_datetime(combined_data[self.DATETIME], utc=True, errors="coerce")
                    else:
                        if metadata['time_column']:
                            combined_data['datetime'] = pd.to_datetime(
                                combined_data[self.DATETIME].astype(str).str.strip() + ' ' +
                                combined_data[metadata['time_column']].astype(str).str.zfill(6),
                                format=f"{metadata['date_format']} %H%M%S",
                                errors='coerce'
                            )
                        else:
                            combined_data['datetime'] = pd.to_datetime(
                                combined_data[self.DATETIME])

                        combined_data = combined_data.sort_values(
                            by='datetime',
                            ascending=True,
                            ignore_index=True
                        )
                        combined_data = combined_data.drop(columns=['datetime'])
                    
                    # Select only numeric columns and fill NaN values with 'NaN'
                    combined_data[combined_data.select_dtypes(include=['number']).columns] = combined_data.select_dtypes(include=['number']).fillna('NaN')
                    if 'QSR - S/N 10367' in combined_data.columns:    #hrs2303
                        combined_data['QSR - S/N 10367'] = combined_data['QSR - S/N 10367'].fillna('NaN')

                    date_format = metadata['date_format']
                    if date_format:
                        start_datetime = pd.to_datetime(combined_data[self.DATETIME].min(), format=date_format)
                        end_datetime = pd.to_datetime(combined_data[self.DATETIME].max(), format=date_format)
                    else:
                        start_datetime = pd.to_datetime(combined_data[self.DATETIME].min())
                        end_datetime = pd.to_datetime(combined_data[self.DATETIME].max())

                    df_data = clean_column_names(combined_data)

                else:
                    self.logger.error(f"Unsupported cruise type for cruise_name: {cruise_name}")
                    raise ValueError(f"Unsupported cruise type for cruise_name: {cruise_name}")

                start_datetime = None if pd.isna(start_datetime) else self.make_aware_if_naive(start_datetime)
                end_datetime = None if pd.isna(end_datetime) else self.make_aware_if_naive(end_datetime)                

                Underway.objects.update_or_create(
                        cruise=cruise,
                        start_datetime=start_datetime,
                        end_datetime=end_datetime,
                        )       
                
                # Store the Underway data in the vast media store
                csv_buffer = StringIO()
                df_data.to_csv(csv_buffer, index=False)
                csv_binary = csv_buffer.getvalue().encode('utf-8')
                object_key = f"{cruise_name}{self.FILE_SUFFIX}"
                with get_store() as store:
                    try:
                        store.put(object_key, csv_binary)
                    except Exception as e:
                        print(e, flush=True)
                        self.logger.error(f'An error occurred: {str(e)}')
                        raise
 
                # Store the Underway column definition in the vast media store
                if definition_df is not None:
                    csv_buffer = StringIO()
                    definition_df.to_csv(csv_buffer, index=False)
                    csv_binary = csv_buffer.getvalue().encode('utf-8')
                    object_key = f"{cruise_name}{self.HEADER_SUFFIX}"
                    with get_store() as store:
                        try:
                            store.put(object_key, csv_binary)
                        except Exception as e:
                            print(e, flush=True)
                            self.logger.error(f'An error occurred: {str(e)}')
                            raise
                self.stdout.write(self.style.SUCCESS(f'Underway Data for {cruise.name} successfully imported.'))
                self.logger.error((f'Underway Data for {cruise.name} successfully imported.'))
            except Cruise.DoesNotExist:
               self.logger.error(f'Cruise {cruise_name} not found.')
               raise CommandError(f'Cruise {cruise_name} not found.')
            except Exception as e:
                self.logger.error(f'An error occurred: {str(e)}')
                raise CommandError(f'An error occurred: {str(e)}')
