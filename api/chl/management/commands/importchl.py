import os
import io
import glob
import pandas as pd
import re
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from core.models import Cruise
from storage.mediastore import MediaStore
from storage.utils import PrefixStore
from django.conf import settings
import numpy as np
from core.utils import clean_column_names, float_to_datetime, cast_columns

CHL_SUFFIX = '_chl.csv'
BTLSUM_SUFFIX = '_ctd_bottle_summary.csv'
BTLDATA_SUFFIX = '_ctd_bottles.csv'

NEAREST_STATION_COL = 'nearest_station'
DISTANCE_KM_COL = 'distance_km'
DATE_COL = 'date'
LATITUDE_COL = 'latitude'
LONGITUDE_COL = 'longitude'

class Command(BaseCommand):
    help = 'Import Chlorophyll Data. If Cruise Name is not supplied, all Chl files for all Cruises will be created.'

    def __init__(self):
        super().__init__()
        self.URL = os.getenv("URL")
        self.TOKEN = os.getenv("TOKEN")
        self.MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")

    def add_arguments(self, parser):
        parser.add_argument('--cruise_name', type=str, help='Optional name of the cruise.', default=None)

    def read_btl_summary(self, cruise, chl):

        object_key = f"{cruise}{BTLSUM_SUFFIX}"
        with MediaStore(self.URL, token=self.TOKEN) as store:
            prefix = PrefixStore(store, self.MEDIASTORE_PREFIX)
            try:
                data = prefix.get(object_key)
            except Exception as e:
                print(e, flush=True)
                print("Run ImportCast.py & ImportNiskin.py to import bottle summary file.", flush=True)
                return pd.DataFrame()

            btl_sum = pd.read_csv(io.BytesIO(data))
            chl.cruise = chl.cruise.str.lower()
            chl.cast = chl.cast.astype(str)
            chl.niskin = chl.niskin.astype(int)
            btl_sum.cast = btl_sum.cast.astype(str).str.lstrip("0")  #remove leading 0s for merge
            btl_sum.niskin = btl_sum.niskin.astype(int)

            chl = chl.merge(btl_sum, on=['cruise','cast','niskin'], how='left')
            chl = chl.dropna(subset=['cruise'])
            chl.sort_values('date')
            return chl

    def read_chl_data(self):

        cols = ['cruise','cast','niskin','replicate','vol_filtered','filter_size',
                'tau_calibration','fd_calibration',
                'rb','ra','blank','rb_blank','ra_blank',
                'chl','phaeo','quality_flag']

        file = f'/vast/raw/all/chl/NESLTERchl.xlsx'
        df = pd.read_excel(file, dtype={'Cast #': str})

        # check for regression
        # assert set(raw.columns) == set(RAW_COLS), 'chl spreadsheet does not contain expected columns'
        # clean and rename columns
        df = clean_column_names(df, {
            'Vol\nFilt': 'vol_filtered', # remove abbreviation
            'Chl (ug/l)': 'chl', # remove unit
            'Phaeo (ug/l)': 'phaeo', # remove unit
            '90% Acetone': 'ninety_percent_acetone' # remove leading digit
        })

        cols2delete = set()
        for c in df.columns:
            if c.startswith('unnamed_'):
                cols2delete.add(c)
        for c in cols2delete:
            df.pop(c)
        # cast the int columns
        df = df.astype({ 'filter_size': int })
        # convert floats like 20180905.0 to dates
        df['date'] = float_to_datetime(df['date'])
        df['cal_date'] = float_to_datetime(df['cal_date'])
        # cast all string columns
        str_cols = ['cast', 'niskin', 'sample']
        df = cast_columns(df, str, str_cols, fillna='')
        # deal with missing values in cast/niskin
        df['cast'] = df['cast'].str.replace(' +','',regex=True)
        df['cast'] = df['cast'].replace('',np.nan)
        df['niskin'] = df['niskin'].str.replace('nan','',regex=True)
        df['niskin'] = df['niskin'].replace('',np.nan)
        df = df.dropna(subset=['cast','niskin'])
        # deal with niskin numbers like 4/5/6 by picking first one
        df['niskin'] = df['niskin'].str.replace(r'/.*','',regex=True).astype(int)
        df['cast'] = df['cast'].astype(int)
        # deal with 'freeze' in time_in and time_out columns
        # add freeze column
        freeze = df['time_in'].astype(str).str.lower() == 'freeze'
        df['freeze'] = freeze
        # now parse time in and time out date cols
        for c in ['time_in', 'time_out']:
            df.loc[freeze, c] = np.nan
            # deal with whitespace-only time columns
            regex = re.compile(r'^ +$')
            df[c] = pd.to_datetime(df[c].astype(str).str.replace(regex,'',regex=True))
        df.filter_size = df.filter_size.astype(str)
        def fms_replace(value, replacement):
            df.filter_size = df.filter_size.replace(value, replacement)
        fms_replace('0','>0') # whole seawater
        fms_replace('10','<10') # we know < a priori
        fms_replace('5','>5') # we know > a priori
        fms_replace('20','>20') # we know > a priori

        return df[cols]

    def handle(self, *args, **options):

        cruise_name = options['cruise_name']
        if cruise_name is None:
            parent_dir = Path('/vast/raw/')
            cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
        else:
            cruises = [cruise_name]

        # read and parse chlorophyll data
        chl_data = self.read_chl_data()
        
        for cruise_name in cruises:
            try:
                Cruise.objects.get(name__iexact=cruise_name)
                cruise_name = cruise_name.lower()

                chl_cruise = chl_data[chl_data['cruise'] == cruise_name.upper()].copy()

                # read and merge bottle summary
                merged = self.read_btl_summary(cruise_name, chl_cruise)

                # write chl file to media store
                csv_buffer = io.StringIO()
                merged.to_csv(csv_buffer, index=False, na_rep="NaN")
                csv_binary = csv_buffer.getvalue().encode("utf-8")

                object_key = f"{cruise_name}{CHL_SUFFIX}"
                with MediaStore(self.URL, token=self.TOKEN) as store:
                    prefix = PrefixStore(store, self.MEDIASTORE_PREFIX)
                    try:
                        prefix.put(object_key, csv_binary)
                        self.stdout.write(self.style.SUCCESS(f'{cruise_name}{CHL_SUFFIX} successfully created.'))
                    except Exception as e:
                        print(e, flush=True)
                        raise

                self.stdout.write(self.style.SUCCESS(f'Chl files successfully imported.'))
            except Cruise.DoesNotExist:
                    raise CommandError(f'Cruise not found {cruise_name}. Run importcruise.py')
            except Exception as e:
                raise CommandError(f'An error occurred: {str(e)}')
