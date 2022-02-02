#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  1 15:15:20 2021

watchdog.py

This has useful functions for starting and stopping the wsp watchdog


@author: nlourie
"""

import os
import sys
#import time
from datetime import datetime
#import subprocess
import yaml
import Pyro5.client
import pygetdata as getdata

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)

# import the alert handler
from alerts import alert_handler
#from utils import utils
from daemon import daemon_utils


class StateMonitor(object):
    
    """
    This is the pyro object that handles the creation of the dirfile,
    polling the published state from the Pyro nameserver, and updating the
    dirfile.
    
    NOTE:
        This inherets from QObject, which allows it to have custom signals
        which can communicate with the communication threads
    """
    
    
    def __init__(self, verbose = False):
        #super(StateGetter, self).__init__()
        
        #self.base_directory = base_directory
        #self.config = config
        #self.logger = logger
        self.verbose = verbose
                
        # current state values
        self.state = dict()
        self.timestamp_dts = dict()
        self.bad_timestamps = dict()
        # connect the signals and slots
        
        self.check_dirfile = False
        
        # Startup
        self.init_remote_object()
        #self.update_state()
        
        
        
        
    def init_remote_object(self):
        # init the remote object
        watchdog_timestamp = datetime.utcnow().timestamp()
        self.state.update({'watchdog_timestamp' : watchdog_timestamp})
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
                
                self.remote_state = self.remote_object.GetStatus()
                for field in self.remote_state:
                    self.state.update({field: self.remote_state[field]})
                watchdog_timestamp = datetime.utcnow().timestamp()
                self.state.update({'watchdog_timestamp' : watchdog_timestamp})
                if self.check_dirfile:
                    self.dirfile_timestamp = self.get_dirfile_write_timestamp()
                    self.state.update({'dirfile_timestamp' : self.dirfile_timestamp})
                #print(f'count = {self.state["count"]}')
                
                
                
                
            except Exception as e:
                if self.verbose:
                    print(f'stategetter: could not update remote state: {e}')
                
                pass
            # chedcfk the dt here outside the try/except so it will return an 
            # bad dt if we can't poll the remote_object
            self.check_times()
    
    def setupDirfileMonitor(self, dirfilepath):
        # set up the link to the dirfile (df)
        self.dirfilePath = dirfilepath
        
        self.df = getdata.dirfile(self.dirfilePath)
        self.check_dirfile = True
    
    def get_dirfile_write_timestamp(self):
        # Get the last timestamp written to the dirfile
        #last_timestamp = os.path.getatime(filePath)
        # sometimes it seems like it might not want to read the *last* frame?
        frame_to_read = self.df.nframes-1
        last_timestamp = self.df.getdata('timestamp',first_frame = frame_to_read, num_frames = 1)[0]

        
        return last_timestamp
        
    def check_times(self):
        
        for field in self.state:
            if 'timestamp' in field:
                #dt = self.state['watchdog_timestamp'] - self.state[field]
                dt = datetime.utcnow().timestamp() - self.state[field]
                self.timestamp_dts.update({field : dt})
                if self.verbose:   
                    print(f'{field:40}: {dt}')
                
    def get_bad_timestamps(self, dt_max, overrides = dict()):
        # start with no bad timestamps
        self.bad_timestamps = dict()
        # now see if any fields have dt >= dt_max
        for field in self.timestamp_dts:
            
            # make a carveout for any field in the overrides dictionary
            # overrides needs to be something like {'ccd_last_update_timestamp' : 600.0}
            # try to get the dt for the field from the override dictionary
            dt_max_field = overrides.get(field, dt_max)
            
            if self.timestamp_dts[field] >= dt_max_field:
                self.bad_timestamps.update({field : self.timestamp_dts[field]})
        
            

def shutdown_watchdog():
    
    # set up the alert system to post to slack
    auth_config_file  = wsp_path + '/credentials/authentication.yaml'
    user_config_file = wsp_path + '/credentials/alert_list.yaml'
    alert_config_file = wsp_path + '/config/alert_config.yaml'
    
    auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
    user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
    alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)
    
    alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
    
    program_to_monitor = 'watchdog_start.py'
    
    msg = f"{datetime.now().strftime('%m/%d/%Y %H:%M')} Turning off wsp watchdog"
    
    alertHandler.slack_log(msg, group = None)
    
    print('Checking if watchdog is running:')
    main_pid, child_pids = daemon_utils.checkParent(program_to_monitor,printall = False)
    
    if not main_pid is None:
        print(f'killing {program_to_monitor} parent process')
        # kill the parent process
        daemon_utils.killPIDS(main_pid)
        
        print('Checking if watchdog is still running:')
        main_pid, child_pids = daemon_utils.checkParent(program_to_monitor,printall = False)
        
    # close the connection to the dirfile
    print('done.')
    return True

def kill_wsp():
    
    # set up the alert system to post to slack
    auth_config_file  = wsp_path + '/credentials/authentication.yaml'
    user_config_file = wsp_path + '/credentials/alert_list.yaml'
    alert_config_file = wsp_path + '/config/alert_config.yaml'
    
    auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
    user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
    alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)
    
    alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)
    
    program_to_monitor = 'wsp.py'
    
    msg = f"{datetime.now().strftime('%m/%d/%Y %H:%M')} Using the WSP Killer to kill all WSP processes!"
    
    #alertHandler.slack_log(msg, group = None)
    print()
    print('________________________________')
    print('##### WSP KILLER INITIATED #####')
    
    print('Checking if watchdog is running:')
    main_pid, child_pids = daemon_utils.checkParent(program_to_monitor,printall = False, verbose = True)
    
    if not main_pid is None:
    
        print(f'killing {program_to_monitor} parent process')
        # kill the parent process
        daemon_utils.killPIDS(main_pid)
        
        print(f'killing child processes')
        daemon_utils.killPIDS(child_pids)
        
        print('Checking if wsp is still running:')
        main_pid, child_pids = daemon_utils.checkParent(program_to_monitor,printall = False)
    print('Killing any running instances of huaso_server')
    # kill any dangling huaso server instances
    huaso_pids = daemon_utils.getPIDS('huaso_server')
    daemon_utils.killPIDS(huaso_pids)
    print('wsp killer done.')
    print('________________________________')
    
    return True