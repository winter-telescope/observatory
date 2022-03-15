#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 15 10:36:43 2022

@author: nlourie
"""

import astropy.coordinates
import astropy.units as u
import numpy as np
"""
ra_str = '17h35m20.0s'
dec_str = '76d31m37.3s'

ra = astropy.coordinates.Angle(ra_str)
dec = astropy.coordinates.Angle(dec_str)

ra0_j2000_hours = ra.hour
dec0_j2000_deg = dec.deg
"""

ra0_j2000_hours = 14.623094
dec0_j2000_deg = -2.1017299

axis = 'ra'
arcsec = 10

print()
print('no spherical geometry method:')

if axis == 'ra':
    delta_ra_hours = (arcsec * (1/60.0/60.0) * (24/360.0))
    delta_dec_deg = 0.0
elif axis == 'dec':
    delta_ra_hours = 0.0
    delta_dec_deg = (arcsec/60.0/60.0)

        #print(f'delta_ra = {delta_ra_hours} hours, delta_dec = {delta_dec_deg}')
ra_j2000_hours_goal = ra0_j2000_hours + delta_ra_hours
dec_j2000_deg_goal = dec0_j2000_deg + delta_dec_deg
        
ra_dist_hours = abs(ra0_j2000_hours - ra_j2000_hours_goal)
ra_dist_arcsec = ra_dist_hours * (360/24.0) * 3600.0

dec_dist_deg = abs(dec0_j2000_deg - dec_j2000_deg_goal)
dec_dist_arcsec = dec_dist_deg * 3600.0
print(f'ra dist to target = {ra_dist_arcsec:.2f} arcsec')
print(f'dec dist to target = {dec_dist_arcsec:.2f} arcsec')
print(f'ra: {ra0_j2000_hours} --> {ra_j2000_hours_goal} (hour)')
print(f'dec: {dec0_j2000_deg} --> {dec_j2000_deg_goal} (deg)')

#%%
print()
print('spherical geometry approximation method:')

ra0_j2000 = astropy.coordinates.Angle(ra0_j2000_hours*u.hourangle)
dec0_j2000 = astropy.coordinates.Angle(dec0_j2000_deg*u.deg)

if axis == 'ra':
    #delta_ra = arcsec * u.arcsecond
    delta_ra = delta_ra_hours*u.hourangle/np.cos(dec0_j2000.radian)
    delta_dec = 0.0
elif axis == 'dec':
    delta_ra = 0.0
    #delta_dec = arcsec * u.arcsecond
    delta_dec = delta_dec_deg*u.deg
        #print(f'delta_ra = {delta_ra_hours} hours, delta_dec = {delta_dec_deg}')


ra_j2000_goal = ra0_j2000 + delta_ra
dec_j2000_goal = dec0_j2000 +  delta_dec
        
ra_dist_arcsec = abs((ra0_j2000 - ra_j2000_goal).arcsecond)

dec_dist_arcsec = abs((dec0_j2000 - dec_j2000_goal).arcsecond)
print(f'ra dist to target = {ra_dist_arcsec:.2f} arcsec')
print(f'dec dist to target = {dec_dist_arcsec:.2f} arcsec')
print(f'ra: {ra0_j2000.hour} --> {ra_j2000_goal.hour} (hour)')
print(f'dec: {dec0_j2000.deg} --> {dec_j2000_goal.deg} (deg)')

#%%
print()
print('astropy offset method')
start = astropy.coordinates.SkyCoord(ra = ra0_j2000_hours*u.hour, dec = dec0_j2000_deg*u.deg)
ra0_j2000 = start.ra
dec0_j2000 = start.dec

if axis == 'ra':
    offset_ra = arcsec*u.arcsecond
    offset_dec = 0.0 * u.arcsecond
elif axis == 'dec':
    offset_ra = 0.0 * u.arcsecond
    offset_dec = arcsec * u.arcsecond
    
end = start.spherical_offsets_by(offset_ra, offset_dec)
ra_j2000_goal = end.ra
dec_j2000_goal = end.dec
print(f'ra dist to target = {ra_dist_arcsec:.2f} arcsec')
print(f'dec dist to target = {dec_dist_arcsec:.2f} arcsec')
print(f'ra: {ra0_j2000.hour} --> {ra_j2000_goal.hour} (hour)')
print(f'dec: {dec0_j2000.deg} --> {dec_j2000_goal.deg} (deg)')


#%% Check

ra_end_hour = 14.623278
dec_end_deg = -2.1017589

