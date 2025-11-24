import os
import glob
import io
import logging
from django.core.management.base import BaseCommand, CommandError
import pandas as pd
from core.models import Cruise
from core.models import Event
from core.utils import get_store
from django.contrib.gis.geos import Point
from collections import Counter, defaultdict

DATETIME = 'dateTime8601'
MESSAGE_ID = 'Message ID'
R2R_EVENT = 'R2R_Event'
FILE_SUFFIX = '_elog.csv'

INSTRUMENT_MAPPING = {
    "Attune": "Attune Flow Cytometer",
    "Attune Flow Cytomoeter": "Attune Flow Cytometer",
    "Bongo": "Bongo Net",
    "Cytomeoter": "Cytometer",
    "EK80": "EK80 broadband",
    "IFCB_continuous": "IFCB continuous",
    "IFCB Continuous": "IFCB continuous",
    "IFCB 109": "IFCB continuous",
    "IFCB": "IFCB continuous",
    "Incubation": "Incubation Grazing",
    "Incubation O2": "Incubation Respiration O2",
    "Issacs Kidd Midwater Trawl": "Isaacs-Kidd Midwater Trawl",
    "Midwater Trawl": "RMT10 Midwater Trawl (Tucker-style)",
    "RMT8 Midwater Trawl": "RMT10 Midwater Trawl (Tucker-style)",
    "RingNet": "Ring Net",
    "RingNetIFCB Continuous": "IFCB continuous",
    "SSW": "Underway Science seawater diaphragm pump",
    "Stingray": "Sting Ray",
    "SUNA V2": "SUNAV2",
    "Thermosalinograph SBE45": "Thermosalinographs on underway impeller ",
    "Transmissometer 10": "Transmissometer 10cm",
    "trans10": "Transmissometer 10cm",    
    "trans25": "Transmissometer 25cm",        
    "Underway diaphram pump": "Underway Science seawater diaphragm pump",
    "Underway Impeller": "Underway Science seawater impeller",
    "Underway Science seawater impeller pump": "Underway Science seawater impeller",
    "Underway Science Seawater Diaphragm Pump": "Underway Science seawater diaphragm pump",
    "Valeport Modus SVS": "Valeport SVS"
}


class Command(BaseCommand):
    help = 'Import in Events for a given Cruise. If Cruise is not supplied, all Events for all Cruises will be imported.'

    def __init__(self):
        super().__init__()
        self.URL = os.getenv("URL")
        self.TOKEN = os.getenv("TOKEN")
        self.MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")
        self.logger = logging.getLogger('management')

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
        with get_store(self.URL, self.TOKEN, self.MEDIASTORE_PREFIX) as store:
            try:
                store.put(object_key, csv_binary)
            except Exception as e:
                print(e, flush=True)
                self.logger.error(f'An error occurred: {str(e)}')
                raise

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
               if matching_file and cruise_name.lower() not in ['en608', 'en617', 'en627']:  # serve the original elogs for these cruises
                   file_path = matching_file[0]
                   df = pd.read_csv(file_path, parse_dates=[DATETIME], dtype={'Station': str, 'Cast': str})
                   try:
                       df[DATETIME] = pd.to_datetime(df[DATETIME]).dt.tz_convert('UTC')
                   except:
                       df[DATETIME] = pd.to_datetime(df[DATETIME]).dt.tz_localize('UTC')   # en617
               else:
                   directory = f'/vast/raw/{cruise_name}/elog/'
                   file_pattern = os.path.join(directory, 'R2R_ELOG*FINAL*')  # do not read corrections or additions files in elog dir
                   matching_file = glob.glob(file_pattern)
                   if matching_file:
                       file_path = matching_file[0]
                       df = pd.read_csv(file_path, encoding='latin1',parse_dates=[DATETIME], dtype={'Station': str, 'Cast': str})

               if not df.empty:
                   # track seen events for each cruise 
                   seen_events: dict[int, set[str]] = defaultdict(set)

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

                       message_id = int(row[MESSAGE_ID]) if pd.notna(row[MESSAGE_ID]) else None  # Nan is a float
                       
                       event, created = Event.objects.update_or_create(
                               cruise=cruise,
                               r2r_event=row[R2R_EVENT],
                               defaults={
                                   "message_id": message_id,
                                   "instrument":instrument,
                                   "action":row['Action'],
                                   "station":row['Station'],
                                   "cast":row['Cast'],
                                   "comment":row['Comment'],
                                   "geolocation":geolocation,
                                   "datetime":row[DATETIME],
                                   }
                               )

                       seen_events[cruise.id].add(row[R2R_EVENT])

                       csv_data.append({
                           R2R_EVENT: event.r2r_event,
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

                   # delete events from model not in the current elog files
                   for cruise_id, keep_events in seen_events.items():
                       qs = Event.objects.filter(cruise_id=cruise_id).exclude(r2r_event__in=keep_events).delete()
                       if qs[0] > 0:
                           self.stdout.write(self.style.WARNING(f'Deleted {qs[0]} events for cruise id {cruise_id} not present in elog files.'))
                       
                   # duplicate r2r_events not stored in the model
                   r2r_counts = Counter(row[R2R_EVENT] for row in csv_data)
                   duplicates = [r for r, c in r2r_counts.items() if c > 1]
                   if duplicates:
                       self.stdout.write(self.style.WARNING(f'Duplicates found: {duplicates}'))
                       self.logger.error((f'Duplicates found: {duplicates}'))

                   self.store_csv_file(cruise_name, csv_data)

                   self.stdout.write(self.style.SUCCESS(f'Events for {cruise_name} have been successfully imported.'))
                   self.logger.error((f'Events for {cruise_name} have been successfully imported.'))
            except Cruise.DoesNotExist:
                self.logger.error(f'Cruise {cruise_name} not found.')
                raise CommandError(f'Cruise {cruise_name} not found.')
            except Exception as e:
                self.logger.error(f'An error occurred: {str(e)}')
                raise CommandError(f'An error occurred: {str(e)}')
