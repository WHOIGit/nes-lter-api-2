from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from pathlib import Path
import logging

class Command(BaseCommand):
    help = 'Run all import commands in sequence'

    def add_arguments(self, parser):
        parser.add_argument('--cruise_name', type=str, help='Optional name of the cruise.', default=None)

    def handle(self, *args, **options):
        logger = logging.getLogger('management')

        cruise_name = options['cruise_name']

        if cruise_name is None:
            parent_dir = Path('/vast/raw')
            cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
        else:
            cruises = [cruise_name]

        self.stdout.write("Importing vessels...")
        logger.error("Importing vessels...")
        call_command('importvessel')

        self.stdout.write("Importing stations...")
        logger.error("Importing stations...")
        call_command('importstations')
       
        for cruise_name in cruises:
            try:
                self.stdout.write("Importing cruises...")
                logger.error("Importing cruises...")
                call_command('importcruise', cruise_name=cruise_name)

                self.stdout.write("Importing events...")
                logger.error("Importing events...")
                call_command('importevent', cruise_name=cruise_name)

                self.stdout.write("Importing underway data...")
                logger.error("Importing underway data...")
                call_command('importunderwaydata', cruise_name=cruise_name)

                self.stdout.write("Importing casts...")
                logger.error("Importing casts...")
                call_command('importcast', cruise_name=cruise_name)

                self.stdout.write("Importing niskins...")
                logger.error("Importing niskins...")
                call_command('importniskin', cruise_name=cruise_name)

                self.stdout.write("Importing nutrients...")
                logger.error("Importing nutrients...")
                call_command('importnut', cruise_name=cruise_name)

                self.stdout.write("Importing chlorophyll...")
                logger.error("Importing chlorophyll...")
                call_command('importchl', cruise_name=cruise_name)

                self.stdout.write("Importing hplc...")
                logger.error("Importing hplc...")
                call_command('importhplc', cruise_name=cruise_name)

                self.stdout.write("All import commands completed successfully!")
                logger.error("All import commands completed successfully!")

            except Exception as e:
                logger.error(f"Error during import sequence: {e}")
                raise CommandError(f"Error during import sequence: {e}")
