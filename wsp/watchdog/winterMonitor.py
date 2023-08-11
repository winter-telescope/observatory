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
from Pyt5 import QtCore
from datetime import datetime

class WINTERmonitor(QtCore.QObject):
    
    """
    This is the pyro object that handles the creation of the dirfile,
    polling the published state from the Pyro nameserver, and updating the
    dirfile.
    
    NOTE:
        This inherets from QObject, which allows it to have custom signals
        which can communicate with the communication threads
    """
    
    
    def __init__(self, monitor_config, logger, verbose = False):
        super(WINTERmonitor, self).__init__()
        
        self.monitor_config = monitor_config
        self.logger = logger
        self.verbose = verbose
        self.avgwindow = self.monitor_config['tavg']
        self.timestamp = datetime.utcnow().timestamp()
        self.timestamps = []
        
        # 

    def setupAvgVals(self):
        self.avgdict = dict()
        self.avgdict.update({'timestamps' : []})
        for field in self.monitor_config:
            self.avgdict.update({f'{field}_arr' : []})
            self.avgdict.update({f'{field}_avg' : []})
            
    def updateAvgVals(self, state):
        # read in the state and update all the averages
        self.timestamp = datetime.utcnow().timestamp()
        
        self.timestamps.update(self.timestamp)
        timearr = self.avgdict['timestamps']
        timestamp_condition = self.timestamps[self.timestamps - self.timestamps[-1] > (-1.0*(self.avgwindow))]
        
        for field in self.monitor_config['fields']:
            # append the new data from state, and replace missing vals with nan
            arr = self.avgdict[f'{field}_arr']
            arr.append(state.get(field, np.nan))
            # trim so that we only have times within the average window
            arr = arr[timestamp_condition]
            # update the dict with the new array
            self.avgdict.update({f'{field}_arr' : arr})
            # update the averages
            self.avgdict.update({f'{field}_avg' : np.average(arr)})
        
            
            
    def evalState(self, state):
        """
        check the state against the field limits in the monitor_config
        """
        too_high = []
        too_low = []
        bad_read = []
        
        for field in self.monitor_config:
            try:
                if self.avgdict[f'{field}_avg'] > self.monitor_config[field]['max']:
                    too_high.append(field)
                if self.avgdict[f'{field}_avg'] < self.monitor_config[field]['min']:
                    too_low.append(field)
                if np.isnan(self.avgdict[f'{field}_avg']):
                    bad_read.append(field)
                

                
                