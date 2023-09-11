#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 11 12:53:45 2023

winterMonitor.py

this is a class which parses the current WINTER status dictionary and looks to 
see if there are any scary problems. if there are, it will raise various flags.



@author: nlourie
"""
import numpy as np
import logging
from PyQt5 import QtCore
from datetime import datetime

class WINTER_monitor(QtCore.QObject):
    
    """
    This is the pyro object that handles the creation of the dirfile,
    polling the published state from the Pyro nameserver, and updating the
    dirfile.
    
    NOTE:
        This inherets from QObject, which allows it to have custom signals
        which can communicate with the communication threads
    """
    
    
    def __init__(self, monitor_config, logger, verbose = False):
        super(WINTER_monitor, self).__init__()
        
        self.monitor_config = monitor_config
        self.logger = logger
        self.verbose = verbose
        self.default_value = -888

        self.timestamp = datetime.utcnow().timestamp()
        
        self.lockout = False
        self.lockout_enable = True
        self.setup_avg_vals()
        #self.setup_temp_slope_vals()
        
        
    def log(self, msg, level = logging.INFO):
        
        msg = f'winterMonitor: {msg}'
        
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
        
    def clear_lockout(self):
        """
        clear any lockout conditions.
        """
        self.lockout = True

    def setup_avg_vals(self):
        """
        dictionary to hold average values of various parameters to monitor.
        Using the avg values because these can be very noisy and this will help
        prevent the values from triggering shutdowns just on noise
        """
        self.avgdict = dict()
        self.avgdict.update({'avg_timestamps' : np.array([])})
        for field in self.monitor_config['prestart_conditions']['fields']:
            self.avgdict.update({f'{field}_arr' : np.array([])})
            self.avgdict.update({f'{field}_avg' : self.default_value})
            
    def update_avg_vals(self, state):
        """
        take in a state dictionary, then update all the arrays the corresponding
        average values to use for monitoring whether the camera is in okay
        shape.
        """
        # read in the state and update all the averages
        self.timestamp = datetime.utcnow().timestamp()
                
        timestamps = np.append(self.avgdict['avg_timestamps'], self.timestamp)
        
        timestamp_condition = timestamps - timestamps[-1] > (-1.0*(self.monitor_config['prestart_conditions']['dt_window']))
        timestamps = timestamps[timestamp_condition]
        self.avgdict['avg_timestamps'] = timestamps
        
        for field in self.monitor_config['prestart_conditions']['fields']:
            # append the new data from state, and replace missing vals with nan
            arr = self.avgdict[f'{field}_arr']
            newval = state.get(field, np.nan)
            if newval == 999:
                # skip it, it's just startup junk
                pass
            else:
                arr = np.append(arr, newval)
                # trim so that we only have times within the average window
                arr = arr[timestamp_condition]
                # update the dict with the new array
                self.avgdict.update({f'{field}_arr' : arr})
                # update the averages
                self.avgdict.update({f'{field}_avg' : np.average(arr)})
        
        #print(f'avgdict = {self.avgdict["Flow_LJ0_3_avg"]}')
    
    def setup_temp_slope_vals(self):
        """
        dictionary to hold temperature values and temperature change slopes
        to monitor whether the TEC is hitting its commanded temperature in time
        """
        self.temp_slope_dict = dict()
        self.temp_slope_dict.update({'slope_timestamps' : []})
        for field in self.monitor_config['tec_temps']['fields']:
            self.temp_slope_dict.update({f'{field}_arr' : []})
            self.temp_slope_dict.update({f'{field}_slope' : self.default_value})
            
    
    def update_temp_slope_vals(self, state):
        """
        take in a state dictionary, then update all the arrays and the
        corresponding temperature slope values to use for monitoring whether 
        camera TEC is hitting its desired temperature.
        """
        # read in the state and update all the averages
        self.timestamp = datetime.utcnow().timestamp()
        
        # we don't want to do this at arbitrary time precision, these
        # vectors will get huge. Make sure it's been enough time in between
        # samples
        
        dt_since_last_sample = self.timestamp - self.temp_slop_dict['slope_timestamps'][-1]
        
        if dt_since_last_sample > self.monitor_config['tec_temps']['dt_min']:
        
            self.temp_slope_dict['slope_timestamps'].update(self.timestamp)
            
            timestamps = self.temp_slope_dict['slope_timestamps']
            timestamp_condition = timestamps[timestamps - timestamps[-1] > (-1.0*(self.monitor_config['tec_temps']['dt_window']))]
            
            for field in self.monitor_config['tec_temps']['fields']:
                # append the new data from state, and replace missing vals with nan
                arr = self.temp_slope_dict[f'{field}_arr']
                arr.append(state.get(field, np.nan))
                # trim so that we only have times within the average window
                arr = arr[timestamp_condition]
                # update the dict with the new array
                self.temp_slope_dict.update({f'{field}_arr' : arr})
                # update the averages
                try:
                    self.temp_slope_dict.update({f'{field}_slope' : np.polyfit(self.temp_slope_dict['slope_timestamps'], self.temp_slope_dict[f'{field}_arr'], 1)})
                except Exception as e:
                    if self.verbose:
                        self.log(f'could not update slope calculation for {field}: {e}')
                    self.temp_slope_dict.update({f'{field}_slope' : None})
    
    def get_alarms(self, state):
        """
        check the state against the field limits in the monitor_config
        """
        too_high = []
        too_low = []
        bad_read = []
        alarms = []
        
        self.update_avg_vals(state)
        #self.update_temp_slope_vals()
        
        # if the camera is powered, we need everything to be within range
        camera_powered = self.get_camera_powered_status(state)
        if camera_powered:
            
            # Check if things are generally in range. Driven by config file
            for field in self.monitor_config['prestart_conditions']['fields']:
                maxval = self.monitor_config['prestart_conditions']['fields'][field]['max']
                minval = self.monitor_config['prestart_conditions']['fields'][field]['min']
                try:
                    if type(maxval) is str:
                        if maxval.lower() == 'none':
                            pass
                    else:
                        if self.avgdict[f'{field}_avg'] > maxval:
                            too_high.append(field)
                            alarms.append(f'{field} TOO HIGH')
                    if type(minval) is str:
                        if minval.lower() == 'none':
                            pass
                    else:
                        if self.avgdict[f'{field}_avg'] < minval:
                            too_low.append(field)
                            alarms.append(f'{field} TOO LOW')
                    #if np.isnan(self.avgdict[f'{field}_avg']):
                    #    bad_read.append(field)
                    #    alarms.append(f'{field} NOT READING')
                
                except Exception as e:
                    self.log(f'could not evaluate state: {e}')
                    return
            
            # specific alarms:
            
            
            
            if self.verbose:
                if any(alarms):
                    self.log('FOUND ACTIVE ALARMS!! Camera is powered while these states are out of range:')
                    self.log(alarms)
        else:
            # don't worry about chiller being off if the camera isn't powered
            pass
        
        return alarms
    
    
    def get_depoint_alarm_status(self, state):
        
        pass
        
    
    
    
    def get_camera_powered_status(self, state):
        # is the PDU on?
        if state.get('pdu2_2', 0) == 1:
            pass
        else:
            return False
        
        # is the labjack enabled?
        power_enabled = [ state.get('fpa_port_power_disabled', 0) == 0,
                          state.get('fpa_star_power_disabled', 0) == 0]
        
        if any(power_enabled):
            pass
        else:
            return False
        
        # if we got here the camera is powered on:
        return True
        
    
    def get_camera_running_status(self, state):
        
        camera_powered = self.get_camera_powered_status(state)
        
        if camera_powered:
            pass
        else:
            return False
        
        cams_connected = [state['pa_connected'],
                          state['pb_connected'],
                          state['pc_connected'],
                          state['sa_connected'],
                          state['sb_connected'],
                          state['sc_connected'],
                          ]
        if any(cams_connected):
            pass
        else:
            return False
        
        
        
        return
                
    def get_ready_to_startup_status(self, state):
        
        return
    
    def get_ready_to_image_status(self):
        
        return
                
                