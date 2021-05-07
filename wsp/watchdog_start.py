#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May  6 18:35:27 2021

watchdog_start

This is part of wsp

This will start a simple watchdog loop that just checks to make sure
that wsp.py is still writing housekeeping data to its dirfile database




@author: winter
"""
import os
import sys
import time
from datetime import datetime
import subprocess
import yaml

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, wsp_path)

# import the alert handler
from alerts import alert_handler
from utils import utils
from daemon import daemon_utils

# set up the alert system to post to slack
auth_config_file  = wsp_path + '/credentials/authentication.yaml'
user_config_file = wsp_path + '/credentials/alert_list.yaml'
alert_config_file = wsp_path + '/config/alert_config.yaml'

auth_config  = yaml.load(open(auth_config_file) , Loader = yaml.FullLoader)
user_config = yaml.load(open(user_config_file), Loader = yaml.FullLoader)
alert_config = yaml.load(open(alert_config_file), Loader = yaml.FullLoader)

alertHandler = alert_handler.AlertHandler(user_config, alert_config, auth_config)

msg = f"{datetime.now().strftime('%m/%d/%Y %H:%M')} Starting wsp.py watchdog"

alertHandler.slack_log(msg, group = None)

filePath = os.getenv("HOME") + '/data/dm.lnk'
program_to_monitor = 'wsp.py'

args = ["python", program_to_monitor,'-m', '--domesim']



#print('starting watchdog loop')
while True:
    
    try:
        #lastmod_timestamp = os.path.getmtime(filePath)
        lastmod_timestamp = os.path.getatime(filePath)

        # DO ALL THE CALCULATIONS LOCALLY OTHERWISE THEY WILL BE WRONG! DON'T USE UTC
        now_timestamp = datetime.now().timestamp()
        #print(f'last update timestamp = {lastmod_timestamp}')
        # get dt in seconds
        dt = now_timestamp - lastmod_timestamp
        
        if dt >= 5.0:
            #print(f'dt = {dt:0.2f}, RELAUNCHING WRITER')
            msg = f"{datetime.now().strftime('%m/%d/%Y %H:%M')} last housekeeping update was {dt:0.1f} s ago. *Restarting wsp.py*"

            alertHandler.slack_log(msg, group = None)
            #time.sleep(60)
            # First let's kill any running wsp process running
            main_pid, child_pids = daemon_utils.checkParent(program_to_monitor,printall = False)
            
            # if wsp is running, kill it and wait until it's dead
            if not main_pid is None:
                daemon_utils.killPIDS(main_pid)
                time.sleep(1)
                main_pid, child_pids = daemon_utils.checkParent(program_to_monitor,printall = False)
                
                while not main_pid is None:
                    # wait for it to die
                    time.sleep(1)
                    main_pid, child_pids = daemon_utils.checkParent(program_to_monitor,printall = False)
            
            # Now relaunch
            wsp_process = subprocess.Popen(args, shell = False, start_new_session = True)
            
            # wait a bit for it to get set up
            time.sleep(60)
            
            # relink since the dirfile may need to be reconnected
            filePath = os.getenv("HOME") + '/data/dm.lnk'


#%% kill any main process
#killPIDS(main_pid)
        
        # sleep before running loop again
        time.sleep(0.5)

    except KeyboardInterrupt:
        print('exiting watchdog loop.')
        break
    
print('done.')