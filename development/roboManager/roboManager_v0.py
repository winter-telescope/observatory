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



class RoboManager(object):
    def __init__(self, config, dt = 1000, name = 'roboManager', sunsim = False, verbose = False, logger = None):
        
        self.config = config
        self.name = name
        self.logger = logger
        self.dt = dt
        self.sunsim = sunsim
        
        self.sunalt = 0.0
        self.prev_sunalt = 0.0
        self.sun_rising = False
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
    
    def update(self):
        try:
            time_utc = datetime.utcnow()
            timestamp = time_utc.timestamp()
            self.state.update({'timestamp' : timestamp})
            
            # get the observatory state from the pyro5 server
            self.update_observatoryState()
        
            
            if self.verbose:
                self.printState()
            pass
        except Exception as e:
            #print(f'ephemd: error in update: {e}')
            pass
    
    
    
    
    @Pyro5.server.expose
    def getState(self):
        return self.state
    
    def printState(self):
        print(f'State = {json.dumps(self.state, indent = 2)}')
        print()

        
class PyroGUI(QtCore.QObject):   

                  
    def __init__(self, config, verbose = False, logger = None, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        print(f'main: running in thread {threading.get_ident()}')
        
        self.manager = RoboManager(config = config, dt = 200, name = 'ephem', verbose = verbose, logger = logger)
                
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
    sunsim = True
    verbose = False
    doLogging = True
    
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
                elif opt == 'p':
                    print(modes[arg])
                    doLogging = False

            else:
                print(f'Invalid mode {arg}')

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

