#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 11 12:16:47 2023

This is a watchdog daemon that will monitor the full WINTER system for hardware
problems. It will do several functions:
    - monitor that all the daemons are appropriately working and responding
    - monitor critical hardware like the chiller and the WINTER focal planes
    - it will have some configurability to turn on and off different modules
    - it will rely on wsp to be in touch and to execute necessary sequences
      if there are problems. 
    - it should have some "oh sh*t" type things it can do if there is no handling
      by wsp. for instance it should have the ability to directly power off the
      focal planes.
    - if there are problems with the daemon connections, it should just kill
      wsp. This will then rely on the systemctl daemon running in the background
      to relaunch it.
      


@author: nlourie
"""


import os
import Pyro5.core
import Pyro5.server
from PyQt5 import QtCore
#import numpy as np
import sys
import signal
import threading
import time
import logging
import getopt
import json
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'wsp_path = {wsp_path}')


from housekeeping import data_handler
from daemon import daemon_utils
from utils import logging_setup
from utils import utils
from alerts import alert_handler

from winterMonitor import WINTER_monitor

class Watchdog(QtCore.QObject):
    def __init__(self,  config, monitor_dict, alertHandler, ns_host = None, dt = 1000, name = 'power', logger = None, verbose = False):
        
        super(Watchdog, self).__init__()   
        
        self.config = config
        self.monitor_dict = monitor_dict
        self.alertHandler = alertHandler
        self.ns_host = ns_host
        self.name = name
        self.dt = dt
        self.logger = logger
        self.verbose = verbose
        
        self.state = dict()
        self.hk_state = dict()
        
        self.monitor_dict = monitor_dict
        self.setup_alarm_dict()
        
        self.hk_connected = False
        
        self.log('finished init, starting monitoring loop')
        
        time.sleep(60)
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.dt)
        self.timer.timeout.connect(self.update_state)
        self.timer.start()
        
    
    def log(self, msg, level = logging.INFO):
        
        msg = f'watchdogd: {msg}'
        
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def setup_alarm_dict(self):
        
        self.alarm_dict = dict()
        
        for cam in self.monitor_dict:
            self.alarm_dict.update({cam : []})
    
    def init_hk_state_object(self):
        # init the remote object
        try:
            ns = Pyro5.core.locate_ns(host = self.ns_host)
            uri = ns.lookup("state")
            self.remote_hk_state_object = Pyro5.client.Proxy(uri)
            self.hk_connected = True
        except:
            self.hk_connected = False
            pass
        '''
        except Exception:
            self.log('connection with remote object failed', exc_info = True)
        '''
    def update_hk_state(self):
        # poll the state, if we're not connected try to reconnect
        # this should reconnect down the line if we get disconnected
        if not self.hk_connected:
            self.init_hk_state_object()
            
        else:
            try:
                self.hk_state = self.remote_hk_state_object.GetStatus()
                
            except Exception as e:
                if self.verbose:
                    self.log(f'could not update remote housekeeping state: {e}')
                self.hk_connected = False    
    
    def update_state(self):
        self.update_hk_state()
        self.parse_state()
        """
        try:
            
                            
            self.parse_state()
            
            
        except Exception as e:
            if self.verbose:
                self.log(f'could not update state: {e}')
            pass
        """
    

    
    def parse_state(self):

        for cam in self.monitor_dict:
            
            # check for alarms
            alarms = self.monitor_dict[cam].get_alarms(self.hk_state)
            self.alarm_dict.update({cam : alarms})
        
        # add the active alarms to the state dictionary
        
        self.state.update({'alarms' : self.alarm_dict})
    @Pyro5.server.expose
    def getState(self):
        return self.state 
    

    
class PyroGUI(QtCore.QObject):   

                  
    def __init__(self, config, cams, alertHandler, ns_host, logger, verbose, parent=None ):            
        super(PyroGUI, self).__init__(parent)   
        print(f'main: running in thread {threading.get_ident()}')
        
        self.watchdog = Watchdog(config, cams, alertHandler, ns_host = ns_host,
                                 dt = 1000, name = 'watchdog', verbose = verbose, logger = logger)
                
        self.pyro_thread = daemon_utils.PyroDaemon(obj = self.watchdog, name = 'watchdog',
                                                   ns_host = ns_host)
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
    
    #main.powerManager.daqloop.quit()
    
    QtCore.QCoreApplication.quit()

if __name__ == "__main__":
    
    
    #### GET ANY COMMAND LINE ARGUMENTS #####
    
    args = sys.argv[1:]
    print(f'args = {args}')
    
    # set the defaults
    verbose =  False
    doLogging = True
    ns_host = '192.168.1.10'
    watch_winter = True
    watch_summer = False    
    
    options = "vpn:ws"
    long_options = ["verbose", "print", "ns_host:", "winter", "summer"]
    arguments, values = getopt.getopt(args, options, long_options)
    # checking each argument
    print()
    print(f'Parsing sys.argv...')
    print(f'arguments = {arguments}')
    print(f'values = {values}')
    for currentArgument, currentValue in arguments:
        if currentArgument in ("-v", "--verbose"):
            verbose = True
            print("Running in VERBOSE mode")
        
        elif currentArgument in ("-p", "--print"):
            doLogging = False
            print("Running in PRINT mode (instead of log mode).")
            
        elif currentArgument in ("-n", "--ns_host"):
            ns_host = currentValue
        
        elif currentArgument in ("-w", "--winter"):
            # should the watchdog keep track of WINTER?
            watch_winter = True
        
        elif currentArgument in ("-s", "--summer"):
            # should the watchdog keep track of SUMMER?
            watch_winter = True
            
    print(f'powerd: launching with ns_host = {ns_host}')
    
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
    
    # set up the alert system to post to slack
    auth_config_file  = wsp_path + '/credentials/authentication.yaml'
    user_config_file = wsp_path + '/credentials/alert_list.yaml'
    alert_config_file = wsp_path + '/config/alert_config.yaml'

    auth_config  = utils.loadconfig(auth_config_file) 
    user_config = utils.loadconfig(user_config_file)
    alert_config = utils.loadconfig(alert_config_file)

    alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
    
    monitor_dict = dict()

    if watch_winter:
        winter_monitor_config = utils.loadconfig(wsp_path + '/config/winterMonitorconfig.yaml')
        winter_monitor = WINTER_monitor(monitor_config = winter_monitor_config, 
                                       logger = logger, verbose = verbose)
        monitor_dict.update({'winter' : winter_monitor})
        
    if watch_summer:
        pass
    
    main = PyroGUI(config, monitor_dict, alert_handler, ns_host, logger, verbose)
    
    signal.signal(signal.SIGINT, sigint_handler)

    # Run the interpreter every so often to catch SIGINT
    timer = QtCore.QTimer()
    timer.start(500) 
    timer.timeout.connect(lambda: None) 

    sys.exit(app.exec_())



