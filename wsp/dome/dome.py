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
import Pyro5.client
from datetime import datetime
from PyQt5 import QtCore
import time
import logging
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
    
    startTracking = QtCore.pyqtSignal()
    stopTracking = QtCore.pyqtSignal()
    moveDome = QtCore.pyqtSignal(object)
    
    def __init__(self, base_directory, config, ns_host = None, logger = None, telescope = None):
        super(local_dome, self).__init__()
        
        # Define attributes
        self.base_directory = base_directory
        self.config = config
        self.ns_host = ns_host
        self.logger = logger
        self.state = dict()
        self.remote_state = dict()
        self.connected = False
        self.default = self.config['default_value']
        self.telescope = telescope
        
        ## STUFF FOR TRACKING TELESCOPE MOTION ##
        # initialize a variable to control if we're tracking
        self.tracking = False
        self.tracking_error_threshold = self.config['dome_tracking_error_threshold']
        
        #self.trackingTimer = QtCore.QTimer()
        
        
        
        
        
        # initialize a home azimuth & an azimuth goal
        self.home_az = self.config['dome_home_az_degs']
        self.az_goal = self.home_az
        self.az_error = 0.0
        
        # init the last timestamp since dome was ok to open
        default_timestr = '1970-01-01 00:00:00.00' # last query timestamp
        utc_datetime_obj = datetime.strptime(default_timestr, '%Y-%m-%d %H:%M:%S.%f')        # last query time string
        timestamp = utc_datetime_obj.timestamp()
        self.last_ok_to_open_timestamp = timestamp
        
        # connect the signals and slots
        self.newCommand.connect(self.doCommand)
        self.moveDome.connect(self.GoTo)
        
        # Startup
        self.init_remote_object()
        self.update_state()
        
    def log(self, msg, level = logging.INFO):
        msg = f'local_dome: {msg}'
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)  
        
    def init_remote_object(self):
        # init the remote object
        try:
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = ns.lookup('dome')
            self.remote_object = Pyro5.client.Proxy(uri)
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
        
        #""" FOR TESTING WITHOUT OPENING SHUTTER ONLY!!!!! """
        #self.Shutter_Status = "OPEN"
        self.Shutter_Status = self.remote_state.get('Shutter_Status','FAULT')
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
        
        self.dome_ok = (
                                (self.Dome_Status != 'UNKNOWN') 
                            and (self.Home_Status == 'READY') 
                            and (self.Shutter_Status != 'UNKNOWN') 
                            and (self.Control_Status in ['REMOTE', 'AVAILABLE']) 
                            and (self.Close_Status == 'READY')
                        )
        self.state.update({'dome_ok' : self.dome_ok})
        self.weather_ok =  (
                                    (self.Weather_Status == 'READY')
                                and (self.Wetness_Status == 'READY')
                                #and (self.Sunlight_Status == 'READY') 
                            )
        self.state.update({'weather_ok' : self.weather_ok})
        self.faults_ok = (self.Faults == 0)
        self.state.update({'faults_ok' : self.faults_ok})
        
        self.ok_to_open = self.dome_ok and self.weather_ok and self.faults_ok 
        self.state.update({'ok_to_open' : self.ok_to_open})
        
        # update the last time the dome was okay to open
        if self.ok_to_open:
            self.last_ok_to_open_timestamp = timestamp
        # update the dt in seconds since the last time it was ok to open
        self.dt_since_last_ok_to_open = timestamp - self.last_ok_to_open_timestamp
        self.state.update({'dt_since_last_ok_to_open' : self.dt_since_last_ok_to_open})
        
        
        # record the azimuth goal of the dome
        self.state.update({'az_goal' : self.az_goal})
        self.state.update({'az_error' : self.az_error})
        
        # record if we're tracking
        self.state.update({'tracking' : int(self.tracking)})
        self.telescope_az = self.telescope.state["mount.azimuth_degs"]
        self.az_error = abs(self.telescope_az - self.az_goal)
        
        self.CheckTracking()
    
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
        #TODO: i might need to turn off dome tracking here
        #print(f'dome: trying to move dome to AZ = {az}')
        #self.log(f'doing dome_goto command. updating az_goal to {az}')
        # update the azimuth goal
        self.az_goal = az
        
        try:
            self.remote_object.GoDome(az)
        except:
            pass

    def SetHome(self, az):
        try:
            self.home_az = az
        except:
            pass
        
    def TrackingOn(self):
        self.log('turning on dome tracking')
        #self.startTracking.emit()
        self.tracking = True
        pass
    
    def TrackingOff(self):
        self.log('turning off dome tracking')
        #self.stopTracking.emit()
        self.tracking = False
    
    def CheckTracking(self):
        
        
        # if we're supposed to be tracking, see if we're within the allowed error from the telescope az
        if self.tracking:
            try:
                
                # if the telescope is slewing we don't need to update the tracking
                if self.telescope.state["mount.is_slewing"]:
                    pass
                else:
                    # try to calculate the az error
                    # we want the az_goal to always be within the tracking threshold of the telescope az
                    # self.az_error = abs(self.telescope_az - self.az_goal) <-- calculated in self.parse_state
                    if self.az_error > self.tracking_error_threshold:
                        #self.log(f'UPDATING DOME GOAL: self.az_error = {self.az_error}, self.az_goal = {self.az_goal}, self.tracking_error_threshold = {self.tracking_error_threshold}, self.telescope az = {self.telescope_az}, self.telescope.state["mount.azimuth_degs"] = {self.telescope.state["mount.azimuth_degs"]}')
                        self.moveDome.emit(self.telescope_az)
                
            except:
                # could not calcualte the az error
                pass
            
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
    
    dome = local_dome(wsp_path, config, ns_host = '192.168.1.10')

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