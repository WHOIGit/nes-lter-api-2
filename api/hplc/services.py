import io
import os
from datetime import datetime
from django.http import FileResponse, HttpResponse, Http404
from storage.mediastore import MediaStore
from storage.utils import PrefixStore
from core.models import Cruise, HPLC
from django.conf import settings

class HplcService:

    @classmethod
    def get(cls, cruise_name: str) -> FileResponse:
        URL = os.getenv("URL")
        TOKEN = os.getenv("TOKEN")
        MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")
        FILE_SUFFIX = '_hplc.csv'

        try:
            if cruise_name.lower() != "mvco":
                Cruise.objects.get(name__iexact=cruise_name) 
            object_key = f"{cruise_name.lower()}{FILE_SUFFIX}"
            with MediaStore(URL, token=TOKEN) as store:
                prefix = PrefixStore(store, MEDIASTORE_PREFIX)
                try:
                    data = prefix.get(object_key)
                except Exception as e:
                    print(e, flush=True)
                    raise
            csv_buffer = io.BytesIO(data)
            response = HttpResponse(csv_buffer, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{object_key}"'
            return response
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")    

