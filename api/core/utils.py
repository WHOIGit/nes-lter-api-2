import math
from datetime import datetime
import re
import pandas as pd
import os
import glob
import numpy as np
import logging
from contextlib import contextmanager
from storage.mediastore import MediaStore
from storage.utils import PrefixStore
from storage.object import DictStore
from storage.fs import FilesystemStore
from django.http import Http404

logger = logging.getLogger(__name__)

def path_to_cast(cruise_name, filename):

    CRUISE_CAST_REGEXES = [
         r'cast(\d{1,3}[a-zA-Z]?)', 
         rf'{cruise_name}_?(\d{{1,3}}[a-zA-Z]?)?(?:_u)?\.\w+$'
    ]

    cast = None
    for regex in CRUISE_CAST_REGEXES:
        match = re.search(regex, filename)
        if match:
            cast = match.group(1)
            return cast

def format_utc_date(date_str, time_str):
    dt = datetime.strptime(date_str + " " + time_str, "%b %d %Y %H:%M:%S")
    return dt.strftime("%Y-%m-%d %H:%M:%S") + "Z"

def convert_to_decimal(degrees, minutes, direction):
    decimal = float(degrees) + float(minutes) / 60
    if direction in ['S', 'W']:
        decimal *= -1
    return round(decimal, 6)

def p_to_depth(p, latitude):
    """convert pressure to depth in seawater.
    p = pressure in dbars
    latitude"""

    # use the Seabird calculation
    # from http://www.seabird.com/document/an69-conversion-pressure-depth

    x = math.pow(math.sin(latitude / 57.29578),2)
    g = 9.780318 * ( 1.0  + (5.2788e-3 + 2.36e-5 * x) * x ) + 1.092e-6 * p
    depth_m_sw = ((((-1.82e-15 * p + 2.279e-10) * p - 2.2512e-5) * p + 9.72659) * p) / g
    
    return depth_m_sw

def parse_lat_lon(content):
    lat_pattern = re.search(r'NMEA Latitude\s*=\s*(\d{2})\s*(\d{2}\.\d+)\s*([NS])', content)
    lon_pattern = re.search(r'NMEA Longitude\s*=\s*(\d{3})\s*(\d{2}\.\d+)\s*([EW])', content)
    if lat_pattern != None and lon_pattern != None:
        latitude = convert_to_decimal(lat_pattern.group(1), lat_pattern.group(2), lat_pattern.group(3))
        longitude = convert_to_decimal(lon_pattern.group(1), lon_pattern.group(2), lon_pattern.group(3))
        return latitude, longitude
    else:
        return None, None

def parse_time(content):
    utc_pattern = re.search(r'NMEA UTC \(Time\)\s*=\s*([A-Za-z]+ \d{2} \d{4})\s+(\d{2}:\d{2}:\d{2})', content)

    if utc_pattern != None:
        start_time = format_utc_date(utc_pattern.group(1), utc_pattern.group(2))
        return start_time
    else:
        return None


def clean_column_name(colname):
    """convert column names to lowercase with underbars"""
    colname = colname.lower().rstrip().lstrip()
    colname = re.sub(r'[^a-z0-9_]+','_',colname) # sub _ for nonalpha chars
    colname = re.sub(r'_$','',colname)  # remove trailing _
    colname = re.sub(r'^([0-9])',r'_\1',colname) # insert _ before leading digit
    return colname

def clean_column_names(df, col_map={}, inplace=False):
    """clean all column names for a Pandas dataframe"""
    if not inplace:
        df = df.copy()
    ccns = []
    for c in df.columns:
        if c in col_map:
            ccns.append(col_map[c])
        else:
            ccns.append(clean_column_name(c))
    df.columns = ccns
    return df

def wide_to_long(df, wide_cols_list, value_cols, long_col, long_labels):
    """converts selected columns from wide to long format. params:
    
    - df: the input dataframe
    - wide_cols_list: for each set of wide columns, a list of their names
    - value_cols: for each set of wide columns, the name of the long column to hold the values
    - long_col: the name of the column to indicate which set of wide columns the value comes from
    - long_labels: for each set of wide columns, what to call it in the long_col values.
    
    For example if I have the following DataFrame:
    
    +-----------+-----+-----+-----+-----+
    | other_col | x_a | x_b | y_a | y_b |
    +-----------+-----+-----+-----+-----+
    | something |  1  |  2  |  10 |  20 |
    +-----------+-----+-----+-----+-----+
    
    And I pass these arguments:
    
    wide_cols_list = [['x_a','y_a'],['x_b','y_b']]
    value_cols = ['x','y']
    long_col = 'replicate'
    long_labels = ['a','b']
    
    It'll generate this dataframe:
    
    +-----------+---+----+-----------+
    | other_col | x |  y | replicate |
    +-----------+---+----+-----------+
    | something | 1 | 10 |     a     |
    | something | 2 | 20 |     b     |
    +-----------+---+----+-----------+
    """
    if len(wide_cols_list) != len(long_labels):
        raise ValueError('Number wide columns does not match number long labels')
    for w in wide_cols_list:
        if len(w) != len(value_cols):
            raise ValueError('Number wide columns does not match number value columns')
    exclude_cols = []
    for w in wide_cols_list:
        exclude_cols = exclude_cols + w
    common_cols = [c for c in df.columns if c not in exclude_cols]
    dfs = []
    for wide_cols, long_label in zip(wide_cols_list, long_labels):
        sdf = df[common_cols + wide_cols].copy()
        sdf[long_col] =  long_label
        sdf.columns = common_cols + value_cols + [long_col]
        dfs.append(sdf)
    return pd.concat(dfs).sort_index()

def float_to_datetime(s, format='%Y%m%d'):
    """pandas will interpret some datetime formats as floats, e.g.,
    '20180830' will be parsed as the float 20180830.0.
    convert back to datetimes"""
    def convert(value):
        return pd.to_datetime(str(int(value)), format=format, utc=True)
    return s.map(convert, na_action='ignore')

def cast_columns(df, dtype, columns, inplace=False, fillna=None):
    """convert columns in a dataframe to the given datatype,
    in place"""
    if not inplace:
        df = df.copy()
    for c in columns:
        df[c] = df[c].astype(dtype)
        if fillna is not None:
            df[c] = df[c].fillna(fillna)
    return df

def _use_dictstore() -> bool:
    return os.getenv("USE_DICTSTORE", "FALSE").upper() == "TRUE"

@contextmanager
def get_store( url, token, prefix):

    if _use_dictstore():
        # In-memory store for CI/tests; no network
        root = "/data/.store"
        os.makedirs(root, exist_ok=True)
        base_store = FilesystemStore(root)
        prefixed = PrefixStore(base_store, prefix or "")
        yield prefixed
    else:
        # Real vast store
        with MediaStore(url, token=token) as base_store:
            prefixed = PrefixStore(base_store, prefix or "")
            yield prefixed

def date_time_to_datetime(date, time):
    try:
        # for Series objects (e.g., DataFrame columns)
        return pd.to_timedelta(time.astype(str)) + pd.to_datetime(date, utc=True)
    except AttributeError:
        # for a single date/time
        return pd.to_timedelta(time) + pd.to_datetime(date, utc=True)

def find_readme(cruise_name, data_type):
    for fn in glob.glob(os.path.join(f'/vast/corrected/{cruise_name}/{data_type}/', 'README*')):
        return fn
    for fn in glob.glob(os.path.join(f'/vast/raw/{cruise_name}/{data_type}/', 'README*')):
        return fn
    raise Http404(f"{data_type} README file for {cruise_name} not found.")

def read_sample_log():
    sample_log_path = f'/vast/raw/all/LTER_sample_log.xlsx'
    raw = pd.read_excel(sample_log_path, na_values='-', dtype={
            'Nut a': str,
            'Nut b': str,
            'Niskin #': str
        })
    df = clean_column_names(raw, {
        'Date \n(UTC)': 'date',
        'Start Time (UTC)': 'time',
        'Niskin #': 'niskin',
        'Niskin\nTarget\nDepth': 'depth',
    })

    # for ar24 some niskin numbers are given as a list in the sample log (e.g., "4,5,6")
    # so pick the first one for now, proposed solution is to average the CTD bottle data
    df['niskin'] = df['niskin'].fillna('0').str.replace(',.*','',regex=True).astype(int)
    df['Comments'] = df.comments.fillna('')
    # drop rows without an a replicate

    df = df[['cruise','cast','niskin','nut_a','nut_b', 'ooi_nut_id']].dropna(subset=['nut_a'])        
    df['cruise'] = df['cruise'].astype(str).str.upper()

    # check for duplicate sample ids across nut_a and nut_b columns
    combined = pd.concat([df['nut_a'], df['nut_b']]).dropna()
    duplicate_ids = combined[combined.duplicated(keep=False)].unique()
    dup_rows = df[df['nut_a'].isin(duplicate_ids) | df['nut_b'].isin(duplicate_ids)]
    dup_rows = dup_rows[(dup_rows['nut_a'] != ' -') & (dup_rows['nut_b'] != ' -')]
    if not dup_rows.empty:
        print("Warning: Duplicate sample IDs found across nut_a and nut_b in LTER_sample_log.xlsx:")
        print(dup_rows[['cruise', 'cast', 'niskin', 'nut_a', 'nut_b']].to_string())

    # make replicates long instead of wide
    sample_ids = wide_to_long(df, [['nut_a'],['nut_b']], ['sample_id'], 'replicate', ['a','b'])
    return(sample_ids)

def read_nut_data(cruise, merged):
    RAW_COLS = ['Nutrient \nNumber', 'Cruise', 'Cast', 'LTER \nSample ID', 'Nitrate + Nitrite', 'Ammonium',
    'Phosphate', 'Silicate', 'Comments']

    NUT_COLS = ['nitrate_nitrite', 'ammonium', 'phosphate', 'silicate']

    file = f'/vast/raw/all/nut/LTERnut.xlsx'
    df = pd.read_excel(file, skiprows=[0,1])

    if set(df.columns) != set(RAW_COLS):
        raise ValueError('Nut spreadsheet does not contain expected columns')
    df = clean_column_names(df)

    # mismatches can lead to unexpected results
    nut = df['nutrient_number'].astype(str).str.replace('NL_', '', regex=False)\
        .str.replace('NL', '', regex=False).str.strip()
    nut = pd.to_numeric(nut).astype(int)
    lter = df['lter_sample_id']
    lter = pd.to_numeric(lter).astype(int)
    mismatch_mask = (nut != lter) & ((nut - lter).abs() != 3000) # ignore diffs of 3000
    num_mismatches = mismatch_mask.sum()
    if num_mismatches > 0:
        mismatches = pd.DataFrame({
            'nutrient_number': nut[mismatch_mask],
            'lter_sample_id': lter[mismatch_mask]
        })
        print(mismatches.to_string(index=False), flush=True)
        logger.error(f'Nutrient Number and LTER Sample ID: {num_mismatches} column values do not match in LTERnut.xlsx')
        raise ValueError(f'Nutrient Number and LTER Sample ID: {num_mismatches} column values do not match in LTERnut.xlsx')

    df['comments'] = df['comments'].fillna('')
    # deal with below-detection-limit values
    # for the nut cols, add {}_bdl col with the
    # detection limit value, for all below-detection-limit
    # values. in the value column put a zero
    for col in NUT_COLS:
        bdl = []
        new_values = []
        for v in df[col].values:
            if str(v).startswith('<'): # below detection limit
                detection_limit = float(str(v)[1:])
                bdl.append(detection_limit)
                new_values.append(0)
            else:
                bdl.append(np.nan)
                new_values.append(v)
        bdl_col = '{}_bdl'.format(col)
        df[bdl_col] = bdl
        df[col] = new_values

    # nutrient_number is used instead of lter_sample_id
    df['lter_sample_id'] = df['nutrient_number'].str.replace('NL_','')
    df = df[['lter_sample_id','nitrate_nitrite','ammonium','phosphate','silicate']]
    df['sample_id'] = df.pop('lter_sample_id').astype(str)

    nut_profile = merged.merge(df, on='sample_id')
    nut_profile['date'] = pd.to_datetime(nut_profile['date'], utc=True)
    # sort alphanumeric casts in numeric order (not alpha order) such that 2 preceeds 12
    nut_profile['cast'] = pd.to_numeric(nut_profile['cast'])
    nut_profile = nut_profile.sort_values(['cast','niskin','replicate'])
    nut_profile['cast'] = nut_profile['cast'].astype(str)
    nut_profile['alternate_sample_id'] = nut_profile.pop('ooi_nut_id')

    # set date, lat, lon, depth to NaN when there is no bottle file for the cast
    btl_dir = f'/vast/raw/{cruise}/ctd/'
    for file in sorted(
        f for f in glob.glob(os.path.join(btl_dir, '*.asc'))
        if not f.endswith('_original.asc')
    ):
        if cruise == 'en627':
            file = file.replace("_u", "")
        btl_file = file[:-3] + 'btl'
        if not os.path.exists(btl_file):
            cast = path_to_cast(cruise, btl_file)
            if cast is None:
                    continue
            cast = cast.lstrip('0')
            nut_profile.loc[nut_profile['cast'] == cast, 'date'] = ''
            nut_profile.loc[nut_profile['cast'] == cast, 'latitude'] = np.nan
            nut_profile.loc[nut_profile['cast'] == cast, 'longitude'] = np.nan
            nut_profile.loc[nut_profile['cast'] == cast, 'depth'] = np.nan

    return nut_profile
