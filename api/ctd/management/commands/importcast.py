import os
import io
import glob
import re
import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand, CommandError
from core.models import Cruise, Cast, Station
from core.utils import get_store
from pathlib import Path
from django.contrib.gis.geos import Point
import logging
from collections import defaultdict

from core.utils import path_to_cast, parse_lat_lon, parse_time, clean_column_names

CRUISE_COL = 'cruise'
CAST_COL = 'cast'
DATE_COL = 'date'
METADATA_SUFFIX = '_ctd_metadata.csv'

COLUMNS = ["cruise", "cast", "date", "latitude", "longitude", "nearest_station", "distance_km"]

class Command(BaseCommand):
    help = 'Create Cast Model and Cast files. If Cruise Name is not supplied, all Casts for all Cruises will be created.'

    def __init__(self):
        super().__init__()
        self.URL = os.getenv("URL")
        self.TOKEN = os.getenv("TOKEN")
        self.MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")
        self.logger = logging.getLogger('management')

    def add_arguments(self, parser):
        parser.add_argument('--cruise_name', type=str, help='Optional name of the cruise.', default=None)

    def parse_asc_fixed_width(self, asc_path):
        # do some hacking to determine width of columns
        # first, read the file without the header to determine how many columns.
        # we can't do this from the header because in fixed-width files the
        # column names might not have any whitespace between them.
        # if this is the case for data values, this whole approach will fail
        df = pd.read_fwf(asc_path, skiprows=1, nrows=1, header=None, encoding='latin-1')
        n_cols = len(df.columns)  
        # now get the length of the first line which contains headers
        with open(asc_path, encoding='latin-1') as fin:
            for line in fin.readlines():
                break
        # assume all columns are the same width. determine that width
        line = line.rstrip()
        col_width = int(len(line) / n_cols)
        col_widths = [col_width for _ in range(n_cols)]
        # now parse the fixed-width format
        # Pandas will automatically append ".1" to any duplicate column name
        df = pd.read_fwf(asc_path, widths=col_widths, encoding='latin-1')
        return df
    
    def create_cast_file(self, file, cruise, cast, time):
        delimiter = ';'
        base_dir = os.path.dirname(file.name)
        base_name = os.path.splitext(os.path.basename(file.name))[0]

        # Look for matching .asc file (case-sensitive)
        ascfile = None
        for f in os.listdir(base_dir):
            if f.lower() == f"{base_name.lower()}.asc":
                ascfile = os.path.join(base_dir, f)
                break

        if not ascfile:
            self.stdout.write(self.style.ERROR(f'No .asc file found for cruise {cruise} cast {cast}.'))
            self.logger.error((f'No .asc file found for cruise {cruise} cast {cast}.'))
            return
        
        #read .asc file
        try:
            df = pd.read_csv(ascfile, encoding='latin-1', delimiter=delimiter)
            if len(df.columns) == 1: # whoops, try a different delimiter
                if delimiter == ',':
                    delimiter = ';'
                elif delimiter == ';':
                    delimiter = ','
                df = pd.read_csv(ascfile, encoding='latin-1', delimiter=delimiter)
            if len(df.columns) == 1: # try fixed-width
                df = self.parse_asc_fixed_width(ascfile)
            df = clean_column_names(df)

            df[CRUISE_COL] = cruise.upper()
            df[CAST_COL] = cast
            # move to front
            cols = df.columns.tolist()
            cols = cols[-2:] + cols[:-2]
            df = df[cols]
            if 'times' in df.columns:
                timestamp = pd.to_datetime(time) + pd.to_timedelta(df['times'], unit='s')
                df[DATE_COL] = timestamp

            # write cast csv file to media store
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, na_rep="NaN")
            csv_binary = csv_buffer.getvalue().encode("utf-8")

            object_key = f"{cruise}{"_ctd_cast_"}{cast}{".csv"}"
            with get_store(self.URL, self.TOKEN, self.MEDIASTORE_PREFIX) as store:
                try:
                    store.put(object_key, csv_binary)
                except Exception as e:
                    print(e, flush=True)
                    self.logger.error(f'Exception {e}')
                    raise  
        except pd.errors.ParserError as e:
            self.stdout.write(self.style.ERROR(f"{ascfile} not parsable."))
            self.logger.error((f"{ascfile} not parsable."))

    def handle(self, *args, **options):
        #self.stdout = options.get('stdout', sys.stdout) # removes /n's
        cruise_name = options['cruise_name']

        if cruise_name is None:
            parent_dir = Path('/vast/raw')
            cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
        else:
            cruises = [cruise_name]

        self.stdout.write(self.style.SUCCESS(f'For each .hdr file, look for a matching .asc file.'))
        self.logger.error((f'For each .hdr file, look for a matching .asc file.'))

        for cruise_name in cruises:
            try:
                cruise = Cruise.objects.get(name__iexact=cruise_name)
                directory = f'/vast/raw/{cruise_name}/ctd/'
                hdr_files = sorted(glob.glob(os.path.join(directory, '*.hdr')))
                if cruise_name.lower() == "en627":
                    added_dir = os.path.join(directory, "cast_1_files_used_for_corrected_cast_2")
                    hdr_files += sorted(glob.glob(os.path.join(added_dir, '*.hdr')))

                # track seen casts for each cruise 
                seen_casts: dict[int, set[int]] = defaultdict(set)

                for file in hdr_files:
                    filename = os.path.basename(file).lower()
                    if cruise_name == 'ar24a':
                        cruise_pattern = re.escape(cruise_name[:-1])  
                    else:
                        cruise_pattern = re.escape(cruise_name)

                    cast = path_to_cast(cruise_pattern, filename)
                    if cruise_name.lower() == "en627" and cast == "001":
                        cast = "002"
                    if cast is not None:
                        cast = cast.lstrip('0')

                        # get lat, lon and time from .hdr file
                        with open(file, 'r', encoding='utf-8', errors='ignore') as file:
                            content = file.read()

                        latitude, longitude = parse_lat_lon(content)
                        start_time = parse_time(content)
                        
                        if latitude != None and longitude != None and start_time != None:
                            Cast.objects.update_or_create(
                                cruise=cruise,
                                number=cast,
                                depth= 0,     # nominal depth is entered by user
                                geolocation = Point(float(longitude), float(latitude), srid=4326),
                                defaults={
                                    "start_time": start_time,  
                                    "end_time": None
                                }
                            )

                            seen_casts[cruise.id].add(cast)
                        else:
                            print(f"Cast {cast} for {cruise.name} has null lat, lon, start_time. Will not be saved in the model!")
                            self.logger.error(f"Cast {cast} for {cruise.name} has null lat, lon, start_time. Will not be saved in the model!")
                     
                        # create individual cast file
                        self.create_cast_file(file, cruise_name, cast, start_time)

                if glob.glob(os.path.join(directory, "*.hdr")):
                    self.stdout.write(self.style.SUCCESS(f'Casts for Cruise {cruise_name} successfully imported.'))
                    self.logger.error((f'Casts for Cruise {cruise_name} successfully imported.'))
                else:
                    self.stdout.write(self.style.ERROR(f'No Casts found for Cruise {cruise_name}.'))
                    self.logger.error((f'No Casts found for Cruise {cruise_name}.'))

                # delete casts from model not in the current files
                for cruise_id, keep_numbers in seen_casts.items():
                    qs = Cast.objects.filter(cruise_id=cruise_id).exclude(number__in=keep_numbers).delete()
                    if qs[0] > 0:
                        self.stdout.write(self.style.WARNING(f'Deleted {qs[0]} casts for cruise id {cruise_id} not present in current hdr files.'))

                data = []
                for cast in Cast.objects.filter(cruise=cruise):
                    station_location = Station.nearest_location(
                        latitude= cast.geolocation.y,
                        longitude=cast.geolocation.x,
                        timestamp=cast.start_time)

                    data.append({
                        "cruise": cruise.name.upper(),
                        "cast": cast.number,
                        "date": cast.start_time,
                        "latitude": cast.geolocation.y,
                        "longitude": cast.geolocation.x,
                        "nearest_station": station_location.content_object.name,
                        "distance_km": station_location.distance.km
                    })
                df = pd.DataFrame(data, columns=COLUMNS)
                # sort by cast number 
                s = df["cast"].astype(str).str.strip().str.lower()
                num = pd.to_numeric(s.str.extract(r"^(\d+)")[0], errors="coerce").fillna(10**9).to_numpy()
                suf = s.str.extract(r"([a-z]+)$", expand=False).fillna("").to_numpy()
                order = np.lexsort((suf, num))   # primary: num, tie-break: suf
                df = df.iloc[order]

                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False, na_rep="NaN")
                csv_binary = csv_buffer.getvalue().encode("utf-8")

                object_key = f"{cruise.name}{METADATA_SUFFIX}"
                with get_store(self.URL, self.TOKEN, self.MEDIASTORE_PREFIX) as store:
                    try:
                        store.put(object_key, csv_binary)
                    except Exception as e:
                        print(e, flush=True)
                        self.logger.error(f'Exception {e}')
                        raise

            except Cruise.DoesNotExist:
                self.logger.error(f'Cruise not found {cruise_name}. Run importcruise.py')
                raise CommandError(f'Cruise not found {cruise_name}. Run importcruise.py')
            except Exception as e:
                self.logger.error(f'An error occurred: {str(e)}')
                raise CommandError(f'An error occurred: {str(e)}')
