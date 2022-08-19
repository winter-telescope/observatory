#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 15 13:52:18 2022

@author: winter
"""
import astropy.units as u
import astropy.coordinates
from datetime import datetime
import pytz

config = dict({'site':
                {
                    # lat/lon. expects a format that can be read with astropy.coordinates.Angle()
                    'lat': '33d21m21.6s',
                    'lon': '-116d51m46.8s',
                    # height (site altitude). height is a number, units are something that can be parsed with astropy.units.Unit()
                    'height': 1706,
                    'height_units': 'm',
                    'timezone': 'America/Los_Angeles',
                }})


#obj = 'ngc3031'

obj = 'm1'

print(f'Converting Palomar Time --> MJD')
times_local_str = ['2022-08-16 21:30:00', '2022-8-19 08:00:00']

times_mjd = []

times_datetime_local = []
times_astropy = []
times_local_str_check = []
times_utc_str_check = []

for timestr in times_local_str:
    fmt = '%Y-%m-%d %H:%M:%S'
    
    datetime_obj_without_timezone = datetime.strptime(timestr, fmt)
    
    datetime_obj_with_timezone = pytz.timezone('America/Los_Angeles').localize(datetime_obj_without_timezone)
    t_datetime_obj_utc = datetime_obj_with_timezone.astimezone(pytz.utc)
    times_datetime_local.append(datetime_obj_with_timezone)
    
    times_local_str_check.append(datetime_obj_with_timezone.strftime(fmt))
    times_utc_str_check.append(t_datetime_obj_utc.strftime(fmt))
    
    astropy_obj = astropy.time.Time(datetime_obj_with_timezone, format = 'datetime')
    times_astropy.append(astropy_obj)
    
    mjd = astropy_obj.mjd
    
    times_mjd.append(mjd)


print(f'Local Times: {times_local_str} (Original Times from Strings)')

print(f'Local Times: {times_local_str_check} (Imported and Converted through datetime)')
print(f'UTC Times:   {times_utc_str_check} (Imported and Converted through datetime)')

print(f'MJD:         {times_mjd}')

print()
print(f'Converting UTC --> MJD')
"""
times_local_str = '2022-08-15 20:00:00'


fmt = '%Y-%m-%d %H:%M:%S'

datetime_obj_without_timezone = datetime.strptime(times_local_str, fmt)

datetime_obj_with_timezone = pytz.timezone(config['site']['timezone']).localize(datetime_obj_without_timezone)
times_datetime_local = datetime_obj_with_timezone

times_local_str_check = datetime_obj_with_timezone.strftime(fmt)

astropy_obj = astropy.time.Time(datetime_obj_with_timezone, format = 'datetime')
times_astropy = astropy_obj

mjd = astropy_obj.mjd

print(f'Converting Palomar Time --> MJD')

print(f'\tLocal Time: {times_local_str} (Original Times from Strings)')

print(f'\tLocal Time: {times_local_str_check} (Imported and Converted through datetime)')

print(f'\tMJD: {mjd}')

print()
"""

lat = astropy.coordinates.Angle(config['site']['lat'])
lon = astropy.coordinates.Angle(config['site']['lon'])
height = config['site']['height'] * u.Unit(config['site']['height_units'])
site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)

j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame = 'icrs')
target_ra_j2000_hours = j2000_coords.ra.hour
target_dec_j2000_deg = j2000_coords.dec.deg
ra_deg = j2000_coords.ra.deg


site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)

obstime = times_astropy[0]

                                
frame = astropy.coordinates.AltAz(obstime = obstime, location = site)
local_coords = j2000_coords.transform_to(frame)
target_alt = local_coords.alt.deg
target_az = local_coords.az.deg

print(f'Target Name = {obj}')
print(f'Catalog Coords:')
print(f'\tRA  = {j2000_coords.ra.to_string(unit = "hour", precision = 1)}')
print(f'\tDec = {j2000_coords.dec.to_string(unit = "deg", precision = 1)}')
print(f'Degree Coords for WSP:')
print(f'\tRA  = {j2000_coords.ra.deg:>10.6f} deg')
print(f'\tDec = {j2000_coords.dec.deg:>10.6f} deg')
print(f'Telescope Coords:')
print(f'\tAlt = {target_alt:>10.3f} deg')
print(f'\tAz  = {target_az:>10.3f} deg')


# plot the altitude over the full range of times allowed
