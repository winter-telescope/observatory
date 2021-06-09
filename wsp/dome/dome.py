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
#import numpy as np
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
        
        # initialize a home azimuth
        self.home_az = self.config['telescope']['home_az_degs']
        
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
                #print(f'dome: could not update remote state: {e}')
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
        
        self.state.update({'Telescope_Power'                :   self.remote_state.get('Telescope_Power',                  self.default)})
        self.state.update({'Dome_Azimuth'                   :   self.remote_state.get('Dome_Azimuth',                     self.default)})
        
        self.Dome_Status = self.remote_state.get('Dome_Status', 'FAULT')               # status of observatory dome
        self.state.update({'Dome_Status_Num'                :   self.config['Dome_Status_Dict']['Dome_Status'].get(self.Dome_Status,       self.default) })
        
        self.Home_Status = self.remote_state.get('Home_Status', 'NOT_READY')               # status of whether dome needs to be homed
        self.state.update({'Home_Status_Num'                :   self.config['Dome_Status_Dict']['Home_Status'].get(self.Home_Status,       self.default) })
        
        """ FOR TESTING WITHOUT OPENING SHUTTER ONLY!!!!! """
        self.Shutter_Status = "OPEN"
        #self.Shutter_Status = self.remote_state.get('Shutter_Status','FAULT')
        self.state.update({'Shutter_Status_Num'             :   self.config['Dome_Status_Dict']['Shutter_Status'].get(self.Shutter_Status, self.default) })
        
        self.Control_Status = self.remote_state.get('Control_Status','FAULT')
        self.state.update({'Control_Status_Num'             :   self.config['Dome_Status_Dict']['Control_Status'].get(self.Control_Status, self.default) })
        
        self.Close_Status = self.remote_state.get('Close_Status','FAULT')
        self.state.update({'Close_Status_Num'               :   self.config['Dome_Status_Dict']['Close_Status'].get(self.Close_Status,     self.default) })
        
        self.Weather_Status = self.remote_state.get('Weather_Status','FAULT')
        self.state.update({'Weather_Status_Num'             :   self.config['Dome_Status_Dict']['Weather_Status'].get(self.Weather_Status, self.default) })

        self.Sunlight_Status = self.remote_state.get('Sunlight_Status','NOT_READY')
        self.state.update({'Sunlight_Status_Num'             :   self.config['Dome_Status_Dict']['Sunlight_Status'].get(self.Sunlight_Status, self.default) })
        
        self.Wetness_Status = self.remote_state.get('Wetness','NOT_READY')
        self.state.update({'Wetness_Status_Num'             :   self.config['Dome_Status_Dict']['Wetness_Status'].get(self.Wetness_Status, self.default) })
        
        self.state.update({'Outside_Dewpoint_Threshold'     :   self.remote_state.get('Outside_Dewpoint_Threshold',     self.default)})
        self.state.update({'Average_Wind_Speed_Threshold'   :   self.remote_state.get('Average_Wind_Speed_Threshold',   self.default)})
        self.state.update({'Outside_Temp'                   :   self.remote_state.get('Outside_Temp',                   self.default)})
        self.state.update({'Outside_RH'                     :   self.remote_state.get('Outside_RH',                     self.default)})
        self.state.update({'Outside_Dewpoint'               :   self.remote_state.get('Outside_Dewpoint',               self.default)})
        self.state.update({'Pressure'                       :   self.remote_state.get('Pressure',                       self.default)})
        self.state.update({'Wind_Direction'                 :   self.remote_state.get('Wind_Direction',                 self.default)})
        self.state.update({'Average_Wind_Speed'             :   self.remote_state.get('Average_Wind_Speed',             self.default)})
        self.state.update({'Weather_Hold_time'              :   self.remote_state.get('Weather_Hold_time',              self.default)})
        
        # Handle the fault code. This uses the Dome_Status_Dict from the config file
        self.Faults = self.remote_state.get('Faults', 0)
        for fault_code in self.config['Dome_Status_Dict']['Faults']:
            if self.Faults & fault_code:
                
                # print the message (ie log it)
                #print(self.config['Dome_Status_Dict']['Faults'][fault_code]['msg'])
                    
                # assign the variable to true
                self.state.update({self.config['Dome_Status_Dict']['Faults'][fault_code]['field'] : 1})
            else:
                # assign the variable to false
                self.state.update({self.config['Dome_Status_Dict']['Faults'][fault_code]['field'] : 0})
        
        self.dome_ok = (self.Dome_Status != 'UNKNOWN') & (self.Home_Status == 'READY') & (self.Shutter_Status != 'UNKNOWN') & (self.Control_Status == 'REMOTE') & (self.Close_Status == 'READY')
        self.state.update({'dome_ok' : self.dome_ok})
        self.weather_ok =  (self.Weather_Status == 'READY') & (self.Sunlight_Status == 'READY') & (self.Wetness_Status == 'READY')
        self.state.update({'weather_ok' : self.weather_ok})
        self.faults_ok = (self.Faults == 0)
        self.state.update({'faults_ok' : self.faults_ok})
        
        self.ok_to_open = self.dome_ok & self.weather_ok & self.faults_ok
        self.state.update({'ok_to_open' : self.ok_to_open})
    
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
        #print(f'dome: trying to HOME dome')
        try:
            self.remote_object.Home()
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
    
    def TakeControl(self):
        #print(f'dome: trying to TAKE control')
        try:
            self.remote_object.TakeControl()
        except:
            pass
    
    def GiveControl(self):
        #print(f'dome: trying to GIVE control')

        try:
            self.remote_object.GiveControl()
        except:
            pass
    
    def GoTo(self, az):
        #print(f'dome: trying to move dome to AZ = {az}')
        try:
            self.remote_object.GoDome(az)
        except:
            pass

    def SetHome(self, az):
        try:
            self.home_az = az
        except:
            pass
        
    """def GoHome(self):
        try:
            self.remote_object.GoDome(self.home_az)
        except:
            pass"""

    def print_state(self):
        self.update_state()
        print(f'Local Object Status: {json.dumps(self.state, indent = 2)}')
        
        
# Try it out
if __name__ == '__main__':

    config = utils.loadconfig(wsp_path + '/config/config.yaml')
    
    dome = local_dome(wsp_path, config)

    while True:
        try:
            dome.print_state()
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