import csv
import os
import glob
import dotenv
from django.core.management.base import BaseCommand, CommandError
from io import BytesIO, StringIO
import pandas as pd
from core.models import Cruise
from core.models import Vessel
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'Create Cruise Model. If Cruise Name is not supplied, all Cruises will be created.'

    dotenv.load_dotenv()
    URL = os.getenv("URL")
    TOKEN = os.getenv("TOKEN")

    def add_arguments(self, parser):
        parser.add_argument('--cruise_name', type=str, help='Optional name of the cruise.', default=None)

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

        if cruise_name is None:
            parent_dir = Path('/vast/raw')
            cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
        else:
            cruises = [cruise_name]
       
        for cruise_name in cruises:
            try:
                vessel = Vessel.objects.get(code__istartswith=cruise_name[:2])
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

                if start_time is None:
                    self.stdout.write(self.style.WARNING(f'Cruise {cruise_name} startCruise event not found.'))
                if end_time is None:
                    self.stdout.write(self.style.WARNING(f'Cruise {cruise_name} stopCruise event not found.'))

                Cruise.objects.update_or_create(
                    name=cruise_name,
                    vessel=vessel,
                    defaults={
                        "start_time": start_time,  
                        "end_time": end_time
                    }
                )

                self.stdout.write(self.style.SUCCESS(f'Cruise {cruise_name} successfully imported.'))
            except Vessel.DoesNotExist:
                raise CommandError(f'Vessel not found. Run importvessel.py')
            except Exception as e:
                raise CommandError(f'An error occurred: {str(e)}')
