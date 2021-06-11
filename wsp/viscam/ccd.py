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



#class local_dome(object):
class local_ccd(QtCore.QObject):    
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
    
    def __init__(self, base_directory, config, logger):
        super(local_ccd, self).__init__()
        
        # Define attributes
        self.base_directory = base_directory
        self.config = config
        self.state = dict()
        self.remote_state = dict()
        self.connected = False
        self.logger = logger
        self.default = self.config['default_value']
        
        # connect the signals and slots
        self.newCommand.connect(self.doCommand)
        
        # Startup
        self.init_remote_object()
        self.update_state()
        
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
                #print(f'ccd: could not update remote state: {e}')
                pass
    
    def parse_state(self):
        '''
        Do any conditioning we need to properly handle and parse the state dictionary
        '''
        """ # things that have to do with querying server
        self.state.update({'last_command_reply'             :   self.remote_state.get('command_reply', self.default)})
        self.state.update({'query_timestamp'                :   self.remote_state.get('timestamp', self.default)})
        self.state.update({'reconnect_remaining_time'       :   self.remote_state.get('reconnect_remaining_time', self.default)})
        self.state.update({'reconnect_timeout'              :   self.remote_state.get('reconnect_timeout', self.default)})
        """
        # update the rest of the stuff
        for key in self.remote_state.keys():
            self.state.update({key : self.remote_state[key]})
        
        self.state.update({'is_connected'                   :   bool(self.remote_state.get('is_connected', self.default))})
        
        
            
    def print_state(self):
        self.update_state()
        print(f'state = {json.dumps(ccd.state, indent = 2)}')
        
    
    def setexposure(self, exptime):
        self.remote_object.setexposure(exptime)
        
    def setSetpoint(self, temp):
        self.remote_object.setSetpoint(temp)
        
    def doExposure(self):
        try:
            self.remote_object.doExposure()
        except Exception as e:
            print(f'Error: {e}, PyroError: {Pyro5.errors.get_pyro_traceback()}')
    def tecStart(self):
        self.remote_object.tecStart()
        
    def tecStop(self):
        self.remote_object.tecStop()
        
    
        
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
    
    
    while True:
        try:
            ccd.update_state()
            ccd.print_state()
            time.sleep(1)
            
        except KeyboardInterrupt:
            break
    
