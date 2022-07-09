#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  7 09:29:29 2022

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

schedulepaths = [os.readlink(os.path.join(os.getenv("HOME"), 'data', 'nightly_schedule.lnk')),
                 os.path.join(os.getenv("HOME"), 'data','schedules','ToO','timed_requests_06_08_2022_12_1654715434_.db')]

schedulepaths = [os.readlink(os.path.join(os.getenv("HOME"), 'data', 'nightly_schedule.lnk'))]

for schedulepath in schedulepaths:
    engine = db.create_engine('sqlite:///'+schedulepath)
    
    conn = engine.connect()
    df = pd.read_sql('SELECT * FROM summary;',conn)
    
    df['priority'] = 0
    if 'maxAirmass' not in df:
        minalt = 20
        default_max_airmass = 1.0/np.cos((90 - minalt)*np.pi/180.0)
        df['maxAirmass'] = default_max_airmass
    
    #df['origin_filename'] = too_file
    #full_df = pd.concat([full_df,df])
    conn.close()
    
    def validateSchedule(df):
        # try to validate the schedule:
        try:
            wintertoo.validate.validate_schedule_df(df)
            return True
        
        except Exception as e:
            #print(e)
            print('schedule not valid')
            
            return False
        
    schedvalid = validateSchedule(df)
    print(f'Schedulefile: {schedulepath}')
    print(f'Valid Schedule? {schedvalid}')
    
    # calculate the current airmass of all targets
    # set up site
    config = utils.loadconfig(os.path.join(wsp_path, 'config', 'config.yaml'))
    lat = astropy.coordinates.Angle(config['site']['lat'])
    lon = astropy.coordinates.Angle(config['site']['lon'])
    height = config['site']['height'] * u.Unit(config['site']['height_units'])
                                    
    site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)


    # calculate the current Alt and Az of the target 
    obstime_mjd = 59762.1726555993
    obstime_utc = astropy.time.Time(obstime_mjd, format = 'mjd', \
                                    location=site)
        
    frame = astropy.coordinates.AltAz(obstime = obstime_utc, location = site)
    j2000_coords = astropy.coordinates.SkyCoord(ra = df['raDeg']*u.deg, dec = df['decDeg']*u.deg, frame = 'icrs')
    local_coords = j2000_coords.transform_to(frame)
    local_alt_deg = local_coords.alt.deg
    local_az_deg = local_coords.az.deg
    airmass = 1/np.cos((90 - local_alt_deg)*np.pi/180.0)
    df['airmass'] = airmass
    df['altDeg'] = local_alt_deg
    df['azDeg'] = local_az_deg
    
    df_select = df.loc[(df['airmass'] < df['maxAirmass']) & (df['airmass'] > 0)]
    
    # check if there is any ephem in view
    bodies_inview = np.array([])
    bodies = list(config['ephem']['min_target_separation'].keys())
    for i in range(len(bodies)):
        
        body = bodies[i]
        mindist = config['ephem']['min_target_separation'][body]
        
        body_loc = astropy.coordinates.get_body(body, time = obstime_utc, location = site)
        body_coords = body_loc.transform_to(frame)
        body_alt = body_coords.alt
        body_az = body_coords.az
        
        dist = np.array(((df_select['azDeg'] - body_az.deg)**2 + (df_select['altDeg'] - body_alt.deg)**2)**0.5)
        
        # make a list of whether the body is in view for each target
        body_inview = dist<mindist
        
        # now make a big array of all bodies and all targets
        if i == 0:
            bodies_inview = body_inview
        else:
            bodies_inview = np.vstack((bodies_inview, body_inview))
        
        # now collapse the array of bodies and targests so it's just a list of targets and w
        # wheather there are ANY bodies in view
        ephem_inview = np.any(bodies_inview, axis = 0)
    
    # add the ephem in view to the dataframe
    df_select['ephem_inview'] = ephem_inview
    
    plt.figure(figsize = (10,4))
    plt.suptitle('Checking Airmass Cut')
    plt.subplot(1,2,1)
    plt.plot(df['obsHistID'], df['altDeg'], 'o', label = 'All Data')
    plt.plot(df_select['obsHistID'], df_select['altDeg'], 'o', label = 'Selection')
    plt.plot(df['obsHistID'], df['obsHistID']*0.0 + minalt, '-', label = 'Min Alt')
    plt.ylabel('Current Target Alt [deg]')
    plt.xlabel('obsHistID')
    plt.legend()
    
    plt.subplot(1,2,2)
    plt.plot(df['obsHistID'], df['airmass'], 'o', label = 'All Data')
    plt.plot(df_select['obsHistID'], df_select['airmass'], 'o', label = 'Selection')
    plt.plot(df['obsHistID'], df['obsHistID']*0.0 + default_max_airmass, '-', label = 'Max Airmass')
    plt.ylabel('Current Target Airmass [-]')
    plt.xlabel('obsHistID')
    plt.legend()
    plt.tight_layout()
    
    