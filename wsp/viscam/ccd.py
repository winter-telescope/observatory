#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  1 16:22:38 2021

ccd.py

This file is part of wsp

# PURPOSE #
This class represents the local interface between WSP and the viscam daemon.


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
import time
import json
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'ccd: wsp_path = {wsp_path}')
from utils import utils
from utils import logging_setup
from housekeeping import data_handler


#class local_dome(object):
class local_ccd(QtCore.QObject):    
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
    
    imageSaved = QtCore.pyqtSignal()
    
    def __init__(self, base_directory, config, logger, verbose = False):
        super(local_ccd, self).__init__()
        
        # Define attributes
        self.base_directory = base_directory
        self.config = config
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
            self.remote_hk_state_object = Pyro5.client.Proxy("PYRONAME:state")
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
                pass    
        
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
            self.remote_object = Pyro5.client.Proxy("PYRONAME:ccd")
            self.connected = True
        except:
            self.connected = False
            pass
        '''
        except Exception:
            self.logger.error('connection with remote object failed', exc_info = True)
        '''
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
                #(f'ccd: could not update remote state: {e}')
                pass
            
            # get the last image name
            try:
                self.image_directory, self.image_filename = self.remote_object.getLastImagePath()
            except Exception as e:
                self.image_directory = 'UNKNOWN'
                self.image_filename = 'UNKNOWN'
                if self.verbose:
                    self.logger.error(f'ccd: could not get last image filename due to {e}')#', {tb.format_exc()}')
    
    def getLastImagePath(self):
        
        image_directory = self.image_directory
        image_filename = self.image_filename
        
        return image_directory, image_filename
            
    def parse_state(self):
        '''
        Do any conditioning we need to properly handle and parse the state dictionary
        '''
        """ 
        # things that have to do with querying server
        self.state.update({'last_command_reply'             :   self.remote_state.get('command_reply', self.default)})
        self.state.update({'query_timestamp'                :   self.remote_state.get('timestamp', self.default)})
        self.state.update({'reconnect_remaining_time'       :   self.remote_state.get('reconnect_remaining_time', self.default)})
        self.state.update({'reconnect_timeout'              :   self.remote_state.get('reconnect_timeout', self.default)})
        """
        # update the rest of the stuff
        for key in self.remote_state.keys():
            self.state.update({key : self.remote_state[key]})
        
        self.state.update({'is_connected'                   :   bool(self.remote_state.get('is_connected', self.default))})
        
        self.imageSavedFlag = self.state.get('imageSavedFlag', False)
        """
        if self.imageSavedFlag:
            self.logger.info(f'local_ccd: image saved flag is True!')
            self.imageSaved.emit()
            self.resetImageSavedFlag()
        """
    def resetImageSavedFlag(self):
        self.logger.info(f'local ccd: resetting image saved flag')
        #self.remote_object.resetImageSavedFlag()
        self.remote_object.requestResetImageSavedFlag()
    def print_state(self):
        self.update_state()
        print(f'state = {json.dumps(ccd.state, indent = 2)}')
        
    
    def setexposure(self, exptime):
        self.remote_object.setexposure(exptime)
        
    def setSetpoint(self, temp):
        self.remote_object.setSetpoint(temp)
        
    def doExposure(self, dark = False):
        # first get the housekeeping state
        self.update_hk_state()
        
        # now dispatch the observation
        
        try:
            self.remote_object.doExposure(state = self.hk_state, dark = dark)
        except Exception as e:
            print(f'Error: {e}, PyroError: {Pyro5.errors.get_pyro_traceback()}')
            
    def tecStart(self):
        self.remote_object.tecStart()
        
    def tecStop(self):
        self.remote_object.tecStop()
    
    def getExposure(self):
        exptime = self.remote_object.getExposure()
    
        #print(f'exposure time = {exptime}')
    
    # some polling functions
    def pollStatus(self):
        self.remote_object.pollStatus()
    def pollExptime(self):
        self.remote_object.pollExptime()
    def pollTECTemp(self):
        self.remote_object.pollTECTemp()
    def pollTECSetpoint(self):
        self.remote_object.pollTECSetpoint()
    def pollPCBTemp(self):
        self.remote_object.pollPCBTemp()
    def pollTECStatus(self):
        self.remote_object.pollTECStatus()
    
    def shutdownCameraClient(self):
        self.remote_object.shutdownCameraClient()
        
    def reconnectServer(self):
        self.remote_object.triggerReconnect()
        #self.remote_object.reconnect()
        
    def killServer(self):
        self.remote_object.killServer()
'''
    def setSetpoint(self, temperature):
        #print(f'ccd: trying to set the set point to {temperature}')
        self.remote_object.setSetpoint(temperature)
    
    def TurnOn(self):
        self.remote_object.TurnOn()
    
    def TurnOff(self):
        self.remote_object.TurnOff()
    
    def WriteRegister(self, register, value):
        self.remote_object.WriteRegister(register, value)
   '''     
        
# Try it out
if __name__ == '__main__':


    config = utils.loadconfig(wsp_path + '/config/config.yaml')
        
    logger = logging_setup.setup_logger(wsp_path, config)        
    
    ccd = local_ccd(wsp_path, config, logger)
    
    ccd.print_state()
    
    
    while False:
        try:
            ccd.update_state()
            ccd.print_state()
            time.sleep(1)
            
        except KeyboardInterrupt:
            break
    
