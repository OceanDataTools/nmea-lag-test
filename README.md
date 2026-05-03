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

Sample usage and output:
```
>  python nmea_lag.py --serial /dev/ttyS0 --baud 4800
encoded=2026-05-03 22:40:18.000000	system=2026-05-03 22:40:18.256555	delta=+0.256555	$GPGGA,224018.00000,5101.901678,N,09418.211929,W,5,22,0.9,15.2,M,-17.5,M,,*56
[no timestamp]	$GPVTG,44.76,T,,M,10.00,N,18.52,K,D*06
encoded=2026-05-03 22:40:18.000000	system=2026-05-03 22:40:18.313671	delta=+0.313671	$GPGLL,5101.901678,N,09418.211929,W,224018.00000,A,D*43
encoded=2026-05-03 22:40:18.000000	system=2026-05-03 22:40:18.394695	delta=+0.394695	$GPRMC,224018.00000,A,5101.901678,N,09418.211929,W,10.00,44.76,030526,,D*5A
encoded=2026-05-03 22:40:18.000000	system=2026-05-03 22:40:18.435101	delta=+0.435101	$GPZDA,224018.00000,03,05,2026,,*5B
encoded=2026-05-03 22:40:19.000000	system=2026-05-03 22:40:19.257594	delta=+0.257594	$GPGGA,224019.00000,5101.903649,N,09418.208822,W,5,22,0.9,15.2,M,-17.5,M,,*55
[no timestamp]	$GPVTG,44.91,T,,M,10.00,N,18.52,K,D*0F
encoded=2026-05-03 22:40:19.000000	system=2026-05-03 22:40:19.318713	delta=+0.318713	$GPGLL,5101.903649,N,09418.208822,W,224019.00000,A,D*40
encoded=2026-05-03 22:40:19.000000	system=2026-05-03 22:40:19.402179	delta=+0.402179	$GPRMC,224019.00000,A,5101.903649,N,09418.208822,W,10.00,44.91,030526,,D*50

```
