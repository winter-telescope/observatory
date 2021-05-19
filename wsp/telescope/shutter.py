#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  8 14:34:39 2021

dome.py

This is part of wsp

# Purpose #

This program contains the software interface for the WINTER telescope dome,
including a dome class that contains the necessary commands to communicate
with the telescope dome


@author: nlourie
"""


import os
import numpy as np
import sys
import Pyro5.core
import Pyro5.server
from datetime import datetime
from PyQt5 import QtCore
import time
import json
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(1, wsp_path)

from utils import utils




#class local_dome(object):
class local_shutter(QtCore.QObject):    
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
    
    def __init__(self, base_directory, config):
        super(local_shutter, self).__init__()
        
        # Define attributes
        self.base_directory = base_directory
        self.config = config
        self.state = dict()
        self.remote_state = dict()
        self.connected = False
        self.default = self.config['default_value']
        
        
        # connect the signals and slots
        self.newCommand.connect(self.doCommand)
        
        # Startup
        self.init_remote_object()
        self.update_state()
        
        
        
    def init_remote_object(self):
        # init the remote object
        try:
            self.remote_object = Pyro5.client.Proxy("PYRONAME:shutter")
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
                print(f'shutter: could not update remote state: {e}')
                pass
    
    
    def parse_state(self, ):
        '''
        Do any conditioning we need to properly handle and parse the state dictionary
        '''
        # things that have to do with querying server
        self.state.update({'last_command_reply'             :   self.remote_state.get('command_reply', self.default)})
        self.state.update({'query_timestamp'                :   self.remote_state.get('timestamp', self.default)})
        self.state.update({'reconnect_remaining_time'       :   self.remote_state.get('reconnect_remaining_time', self.default)})
        self.state.update({'reconnect_timeout'              :   self.remote_state.get('reconnect_timeout', self.default)})
        self.state.update({'is_connected'                   :   bool(self.remote_state.get('is_connected', self.default))})
        
        # timestamp of last reply
        utc = self.remote_state.get('UTC', '1970-01-01 00:00:00.00') # last query timestamp
        utc_datetime_obj = datetime.strptime(utc, '%Y-%m-%d %H:%M:%S.%f')        # last query time string
        timestamp = utc_datetime_obj.timestamp()
        #self.state.update({'UTC_timestamp' : timestamp})
        self.state.update({'timestamp' : timestamp})
        
        self.state.update({'open_status'                :   self.remote_state.get('Open_Status',                  self.default)})

        
    
    def doCommand(self, cmd_obj):
        """
        This is connected to the newCommand signal. It parses the command and
        then executes the corresponding command from the list below

        using this as a reference: (source: https://stackoverflow.com/questions/6321940/how-to-launch-getattr-function-in-python-with-additional-parameters)     
        
        """
        #print(f'dome: caught doCommand signal: {cmd_obj.cmd}')
        cmd = cmd_obj.cmd
        args = cmd_obj.args
        kwargs = cmd_obj.kwargs
        
        try:
            getattr(self, cmd)(*args, **kwargs)
        except:
            pass
    

    def Close(self):
        #print(f'dome: trying to CLOSE dome')
        try:
            self.remote_object.Close()
        except:
            pass
    
    def Open(self):
        #print(f'dome: trying to OPEN dome')
        try:
            self.remote_object.Open()
        except:
            pass
        
    def Stop(self):
        try:
            self.remote_object.Stop()
        except:
            pass
    
    

    def print_state(self):
        self.update_state()
        print(f'Local Object Status: {json.dumps(self.state, indent = 2)}')
        
        
# Try it out
if __name__ == '__main__':

    config = utils.loadconfig(wsp_path + '/config/config.yaml')
    
    shutter = local_shutter(wsp_path, config)

    while True:
        try:
            shutter.print_state()
            time.sleep(.5)
            #dome.Home()
            time.sleep(0.5)
        except KeyboardInterrupt:
            break
    """
    
    dome = local_dome(wsp_path, config)
    dome.remote_state.update({'Dome_Status' : 'UNKNOWN',
                              'Shutter_Status' : 'STOPPED',
                              'Control_Status' : 'CONSOLE',
                              'Close_Status' : 'READY',
                              'Weather_Status' : 'READY'})
    
    dome.parse_state()
    """