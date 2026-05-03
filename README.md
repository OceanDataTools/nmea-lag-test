# NMEA-lag-test
Python code to read NMEA data from serial or UDP port and report the lag between encoded time and arrival.

We've discovered that some data acquisition devices and systems can have substantial lag between the moment
when the measurement is taken and when it becomes available for external timestamping, storage or processing.
(https://tinyurl.com/cohn-race-gps-timestamps). This can lead to undetected data skew.

The Python script in this repository is a tool to help detect such situations: it reads NMEA data from a
specified serial or UDP port and tries to parse it for an encoded timestamp. It compares that timestamp to
the system clock and reports on any lag.

```
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
```
