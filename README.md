# NMEA-lag-test
Python code to read NMEA data from serial or UDP port and report the lag between encoded time and arrival.

We've discovered that some data acquisition devices and systems can have substantial lag between the moment
when the measurement is taken and when it becomes available for external timestamping, storage or processing.
(https://tinyurl.com/cohn-race-gps-timestamps). This can lead to undetected data skew.

The Python script in this repository is a tool to help detect such situations: it reads NMEA data from a
specified serial or UDP port and tries to parse it for an encoded timestamp. It compares that timestamp to
the system clock and reports on any lag.
