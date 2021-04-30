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

#palomar = astropy.coordinates.EarthLocation.of_site('Palomar')

#lat = astropy.coordinates.Latitude(angle = (33, 21, 21.6), unit = u.deg)
#lon = astropy.coordinates.Longitude(angle = (-116, 51, 46.8), unit = u.deg)
lat = astropy.coordinates.Angle('33d21m21.6s')
lon = astropy.coordinates.Angle('-116d51m46.8s')
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