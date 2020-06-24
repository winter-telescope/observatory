#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 23 12:34:10 2020

data_handler.py

This file is part of wsp

# PURPOSE #
This module has dedicated QThread data acquisition (DAQ)loops that run at 
various times and log system information. It is instatiated by the 
housekeeping class.

A writer thread uses the pygetdata library to log the housekeeping data to 
dirfile directories using the getdata standard. This data is stored
as binary files, one for each field to be monitored from the housekeeping
script. These binary files and the database key, stored in the format file,
can be read and visualized in real time using KST.

@author: nlourie
"""




# system packages
import sys
import os
import numpy as np
import time
from datetime import datetime
from PyQt5 import uic, QtCore, QtGui, QtWidgets

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter modules
from housekeeping import easygetdata as egd


class slow_loop(QtCore.QThread):
    
    def __init__(self,config, state, curframe, weather):
        QtCore.QThread.__init__(self)
        # loop execution number
        self.index = 0
        
        # subclass the methods passed in (ie, the hardware systems)
        self.weather = weather
        
        
        # pass the config to the thread
        self.config = config
        
        # give thread access to these methods to update the data as it comes in
        self.state = state
        self.curframe = curframe

        self.dt = self.config['daq_dt']['slow']
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        #self.exec()
        
    def __del__(self):
        self.wait()
    
    def update(self):
        # Only print the even numbers
        self.index +=1
    
        ### UPDATE THE DATA ###
        
        # update weather
        self.weather.getWeather()
        
        
        ### MAP THE DATA TO THE STATUS FIELDS ###
        # describe the mapping between variables and data
        self.map = dict({
            'scount'            : self.index,
            'cds_cloud'         : self.weather.CDSCLOUD,
            'cloud_min'         : self.weather.CLOUD_MIN,
            'cloud_max'         : self.weather.CLOUD_MAX
            })
        
        # update the state and frame dictionaries
        for field in self.map.keys():
            curval = self.map[field]
            # update the state variables
            self.state.update({ field : curval })
        
            # update the vectors in the current frame
            # shift over the vector by one, then replace the last
            self.curframe[field] = np.append(self.curframe[field][1:], curval)
            
        #print(f'slowloop: count = {self.index}, state = {self.state}')
 
        
    def run(self):
        print("slowloop: starting")
        """
        while True:
            self.update()
            time.sleep(float(self.dt) / 1000.)
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        #self.exec()
        """
        print("slowloop: ending?")
        
class fast_loop(QtCore.QThread):
    
    def __init__(self,config, state, curframe, telescope):
        QtCore.QThread.__init__(self)
        
        # subclass the methods passed in (ie, the hardware systems)
        self.telescope = telescope
        
        
        # loop execution number
        self.index = 0
        
        # pass the config to the thread
        self.config = config
        
        # give thread access to these methods to update the data as it comes in
        self.state = state
        self.curframe = curframe
        
        # get the loop run time increment
        self.dt = self.config['daq_dt']['fast']
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        #self.exec()
        
    def __del__(self):
        self.wait()
    
    def update(self):
        # Only print the even numbers
        self.index +=1
        #print(f'fastloop: count = {self.index}')
        
        ### POLL THE DATA ###
        
        # poll telescope status
        self.telescope_status = self.telescope.status()
        
        
        ### MAP THE DATA TO THE STORED VARIABLES ###
        # describe the mapping between variables and data
        self.map = dict({
            'fcount'                : self.index,
            'mount_is_connected'    : int(self.telescope_status.mount.is_connected),
            'mount_is_slewing'      : int(self.telescope_status.mount.is_slewing),
            'mount_az_deg'          : self.telescope_status.mount.azimuth_degs,
            'mount_alt_deg'         : self.telescope_status.mount.altitude_degs
            
            })
        #print('datahandler: map = ', self.map)
        # update the state and frame dictionaries
        for field in self.map.keys():
            curval = self.map[field]
            # update the state variables
            self.state.update({ field : curval })
        
            # update the vectors in the current frame
            # shift over the vector by one, then replace the last
            self.curframe[field] = np.append(self.curframe[field][1:], curval)
        
    def run(self):
        print("fastloop: starting")
        """
        while True:
            self.update()
            time.sleep(float(self.dt) / 1000.)
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        #self.exec()
        """
        print("fastloop: ending?")

class write_thread(QtCore.QThread):
    
    def __init__(self,config, dirfile, state, curframe):
        QtCore.QThread.__init__(self)
        
        # pass the config to the thread
        self.config = config
        
        # give thread access to these methods to update the data as it comes in
        #self.state = state
        self.curframe = curframe
        self.db = dirfile
        
        self.index = 0
        self.dt = self.config['write_dt']
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        #self.exec()
        
    def __del__(self):
        self.wait()
    
    def update(self):
        # Only print the even numbers
        #print(f'state = {self.state}')
        #print('writethread: saving frame to dirfile')
        
        self.index +=1
        
        # write out all the fields in the current frame to the dirfile
        for field in self.curframe.keys():
            #print(f'writethread: writing to {field}: {self.curframe[field]}')
            self.db.write_field(field, self.curframe[field], start_frame = 'last')
            
        
    def run(self):
        print("writethread: starting")
        """
        while True:
            self.update()
            time.sleep(float(self.dt) / 1000.)
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        #self.exec()
        """
        print("writethread: ending?")
