#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep 26 16:25:39 2023

dark routine tracker

this exists just to keep a log of when we last took darks with the camera
so we can enforce regular dark sequences at a specified cadence without 
interrupting an ongoing observation

@author: nlourie
"""

import os
import sys
#import pathlib
import json
import yaml
import logging
import traceback
from datetime import datetime
import pytz
import pathlib

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f'darkTracker: wsp_path = {wsp_path}')


class DarkTracker(object):

    def __init__(self, config, logger = None):
        self.config = config
        self.logger = logger
        
        self.logdict = dict()
        
        self.setupLog()
    
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def setupLog(self):
        """
        Load in the contents of the log file and store to self.logdict
        """
        
        self.log_dir = os.path.join(os.getenv("HOME"),self.config['cal_params']['dark_tracker']['log_dir'])
        self.log_path = os.path.join(self.log_dir, self.config['cal_params']['dark_tracker']['log_file'])
        
        try:
            self.logdict = json.load(open(self.log_path))
            self.log('loaded existing focus log')
            
            
            
        except json.decoder.JSONDecodeError:
            # this error is thrown when the file is empty
            self.log('found reboot log file but it was empty. setting logdict to empty dictionary.')

            # create a new log file
            self.resetLog()
        
        except FileNotFoundError:
            # the file didn't exist
            self.log('no focus log file found. setting up new empty log dictionary')
            
            # create a new log file
            self.resetLog()
    
    def resetLog(self, updateFile = True):
        self.log(f'resetting reboot log at {self.log_path}')
        
        # re-init dictionary so that anything that got imported is cleaned out
        self.logdict = dict()
        
        # now init the dictionary with the minimum keys and times init'ed to None
        self.logdict.update({'last_darkseq_timestamp_utc'   : None,
                                'last_darkseq_time_local'      : None
                                                    })
        # check whether the file exists
        if os.path.exists(self.log_path):
            # delete the file
            os.remove(self.log_path)
        
        if updateFile:
            self.updateLogFile()
    
    def updateLogFile(self):
        
        # saves the current value of the self.triglog to the self.triglog_filepath file
        # dump the yaml file
        try:
            with open(self.log_path, 'w+') as file:
                #yaml.dump(self.triglog, file)#, default_flow_style = False)
                json.dump(self.logdict, file, indent = 2)
        except FileNotFoundError:
            # create the log file directory if it doesn't exist already
            pathlib.Path(self.log_dir).mkdir(parents = True, exist_ok = True)
            self.log(f'making directory: {self.log_dir}')
            
            # write it out again
            with open(self.log_path, 'w+') as file:
                #yaml.dump(self.triglog, file)#, default_flow_style = False)
                json.dump(self.logdict, file, indent = 2)
            
    def updateDarkSeqTime(self, timestamp = 'now'):
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
        self.logdict.update({'last_darkseq_timestamp_utc'   : timestamp,
                                'last_darkseq_time_local'      : local_datetime_str
                                            })
        
       
        # now update the focus log file
        self.updateLogFile()
    
    def getHoursSinceLastDarkSeq(self, timestamp = 'now'):
        """
        Read the log file, and return the time since the last reboot
        
        Allows you to pass in a timestamp (UTC) to get the delta from, or
        just assumes now
        
        """
        
        if self.logdict['last_darkseq_timestamp_utc'] is None:
            # if there is no record of a reboot, report a big number to force one
            dt_hr = 999
        
        else:
            if timestamp == 'now':
                timestamp = datetime.utcnow().timestamp()
            
            dt_sec = timestamp - self.logdict['last_darkseq_timestamp_utc']
            dt_hr = dt_sec/3600.0
        
        return dt_hr
   
    def printLog(self):
        print('Dark Tracker Log: ', json.dumps(self.focus_log, indent = 2))
        
        
if __name__ == '__main__':

    config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)
    
    
    darkTracker = DarkTracker(config)
    
    darkTracker.resetLog()
    
    dt_hr = darkTracker.getHoursSinceLastDarkSeq()
    print(f'It has been {dt_hr:.2f} hours since the last dark seq')
    
    print()
    print('Simulating a Dark Seq Acquisition')
    darkTracker.updateDarkSeqTime()
    
    dt_hr = darkTracker.getHoursSinceLastDarkSeq()
    print(f'It has been {dt_hr:.2f} hours since the last dark seq')

