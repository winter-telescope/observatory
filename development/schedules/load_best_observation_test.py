#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 17 08:06:42 2022

@author: winter
"""



import os
import wintertoo.validate
#from wintertoo import validate as wintertoo_validate
import pandas as pd
import sqlalchemy as db
import astropy.coordinates
import astropy.units as u
import astropy.time
import numpy as np
import matplotlib.pyplot as plt
import sys
# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')

sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')
from utils import utils
from ephem import ephem_utils

def log(str):
    print(str)
# load the config

config_file = wsp_path + '/config/config.yaml'
config = utils.loadconfig(config_file)

lat = astropy.coordinates.Angle(config['site']['lat'])
lon = astropy.coordinates.Angle(config['site']['lon'])
height = config['site']['height'] * u.Unit(config['site']['height_units'])
                                
site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)

schedulepaths = [#os.readlink(os.path.join(os.getenv("HOME"), 'data', 'nightly_schedule.lnk')),
                 #os.path.join(os.getenv("HOME"), 'data','schedules','ToO','timed_requests_08_12_2022_14_1660339301_.db'),
                 #os.path.join(os.getenv("HOME"), 'data', 'schedules', 'ToO', 'timed_requests_08_15_2022_15_1660601716_.db'),
                 #os.path.join(os.getenv("HOME"), 'data', 'schedules', 'ToO', '/home/winter/data/schedules/ToO/timed_requests_08_16_2022_13_1660680719_.db'),
                 os.path.join(os.getenv("HOME"), 'data', 'schedules', 'ToO', '/home/winter/data/schedules/ToO/testcrab.db'),   
                 ]

#schedulepaths = [os.readlink(os.path.join(os.getenv("HOME"), 'data', 'nightly_schedule.lnk'))]

for too_file in schedulepaths:
    obstime_mjd = 59809.1
    
    log(f'validating too_file = {too_file}')
    engine = db.create_engine('sqlite:///'+too_file)
    conn = engine.connect()
    df = pd.read_sql('SELECT * FROM summary;',conn)
    
    # keep analyzing and making cuts unless you throw away all the entries
    
    df['origin_filename'] = too_file
    conn.close()
    
    ### if we were able to load and query the SQL db, check to make sure the schema are correct
    wintertoo.validate.validate_schedule_df(df)
    log(f'obstime_mjd = {obstime_mjd}')
    log(f'entries before making any cuts: df = \n{df}')
    
    
    ### if the schema were correct, make cuts based on observability
    # Note: if we don't do this we can end up in a situation where do_Observation will reject an 
    #       observation, but this will keep submitting it and we'll get stuck in a useless loop
    # select only targets within their valid start and stop times
    df = df.loc[(obstime_mjd >= df['validStart']) & (obstime_mjd<= df['validStop']) & (df['observed'] == 0)]
    
    if len(df) == 0:
        log(f'{too_file}: no valid entries after start/stop/observed cuts')
        continue
    else:
        pass
    # if the maxAirmass is not specified, add it in
    if 'maxAirmass' not in df:
        default_max_airmass = 1.0/np.cos((90 - config['telescope']['min_alt'])*np.pi/180.0)
        df['maxAirmass'] = default_max_airmass
        
    # calculate the current airmass of all targets
    
    obstime_astropy = astropy.time.Time(obstime_mjd, format = 'mjd')
    
    
    frame = astropy.coordinates.AltAz(
                                        obstime = obstime_astropy,
                                        location = site)
    log('made the frame ?')
    #print('RA')
    log(f"df['raDeg'] = {df['raDeg']}")
    log(f"df['decDeg'] = {df['decDeg']}")
    #log(f"df['raDeg']*u.deg = {df['raDeg']*u.deg}")
    #log(f"df['decDeg']*u.deg = {df['decDeg']*u.deg}")
    #print('DEC')
    #print(df['decDeg'])
    j2000_coords = astropy.coordinates.SkyCoord(ra = df['raDeg']*u.deg, dec = df['decDeg']*u.deg, frame = 'icrs')
    log('made the j2000 coords?')