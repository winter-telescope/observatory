#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 22 14:54:47 2023

FITS Header Creator

Takes in metadata, typically a state dictionary from WSP, and produces 
a full FITS header

@author: winter
"""
import sys
import os
from PyQt5 import QtCore
import threading
import Pyro5.core
import Pyro5.server
import signal
import yaml
import logging
import time
from datetime import datetime
import pathlib
from astropy.time import Time
import astropy.units as u
import astropy.coordinates
import astropy.io.fits as fits
import pytz
import numpy as np

def GetHeader(state, imageinfo):
    
    # state is the WSP housekeeping state metadata
    # imageinfo is specific information about the image
    
    # state should be the housekeeping state of the full observatory
    
    # make an empty header LIST: EACH ENTRY WILL BE A fits.Card object
    header =list()
    
    # populate the header. this would be better done driven by a config file
    
    ###### BASIC PARAMETERS ######
    header.append(fits.Card('OBSTYPE',  state.get('obstype', ''),            'Observation Type'))
    #add the filename to the header
    header.append(fits.Card('FILENAME', imageinfo.get('imname', ''), 'File name'))
    header.append(fits.Card('ORIGNAME', imageinfo.get('imname', ''), 'Original filename'))
    
    
    ###### TELESCOPE PARAMETERS ######
    # Site lon/lat/height
    header.append(fits.Card('OBSERVAT', 'Palomar Observatory', 'Observatory'))
    header.append(fits.Card('TELESCOP', 'WINTER / P39', 'Observatory telescope'))
    header.append(fits.Card('OBSLAT',   state.get('site_latitude_degs', ''),    'Observatory latitude (deg)' ))
    header.append(fits.Card('OBSLON',   state.get('site_longitude_degs', ''),   'Observatory longitude (deg)'))
    header.append(fits.Card('OBSALT',   state.get('site_height_meters', ''),    'Observatory altitude (m)'))
    header.append(fits.Card('TELLAT',   state.get('mount_latitude_degs', ''),   'Telescope latitude (deg)'))
    header.append(fits.Card('TELLON',   state.get('mount_longitude_degs', ''),  'Telescope longitude (deg)'))
    header.append(fits.Card('TELALT',   state.get('mount_height_meters', ''),   'Telescope altitude (m)'))
    # target RA/DEC

    # RA
    ra_hours = state.get('mount_ra_j2000_hours', 0)
    ra_obj = astropy.coordinates.Angle(ra_hours * u.hour)
    header.append(fits.Card('RA',           ra_obj.to_string(unit = u.deg, sep = ':'),  'Requested right ascension (deg:m:s)'))
    # DEC
    dec_deg = state.get('mount_dec_j2000_deg', 0)
    dec_obj = astropy.coordinates.Angle(dec_deg * u.deg)
    header.append(fits.Card('DEC',          dec_obj.to_string(unit = u.deg, sep = ':'), 'Requested declination (deg:m:s)'))
    
    header.append(fits.Card('TELRA',        ra_obj.to_string(unit = u.deg, sep = ':'),  'Telescope right ascension (deg:m:s)'))
    header.append(fits.Card('TELDEC',       dec_obj.to_string(unit = u.deg, sep = ':'), 'Telescope declination (deg:m:s)'))
    
    # Alt and Az
    header.append(fits.Card('AZIMUTH',      state.get('mount_az_deg', ''),              'Telescope azimuth (deg)'))
    header.append(fits.Card('ALTITUDE',     state.get('mount_alt_deg', ''),             'Telescope altitude (deg)'))
    header.append(fits.Card('ELVATION',     state.get('mount_alt_deg', ''),             'Telescope elevation (deg)'))
    # airmass
    z = (90 - state.get('mount_alt_deg', 0))*np.pi/180.0
    airmass = 1/np.cos(z)
    header.append(fits.Card('AIRMASS',      airmass,        'Airmass'))
    header.append(fits.Card('DOME_AZ',      state.get('dome_az_deg', ''),               'Dome azimuth (deg)'))
    
    header.append(fits.Card('FOCPOS',       state.get('focuser_position', ''),          'Focuser position (micron)'))
    header.append(fits.Card('ROTMECH',      state.get('rotator_mech_position', ''),     'Rotator mechanical angle (deg)'))        
    header.append(fits.Card('ROTFIELD',     state.get('rotator_field_angle', ''),       'Rotator field angle (deg)'))
    
    ###### QUEUE PARAMETERS ######
    header.append(fits.Card('PROGID',       state.get('robo_programID',''),                      'Queue program PI'))
    header.append(fits.Card('PROGNAME',     state.get('programName',''),                    'Queue program name'))
    header.append(fits.Card('PROGPI',       state.get('programPI',''),                    'Queue program ID'))
    header.append(fits.Card('QCOMMENT',     state.get('qcomment',''),                       'Queue comment'))
    header.append(fits.Card('FIELDID',      state.get('robo_fieldID',''),                   'Field ID number'))
    header.append(fits.Card('OBHISTID',     state.get('robo_obsHistID',''),                 'obsHistID: line in schedulefile'))
    
    
    try:
        objra = astropy.coordinates.Angle(state.get('robo_target_ra_j2000', 0)*u.hour)
        objdec = astropy.coordinates.Angle(state.get('robo_target_dec_j2000', 0)*u.deg)
        objra_str = objra.to_string(unit = u.deg, sep = ':')
        objdec_str = objdec.to_string(unit = u.deg, sep = ':')
    except Exception as e:
        objra_str = ''
        objdec_str = ''
        print(f'ccd_daemon: could not form object ra/dec strings: {e}')
        
    header.append(fits.Card('OBJRA', objra_str,     'Object right ascension (deg:m:s)'))
    header.append(fits.Card('OBJDEC', objdec_str,   'Object declination (deg:m:s)'))
    
    # target type: altaz, radec, schedule
    header.append(fits.Card('TARGTYPE', state.get('targtype',''),           'Target Type'))

    
    ###### FILTER PARAMETERS ######

    filtername = imageinfo.get('filtername', '')
    filterID = imageinfo.get('filterID', '')
    filterpos = imageinfo.get('filterpos', '')
    header.append(fits.Card('FILTER',        filtername,        'Filter name'))
    header.append(fits.Card('FILTERID',      filterID,          'Filter ID'))
    header.append(fits.Card('FILPOS',        filterpos,         'Filter position'  ))
    
                    

    ###### CAMERA PARAMETERS #####
    instrument = imageinfo.get('camname', '').upper()
    header.append(fits.Card('INSTRUME',     instrument,        'Instrument name'))
    header.append(fits.Card('EXPTIME',      imageinfo.get('exptime', -1),                   'Requested exposure time (sec)'))


    #MODE_NUM
    
    ###### TIME PARAMETERS ######
    try:
        # add the image acquisition timestamp to the fits header
        image_starttime_utc = imageinfo.get('image_starttime_utc')
        image_starttime_utc_object = Time(image_starttime_utc)
        header.append(fits.Card('UTC',          image_starttime_utc.strftime('%Y%m%d_%H%M%S.%f'),  'Time of observation '))
        header.append(fits.Card('UTCISO',       image_starttime_utc_object.iso,                    'Time of observation in ISO format'))
        header.append(fits.Card('UTCSHUT',      image_starttime_utc.strftime('%Y%m%d_%H%M%S.%f'),  'UTC time shutter open'))
        header.append(fits.Card('UTC-OBS',      image_starttime_utc.strftime('%Y%m%d %H%M%S.%f'),  'UTC time shutter open'))
        header.append(fits.Card('DATE-OBS',     image_starttime_utc.strftime('%Y%m%d %H%M%S.%f'),  'UTC date of observation (MM/DD/YY)'))
        header.append(fits.Card('OBSJD',        image_starttime_utc_object.jd,                     'Julian day corresponds to UTC'))
        header.append(fits.Card('OBSMJD',       image_starttime_utc_object.mjd,                    'MJD corresponds to UTC'))
    except:
        header.append(fits.Card('UTC',          '',  'Time of observation '))
        header.append(fits.Card('UTCISO',       '',  'Time of observation in ISO format'))
        header.append(fits.Card('UTCSHUT',      '',  'UTC time shutter open'))
        header.append(fits.Card('UTC-OBS',      '',  'UTC time shutter open'))
        header.append(fits.Card('DATE-OBS',     '',  'UTC date of observation (MM/DD/YY)'))
        header.append(fits.Card('OBSJD',        '',  'Julian day corresponds to UTC'))
        header.append(fits.Card('OBSMJD',       '',  'MJD corresponds to UTC'))
    """
    obstime = Time(self.image_starttime_utc, scale = 'utc', location = self.site)
    lst_obj = obstime.sidereal_time('mean')
    header.append(fits.Card('OBSLST', lst_obj.to_string(unit = u.deg, sep = ':'),              'Mean LST corresponds to UTC'))
    """
    
    ###### WEATHER PARAMETERS ######
    #UT_WEATH
    try:
        weather_datetime = datetime.fromtimestamp(state['dome_timestamp'])
        ut_weath = weather_datetime.strftime('%Y-%m-%d %H%M%S.%f')
    except Exception as e:
        print(f'could not get dome time, {e}')
        ut_weath = ''
    header.append(fits.Card('UT_WEATH',     ut_weath, 'UT of weather data'))
    #TEMPTURE
    header.append(fits.Card('TEMPTURE',     state.get('T_outside_pcs', ''),             'Outside air temperature (C)'))
    #WINDSPD
    header.append(fits.Card('WINDSPD',      state.get('windspeed_average_pcs', ''),     'Outside wind speed'))
    #WINDDIR
    header.append(fits.Card('WINDDIR',      state.get('wind_direction_pcs', ''),        'Outside wind direction (deg)'))
    #DEWPOINT
    header.append(fits.Card('DEWPOINT',     state.get('Tdp_outside_pcs', ''),           'Dewpoint (C)'))
    #WETNESS
    header.append(fits.Card('WETNESS',      state.get('dome_wetness_pcs', ''),          'Wetness sensor reading'))
    #HUMIDITY
    header.append(fits.Card('HUMIDITY',     state.get('rh_outside_pcs', ''),            'Relative humidity (%)'))
    #PRESSURE
    header.append(fits.Card('PRESSURE',     state.get('pressure_pcs', ''),              'Atmospheric pressure, millibars'))
    #TELESCOPE TEMPS
    header.append(fits.Card('TEMPM1',     state.get('telescope_temp_m1', ''),              'telescope temp M1, C'))
    header.append(fits.Card('TEMPM2',     state.get('telescope_temp_m2', ''),              'telescope temp M2, C'))
    header.append(fits.Card('TEMPM3',     state.get('telescope_temp_m3', ''),              'telescope temp M3, C'))
    header.append(fits.Card('TEMPAMB',    state.get('telescope_temp_ambient', ''),         'telescope temp ambient, C'))

    
    ###### INSTRUMENT MONITOR PARAMETERS ######
    
    
    
    ###### OTHER PARAMETERS ######
    header.append(fits.Card('MOONRA',       state.get('moon_ra_deg', ''),                   'Moon J2000.0 R.A. (deg)'))
    header.append(fits.Card('MOONDEC',      state.get('moon_dec_deg', ''),                  'Moon J2000.0 Dec. (deg)'))
    header.append(fits.Card('MOONILLF',     state.get('moon_illf', ''),                     'Moon illuminated fraction (frac)'))
    header.append(fits.Card('MOONPHAS',     state.get('moon_phase', ''),                    'Moon phase angle (deg)'))
    header.append(fits.Card('MOONESB',      state.get('moon_excess_brightness_vband', ''),  'Moon excess in sky brightness V-band'))
    header.append(fits.Card('MOONALT',      state.get('moon_alt', ''),                      'Moon altitude (deg)'))
    header.append(fits.Card('MOONAZ',       state.get('moon_az', ''),                       'Moon azimuth (deg)'))
    header.append(fits.Card('SUNALT',       state.get('sun_alt', ''),                       'Sun altitude (deg)'))
    header.append(fits.Card('SUNAZ',        state.get('sun_az', ''),                        'Sun azimuth (deg)'))
    header.append(fits.Card('SEEING',       state.get('fwhm_mean', ''),                     'Seeing measurement: FWHM mean from focusing'))
             
    return header

if __name__ == '__main__':
    
    header = GetHeader({}, {})
    
    hdu = fits.PrimaryHDU()
    
    hdu.data = np.zeros((1080, 1920))
    for card in header:
        hdu.header.append(card)
    
    hdu.writeto(os.path.join(os.getenv("HOME"), 'data','test.fits'), overwrite = True)
    