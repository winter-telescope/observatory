#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 15 09:33:50 2020


converting MJD to datetime with astropy

@author: nlourie
"""

import astropy.time
from datetime import datetime

t = 59341.1489157446

t_obj = astropy.time.Time(t,format = 'mjd')

t_datetime_obj = t_obj.datetime

timestamp_from_mjd = t_datetime_obj.timestamp()

print(f'The MJD is:           {t}')
print(f'The UTC time is:      {t_datetime_obj.strftime("%Y-%m-%d %H:%M:%S.%f")} UTC')
print(f'The UTC timestamp is: {timestamp_from_mjd}')


# go from datetime to MJD

utc_time = '2021-05-07 03:34:26.320'
dt_obj = datetime.strptime(utc_time, "%Y-%m-%d %H:%M:%S.%f")
T = astropy.time.Time(dt_obj, format = 'datetime')
timestamp_from_datetime = dt_obj.timestamp()
t_mjd = T.mjd
print()

print(f'The UTC timestamp is: {timestamp_from_datetime}')
print(f'The UTC time is:      {dt_obj.strftime("%Y-%m-%d %H:%M:%S.%f")} UTC')
print(f'The MJD is:           {t_mjd}')

assert abs(timestamp_from_mjd - timestamp_from_datetime) < 1e-3