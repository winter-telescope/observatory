#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 10 12:28:25 2021

@author: nlourie
"""

import astropy.coordinates
import astropy.time
import astropy.units as u
from datetime import datetime

obj = 'antares'

j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame = 'icrs')

j2000_ra_hours = j2000_coords.ra.hour
j2000_dec_deg = j2000_coords.dec.deg

obstime = 'now'
                                
palomar = astropy.coordinates.EarthLocation.of_site('palomar')
# this gives the same result as using the of_site('Palomar') definition

if obstime == 'now':
    obstime = datetime.utcnow()

obstime = astropy.time.Time(obstime, format = 'datetime')


frame = astropy.coordinates.AltAz(obstime = obstime, location = palomar)

#sunloc = astropy.coordinates.get_sun(obstime)

local_coords = j2000_coords.transform_to(frame)
local_alt_deg = local_coords.alt.deg
local_az_deg = local_coords.az.deg

print(f'Position of Sky Object: {obj}')
print(f'\t J2000: RA  = {j2000_ra_hours:0.3f} h, \t\t DEC = {j2000_dec_deg:0.3f} deg')
print(f'\t Local: Alt = {local_alt_deg:0.3f} deg, \t Az  = {local_az_deg:0.3f} deg')
print(f"RA  h:m:s = {j2000_coords.ra.to_string(u.hour, sep = ':')}")
print(f"Dec d:m:s = {j2000_coords.dec.to_string(u.deg, sep = ':')}")

#%%
# go from local to sky coords



az = astropy.coordinates.Angle(260*u.deg)
alt = astropy.coordinates.Angle(75*u.deg)

#altaz = astropy.coordinates.AltAz(alt = alt, az = az, obstime = obstime, location = palomar)
# Convert back to ICRS to make sure round-tripping is OK
#icrs2 = altaz.transform_to(astropy)
#print('RA = {pos.ra.deg:10.5f}, DEC = {pos.dec.deg:10.5f}'.format(pos=icrs2))
altaz = astropy.coordinates.SkyCoord(alt = alt, az = az, location = palomar, obstime = obstime, frame = 'altaz')
j2000 = altaz.transform_to('icrs')