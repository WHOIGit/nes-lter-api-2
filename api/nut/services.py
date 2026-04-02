import io
import os
import csv
import glob
import pandas as pd
from django.http import FileResponse, HttpResponse, Http404
from core.utils import get_store, read_sample_log, read_nut_data
from core.models import Cruise

class NutService:
    URL = os.getenv("URL")
    TOKEN = os.getenv("TOKEN")
    MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")
    FILE_SUFFIX = '_nut.csv'

    @classmethod
    def get(cls, cruise_name: str) -> FileResponse:

        try:
            Cruise.objects.get(name__iexact=cruise_name) 
            object_key = f"{cruise_name.lower()}{cls.FILE_SUFFIX}"
            with get_store(cls.URL, cls.TOKEN, cls.MEDIASTORE_PREFIX) as store:
                try:
                    data = store.get(object_key)
                except Exception as e:
                    print(e, flush=True)
                    raise Http404(f"Nutrient data not found for cruise {cruise_name}")
            csv_buffer = io.BytesIO(data)
            response = HttpResponse(csv_buffer, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{object_key}"'
            return response
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")    

    @classmethod
    def getall(cls) -> FileResponse:
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)

        is_first_cruise = True
        cruises = Cruise.objects.all().order_by('name')

        for cruise in cruises:
            object_key = f"{cruise.name}{cls.FILE_SUFFIX}"
            with get_store(cls.URL, cls.TOKEN, cls.MEDIASTORE_PREFIX) as store:
                try:
                    data = store.get(object_key)
                except Exception as e:
                    continue

            cruise_data = data.decode('utf-8')
            reader = csv.reader(io.StringIO(cruise_data))

            if is_first_cruise:
                # first cruise: write everything including header
                for row in reader:
                    csv_writer.writerow(row)
                is_first_cruise = False
            else:
                # other cruises: skip header
                next(reader, None) 
                for row in reader:
                    csv_writer.writerow(row)

        # Reset the pointer to the start
        csv_buffer.seek(0)
        response = HttpResponse(csv_buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="all_nut.csv"'
        return response


    @classmethod
    def get_readme(cls) -> str:
        path = glob.glob(os.path.join(f'/vast/raw/all/nut/', 'README*'))[0]
        with open(path, 'r') as fin:
            content = fin.read()
        return HttpResponse(content, content_type="text/plain")

    @classmethod
    def ar52_nutrient_samplelog(cls) -> FileResponse:

        # read and parse the LTER sample log
        sample_ids = read_sample_log()

        cruises = {"AR52A", "AR52B"}
        filtered = sample_ids[sample_ids["cruise"].isin(cruises)]

        filtered["date"] = pd.NaT

        # read and merge nutrient data
        nut_profile = read_nut_data("", filtered)

        nut_profile = nut_profile.drop(columns=["date"])
        nut_profile["cast"] = nut_profile["cast"].astype(int)
        nut_profile["niskin"] = nut_profile["niskin"].astype(int)

        nut_profile = nut_profile.sort_values(["cruise", "cast", "niskin"]).reset_index(drop=True)

        # Convert to CSV
        csv_content = nut_profile.to_csv(index=False)

        return HttpResponse(csv_content,content_type="text/csv")