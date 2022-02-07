#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 25 13:51:59 2022

@author: frostig
"""

import astropy.units as u
from astropy.time import Time, TimeDelta
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
import astropy.coordinates as coords
import astroplan
import numpy as np
import pandas as pd


# define location of Wallace Observatory
W_loc = coords.EarthLocation(lat=coords.Latitude('33d21m25.5s'),
                              lon=coords.Longitude('-116d51m58.4s'),
                              height=1696.)

W_Observer = astroplan.Observer(location=W_loc)

# get alt and az of observations
# in decimal degrees
def get_alt_az(times, ra, dec):
    loc = SkyCoord(ra=ra, dec=dec, frame='icrs')
    time = Time(times, format='mjd')         
    altaz = loc.transform_to(AltAz(obstime=time,location=W_loc))
    degs = SkyCoord(altaz.az, altaz.alt, frame='icrs')
    #print('altaz'  , altaz)
    alt_array = degs.dec.degree
    az_array = degs.ra.degree
    
    return (alt_array, az_array)

# what is up (above altitude 20 deg) in a given night?
# date in MJD (median Julian Date), e.g. 59480 (Sept 23)
# ra (right ascension) in hours, minutes, seconds, e.g. '+19h50m41s'
# dec (declination) in hours, minutes, seconds, e.g. '+08d50m58s'
def up_tonight(time, ra, dec):
    loc = SkyCoord(ra=ra, dec=dec, frame='icrs')
    time = Time(time, format='mjd') 
    sun_rise = W_Observer.sun_rise_time(time, which="previous") 
    sun_set = W_Observer.sun_set_time(time, which="next") 
    night =(sun_set.jd-sun_rise.jd)
    if night >= 1:
        # if next day, subtract a day
        dt = np.linspace(sun_set.jd, sun_set.jd+(night-1), 100)
    else:
        dt = np.linspace(sun_set.jd, sun_set.jd+(night), 100)
        
    altaz = loc.transform_to(AltAz(obstime=Time(dt, format='jd'),location=W_loc))
    d = {'time': dt, 'alt': altaz.alt}
    df = pd.DataFrame(data=d)
    df = df[df['alt']>=20] # can change limiting altitude here 
    try:
        time_up = df['time'].iloc[-1] - df['time'].iloc[0]
    except:
        time_up = 0
     
    if time_up > 0:
        start = Time(df['time'].iloc[0], format='jd').isot
        end = Time(df['time'].iloc[-1], format='jd').isot
        is_available = 'Object is up between UTC ' + str(start)+ ' and ' + str(end)
        avail_bool = True
    else:
        is_available = 'Object is not up'
        avail_bool = False
        
    
    return (avail_bool, is_available)


### backend 
def rad_to_deg(x):
    return x * 180 / np.pi

camera_field_size = 0.26112 /2

git_path = '../daily_summer_scheduler/data/'

field_filename = git_path + 'SUMMER_fields.txt'


def get_field_ids(ras, decs, units="degrees"):
    field_list = []
    
    lists = [ras, decs]
    if len(set(map(len, lists))) not in (0, 1):
        raise ValueError('RA and Dec lists are not the same length')
    
    for ra, dec in zip(ras, decs):
        summer_fields = pd.read_csv(field_filename,
         names=['field_id','ra','dec','ebv','l','b',
             'ecliptic_lon', 'ecliptic_lat', 'number'],
         sep='\s+',usecols=['field_id','ra','dec', 'l','b', 
             'ecliptic_lon', 'ecliptic_lat'],index_col='field_id',
         skiprows=1)
        ra = float(ra)
        dec = float(dec)
        if units=="radians":
            ra_degs = rad_to_deg(ra)
            dec_degs = rad_to_deg(dec)
        elif units == "degrees":
            ra_degs = ra
            dec_degs = dec
            
        print(ra, dec)
        # sort dec
        dec_sort = summer_fields.iloc[((summer_fields['dec']-dec_degs).abs() <= camera_field_size).values]
        print('dec', dec_sort)
        
        # sort ra
        ra_sort = dec_sort.iloc[((dec_sort['ra']-ra_degs).abs() <= camera_field_size).values]
        print('ra', ra_sort)
        
        field_num = ra_sort.index[0]
        field_list.append(int(field_num))
        
    return field_list

