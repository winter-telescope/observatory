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
import functools

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter modules
from housekeeping import easygetdata as egd
from telescope import pwi4

class slow_loop(QtCore.QThread):
    
    def __init__(self,config, state, curframe, weather):
        QtCore.QThread.__init__(self)
        # loop execution number
        self.index = 0
        self.timestamp = datetime.utcnow().timestamp()
        
        # subclass the methods passed in (ie, the hardware systems)
        self.weather = weather
        
        
        # pass the config to the thread
        self.config = config
        
        # give thread access to these methods to update the data as it comes in
        self.state = state
        self.curframe = curframe

        # describe the loop rate
        self.rate = 'slow'
        self.dt = self.config['daq_dt'][self.rate]

        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update_status)
        self.timer.start()
        #self.exec()
        print(f'datahandler: running slowloop update in thread {self.currentThread()}')

        
    def __del__(self):
        self.wait()
    
    def get(self, varname, default_val = -999):
        try:
            return eval( 'self.' + varname)
        except Exception as e:
            #print('could not get thing: ',e)
            return default_val
    
    def update_status(self, default_value = -999):
        self.index +=1
        self.timestamp = datetime.utcnow().timestamp()
        
        for field in self.config['fields']:
            if self.config['fields'][field]['rate'] == self.rate:
                # if the field is to be sampled at the loop rate, then log it
                try:
                    # update the state and frame dictionaries
                    curval = self.get(self.config['fields'][field]['var'])
                    self.state.update({field : curval})
                    
                    # update the vectors in the current frame
                    # shift over the vector by one, then replace the last
                    self.curframe[field] = np.append(self.curframe[field][1:], curval)
                except Exception as e:
                    """
                    we end up here if there's a problem either getting the field,
                    or with the config for that field. either way log it and 
                    just keep moving
                    """
                    #print(f'could not update field [{field}] due to {e.__class__}: {e}')
                    pass
            else:
                pass


        
class fast_loop(QtCore.QThread):
    
    def __init__(self,config, state, curframe, telescope):
        QtCore.QThread.__init__(self)
        
        # subclass the methods passed in (ie, the hardware systems)
        self.telescope = telescope
        
        
        # loop execution number
        self.index = 0
        self.timestamp = datetime.utcnow().timestamp()
        
        # pass the config to the thread
        self.config = config
        
        # give thread access to these methods to update the data as it comes in
        self.state = state
        self.curframe = curframe
        
        # describe the loop rate
        self.rate = 'fast'
        self.dt = self.config['daq_dt'][self.rate]

        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        #self.exec()
        print(f'datahandler: running fastloop update in thread {self.currentThread()}')
        
    def __del__(self):
        self.wait()
    
    def get(self, varname, default_val = -999):
        try:
            return eval( 'self.' + varname)
        except Exception as e:
            #print('could not get thing: ',e)
            return default_val
    
    def update_status(self, default_value = -999):
        #print('telescope mount az = ', self.telescope.state.mount.azimuth_degs)
        for field in self.config['fields']:
            if self.config['fields'][field]['rate'] == self.rate:
                # if the field is to be sampled at the loop rate, then log it
                try:
                    # update the state and frame dictionaries
                    curval = self.get(self.config['fields'][field]['var'])
                    self.state.update({field : curval})
                    
                    # update the vectors in the current frame
                    # shift over the vector by one, then replace the last
                    self.curframe[field] = np.append(self.curframe[field][1:], curval)
                except Exception as e:
                    """
                    we end up here if there's a problem either getting the field,
                    or with the config for that field. either way log it and 
                    just keep moving
                    """
                    #print(f'could not update field [{field}] due to {e.__class__}: {e}')
                    pass
            else:
                pass
    
    
    def update(self):
        # Update the loop number
        self.index +=1
        self.timestamp = datetime.utcnow().timestamp()

        """
        ### POLL THE DATA ###
        
        # poll telescope status
        try:
            self.telescope_status = self.telescope.status()
        except Exception as e:
            '''
            do nothing here. this avoids flooding the log with errors if
            the system is disconnected. Instead, this should be handled by the
            watchdog to signal/log when the system is offline at a reasonable 
            cadance.
            '''
            #self.telescope_status = pwi4.defaultPWI4Status()
            #print(f'could not poll telescope status: {type(e)}: {e}')
            pass
        """
        ### MAP THE DATA TO THE STORED VARIABLES ###
        self.update_status()
        
        
    """
    def run(self):
        print("fastloop: starting")
        '''
        while True:
            self.update()
            time.sleep(float(self.dt) / 1000.)
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        #self.exec()
        '''
        print("fastloop: ending?")
    """

class daq_loop(QtCore.QThread):
    """
    This is a generic QThread which will execute the specified function
    at the specified cadence.
    
    It is meant for polling different sensors or instruments or servers
    each in their own thread so they don't bog each other down.
    """
    def __init__(self, config, func, rate, *args, **kwargs):
        QtCore.QThread.__init__(self)
        
        # pass in methods from elsewhere
        self.config = config
        #self.telescope = telescope
        self.index = 0
        
        # define the function and options that will be run in this daq loop
        self.func = func
        self.args = args
        self.kwargs = kwargs
        
        # describe the loop rate
        self.rate = rate
        self.dt = self.config['daq_dt'][self.rate]

        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        #self.exec()
        print(f'datahandler: running daqloop of func: {self.func.__name__} in thread {self.currentThread()}')
    def __del__(self):
        self.wait()

    
    def update(self):
        
        
        ### POLL THE DATA ###
        
        try:
            #print(f'daq_loop: index = {self.index}')
            self.func(*self.args, **self.kwargs)
            #self.telescope.update_state()
        except Exception as e:
            '''
            do nothing, don't want to clog up the program with errors if there's 
            a problem. let this get handled elsewhere.
            '''
            #print(f'could not execute function {self.func.__name__} because of {type(e)}: {e}')
            pass
        
        
        self.index += 1


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
        print(f'datahandler: running dirfile write in thread {self.currentThread()}')

        
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
            
    '''
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
    '''