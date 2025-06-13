import csv
import os
import glob
import io
from django.core.management.base import BaseCommand, CommandError
import pandas as pd
import numpy as np
from core.models import Cruise
from core.models import Event
from storage.fs import FilesystemStore
from storage.mediastore import MediaStore
from storage.utils import PrefixStore
from django.conf import settings
from django.contrib.gis.geos import Point
import pytz
from datetime import datetime

DATETIME = 'dateTime8601'
MESSAGE_ID = 'Message ID'  
FILE_SUFFIX = '_elog.csv'

INSTRUMENT_MAPPING = {
    "Attune": "Attune Flow Cytometer",
    "Bongo": "Bongo Net",
    "Cytomeoter": "Cytometer",
    "EK80": "EK80 broadband",
    "IFCB_continuous": "IFCB continuous",
    "IFCB Continuous": "IFCB continuous",
    "IFCB 109": "IFCB continuous",
    "Incubation": "Incubation Grazing",
    "Incubation O2": "Incubation Respiration O2",
    "RingNet": "Ring Net",
    "RingNetIFCB Continuous": "IFCB continuous",
    "SSW": "Underway Science seawater diaphragm pump",
    "SUNA V2": "SUNAV2",
    "Thermosalinograph SBE45": "Thermosalinographs on underway impeller ",
    "Transmissometer 10": "Transmissometer 10cm",
    "trans10": "Transmissometer 10cm",    
    "trans25": "Transmissometer 25cm",        
    "Underway diaphram pump": "Underway Science seawater diaphragm pump",
    "Underway Impeller": "Underway Science seawater impeller",
    "Underway Science Seawater Diaphragm Pump": "Underway Science seawater diaphragm pump",
}


class Command(BaseCommand):
    help = 'Import in Events for a given Cruise. If Cruise is not supplied, all Events for all Cruises will be imported.'

    def __init__(self):
        super().__init__()
        self.URL = os.getenv("URL")
        self.TOKEN = os.getenv("TOKEN")
        self.MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")

    def add_arguments(self, parser):
        parser.add_argument('--cruise_name', type=str, help='Optional name of the cruise.', default=None)

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
            prefix = PrefixStore(store, self.MEDIASTORE_PREFIX)
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

    def handle(self, *args, **options):
        cruise_name = options['cruise_name']
        
        if cruise_name is None:
            cruises = list(Cruise.objects.values_list('name', flat=True))
        else:
            cruises = [cruise_name]

        for cruise_name in cruises:
            csv_data = []
            df = pd.DataFrame()
            try:
               cruise = Cruise.objects.get(name__iexact=cruise_name)
               directory = f'/vast/corrected/{cruise_name}/elog/'
               file_pattern = os.path.join(directory, '*_elog.csv')
               matching_file = glob.glob(file_pattern)
               if matching_file:
                   file_path = matching_file[0]
                   df = pd.read_csv(file_path, parse_dates=[DATETIME], dtype={'Station': str, 'Cast': str})
                   try:
                       df[DATETIME] = pd.to_datetime(df[DATETIME]).dt.tz_convert('UTC')
                   except:
                       df[DATETIME] = pd.to_datetime(df[DATETIME]).dt.tz_localize('UTC')   # en617
                   df[MESSAGE_ID] = range(1, len(df) + 1)   # assign message ids
               else:
                   directory = f'/vast/raw/{cruise_name}/elog/'
                   file_pattern = os.path.join(directory, 'R2R_ELOG*FINAL*')  # do not read corrections or additions files in elog dir
                   matching_file = glob.glob(file_pattern)
                   if matching_file:
                       file_path = matching_file[0]
                       df = pd.read_csv(file_path, encoding='latin1',parse_dates=[DATETIME], dtype={'Station': str, 'Cast': str})

               if not df.empty:
                   df['Comment'] = df['Comment'].fillna('')

                   for _, row in df.iterrows():
                       longitude = row['Longitude']
                       latitude = row['Latitude']
                       if longitude == "NaN" or latitude == "NaN" or longitude == "NO_GPS" or latitude == "NO_GPS":
                           geolocation = Point(0.0, 0.0, srid=4326)
                       else:
                           geolocation = Point(float(longitude), float(latitude), srid=4326) 
                       
                       # regularize the instrument name
                       raw_instrument = row['Instrument']
                       instrument = INSTRUMENT_MAPPING.get(raw_instrument, raw_instrument)

                       event, created = Event.objects.update_or_create(
                               cruise=cruise,
                               message_id=row[MESSAGE_ID],
                               defaults={
                                   "instrument":instrument,
                                   "action":row['Action'],
                                   "station":row['Station'],
                                   "cast":row['Cast'],
                                   "comment":row['Comment'],
                                   "geolocation":geolocation,
                                   "datetime":row[DATETIME],
                                   }
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

                   self.store_csv_file(cruise_name, csv_data)

                   self.stdout.write(self.style.SUCCESS(f'Events for {cruise_name} have been successfully imported.'))
            except Cruise.DoesNotExist:
                raise CommandError(f'Cruise {cruise_name} not found.')
            except Exception as e:
                raise CommandError(f'An error occurred: {str(e)}')
