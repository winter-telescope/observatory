#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 16 02:56:00 2023

@author: nlourie
"""

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
import logging
from PyQt5 import QtCore
import json

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(1, wsp_path)

from utils import utils



class local_watchdog(QtCore.QObject):

    winterAlarm = QtCore.pyqtSignal(object)
    
    def __init__(self, base_directory, config, ns_host = None, logger = None, verbose = False):
        super(local_watchdog, self).__init__()
        self.base_directory = base_directory
        self.config = config
        self.ns_host = ns_host
        self.logger = logger
        self.verbose = verbose
        
        # default value for bad query
        self.default = -888
        self.default_timestamp = datetime(1970,1,1,0,0).timestamp()
        
        self.min_dt_between_alarms = 60.0
        self.timestamp_of_last_alarm = datetime.utcnow().timestamp()
        
        # init the local and remote state dictionaries
        self.state = dict()
        self.remote_state = dict()
        
        self.init_remote_object()
        self.update_state()
    
    def log(self, msg, level = logging.INFO):
        msg = f'watchdog: {msg}'
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)  
        
        
    def init_remote_object(self):
        # init the remote object
        try:
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = ns.lookup('watchdog')
            self.remote_object = Pyro5.client.Proxy(uri)
        
        except Exception as e:
            if self.verbose:
                self.log(f'connection with remote object failed: {e}', level = logging.ERROR)#, exc_info = True)
            
    def update_state(self):
        try:

            self.remote_state = self.remote_object.getState()
            self.parse_state()  

        except Exception as e:
            if self.verbose:
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
        
        # trigger any alarms
        if any(self.state['alarms']['winter']):
            alarm_timestamp = datetime.utcnow().timestamp()
            dt_since_last_alarm = alarm_timestamp - self.timestamp_of_last_alarm
            
            if dt_since_last_alarm > self.min_dt_between_alarms:
                self.winterAlarm.emit(self.state['alarms']['winter'])
                
                self.log("FOUND ACTIVE ALARMS!! Camera is powered while these states are out of range: ")
                self.log(f"{self.state['alarms']['winter']}")
                
                self.timestamp_of_last_alarm = alarm_timestamp
            else:
                pass
        
        
        
        
    def print_state(self):
        #self.update_state()
        #print(f'Local Object: {self.msg}')
        print(json.dumps(self.state, indent = 3))
    
  
        
# Try it out
if __name__ == '__main__':
    
    ns_host = '192.168.1.10'
    logger = None
    
    config = utils.loadconfig(wsp_path + '/config/config.yaml')

    mon = local_watchdog(wsp_path, config, ns_host = ns_host, logger = logger)


    while True:
        try:
            mon.update_state()
            #counter.get_remote_status()
            #counter.print_status()
            mon.print_state()
            time.sleep(.5)
        except KeyboardInterrupt:
            break
