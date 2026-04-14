#!/usr/bin/env python3
"""
nmea_lag.py - Measure lag between NMEA device timestamps and system receive time.

Reads records from a UDP port or serial port, extracts NMEA 0183 timestamps,
and reports the difference between the encoded time and the moment the record
was received. Useful for diagnosing end-to-end latency from a device to the
host that will be logging it.

Records may contain multiple NMEA sentences; each line is examined independently.

Usage:
    python nmea_lag.py --udp PORT [--quiet]
    python nmea_lag.py --serial DEVICE [--baud RATE] [--quiet]

Dependencies:
    stdlib only for UDP mode.
    pyserial (pip install pyserial) required for --serial mode.

Output columns (tab-separated):
    encoded     UTC time encoded in the NMEA sentence
    system      UTC time the record was received by this script
    delta       (system - encoded) seconds; positive = lag
    sentence    the raw NMEA sentence the timestamp was taken from
"""

import argparse
import datetime
import re
import socket
import sys

# pyserial is only needed for --serial mode
_serial = None
try:
    import serial as _serial
except ImportError:
    pass


# ── NMEA timestamp parsing ─────────────────────────────────────────────────────

# NMEA time field: HHMMSS or HHMMSS.sss
_TIME_RE = re.compile(r'^(\d{2})(\d{2})(\d{2})(\.\d+)?$')

# Finds an NMEA sentence anywhere within a line (handles prefixed text/timestamps)
_NMEA_SEARCH_RE = re.compile(r'([\$!][A-Z]{2,5},[^\r\n]*)')

# Map of sentence formatter (last 3 chars of sentence ID) to the field index
# containing the time. Defaults to 1 if not listed here.
_TIME_FIELD = {
    'GLL': 5,   # $xxGLL,lat,N,lon,W,HHMMSS.ss,status
    'BWC': 1,   # keep explicit as a reminder; field 1 is time
}

# Formatters that carry a date field alongside the time
_DATE_IN_FIELD_9 = {'RMC'}           # DDMMYY in field 9  ($xxRMC all talkers)
_DATE_IN_FIELDS_234 = {'ZDA'}        # DD,MM,YYYY in fields 2-4 ($xxZDA all talkers)


def _parse_nmea_time_field(time_str):
    """Return (hour, minute, second, microsecond) from an NMEA time field, or None."""
    m = _TIME_RE.match(time_str)
    if not m:
        return None
    hh, mm, ss = int(m.group(1)), int(m.group(2)), int(m.group(3))
    us = round(float(m.group(4) or '0') * 1_000_000)
    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 60):
        return None
    return hh, mm, ss, us


def parse_nmea_datetime(fields, receive_utc):
    """
    Extract a UTC datetime from a parsed NMEA sentence's fields.

    fields       -- list of comma-split fields; fields[0] is the sentence ID
    receive_utc  -- datetime.datetime (UTC, aware) when the record arrived

    Returns a UTC-aware datetime, or None if no valid timestamp is found.
    """
    sentence_type = fields[0].lstrip('$!').upper()
    formatter = sentence_type[-3:]
    time_field_idx = _TIME_FIELD.get(formatter, 1)

    if len(fields) <= time_field_idx or not fields[time_field_idx]:
        return None

    t = _parse_nmea_time_field(fields[time_field_idx])
    if t is None:
        return None
    hh, mm, ss, us = t

    date = None

    if formatter in _DATE_IN_FIELD_9:
        if len(fields) > 9 and len(fields[9]) == 6:
            try:
                day   = int(fields[9][0:2])
                month = int(fields[9][2:4])
                year  = 2000 + int(fields[9][4:6])
                date  = datetime.date(year, month, day)
            except (ValueError, OverflowError):
                pass

    elif formatter in _DATE_IN_FIELDS_234:
        if len(fields) > 4:
            try:
                day   = int(fields[2])
                month = int(fields[3])
                year  = int(fields[4])
                date  = datetime.date(year, month, day)
            except (ValueError, OverflowError):
                pass

    if date is None:
        # Fall back to the receive date (UTC), handling midnight rollover
        date = receive_utc.date()
        if hh == 23 and receive_utc.hour == 0:
            date -= datetime.timedelta(days=1)   # sentence from just before midnight
        elif hh == 0 and receive_utc.hour == 23:
            date += datetime.timedelta(days=1)   # clock skew edge case

    try:
        return datetime.datetime(date.year, date.month, date.day,
                                 hh, mm, ss, us,
                                 tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


# ── Per-line processing ────────────────────────────────────────────────────────

def process_line(line, receive_utc, quiet):
    """
    Examine one line. If it contains an NMEA timestamp, print a result row.
    Without --quiet, lines with no timestamp are printed with a [no timestamp] note.
    """
    stripped = line.strip()
    if not stripped:
        return

    # Search for an NMEA sentence anywhere in the line — handles lines where
    # text (instrument prefix, host timestamp, etc.) precedes the sentence.
    m = _NMEA_SEARCH_RE.search(stripped)
    if not m:
        if not quiet:
            print(f'[no timestamp]\t{stripped}')
        return

    nmea_part = m.group(1)

    # Strip checksum (*XX) before splitting
    sentence_body = nmea_part[:nmea_part.rindex('*')] if '*' in nmea_part else nmea_part
    fields = sentence_body.split(',')

    nmea_dt = parse_nmea_datetime(fields, receive_utc)

    if nmea_dt is None:
        if not quiet:
            print(f'[no timestamp]\t{stripped}')
        return

    delta_s = (receive_utc - nmea_dt).total_seconds()
    enc_str = nmea_dt.strftime('%Y-%m-%d %H:%M:%S.%f')
    sys_str = receive_utc.strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f'encoded={enc_str}\tsystem={sys_str}\tdelta={delta_s:+.6f}\t{stripped}')


def process_record(record, receive_utc, quiet):
    """Split a potentially multi-line record and process each line."""
    for line in record.splitlines():
        process_line(line, receive_utc, quiet)


# ── Input readers ──────────────────────────────────────────────────────────────

def read_udp(port, quiet):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', port))
    print(f'Listening on UDP :{port} ...', file=sys.stderr)
    sys.stderr.flush()

    while True:
        data, _addr = sock.recvfrom(65535)
        receive_utc = datetime.datetime.now(datetime.timezone.utc)
        process_record(data.decode('utf-8', errors='replace'), receive_utc, quiet)


def read_serial(device, baud, quiet):
    if _serial is None:
        print('ERROR: pyserial is not installed. Run: pip install pyserial',
              file=sys.stderr)
        sys.exit(1)

    with _serial.Serial(device, baudrate=baud, timeout=1) as ser:
        print(f'Reading {device} at {baud} baud ...', file=sys.stderr)
        sys.stderr.flush()

        while True:
            raw = ser.readline()
            if not raw:
                continue
            receive_utc = datetime.datetime.now(datetime.timezone.utc)
            process_record(raw.decode('utf-8', errors='replace'), receive_utc, quiet)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Measure lag between NMEA device timestamps and system receive time.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument('--udp', type=int, metavar='PORT',
                     help='UDP port number to listen on')
    src.add_argument('--serial', metavar='DEVICE',
                     help='Serial device path (e.g. /dev/ttyUSB0)')

    parser.add_argument('--baud', type=int, default=4800,
                        help='Serial baud rate (default: 4800)')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress output for lines with no detectable timestamp')

    args = parser.parse_args()

    try:
        if args.udp is not None:
            read_udp(args.udp, args.quiet)
        else:
            read_serial(args.serial, args.baud, args.quiet)
    except KeyboardInterrupt:
        print('\nStopped.', file=sys.stderr)


if __name__ == '__main__':
    main()
