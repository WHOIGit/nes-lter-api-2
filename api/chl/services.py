import io
import os
import csv
from django.http import FileResponse, HttpResponse, Http404
from core.utils import get_store
from core.models import Cruise

class ChlService:
    URL = os.getenv("URL")
    TOKEN = os.getenv("TOKEN")
    MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")
    FILE_SUFFIX = '_chl.csv'

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
                    raise
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
        response['Content-Disposition'] = f'attachment; filename="all_chl.csv"'
        return response
