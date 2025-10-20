import os
import io
import glob
import pandas as pd
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import Point
from core.models import Cruise, HPLC, Station
from core.utils import get_store
import numpy as np

HPLC_SUFFIX = '_hplc.csv'

NEAREST_STATION_COL = 'nearest_station'
DISTANCE_KM_COL = 'distance_km'
DATE_COL = 'date'
LATITUDE_COL = 'latitude'
LONGITUDE_COL = 'longitude'
CRUISE_COL = 'cruise'

class Command(BaseCommand):
    help = 'Import HPLC Data. If Cruise Name is not supplied, all HPLC files for all Cruises will be created.'

    def __init__(self):
        super().__init__()
        self.URL = os.getenv("URL")
        self.TOKEN = os.getenv("TOKEN")
        self.MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")

    def add_arguments(self, parser):
        parser.add_argument('--cruise_name', type=str, help='Optional name of the cruise.', default=None)

    def read_hplc_files(self):
        dfs = []
        directory = f'/vast/raw/all/hplc'
        hplc_files = sorted(glob.glob(os.path.join(directory, '*Sosik*report.xlsx')))

        for file in hplc_files:
            if file.endswith("Sosik_13-07_report.xlsx") and not file.endswith("Fixed_Sosik_13-07_report.xlsx"):
                continue

            Y = 'Year'
            M = 'Month'
            D = 'Day of Gregorian Month'
            T = 'GMT Time'

            report = pd.read_excel(file, skiprows=8, dtype={
                Y: str,
                M: str,
                D: str,
                T: str
            })
            # report file contains invalid time fields, ie 6:40:00 AM, instead of 06:40
            # minutes must be padded with a leading zero before passed to pd.to_datetime
            report[T] = report[T].str.split(':', n=2).str[:2].str.join(':')
            report[T] = report[T].str.zfill(5)
            dates = report[M] + ' ' + report[D] + ' ' + report[Y] + ' ' + report[T]
            
            if "13-07" in os.path.basename(file):
                report['other.1'] = ''
        
            report[DATE_COL] = pd.to_datetime(dates, utc=True)

            mappings = HPLC.get_mappings()
            report.columns = [mappings.get(c, c) for c in report.columns]

            # produce replicate column
            report.sort_values(['cruise','cast','niskin'], inplace=True)

            R = report.pop('R')
            is_a = (R == 'S') | ((R == 'D') & (R.shift(-1) == 'D'))

            report['replicate'] = np.where(is_a, 'a', 'b')

            # add project_id
            report['project_id'] = 'NESLTER'

            # reorder columns
            report = report[HPLC.get_columns()]

            # consolidate the comments columns
            report['comments'] = report['comments'].fillna('')
            report['comments2'] = report['comments2'].fillna('')
            report['comments3'] = report['comments3'].fillna('')
            report['comments'] = report.pop('comments') + ' ' \
                + report.pop('comments2') + ' ' + report.pop('comments3')
            report['comments'] = report['comments'].str.strip()

            dfs.append(report)
        return(dfs)

    def handle(self, *args, **options):

        dfs = self.read_hplc_files()
        dfs = pd.concat(dfs, sort=False)
        dfs_hplc = dfs.replace(-8888,0)

        cruise_name = options['cruise_name']
        if cruise_name is None:
            parent_dir = Path('/vast/raw/')
            cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
            cruises.append("mvco")
        else:
            cruises = [cruise_name]
        
        for cruise_name in cruises:
            try:
                if cruise_name.lower() != "mvco":
                    Cruise.objects.get(name__iexact=cruise_name)           
                cruise_hplc = dfs_hplc[dfs_hplc[CRUISE_COL].str.lower() == cruise_name].copy()           
                cruise_hplc[NEAREST_STATION_COL] = None
                cruise_hplc[DISTANCE_KM_COL] = None

                for idx, row in cruise_hplc.iterrows():
                    geolocation = Point(row[LONGITUDE_COL], row[LATITUDE_COL], srid=4326)
                    station_location = Station.nearest_location(
                        latitude= geolocation.y,
                        longitude=geolocation.x,
                        timestamp=row[DATE_COL]
                    )
                    if station_location:
                        cruise_hplc.at[idx, NEAREST_STATION_COL] = station_location.content_object.name
                        cruise_hplc.at[idx, DISTANCE_KM_COL] = round(station_location.distance.km, 3)
                
                # write hplc file to media store
                csv_buffer = io.StringIO()
                cruise_hplc.to_csv(csv_buffer, index=False, na_rep="NaN")
                csv_binary = csv_buffer.getvalue().encode("utf-8")

                object_key = f"{cruise_name}{HPLC_SUFFIX}"
                with get_store(self.URL, self.TOKEN, self.MEDIASTORE_PREFIX) as store:
                    try:
                        store.put(object_key, csv_binary)
                        self.stdout.write(self.style.SUCCESS(f'{cruise_name}{HPLC_SUFFIX} successfully created.'))
                    except Exception as e:
                        print(e, flush=True)
                        raise

                self.stdout.write(self.style.SUCCESS(f'HPLC files successfully imported.'))
            except Cruise.DoesNotExist:
                    raise CommandError(f'Cruise not found {cruise_name}. Run importcruise.py')
            except Exception as e:
                raise CommandError(f'An error occurred: {str(e)}')
