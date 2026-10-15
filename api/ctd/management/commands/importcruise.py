import os
import glob
import re
from django.core.management.base import BaseCommand, CommandError
import pandas as pd
from core.models import Cruise, Vessel, Underway
from core.utils import get_store
from core.models import Vessel
from pathlib import Path
import logging
from io import BytesIO

class Command(BaseCommand):
    help = 'Create Cruise Model. If Cruise Name is not supplied, all Cruises will be created.'

    UNDERWAY_SPEED_COLUMN = {
        "ar": "spd",
        "hrs": "sog_kts",
        "ae": "sog_kts",
        "en": "gps_furuno_smg",
        "at": "spd",
    }

    logger = logging.getLogger('management')

    def add_arguments(self, parser):
        parser.add_argument('--cruise_name', type=str, help='Optional name of the cruise.', default=None)

    def load_cruise_types(self):
        file = f'/vast/raw/all/metadata/NES-LTER_cruise_types.csv'
        df = pd.read_csv(file)

        valid_types = set(Cruise.CruiseType.values)
        cruise_types = {}

        for _, row in df.iterrows():
            cruise = str(row["Cruise"]).strip().lower()
            cruise_type = str(row["Cruise Type"]).strip()

            # skip bad rows so one typo doesn't discard the rest of the file
            if pd.isna(row["Cruise"]) or not cruise:
                msg = f'Skipping cruise types row with no cruise name: {row.to_dict()}'
            elif cruise_type not in valid_types:
                msg = f"Skipping invalid cruise type '{cruise_type}' for cruise '{cruise}'"
            else:
                cruise_types[cruise] = cruise_type
                continue
            self.stdout.write(self.style.WARNING(msg))
            self.logger.error(msg)
        return cruise_types

    def parse_elog(self, file_pattern):
        matching_files = glob.glob(file_pattern)
        if matching_files:
            file_path = matching_files[0]
            try:
                df = pd.read_csv(file_path, encoding="latin1")
            except:
                df = pd.read_excel(file_path)   # additions and corrections files
            try:
                start_time = df.loc[df["Action"].str.contains("startCruise"), "dateTime8601"].iloc[0]
            except:
                start_time = None
            try:
                end_time = df.loc[df["Action"].str.contains("endCruise"), "dateTime8601"].iloc[0]
            except:
                end_time = None
            return start_time, end_time
        return None, None


    def get_underway_start(self, vessel_code, csv_buffer):
        speed_col = self.UNDERWAY_SPEED_COLUMN[vessel_code.lower()]
        # Return the first underway record where speed > 2.
        #Assumes the CSV is already sorted by ascending time.

        df = pd.read_csv(
            csv_buffer,
            usecols=["date", speed_col],
            low_memory=False,
        )

        df[speed_col] = pd.to_numeric(df[speed_col], errors="coerce")

        underway = df[df[speed_col] > 2] 

        if underway.empty:
            return None

        return underway.iloc[0]["date"]

    def get_underway_end(self, vessel_code, csv_buffer):
        speed_col = self.UNDERWAY_SPEED_COLUMN[vessel_code.lower()]
        # Return the last underway record where speed > 2.
        #Assumes the CSV is already sorted by ascending time.

        df = pd.read_csv(
            csv_buffer,
            usecols=["date", speed_col],
            low_memory=False,
        )

        df[speed_col] = pd.to_numeric(df[speed_col], errors="coerce")

        underway = df[df[speed_col] > 2]

        if underway.empty:
            return None

        return underway.iloc[-1]["date"]

    def handle(self, *args, **options):
        cruise_name = options['cruise_name']

        try:
            cruise_types = self.load_cruise_types()
        except Exception as e:
            if cruise_name is None:
                # bulk run (cruise_types upload): surface the bad file
                raise CommandError(f'Could not load cruise types: {str(e)}')
            # single-cruise run (ctd/elog/underway upload): don't let a bad or
            # missing cruise types file block it; cruises keep their existing
            # type (or get the default if the cruise is new)
            self.stdout.write(self.style.WARNING(f'Could not load cruise types, keeping existing types: {str(e)}'))
            self.logger.error(f'Could not load cruise types, keeping existing types: {str(e)}')
            cruise_types = None

        if cruise_name is None:
            parent_dir = Path('/vast/raw')
            cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
        else:
            cruises = [cruise_name]
       
        for cruise_name in cruises:
            try:
                vessel = Vessel.objects.get(code__istartswith=cruise_name[:2])
                cruise_name = cruise_name.strip().lower()
                # assign cruise type: the cruise types file applies to every
                # vessel; without a row, keep the cruise's existing type
                existing = Cruise.objects.filter(name=cruise_name).values_list('type', flat=True).first()
                if cruise_types is not None and cruise_name in cruise_types:
                    cruise_type = cruise_types[cruise_name]
                else:
                    if cruise_types is not None and vessel.code == 'ar':
                        # AR cruises are expected to have a row
                        self.stdout.write(self.style.WARNING(f'Cruise {cruise_name} type not defined.'))
                        self.logger.error((f'Cruise {cruise_name} type not defined.'))
                    cruise_type = existing or Cruise.CruiseType.NESLTER
                # get the cruise start and end times from the elog
                directory = f'/vast/corrected/{cruise_name}/elog/'
                file_pattern = os.path.join(directory, '*_elog.csv')
                start_time, end_time = self.parse_elog(file_pattern)
                if start_time is None and end_time is None:
                    directory = f'/vast/raw/{cruise_name}/elog/'
                    file_pattern = os.path.join(directory, 'R2R_ELOG*additions*')
                    start_time, end_time = self.parse_elog(file_pattern)
                    if start_time is None and end_time is None:
                        file_pattern = os.path.join(directory, 'R2R_ELOG*corrections*')
                        start_time, end_time = self.parse_elog(file_pattern)
                        if start_time is None and end_time is None:
                            file_pattern = os.path.join(directory, 'R2R_ELOG*FINAL*')
                            start_time, end_time = self.parse_elog(file_pattern)
                        if start_time is None and end_time is None:
                            self.stdout.write(self.style.SUCCESS(f'Cruise {cruise_name} event log not found.'))
                            self.logger.error((f'Cruise {cruise_name} event log not found.'))

                cruise, created = Cruise.objects.update_or_create(
                    name=cruise_name,
                    defaults={
                       "vessel": vessel,
                       "type": cruise_type,
                       "start_time": start_time,
                       "end_time": end_time,
                    }
                )

                csv_buffer = None
                if start_time is None or end_time is None:
                    if Underway.objects.filter(cruise=cruise).exists():
                        object_key = f"{cruise_name.lower()}{'_underway.csv'}"

                        with get_store() as store:
                            try:
                                data = store.get(object_key)
                            except Exception as e:
                                print(e, flush=True)
                                raise

                        csv_buffer = BytesIO(data)
                
                if csv_buffer is not None:
                    if start_time is None:
                        # Obtain the start time from the underway data speed
                        csv_buffer.seek(0)
                        start_time = self.get_underway_start(vessel.code, csv_buffer)
                        if start_time is None:
                            self.stdout.write(self.style.WARNING(f'Cruise {cruise_name} startCruise datetime could not determined.'))
                            self.logger.error((f'Cruise {cruise_name} startCruise datetime could not be determined.'))
                        else:
                            Cruise.objects.update_or_create(
                                name=cruise_name,
                                defaults={
                                    "vessel": vessel,
                                    "type": cruise_type,
                                    "start_time": start_time,
                                    "end_time": end_time,
                                }
                            )

                    if end_time is None:
                        # Obtain the end time from the underway data speed
                        csv_buffer.seek(0)
                        end_time = self.get_underway_end(vessel.code, csv_buffer)
                        if end_time is None:
                            self.stdout.write(self.style.WARNING(f'Cruise {cruise_name} endCruise datetime could not be determined.'))
                            self.logger.error((f'Cruise {cruise_name} endCruise datetime could not be determined..'))
                        else:
                            Cruise.objects.update_or_create(
                                name=cruise_name,
                                defaults={
                                    "vessel": vessel,
                                    "type": cruise_type,
                                    "start_time": start_time,
                                    "end_time": end_time,
                                }
                            )

                self.stdout.write(self.style.SUCCESS(f'Cruise {cruise_name} successfully imported.'))
                self.logger.error((f'Cruise {cruise_name} successfully imported.'))
            except Vessel.DoesNotExist:
                self.logger.error(f'Vessel not found. Run importvessel.py')
                raise CommandError(f'Vessel not found. Run importvessel.py')
            except Exception as e:
                self.logger.error(f'An error occurred: {str(e)}')
                raise CommandError(f'An error occurred: {str(e)}')
