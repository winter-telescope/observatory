#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 28 18:21:05 2021

Get the sun's altitude using astropy.

Following the examples on astropy's documentation


@author: nlourie
"""


import astropy.coordinates
import astropy.units as u
from datetime import datetime
import json

#palomar = astropy.coordinates.EarthLocation.of_site('Palomar')

#lat = astropy.coordinates.Latitude(angle = (33, 21, 21.6), unit = u.deg)
#lon = astropy.coordinates.Longitude(angle = (-116, 51, 46.8), unit = u.deg)
#lat = astropy.coordinates.Angle('33d21m21.6s')
#lon = astropy.coordinates.Angle('-116d51m46.8s')

lat = astropy.coordinates.Angle('33d21m22s')
lon = astropy.coordinates.Angle('-116d51m47s')

height = 1706 * u.m
palomar = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
# this gives the same result as using the of_site('Palomar') definition

now_datetime = datetime.utcnow()

now = astropy.time.Time(now_datetime, format = 'datetime')


frame = astropy.coordinates.AltAz(obstime = now, location = palomar)

sunloc = astropy.coordinates.get_sun(now)

sun_coords = sunloc.transform_to(frame)

sunalt = sun_coords.alt.value

print(f'sun alt = {sunalt} deg')

finish = datetime.utcnow()
dt_ms = (finish.timestamp() - now_datetime.timestamp())*1000
print(f'dt = {dt_ms} ms')

#%%

body = 'Venus'
body_loc = astropy.coordinates.get_body(body, time = now, location = palomar)
body_coords = body_loc.transform_to(frame)
body_alt = body_coords.alt
body_az = body_coords.az
body_ra = body_loc.ra
body_dec = body_loc.dec

print(f'{body} Location:')
print(f'ra = {body_ra.to_string(unit = u.hour, sep = " ")}')
print(f'dec = {body_dec.to_string(unit = u.degree, sep = " ")}')
print()
print(f'alt = {body_alt.to_string(unit = u.degree, sep = " ")}')
print(f'az = {body_az.to_string(unit = u.degree, sep = " ")}')
print()

"""current_alt = 24.0
current_az = 271

print(f'current_alt = {current_alt:0.2f}')
print(f'body_alt = {body_alt.deg:0.2f}')
print()
print(f'current az = {current_az:0.2f}')
print(f'body_az = {body_az.deg:0.2f}')
print()
print(f'dist to body = {dist:0.2f} deg')"""

#%%
deg = str
def bodyTargetDist(target_alt: deg, target_az: deg, body: str):
    
    if not body.lower() in astropy.coordinates.solar_system_ephemeris.bodies:
        raise IOError(f'body "{body}" not in ephemeris catalog')
    
    
    body_loc = astropy.coordinates.get_body(body, time = now, location = palomar)
    body_coords = body_loc.transform_to(frame)
    body_alt = body_coords.alt
    body_az = body_coords.az
    
    dist = ((target_az - body_az.deg)**2 + (target_alt - body_alt.deg)**2)**0.5
    return dist

def getObjectAltAz(obj):

    j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame = 'icrs')
    #j2000_ra_hours = j2000_coords.ra.hour
    #j2000_dec_deg = j2000_coords.dec.deg
    
    obstime = astropy.time.Time(datetime.utcnow())
    
    frame = astropy.coordinates.AltAz(obstime = obstime, location = palomar)
    local_coords = j2000_coords.transform_to(frame)
    local_alt_deg = local_coords.alt.deg
    local_az_deg = local_coords.az.deg
    return local_alt_deg, local_az_deg

#current_alt = 24.0
#current_az = 271

bodies = ['sun', 'moon', 'fart', 'Venus', 'mars', 'jupiter', 'saturn']
target = 'M31'

target_alt, target_az = getObjectAltAz(target)
dist_dict = {}

for body in bodies:
    try:
        dist = bodyTargetDist(target_alt, target_az, body)
        dist_dict.update({body : dist})
    except Exception as e:
        print(e)

print(f'target_alt = {target_alt:0.2f}')
print(f'target_az = {target_az:0.2f}')

print('Target Distances to Ephem:')
print(json.dumps(dist_dict, indent = 2))
    
    
    

