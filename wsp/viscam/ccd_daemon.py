#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  1 16:20:02 2021

ccd_daemon.py

This file is part of wsp

# PURPOSE #
This module runs the visible camera daemon that controls the LLAMAS
camera interface.



@author: nlourie
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
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f'wsp_path = {wsp_path}')
sys.path.insert(1, wsp_path)

# Import WINTER Modules
from utils import utils
from daemon import daemon_utils
from utils import logging_setup
from alerts import alert_handler
from viscam import web_request


# add the huaso directory to the PATH
home_path = os.getenv("HOME")
huaso_path = os.path.join(home_path, 'LLAMAS_GIT','huaso')
server_daemon_dir = os.path.join(huaso_path, 'server_daemon', 'bin')
server_daemon_path = os.path.join(server_daemon_dir, 'huaso_server')
#sys.path.insert(1, huaso_path)
sys.path.append(huaso_path)
sys.path.append(server_daemon_dir)
# import huaso modules
from console import cameraClient
from housekeeping import data_handler


#%%

        
        
class CCD(QtCore.QObject):
    
    startStatusLoop = QtCore.pyqtSignal()
    
    imageAcquired = QtCore.pyqtSignal()
    imageSaved = QtCore.pyqtSignal()
    
    #shutdownCameraClientSignal = QtCore.pyqtSignal()
    
    """
    # these are signals to start timers which are kept in the main PyroGUI object
    WHY? Well this is a workaround because when I tried to put the QTimers in
    the __init__ of this QObject, it didn't work. Everytime pyro would trigger the 
    function it would throw an error that QTimers could not be started from a different
    thread. Even though it seems like it should all be the same thread, evidently
    all the pyro function calls happen in worker threads. This seems to fix it, 
    so we'll give it a try!
    
    """
    
    startExposureTimer = QtCore.pyqtSignal(object)
    startReadTimer = QtCore.pyqtSignal(object)
    
    preventPollingSignal = QtCore.pyqtSignal()
    allowPollingSignal = QtCore.pyqtSignal()
    
    
    #commandRequest = QtCore.pyqtSignal(str) 
    
    # put any signal defs here
    def __init__(self, camnum, config, logger = None, verbose = False ):
        super(CCD, self).__init__()
        
        # set up the internals
        self.camnum = camnum
        self.config = config
        self.logger = logger
        self.verbose = verbose
        
        # empty var initialization
        # there will be issues on startup if these don't exist!
        self.exptime = None
        self.tec_temp = None
        self.tec_setpoint = None
        self.pcb_temp = None
        self.tec_status = None
        self.lastfilename = ''
        
        ## set up site: used for putting LST into the header
        lat = astropy.coordinates.Angle(self.config['site']['lat'])
        lon = astropy.coordinates.Angle(self.config['site']['lon'])
        height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])
                                        
        self.site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
        
        # for now, just hardcode the image path and prefix
        #self.imagepath = os.path.join(os.getenv("HOME"), 'data','viscam', '20210610')
        self.camname = 'SUMMER_'
        #self.default_imagepath = os.path.join(os.getenv("HOME"), self.config['image_directory'],)
        
        # local timezone for writing timestamps in local time
        self.local_timezone = pytz.timezone(self.config['site']['timezone'])
        
        # init the state dictionary
        self.state = dict()
        
        # empty dictionary that will hold things that get passed into the fits header
        self.imagestate = dict()
        
        # init the viscam (ie the shutter)
        self.viscam = web_request.Viscam(URL = self.config['viscam_url'], logger = self.logger)
        
        # flag to control whether or not we should open the shutter during the image
        self.useshutter = True
        
        # flags to monitor connection status
        self.server_running = False
        self.connected = False
        
        # flag to indicate that an image has been saved.
        # set it to false and add it to state
        self.resetImageSavedFlag()
        

        
        # connect signals and slots
        self.startStatusLoop.connect(self.startPollingStatus)
        self.allowPollingSignal.connect(self.allowPolling)
        self.preventPollingSignal.connect(self.preventPolling)
        self.imageSaved.connect(self.raiseImageSavedFlag)
        
        # create a QTimer which will allow regular polling of the status
        self.pollTimer_dt = 20*1000
        """
        self.pollTimer = QtCore.QTimer()
        self.pollTimer.setInterval(self.pollTimer_dt)
        self.pollTimer.setSingleShot(False)
        self.pollTimer.timeout.connect(self.pollStatus)
        """
        # start with the do polling flag true
        self.doPolling = True
        # is a poll currently happening?
        self.doing_poll = False
        
        # doing an exposure?
        self.doing_exposure = False
        
        # NOTE: NPL 7-12-21 it looks like somebody commented out the connections below...
        # that means the camera won't actually take an image... so not sure why. I'm  uncommenting
        # it again.
        # NOTE: NPL 7-15-21 nevermind, this actually happens in the PyroGUI thread and should stay commented out!
        """
        # exposure timer
        self.expTimer = QtCore.QTimer()
        self.expTimer.setSingleShot(True)
        self.expTimer.timeout.connect(self.readImg)
        
        # readout timer
        self.readTimer = QtCore.QTimer()
        self.readTimer.setSingleShot(True)
        self.readTimer.timeout.connect(self.fetchImg)
        """
        # set up poll status thread
        self.statusThread = data_handler.daq_loop(func = self.pollStatus, 
                                                       dt = self.pollTimer_dt,
                                                       name = 'ccd_status_loop'
                                                       )
        
        # set up the image directories
        self.setupFITS_directory() # just use the defaults
        
        # set up the camera and server
        self.startup()
        
        
        
    def log(self, msg, level = logging.INFO):
        
        msg = f'ccd_daemon: {msg}'
        
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def startup(self):
        
        self.reconnect()
    
    def allowPolling(self):
        self.doPolling = True
        self.log(f'allowing further status polls')
        
    def preventPolling(self):
        self.doPolling = False
        self.log(f'preventing further status polls')

    def startPollingStatus(self):
        self.pollTimer.start()
    
    def waitForClientIdle(self, dt = 0.1, timeout = 2.0, raiseException = True):
        t = 0
        
        while True:
            status = self.cc.getsocketstatus()
            #self.log(f'status = {status}')
            if status != 'IDLE':
                time.sleep(dt)
                t = t+dt
            else:
                #self.log(f'command done.')
                break
            if t>timeout:
                #self.log(f'command timed out')
                if raiseException:
                    raise TimeoutError(f'command timed out')
                else:
                    break
            
    def pollStatus(self):
        
        # things that don't require asking anything of the camera server
        self.state.update({'doing_exposure' : self.doing_exposure})
        
        
        # only update the last_update_timestamp when we've actually made a successful query of the camera
        
        
        #if self.doPolling and False: # for muting the polling during tests/dev
        if self.doPolling:
            #self.log('polling status')
            self.doing_poll = True
            
            
            try:
                #print('polling exposure time')
                #self.log(f'polling exposure time')
                
                if self.exptime is None:
                    # USE THIS IF YOU WANT TO ACTUALLY READ FROM CAMERA
                    self.exptime = self.cc.getexposure(self.camnum)[self.camnum]
                    self.waitForClientIdle()
                    self.state.update({'last_update_timestamp' : datetime.utcnow().timestamp()})

                    
                else:
                   # just read from client register
                    self.exptime = self.cc._exposure[self.camnum]
                
                #print(f"EXPOSURE TIME = {self.exptime}")
                self.state.update({'exptime' : self.exptime})
                
            except Exception as e:
                #self.log(f'badness while polling exposure time: {e}')
                self.log(e)
           
            time.sleep(1)
            
            try:
                #print('polling ccd temp')
                #self.log(f'polling ccd temp')
                self.tec_temp = self.cc.getccdtemp(self.camnum)[self.camnum]
                self.waitForClientIdle()
                self.state.update({'tec_temp' : self.tec_temp})
                self.state.update({'last_update_timestamp' : datetime.utcnow().timestamp()})
                
            except Exception as e:
                #self.log(f'badness while polling ccd temp: {e}')
                self.log(e)
            
            time.sleep(1)
            
            try:
                #print('polling tec setpoint')
                #self.log('polling tec setpoint')
                self.tec_setpoint = self.cc.gettecpt(self.camnum)[self.camnum]
                self.waitForClientIdle()
                self.state.update({'tec_setpoint' : self.tec_setpoint})
                self.state.update({'last_update_timestamp' : datetime.utcnow().timestamp()})
                
            except Exception as e:
                #self.log(f'badness while polling tec setpoint: {e}')
                self.log(e)
            
            time.sleep(1)
            
            try:
                #print('polling pcb temp')
                #self.log('polling pcb temp')
                self.pcb_temp = self.cc.getpcbtemp(self.camnum)[self.camnum]
                self.waitForClientIdle()
                self.state.update({'pcb_temp' : self.pcb_temp})
                self.state.update({'last_update_timestamp' : datetime.utcnow().timestamp()})
                
            except Exception as e:
                #self.log(f'badness while polling pcb temp: {e}')
                self.log(e)
            
            time.sleep(1)
            
            try:
                #print('polling tec status')
                #self.log('polling tec status')
                fpgastatus_str = self.cc.getfpgastatus(self.camnum)[self.camnum]
                self.waitForClientIdle()
                self.tec_status = int(fpgastatus_str[0])
                self.state.update({'tec_status' : self.tec_status})
                self.state.update({'last_update_timestamp' : datetime.utcnow().timestamp()})
                
            except Exception as e:
                #self.log(f'badness while polling tec status: {e}')
                self.log(e)
            
            time.sleep(1)
            
            try:
                self.getExposureTimeout()
                self.state.update({'exposureTimeout' : self.exposureTimeout})
            except Exception as e:
                #self.log(f'badness while calculating exposure sequence timeout: {e}')
                self.log(e)
                
            # record this update time
            
            self.state.update({'last_poll_attempt_timestamp': datetime.utcnow().timestamp()})   
                
                #print(f'>> TEC TEMP = {self.tec_temp}')
            
            
            # done with the current poll
            self.doing_poll = False
            pass
        else:
            self.log('I would have polled but it was prevented')
        
        
    @Pyro5.server.expose
    def resetImageSavedFlag(self):
        # pause for a few seconds to leave the image high
        time.sleep(1)
        self.imageSavedFlag = False
        self.state.update({'imageSavedFlag' : self.imageSavedFlag})
    
    def raiseImageSavedFlag(self):
        self.imageSavedFlag = True
        self.state.update({'imageSavedFlag' : self.imageSavedFlag})
    
    def cc_waitTilDone(self, timeout, dt = 0.1, verbose = False):
        t = 0
        #time.sleep(dt)
        while True:
            status = self.cc.getsocketstatus()
            if verbose:
                self.log(f'ccd socket status = {status}')
            if status != 'IDLE':
                time.sleep(dt)
                t = t+dt
            else:
                if verbose:
                    self.log(f'command done.')
                return True
                #break
            if t>timeout:
                if verbose:
                    self.log(f'command timed out')
                return False

    @Pyro5.server.expose
    def setexposure(self, seconds):
        self.log(f'setting exposure to {seconds}s')
        
        """self.preventPollingSignal.emit()
        
        # wait for the current poll to be finished
        while self.doing_poll:
            time.sleep(0.5)
            self.log('poll still happening, waiting 0.5 seconds')"""
        
        #self.exptime_nom = seconds
        self.exptime_nom = seconds
        """
        # NPL 7-15-21: this is the old approach. updated below with Rob's new huaso_server api
        time_in_ccd_units = int(seconds*40000000)
        self.cc.setexposure(self.camnum, time_in_ccd_units,readback=True)
        time.sleep(0.10)
        print("ACK EXPOSURE TIME: {}".format(self.cc._result[self.camnum]))   
        """
        self.cc.setexposure(self.camnum, self.exptime_nom)
        
        completed = self.cc_waitTilDone(2, verbose = True)
        self.log(f'set exposure completed = {completed}')
        
        
        
        # update the state
        self.log(f'robo: updating the exptime')
        self.state.update({'exptime' : self.cc._exposure[self.camnum]})
        
        """# ohhhh gosh we probably don't need all this nonsense.
        self.log('waiting for the exposure time to be set...')
        t = 0
        dt = 0.1
        timeout = 2.0
        while True:
            status = self.cc.getsocketstatus()
            self.log(f'status = {status}')
            if status != 'IDLE':
                time.sleep(dt)
                t = t+dt
            else:
                self.log(f'command done.')
                break
            if t>timeout:
                self.log(f'command timed out')
                break
        
        pass
        # re-enable the polling
        self.allowPollingSignal.emit()"""
    
    @Pyro5.server.expose
    def shutdownCameraClient(self):
        # Client is responsible for closing down the connection cleanly
        # otherwise it can hang.
        self.log(f'SHUTTING DOWN CCD CAMERA CLIENT SESSION')
        self.cc._shutdown()
        
    @Pyro5.server.expose
    def killServer(self):
        daemon_utils.killPIDS(self.huaso_server_pids, logger = self.logger)
        
    
    
    @Pyro5.server.expose
    def getExposure(self):
        self.log(f'getting current exposure time')
        exptime = self.cc.getexposure(self.camnum)[self.camnum]
        return exptime
    
    @Pyro5.server.expose
    def setSetpoint(self, temp):
        self.log(f'setting TEC setpoint to {temp} C')
        #self.pollTimer.stop()
        self.cc.settecpt(self.camnum, temp)
        #self.pollTimer.start()
        pass
    
    @Pyro5.server.expose
    def setupFITS_directory(self, image_directory = 'default'):
        """
        set up the FITS file that will be used for the next 
        """
        
        if image_directory == 'default':
            
            #tonight = utils.tonight()
            tonight = utils.tonight_local()
            
            ### SET UP NIGHTLY IMAGE DIRECTORY ###
            self.image_directory = os.path.join(os.getenv("HOME"), self.config['image_directory'], tonight)
            self.log(f'setting FITS image directory set to {self.image_directory}')
            
            # create the image data directory if it doesn't exist already
            pathlib.Path(self.image_directory).mkdir(parents = True, exist_ok = True)
            self.log(f'making image directory: {image_directory}')
            
        elif image_directory == '':
            
            self.image_directory = '/home/winter/data/images/tmp_unfiled'
            
        else:
            self.image_directory = image_directory
            
        ### SET UP SYMBOLIC LINK TO CURRENT IMAGE DIRECTORY ###
        # create the data link directory if it doesn't exist already
        image_link_path = os.path.join(os.getenv("HOME"), self.config['image_data_link_directory'], self.config['image_data_link_name'])
        try:
            os.symlink(self.image_directory, image_link_path)
        except FileExistsError:
            self.log('deleting existing symbolic link to current image directory')
            os.remove(image_link_path)
            os.symlink(self.image_directory, image_link_path)
            

        pass
    
    def makeSymLink_lastImage(self):
        # make a symbolic link to the last image taken: self.lastfilename
        
        last_image_link_path = os.path.join(os.getenv("HOME"), self.config['image_data_link_directory'],self.config['image_last_taken_link'])
        
        last_image_path = os.path.join(self.image_directory, self.lastfilename)
        
        try:
            os.symlink(last_image_path, last_image_link_path)
        except FileExistsError:
            self.log('deleting existing symbolic link to last image taken')
            os.remove(last_image_link_path)
            os.symlink(last_image_path, last_image_link_path)
        
    def getDefaultHeader(self, state):
        
        # state should be the housekeeping state of the full observatory
        
        # make an empty header LIST: EACH ENTRY WILL BE A fits.Card object
        header =list()
        
        # populate the header. this would be better done driven by a config file
        
        ###### BASIC PARAMETERS ######
        header.append(fits.Card('ORIGIN',   'WINTER: SUMMER Camera', 'Data Origin'))
        header.append(fits.Card('OBSERVER', state.get('operator_name', ''),     'Observer'))
        header.append(fits.Card('OBSTYPE',  state.get('obstype', ''),            'Observation Type'))
        #add the filename to the header
        header.append(fits.Card('FILENAME', self.lastfilename, 'File name'))
        header.append(fits.Card('ORIGNAME', self.lastfilename, 'Original filename'))
        
        
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
        header.append(fits.Card('PROGRMPI',     state.get('programPI',''),                   'Queue program PI'))
        header.append(fits.Card('PROGRMID',     state.get('programID',''),                   'Queue program ID'))
        header.append(fits.Card('QCOMMENT',     state.get('qcomment',''),                    'Queue comment'))
        header.append(fits.Card('FIELDID',      state.get('qcomment',''),                    'Field ID number'))
        
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
        except Exception as e:
            filterID = '?'
            filtername = '?'
            print(f"couldn't get filter info for FITS header: {e}")
        header.append(fits.Card('FILTER',        filtername,        'Filter name'))
        header.append(fits.Card('FILTERID',      filterID,          'Filter ID'))
        header.append(fits.Card('FILPOS',        filterpos,         'Filter position'  ))

        # SHUTTER PARAMETERS
        if self.shutter_open_timestamp != 0.0:
            SHUTOPEN = datetime.fromtimestamp(self.shutter_open_timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')
            header.append(fits.Card('SHUTOPEN', SHUTOPEN, 'Shutter Open Time (UTC)'))
        else:
            header.append(fits.Card('SHUTOPEN', 0.0, 'Shutter Open Time (UTC)'))
    
        if self.shutter_close_timestamp != 0.0:
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
        header.append(fits.Card('EXPTIME',      self.exptime,                   'Requested exposure time (sec)'))
        header.append(fits.Card('AEXPTIME', self.exptime_actual, 'Actual exposure time (sec)'))
        #MODE_NUM
        header.append(fits.Card('CCDSUM',       '1 1',                          'CCD binning'))
        
        ###### TIME PARAMETERS ######

        # add the image acquisition timestamp to the fits header
        image_starttime_utc_object = Time(self.image_starttime_utc)
        header.append(fits.Card('UTC',          self.image_starttime_utc.strftime('%Y%m%d_%H%M%S.%f'),  'Time of observation '))
        header.append(fits.Card('UTCISO',       image_starttime_utc_object.iso,                         'Time of observation in ISO format'))
        header.append(fits.Card('UTCSHUT',      self.image_starttime_utc.strftime('%Y%m%d_%H%M%S.%f'),  'UTC time shutter open'))
        header.append(fits.Card('UTC-OBS',      self.image_starttime_utc.strftime('%Y%m%d %H%M%S.%f'),  'UTC time shutter open'))
        header.append(fits.Card('DATE-OBS',     self.image_starttime_utc.strftime('%Y%m%d %H%M%S.%f'),  'UTC date of observation (MM/DD/YY)'))
        header.append(fits.Card('OBSJD',       image_starttime_utc_object.jd,                          'Julian day corresponds to UTC'))
        header.append(fits.Card('OBSMJD',      image_starttime_utc_object.mjd,                         'MJD corresponds to UTC'))
        
        obstime = Time(self.image_starttime_utc, scale = 'utc', location = self.site)
        lst_obj = obstime.sidereal_time('mean')
        header.append(fits.Card('OBSLST', lst_obj.to_string(unit = u.deg, sep = ':'),              'Mean LST corresponds to UTC'))
        
        
        ###### WEATHER PARAMETERS ######
        #UT_WEATH
        try:
            weather_datetime = datetime.fromtimestamp(state['dome_time_utc'])
            ut_weath = weather_datetime.strftime('%Y-%m-%d %H%M%S.%f')
        except Exception as e:
            print(f'could not get weather time, {e}')
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
        #CLOUDS
        
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
    
    def makeLastImgLink(self):
        # make a symbolic link so we can easily open the last image taken
        pass
    
    def getExposureTimeout(self):
        # estimate the total exposure timeout
        timeout_buffer = self.pollTimer_dt/1000
        self.getReadoutTime()
        self.exposureTimeout = self.cc._exposure[self.camnum] + self.readoutTime + timeout_buffer
    
    @Pyro5.server.expose
    def getLastImagePath(self):
        # send the image name back over the pyro server for obsLogging
        image_filename = self.lastfilename
        image_directory = self.image_directory
        
        return image_directory, image_filename
        
    @Pyro5.server.expose
    def doExposure(self, state = {}, image_suffix = None, dark = False):
        """
        self.cc.downloadimg(self.camnum, 
                            image_path = self.image_directory,
                            image_prefix = image_prefix,
                            image_suffix = self.image_suffix,
                            metadata = self.header)"""
        
        # should we use the shutter?
        if dark:
            self.useshutter = False
        else:
            self.useshutter = True
        
        # first update the timeout so that we properly timeout when calling this function
        self.getExposureTimeout()
        self.state.update({'exposureTimeout' : self.exposureTimeout})

        
        self.preventPollingSignal.emit()
        
        # record that we are doing an exposure
        self.doing_exposure = True
        self.state.update({'doing_exposure' : self.doing_exposure})
        
        # record the instrument state when image was triggered
        self.imagestate = state
        
        # wait for the current poll to be finished
        while self.doing_poll:
            time.sleep(0.5)
            self.log('poll still happening, waiting 0.5 seconds')
        
        
        if image_suffix is None:
            self.image_suffix = ''
        else:
            self.image_suffix = image_suffix
        
        self.image_starttime_utc = datetime.now(pytz.utc)
        
        filename_timestamp = self.image_starttime_utc.astimezone(self.local_timezone).strftime('%Y%m%d_%H%M%S')
        
        
        # set up the image prefix with the local time for easy filename lookup
        self.image_prefix = self.camname + f'{filename_timestamp}'
        
        self.log(f'IMAGE PATH: {self.image_directory}')
        self.log(f'IMAGE PREFIX: {self.image_prefix}')
        self.log(f'IMAGE SUFFIX: {self.image_suffix}')
        
        if self.image_suffix == '':
            suffix_to_use = ''
        else:
            suffix_to_use = f'_{self.image_suffix}'
        self.lastfilename = f'{self.image_prefix}_Camera{int(self.camnum)}{suffix_to_use}.fits'
        self.log(f'IMAGE WILL BE SAVED TO: {self.lastfilename}')
        
        # set up the exposure timer waittime
        waittime = self.cc._exposure[self.camnum] * 1000
        
        
        
        self.log(f'starting an exposure!')
        self.log(f'doExposure is being called in thread {threading.get_ident()}')
        
        
        
        # set up the image acquisition buffer
        self.cc.acquireimg(self.camnum)
        # NPL 7-30-21: added this sleep to avoid badness. settrigmode was timeing out,
        # and once this happened the camera would get stuck and require WSP reboot.
        time.sleep(0.5)
        # This settrigmode is absolutely essential, otherwise
        # the camera freezes up.  Every exposure.
        self.cc.settrigmode(self.camnum, '01', readback=False)
        
        # then start the exposure timer            
        self.log(f'starting {waittime}s timer to wait for exposure to finish')
        #self.expTimer.start(int(waittime))
        self.startExposureTimer.emit(waittime)
        
        # OPEN THE SHUTTER IF WE'RE DOING A LIGHT FRAME
        if self.useshutter:
            # open the shutter!!
            self.log('opening the shutter!')
            self.viscam.send_shutter_command(1)
        
            self.shutter_open_timestamp = datetime.utcnow().timestamp()
            
        
        else:
            # handle a dark image
            self.shutter_open_timestamp = 0
        
        # add the shutter open timestamp to the imagestate snapshot dictionary
            self.imagestate.update({'shutter_open_timestamp' : self.shutter_open_timestamp})
        
        self.log('got to the end of the doExposure method')
        pass
    
    def readImg(self):
        
        if self.useshutter:
            # CLOSE THE SHUTTER!
            self.log('closing the shutter!')
            self.viscam.send_shutter_command(0)
            
            self.shutter_close_timestamp = datetime.utcnow().timestamp()
            self.exptime_actual = self.shutter_close_timestamp - self.shutter_open_timestamp
        else:
            self.shutter_close_timestamp = 0
            self.exptime_actual = self.exptime
        
        # add the shutter close time to the imagestate snapshot dictionary
        self.imagestate.update({'shutter_close_timestamp' : self.shutter_close_timestamp})
        
        # add the exposure time actual to the state dict for monitoring
        self.state.update({'exptime_actual' : self.exptime_actual})
        # add the exposure time actual to the image state snapshot to record in the fits header
        self.imagestate.update({'exptime_actual' : self.exptime_actual})
        
        # double check the readout time
        self.getReadoutTime()
        
        waittime = self.readoutTime * 1000
        self.log(f'starting {self.readoutTime}s timer to wait for image to download')
        
        #self.readTimer.start(int(waittime))
        self.startReadTimer.emit(waittime)
        
        # emit a signal that we're done acquiring the image. useful for roboOperator
        self.imageAcquired.emit()
        
        # create a symlink to the last image taken
        self.makeSymLink_lastImage()
        pass
    
    def fetchImg(self):
        
        # prevent status polling while downloading the image so the buffer stays clear
        
        
        self.log(f'downloading image to directory: {self.image_directory}')
        # download the image from the cam buffer
        
        self.log(f'Image Prefix = {self.image_prefix}, type = {type(self.image_prefix)}')
        self.log(f'Image Suffix = {self.image_suffix}, type = {type(self.image_suffix)}')
        
        
        # update the header info and image suffix (some note) that got passed in
        self.header = self.getDefaultHeader(self.imagestate)
        
        self.cc.downloadimg(self.camnum, 
                            image_path = self.image_directory,
                            image_prefix = self.image_prefix,
                            image_suffix = self.image_suffix,
                            metadata = self.header)
        
        

        #self.cc.downloadimg(cameras,metadata=metadata,image_prefix=image_prefix,image_path=image_path,image_suffix=image_suffix)
        
        time.sleep(0.5)
        t=0
        while (t < 5):
            if(self.cc._imageState == self.cc.ImageState.REQUESTED):
                break
            else:
                time.sleep(0.5)
                t+=0.5
                
        self.cc._printMsg("Exposure Complete")
    
    
        # make a symbolic link to the last image
        #filename = image_prefix + self.
        #filepath = os.path.join(self.imagepath, )
        
        self.log(f'Exposure Complete')
        #time.sleep(40)
        # re-enable the polling
        self.allowPollingSignal.emit()
        
        # send out signal that the image has been saved to the directory
        self.imageSaved.emit()
        
        # update the state dictionary
        self.doing_exposure = False
        self.state.update({'doing_exposure' : self.doing_exposure})
        
        pass
    
    
    @Pyro5.server.expose
    def tecStop(self):
        #self.pollTimer.stop()
        self.log(f'sending command to ccd: setfpgactrlreg({self.camnum}, {"off"})')
        #self.cc.setfpgactrlreg(self.camnum, 'off')
        self.cc.setfpgactrlreg(self.camnum,'off')
        #self.pollTimer.start()
        pass
    
    @Pyro5.server.expose
    def tecStart(self):
        #self.pollTimer.stop()
        
        self.log(f'sending command to ccd: setfpgactrlreg({self.camnum}, {"on"})')
        
        self.cc.setfpgactrlreg(self.camnum, 'on')
        #self.cc.setfpgactrlreg('00','on')
        #self.pollTimer.start()
        pass
    
    def getReadoutTime(self):
        #self.log(f'trying to get readout time, note: readout clock = {self.readoutclock}, type(readout clock) = {type(self.readoutclock)}')
        #self.readoutTime = (2049 * 2048)/self.readoutclock
        
        # The download request comes early and
        # seems unreliable for exposure times below
        # ~5 seconds, for reasons that aren't fully clear.
        # This fixes the problem, at the expense of unfavorable
        # overheads for exposures < about 3 secs, which is
        # probably OK.
        if (self.cc._exposure[self.camnum] > 5):
            timebuffer = 5
        else:
            timebuffer = 5
        
        #OVERWRITE TIME BUFFER TO MAKE SURE THERE'S ENOUGH LAG TO GET THE IMAGE
        timebuffer = 10
        
        readouttime =  self.cc._naxis1[self.camnum] * self.cc._naxis2[self.camnum] \
                       / self.cc._readoutclock[self.camnum]
        
        self.readoutTime = readouttime + timebuffer
        #self.log(f'setting readout waittime to {readouttime} (readout) + {timebuffer} (buffer) = {self.readoutTime}')
        
        
    # Return the Current Status (the status is updated on its own)
    @Pyro5.server.expose
    def GetStatus(self):
        # make a note of the time that the status was requested
        self.state.update({'request_timestamp' : datetime.utcnow().timestamp()})
        
        return self.state
        

    @Pyro5.server.expose
    def reconnect(self):
        #self.pollTimer.stop()
        try:
            # first kill any running instances of the server daemon
            self.huaso_server_pids = daemon_utils.getPIDS('huaso_server')
            if len(self.huaso_server_pids) > 0:
                self.log(f'found instances of huaso_server running with PIDs = {self.huaso_server_pids}')
            else:
                self.log(f'no instances of huaso_server already running')
            
            daemon_utils.killPIDS(self.huaso_server_pids, logger = self.logger)
            
            
            # re-init the daemon
            self.daemonlist = daemon_utils.daemon_list()
            
            self.log(f'relaunching huaso_server from {server_daemon_path}')
            self.serverd = daemon_utils.PyDaemon(name = 'huaso_server>/home/winter/data/huaso_server.log', filepath = server_daemon_path, python = False)
            self.daemonlist.add_daemon(self.serverd)
            # launch the daemon
            self.daemonlist.launch_all()
            
            # we got here so I think the server is running. 
            # BUT this isn't really a guarentee.. we haven't probed it yet but it's probably fine if we get here
            self.server_running = True
        
        except Exception as e:
            self.log(f'could not start launch server due to {type(e)}: {e}')
            self.server_running = False
        
        # init the camera client
        # do this in a while loop but have a timeout
        t_elapsed = 0
        dt = 0.5
        timeout = 10.0
        
        while t_elapsed < timeout:
            try:
                #self.cc = cameraClient.CameraClient('huaso_server', ('localhost', 43322))
                #self.connected = self.cc._connect()
                # 7-15-21 updating with Rob's new huaso_server client approach
                self.cc = cameraClient.CameraClient('SUMMER', ('localhost', 43322), verbose = False, debug = False)
                self.connected = self.cc._connect()
            except:
                self.connected = False
            
            if self.connected:
                break
            else:
                time.sleep(dt)
                t_elapsed += dt
            
            
            
        if self.connected:
            
            # Do some startup things
            
            self.log(">> successfully connected to huaso_server!")
            
            
            # Download current trigger mode:
            # gettrigmode return byte array, LSB is what we switch
            #    '00' = continuous parallel dump
            #    '01' = software trigger (use this when integrating)
            #camdict['settrigmode']('all','00')
            
            #NPL 7-15-21: deprecated.  DON"T DO THIS ANYMORE
            #self.cc.settrigmode(self.camnum, '00')
            
            #self.startStatusLoop.emit()
            
            # get the readout speed
            self.readoutclock = self.cc.getreadoutclock(self.camnum)[self.camnum]
            
            #self.startStatusLoop.emit()
            # wait a few seconds before starting up the housekeeping loop
            waittime = 5
            
            # poll the initial status
            self.pollStatus()
            
            self.log(f">> waiting to {waittime} s to start camera polling")
            time.sleep(waittime)
            self.statusThread.start()
        else:
            self.log(">> error: Could not connect to huaso_server")
            
        #self.pollTimer.start()
        



class PyroGUI(QtCore.QObject):   

    Tell_CCD_To_Read_Image = QtCore.pyqtSignal()              
    Tell_CCD_To_Download_Image = QtCore.pyqtSignal()
    
    def __init__(self, config, logger = None, verbose = False, parent=None):            
        super(PyroGUI, self).__init__(parent)   
        print(f'main: running in thread {threading.get_ident()}')
        
        self.config = config
        self.logger = logger
        self.verbose = verbose
        
        msg = f'(Thread {threading.get_ident()}: Starting up CCD Daemon '
        if logger is None:
            print(msg)
        else:
            logger.info(msg)

        
        # set up an alert handler so that the dome can send messages directly
        auth_config_file  = wsp_path + '/credentials/authentication.yaml'
        user_config_file = wsp_path + '/credentials/alert_list.yaml'
        alert_config_file = wsp_path + '/config/alert_config.yaml'
        
        auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
        user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
        alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)
        
        self.alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config) 
        
        self.logger.info(f'initializing ccd object in thread {threading.get_ident()}')
        
        ##### Define the timers which will be used to sequence the image taking #####
        # exposure timer
        self.expTimer = QtCore.QTimer()
        self.expTimer.setSingleShot(True)
        #self.expTimer.timeout.connect(self.readImg)
        self.expTimer.timeout.connect(self.expTimerComplete)
        
        # readout timer
        self.readTimer = QtCore.QTimer()
        self.readTimer.setSingleShot(True)
        #self.readTimer.timeout.connect(self.fetchImg)
        self.readTimer.timeout.connect(self.readTimerComplete)
        
        ##### DEFINE THE CCD #####
        
        self.ccd = CCD(camnum = '00', config = config, logger = logger, verbose = verbose)
        
        # Connect the signals 
        #self.counter.runTimerSignal.connect(self.timer.start)
        
        self.ccd.startExposureTimer.connect(self.startExpTimer)
        self.Tell_CCD_To_Read_Image.connect(self.ccd.readImg)
        
        self.ccd.startReadTimer.connect(self.startReadTimer)
        self.Tell_CCD_To_Download_Image.connect(self.ccd.fetchImg)
        
        
        self.logger.info(f'trying to do all the stupid pyro stuff now...? ')

        
        
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.ccd, name = 'ccd')
        self.pyro_thread.start()
        
    
    def startExpTimer(self, waittime):
        self.logger.info(f'starting exposure timer, waittime = {waittime}')
        self.expTimer.setInterval(waittime)
        self.expTimer.start()
        
    def expTimerComplete(self):
        self.logger.info(f'exposure timer complete! telling ccd to read image')
        self.Tell_CCD_To_Read_Image.emit()

    def startReadTimer(self, waittime):
        self.logger.info(f'starting readout timer, waittime = {waittime}')
        waittime_int = int(waittime)
        self.readTimer.setInterval(waittime_int)
        self.readTimer.start()
        
    def readTimerComplete(self):
        self.logger.info(f'readout timer complete! telling ccd to download image')
        self.Tell_CCD_To_Download_Image.emit()
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    try:
        # shutdown the camera client nicely
        main.ccd.cc._shutdown()
    except:
        pass
    #main.counter.daqloop.quit()
    
    QtCore.QCoreApplication.quit()




if __name__ == "__main__":
    
    print(f'the main lives in thread {threading.get_ident()}')
    
    #### GET ANY COMMAND LINE ARGUMENTS #####
    
    args = sys.argv[1:]
    
    
    modes = dict()
    modes.update({'-v' : "Running in VERBOSE mode"})
    modes.update({'-p' : "Running in PRINT mode (instead of log mode)."})
    
    # set the defaults
    verbose = True
    doLogging = True

    
    #print(f'args = {args}')
    
    if len(args)<1:
        pass
    
    else:
        for arg in args:
            
            if arg in modes.keys():
                
                # remove the dash when passing the option
                opt = arg.replace('-','')
                if opt == 'v':
                    print(modes[arg])
                    verbose = True
                    
                elif opt == 'p':
                    print(modes[arg])
                    doLogging = False

            else:
                print(f'Invalid mode {arg}')
    

    
    
    
    
    
    
    ##### RUN THE APP #####
    app = QtCore.QCoreApplication(sys.argv)

    # set the wsp path as the base directory
    base_directory = wsp_path

    # load the config
    config_file = base_directory + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    
    
    # set up the logger
    if doLogging:
        logger = logging_setup.setup_logger(base_directory, config)    
    else:
        logger = None
    
    # set up the main app. note that verbose is set above
    main = PyroGUI(config = config, logger = logger, verbose = verbose)

    # handle the sigint with above code
    signal.signal(signal.SIGINT, sigint_handler)
    # Murder the application (reference: https://stackoverflow.com/questions/4938723/what-is-the-correct-way-to-make-my-pyqt-application-quit-when-killed-from-the-co)
    #signal.signal(signal.SIGINT, signal.SIG_DFL)


    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(100) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())



