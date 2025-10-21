#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 11 16:28:33 2023

@author: winter
"""
import os
import sys
from datetime import datetime

import astropy.coordinates
import astropy.units as u
import numpy as np
import yaml

config = dict({'site': {
                   # lat/lon. expects a format that can be read with astropy.coordinates.Angle()
                   'lat' : '33d21m21.6s',
                   'lon' : '-116d51m46.8s',
                   # height (site altitude). height is a number, units are something that can be parsed with astropy.units.Unit()
                   'height' : 1706,
                   'height_units': 'm',
                   'timezone' : 'America/Los_Angeles'},
    
                'telescope' : {
                    'host': 'thor',
                    'simhost': '192.168.1.106',
                    'port': 8220,
                    'home_alt_degs': 45.0,
                    'home_az_degs': 0,
                    'min_alt': 30,
                    'max_alt': 85.0,
                    'rotator': 
                        {'winter': {
                            'rotator_field_angle_zeropoint': 155.0,
                            'rotator_home_degs': 65.5,
                            'rotator_max_degs': 120.0,
                            'rotator_min_degs': -50.0},
                         'summer': { 
                             'rotator_field_angle_zeropoint': 155.0,
                             'rotator_home_degs': -25.0,
                             'rotator_max_degs': 160.0,
                             'rotator_min_degs': -120.0}
                         }
                        }
        })


camname = 'summer'


obj = 'm37'
j2000_coords = astropy.coordinates.SkyCoord.from_name(obj, frame = 'icrs')

ra, dec = "5:52:17.76", "32:32:42.0"
ra_hours = astropy.coordinates.Angle(ra, unit=u.hour)
dec_deg = astropy.coordinates.Angle(dec, unit=u.deg)
j2000_coords = astropy.coordinates.SkyCoord(ra_hours, dec_deg, frame='icrs')
        
target_ra_j2000_hours = j2000_coords.ra.hour
target_dec_j2000_deg = j2000_coords.dec.deg
ra_deg = j2000_coords.ra.deg




lat = astropy.coordinates.Angle(config['site']['lat'])
lon = astropy.coordinates.Angle(config['site']['lon'])
height = config['site']['height'] * u.Unit(config['site']['height_units'])
                                
site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)

obstime = astropy.time.Time(datetime.utcnow(),\
                            location=site)

frame = astropy.coordinates.AltAz(obstime = obstime, location = site)
local_coords = j2000_coords.transform_to(frame)
target_alt = local_coords.alt.deg
target_az = local_coords.az.deg

msg = f'Doing observation of {obj} @ (RA, DEC) = ({target_ra_j2000_hours:0.2f}, {target_dec_j2000_deg:0.2f})'
msg+= f', (Alt, Az) = ({target_alt:0.2f}, {target_az:0.2f})'
print(msg)


# handle the field angle
target_field_angle = config['telescope']['rotator'][camname]['rotator_field_angle_zeropoint']

lat = astropy.coordinates.Angle(config['site']['lat']).rad
dec = target_dec_j2000_deg*np.pi/180.0
lst = obstime.sidereal_time('mean').rad
hour_angle = lst - ra_deg*np.pi/180.0
if (hour_angle < -1*np.pi):
    hour_angle += 2 * np.pi
if (hour_angle > np.pi):
    hour_angle -= 2 * np.pi

parallactic_angle = np.arctan2(np.sin(hour_angle), \
                             np.tan(lat)*np.cos(dec)- \
                             np.sin(dec)*np.cos(hour_angle)) * \
                             180 / np.pi

predicted_rotator_mechangle = config['telescope']['rotator'][camname]['rotator_field_angle_zeropoint'] - parallactic_angle + target_alt

print("\n##########################################")
print("Predicted rotator angle: {} degrees".format(predicted_rotator_mechangle))
if (predicted_rotator_mechangle > \
    config['telescope']['rotator'][camname]['rotator_min_degs'] \
    and predicted_rotator_mechangle < \
    config['telescope']['rotator'][camname]['rotator_max_degs']):
    print("No rotator wrap predicted")
    target_mech_angle = predicted_rotator_mechangle
    print(f"Target field angle --> {target_field_angle}")
    print(f"Target mech angle = {target_mech_angle}")    
if (predicted_rotator_mechangle < \
    config['telescope']['rotator'][camname]['rotator_min_degs']):
    print("Rotator wrapping < min, adjusting")
    target_field_angle -= 360.0
    target_mech_angle = predicted_rotator_mechangle + 360.0
    print(f"Adjusted field angle --> {target_field_angle}")
    print(f"New target mech angle = {target_mech_angle}")
    
if (predicted_rotator_mechangle > \
    config['telescope']['rotator'][camname]['rotator_max_degs']):
    print("Rotator wrapping > max, adjusting")
    # Changed line below from + to -= as a test...RAS
    target_field_angle -= 360.0
    target_mech_angle = predicted_rotator_mechangle - 360.0
    print(f"Adjusted field angle --> {target_field_angle}")
    print(f"New target mech angle = {target_mech_angle}")
print("##########################################")
