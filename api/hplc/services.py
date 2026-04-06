import io
import os
import glob
from django.http import FileResponse, HttpResponse, Http404
from core.utils import get_store
from core.models import Cruise
from django.conf import settings

class HplcService:

    @classmethod
    def get(cls, cruise_name: str) -> FileResponse:
        FILE_SUFFIX = '_hplc.csv'

        try:
            if cruise_name.lower() != "mvco":
                Cruise.objects.get(name__iexact=cruise_name) 
            object_key = f"{cruise_name.lower()}{FILE_SUFFIX}"
            with get_store() as store:
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
    def get_readme(cls) -> str:
        path = glob.glob(os.path.join(f'/vast/raw/all/hplc/', 'README*'))[0]
        with open(path, 'r') as fin:
            content = fin.read()
        return HttpResponse(content, content_type="text/plain")

