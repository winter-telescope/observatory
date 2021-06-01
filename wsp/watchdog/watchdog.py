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
#import pygetdata as getdata

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)

# import the alert handler
from alerts import alert_handler
#from utils import utils
from daemon import daemon_utils


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
        
    
    print('wsp killer done.')
    print('________________________________')
    
    return True