#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 16:13:17 2020

housekeeping.py

This file is part of wsp

# PURPOSE #
This module has dedicated QThread loops that run at various times 
and log system information.

@author: nlourie
"""

# system packages
import sys
import os
import numpy as np
import time
from datetime import datetime
from PyQt5 import uic, QtCore, QtGui, QtWidgets
import pathlib

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter modules
from housekeeping import easygetdata as egd
from housekeeping import data_handler

# the main housekeeping class it lives in the namespace of the control class

class housekeeping():                     
    def __init__(self, config, telescope = None, weather = None, schedule = None):            
        
        
        # store the config
        self.config = config
        
        # redefine the methods passed in: ie the hardware systems
        self.telescope = telescope
        self.weather = weather
        self.schedule = schedule
        # define the housekeeping data dictionaries
        # samples per frame for each daq loop
        self.spf = dict()
        
        # current state values
        self.state = dict()
        
        # vectors holding all the samples in the current frame
        self.curframe = dict()
        
        # build the dictionaries for current data and fame
        self.build_dicts()
        
        # create the dirfile
        self.create_dirfile()
        
        # define the DAQ loops
        self.daq_telescope = data_handler.daq_loop(config = self.config,
                                                   func = self.telescope.update_state, 
                                                   rate = 'fast')
        
        self.daq_weather = data_handler.daq_loop(config = self.config,
                                                 func = self.weather.getWeather,
                                                 rate = 'slow')
        
        # define the status update loops
        self.fastloop = data_handler.fast_loop(config = self.config, 
                                               state = self.state, 
                                               curframe = self.curframe, 
                                               telescope = self.telescope)
        self.slowloop = data_handler.slow_loop(config = self.config, 
                                               state = self.state, 
                                               curframe = self.curframe,
                                               weather = self.weather,
                                               schedule = self.schedule)
        
        # define the dirfile write loop
        self.writethread = data_handler.write_thread(config = config, dirfile = self.df, state = self.state, curframe = self.curframe)
        
        print("Done init'ing housekeeping")
        
        
    
                
    def create_dirfile(self):
        """
        Create the dirfile to hold the data from the DAQ loops
        All the fields from the config file will be added automatically
        """
        # create the dirfile directory
        hk_dir = os.getenv("HOME") + '/' + self.config['housekeeping_data_directory']
        
        now = datetime.utcnow() # or can use now for local time
        #now = str(int(now.timestamp())) # give the name the current ctime
        now_str = now.strftime('%Y%M%d_%H%M%S') # give the name a more readable date format
        self.dirname = now_str + '.dm'
        self.dirpath = hk_dir + '/' + self.dirname
        
        # create the directory and filenames for the data storage
        hk_link_dir = os.getenv("HOME") + '/' + self.config['housekeeping_data_link_directory']
        hk_link_name = self.config['housekeeping_data_link_name']
        hk_linkpath = hk_link_dir + '/' + hk_link_name
        
        # create the data directory if it doesn't exist already
        pathlib.Path(hk_dir).mkdir(parents = True, exist_ok = True)
        print(f'housekeeping: making directory: {hk_dir}')
                
        # create the data link directory if it doesn't exist already
        pathlib.Path(hk_link_dir).mkdir(parents = True, exist_ok = True)
        print(f'housekeeping: making directory: {hk_link_dir}')
        
        # create the dirfile database
        self.df = egd.EasyGetData(self.dirpath, "w")
        print(f'housekeeping; creating dirfile at {self.dirpath}')
        #/* make a link to the current dirfile - kst can read this to make life easy... */
        print(f'housekeeping: trying to create link at {hk_linkpath}')
        
        try:
            os.symlink(self.dirpath, hk_linkpath)
        except FileExistsError:
            print('housekeeping: deleting existing symbolic link')
            os.remove(hk_linkpath)
            os.symlink(self.dirpath, hk_linkpath)
        
        # add the fields from the config file to the dirfile
        for field in self.config['fields']:
            self.df.add_raw_entry(field = field, 
                                  spf = self.spf[self.config['fields'][field]['rate']],
                                  dtype = np.dtype(self.config['fields'][field]['dtype']),
                                  units = self.config['fields'][field]['units'],
                                  label = self.config['fields'][field]['label'])
        
        
        
    def build_dicts(self):
        """
        gets the fields and daq rates from the config file
        uses daq rates to calculate the samples per frame (spf) of each 
        field and build the vectors to hold the data for the current frame
        """
        
        # go through each daq loop in the config file and build the HK dictionaries
        for rate in self.config['daq_dt']:
            # calculate the spf for each daq loop
            spf = int(self.config['write_dt']/self.config['daq_dt'][rate])
            self.spf.update({rate : spf})
            print(f'{rate} daq loop: {spf} samples per frame')
            
        # go through all the fields
        for field in self.config['fields']:
            
            # add an item to the state dictionary, initialize with zeros
            self.state.update({field : None})
            print(f'housekeeping: adding field "{field}"')
            
            # add a numpy array item to the curframe dictionary
            spf = self.spf[self.config['fields'][field]['rate']]
            dtype = np.dtype(self.config['fields'][field]['dtype'])         
            self.curframe.update({field : np.full(spf, 0, dtype = dtype)})
            #print(f'adding vector with len = {spf} and type {dtype} to current frame dictionary')


        
        
        