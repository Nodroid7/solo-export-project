#!/usr/bin/env python3

import sys
import argparse
import json
from struct import Struct
from collections import namedtuple
from datetime import datetime

# Version number of the tool
VERSION="1.0"

# 2007-01-01 00:00:00 UTC
BASE_DATE_OFFSET = 1167609600

cmdline = None
date_map = {}

## output helpers

def _error(*args, **kwargs):
    print("ERROR:", *args, file=sys.stderr, **kwargs)

def _verbose(*args, v=1, **kwargs):
    if cmdline.verbose >= v:
        print(*args, file=sys.stderr, **kwargs)

def _debug(*args, v=None, **kwargs):
    if cmdline.debug:
        if v is None or cmdline.verbose >= v:
            print("DEBUG:", *args, file=sys.stderr, **kwargs)

## helpers

def format_date(timestamp):
    date_str = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S%z")
    return date_str

def get_timestamp(n, i):
    # n = mod 38912 = 19 * 2048
    # i = mod 65536 = 32 * 2048

    # xn * 38912 + n == xi * 65536 + i == 15min date offset from 2007-01-01

    # Cache calculated offsets
    xn = date_map.get(n - i)

    x = True
    if xn is None:
        _debug(f"Finding new date offset: row={n} index={i} diff={n - i}", v=1)
        # xi = ( 38912 * xn + n - i ) / 65536  if mod == 0
        xn = 0
        # CHECK add failsafe max based on possible date-result
        while x:
            xi, x = divmod(38912 * xn + n - i, 65536)
            _debug(f"get_timestamp: row={n} index={i} modulo search: row={xn}: index={xi} reminder={x}", v=2)
            xn += 1
            if xn > 255:
                _error(f"Date not found: row={n} index={i}")
                return None
        xn -= 1

        _debug(f"Found new date offset: {n - i} = {xn} ({xi})", v=2)
        date_map[n - i] = xn

    date_offset = xn * 38912 + n
    #date_offset = xi * 65536 + i

    # Get unixtime
    timestamp = date_offset * 900 + BASE_DATE_OFFSET

    if x == 0:
        _verbose(f"Date changed: {format_date(timestamp)} row={n} index={i}")

    return timestamp

def get_date(n, i):
    timestamp = get_timestamp(n, i)
    date_str = format_date(timestamp)
    return date_str

## functionality

def read_header(f):
    header_format = Struct("<BB 5H 4B 6B 13B")
    header_names = (
        'x_0_165',
        'x_33',

        'tariff_1',
        'tariff_2',
        'tariff_3',
        'std_charge', # CHECK
        'budget_yearly',

        'x_244',
        'x_1',
        'x_232',
        'x_3',

        'time_1_start',
        'time_1_end',
        'time_2_start',
        'time_2_end',
        'time_3_start',
        'time_3_end',

        'x_0_23',
        'z__50_52',
        'x_98',
        'z__1_2',

        'x_0_27',
        'x_100',
        'x_2',

        'z__255_1',
        'z__88_92_0',
        'z__24_26',

        'x_0_33',
        'x_0_34',

        'i', # index
    )
    Header = namedtuple('Header', header_names)

    ### header
    f.seek(9)

    n = 0
    while True:
        n += 1
        entry_bytes = f.read(35)
        if len(entry_bytes) < 35:
            if entry_bytes:
                _error(f"length={len(entry_bytes)}: {entry_bytes}")
            break

        if entry_bytes == (chr(0xff) * 35).encode('latin1'):
            _debug(f"End of headers: {n}")
            break

        entry_data = header_format.unpack(entry_bytes)
        header = Header._make(entry_data)

        # Print output
        #print(f"Header {n:3}: {[f'{v:5}' for v in entry_data]}")
        print(f"Header {n:3}: { {k: v for k, v in header._asdict().items() if k[0:2] not in {'x_', 'z_'}} }")

        # TODO split fields

        if n == 116:
            _error(f"Header area full: {n}")
            break

def read_extra(f):
    # Data between magic string and header entries
    f.seek(6)
    data = f.read(3)
    print(f"Data 6-8:  {' '.join('{:02x}'.format(v) for v in data)}")

    # Data between header and data
    f.seek(4069)
    data = f.read(27)
    print(f"Data 4069: {' '.join('{:02x}'.format(v) for v in data)}")

    # Extra data
    #f.seek(4096)
    data = f.read(4096)
    m = 64
    for i in range(64):
        print(f"Data {4096 + i * m}: {' '.join('{:02x}'.format(v) for v in data[i*m:(i+1)*m])}")


def read_data(f):
    data_format = Struct("<HHH 4s B 12s BBb H BB H")
    data_names = (
        'i', # 2 bytes
        'x_fefe', # 2
        'pwr_Wh',
        'x_00_1', # 4
        'price',
        'x_00_2', # 12
        'temp_out',
        'temp_in',
        'signal',
        'x_ff00', # 2
        'missed',
        'kk',
        'x_0000', # 2
    )
    Entry = namedtuple('Entry', data_names)
    Data = namedtuple('Data', [v for v in data_names if v[0:2] != 'x_'])

    if cmdline.format == 'csv':
        print('"' + '","'.join([
            "date",
            'pwr_Wh',
            'price',
            'temp_out',
            'temp_in',
            'signal',
            'missed',
            'kk',
            'accuracy',
        ]) + '"')
    elif cmdline.format == 'energynote':
        print("\ufeffDate (yyyymmdd hh:mm),Cost (Kr),Extra Cost (Kr),Consumption (kWh),Carbon (kg)")
    elif cmdline.format == 'json':
        print("[")

    ### data
    f.seek(8192)

    json_started = False
    unknown_start = None
    unknown_count = 0
    n = 0
    while True:
        entry_bytes = f.read(32)
        if len(entry_bytes) < 32:
            if entry_bytes:
                _error(f"length={len(entry_bytes)}: {entry_bytes}")
            break

        entry_data = data_format.unpack(entry_bytes)
        entry = Entry._make(entry_data)
        data = Data._make([entry_data[i] for i in (0, 2, 4, 6, 7, 8, 10, 11)])

        if data.missed == 255:
            if unknown_start is None:
                unknown_start = n
                unknown_count = 0
            unknown_count += 1
        else:
            if unknown_start is not None:
                _verbose(f"Empty data rows: {unknown_count} from row {unknown_start} to {n - 1}")
                unknown_start = None
                unknown_count = 0

            fields = data._asdict()
            del fields['i']

            # temp: x/2 - 30 ?
            fields['temp_out'] = None if data.temp_out == 255 else data.temp_out / 2 - 30
            fields['temp_in'] = data.temp_in / 2 - 30
            fields['accuracy'] = 100 * (254 - data.missed) / 254

            fields['price'] /= 1000

            timestamp = get_timestamp(n, data.i)
            if cmdline.time_shift:
                timestamp += cmdline.time_shift * 3600

            # Print output CHECK
            if cmdline.format == 'influxdb':
                # InfluxDB line format

                # Move some fields into tags
                tags = {}
                for k in ('kk',):
                    tags[k] = fields[k]
                    del fields[k]

                # Add integer suffix
                if fields['pwr_Wh'] == 0:
                    del fields['pwr_Wh']
                else:
                    fields['pwr_Wh'] = str(fields['pwr_Wh']) + "i"  # u
                fields['missed'] = str(fields['missed']) + "i"  # u
                fields['signal'] = str(fields['signal']) + "i"

                if fields['temp_out'] is None:
                    del fields['temp_out']

                print("{measurement}{tags_sep}{tags_str} {fields_str} {timestamp}".format(
                    measurement=cmdline.measurement,
                    tags_sep=',' if tags else '',
                    tags_str=','.join(f"{k}={v}" for k, v in tags.items()),
                    fields_str=','.join(f"{k}={v}" for k, v in fields.items()),
                    timestamp=timestamp
                ))

            elif cmdline.format == 'json':
                if json_started:
                    print(",")
                print(json.dumps({**{'timestamp': timestamp}, **fields}), end="")
                json_started = True

            elif cmdline.format == 'csv':
                fields['accuracy'] = "{:.3f}".format(fields['accuracy'])
                print(",".join('"' + str(v) + '"' for v in [format_date(timestamp)] + list(fields.values())))

            elif cmdline.format == 'energynote':
                date_str = datetime.utcfromtimestamp(timestamp).strftime("%Y%m%d %H:%M")
                # Date (yyyymmdd hh:mm),Cost (Kr),Extra Cost (Kr),Consumption (kWh),Carbon (kg)
                print(date_str + "," + ",".join("{:7.5f}".format(v) for v in [
                    fields['pwr_Wh'] / 1000 * fields['price'],
                    0,  # CHECK
                    fields['pwr_Wh'] / 1000,
                    fields['pwr_Wh'] / 1000 / 2,
                ]))

            else:
                # Default debug output
                if fields['temp_out'] is None:
                    fields['temp_out'] = 0
                print("{date} {n:5}: {accuracy:5.1f}% kW={kW:4.2f} pwr={pwr_Wh:4} out={temp_out:5} in={temp_in:5} {bars_pwr:40}|{bars_out_neg:>30s}{bars_out:40s} {bars_in:50s} {data}".format(
                    **fields,  # merge
                    date=format_date(timestamp) if data.missed != 255 else 'UNKNOWN',
                    n=n,
                    kW=fields['pwr_Wh'] * 4 / 1000,
                    bars_pwr='!' * int(fields['pwr_Wh'] / 10 / 5),
                    bars_out_neg='-' * int(-fields['temp_out']),
                    bars_out='.' * int(fields['temp_out']),
                    bars_in='.' * int( (fields['temp_in'] - 17) * 4 ),
                    data=data
                ))

        n += 1

    if cmdline.format == 'json':
        print("\n]")



def solo_export(filename):
    
    # datasets: pre-header (0-8 and 4069-4095), header (9-4068), extra-header (4096-8191), data (8192-end)

    with open(filename, "rb") as f:
        # Check file format
        magic_str = f.read(6)
        if magic_str != b'SoloII':
            _error("Not SOLOII.DAT file.")
            return None

        default = True

        if cmdline.header:
            default = False
            read_header(f)

        if cmdline.extra:
            default = False
            read_extra(f)

        if default or cmdline.data:
            read_data(f)

def parse_args():
    parser = argparse.ArgumentParser(description='Export data from Geo Solo 2 SOLOII.DAT binary data file.')

    parser.add_argument('filename',
                    help="SOLOII.DAT binary file to read")

    # Output selection
    parser.add_argument('-H', '--header', action='store_true',
                    help="Read header entries")
    parser.add_argument('-E', '--extra', action='store_true',
                    help="Read header extra data")
    parser.add_argument('-D', '--data', action='store_true',
                    help="Read data entries (default)")

    # Output format
    parser.add_argument('-f', '--format', choices=["influxdb", "json", "csv", "energynote"],
                    help="Output format (influxdb line format, JSON, CSV, energynote.eu detailedReadings.csv)")
    
    parser.add_argument('-m', '--measurement', default="solo",
                    help="Measurement name for influxdb (default: solo)")
    
    parser.add_argument('-t', '--time-shift', type=int,
                    help="Change original entry timestamp (hours)")

    # Debug options
    parser.add_argument('-d', '--debug', action='store_true',
                    help="Print debug information to stderr")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                    help="Increase verbosity (can be used multiple times)")

    # TODO write to file instead of stdout
    # TODO choose output format: columns, key_value, csv, json, xml, influxdb_line_format
    # TODO choose pretty options for columns output (e.g. bars for temp and pwr)
    # TODO choose time format

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    # set to global variable
    cmdline = parse_args()

    try:
        # Read file
        solo_export(cmdline.filename)
    except BrokenPipeError as e:
        _error(e)

