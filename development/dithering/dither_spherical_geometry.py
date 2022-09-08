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


ra0_j2000_hours = 5
dec0_j2000_deg = 33

#axis = 'dec'
#arcsec = 10

ra_arcsec = 30
dec_arcsec = 40


print()
print('no spherical geometry method:')
"""
if axis == 'ra':
    delta_ra_hours = (arcsec * (1/60.0/60.0) * (24/360.0))
    delta_dec_deg = 0.0
elif axis == 'dec':
    delta_ra_hours = 0.0
    delta_dec_deg = (arcsec/60.0/60.0)
"""
delta_ra_hours = (ra_arcsec * (1/60.0/60.0) * (24/360.0))
delta_dec_deg = (dec_arcsec/60.0/60.0)

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

# calc dist with astropy
start = astropy.coordinates.SkyCoord(ra = ra0_j2000_hours*u.hour, dec = dec0_j2000_deg*u.deg)
end = astropy.coordinates.SkyCoord(ra = ra_j2000_hours_goal*u.hour, dec = dec_j2000_deg_goal*u.deg)
sep = start.separation(end)
print(f'separation = {sep.arcsecond:0.3f} arcsec')

#%%
print()
print('spherical geometry approximation method:')

ra0_j2000 = astropy.coordinates.Angle(ra0_j2000_hours*u.hourangle)
dec0_j2000 = astropy.coordinates.Angle(dec0_j2000_deg*u.deg)
"""
if axis == 'ra':
    #delta_ra = arcsec * u.arcsecond
    delta_ra = delta_ra_hours*u.hourangle/np.cos(dec0_j2000.radian)
    delta_dec = 0.0
elif axis == 'dec':
    delta_ra = 0.0
    #delta_dec = arcsec * u.arcsecond
    delta_dec = delta_dec_deg*u.deg
        #print(f'delta_ra = {delta_ra_hours} hours, delta_dec = {delta_dec_deg}')
"""
delta_ra = delta_ra_hours*u.hourangle/np.cos(dec0_j2000.radian)
delta_dec = delta_dec_deg*u.deg


ra_j2000_goal = ra0_j2000 + delta_ra
dec_j2000_goal = dec0_j2000 +  delta_dec
        
ra_dist_arcsec = abs((ra0_j2000 - ra_j2000_goal).arcsecond)

dec_dist_arcsec = abs((dec0_j2000 - dec_j2000_goal).arcsecond)
print(f'ra dist to target = {ra_dist_arcsec:.2f} arcsec')
print(f'dec dist to target = {dec_dist_arcsec:.2f} arcsec')
print(f'ra: {ra0_j2000.hour} --> {ra_j2000_goal.hour} (hour)')
print(f'dec: {dec0_j2000.deg} --> {dec_j2000_goal.deg} (deg)')

# calc dist with astropy
start = astropy.coordinates.SkyCoord(ra = ra0_j2000_hours*u.hour, dec = dec0_j2000_deg*u.deg)
end = astropy.coordinates.SkyCoord(ra = ra_j2000_hours_goal*u.hour, dec = dec_j2000_deg_goal*u.deg)
sep = start.separation(end)
print(f'separation = {sep.arcsecond:0.3f} arcsec')

#%%
print()
print('astropy offset method')
start = astropy.coordinates.SkyCoord(ra = ra0_j2000_hours*u.hour, dec = dec0_j2000_deg*u.deg)
ra0_j2000 = start.ra
dec0_j2000 = start.dec
"""
if axis == 'ra':
    offset_ra = arcsec*u.arcsecond
    offset_dec = 0.0 * u.arcsecond
elif axis == 'dec':
    offset_ra = 0.0 * u.arcsecond
    offset_dec = arcsec * u.arcsecond
"""    
offset_ra = ra_arcsec*u.arcsecond
offset_dec = dec_arcsec * u.arcsecond

end = start.spherical_offsets_by(offset_ra, offset_dec)
ra_j2000_goal = end.ra
dec_j2000_goal = end.dec
print(f'ra dist to target = {ra_dist_arcsec:.2f} arcsec')
print(f'dec dist to target = {dec_dist_arcsec:.2f} arcsec')
print(f'ra: {ra0_j2000.hour} --> {ra_j2000_goal.hour} (hour)')
print(f'dec: {dec0_j2000.deg} --> {dec_j2000_goal.deg} (deg)')


sep = start.separation(end)
print(f'separation = {sep.arcsecond:0.3f} arcsec')

#%% 
print()
print('sandbox:')
ra_dist_arcsec = 30
dec_dist_arcsec = 40

start = astropy.coordinates.SkyCoord(ra = ra0_j2000_hours*u.hour, dec = dec0_j2000_deg*u.deg)

offset_ra = ra_dist_arcsec *u.arcsecond
offset_dec = dec_dist_arcsec * u.arcsecond
end = start.spherical_offsets_by(offset_ra, offset_dec)
ra_j2000_goal = end.ra
dec_j2000_goal = end.dec

# calculate the literal difference required by PWI4 mount_offset
ra_delta_arcsec = end.ra.arcsecond - start.ra.arcsecond
dec_delta_arcsec = end.dec.arcsecond - start.dec.arcsecond

sep = start.separation(end)
print(f' actual angular distance to move:')
print(f' \tra dist to target  = {ra_dist_arcsec:.2f} arcsec')
print(f' \tdec dist to target = {dec_dist_arcsec:.2f} arcsec')

print(f' literal differences to pass to PWI4 mount_offset')
print(f' \tra delta  = {ra_delta_arcsec:>10.6f} arcsec')
print(f' \tdec delta = {dec_delta_arcsec:>10.6f} arcsec')

print(f' RA/Dec Coords: Start --> Finish')
print(f' \tra : {ra0_j2000.hour:>10.6f} --> {ra_j2000_goal.hour:>10.6f} (hour)')
print(f' \tdec: {dec0_j2000.deg:>10.6f} --> {dec_j2000_goal.deg:>10.6f} (deg)')
print(f' \tseparation = {sep.arcsecond:0.6f} arcsec')


# calc dist between two points
a = astropy.coordinates.SkyCoord(ra = 5.320000*u.hour, dec = 46.000006*u.deg)
b = astropy.coordinates.SkyCoord(ra = 5.320797*u.hour, dec = 46.011138*u.deg)
sep_ab = a.separation(b)
print()
print(f'check dist btwn two coords')
print(f' RA/Dec Coords: Start --> Finish')
print(f' \tra : {a.ra.hour:>10.6f} --> {b.ra.hour:>10.6f} (hour)')
print(f' \tdec: {a.dec.deg:>10.6f} --> {b.dec.deg:>10.6f} (deg)')
print(f' \tseparation = {sep.arcsecond:0.6f} arcsec')

print()
#%% get distances for a random dither

dither_step_size = 7.5
#ra_dist_arcsec, dec_dist_arcsec = np.random.uniform(-dither_step_size, dither_step_size, 2)
ra_dist_arcsec = 0
dec_dist_arcsec = 60

start = astropy.coordinates.SkyCoord(ra = ra0_j2000_hours*u.hour, dec = dec0_j2000_deg*u.deg)

offset_ra = ra_dist_arcsec *u.arcsecond
offset_dec = dec_dist_arcsec * u.arcsecond
end = start.spherical_offsets_by(offset_ra, offset_dec)
ra_j2000_goal = end.ra
dec_j2000_goal = end.dec

# calculate the literal difference required by PWI4 mount_offset
ra_delta_arcsec = end.ra.arcsecond - start.ra.arcsecond
dec_delta_arcsec = end.dec.arcsecond - start.dec.arcsecond

sep = start.separation(end)



print(f'Random Dither, dither step size = {dither_step_size}')
print(f' Original Pointing: ')
print(f' \tRA0 = {ra0_j2000_hours:>10.6f} h')
print(f' \tDec0 = {dec0_j2000_deg:>10.6f} deg')

print(f' actual angular distance to move:')
print(f' \tRA dist to target  = {ra_dist_arcsec:.2f} arcsec')
print(f' \tDec dist to target = {dec_dist_arcsec:.2f} arcsec')

print(f' literal differences to pass to PWI4 mount_offset')
print(f' \tRA delta   = {ra_delta_arcsec:>10.6f} arcsec ({ra_delta_arcsec/60.0:>6.3f} arcmin)')
print(f' \tDec delta = {dec_delta_arcsec:>10.6f} arcsec ({dec_delta_arcsec/60.0:>6.3f} arcmin)')

print(f' RA/Dec Coords: Start --> Finish')
print(f' \tRA : {ra0_j2000.hour:>10.6f} --> {ra_j2000_goal.hour:>10.6f} (hour)')
print(f' \tDec: {dec0_j2000.deg:>10.6f} --> {dec_j2000_goal.deg:>10.6f} (deg)')
print(f' \tseparation = {sep.arcsecond:0.6f} arcsec')



    
# recover the original pointing using just the current ra/dec and the PWI4 offsets
ra_cur = ra_j2000_goal.hour
dec_cur = dec_j2000_goal.deg
pwi4_offset_ra = ra_delta_arcsec
pwi4_offset_dec = dec_delta_arcsec


ra_center = ra_cur - pwi4_offset_ra*(1/3600)*(24/360)
dec_center = dec_cur - pwi4_offset_dec*(1/3600)



print(f' Recovered Central Pointing')
print(f' \tRA0 = {ra_center:>10.6f}')
print(f' \tDec0 = {dec_center:>10.6f}')
    
