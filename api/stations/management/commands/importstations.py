import os
import io
import pandas as pd
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.models import Station, StationLocation
from core.utils import get_store
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
        self.logger = logging.getLogger('management')

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
                with get_store() as store:
                    try:
                        store.put(object_key, csv_binary)
                        self.stdout.write(self.style.SUCCESS(f"{STATION_FILENAME} successfully created."))
                        self.logger.error((f"{STATION_FILENAME} successfully created."))
                    except Exception as e:
                        print(e, flush=True)
                        self.logger.error(f'An error occurred: {str(e)}')
                        raise

                self.stdout.write(self.style.SUCCESS(f'Stations successfully imported.'))
                self.logger.error((f'Stations successfully imported.'))
            except Exception as e:
                self.logger.error(f'An error occurred: {str(e)}')
                raise CommandError(f'An error occurred: {str(e)}')
