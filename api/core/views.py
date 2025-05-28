from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
import os
import io
import json
import pandas as pd
import re
from django.conf import settings
from django.core.management.base import CommandError
from .models import Cruise, Cast
from storage.mediastore import MediaStore
from storage.utils import PrefixStore
from django.conf import settings
import matplotlib.pyplot as plt
from io import BytesIO
from pathlib import Path
from django.core.management import call_command
from django.contrib.auth.decorators import login_required, user_passes_test

def is_staff(user):
    return user.is_staff

@login_required
@user_passes_test(is_staff)
def file_upload_view(request):
    if request.method == 'POST':

        dest_dir_lookup = {
            'ctd': lambda cruise_name: Path(f'/vast/raw/{cruise_name}/ctd'),
            'elog': lambda cruise_name: Path(f'/vast/raw/{cruise_name}/elog'),
            'underway': lambda cruise_name: Path(f'/vast/raw/{cruise_name}/underway'),
            'nutrient': Path('/vast/raw/all/nut'),
            'sample_log': Path('/vast/raw/all'),
            'station_list' : Path('/vast/raw/all/metadata'),
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
                'error': f"The file '{filename}' already exists in {destination_dir}.",
                'conflict': True  # Flag for frontend to prompt user
            }, status=409)

        # Save file
        try:
            with open(upload_path, 'wb+') as f:
                for chunk in file_obj.chunks():
                    f.write(chunk)
        except Exception as e:
            return JsonResponse({'error': f'Failed to save file: {str(e)}'}, status=500)

        buffer = io.StringIO()
        command_lookup = {
            'ctd': 'importcast',
            'elog': 'importevent',
            'underway': 'importunderwaydata',
            'nutrient' : 'importnut',
            'sample_log' : 'importnut',
            'station_list' : 'importstations',
            'hplc' : 'importhplc',
            'chlorophyll' : 'importchl'
        }
        message = f'Cruise name: {cruise_name},'
        message += f' File type: {file_type}.\n'
        try:
            if file_type == 'station_list':
                call_command(command_lookup.get(file_type), stdout=buffer)
            else:
                call_command(command_lookup.get(file_type), cruise_name=cruise_name, stdout=buffer)
            output = buffer.getvalue()
            buffer.close()
            import_message = output + '\nImport completed successfully.'
            message += import_message
        except Exception as e:
            return JsonResponse({'error': f'{command_lookup.get(file_type)} failed: {str(e)}'}, status=500)
        return JsonResponse({'message': message})

    return render(request, 'upload.html')

def cruise_track_view(request, cruise_name):
    try:
        cruise = Cruise.objects.get(name__iexact=cruise_name)
        casts = Cast.objects.filter(cruise=cruise).order_by('start_time')

        # Prepare track points for JS (GeoJSON-like)
        track_points = [
            {
                "lat": cast.geolocation.y,
                "lng": cast.geolocation.x,
                "label": cast.number,
                "depth": cast.depth,
                "start_time": cast.start_time.strftime("%Y-%m-%d %H:%M")
            }
            for cast in casts
        ]

        context = {
            'cruise': cruise,
            'track_points_json': json.dumps(track_points),
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

    URL = os.getenv("URL")
    TOKEN = os.getenv("TOKEN")
    MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")

    object_key = f"{cruise_name}_ctd_cast_{cast_number}.csv"
    with MediaStore(URL, token=TOKEN) as store:
        prefix = PrefixStore(store, MEDIASTORE_PREFIX)
        try:
            data = prefix.get(object_key)
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

    df = df.sort_values('date')
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

    return HttpResponse(buffer.getvalue(), content_type='image/png')
