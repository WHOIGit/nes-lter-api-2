import os
import io
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.models import Station, StationLocation, Cruise, Cast
from storage.mediastore import MediaStore
from storage.utils import PrefixStore
from django.conf import settings
from django.db import transaction

STATION_FULL_COL = 'stationfullname'
STATION_COL = 'station'
START_DATE_COL = 'startDate'
END_DATE_COL = 'endDate'
LATITUDE_COL = 'decimalLatitude'
LONGITUDE_COL = 'decimalLongitude'
DEPTH_COL = 'depth_m'
COMMENT_COL = 'comment'

STATION_FILENAME = 'stations.csv'

class Command(BaseCommand):
    help = 'Create Station Model.'

    def __init__(self):
        super().__init__()
        self.URL = os.getenv("URL")
        self.TOKEN = os.getenv("TOKEN")
        self.MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")

    def handle(self, *args, **options):

        with transaction.atomic():
            # delete all the objects and repopulate model - set_location doesn't allow update
            Station.objects.all().delete()
            StationLocation.objects.all().delete()

            try:
                df = pd.read_excel("/vast/raw/all/metadata/NES-LTER_station_list_compilation.xlsx")
                # fill in empty fullnames with previous value
                df["stationfullname"] = df["stationfullname"].apply(lambda x: None if x == "" else x).ffill()

                for _, row in df.iterrows():                                

                    station, _  = Station.objects.update_or_create(
                        name=row[STATION_COL],
                        full_name=row[STATION_FULL_COL]
                    )
                
                    if row[END_DATE_COL] == 'current':
                        row[END_DATE_COL] = timezone.now()
                    else:
                        row[END_DATE_COL] = pd.to_datetime(row[END_DATE_COL], errors='coerce')
                        if pd.notna(row[END_DATE_COL]):
                            row[END_DATE_COL] = timezone.make_aware(row[END_DATE_COL], timezone.get_default_timezone())
                    row[START_DATE_COL] = pd.to_datetime(row[START_DATE_COL], errors='coerce')
                    if pd.notna(row[START_DATE_COL]):
                        row[START_DATE_COL] = timezone.make_aware(row[START_DATE_COL], timezone.get_default_timezone())

                    station.set_location(
                        latitude=row[LATITUDE_COL],
                        longitude=row[LONGITUDE_COL],
                        start_time=row[START_DATE_COL],
                        end_time=row[END_DATE_COL],
                        depth=row[DEPTH_COL],
                        comment=row[COMMENT_COL]
                    )

                # write station file to media store
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False, na_rep="NaN")
                csv_binary = csv_buffer.getvalue().encode("utf-8")

                object_key = f'{STATION_FILENAME}'
                with MediaStore(self.URL, token=self.TOKEN) as store:
                    prefix = PrefixStore(store, self.MEDIASTORE_PREFIX)
                    try:
                        prefix.put(object_key, csv_binary)
                        self.stdout.write(self.style.SUCCESS(f'{STATION_FILENAME} successfully created.'))
                    except Exception as e:
                        print(e, flush=True)
                        raise

                # create and write ctd metadata file to media store
                #for cruise in Cruise.objects.all():
                    
                self.stdout.write(self.style.SUCCESS(f'Stations successfully imported.'))
            except Exception as e:
                raise CommandError(f'An error occurred: {str(e)}')
