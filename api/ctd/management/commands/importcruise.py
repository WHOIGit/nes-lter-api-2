import os
import glob
import re
from django.core.management.base import BaseCommand, CommandError
import pandas as pd
from core.models import Cruise
from core.models import Vessel
from pathlib import Path
import logging

class Command(BaseCommand):
    help = 'Create Cruise Model. If Cruise Name is not supplied, all Cruises will be created.'

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

            if cruise_type not in valid_types:
                raise ValueError(
                    f"Invalid cruise type '{cruise_type}' for cruise '{cruise}'"
                )

            cruise_types[cruise] = cruise_type
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

    def handle(self, *args, **options):
        cruise_name = options['cruise_name']

        cruise_types = self.load_cruise_types()

        if cruise_name is None:
            parent_dir = Path('/vast/raw')
            cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
        else:
            cruises = [cruise_name]
       
        for cruise_name in cruises:
            try:
                vessel = Vessel.objects.get(code__istartswith=cruise_name[:2])
                # assign cruise type
                cruise_name = cruise_name.strip().lower()
                if vessel.code == 'ar': 
                    if cruise_name not in cruise_types:
                        self.stdout.write(self.style.WARNING(f'Cruise {cruise_name} type not defined.'))
                        self.logger.error((f'Cruise {cruise_name} type not defined.'))
                        cruise_type = Cruise.CruiseType.NESLTER
                    else:
                        cruise_type = cruise_types.get(cruise_name)
                else:    # en, ae, hrs, at cruises are all NESLTER
                    cruise_type = Cruise.CruiseType.NESLTER
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

                if start_time is None:
                    self.stdout.write(self.style.WARNING(f'Cruise {cruise_name} startCruise event not found.'))
                    self.logger.error((f'Cruise {cruise_name} startCruise event not found.'))
                if end_time is None:
                    self.stdout.write(self.style.WARNING(f'Cruise {cruise_name} stopCruise event not found.'))
                    self.logger.error((f'Cruise {cruise_name} stopCruise event not found.'))

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
