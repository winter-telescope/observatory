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
#from housekeeping import easygetdata as egd
from housekeeping import data_handler
from housekeeping import labjacks
from daemon import daemon_utils
#from housekeeping import dirfile_python

# the main housekeeping class, it lives in the namespace of the control class



class housekeeping():                     
    def __init__(self, config, base_directory, mode = None, 
                 watchdog = None,
                 schedule = None, 
                 telescope = None, 
                 mirror_cover=None, 
                 dome = None, 
                 chiller = None, 
                 labjacks = None,
                 powerManager = None, 
                 counter = None, 
                 ephem = None, 
                 #viscam = None, 
                 #ccd = None, 
                 #summercamera = None,
                 #wintercamera = None,
                 camdict = None,
                 fwdict = None,
                 imghandlerdict = None,
                 robostate = None, 
                 sunsim = False, 
                 ns_host = None, 
                 logger = None,
                 ):
        
        
        # store the config
        self.config = config
        self.base_directory = base_directory
        
        # define the housekeeping mode. this dictates which fields are read
        self.mode = mode
        
        # redefine the methods passed in: ie the hardware systems
        self.watchdog = watchdog
        self.schedule = schedule
        self.telescope = telescope
        self.dome = dome
        self.chiller = chiller
        self.labjacks = labjacks
        self.powerManager = powerManager
        self.counter = counter
        self.ephem = ephem
        #self.viscam = viscam
        #self.ccd = ccd
        #self.summercamera = summercamera
        #self.wintercamera = wintercamera
        self.camdict = camdict
        self.fwdict = fwdict
        self.imghandlerdict = imghandlerdict
        self.mirror_cover = mirror_cover
        self.robostate = robostate
        self.sunsim = sunsim
        self.ns_host = ns_host
        self.logger = logger
        # setup any labjacks that are in the config
        '''
        ### Labjack Definitions ###
        labjacks:
            lj0:
                config: 'labjack0_config.yaml'
        '''
        #self.labjacks = labjacks.labjack_set(self.config, self.base_directory)
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
        
        if mode.lower() in ['i']:
            #TODO: this should also run in 'm' and 'r' mode eventually...
            #self.housekeeping_poll_functions.append(self.labjacks.update_state)
            #self.housekeeping_poll_functions.append(self.summercamera.update_state)
            #self.housekeeping_poll_functions.append(self.wintercamera.update_state)
            pass
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
            
            #self.housekeeping_poll_functions.append(self.viscam.update_state)
            #self.housekeeping_poll_functions.append(self.ccd.update_state)
            
            if self.mirror_cover is not None:
                self.housekeeping_poll_functions.append(self.mirror_cover.update_state)
            
            #self.housekeeping_poll_functions.append(self.powerManager.update_state)
            
            self.housekeeping_poll_functions.append(self.watchdog.update_state)
        # things that should happen in all modes
        self.housekeeping_poll_functions.append(self.labjacks.update_state)
        self.housekeeping_poll_functions.append(self.powerManager.update_state)

        for cam in self.camdict:
            self.housekeeping_poll_functions.append(self.camdict[cam].update_state)
        
        for fw in self.fwdict:
            self.housekeeping_poll_functions.append(self.fwdict[fw].update_state)
        
        """
        self.daq_labjacks = data_handler.daq_loop(func = self.labjacks.read_all_labjacks,
                                                  dt = self.config['daq_dt']['hk'],
                                                  name = 'labjack_daqloop'
                                                  )
                                                  #rate = 'very_slow')
        """
        # write the current state to a file
        
        
        self.statedump_loop = data_handler.daq_loop(func = self.dump_state,
                                                    dt = 5000,
                                                    name = 'state_dump')
        
        # add status polls that we CALL NO MATTER WHAT MODE to the housekeeping poll list
        self.housekeeping_poll_functions.append(self.counter.update_state)
        self.housekeeping_poll_functions.append(self.chiller.update_state)
        

        self.hk_loop = data_handler.hk_loop(config = self.config, 
                                               state = self.state, 
                                               curframe = self.curframe,
                                               schedule = self.schedule,
                                               telescope = self.telescope,
                                               labjacks = self.labjacks,
                                               counter = self.counter,
                                               dome = self.dome,
                                               chiller = self.chiller,
                                               powerManager = self.powerManager,
                                               ephem = self.ephem,
                                               #viscam = self.viscam,
                                               #ccd = self.ccd,
                                               #summercamera = self.summercamera,
                                               #wintercamera = self.wintercamera,
                                               camdict = self.camdict,
                                               fwdict = self.fwdict,
                                               imghandlerdict = self.imghandlerdict,
                                               mirror_cover = self.mirror_cover,
                                               robostate = self.robostate,
                                               sunsim = self.sunsim,
                                               ns_host = self.ns_host, 
                                               logger = self.logger)

        
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
            #print(func)
            func()
            
    def start_housekeeping_poll_loop(self):
        self.timer = QtCore.QTimer()
        hk_poll_dt = int(np.round(self.config['daq_dt']['hk'], 0))
        self.timer.setInterval(hk_poll_dt)
        self.timer.timeout.connect(self.poll_housekeeping)
        self.timer.start()
    
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
