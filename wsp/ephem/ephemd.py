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
#import time
from PyQt5 import QtCore
#from PyQt5, uic, QtGui, QtWidgets
#from astropy.io import fits
#import numpy as np
import sys
import signal
import pytz
#import queue
import threading
import astropy.coordinates
import astropy.units as u
from datetime import datetime
import json
import logging


# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')


from housekeeping import data_handler
from daemon import daemon_utils
from utils import utils
import ephem_utils
from utils import logging_setup



class EphemMon(object):
    def __init__(self, config, dt = 1000, name = 'ephemd', sunsim = False, verbose = False, logger = None):
        
        self.config = config
        self.name = name
        self.logger = logger
        self.dt = dt
        self.sunalt = 0.0
        self.prev_sunalt = 0.0
        self.sun_rising = False
        self.sunsim = sunsim
        self.verbose = verbose
        self.state = dict()
        self.observatoryState = dict() # this will hold the current state of the FULL instrument
        
        # set up site
        lat = astropy.coordinates.Angle(self.config['site']['lat'])
        lon = astropy.coordinates.Angle(self.config['site']['lon'])
        height = self.config['site']['height'] * u.Unit(self.config['site']['height_units'])
                                        
        self.site = astropy.coordinates.EarthLocation(lat = lat, lon = lon, height = height)
        # this gives the same result as using the of_site('Palomar') definition
        
        # set up dictionary of tracked ephem distances
        self.ephem_dist_dict = dict()
        self.ephem_in_view = False
        
        # set up the remote object to poll the observatory state
        self.init_remote_object()
        if self.sunsim:
            self.init_sunsim_remote_object()
        
        # Start QTimer which updates state
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.update)
        self.timer.start(self.dt)
        """
        # if you oupdate the state in a different thread than it will need a more sophisticated communication approach between threads
        if verbose:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name, print_thread_name_in_update = True, thread_numbering = 'norm')
        else:
            self.daqloop = data_handler.daq_loop(self.update, dt = self.dt, name = self.name)
        """
    
    def log(self, msg, level = logging.INFO):
        
        msg = f'ephemd: {msg}'
        
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    # observatory state polling:
    def init_remote_object(self):
        # init the remote object
        try:
            self.remote_object = Pyro5.client.Proxy("PYRONAME:state")
            self.connected = True
        except Exception as e:
            self.connected = False
            self.logger.error(f'ephemd: connection with remote object failed', exc_info = True)
            pass
        '''
        except Exception:
            self.logger.error('connection with remote object failed', exc_info = True)
        '''
    
    def update_observatoryState(self):
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        if not self.connected:
            self.init_remote_object()
        else:
            try:
                self.observatoryState = self.remote_object.GetStatus()
                
            except Exception as e:
                if self.verbose:
                    print(f'ephemd: could not update observatory state: {e}')
                pass
        if self.sunsim:
            if not self.sunsim_connected:
                self.init_sunsim_remote_object()
            else:
                try:
                    self.sunsimState = self.sunsim_remote_object.GetStatus()
                except Exception as e:
                    if True:#self.verbose:
                        self.logger.exception(f'ephemd: could not update sunsim state: {e}')
                    pass
        
            
        self.current_alt = self.observatoryState.get('mount_alt_deg', None)
        self.current_az = self.observatoryState.get('mount_az_deg', None)
    def init_sunsim_remote_object(self):
        # init the remote object
        try:
            self.sunsim_remote_object = Pyro5.client.Proxy("PYRONAME:sunsim")
            self.sunsim_connected = True
        except Exception as e:
            self.sunsim_connected = False
            self.logger.error(f'ephemd: connection with sunsim remote object failed: {e}', exc_info = True)
            pass
        '''
        except Exception:
            self.logger.error('connection with remote object failed', exc_info = True)
        '''
    def update(self):
        try:
            # get the observatory state from the pyro5 server
            self.update_observatoryState()
            
            if self.sunsim:
                local_timestamp = self.sunsimState.get('timestamp', -888)
                time_local = datetime.fromtimestamp(local_timestamp, tz = pytz.timezone('America/Los_Angeles'))
                self.time_utc = time_local.astimezone(pytz.utc)
                timestamp = self.time_utc.timestamp()
                #print(f'local time = {time_local}, local_timestamp = {local_timestamp}')
                #print(f'utc   time = {time_utc}, utc timestamp = {timestamp}')

            else:
                self.time_utc = datetime.utcnow()
                timestamp = self.time_utc.timestamp()
                
            self.state.update({'timestamp' : timestamp})
            
            #
            
            # update the distance to the ephemeris
            self.updateCurrentEphemDist(obstime = self.time_utc, time_format = 'datetime')
            
            # update the flag for ephemeris in view
            self.state.update({'ephem_in_view' : self.ephemInViewCurrent()})
            
            # get sun altitude
            self.prev_sunalt = self.sunalt
            self.sunalt = self.get_sun_alt(obstime = self.time_utc, time_format = 'datetime')
            if self.sunalt > self.prev_sunalt:
                self.sun_rising = True
            else:
                self.sun_rising = False
            self.moonalt, self.moonaz = self.get_moon_altaz(obstime = self.time_utc, time_format = 'datetime')
            self.state.update({'sunalt' : self.sunalt})
            self.state.update({'moonalt' : self.moonalt})
            self.state.update({'moonaz' : self.moonaz})
            self.state.update({'sun_rising' : self.sun_rising})
            
            # is the sun  below the horizon?
            if self.sunalt < 0:
                self.sun_below_horizon = True
            
            else:
                self.sun_below_horizon = False
            self.state.update({'sun_below_horizon' : self.sun_below_horizon})
            
            if self.verbose:
                self.printState()
            pass
        except Exception as e:
            #print(f'ephemd: error in update: {e}')
            self.logger.exception(f'error in update: {e}')
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
    
    """
    def setup_ephem_dist_dict(self):
        # first handle the moon
        self.ephem_dist_dict = dict()
        self.ephem_dist_dict.update({'moon' : {'mindist' : self.config['ephem']['moon_target_separation']}})
    
        # now go through any other objects in the list
        for body in self.config['ephem']['bodies']:
            self.ephem_dist_dict.update({body : {'mindist' : self.config['ephem']['general_min_separation']}})
    """
        
    def updateCurrentEphemDist(self, obstime = 'now', time_format = 'datetime'):
        # get the current distance to all tracked ephemeris objects
        # call: getTargetEphemDist_AltAz( target_alt, target_az, body, location, obstime = 'now', time_format = 'datetime'):
        # first handle the moon
        #print(f'current alt = {self.current_alt}, current az = {self.current_az}')
        
        if (self.current_alt is None) or (self.current_alt == self.config['default_value']) or (self.current_az is None) or (self.current_az == self.config['default_value']):
            # we don't know where the telescope is pointing! 
            self.telemetry_connected = False
            # protect the instrument by reporting zero distance to all bodies
            dist = 0.0
            for body in self.config['ephem']['min_target_separation']:
                self.state.update({f'ephem_dist_{body}' : dist})
                self.ephem_dist_dict.update({body : dist})
            
            
        else:
            self.telemetry_connected = True
            for body in self.config['ephem']['min_target_separation']:
                
                dist = ephem_utils.getTargetEphemDist_AltAz(target_alt = self.current_alt,
                                                            target_az = self.current_az,
                                                            body = body,
                                                            location = self.site,
                                                            obstime = obstime,
                                                            time_format = 'datetime')
                
                self.state.update({f'ephem_dist_{body}' : dist})
                self.ephem_dist_dict.update({body : dist})
        # update whether we're getting telemetry data
        self.state.update({'telemetry_connected' : self.telemetry_connected})
        pass
    
    
    def ephemInViewCurrent(self):
        # check if any of the ephemeris bodies are too close
        inview = list()
        for body in self.config['ephem']['min_target_separation']:
            mindist = self.config['ephem']['min_target_separation'][body]
            dist = self.ephem_dist_dict[body]
            if dist < mindist:
                inview.append(True)
            else:
                inview.append(False)
    
        if any(inview):
            return True
        else:
            return False
    
    @Pyro5.server.expose
    def ephemInViewTarget_AltAz(self, target_alt, target_az, obstime = 'now', time_format = 'datetime'):
        # check if any of the ephemeris bodies are too close to the given target alt/az
        inview = list()
        for body in self.config['ephem']['min_target_separation']:
            mindist = self.config['ephem']['min_target_separation'][body]
            dist = ephem_utils.getTargetEphemDist_AltAz(target_alt = target_alt,
                                                        target_az = target_az,
                                                        body = body,
                                                        location = self.site,
                                                        obstime = obstime,
                                                        time_format = time_format)
            if dist < mindist:
                inview.append(True)
            else:
                inview.append(False)
    
        if any(inview):
            return True
        else:
            return False
    
    
    @Pyro5.server.expose
    def getState(self):
        return self.state
    
    def printState(self):
        print(f'Ephemeris State = {json.dumps(self.state, indent = 2)}')
        print()

        
class PyroGUI(QtCore.QObject):   

                  
    def __init__(self, config, sunsim = False, verbose = False, logger = None, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        print(f'main: running in thread {threading.get_ident()}')
        
        self.ephem = EphemMon(config = config, dt = 200, name = 'ephem', sunsim = sunsim, verbose = verbose, logger = logger)
                
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
    modes.update({'--sunsim' : "Running in simulated sun mode"})
    
    # set the defaults
    verbose = False
    doLogging = True
    sunsim = False
    #print(f'args = {args}')
    
    if len(args)<1:
        pass
    
    else:
        for arg in args:
            
            if arg in modes.keys():
                
                # remove the dash when passing the option
                opt = arg.replace('-','')
                if opt == 'v':
                    print(f'ephemd: {modes[arg]}')
                    verbose = True
                elif opt == 'p':
                    print(f'ephemd: {modes[arg]}')
                    doLogging = False
                elif opt == 'sunsim':
                    print(f'ephemd: {modes[arg]}')
                    sunsim = True

            else:
                print(f'ephemd: Invalid mode {arg}')

    ##### RUN THE APP #####
    app = QtCore.QCoreApplication(sys.argv)

    # set the wsp path as the base directory
    base_directory = wsp_path

    # load the config
    config_file = base_directory + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    
    # set up the logger
    if doLogging:
        logger = logging_setup.setup_logger(base_directory, config)    
    else:
        logger = None
    
    main = PyroGUI(config, sunsim = sunsim, verbose = verbose, logger = logger)

    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())

