#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  8 11:51:53 2022

headerCreator.py

This script defines an object which takes in a status dictionary, and spits out
a FITS header. This will allow multiple cameras on the WINTER system to
all create the same headers.



@author: nlourie
"""

import astropy.io.fits as fits
import astropy.units as u
import astropy.coordinates
from astropy.time import Time
import numpy as np
from datetime import datetime

class HeaderCreator(object):
    
    def __init__(self, config, site, cameraName):
        
        self.config = config
        self.site = site
        self.camname = cameraName
        
        
    
    def getDefaultHeader(self, image_info_dict, observatory_state_dict):
            
            state = observatory_state_dict
            imginfo = image_info_dict
        
            # state should be the housekeeping state of the full observatory
            
            # make an empty header LIST: EACH ENTRY WILL BE A fits.Card object
            header =list()
            
            # populate the header. this would be better done driven by a config file
            
            ###### BASIC PARAMETERS ######
            header.append(fits.Card('ORIGIN',   f'WINTER: {self.camname} Camera', 'Data Origin'))
            header.append(fits.Card('OBSERVER', state.get('operator_name', ''),     'Observer'))
            header.append(fits.Card('OBSTYPE',  state.get('obstype', ''),            'Observation Type'))
            #add the filename to the header
            header.append(fits.Card('FILENAME', imginfo.get('lastfilename', ''), 'File name'))
            header.append(fits.Card('ORIGNAME', imginfo.get('lastfilename', ''), 'Original filename'))
            
            
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
            """
            there are a few relevant fields here:
                mount_ra_j2000_hours: the current (instantaneous) mount ra hours
                mount_dec_j2000_deg: the current mount dec in degrees
                robo_target_ra_j2000: the requested target RA from roboOperator (hours)
                robo_target_dec_j2000: the requested target DEC from roboOperator (degs)
            
            """
            # not putting in hourangle for now... need to figure out how to calculate it properly!
            #header.append(fits.Card('HOURANG',  '', 'Hour angle'))
            #TODO: add hourangle
            #TODO: change RA and DEC to the requested RA DEC, not the instantaneous RA/DEC
            
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
            #header.append(fits.Card('PROGRMPI',     state.get('programPI',''),                   'Queue program PI'))
            #header.append(fits.Card('PROGRMID',     state.get('programID',''),                   'Queue program ID'))
            header.append(fits.Card('PROGID',       state.get('programPI',''),                      'Queue program PI'))
            header.append(fits.Card('PROGNAME',     state.get('programName',''),                    'Queue program name'))
            header.append(fits.Card('PROGPI',       state.get('robo_progID',''),                    'Queue program ID'))
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
            filterpos = state.get('Viscam_Filter_Wheel_Position', 0)
            try:
                filterID = self.config['filter_wheels']['summer']['positions'][filterpos]
                filtername = self.config['filters']['summer'][filterID]['name']
                print(f"filterpos = {filterpos}, filterID = {filterID}, filtername = {filtername}")
            except Exception as e:
                filterID = '?'
                filtername = '?'
                print(f"couldn't get filter info for FITS header: {e}")
            header.append(fits.Card('FILTER',        filtername,        'Filter name'))
            header.append(fits.Card('FILTERID',      filterID,          'Filter ID'))
            header.append(fits.Card('FILPOS',        filterpos,         'Filter position'  ))
    
            # SHUTTER PARAMETERS
            shutter_open_timestamp = imginfo.get('shutter_open_timestamp', 0.0)
            shutter_close_timestamp = imginfo.get('shutter_close_timestamp', 0.0)
            
            if shutter_open_timestamp != 0.0:
                SHUTOPEN = datetime.fromtimestamp(self.shutter_open_timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')
                header.append(fits.Card('SHUTOPEN', SHUTOPEN, 'Shutter Open Time (UTC)'))
            else:
                header.append(fits.Card('SHUTOPEN', 0.0, 'Shutter Open Time (UTC)'))
        
            if shutter_close_timestamp != 0.0:
                SHUTCLSD = datetime.fromtimestamp(self.shutter_close_timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')
                header.append(fits.Card('SHUTCLSD', SHUTCLSD, 'Shutter Open Time (UTC)'))
            else:
                header.append(fits.Card('SHUTCLSD', 0.0, 'Shutter Open Time (UTC)'))                       
            
            ###### CAMERA PARAMETERS #####
            header.append(fits.Card('INSTRUME',     'WINTER/SUMMER',        'Instrument name'))
            header.append(fits.Card('DETECTOR',     'LLAMAS Raptor Photonics e2v CCD42-40 NIMO',    'Camera sensor'))
            camID = f'Camera SN: {self.cc._manufData[self.camnum].serial_num}, Mfg: {self.cc._manufData[self.camnum].build_code}, {self.cc._manufData[self.camnum].build_date}'
            header.append(fits.Card('DETID',        camID,  'Detector ID'))
            header.append(fits.Card('DETSOFT',      'LLAMAS/huaso: WINTER branch pre-release',  'Detoector software version'))
            firmware = f'FPGA: {self.cc._fpgaversion[self.camnum]}, MicroVersion: {self.cc._microversion[self.camnum]}'
            header.append(fits.Card('DETFIRM', firmware,    'Detector firmware version'))
            header.append(fits.Card('DETSIZE', '[1:2048,1:2048]', 'CCD size (pixels)'))
            header.append(fits.Card('INFOSEC', '[1:2048,2049:2049]', 'Image metadata section'))
            # ROISEC
            # AMPSEC
            header.append(fits.Card('TRIMSEC', '[1:2048,1:2048]', 'trim secion'))
            header.append(fits.Card('DATASEC', '[1:2048,1:2048]', 'trim secion'))
            # BIASSEC
            # DETSEC
            header.append(fits.Card('PIXSCALE',     0.466,                          'Pixel scale in arcsec per pixel'))
            header.append(fits.Card('EXPOSURE',     state.get('exptime_total', 0),  'Total exposure time (sec)'))
            header.append(fits.Card('EXPTIME',      imginfo.get('exptime', '?'),                   'Requested exposure time (sec)'))
            header.append(fits.Card('AEXPTIME',     imginfo.get('exptime_actual', '?'), 'Actual exposure time (sec)'))
            #MODE_NUM
            header.append(fits.Card('CCDSUM',       '1 1',                          'CCD binning'))
            
            ###### TIME PARAMETERS ######
    
            # add the image acquisition timestamp to the fits header
            image_starttime_utc = imginfo.get('image_starttime_utc', None)
            if image_starttime_utc is not None:
                image_starttime_utc_object = Time(image_starttime_utc)    
                utc = image_starttime_utc.strftime('%Y%m%d_%H%M%S.%f')
                utciso = image_starttime_utc_object.iso
                utcshut = image_starttime_utc.strftime('%Y%m%d_%H%M%S.%f')
                utcobs = image_starttime_utc.strftime('%Y%m%d %H%M%S.%f')
                dateobs = image_starttime_utc.strftime('%Y%m%d %H%M%S.%f')
                obsjd = image_starttime_utc_object.jd
                obsmjd = image_starttime_utc_object.mjd
                obstime = Time(image_starttime_utc, scale = 'utc', location = self.site)
                lst_obj = obstime.sidereal_time('mean')
                obslst = lst_obj.to_string(unit = u.deg, sep = ':')
            else:
                utc = ''
                utciso = ''
                utcshut = ''
                utcobs = ''
                dateobs = ''
                obsjd = ''
                obsmjd = ''
                obslst = ''
            header.append(fits.Card('UTC',          utc,     'Time of observation '))
            header.append(fits.Card('UTCISO',       utciso,  'Time of observation in ISO format'))
            header.append(fits.Card('UTCSHUT',      utcshut, 'UTC time shutter open'))
            header.append(fits.Card('UTC-OBS',      utcobs,  'UTC time shutter open'))
            header.append(fits.Card('DATE-OBS',     dateobs, 'UTC date of observation (MM/DD/YY)'))
            header.append(fits.Card('OBSJD',        obsjd,   'Julian day corresponds to UTC'))
            header.append(fits.Card('OBSMJD',       obsmjd,  'MJD corresponds to UTC'))
            header.append(fits.Card('OBSLST',       obslst,  'Mean LST corresponds to UTC'))
        
            
            
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