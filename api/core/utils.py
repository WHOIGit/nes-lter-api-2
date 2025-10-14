import math
from datetime import datetime
import re
import pandas as pd
import os
from contextlib import contextmanager
from storage.mediastore import MediaStore
from storage.utils import PrefixStore
from storage.object import DictStore
from storage.fs import FilesystemStore

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
        print("USE DICTSTORE", flush=True)
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