#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 29 09:16:01 2021

ephemeris daemon. just runs some astropy stuff to get the locations of
useful ephemeris. Some of these run a little slow, so I'm pushing it out into
its own daemon



@author: nlourie
"""
import os
import Pyro5.core
import Pyro5.server
import time
from PyQt5 import uic, QtCore, QtGui, QtWidgets
from astropy.io import fits
import numpy as np
import sys
import signal
import queue
import threading
import astropy.coordinates
import astropy.units as u
from datetime import datetime
import json

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')


from housekeeping import data_handler
from daemon import daemon_utils
from utils import utils




@Pyro5.server.expose
class EphemMon(object):
    def __init__(self, config, dt = 1000, name = 'ephem', verbose = False):
        
        self.config = config
        self.name = name
        self.dt = dt
        self.sunalt = 0.0
        self.verbose = verbose
        self.state = dict()
        
        # set up site
        lat = astropy.coordinates.Angle(self.config['site']['lat'])
        lon = astropy.coordinates.Angle(self.config['site']['lon'])
        height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])
                                        
        self.site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
        # this gives the same result as using the of_site('Palomar') definition
        
        
        
        if verbose:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name, print_thread_name_in_update = True, thread_numbering = 'norm')
        else:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name)
        
    def update(self):
        
        time_utc = datetime.utcnow()
        timestamp = time_utc.timestamp()
        self.state.update({'timestamp' : timestamp})
        
        # get sun altitude
        self.sunalt = self.get_sun_alt(obstime = time_utc, time_format = 'datetime')
        self.moonalt, self.moonaz = self.get_moon_altaz(obstime = time_utc, time_format = 'datetime')
        self.state.update({'sunalt' : self.sunalt})
        self.state.update({'moonalt' : self.moonalt})
        self.state.update({'moonaz' : self.moonaz})
        
        # is the sun  below the horizon?
        if self.sunalt < 0:
            self.sun_below_horizon = True
        
        else:
            self.sun_below_horizon = False
        self.state.update({'sun_below_horizon' : self.sun_below_horizon})
        
        if self.verbose:
            self.printState()
        pass
    
    def get_sun_alt(self, obstime = 'now', time_format = 'datetime'):
        
        if obstime == 'now':
            obstime = datetime.utcnow()
        
        obstime = astropy.time.Time(obstime, format = time_format)
        
        frame = astropy.coordinates.AltAz(obstime = obstime, location = self.site)
        
        sunloc = astropy.coordinates.get_sun(obstime)
        
        sun_coords = sunloc.transform_to(frame)
        
        sunalt = sun_coords.alt.value
        return sunalt
    
    def get_moon_altaz(self, obstime = 'now', time_format = 'datetime'):
        
        if obstime == 'now':
            obstime = datetime.utcnow()
        
        obstime = astropy.time.Time(obstime, format = time_format)

        frame = astropy.coordinates.AltAz(obstime = obstime, location = self.site)
        
        loc = astropy.coordinates.get_moon(obstime)
        
        coords = loc.transform_to(frame)
        
        alt = coords.alt.value
        az = coords.az.value
        return alt, az
    
    def getState(self):
        return self.state
    
    def printState(self):
        print(f'Ephemeris State = {json.dumps(self.state, indent = 2)}')
        print()

        
class PyroGUI(QtCore.QObject):   

                  
    def __init__(self, config, verbose = False, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        print(f'main: running in thread {threading.get_ident()}')
        
        self.ephem = EphemMon(config = config, dt = 200, name = 'ephem', verbose = verbose)
                
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.ephem, name = 'ephem')
        self.pyro_thread.start()
        
        """
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.check_pyro_queue)
        self.timer.start()
        """


            
        
def sigint_handler( *args):
    """Handler for the SIGINT signal."""
    sys.stderr.write('\r')
    
    main.ephem.daqloop.quit()
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    
    args = sys.argv[1:]
    
    
    modes = dict()
    modes.update({'-v' : "Running in VERBOSE mode"})

    
    # set the defaults
    verbose = False

    
    #print(f'args = {args}')
    
    if len(args)<1:
        pass
    
    else:
        for arg in args:
            
            if arg in modes.keys():
                
                # remove the dash when passing the option
                opt = arg.replace('-','')
                if opt == 'v':
                    print(modes[arg])
                    verbose = True

            else:
                print(f'Invalid mode {arg}')

    ##### RUN THE APP #####
    app = QtCore.QCoreApplication(sys.argv)

    # set the wsp path as the base directory
    base_directory = wsp_path

    # load the config
    config_file = base_directory + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    
    main = PyroGUI(config, verbose = verbose)

    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())

