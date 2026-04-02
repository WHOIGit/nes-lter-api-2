import csv
import os
import json

import io
from io import StringIO
from io import BytesIO
from datetime import datetime, time, timedelta, timezone as dt_tz
from django.http import JsonResponse
from django.http import HttpResponse

from pydantic import BaseModel
from django.db.models import Q
import pandas as pd

from core.models import Cruise
from core.models import Underway

from django.http import FileResponse, Http404
from ninja.errors import HttpError

from core.utils import get_store, find_readme

AR_COLUMN_DEF = [
    ("DATE", "GMT date time", "YYYY-MM-DD HH:MM:SS.SSS"),
    ("Dec_LAT", "Decimal Latitude", ""),
    ("Dec_LON", "Decimal Longitude", ""),
    ("SPD", "Ship Speed", ""),
    ("HDT", "Heading - Gyro", "degrees"),
    ("COG", "Course Over Ground - from GPS", "degrees"),
    ("DPS_COG", "Course Over Ground - from GPS", "degrees"),
    ("CNAV_COG", "Course Over Ground - from GPS", "degrees"),
    ("SOG", "Speed Over Ground - from GPS", ""),
    ("WXTP_Ta", "Port Vaisala air temp", "degrees C"),
    ("WXTS_Ta", "Starboard Vaisala air temp", "degrees C"),
    ("WXTP_Pa", "Port Vaisala air pressure", "hPa"),
    ("WXTS_Pa", "Starboard Vaisala air pressure", "hPa"),
    ("WXTP_Ri", "Port Vaisala rain intensity", "mm/h"),
    ("WXTS_Ri", "Starboard Vaisala rain intensity", "mm/h"),
    ("WXTP_Rc", "Port Vaisala rain accumulation", "mm"),
    ("WXTS_Rc", "Starboard Vaisala rain accumulation", "mm"),
    ("WXTP_Dm", "Port Vaisala relative wind direction average", "degrees"),
    ("WXTS_Dm", "Starboard Vaisala relative wind direction average", "degrees"),
    ("WXTP_Sm", "Port Vaisala relative wind speed average", "m/s"),
    ("WXTS_Sm", "Starboard Vaisala relative wind speed average", "m/s"),
    ("WXTP_Ua", "Port Vaisala relative humidity", "percent"),
    ("WXTS_Ua", "Starboard Vaisala relative humidity", "percent"),
    ("WXTP_TS", "Port Vaisala True Wind Speed", "m/s"),
    ("WXTS_TS", "Starboard Vaisala True Wind Speed", "m/s"),
    ("WXTP_TD", "Port Vaisala True Wind Direction", "degrees"),
    ("WXTS_TD", "Starboard Vaisala True Wind Direction", "degrees"),
    ("RAD_SW", "Shortwave Radiation", "watts/square meter"),
    ("RAD_LW", "Longwave Radiation flux", "watts/square meter"),
    ("PAR", "Photosynthetically active radiation", "uE/m2/sec"),
    ("SBE45S", "Sea surface salinity (5m)", "psu"),
    ("SBE48T", "Sea surface temperature (5m)", "degrees C"),
    ("AML_SST", "temperature", "degress celsius ITS-90"),
    ("EST_NITRATE", "", ""),
    ("EST_PHOSPHATE", "", ""),
    ("BAROM_P", "Port Barometric pressure", "hPa"),
    ("BAROM_S", "Starboard Barometric pressure", "hPa"),
    ("FLR", "Fluorometer", "millivolts"),
    ("FLOW", "flow", "ml/s"),
    ("TRANS25_REF", "CSTAR 25 CM Transmissometer reference", ""),
    ("TRANS25_SIG", "CSTAR 25 CM Transmissometer signal", ""),
    ("TRANS25_SIGCOR", "CSTAR 25 CM Transmissometer signal corrected", ""),
    ("TRANS25_CALC", "CSTAR 25 CM Transmissometer calculated beam c", ""),
    ("TRANS25_THERM", "CSTAR 25 CM Transmissometer m-1 and thermistor", ""),
    ("TRANS10_REF", "CSTAR 10 CM Transmissometer reference", ""),
    ("TRANS10_SIG", "CSTAR 10 CM Transmissometer signal", ""),
    ("TRANS10_SIGCOR", "CSTAR 10 CM Transmissometer signal corrected", ""),
    ("TRANS10_CALC", "CSTAR 10 CM Transmissometer calculated beam c", ""),
    ("TRANS10_THERM", "CSTAR 10 CM Transmissometer m-1 and thermistor", ""),
    ("SSV", "Sea surface sound velocity", "m/s"),
    ("SSVDSLOG", "Sea surface sound velocity", "m/s"),
    ("Depth12", "12kHz water depth", "m"),
    ("Depth35", "3.5kHz water depth", "m"),
    ("EM122", "12kHz multibeam centre depth", "m"),
    ("EM124", "12kHz multibeam centre depth", "m"),
    ("EM710", "12kHz multibeam centre depth", "m"),
    ("EM712", "12kHz multibeam centre depth", "m")
]

HR_COLUMN_DEF = [
    ("DATE", "GMT date time", "YYYY-MM-DD HH:MM:SS.SSS"),
    ("Latitude_Deg", "GPS Lat Decimal Degrees", ""),
    ("Longitude_Deg", "GPS Long Dec Degrees", ""),
    ("COG_Deg", "GPS Course Over Ground", "degrees"),
    ("SOG_Knots", "GPS Speed Over Ground", "knots" ),
    ("COG_deg.1", "POSmv Course Over Ground", "degrees"),
    ("SOG_kts", "POSmv Speed Over Ground", "knots"),
    ("Depth_Meters", "Depth in Meters", "m"),
    ("Relative_Wind_Speed_1_Knots", "Relative Wind Speed #1", "knots"),
    ("Relative_Wind_Direction_1_Deg", "Relative Wind Direction #1", "degrees"),
    ("Relative_Wind_Speed_2_Knots", "Relative Wind Speed #2", "knots"),
    ("Relative_Wind_Direction_2_Deg", "Relative Wind Direction #2", "degrees"),
    ("True_Wind_Speed__Knots","True Wind Speed", "knots"),
    ("True_Wind_Direction_Deg", "True Wind Direction", "degrees"),
    ("Air_Temperature_C", "Air Temperature", "c"),
    ("Humidity_", "Humidity", "%"),
    ("Barometer_Decibars", "Pressure", "decibars"),
    ("Water_Temperature_Degree_C", "Surface Water Temp", "degree c"),
    ("Salinity_Psu", "Surface Water Salinity", "psu"),
    ("Fluorometer_Turner_Raw", "Fluorometer", "turner raw"),
    ("Keel_Depth_Meters", "Keel Depth", "m"),
    ("Science_Log_Text", "Comment", ""),
    ("Qsr_S_N_10367", "CSTAR 25 CM Transmissometer reference", "")
]

AE_COLUMN_DEF = [
    ("File", "", ""),
    ("Call_Sign", "", "Sign"),
    ("YMD", "", ""),
    ("HMS", "", ""),
    ("Latitude", "", ""),
    ("Longitude", "", ""),
    ("GPS_HDT_deg", "", "deg"),
    ("COG_deg", "", "deg"),
    ("SOG_kts", "", "kts"),
    ("RMY_AirTemp_C", "", "C"),
    ("AirTemp_C", "", "C"),
    ("BP_Corr_mBar", "", "mBar"),
    ("RMY_BP_mBar", "", "mBar"),
    ("RMY_RH_percent", "", "percent"),
    ("RH_Percent", "", "Percent"),
    ("RMY_PriWD_deg", "", "deg"),
    ("RMY_SecWD_deg", "", "deg"),
    ("Gill_WD_deg", "", "deg"),
    ("RMY_PriWS_kts", "", "kts"),
    ("RMY_SecWS_kts", "", "kts"),
    ("Gill_WS_kts", "", "kts"),
    ("TWindDirPri_deg", "", "deg"),
    ("TWindDirSec_deg", "", "deg"),
    ("TWindDirTer_deg", "", "deg"),
    ("TWindSpdPri_kts", "", "kts"),
    ("TWindSpdSec_kts", "", "kts"),
    ("TWindSpdTer_kts", "", "kts"),
    ("Flow1_L_min", "", "min"),
    ("Flow_Flag", "", "Flag"),
    ("PriCHL_ug_l", "", "l"),
    ("SecCHL_ug_l", "", "l"),
    ("SBE38_RemoteTemp_C", "", "C"),
    ("SBE38Sec_RemoteTemp_C", "", "C"),
    ("SBE45Pri_Temp_C", "", "C"),
    ("SBE45Sec_Temp_C", "", "C"),
    ("SBE45Pri_Cond_S_m", "", "m"),
    ("SBE45Sec_Cond_S_m", "", "m"),
    ("SBE45Pri_Sal_PSU", "", "PSU"),
    ("SBE45Sec_Sal_PSU", "", "PSU"),
    ("PriLightTrans_percentage", "", "percentage"),
    ("SecLightTrans_percentage", "", "percentage"),
    ("PAR_uE_m2Sec", "", "m2Sec"),
    ("SPP_W_m2", "", "m2"),
    ("PIR_Corr_W_m2", "", "m2"),
    ("PrecipRaw_mm", "", "mm"),
]

class UnderwayOutput(BaseModel):
    file_name: str

class UnderwayService:
    FILE_SUFFIX = '_underway.csv'
    HEADER_SUFFIX = '_underway_column_def.csv'
    
    @classmethod
    def get_data(cls, cruise_name: str) -> FileResponse:
        URL = os.getenv("URL")
        TOKEN = os.getenv("TOKEN")
        MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            if Underway.objects.filter(cruise=cruise).exists():
                object_key = f"{cruise_name.lower()}{cls.FILE_SUFFIX}"
                with get_store(URL, TOKEN, MEDIASTORE_PREFIX) as store:
                   try:
                       data = store.get(object_key)
                   except Exception as e:
                       print(e, flush=True)
                       raise
                csv_buffer = BytesIO(data)
                response = HttpResponse(csv_buffer, content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="{object_key}"'
                return response
            else:
                raise Http404(f"Underway data not imported. Import using manage.py importunderwaydata")    
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")   
       
    @classmethod
    def get_column_headers(cls, cruise_name: str) -> JsonResponse:
        URL = os.getenv("URL")
        TOKEN = os.getenv("TOKEN")
        MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            if Underway.objects.filter(cruise=cruise).exists(): 
                object_key = f"{cruise_name.lower()}{cls.FILE_SUFFIX}"
                with get_store(URL, TOKEN, MEDIASTORE_PREFIX) as store:
                    try:
                        data = store.get(object_key)
                    except Exception as e:
                        print(e, flush=True)
                        raise
                csv_buffer = BytesIO(data)
                df = pd.read_csv(csv_buffer)
                columns = df.columns.tolist()
                response = {
                    "metadata": {
                        "columns": columns,
                        "num_columns": len(columns),
                    },
                    "data": None
                }    
                return JsonResponse(response, safe=False)
            else:
               raise Http404(f"Underway data not imported.")    
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")   

    @classmethod
    def find_underway_files(cls, start_timestamp: str, end_timestamp: str) -> list[UnderwayOutput]:
        try:
            start_date = datetime.strptime(start_timestamp, "%Y-%m-%d")
            end_date = datetime.strptime(end_timestamp, "%Y-%m-%d")
        except ValueError:
            raise HttpError(400, "Invalid date format. Use yyyy-mm-dd")

        # datetime format yyyy-mm-dd hh:mm:ss
        if end_date < start_date:
            raise HttpError(500, f"end_timestamp must be greater than or equal to start_timestamp")

        UTC = dt_tz.utc
        start_dt = datetime.combine(start_date, time.min, tzinfo=UTC)
        end_dt = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC)

        underway_objects = Underway.objects.filter(
            Q(start_datetime__lte=end_dt) & Q(end_datetime__gte=start_dt)
        )

        responses = []
        for underway in underway_objects:
            object_key = f"{underway.cruise.name}{cls.FILE_SUFFIX}"
            responses.append(UnderwayOutput(file_name=object_key))
        if not responses:
            raise Http404(f"Underway data files not found between start timestamp {start_timestamp} and {end_timestamp}.")   
        else:
            return responses

    @classmethod
    def get_readme(cls, cruise_name: str) -> str:
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            path = find_readme(cruise_name, 'underway')
            with open(path, 'r') as fin:
                content = fin.read()
            return HttpResponse(content, content_type="text/plain")
        except Cruise.DoesNotExist:
            raise Http404(f"Cruise {cruise_name} not found.")

    @classmethod
    def get_column_data(cls, cruise_name):
        header_response = cls.get_column_headers(cruise_name)

        # Extract JSON data from JsonResponse
        payload = json.loads(header_response.content)
        actual_columns = [col.upper() for col in payload["metadata"]["columns"]]

        if cruise_name.lower().startswith(("ar", "at")):
            expected_columns = [col[0].upper() for col in AR_COLUMN_DEF]
        elif cruise_name.lower().startswith("hr"):
            expected_columns = [col[0].upper() for col in HR_COLUMN_DEF]  
        else:
            expected_columns = [col[0].upper() for col in AE_COLUMN_DEF]

        extra_columns = [col for col in actual_columns if col not in expected_columns]
        #print(extra_columns, flush=True)  # for debugging

        # Select expected columns for the cruise 
        common_columns = [col for col in expected_columns if col in actual_columns]

        if cruise_name.lower().startswith(("ar", "at")):
            rows = [
                (name, desc, units)
                for name, desc, units in AR_COLUMN_DEF
                if name.strip().upper() in common_columns
            ]
        elif cruise_name.lower().startswith("hr"):
            rows = [
                (name, desc, units)
                for name, desc, units in HR_COLUMN_DEF
                if name.strip().upper() in common_columns
            ]
        else:
            rows = [
                (name, desc, units)
                for name, desc, units in AE_COLUMN_DEF
                if name.strip().upper() in common_columns
            ]
        return rows

    @classmethod
    def get_column_definition_csv(cls, cruise_name: str) -> FileResponse:
        URL = os.getenv("URL")
        TOKEN = os.getenv("TOKEN")
        MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            if Underway.objects.filter(cruise=cruise).exists():
                cruise_name = cruise_name.lower()
                if cruise_name.startswith(("ar", "at", "hrs", "ae")):

                    rows = cls.get_column_data(cruise_name)

                    buffer = StringIO()
                    writer = csv.writer(buffer)
                    writer.writerow(["Name", "Description", "Units"])
                    writer.writerows(rows)
                    buffer.seek(0)

                    response = HttpResponse(buffer, content_type="text/csv")
                    response["Content-Disposition"] = f'attachment; filename="{cruise_name}_underway_column_definition.csv"'
                    return response
                elif cruise_name.lower().startswith("en"):
                    object_key = f"{cruise_name.lower()}{cls.HEADER_SUFFIX}"
                    with get_store(URL, TOKEN, MEDIASTORE_PREFIX) as store:
                       try:
                           data = store.get(object_key)
                       except Exception as e:
                           print(e, flush=True)
                           raise
                    csv_buffer = BytesIO(data)
                    response = HttpResponse(csv_buffer, content_type='text/csv')
                    response['Content-Disposition'] = f'attachment; filename="{object_key}"'
                    return response
                else:
                    raise Http404(f"Column definitions not available for {cruise_name}.")   
            else:
                raise Http404(f"Underway data not imported. Import using manage.py importunderwaydata")    
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")

    @classmethod
    def get_column_definition(cls, cruise_name: str) -> JsonResponse:
        URL = os.getenv("URL")
        TOKEN = os.getenv("TOKEN")
        MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")
        try:
            cruise = Cruise.objects.get(name__iexact=cruise_name)
            if Underway.objects.filter(cruise=cruise).exists():
                cruise_name = cruise_name.lower()
                if cruise_name.startswith(("ar", "at", "hrs", "ae")):

                    rows = cls.get_column_data(cruise_name)
                    data = [
                            {"name": name, "description": desc, "units": units}
                            for name, desc, units in rows
                        ]
                    return JsonResponse(data, safe=False)

                elif cruise_name.lower().startswith("en"):
                    object_key = f"{cruise_name.lower()}{cls.HEADER_SUFFIX}"
                    with get_store(URL, TOKEN, MEDIASTORE_PREFIX) as store:
                       try:
                           data = store.get(object_key)
                       except Exception as e:
                           print(e, flush=True)
                           raise

                    text = data.decode("utf-8")
                    reader = csv.DictReader(io.StringIO(text))
                    rows = list(reader)
                    return JsonResponse(rows, safe=False)
                else:
                    raise Http404(f"Column definitions not available for {cruise_name}.")   
            else:
                raise Http404(f"Underway data not imported. Import using manage.py importunderwaydata")    
        except Cruise.DoesNotExist:
           raise Http404(f"Cruise {cruise_name} not found.")  