#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 24 14:37:29 2023

# camera.py

This file is part of WSP

# PURPOSE #
Generic WSP Camera Object: interface between the camera and camera pyro daemon

@author: nlourie
"""

import os
#import numpy as np
import sys
import Pyro5.core
import Pyro5.server
import Pyro5.errors
#import traceback as tb
from datetime import datetime
from PyQt5 import QtCore
import logging
import time
import astropy.io.fits as fits
import json
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'camera: wsp_path = {wsp_path}')
from utils import utils
from utils import logging_setup
#from housekeeping import data_handler
try:
    import fitsheader
except:
    from camera import fitsheader

class local_camera(QtCore.QObject):    
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
    
    imageSaved = QtCore.pyqtSignal()
    
    def __init__(self, base_directory, config, camname, daemon_pyro_name,
                 ns_host = None,
                 logger = None, verbose = False,
                 ):
        super(local_camera, self).__init__()
        
        # Define attributes
        self.base_directory = base_directory
        self.config = config
        self.camname = camname
        self.daemonname = daemon_pyro_name # the name that the camera daemon is registered under
        self.ns_host = ns_host # the ip address of the pyro name server, eg `192.168.1.10`
        self.state = dict()
        self.hk_state = dict()
        self.remote_state = dict()
        self.connected = False
        self.hk_connected = False
        self.logger = logger
        self.default = self.config['default_value']
        self.verbose = verbose
        
        # placeholders for getting the image parameters from ccd_daemon
        self.connected = 0
        self.imdir = ''
        self.imname = ''
        self.imstarttime = ''
        self.mode = None
        self.imtype = None
        
        
        # connect the signals and slots
        self.newCommand.connect(self.doCommand)
                
        # Startup
        # setup connection to pyro ccd
        self.init_remote_object()
        self.update_state()
        
        # setup connection to pyro state
        self.init_hk_state_object()
        self.update_hk_state()
        
        
    def log(self, msg, level = logging.INFO):
        msg = f'{self.daemonname}_local: {msg}'
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg) 
    
    ### Things for getting the housekeeping state from the Pyro Server ###
    
    def init_hk_state_object(self):
        # init the remote object
        try:
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = ns.lookup("state")
            self.remote_hk_state_object = Pyro5.client.Proxy(uri)
            self.hk_connected = True
        except:
            self.hk_connected = False
            pass
        '''
        except Exception:
            self.log('connection with remote object failed', exc_info = True)
        '''
    def update_hk_state(self):
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        if not self.hk_connected:
            self.init_hk_state_object()
            
        else:
            try:
                self.hk_state = self.remote_hk_state_object.GetStatus()
                
            except Exception as e:
                if self.verbose:
                    self.log(f'could not update remote housekeeping state: {e}')
                self.hk_connected = False    
        
    ###    
    def doCommand(self, cmd_obj):
        """
        This is connected to the newCommand signal. It parses the command and
        then executes the corresponding command from the list below

        using this as a reference: (source: https://stackoverflow.com/questions/6321940/how-to-launch-getattr-function-in-python-with-additional-parameters)     
        
        """
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs
        
        #print(f'ccd: caught doCommand signal: {cmd}, args = {args}, kwargs = {kwargs}')

        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass
        
    def init_remote_object(self):
        # init the remote object
        try:
            if self.verbose:
                self.log(f'init_remote_object: trying to connect to {self.daemonname}')
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = ns.lookup(self.daemonname)
            self.remote_object = Pyro5.client.Proxy(uri)
            self.connected = True
        except Exception as e:
            self.connected = False
            if self.verbose:
                self.log(f'connection to remote object failed: {e}')
            pass
        
    def update_state(self):
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        #self.log(f'updating remote state: self.connected = {self.connected}')
        
        if not self.connected:
            if self.verbose:
                self.log(f'self.connected = {self.connected}: try to init_remote_object again')
            self.init_remote_object()
        
        if not self.hk_connected:
            self.init_hk_state_object()
        
        else:
            try:
                #self.log(f'updating remote state')
                self.remote_state = self.remote_object.getStatus()
            except Exception as e:
                if self.verbose:
                    self.log(f'camera: could not update remote state: {e}')
                self.connected = False
                pass    
           
            try:
                self.parse_state()
                
                
            except Exception as e:
                if self.verbose:
                    self.log(f'camera: could not parse remote state: {e}')
                #self.connected = False
                pass
            
            # get the last image name
            """
            try:
                self.image_directory, self.image_filename = self.remote_object.getLastImagePath()
            except Exception as e:
                self.image_directory = 'UNKNOWN'
                self.image_filename = 'UNKNOWN'
                if self.verbose:
                    self.log(f'could not get last image filename due to {e}')#', {tb.format_exc()}')
            """
    
    
    def getLastImagePath(self):
        
        return self.imdir, self.imname
            
    def parse_state(self):
        '''
        Do any conditioning we need to properly handle and parse the state dictionary
        '''
         
        
        # update the rest of the stuff
        for key in self.remote_state.keys():
            self.state.update({key : self.remote_state[key]})
    
        #self.state.update({'is_connected'                   :   bool(self.remote_state.get('is_connected', self.default))})
        self.state.update({'camname' : self.camname,
                           'is_connected' : self.connected,
                           'imdir'        : self.imdir,
                           'imname'       : self.imname,
                           'imstarttime'  : self.imstarttime,
                           'imtype'       : self.imtype,
                           })
        
    def getFITSheader(self):
        #self.log(f'making default header')
        # make the baseline header
        try:
            header = fitsheader.GetHeader(self.config, self.hk_state, self.state)
        except Exception as e:
            self.log(f'could not build default header: {e}')
            header = []

        
        
        #self.log('now adding sensor specific fields')
        # now add some sensor specific stuff
        for addr in self.state.get('addrs', ['sa', 'sb', 'sc', 'pa', 'pb', 'pc']):
            try:
                header.append((f'{addr}TPID'.upper(),          self.state.get(f'{addr}_T_pid', ''),        f'{addr} FPA PID Temp (C)'))
                header.append((f'{addr}TFPA'.upper(),          self.state.get(f'{addr}_T_fpa', ''),        f'{addr} FPA Temp (C)'))
                header.append((f'{addr}TROIC'.upper(),         self.state.get(f'{addr}_T_roic', ''),       f'{addr} ROIC Temp (C)'))
                header.append((f'{addr}TECST'.upper(),         self.state.get(f'{addr}_tec_status', ''),   f'{addr} TEC Status'))
                header.append((f'{addr}TECSP'.upper(),         self.state.get(f'{addr}_tec_setpoint', ''), f'{addr} TEC Status'))
                header.append((f'{addr}TECV'.upper(),          self.state.get(f'{addr}_V_tec', ''),        f'{addr} TEC Voltage (V)'))
                header.append((f'{addr}TECI'.upper(),          self.state.get(f'{addr}_I_tec', ''),        f'{addr} TEC Current (A)'))
            except Exception as e:
                self.log(f'could not add {addr} FPA Card entries: {e}')
        #print(f'got FITS header: {header}')
        self.header = header
        return header   
    
    def print_state(self):
        self.update_state()
        print(f'state = {json.dumps(self.state, indent = 2)}')
        
    #### CAMERA API METHODS ####
    def setExposure(self, exptime, addrs = None):
        self.remote_object.setExposure(exptime, addrs = addrs)
                
    def doExposure(self, imdir=None, imname = None, imtype = None, mode = None, addrs = None):
        
        
        
        
        
        # now dispatch the observation
        self.log(f'running doExposure')     
        
        self.imstarttime = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")[:-3]

        if imname is None:
            
            
            imname = f'{self.daemonname}_{self.imstarttime}'
            
        self.imname = imname
        
        if imdir is None:
            #imdir = os.path.join(os.getenv("HOME"), 'data', 'images', 'tmp')
            #imdir = 'default'
            imdir = self.remote_object.getDefaultImageDirectory()
        self.imdir = imdir
        
        if imtype is None:
            imtype = 'test'
        self.imtype = imtype
        
        if mode is None:
            mode = 'cds'
        self.mode = mode
        
        
        
        self.log(f'updating state dictionaries')
        # make sure all the state dictionaries are up-to-date
        # update the camera state by querying the camera daemon
        self.update_state()
        # update the housekeeping state by grabbing it from the housekeeping server
        self.update_hk_state()
        
        #print(f'hk_state = {self.hk_state}')
        #print()
        #print(f'state = {self.state}')
        
        # now make the fits header
        self.log(f'making FITS header')
        header = self.getFITSheader()
        #print(f'header = {header}')
        self.log(f'sending doExposure request to camera: imdir = {self.imdir}, imname = {self.imname}')
        try:
            self.remote_object.doExposure(imdir = self.imdir, imname = self.imname, imtype = self.imtype, mode = self.mode, metadata = header, addrs = addrs)
        except Exception as e:
            print(f'Error: {e}, PyroError: {Pyro5.errors.get_pyro_traceback()}')
    
    def tecSetSetpoint(self, temp, addrs = None):
        self.remote_object.tecSetSetpoint(temp, addrs = addrs)
        
    def setDetbias(self, detbias, addrs = None):
        self.remote_object.setDetbias(detbias, addrs = addrs)
    
    def tecSetCoeffs(self, Kp, Ki, Kd, addrs = None):
        self.remote_object.tecSetCoeffs(Kp, Ki, Kd, addrs = addrs)
    
    def tecSetVolt(self, volt, addrs = None):
        self.remote_object.tecSetVolt(volt, addrs = addrs)
    
    def tecStart(self, addrs = None):
        self.remote_object.tecStart(addrs = addrs)
        
    def tecStop(self, addrs = None):
        self.remote_object.tecStop(addrs = addrs)
        
    def startupCamera(self, addrs = None):
        self.remote_object.startupCamera(addrs = addrs)
        
    def shutdownCamera(self, addrs = None):
        self.remote_object.shutdownCamera(addrs = addrs)
        
    def restartSensorDaemon(self, addrs = None):
        self.remote_object.restartCameraDaemon(addrs = addrs)
        #self.remote_object.reconnect()
    def killCameraDaemon(self):
        self.remote_object.killCameraDaemon()
    

        
# Try it out
if __name__ == '__main__':


    config = utils.loadconfig(wsp_path + '/config/config.yaml')
        
    logger = logging_setup.setup_logger(wsp_path, config)        
    
    logger = None
    verbose = True
    
    """
    def __init__(self, base_directory, config, daemon_pyro_name,
                 pyro_ns_host = None,
                 logger = None, verbose = False,
                 ):
    """
    cam = local_camera(wsp_path, config, camname = 'winter',
                       daemon_pyro_name = 'WINTERcamera',
                       ns_host = '192.168.1.10', logger = logger, verbose = verbose)
    
    cam.print_state()
    
    """
    while True:
        try:
            #cam.update_state()
            cam.print_state()
            time.sleep(1)
            
        except KeyboardInterrupt:
            break
    """
