import io
import dotenv
import os
from datetime import datetime
from django.http import FileResponse, HttpResponse, Http404
from storage.mediastore import MediaStore
from storage.utils import PrefixStore
from core.models import Cruise
from django.conf import settings
from pathlib import Path

class ChlService:

    dotenv.load_dotenv()
    URL = os.getenv("URL")
    TOKEN = os.getenv("TOKEN")

    @classmethod
    def get(cls, cruise_name: str) -> FileResponse:
        FILE_SUFFIX = '_chl.csv'
        combined = bytearray()
        first = True

        if cruise_name.lower() == 'all':
            parent_dir = Path('/vast/raw/')
            cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
        else:
            cruises = [cruise_name]
      
        for cruise_name in cruises:
            try:
                Cruise.objects.get(name__iexact=cruise_name)
                object_key = f"{cruise_name}{FILE_SUFFIX}"
                with MediaStore(cls.URL, token=cls.TOKEN) as store:
                    prefix = PrefixStore(store, settings.MEDIASTORE_PREFIX)
                    try:
                        data = prefix.get(object_key)
                    except Exception as e:
                        print(e, flush=True)
                        raise

                    lines = data.decode('utf-8').splitlines(keepends=True)
                    if not lines:
                        continue
                    if first:
                        combined.extend("".join(lines).encode('utf-8'))
                        first = False
                    else:
                        # Skip the header (line 0)
                        combined.extend("".join(lines[1:]).encode('utf-8'))
                        print(combined, flush=True)
            except Cruise.DoesNotExist:
                raise Http404(f"Cruise {cruise_name} not found.")
            
        csv_buffer = io.BytesIO(combined)
        response = HttpResponse(csv_buffer, content_type='text/csv')
        if len(cruises) > 1:
            object_key = f"all{FILE_SUFFIX}"
        response['Content-Disposition'] = f'attachment; filename="{object_key}"'
        return response
    

