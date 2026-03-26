import os
import glob
import re
import io
import pandas as pd
import sys
import logging
from django.core.management.color import color_style
from django.core.management.base import BaseCommand, CommandError
from core.models import Cruise
from core.models import Cast, Niskin
from pathlib import Path
from django.contrib.gis.geos import Point
from django.core.exceptions import ObjectDoesNotExist
from core.utils import p_to_depth, path_to_cast, get_store, \
                       parse_lat_lon, clean_column_names
from collections import defaultdict

# date column is the second column (index 1)
DATE_COL_IX = 1
BOTTLE_COL = 'Bottle'
DATE_COL = 'Date'
PRESSURE_COL = 'PrDM'
DEPTH_COL = 'DepSM'
LAT_COL = 'Latitude'
LON_COL = 'Longitude'

CRUISE_COL = 'cruise'
CAST_COL = 'cast'
NISKIN_COL = 'niskin'

BOTTLES_SUFFIX = '_ctd_bottles.csv'
SUMMARY_SUFFIX = '_ctd_bottle_summary.csv'

logger = logging.getLogger('management')

def col_values(line, col_widths, justification='right'):
    """read fixed-width column values"""
    if justification not in ['left', 'right', 'center']:
        raise ValueError('Justification not left, right, or center')
    vals = []
    i = 0

    for w in col_widths:
        start = i
        end = i + w
        raw_val = line[start:end]
        # handle justification
        if justification == 'right':
            val = raw_val.lstrip()
        elif justification == 'left':
            val = raw_val.rstrip()
        elif justification == 'center':
            val = raw_val.lstrip().rstrip()
        vals.append(val)
        i += w

    return vals

def to_dataframe(cruise_name, cast, in_lines):
        
    lines = []

    for l in in_lines:
        if l.startswith('#') or l.startswith('*'):
            continue
        lines.append(l)

    # column headers are fixed width at 11 characters per column,
    # except the first two
    h1_width = 10
    h2_width = 12
    n_cols = ((len(lines[0]) - (h1_width + h2_width)) // 11) + 2
    header_col_widths = [h1_width,h2_width] + [11] * (n_cols - 2)
    # the first line is the first line of column headers; skip the second
    col_headers = col_values(lines[0], header_col_widths)

    # discard the header lines, the rest are data lines
    lines = lines[2:]

    # data lines are in groups of 4 (if min/max is written to the file)
    # or in groups of 2
    n_lines_per_sample = 2

    for line in lines:
        if line.strip().endswith('(min)'):  # min/max are present
            n_lines_per_sample = 4
            break
    
    # average values are every 2 or 4 lines
    avg_lines = lines[::n_lines_per_sample]
    # the lines with the time (and stddev values) are the ones immediately
    # following the average value lines
    time_lines = lines[1::n_lines_per_sample]

    # value columns are fixed width 11 characters per col except the first two
    bottle_column_width = 7 # bottle number column
    datetime_column_width = 15 # date/time column

    value_col_widths = [11] * (n_cols - 2)
    col_widths = [bottle_column_width, datetime_column_width] + value_col_widths

    # now assemble the rows of the dataframe
    rows = []

    for al, tl in zip(avg_lines, time_lines):
        cvs = col_values(al, col_widths)
        # date/time is split across two rows
        time = col_values(tl, col_widths)[DATE_COL_IX]
        cvs[DATE_COL_IX] = '{} {}'.format(cvs[DATE_COL_IX], time)
        rows.append(cvs)

    try:
        df = pd.DataFrame(rows, columns=col_headers)
    except:
        style = color_style()
        sys.stdout.write(style.ERROR(f'Bad formatted .btl file columns found for cruise {cruise_name} cast {cast}.'))
        logger.error((f'Bad formatted .btl file columns found for cruise {cruise_name} cast {cast}.'))
        return

    # convert df columns to reasonable types
    df[BOTTLE_COL] = df[BOTTLE_COL].astype(int)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], utc=True)

    for c in df.columns[2:]:
        df[c] = df[c].astype(float)

    # add cruise / cast
    df[CRUISE_COL] = cruise_name
    df[CAST_COL] = cast

    # rename Bottle column
    df = df.rename(columns={BOTTLE_COL: NISKIN_COL})

    # move those columns to the front
    cols = df.columns.tolist()
    cols = cols[-2:] + cols[:-2]
    df = df[cols]
    return df

class Command(BaseCommand):
    help = 'Create Ninkin Models. If Cruise Name is not supplied, all Niskins for all Cruises and Casts will be created.'

    def __init__(self):
        super().__init__()
        self.URL = os.getenv("URL")
        self.TOKEN = os.getenv("TOKEN")
        self.MEDIASTORE_PREFIX = os.getenv("MEDIASTORE_PREFIX")

    def add_arguments(self, parser):
        parser.add_argument('--cruise_name', type=str, help='Optional name of the cruise.', default=None)

    def handle(self, *args, **options):

        cruise_name = options['cruise_name']
        if cruise_name is None:
            parent_dir = Path('/vast/raw')
            cruises = [f.name for f in parent_dir.iterdir() if f.is_dir() and f.name != "all"]
        else:
            cruises = [cruise_name]

        for cruise_name in cruises:
            try:
                dfs = []
                cruise = Cruise.objects.get(name__iexact=cruise_name)

                directory = f'/vast/raw/{cruise_name}/ctd/'
                btl_files = sorted(
                    f for f in glob.glob(os.path.join(directory, '*.btl'))
                    if not f.endswith('_original.btl')
                )
                if cruise_name.lower() == "en627":
                    added_dir = os.path.join(directory, "cast_1_files_used_for_corrected_cast_2")
                    btl_files += sorted(glob.glob(os.path.join(added_dir, '*.btl')))

                # track seen niskin numbers for each cast
                seen_niskins: dict[int, set[int]] = defaultdict(set)

                for file in btl_files:

                    filename = os.path.basename(file).lower()
                    if cruise_name == 'ar24a':
                        cruise_pattern = re.escape(cruise_name[:-1])  
                    else:
                        cruise_pattern = re.escape(cruise_name)

                    cast = path_to_cast(cruise_pattern, filename)
                    if cruise_name.lower() == "en627" and cast == "001":
                        cast = "002"
                    if cast is not None:
                        try:
                            cast_obj = Cast.objects.get(cruise=cruise, number__iexact=cast.lstrip('0'))

                            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            latitude, longitude = parse_lat_lon(content)
                         
                            with open(file, 'r', encoding='latin1') as f:
                                lines = f.readlines()                            
                            df = to_dataframe(cruise_name, cast, lines)
                            if df is None:
                                continue
                            
                            # add lat/lon and depth for armstrong and atlantis cruises
                            if LAT_COL not in df.columns and LON_COL not in df.columns:
                                df[LAT_COL] = latitude
                                df[LON_COL] = longitude
                            
                            if DEPTH_COL not in df.columns and PRESSURE_COL in df.columns:
                                df[DEPTH_COL] = [
                                    p_to_depth(float(p), float(lat)) if pd.notna(p) and pd.notna(lat) else None
                                    for p, lat in zip(df[PRESSURE_COL], df[LAT_COL])
                                ]
                                lat_index = df.columns.get_loc(LAT_COL)
                                df.insert(lat_index, DEPTH_COL, df.pop(DEPTH_COL))
                            
                            for _, row in df.iterrows():
                                if row[LON_COL] is not None and row[LAT_COL] is not None:
                                    geolocation = Point(float(row[LON_COL]), float(row[LAT_COL]), srid=4326)
                                else:
                                    geolocation = None
                               
                                if DEPTH_COL in row and row[DEPTH_COL] is not None:
                                    Niskin.objects.update_or_create(
                                        cast=cast_obj,
                                        number=row[NISKIN_COL],
                                        defaults={
                                            'depth': row[DEPTH_COL],
                                            'geolocation': geolocation
                                        }
                                    )

                                    seen_niskins[cast_obj.id].add(row[NISKIN_COL])

                                else:
                                    self.stdout.write(self.style.ERROR(f'Depth for Cruise {cruise_name} cast {cast} niskin {row[NISKIN_COL]} null. Model not updated.'))

                            # compile bottle files into a single dataframe
                            df = clean_column_names(df)  #converts to lower case
                            df = df.loc[:,~df.columns.duplicated()].copy()
                            df = df.astype({ NISKIN_COL: int })
                            dfs.append(df)

                        except ObjectDoesNotExist:
                            self.stdout.write(self.style.ERROR(f'Cast {cast} for Cruise {cruise_name} not imported. Run importcast.py'))
                            logger.error((f'Cast {cast} for Cruise {cruise_name} not imported. Run importcast.py'))

                # delete niskins from model not in the current files
                for cast_id, keep_numbers in seen_niskins.items():
                    qs = Niskin.objects.filter(cast_id=cast_id).exclude(number__in=keep_numbers).delete()
                    if qs[0] > 0:
                        self.stdout.write(self.style.WARNING(f'Deleted {qs[0]} niskins for cast id {cast_id} not present in current bottle files.'))

                if glob.glob(os.path.join(directory, "*.btl")) and dfs:
                    dfs = [df for df in dfs if not df.empty]  #remove empty dataframes
                    compiled_df = pd.concat(dfs, sort=False)
                    # 3 digit casts needed for sorting
                    compiled_df = compiled_df.sort_values([CAST_COL,NISKIN_COL])
                    compiled_df.reset_index()
                    compiled_df[CAST_COL] = compiled_df[CAST_COL].str.lstrip('0')
                    compiled_df[CRUISE_COL] = compiled_df[CRUISE_COL].str.upper()

                    # special case for ar28b missing btl file for cast 1
                    if cruise_name.lower() == "ar28b":
                        sample_file = os.path.join(directory, "samples_lacking_bottle_metadata-v3.csv")
                        samples_df = pd.read_csv(sample_file)
                        for col in ["cruise", "cast", "niskin"]:
                            compiled_df[col] = compiled_df[col].astype(str).str.strip()
                            samples_df[col] = samples_df[col].astype(str).str.strip()
                        samples_df["date"] = (
                            pd.to_datetime(
                                samples_df["date"],
                                format="%m/%d/%Y %H:%M",
                                errors="coerce"
                            )
                            .dt.tz_localize("UTC")
                        )
                        samples_df = samples_df.rename(columns={"depth": "depsm"})
                        ar28b_samples = samples_df[samples_df["cruise"].astype(str).str.lower() == "ar28b"].copy()
                        ar28b_for_bottles = ar28b_samples.reindex(columns=compiled_df.columns)
                        compiled_df = pd.concat([compiled_df, ar28b_for_bottles], ignore_index=True)
                        compiled_df['cast'] = pd.to_numeric(compiled_df['cast'])
                        compiled_df['niskin'] = pd.to_numeric(compiled_df['niskin'])
                        compiled_df = compiled_df.sort_values(['cast','niskin'])
                        compiled_df['cast'] = compiled_df['cast'].astype(str)
                        compiled_df['niskin'] = compiled_df['niskin'].astype(str)
                        compiled_df = compiled_df.drop_duplicates().reset_index(drop=True)

                    # write bottle file to media store
                    csv_buffer = io.StringIO()
                    compiled_df.to_csv(csv_buffer, index=False, na_rep="NaN")
                    csv_binary = csv_buffer.getvalue().encode("utf-8")

                    object_key = f"{cruise_name}{BOTTLES_SUFFIX}"
                    with get_store(self.URL, self.TOKEN, self.MEDIASTORE_PREFIX) as store:
                        try:
                            store.put(object_key, csv_binary)
                        except Exception as e:
                            print(e, flush=True)
                            logger.error(f'Exception {e}')
                            raise

                    # bottle summary
                    btl_sum = compiled_df.loc[:,['cruise','cast','niskin','date','latitude','longitude','depsm']]
                    btl_sum = btl_sum.rename(columns={'depsm':'depth'})

                    csv_buffer = io.StringIO()
                    btl_sum.to_csv(csv_buffer, index=False, na_rep="NaN")
                    csv_binary = csv_buffer.getvalue().encode("utf-8")

                    object_key = f"{cruise_name}{SUMMARY_SUFFIX}"
                    with get_store(self.URL, self.TOKEN, self.MEDIASTORE_PREFIX) as store:
                        try:
                            store.put(object_key, csv_binary)
                            self.stdout.write(self.style.SUCCESS(f'Niskins for Cruise {cruise_name} successfully imported.'))
                            logger.error((f'Niskins for Cruise {cruise_name} successfully imported.'))
                        except Exception as e:
                            print(e, flush=True)
                            logger.error(f'Exception {e}')
                            raise
                else:
                    self.stdout.write(self.style.ERROR(f'No Bottle or Header files found for Cruise {cruise_name}.'))
                    logger.error((f'No Bottle or Header files found for Cruise {cruise_name}.'))
            except Cruise.DoesNotExist:
                logger.error(f'Cruise not found {cruise_name}. Run importcruise.py')
                raise CommandError(f'Cruise not found {cruise_name}. Run importcruise.py')
            except Exception as e:
                logger.error(f'An error occurred: {str(e)}')
                raise CommandError(f'An error occurred: {str(e)}')
