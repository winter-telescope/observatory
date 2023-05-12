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
import numpy as np
import sys
import Pyro5.core
import Pyro5.server
import Pyro5.errors
import traceback as tb
from datetime import datetime
from PyQt5 import QtCore
import logging
import time
import json
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'camera: wsp_path = {wsp_path}')
from utils import utils
from utils import logging_setup
from housekeeping import data_handler


class local_camera(QtCore.QObject):    
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
    
    imageSaved = QtCore.pyqtSignal()
    
    def __init__(self, base_directory, config, daemon_pyro_name,
                 pyro_ns_host = None,
                 logger = None, verbose = False,
                 ):
        super(local_camera, self).__init__()
        
        # Define attributes
        self.base_directory = base_directory
        self.config = config
        self.daemonname = daemon_pyro_name # the name that the camera daemon is registered under
        self.ns_host = pyro_ns_host # the ip address of the pyro name server, eg `192.168.1.10`
        self.state = dict()
        self.hk_state = dict()
        self.remote_state = dict()
        self.connected = False
        self.hk_connected = False
        self.logger = logger
        self.default = self.config['default_value']
        self.verbose = verbose
        
        # placeholders for getting the image parameters from ccd_daemon
        self.image_directory = 'UNKNOWN'
        self.image_filename = 'UNKNOWN'
        
        # connect the signals and slots
        self.newCommand.connect(self.doCommand)
                
        # Startup
        # setup connection to pyro ccd
        self.init_remote_object()
        self.update_state()
        
        # setup connection to pyro state
        self.init_hk_state_object()
        self.update_hk_state()
        
    ### Things for getting the housekeeping state from the Pyro Server ###
    
    def init_hk_state_object(self):
        # init the remote object
        try:
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = self.ns.lookup("state")
            self.remote_hk_state_object = Pyro5.client.Proxy(uri)
            self.hk_connected = True
        except:
            self.hk_connected = False
            pass
        '''
        except Exception:
            self.logger.error('connection with remote object failed', exc_info = True)
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
                    self.logger.info(f'local ccd could not update remote housekeeping state: {e}')
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
            uri = self.ns.lookup(self.daemonname)
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
        if not self.connected:
            self.init_remote_object()
            
        else:
            try:
                self.remote_state = self.remote_object.GetStatus()
                
                
                self.parse_state()
                
                
            except Exception as e:
                #self.log(f'camera: could not update remote state: {e}')
                pass
            
            # get the last image name
            try:
                self.image_directory, self.image_filename = self.remote_object.getLastImagePath()
            except Exception as e:
                self.image_directory = 'UNKNOWN'
                self.image_filename = 'UNKNOWN'
                if self.verbose:
                    self.logger.error(f'ccd: could not get last image filename due to {e}')#', {tb.format_exc()}')
    
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    
    def getLastImagePath(self):
        
        image_directory = self.image_directory
        image_filename = self.image_filename
        
        return image_directory, image_filename
            
    def parse_state(self):
        '''
        Do any conditioning we need to properly handle and parse the state dictionary
        '''
         
        
        # update the rest of the stuff
        for key in self.remote_state.keys():
            self.state.update({key : self.remote_state[key]})
        
        self.state.update({'is_connected'                   :   bool(self.remote_state.get('is_connected', self.default))})
        
        
        
    
    def print_state(self):
        self.update_state()
        print(f'state = {json.dumps(self.state, indent = 2)}')
        
    
    def setExposure(self, exptime):
        self.remote_object.setexposure(exptime)
                
    def doExposure(self, obstype = 'test', addr = []):
        # first get the housekeeping state
        self.update_hk_state()
        
        # now dispatch the observation
        
        try:
            self.remote_object.doExposure(state = self.hk_state, obstype = obstype, addr = addr)
        except Exception as e:
            print(f'Error: {e}, PyroError: {Pyro5.errors.get_pyro_traceback()}')
        
    def tecSetSetpoint(self, temp, addr = []):
        self.remote_object.tecSetSetpoint(temp, addr = addr)
    
    def tecStart(self, addr = []):
        self.remote_object.tecStart(addr = addr)
        
    def tecStop(self, addr = []):
        self.remote_object.tecStop(addr = addr)
    
    
    def shutdownCameraClient(self, addr = []):
        self.remote_object.shutdownCameraClient(addr = addr)
        
    def reconnectCameraDaemon(self, addr = []):
        self.remote_object.reconnectCameraDaemon(addr = addr)
        #self.remote_object.reconnect()
        
    def killCameraDaemon(self):
        self.remote_object.killCameraDaemon()

        
# Try it out
if __name__ == '__main__':


    config = utils.loadconfig(wsp_path + '/config/config.yaml')
        
    logger = logging_setup.setup_logger(wsp_path, config)        
    
    cam = local_camera(wsp_path, config, logger, daemon_pyro_name = 'camsim')
    
    cam.print_state()
    
    
    while False:
        try:
            cam.update_state()
            cam.print_state()
            time.sleep(1)
            
        except KeyboardInterrupt:
            break
    
