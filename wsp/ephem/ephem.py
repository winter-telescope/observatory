#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 29 09:57:39 2021

@author: nlourie
"""

import os
#import numpy as np
import sys
import Pyro5.core
import Pyro5.server
import time
from datetime import datetime
import astropy.coordinates
import astropy.units as u
import logging

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(1, wsp_path)

from utils import utils



class local_ephem(object):
    
    def __init__(self, base_directory, config, ns_host = None, logger = None):
        self.base_directory = base_directory
        self.config = config
        self.ns_host = ns_host
        self.logger = logger
        
        # default value for bad query
        self.default = -888
        self.default_timestamp = datetime(1970,1,1,0,0).timestamp()
        
        # set up site
        lat = astropy.coordinates.Angle(self.config['site']['lat'])
        lon = astropy.coordinates.Angle(self.config['site']['lon'])
        self.height_m = self.config['site']['height']
        height = self.height_m * u.Unit(self.config['site']['height_units'])
                                        
        self.site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
        self.lat_deg = lat.deg
        self.lon_deg = lon.deg
        # init the local and remote state dictionaries
        self.state = dict()
        self.remote_state = dict()
        
        self.init_remote_object()
        self.update_state()
    
    def log(self, msg, level = logging.INFO):
        msg = f'ephem: {msg}'
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)  
        
        
    def init_remote_object(self):
        # init the remote object
        try:
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = ns.lookup('ephem')
            self.remote_object = Pyro5.client.Proxy(uri)
        
        except Exception as e:
            
            self.log(f'connection with remote object failed: {e}', level = logging.ERROR)#, exc_info = True)
    
    def update_state(self):
        try:

            self.remote_state = self.remote_object.getState()
            self.parse_state()  

        except Exception as e:
            self.log(f'Could not update remote status: {e}', level = logging.ERROR)
            self.init_remote_object()
    def parse_state(self):
        # get the timestamp of the last update from the ephem daemon
        self.state.update({'timestamp' : self.remote_state.get('timestamp', self.default_timestamp)})
        
        # get the ephemeris data
        # update all the fields we get from remote_state
        for key in self.remote_state.keys():
            self.state.update({key : self.remote_state[key]})
        
        # assign some variables we need internally
        self.sunalt = self.remote_state.get('sunalt', self.default)
        self.moonalt = self.remote_state.get('moonalt', self.default)
        self.moonaz = self.remote_state.get('moonaz', self.default)
        
        
        
            
        # is the sun below the horizon?
        self.sun_below_horizon = self.remote_state.get('sun_below_horizon', False)
        self.state.update({'sun_below_horizon' : self.sun_below_horizon})
        
        
        
        
    def print_state(self):
        #self.update_state()
        #print(f'Local Object: {self.msg}')
        print(f'state = {self.state}')
    
    def ephemInViewTarget_AltAz(self, target_alt, target_az, obstime = 'now', time_format = 'datetime'):
        # send a query to the ephemeris daemon to ask if the specified target is too close to ephemeris bodies
        
        inview = self.remote_object.ephemInViewTarget_AltAz(target_alt, target_az, obstime, time_format)
        
        return inview
        
# Try it out
if __name__ == '__main__':
    
    config = utils.loadconfig(wsp_path + '/config/config.yaml')

    while True:
        try:
            ephem = local_ephem(wsp_path, config)
            #counter.get_remote_status()
            #counter.print_status()
            print(f'sunalt = {ephem.state["sunalt"]}')
            time.sleep(.5)
        except KeyboardInterrupt:
            break
