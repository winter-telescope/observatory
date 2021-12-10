#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 27 12:47:07 2021

@author: winter
"""


import os
import Pyro5.core
import Pyro5.server
#import time
#from PyQt5 import uic, QtGui, QtWidgets
from PyQt5 import QtCore
#from astropy.io import fits
import numpy as np
import sys
import signal
#import queue
#import threading
from datetime import datetime
import pathlib




# add the wsp directory to the PATH
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'dirfiled: wsp_path = {wsp_path}')

# winter modules

#from housekeeping import data_handler

try:
    from housekeeping import dirfile_python
except:
    import dirfile_python

#from daemon import daemon_utils

from utils import utils
from utils import logging_setup

class StateGetter(QtCore.QObject):
    
    """
    This is the pyro object that handles the creation of the dirfile,
    polling the published state from the Pyro nameserver, and updating the
    dirfile.
    
    NOTE:
        This inherets from QObject, which allows it to have custom signals
        which can communicate with the communication threads
    """
    
    
    def __init__(self, base_directory, config, logger, verbose = False):
        super(StateGetter, self).__init__()
        
        self.base_directory = base_directory
        self.config = config
        self.logger = logger
        self.verbose = verbose
                
        # current state values
        self.state = dict()
        self.timestamp_dts = dict()
        # connect the signals and slots
        
        # Startup
        self.init_remote_object()
        #self.update_state()
        
        
        
        
    def init_remote_object(self):
        # init the remote object
        try:
            self.remote_object = Pyro5.client.Proxy("PYRONAME:state")
            self.connected = True
        except:
            self.connected = False
            pass
        '''
        except Exception:
            self.logger.error('connection with remote object failed', exc_info = True)
        '''
    def update_state(self):
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        if not self.connected:
            self.init_remote_object()
            
        else:
            try:
                self.state = self.remote_object.GetStatus()
                watchdog_timestamp = datetime.utcnow().timestamp()
                self.state.update({'watchdog_timestamp' : watchdog_timestamp})
                #print(f'count = {self.state["count"]}')
                
                self.check_times()
                
                
            except Exception as e:
                if self.verbose:
                    print(f'stategetter: could not update remote state: {e}')
                pass
    
    def check_times(self):
        
        for field in self.state:
            if 'timestamp' in field:
                dt = self.state['watchdog_timestamp'] - self.state[field]
                self.timestamp_dts.update({field : dt})
                    
                print(f'{field:40}: {dt}')
            
        
if __name__ == '__main__':
    
    # set the wsp path as the base directory
    base_directory = wsp_path

    # load the config
    config_file = base_directory + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    
    doLogging = False
    
    # set up the logger
    if doLogging:
        logger = logging_setup.setup_logger(base_directory, config)    
    else:
        logger = None
    monitor = StateGetter(base_directory = base_directory, config = config, logger = logger)
    monitor.update_state()
    
    