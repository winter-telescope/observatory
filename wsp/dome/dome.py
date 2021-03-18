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
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(1, wsp_path)

from utils import utils




#class local_dome(object):
class local_dome(QtCore.QObject):    
    '''
    Using a QObject so that it can signals. The problem is that all the Pyro
    calls for a given proxy have to be handled in a single thread. To execute commands
    from outside this thread let's try using the signal/slot approach.
    '''
    newCommand = QtCore.pyqtSignal(object)
    
    def __init__(self, base_directory, config):
        super(local_dome, self).__init__()
        
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
            self.remote_object = Pyro5.client.Proxy("PYRONAME:dome")
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
                print(f'dome: could not update remote state: {e}')
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
        
        
        utc = self.remote_state.get('UTC', '1970-01-01 00:00:00.00') # last query timestamp
        utc_datetime_obj = datetime.strptime(utc, '%Y-%m-%d %H:%M:%S.%f')        # last query time string
        timestamp = utc_datetime_obj.timestamp()
        self.state.update({'UTC_timestamp' : timestamp})
        
        self.state.update({'Dome_Azimuth'                   :   self.remote_state.get('Dome_Azimuth',                     self.default)})
        
        Dome_Status = self.remote_state.get('Dome_Status', 'FAULT')               # status of observatory dome
        self.state.update({'Dome_Status_Num'                :   self.config['status_dict']['Dome_Status'].get(Dome_Status,       self.default) })
        
        Shutter_Status = self.remote_state.get('Shutter_Status','FAULT')
        self.state.update({'Shutter_Status_Num'             :   self.config['status_dict']['Shutter_Status'].get(Shutter_Status, self.default) })
        
        Control_Status = self.remote_state.get('Control_Status','FAULT')
        self.state.update({'Control_Status_Num'             :   self.config['status_dict']['Control_Status'].get(Control_Status, self.default) })
        
        Close_Status = self.remote_state.get('Close_Status','FAULT')
        self.state.update({'Close_Status_Num'               :   self.config['status_dict']['Close_Status'].get(Close_Status,     self.default) })
        
        Weather_Status = self.remote_state.get('Weather_Status','FAULT')
        self.state.update({'Weather_Status_Num'             :   self.config['status_dict']['Weather_Status'].get(Weather_Status, self.default) })

        self.state.update({'Outside_Dewpoint_Threshold'     :   self.remote_state.get('Outside_Dewpoint_Threshold',     self.default)})
        self.state.update({'Average_Wind_Speed_Threshold'   :   self.remote_state.get('Average_Wind_Speed_Threshold',   self.default)})
        self.state.update({'Outside_Temp'                   :   self.remote_state.get('Outside_Temp',                   self.default)})
        self.state.update({'Outside_RH'                     :   self.remote_state.get('Outside_RH',                     self.default)})
        self.state.update({'Outside_Dewpoint'               :   self.remote_state.get('Outside_Dewpoint',               self.default)})
        self.state.update({'Average_Wind_Speed'             :   self.remote_state.get('Average_Wind_Speed',               self.default)})
        self.state.update({'Weather_Hold_time'              :   self.remote_state.get('Weather_Hold_time',              self.default)})
        
        
        
        
        """
        self.PCS_UTC                        = self.status_PCS.get('UTC', '1970-01-01 00:00:00.00') # last query timestamp
        self.PCS_UTC_datetime_obj           = datetime.strptime(self.PCS_UTC, '%Y-%m-%d %H:%M:%S.%f')        # last query time string
        self.PCS_UTC_timestamp              = self.PCS_UTC_datetime_obj.timestamp()                          # last read timestamp
        self.PCS_Dome_Azimuth               = self.status_PCS.get('Dome_Azimuth', default)                                # azimuth of observatory dome
        self.PCS_Dome_Status                = self.status_PCS.get('Dome_Status', 'FAULT')               # status of observatory dome
        self.PCS_Dome_Status_Num            = self.config['status_dict']['Dome_Status'].get(self.PCS_Dome_Status, default)
        self.PCS_Shutter_Status             = self.status_PCS.get('Shutter_Status','FAULT')
        self.PCS_Shutter_Status_Num         = self.config['status_dict']['Shutter_Status'].get(self.PCS_Shutter_Status, default)
        
        self.PCS_Control_Status             = self.status_PCS.get('Control_Status','FAULT')
        self.PCS_Control_Status_Num         = self.config['status_dict']['Control_Status'].get(self.PCS_Control_Status, default)
        
        self.PCS_Close_Status               = self.status_PCS.get('Close_Status','FAULT')
        self.PCS_Close_Status_Num           = self.config['status_dict']['Close_Status'].get(self.PCS_Close_Status, default)
        
        self.PCS_Weather_Status             = self.status_PCS.get('Weather_Status','FAULT')
        self.PCS_Weather_Status_Num         = self.config['status_dict']['Weather_Status'].get(self.PCS_Weather_Status, default)
        
        self.PCS_Outside_Dewpoint_Threshold = self.status_PCS.get('Outside_Dewpoint_Threshold',default)
        self.PCS_Outside_Temp               = self.status_PCS.get('Outside_Temp', default)
        self.PCS_Outside_RH                 = self.status_PCS.get('Outside_RH', default)
        self.PCS_Outside_Dewpoint           = self.status_PCS.get('Outside_Dewpoint', default)
        self.PCS_Weather_Hold_time          = self.status_PCS.get('Weather_Hold_time', default)
    
        """
    
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
    
    def Home(self):
        #print(f'dome: tryin to Home dome')
        try:
            self.remote_object.Home()
        except:
            pass
    
    def Close(self):
        try:
            self.remote_object.Close()
        except:
            pass
    
    def Open(self):
        try:
            self.remote_object.Open()
        except:
            pass
        
    def Stop(self):
        try:
            self.remote_object.Stop()
        except:
            pass
    
    def TakeControl(self):
        try:
            self.remote_object.TakeControl()
        except:
            pass
    
    def GiveControl(self):
        try:
            self.remote_object.GiveControl()
        except:
            pass
    
    def GoTo(self, az):
        try:
            self.remote_object.GoDome(az)
        except:
            pass

    
    def print_state(self):
        self.update_state()
        print(f'Local Object Status: {self.state}')
        
        
# Try it out
if __name__ == '__main__':

    config = utils.loadconfig(wsp_path + '/config/config.yaml')
    """
    while True:
        try:
            dome = local_dome(wsp_path, config)
            dome.print_state()
            time.sleep(.5)
            dome.Home()
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
    