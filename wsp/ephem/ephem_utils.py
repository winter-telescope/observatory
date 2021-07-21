#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 20 21:36:01 2021

EPHEM UTILS

These are various functions and transformations that get called throughout
the code having to do with the sky coordinates and such


@author: winter
"""

from datetime import datetime
import astropy.coordinates

def getTargetEphemDist_AltAz( target_alt, target_az, body, location, obstime = 'now', time_format = 'datetime'):
    # get the current distance in degrees from the target (alt/az in deg) to the specified ephemeris body
    
    if not body.lower() in astropy.coordinates.solar_system_ephemeris.bodies:
       raise IOError(f'body "{body}" not in ephemeris catalog')
    
    if obstime == 'now':
        obstime = datetime.utcnow()
    
    obstime = astropy.time.Time(obstime, format = time_format)
    
    frame = astropy.coordinates.AltAz(obstime = obstime, location = location)
    
    body_loc = astropy.coordinates.get_body(body, time = obstime, location = location)
    body_coords = body_loc.transform_to(frame)
    body_alt = body_coords.alt
    body_az = body_coords.az
    
    dist = ((target_az - body_az.deg)**2 + (target_alt - body_alt.deg)**2)**0.5
    return dist
    
    
def getTargetEphemDist_J200radec( target_ra, target_dec, body, location, obstime = 'now', time_format = 'datetime'):
    # takes ra and dec in as astropy.coordinate.Angle objects
    if not ((type(target_ra) is astropy.coordinates.Angle) & (type(target_dec) is astropy.coordinates.Angle)):
        raise TypeError(f'target RA and DEC must both be astropy.coordinate.Angle objects')
        
    if obstime == 'now':
        obstime = datetime.utcnow()
    
    obstime = astropy.time.Time(obstime, format = time_format)
    j2000_coords = astropy.coordinates.SkyCoord(ra = target_ra, dec = target_dec, frame = 'icrs')
    frame = astropy.coordinates.AltAz(obstime = obstime, location = location)
    local_coords = j2000_coords.transform_to(frame)
    local_alt_deg = local_coords.alt.deg
    local_az_deg = local_coords.az.deg
    
    # Now calculate the dist to the target
    dist = getTargetEphemDist_AltAz(local_alt_deg, local_az_deg, body, obstime = obstime, time_format = time_format)
    return dist

