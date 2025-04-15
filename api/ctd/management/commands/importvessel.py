from django.core.management.base import BaseCommand, CommandError
import pandas as pd
from core.models import Vessel

class Command(BaseCommand):
    help = 'Create Vessel Model. Creates all Vessels'

    vessel_data = [
        {"designation": "R/V", "name": "Neil Armstrong", "short_name": "Armstrong", "code": "ar"},
        {"designation": "R/V", "name": "Atlantis", "short_name": "Atlantis", "code": "at"},
        {"designation": "R/V", "name": "Endeavor", "short_name": "Endeavor", "code": "en"},
        {"designation": "R/V", "name": "Sharp", "short_name": "Sharp", "code": "hrs"},
        {"designation": "R/V", "name": "Atlantic Explorer", "short_name": "Explorer", "code": "ae"}
    ]

    vessel_df = pd.DataFrame(vessel_data)

    def handle(self, *args, **options):    

        for _, row in self.vessel_df.iterrows():
            try:
                Vessel.objects.update_or_create(
                    code=row["code"], 
                    defaults={
                        "designation": row["designation"],
                        "name": row["name"],
                        "short_name": row["short_name"],
                        }
                )
                self.stdout.write(self.style.SUCCESS(f'Vessel {row["name"]} successfully created.'))
            except Exception as e:
              raise CommandError(f'An error occurred: {str(e)}')
