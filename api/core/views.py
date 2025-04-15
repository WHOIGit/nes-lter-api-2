from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
import os
import io
import json
import dotenv
import pandas as pd
from django.conf import settings
from django.core.management.base import CommandError
from .models import Cruise, Cast
from storage.mediastore import MediaStore
from storage.utils import PrefixStore
from django.conf import settings
import matplotlib.pyplot as plt
from io import BytesIO

@csrf_exempt
def file_upload_view(request):
    if request.method == 'POST':
        file_obj = request.FILES['file']
        upload_path = os.path.join(settings.MEDIA_ROOT, file_obj.name)
        with open(upload_path, 'wb+') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        return JsonResponse({'message': f'{file_obj.name} uploaded successfully.'})
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

    dotenv.load_dotenv()
    URL = os.getenv("URL")
    TOKEN = os.getenv("TOKEN")

    object_key = f"{cruise_name}_ctd_cast_{cast_number}.csv"
    with MediaStore(URL, token=TOKEN) as store:
        prefix = PrefixStore(store, settings.MEDIASTORE_PREFIX)
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
    else:  # cruise starts with EN
        sensor_columns = en_primary_sensor_list

    df = df.sort_values('depsm')
    print(sensor_columns, flush=True)
    sensors = [col for col in sensor_columns if col in df.columns]
    print(df.columns, flush=True)
    print(sensors, flush=True)

    # Create base figure
    fig, host = plt.subplots(figsize=(7, 6))
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
        ax.set_xlabel(sensor)
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
