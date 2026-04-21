import os
import io
import glob
import pandas as pd
from pathlib import Path
import numpy as np
import logging
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import Point
from core.models import Cruise, Station
from core.utils import get_store, read_sample_log, read_nut_data

NUT_SUFFIX = '_nut.csv'
BTLSUM_SUFFIX = '_ctd_bottle_summary.csv'
BTLDATA_SUFFIX = '_ctd_bottles.csv'

NEAREST_STATION_COL = 'nearest_station'
DISTANCE_KM_COL = 'distance_km'
DATE_COL = 'date'
LATITUDE_COL = 'latitude'
LONGITUDE_COL = 'longitude'

class Command(BaseCommand):
    help = 'Import Nutrient Data. If Cruise Name is not supplied, all Nut files for all Cruises will be created.'

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger('management')

    def add_arguments(self, parser):
        parser.add_argument('--cruise_name', type=str, help='Optional name of the cruise.', default=None)


    def read_btl_summary(self, cruise, sample_ids):

        object_key = f"{cruise}{BTLSUM_SUFFIX}"
        with get_store() as store:
            try:
                data = store.get(object_key)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Run ImportNiskin.py to create bottle summary file for cruise {cruise}.'))
                self.logger.error((f'Run ImportNiskin.py to create bottle summary file for cruise {cruise}.'))
                return pd.DataFrame()

            btl_sum = pd.read_csv(io.BytesIO(data))
            btl_sum.cast = btl_sum.cast.astype(str).str.lstrip("0")  #remove leading 0s for merge
            sample_ids.cast = sample_ids.cast.astype(str)
            btl_sum.niskin = btl_sum.niskin.astype(int)
            sample_ids.niskin = sample_ids.niskin.astype(int)
            # include sample_ids cast rows when cast missing from btl_sum
            merged = btl_sum.merge(sample_ids, on=['cruise','cast','niskin'], how='right')

            return merged

    def read_bottle_data(self, cruise, nut_profile):

        JP_STUDENT_CRUISES = ['ar22', 'ar32', 'ar38']

        object_key = f"{cruise}{BTLDATA_SUFFIX}"
        with get_store() as store:
            try:
                data = store.get(object_key)
            except Exception as e:
                print(e, flush=True)
                print("Run ImportNiskin.py to import bottle file.", flush=True)
                self.logger.error("Run ImportNiskin.py to import bottle file.")
                return nut_profile.head(0)

        bottles = pd.read_csv(io.BytesIO(data))
        bottles.cast = bottles.cast.astype(str).str.lstrip("0")
        nut_profile = nut_profile.merge(
            bottles[['cruise', 'cast', 'niskin', 't090c', 't190c', 'sal00', 'sal11']], 
            on=['cruise', 'cast', 'niskin'], 
            how='right'
        )
        
        # drop rows (picked up in btl_sum.merge right) with casts that were not in btl_sum
        nut_profile.dropna(subset=['date'], inplace=True) # and lat, lon, depth = nan
        if cruise.lower() in JP_STUDENT_CRUISES:
            nut_profile['project_id'] = 'JP'
        else:
            nut_profile['project_id'] = np.where(nut_profile['alternate_sample_id'].isna(), 'LTER', 'OOI')

        return nut_profile

    def apply_flags(self, df):

        # Flagging scheme based on IODE flag
        # 1 = good
        # 2 = not reviewed
        # 3 = questionable
        # 4 = bad (always throw out)

        # Detection Limit diff for each nutrient
        # nitrate_nitrite = 0.04
        # ammonium = 0.015
        # phosphate = 0.009
        # silicate = 0.030

        # Set all OOI ammonium flags to 2, all other OOI flags to 2

        DL_dict = {
            'nitrate_nitrite': 0.04,
            'ammonium': 0.01,
            'phosphate': 0.009,
            'silicate': 0.03
        }
        flag_dict = {
            'nitrate_nitrite': 'flag_nitrate_nitrite',
            'ammonium': 'flag_ammonium',
            'phosphate': 'flag_phosphate',
            'silicate': 'flag_silicate'
        }

        diff_dict = {
            'nitrate_nitrite': 8.5,
            'ammonium': 99,         # 99 represents no processing
            'phosphate': 99,
            'silicate': 99
        }

        # First step of flagging
        df['time'] = pd.to_datetime(df['date'], format='%Y-%m-%d %H:%M:%S')
        df['time_numeric'] = df['time'].map(lambda x: x.toordinal() + x.hour / 24 + x.minute / 1440 + x.second / 86400)

        # Adjust values below detection limits
        for param, DL in DL_dict.items():
            df[param] = pd.to_numeric(df[param], errors='coerce')  #ar61b
            df[param] = df[param].clip(lower=DL)

        # Add flag columns with default values
        for param in DL_dict.keys():
            df[flag_dict[param]] = 1

        # Calculate and apply ratios/differences
        for idx, row in df.iterrows():
            close_rows = df[
                (np.abs((df['time'] - row['time']).dt.total_seconds()) < 60) &
                (np.abs(df['depth'] - row['depth']) < 3) &
                (df.index != idx) &
                (row['project_id'] != 'OOI') &
                (df['project_id'] != 'OOI')
            ]
            for param in DL_dict.keys():
                if not close_rows.empty:
                    mean_value = (close_rows[param].mean() + row[param]) / 2
                    ratio = 100 * (row[param] - mean_value) / mean_value
                    if len(close_rows) >= 2: 
                        # Compare sample value against mean of the other rows
                        if abs(close_rows[param].mean() - row[param]) > diff_dict[param]:
                            df.at[idx, flag_dict[param]] = 4
                        else:
                            # Apply different thresholds for ammonium
                            if param == "ammonium":
                                if abs(ratio) > 50:
                                    df.at[idx, flag_dict[param]] = 4
                                elif abs(ratio) > 20:
                                    df.at[idx, flag_dict[param]] = 3
                            else:
                                #if param == "silicate":
                                    #print(len(close_rows), mean_value, flush=True)
                                    #print(ratio,row, flush=True)
                                if abs(ratio) > 40:
                                    df.at[idx, flag_dict[param]] = 4
                                elif abs(ratio) > 15:
                                    df.at[idx, flag_dict[param]] = 3
                    else:
                        # Apply different thresholds for ammonium
                        if param == "ammonium":
                            if abs(ratio) > 50:
                                df.at[idx, flag_dict[param]] = 4
                            elif abs(ratio) > 20:
                                df.at[idx, flag_dict[param]] = 3
                        else:
                            if abs(ratio) > 40:
                                df.at[idx, flag_dict[param]] = 4
                            elif abs(ratio) > 15:
                                df.at[idx, flag_dict[param]] = 3
                else:
                    # set single row value to not reviewed
                    if (param == 'ammonium') & (df.at[idx, 'project_id'] == 'OOI'):
                        df.at[idx, flag_dict[param]] = 2
                    else:
                        df.at[idx, flag_dict[param]] = 2

        # 1st step of lter nut flagging doesn't work well for low concentrations. 
        # this 2nd step changes flag=4(bad) to flag=3(caution) to be more lenient. 
        # next step is manual inspection of all flagged data
        # do not want to be too lenient and change flags to 1(good) because good will not be manually inspected

        # 2nd step = if both replicates are less than DetectionLimit * 10, then change from bad to caution
        # Detection Limit (DL) is nutrient specific

        # Refine flags for low concentrations
        for param, DL in DL_dict.items():
            flag_col = flag_dict[param]
            for idx, row in df.iterrows():
                if row[flag_col] == 4:
                    close_rows = df[
                        (np.abs(df['time_numeric'] - row['time_numeric']) < 1 / (24 * 60)) &
                        (np.abs(df['depth'] - row['depth']) < 3) 
                    ]
                    if len(close_rows) > 1 and (close_rows[param] < DL * 10).sum() > 1 and row[param] < DL * 10:
                        df.at[idx, flag_col] = 3

        # Drop helper columns
        df.drop(columns=['time', 'time_numeric'], inplace=True)

        return df

    def handle(self, *args, **options):

        cruise_name = options['cruise_name']
        if cruise_name is None:
            parent_dir = Path('/vast/raw/')
            cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
        else:
            cruises = [cruise_name]

        # read and parse the LTER sample log
        sample_ids = read_sample_log()
        
        for cruise_name in cruises:
            try:
                Cruise.objects.get(name__iexact=cruise_name)
                cruise_name = cruise_name.lower()

                # read and merge bottle summary
                merged = self.read_btl_summary(cruise_name, sample_ids)

                if not merged.empty:

                    # filter for just this cruise
                    filtered = merged[merged["cruise"] == cruise_name.upper()]

                    # read and merge nutrient data
                    nut_profile = read_nut_data(cruise_name, filtered)
                   
                    # read and merge temperature and salinity from bottle data
                    nut_profile = self.read_bottle_data(cruise_name, nut_profile)
                   
                    if not nut_profile.empty and cruise_name != 'ar78':
                        # calculate and apply quality flags
                        nut_profile = self.apply_flags(nut_profile)

                        # add nearest station
                        nut_profile[NEAREST_STATION_COL] = None
                        nut_profile[DISTANCE_KM_COL] = None

                        for idx, row in nut_profile.iterrows():
                            geolocation = Point(row[LONGITUDE_COL], row[LATITUDE_COL], srid=4326)
                            station_location = Station.nearest_location(
                                latitude= geolocation.y,
                                longitude=geolocation.x,
                                timestamp=row[DATE_COL]
                            )
                            if station_location:
                                nut_profile.at[idx, NEAREST_STATION_COL] = station_location.content_object.name
                                nut_profile.at[idx, DISTANCE_KM_COL] = round(station_location.distance.km, 3)

                        # write nut file to media store
                        csv_buffer = io.StringIO()
                        nut_profile.to_csv(csv_buffer, index=False, na_rep="NaN")
                        csv_binary = csv_buffer.getvalue().encode("utf-8")

                        object_key = f"{cruise_name}{NUT_SUFFIX}"
                        with get_store() as store:
                            try:
                                store.put(object_key, csv_binary)
                                self.stdout.write(self.style.SUCCESS(f'{cruise_name}{NUT_SUFFIX} successfully created.'))
                                self.logger.error((f'{cruise_name}{NUT_SUFFIX} successfully created.'))
                            except Exception as e:
                                print(e, flush=True)
                                self.logger.error(f'An error occurred: {str(e)}')
                                raise

                        self.stdout.write(self.style.SUCCESS(f'Nut files successfully imported.'))
                        self.logger.error((f'Nut files successfully imported.'))
                    else:
                        self.stdout.write(self.style.WARNING(f'No nutrient data found for cruise {cruise_name}.'))
                        self.logger.warning(f'No nutrient data found for cruise {cruise_name}.')
            except Cruise.DoesNotExist:
                    self.logger.error(f'Cruise not found {cruise_name}. Run importcruise.py')
                    raise CommandError(f'Cruise not found {cruise_name}. Run importcruise.py')
            except Exception as e:
                self.logger.error(f'An error occurred: {str(e)}')
                raise CommandError(f'An error occurred: {str(e)}')
