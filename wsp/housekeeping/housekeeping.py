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
from labjack import ljm
import astropy.coordinates
import astropy.units as u
import json
import Pyro5.server

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)

print(f'housekeeping: wsp_path = {wsp_path}')

# winter modules
from housekeeping import easygetdata as egd
from housekeeping import data_handler
from housekeeping import labjacks
from daemon import daemon_utils

# the main housekeeping class, it lives in the namespace of the control class



class housekeeping():                     
    def __init__(self, config, base_directory, mode = None, schedule = None, telescope = None, mirror_cover=None, dome = None, weather = None, chiller = None, pdu1 = None, counter = None, ephem = None, viscam = None, ccd = None, robostate = None):
        
        
        # store the config
        self.config = config
        self.base_directory = base_directory
        
        # define the housekeeping mode. this dictates which fields are read
        self.mode = mode
        
        # redefine the methods passed in: ie the hardware systems
        self.schedule = schedule
        self.telescope = telescope
        self.dome = dome
        self.weather = weather
        self.chiller = chiller
        self.pdu1 = pdu1
        self.counter = counter
        self.ephem = ephem
        self.viscam = viscam
        self.ccd = ccd
        self.mirror_cover = mirror_cover
        self.robostate = robostate
        # setup any labjacks that are in the config
        '''
        ### Labjack Definitions ###
        labjacks:
            lj0:
                config: 'labjack0_config.yaml'
        '''
        self.labjacks = labjacks.labjack_set(self.config, self.base_directory)
        #print(f"\nHOUSEKEEPING: lj0[AINO] = {self.labjacks.labjacks['lj0'].state['AIN0']}")
        
        #self.labjacks.read_all_labjacks()
        #print(f"\nHOUSEKEEPING: lj0[AINO] = {self.labjacks.labjacks['lj0'].state['AIN0']}")
        
 
        
        
        # define the housekeeping data dictionaries
        # samples per frame for each daq loop
        self.spf = dict()
        
        # current state values
        self.state = dict()
        
       
        
        # vectors holding all the samples in the current frame
        #NPL 6-1-21: removing the dirfile handling from wsp
        self.curframe = dict()
        
        # build the dictionaries for current data and fame
        self.build_dicts()
        
        # create the dirfile
        #NPL 6-1-21: removing the dirfile handling from wsp
        #self.create_dirfile()
        
        # create the housekeeping poll list
        self.housekeeping_poll_functions = list()
        
        
        # define the DAQ loops
        if mode.lower() in ['m','r']:
            self.daq_telescope = data_handler.daq_loop(func = self.telescope.update_state, 
                                                       dt = self.config['daq_dt']['hk'],
                                                       name = 'telescope_daqloop'
                                                       )
                                                       #rate = 'fast')
            # add NON INSTRUMENT status polls to housekeeping
            self.housekeeping_poll_functions.append(self.dome.update_state)
            self.housekeeping_poll_functions.append(self.ephem.update_state)
        
        self.daq_labjacks = data_handler.daq_loop(func = self.labjacks.read_all_labjacks,
                                                  dt = self.config['daq_dt']['hk'],
                                                  name = 'labjack_daqloop'
                                                  )
                                                  #rate = 'very_slow')
        
        # write the current state to a file
        
        
        self.statedump_loop = data_handler.daq_loop(func = self.dump_state,
                                                    dt = 5000,
                                                    name = 'state_dump')
        # add status polls that we CALL NO MATTER WHAT MODE to the housekeeping poll list
        self.housekeeping_poll_functions.append(self.counter.update_state)
        self.housekeeping_poll_functions.append(self.chiller.update_state)
        self.housekeeping_poll_functions.append(self.viscam.update_state)
        self.housekeeping_poll_functions.append(self.ccd.update_state)
        self.housekeeping_poll_functions.append(self.mirror_cover.update_state)

        self.hk_loop = data_handler.hk_loop(config = self.config, 
                                               state = self.state, 
                                               curframe = self.curframe,
                                               schedule = self.schedule,
                                               telescope = self.telescope,
                                               weather = self.weather,
                                               labjacks = self.labjacks,
                                               counter = self.counter,
                                               dome = self.dome,
                                               chiller = self.chiller,
                                               ephem = self.ephem,
                                               viscam = self.viscam,
                                               ccd = self.ccd,
                                               mirror_cover = self.mirror_cover,
                                               robostate = self.robostate)

        
        # define the dirfile write loop
        #NPL 6-1-21: removing the dirfile handling from wsp
        #self.writethread = data_handler.write_thread(config = config, dirfile = self.df, state = self.state, curframe = self.curframe)
        
        # start the housekeeping poll FROM THE MAIN EVENT LOOP
        self.start_housekeeping_poll_loop()
        print("Done init'ing housekeeping")
    
    @Pyro5.server.expose
    def GetStatus(self):
        return self.state
    
    def dump_state(self):
        filepath = os.path.join(os.getenv("HOME"), 'data','data.json')
        with open(filepath, 'w') as outfile:
            json.dump(self.state, outfile, indent = 2)
    
    def poll_housekeeping(self):
        """
        execute all the functions in the housekeeping_poll_functions
        """
        #print(f'housekeeping: {self.robostate}')
        for func in self.housekeeping_poll_functions:
            # do the function
            func()
            
    def start_housekeeping_poll_loop(self):
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.config['daq_dt']['hk'])
        self.timer.timeout.connect(self.poll_housekeeping)
        self.timer.start()
                
    def create_dirfile(self):
        """
        Create the dirfile to hold the data from the DAQ loops
        All the fields from the config file will be added automatically
        """
        # create the dirfile directory
        hk_dir = os.getenv("HOME") + '/' + self.config['housekeeping_data_directory']
        
        now = datetime.utcnow() # or can use now for local time
        #now = str(int(now.timestamp())) # give the name the current ctime
        now_str = now.strftime('%Y%m%d_%H%M%S') # give the name a more readable date format
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
            # add handling for the various field types ('ftype') allowed by the dirfile standards as they come up
            

            self.df.add_raw_entry(field = field, 
                                  spf = self.spf[self.config['fields'][field]['rate']],
                                  dtype = np.dtype(self.config['fields'][field]['dtype']),
                                  units = self.config['fields'][field]['units'],
                                  label = self.config['fields'][field]['label'])
        
        # add in any derived fields
        for field in self.config['derived_fields']:
            ftype = self.config['derived_fields'][field]['ftype'].lower()
            if ftype == 'lincom':
                self.df.add_lincom_entry(field = field, 
                                        input_field = self.config['derived_fields'][field]['input_field'], 
                                        slope = self.config['derived_fields'][field]['slope'], 
                                        intercept = self.config['derived_fields'][field]['intercept'],
                                        units = self.config['derived_fields'][field]['units'],
                                        label = self.config['derived_fields'][field]['label'])
            elif ftype == 'linterp':
                self.df.add_linterp_entry(field, 
                                          input_field = self.config['derived_fields'][field]['input_field'], 
                                          LUT_file = self.base_directory + '/' + self.config['derived_fields'][field]['LUT_file'],
                                          units = self.config['derived_fields'][field]['units'],
                                          label = self.config['derived_fields'][field]['label'])
    def build_dicts(self):
        """
        gets the fields and daq rates from the config file
        uses daq rates to calculate the samples per frame (spf) of each 
        field and build the vectors to hold the data for the current frame
        """
        
        # go through each daq loop in the config file and build the HK dictionaries
        for rate in self.config['daq_dt']:
            # calculate the spf for each daq loop
            spf = int(self.config['dirfile_write_dt']/self.config['daq_dt'][rate])
            self.spf.update({rate : spf})
            print(f'{rate} daq loop: {spf} samples per frame')
            
        # go through all the fields
        for field in self.config['fields']:
            
            # add an item to the state dictionary, initialize with zeros
            self.state.update({field : None})
            #print(f'housekeeping: adding field "{field}"')
            
            #NPL 6-1-21: removing the dirfile handling from wsp
            """
            # add a numpy array item to the curframe dictionary
            spf = self.spf[self.config['fields'][field]['rate']]
            dtype = np.dtype(self.config['fields'][field]['dtype'])         
            self.curframe.update({field : np.full(spf, 0, dtype = dtype)})
            #print(f'adding vector with len = {spf} and type {dtype} to current frame dictionary')
            """

        
    def get_sun_alt(self, time = 'now', time_format = 'datetime'):
        
        if time == 'now':
            now_datetime = datetime.utcnow()
            
        time = astropy.time.Time(time, format = time_format)
        
        
        lat = astropy.coordinates.Angle(self.config['site']['lat'])
        lon = astropy.coordinates.Angle(self.config['site']['lon'])
        height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])
                                        
        palomar = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
        # this gives the same result as using the of_site('Palomar') definition
        
        
        
        
        frame = astropy.coordinates.AltAz(obstime = time, location = palomar)
        
        sunloc = astropy.coordinates.get_sun(time)
        
        sun_coords = sunloc.transform_to(frame)
        
        sunalt = sun_coords.alt.value
        self.sunalt = sunalt
