#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 23 23:45:59 2021

@author: nlourie
"""

import astropy.coordinates
import astropy.units as u


ra = '05:34:30.52'
dec = '22:00:59.9'

#ra = '5.575144444444444'
#dec = '22.016638888888888'

try:
    ra_obj = astropy.coordinates.Angle(ra, unit = u.hour)
    dec_obj = astropy.coordinates.Angle(dec, unit = u.deg)
    
    ra_hour = ra_obj.hour
    dec_deg = dec_obj.deg
except Exception as e:
    print(f'could not convert angles: {e}')
    
print(f'RA (hour) = {ra_hour}, DEC (deg) = {dec_deg}')

try:
    assert(False == True,'fart')
except Exception as e:
    print(f'Error: {e}')