#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 21 17:15:14 2022

@author: nlourie
"""

import pytz
from datetime import datetime
import astropy.time
import astropy.coordinates
import astropy.units as u

print(f'Converting Palomar Time --> MJD')
times_local_str = ['2022-01-21 21:08:00', '2022-01-21 23:29:00','2022-01-22 01:49:00']

times_mjd = []

times_datetime_local = []
times_astropy = []
times_local_str_check = []

for timestr in times_local_str:
    fmt = '%Y-%m-%d %H:%M:%S'
    
    datetime_obj_without_timezone = datetime.strptime(timestr, fmt)
    
    datetime_obj_with_timezone = pytz.timezone('America/Los_Angeles').localize(datetime_obj_without_timezone)
    times_datetime_local.append(datetime_obj_with_timezone)
    
    times_local_str_check.append(datetime_obj_with_timezone.strftime(fmt))
    
    astropy_obj = astropy.time.Time(datetime_obj_with_timezone, format = 'datetime')
    times_astropy.append(astropy_obj)
    
    mjd = astropy_obj.mjd
    
    times_mjd.append(mjd)


print(f'Local Times: {times_local_str} (Original Times from Strings)')

print(f'Local Times: {times_local_str_check} (Imported and Converted through datetime)')

print(f'MJD:         {times_mjd}')

print()
print(f'Converting UTC --> MJD')
# doing it all in UTC
times_utc = ['2022-01-22 05:08:00', '2022-01-22 09:49:00']
times_datetime = []
times_mjd = []
times_str = []
times_astropy = []

for timestr in times_utc:
    fmt = '%Y-%m-%d %H:%M:%S'
    
    datetime_obj = datetime.strptime(timestr, fmt)
    
    datetime_obj = pytz.utc.localize(datetime_obj)
    times_datetime.append(datetime_obj)
    times_str.append(datetime_obj.strftime(fmt))

    astropy_obj = astropy.time.Time(datetime_obj, format = 'datetime')
    times_astropy.append(astropy_obj)
    
    mjd = astropy_obj.mjd
    
    times_mjd.append(mjd)


print(f'Times UTC:   {times_utc} (Original Times from Strings)')

print(f'Times UTC:   {times_str} (Imported and Converted through datetime)')
 
print(f'MJD:         {times_mjd}')


ra_hour_str = '07:48:06.47'
dec_deg_str = '+50:13:32.9'
j2000_ra_scheduled = astropy.coordinates.Angle(ra_hour_str, unit = u.hour)
j2000_dec_scheduled = astropy.coordinates.Angle(dec_deg_str, unit = u.deg)


ra_radians_scheduled  = j2000_ra_scheduled.radian
dec_radians_scheduled = j2000_dec_scheduled.radian

ra_deg_nominal = 117.02696
dec_deg_nominal = 50.22581

ra_deg_scheduled = j2000_ra_scheduled.deg
dec_deg_scheduled = j2000_dec_scheduled.deg

print()
print('Getting RA/DEC in Radians')
print(f'(RA hour, Dec deg)        = ({ra_hour_str}, {dec_deg_str})')
print(f'Nominal (RA deg, Dec deg) = ({ra_deg_nominal}, {dec_deg_nominal})')
print(f'Calc (RA deg, Dec deg)    = ({ra_deg_scheduled:.5f}, {dec_deg_scheduled:.5f})')
print(f'Calc (RA rad, Dec rad)    = ({ra_radians_scheduled}, {dec_radians_scheduled})')