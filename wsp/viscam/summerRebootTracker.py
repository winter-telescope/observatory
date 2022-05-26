#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 19 14:00:52 2022

SUMMER accessories reboot tracker

this exists just to keep a log of when we last power-cycled the summer filter wheel
and shutter, so we can enforce regular reboots so it doesn't lose track of where it is 
for too long

@author: winter
"""

import os
import sys
#import pathlib
import json
import yaml
import logging
import traceback
from datetime import datetime, timedelta
import pytz
import random

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f'SUMMERrebootTracker: wsp_path = {wsp_path}')

from utils import utils

class SUMMERrebootTracker(object):

    def __init__(self, config, logger = None):
        self.config = config
        self.logger = logger
        
        self.reboot_log = dict()
        
        self.setupRebootLog()
    
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def setupRebootLog(self):
        """
        Load in the contents of the reboot log file and store to self.reboot_log
        """
        
        self.reboot_log_path = os.path.join(os.getenv("HOME"),self.config['viscam_accessories_reboot_param']['reboot_log_path'])
        
        try:
            self.reboot_log = json.load(open(self.reboot_log_path))
            self.log('loaded existing focus log')
            
            
            
        except json.decoder.JSONDecodeError:
            # this error is thrown when the file is empty
            self.log('found reboot log file but it was empty. setting reboot_log to empty dictionary.')

            # create a new log file
            self.resetRebootLog()
        
        except FileNotFoundError:
            # the file didn't exist
            self.log('no focus log file found. setting up new empty log dictionary')
            
            # create a new log file
            self.resetRebootLog()
    
    def resetRebootLog(self, updateFile = True):
        self.log(f'resetting reboot log')
        
        
        self.reboot_log.update({'last_reboot_timestamp_utc'   : None,
                                'last_reboot_time_local'      : None
                                                    })
        if updateFile:
            self.updateRebootLogFile()
    
    def updateRebootLogFile(self):
        
        # saves the current value of the self.triglog to the self.triglog_filepath file
        # dump the yaml file
        with open(self.reboot_log_path, 'w+') as file:
            #yaml.dump(self.triglog, file)#, default_flow_style = False)
            json.dump(self.reboot_log, file, indent = 2)

    def updateRebootTime(self, timestamp = 'now'):
        """
        update the log with new results
        """
       
        if timestamp == 'now':
            timestamp = datetime.utcnow().timestamp()
        
        # try to update the actual time from the timestamp
        try:
            utc_unaware = datetime.fromtimestamp(timestamp)
            utc = pytz.utc.localize(utc_unaware)
            local_datetime_str = datetime.strftime(utc.astimezone(tz = pytz.timezone(self.config['site']['timezone'])), '%Y-%m-%d %H:%M:%S.%f')
        except Exception as e:
            tb = traceback.format_exc()
            self.log(f'could not update the string formatted timestamp, something is bad with timestamp: {e.__class__.__name__}, {e}, traceback = {tb}')
            local_datetime_str = None
        
        # now update the filter entry in the focus_log
        self.reboot_log.update({'last_reboot_timestamp_utc'   : timestamp,
                                'last_reboot_time_local'      : local_datetime_str
                                            })
        
       
        # now update the focus log file
        self.updateRebootLogFile()
    
    def getHoursSinceLastReboot(self, timestamp = 'now'):
        """
        Read the log file, and return the time since the last reboot
        
        Allows you to pass in a timestamp (UTC) to get the delta from, or
        just assumes now
        
        """
        
        if self.reboot_log['last_reboot_timestamp_utc'] is None:
            # if there is no record of a reboot, report a big number to force one
            dt_hr = 999
        
        else:
            if timestamp == 'now':
                timestamp = datetime.utcnow().timestamp()
            
            dt_sec = timestamp - self.reboot_log['last_reboot_timestamp_utc']
            dt_hr = dt_sec/3600.0
        
        return dt_hr
   
    def printFocusLog(self):
        print('Reboot Log: ', json.dumps(self.focus_log, indent = 2))
        
        
if __name__ == '__main__':

    config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)
    
    
    rebootTracker = SUMMERrebootTracker(config)
    
    dt_hr = rebootTracker.getHoursSinceLastReboot()
    print(f'It has been {dt_hr:.2f} hours since the last reboot')
    
    print()
    print('Simulating a reboot')
    rebootTracker.updateRebootTime()
    
    dt_hr = rebootTracker.getHoursSinceLastReboot()
    print(f'It has been {dt_hr:.2f} hours since the last reboot')