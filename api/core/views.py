from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404, FileResponse
import io
import json
import pandas as pd
import re
from django.core.management.base import CommandError
from .models import Cruise, Cast
from core.utils import get_store, _use_dictstore
import matplotlib.pyplot as plt
from io import BytesIO
from pathlib import Path
from django.core.management import call_command
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.db.models.functions import ExtractYear, ExtractMonth, Coalesce

def is_staff(user):
    return user.is_staff

@login_required
@user_passes_test(is_staff)
def file_upload_view(request):
    if request.method == 'POST':

        if _use_dictstore():
            dest_dir_lookup = {
                'ctd': lambda cruise_name: Path(f'/data/raw/{cruise_name}/ctd'),
                'elog': lambda cruise_name: Path(f'/data/raw/{cruise_name}/elog'),
                'underway': lambda cruise_name: Path(f'/data/raw/{cruise_name}/underway'),
                'nutrient': Path('/data/raw/all/nut'),
                'sample_log': Path('/data/raw/all'),
                'station_list' : Path('/data/raw/all/metadata'),
                'cruise_types' : Path('/data/raw/all/metadata'),
                'hplc' : Path('/data/raw/all/hplc'),
                'chlorophyll': Path('/data/raw/all/chl'),
            }
        else:
            dest_dir_lookup = {
                'ctd': lambda cruise_name: Path(f'/vast/raw/{cruise_name}/ctd'),
                'elog': lambda cruise_name: Path(f'/vast/raw/{cruise_name}/elog'),
                'underway': lambda cruise_name: Path(f'/vast/raw/{cruise_name}/underway'),
                'nutrient': Path('/vast/raw/all/nut'),
                'sample_log': Path('/vast/raw/all'),
                'station_list' : Path('/vast/raw/all/metadata'),
                'cruise_types' : Path('/vast/raw/all/metadata'),
                'hplc' : Path('/vast/raw/all/hplc'),
                'chlorophyll': Path('/vast/raw/all/chl'),
            }    

        file_obj = request.FILES['file']
        cruise_name = request.POST.get('cruise_name', '').strip().lower()
        filename = file_obj.name.lower()
        
        file_type = request.POST.get('file_type', '').lower()

        # If cruise name is required but missing
        if file_type in ['ctd', 'elog', 'underway']: 
            if not cruise_name:
                return JsonResponse({'error': f'Cruise name is required for {file_type} files.'}, status=400)
        else:
            cruise_name = None

        # Check if cruise directory exists
        parent_dir = Path('/vast/raw/')
        valid_cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
        
        if file_type in ['ctd', 'elog', 'underway'] and cruise_name not in valid_cruises:
            return JsonResponse({'error': f"Cruise '{cruise_name}' not found in /vast/raw/."}, status=400)

        # determine file destination from type
        if file_type in ['ctd', 'elog', 'underway']:
            destination_dir = dest_dir_lookup[file_type](cruise_name)
        else:
            destination_dir = dest_dir_lookup[file_type]

        upload_path = destination_dir / filename
        # Check if file exists and overwrite is not allowed
        overwrite = request.POST.get('overwrite', 'false').lower() == 'true'
        if upload_path.exists() and not overwrite:
            return JsonResponse({
                'error': (
                   f"The file '{filename}' already exists in {destination_dir}.\n"
                   "Please double check the Cruise Name and selected File Type before continuing."
                ),
                'conflict': True  # Flag for frontend to prompt user
            }, status=409)

        # Create dir in github actions
        if _use_dictstore():
            upload_path.parent.mkdir(parents=True, exist_ok=True)

        # Save file
        try:
            with open(upload_path, 'wb+') as f:
                for chunk in file_obj.chunks():
                    f.write(chunk)
        except Exception as e:
            return JsonResponse({'error': f'Failed to save file: {str(e)}'}, status=500)

        buffer = io.StringIO()
        command_lookup = {
            'ctd': ['importcast', 'importniskin'],
            'elog': ['importevent'],
            'underway': ['importunderwaydata'],
            'nutrient' : ['importnut'],
            'sample_log' : ['importnut'],
            'station_list' : ['importstations'],
            'cruise_types' : ['importcruise'],
            'hplc' : ['importhplc'],
            'chlorophyll' : ['importchl']
        }
        message = f'Cruise name: {cruise_name},'
        message += f' File type: {file_type}.\n'
        try:
            commands = command_lookup.get(file_type, [])
            for cmd in commands:
                if file_type == 'station_list':
                    call_command(cmd, stdout=buffer)
                else:
                    call_command(cmd, cruise_name=cruise_name, stdout=buffer)

            output = buffer.getvalue()
            buffer.close()
            import_message = output + '\nImport completed successfully.'
            message += import_message
        except Exception as e:
            return JsonResponse({'error': f'{command_lookup.get(file_type)} failed: {str(e)}'}, status=500)
        return JsonResponse({'message': message})

    return render(request, 'upload.html')

def clean_float(val):
    try:
        return float(str(val).strip().replace("–", "-"))
    except Exception:
        return None

SHIP_PREFIXES = [
    ("ar",  "AR Cruises",  "🚢"),   # Ship
    ("en",  "EN Cruises",  "🛳️"),  # Passenger ship
    ("hrs", "HRS Cruises", "🛥️"),  # Motor boat
    ("at",  "AT Cruises",  "⛴️"),   # Ferry
    ("ae",  "AE Cruises",  "⛵"),   # Sailboat
]

def get_cruises_grouped_by_year():
    cruises = (
        Cruise.objects
        .filter(Q(start_time__isnull=False) | Q(end_time__isnull=False))
        .annotate(year=Coalesce(ExtractYear('start_time'), ExtractYear('end_time')))
        .order_by('-year', 'name')
    )

    # Group: {year: [Cruise, ...]}
    year_map = {}
    for c in cruises:
        year_map.setdefault(c.year, []).append(c)

    # Transform to a list for templates
    cruise_years = [
        {'year': year, 'cruises': year_map[year], 'count': len(year_map[year])}
        for year in sorted(year_map.keys(), reverse=True)
    ]
    return cruise_years

def landing(request):
    cruise_count = Cruise.objects.count()
    cruise_years = get_cruises_grouped_by_year()

    return render(request, "landing.html", {
        "cruise_count": cruise_count,
        "cruise_years": cruise_years,
    })

def cruises_by_ship(request):
    cruise_ships = []
    for prefix, label, emoji in SHIP_PREFIXES:
        count = Cruise.objects.filter(name__istartswith=prefix).count()
        cruise_ships.append({
            "prefix": prefix,
            "label": label,
            "emoji": emoji,
            "count": count,
        })

    return render(request, "cruises_by_ship.html", {
        "cruise_ships": cruise_ships,
    })

def cruises_by_year(request):
    cruise_years = get_cruises_grouped_by_year()

    return render(request, "cruises_by_year.html", {
        "cruise_years": cruise_years,
    })

def cruises_for_year(request, year):
    # Get all cruises where start_time or end_time matches the given year
    cruises = Cruise.objects.filter(
        start_time__year=year
    ) | Cruise.objects.filter(
        end_time__year=year
    )
    cruises = cruises.order_by('start_time')

    label = f"Cruises in {year}"
    emoji = "🗓️"

    return render(request, "cruise_list.html", {
        "label": label,
        "emoji": emoji,
        "cruises": cruises,
    })

SEASON_META = {
    "spring": {"label": "Spring", "emoji": "🌱", "months": [3, 4, 5]},
    "summer": {"label": "Summer", "emoji": "🌞", "months": [6, 7, 8]},
    "fall":   {"label": "Fall",   "emoji": "🍂", "months": [9, 10, 11]},
    "winter": {"label": "Winter", "emoji": "❄️", "months": [12, 1, 2]},
}

def _month_to_season(m: int) -> str:
    if m in (3, 4, 5):   return "spring"
    if m in (6, 7, 8):   return "summer"
    if m in (9, 10, 11): return "fall"
    return "winter"  # 12, 1, 2

def cruises_by_season(request):
    qs = (
        Cruise.objects
        .filter(Q(start_time__isnull=False) | Q(end_time__isnull=False))
        .annotate(month=Coalesce(ExtractMonth("start_time"), ExtractMonth("end_time")))
        .order_by("start_time")
    )

    # Bucket cruises into seasons
    season_map = {k: [] for k in SEASON_META.keys()}
    for c in qs:
        season_map[_month_to_season(c.month)].append(c)

    season_groups = [
        {
            "season": key,
            "label": SEASON_META[key]["label"],
            "emoji": SEASON_META[key]["emoji"],
            "count": len(season_map[key]),
        }
        for key in ["spring", "summer", "fall", "winter"]
    ]

    return render(request, "cruises_by_season.html", {"season_groups": season_groups})

def cruises_for_season(request, season: str):
    season = season.lower()
    if season not in SEASON_META:
        raise Http404("Unknown season")

    qs = (
        Cruise.objects
        .filter(Q(start_time__isnull=False) | Q(end_time__isnull=False))
        .annotate(month=Coalesce(ExtractMonth("start_time"), ExtractMonth("end_time")))
        .filter(month__in=SEASON_META[season]["months"])
        .order_by("start_time")
    )

    return render(request, "cruise_list.html", {
        "label": f"{SEASON_META[season]['label']} Cruises",
        "emoji": SEASON_META[season]["emoji"],
        "cruises": qs,
    })

TYPE_PREFIXES = [
    (Cruise.CruiseType.NESLTER,  "NESLTER",  "🚢"),
    (Cruise.CruiseType.JP_STUDENT,  "JP Student",  "🛳️"),
    (Cruise.CruiseType.OOI_NES, "OOI NES", "🛥️"),
    (Cruise.CruiseType.OOI_MAB, "OOI MAB", "⛴️"),
    (Cruise.CruiseType.OPPORTUNISTIC, "Opportunistic", "⛵"),
]

def cruises_by_type(request):
    cruise_types = []
    for prefix, label, emoji in TYPE_PREFIXES:
        count = Cruise.objects.filter(type=prefix).count()
        cruise_types.append({
            "prefix": prefix,
            "label": label,
            "emoji": emoji,
            "count": count,
        })

    return render(request, "cruises_by_type.html", {
        "cruise_types": cruise_types,
    })

def cruises_for_type(request, cruise_type: str):
    cruises = Cruise.objects.filter(type=cruise_type).order_by("start_time", "name")

    label = next((lbl for p, lbl, _ in TYPE_PREFIXES if p == cruise_type), cruise_type)
    emoji = next((em for p, _, em in TYPE_PREFIXES if p == cruise_type), "🚢")

    return render(request, "cruise_list.html", {
        "label": label,
        "emoji": emoji,
        "cruises": cruises,
    })

def cruise_list(request, prefix: str):
    prefix = prefix.lower()
    # Filter cruises by prefix
    qs = Cruise.objects.filter(name__istartswith=prefix)

    # sort cruises by number and suffix letter
    cruises = sorted(
        qs,
        key=lambda c: (
            int(re.search(r'\d+', c.name).group()),
            re.search(r'[a-z]$', c.name.lower()).group() if re.search(r'[a-z]$', c.name.lower()) else ""
        )
    )

    label = next((lbl for p, lbl, _ in SHIP_PREFIXES if p == prefix), prefix.upper())
    emoji = next((em for p, _, em in SHIP_PREFIXES if p == prefix), "🚢")

    return render(request, "cruise_list.html", {
        "prefix": prefix,
        "label": label,
        "emoji": emoji,
        "cruises": cruises,
    })

def cruise_track_view(request, cruise_name):
    UNDERWAY_SUFFIX = '_underway.csv'

    try:
        cruise = Cruise.objects.get(name__iexact=cruise_name)
        casts = Cast.objects.filter(cruise=cruise).order_by('start_time')

        # Prepare clickable cast points for JS (GeoJSON-like)
        cast_points = [
            {
                "lat": cast.geolocation.y,
                "lng": cast.geolocation.x,
                "label": cast.number,
                "depth": cast.depth,
                "start_time": cast.start_time.strftime("%Y-%m-%d %H:%M")
            }
            for cast in casts
        ]

        object_key = f"{cruise_name}{UNDERWAY_SUFFIX}"
        with get_store() as store:
            try:
                data = store.get(object_key)
            except Exception as e:
                print(e, flush=True)
                return HttpResponse("Underway file not found.", status=404)

        underway_data = pd.read_csv(io.BytesIO(data))

        # Non-clickable track points (no labels or popups)
        try:
            track_points = [
                {"lat": row["dec_lat"], "lng": row["dec_lon"]}   # ar
                for _, row in underway_data.iterrows()
            ]
        except KeyError:
            try:
                track_points = [
                    {"lat": row["latitude_deg"], "lng": row["longitude_deg"]}   # hrs2303
                    for _, row in underway_data.iterrows()
                ]
            except KeyError:
                try:
                    track_points = [
                        {"lat": row["gps_furuno_latitude"], "lng": row["gps_furuno_longitude"]}   # en
                        for _, row in underway_data.iterrows()
                    ]
                except KeyError:
                    
                    track_points = [
                        {"lat": row["latitude"], "lng": row["longitude"]}   # ae2426
                        for _, row in underway_data.iterrows()
                    ]

        clean_track_points = []
        for i, point in enumerate(track_points):
            lat = clean_float(point["lat"])
            lng = clean_float(point["lng"])

            if (
                pd.isnull(lat) or pd.isnull(lng) or
                not isinstance(lat, (float, int)) or
                not isinstance(lng, (float, int)) or
                lat < -90 or lat > 90 or
                lng < -180 or lng > 180
            ):
                print(f"[Invalid] Entry {i}: lat={lat}, lng={lng}")
            else:
                clean_track_points.append(point)

        track_points = clean_track_points
                    
        context = {
            'cruise': cruise,
            'track_points_json': json.dumps(track_points),
            'cast_points_json': json.dumps(cast_points),
        }

        return render(request, 'cruise_track.html', context)
    except Cruise.DoesNotExist:
        raise CommandError(f'Cruise not found {cruise_name}. Run importcruise.py')

def ctd_plot_view(request, cruise_name, cast_number):
    
    ar_primary_sensor_list = ["t090c", "sal00_1", "fleco_afl",  "sbeox0v" ]
    en_primary_sensor_list = ["t090c", "sal00", "fleco_afl",  "sbeox0v"  ]
    at_primary_sensor_list = ["t090c", "sal00",  "fleco_afl",  "sbeox0v"]
    hrs_primary_sensor_list = ["t090c", "sal00",  "fleco_afl",  "sbeox0ml_l" ]

    sensor_label = {
        "t090c": "Temperature (C)",
        "sal00": "Salinity (PSU)",
        "sal00_1": "Salinity (PSU)",
        "fleco_afl": "Fluorescence (MG/M^3)",
        "sbeox0v": "Oxygen (V)",
        "sbeox0ml_l": "Oxygen (mL/L)"
    }

    object_key = f"{cruise_name}_ctd_cast_{cast_number}.csv"

    with get_store() as store:
            try:
                data = store.get(object_key)
            except Exception as e:
                print(e, flush=True)
                return HttpResponse("CTD file not found.", status=404)

    df = pd.read_csv(io.BytesIO(data))

    if cruise_name.startswith('ar'):
        sensor_columns = ar_primary_sensor_list
    elif cruise_name.startswith('at'):
        sensor_columns = at_primary_sensor_list
    elif cruise_name.startswith('hrs'):
        sensor_columns = hrs_primary_sensor_list
    else:
        sensor_columns = en_primary_sensor_list

    try:
        df = df.sort_values('date')
    except:
        print(f'Cannot sort values by date for cruise {cruise_name}', flush=True)

    sensors = [col for col in sensor_columns if col in df.columns]

    # Create base figure
    fig, host = plt.subplots(figsize=(4, 8))  # make taller
    host.invert_yaxis()
    host.set_ylabel("Depth (m)")
    host.grid(True)

    colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red']
    axes = [host]
    lines = []

    for i, sensor in enumerate(sensors):
        if i == 0:
            ax = host
        else:
            ax = host.twiny()  # additional x-axis
            ax.spines['top'].set_position(('axes', 1 + 0.15 * (i - 1)))  # stagger axes
            ax.spines["top"].set_visible(True)
            ax.xaxis.set_ticks_position('top')
            ax.xaxis.set_label_position('top')
        axes.append(ax)

        line, = ax.plot(df[sensor], df['depsm'], label=sensor, color=colors[i % len(colors)])
        ax.set_xlabel(sensor_label.get(sensor, sensor)) 
        ax.tick_params(axis='x', colors=colors[i % len(colors)])
        ax.spines['top'].set_edgecolor(colors[i % len(colors)])
        lines.append(line)

    host.set_title(f"{cruise_name} Cast {cast_number} - CTD Profile")
    fig.tight_layout()

    # Return as image
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)

    # The title will be verified in cruise_track.js automated test
    resp = HttpResponse(buffer.getvalue(), content_type="image/png")
    resp["X-Plot-Title"] = f"{cruise_name} Cast {cast_number} - CTD Profile"
    return resp

def download_bathymetry(request):
        filepath = '/vast/raw/all/bathymetry/neslter_bathymetry.csv'
        return FileResponse(open(filepath, 'rb'), as_attachment=True, filename='bathymetry.csv')

def readme_page(request):
    cruise = request.GET.get("cruise_name", "")
    return render(request, "readmes.html", {"cruise": cruise})

