#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 14 11:01:20 2022

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
import random

# add the wsp directory to the PATH
wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')
# switch to this when ported to wsp
#wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(1, wsp_path)
print(f'FocusTracker: wsp_path = {wsp_path}')

from utils import utils

class FocusTracker(object):
    def __init__(self, config, logger = None):
        """
        This is an object which will help keep track of the focus results.
        When a focus loop is rerun it saves the results,
        and it can be used to query previous focus results.
        
        Focus log will have entries like this:
            {
                "r": {
                    "name": "SDSS r' (Chroma)",
                    "cam": "summer",
                    "nominal_focus": 10150,
                    "last_focus": null,
                    "last_focus_timestamp": null,
                    "last_focus_time": null
            }
        """
        self.config = config
        self.logger = logger
        
        self.focus_log = dict()
        
        self.active_filters = dict()
    
    def log(self, msg, level = logging.INFO):
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def setupFocusLog(self):
        """
        Load in the contents of the focus log file and store to self.focus_log
        """
        
        self.focus_log_path = os.path.join(os.getenv("HOME"),self.config['focus_loop_param']['focus_log_path'])
        
        try:
            self.focus_log = json.load(open(self.focus_log_path))
            self.log('loaded existing focus log')
            
            self.log('searching config file for active filters')
            self.getActiveFilters(cam = 'summer')
            
            
        except json.decoder.JSONDecodeError:
            # this error is thrown when the file is empty
            self.log('found focus log file but it was empty. setting focus_log to empty dictionary.')

            # create a new log file
            self.resetFocusLog()
        
        except FileNotFoundError:
            # the file didn't exist
            self.log('no focus log file found. setting up new empty log dictionary')
            
            # create a new log file
            self.resetFocusLog()
                        
        #except Exception as e:
        #    tb = traceback.format_exc()
        #    msg = f'could not execute due to {e.__class__.__name__}, {e}, traceback = {tb}'
        #    self.log(msg)
        #    self.focus_log = dict()
    
    
    def resetFocusLog(self, updateFile = True):
        self.log(f'resetting focus log')
        # first check the active filters
        self.getActiveFilters()
        
        for filterID in self.active_filters:
                filter_entry = self.active_filters[filterID]
                #self.triglog.update({trigname : False})
                self.focus_log.update({filterID: {  'name' :                filter_entry['name'],
                                                    'cam' :                 filter_entry['cam'],
                                                    'nominal_focus' :       filter_entry.get('nominal_focus', None),
                                                    'last_focus' :          None,
                                                    'last_focus_timestamp': None,
                                                    'last_focus_time':      None
                                                    }})
        if updateFile:
            self.updateFocusLogFile()
    
    def updateFocusLogFile(self):
        
        # saves the current value of the self.triglog to the self.triglog_filepath file
        # dump the yaml file
        with open(self.focus_log_path, 'w+') as file:
            #yaml.dump(self.triglog, file)#, default_flow_style = False)
            json.dump(self.focus_log, file, indent = 2)
    
    def getActiveFilters(self, cam = 'summer'):
        """
        Parameters
        ----------
        cam : string, optional
            DESCRIPTION. Camera name currently operating. The default is 'summer'.

        Returns
        -------
        self.active_flter_list: dictionary
            DESCRIPTION. dictionary of filter entries

        """
        # look through the config file and get any active filters
        # it looks for filters for the current active camera
        #filterID = self.config['filter_wheels'][cam]['positions'][filterpos] # eg. 'r'
        #filtername = self.config['filters'][cam][filterID]['name'] # eg. "SDSS r' (Chroma)"
        
        self.active_filters = dict()
        
        for filterID in self.config['filters'][cam]:
            filter_entry = self.config['filters'][cam][filterID]
            if filter_entry['active'] == True:
                #print(f'Filter with filterID {filterID} is active!')
                self.active_filters.update({filterID: {'name': filter_entry.get('name',''),
                                                       'cam' : cam,
                                                       'nominal_focus' : filter_entry.get('nominal_focus', None)
                                                       }})
                
        return self.active_filters
    
    def checkLastFocus(self, filterID):
        """
        for the given filterID, checks the focus log for previous results.
        returns the last focus timestamp and focuser position
            if no result for filterID returns None for both
        """
        
        if filterID in self.focus_log:
            last_focus = self.focus_log[filterID].get('last_focus', None)
            last_focus_timestamp = self.focus_log[filterID].get('last_focus_timestamp', None)
        
        else:
            last_focus = None
            last_focus_timestamp = None
        
        return last_focus, last_focus_timestamp
    
    def getFiltersToFocus(self, obs_timestamp = 'now'):
        """
        runs through the active filter list and checks the last focus for each
        one. if any filters need focusing it adds them to dictionary of filters
        to focus, self.filters_to_focus, which has key:value pairs of
        filterID:last_focus. If there is no value for the last_focus it will
        give a value of None.
        
        whether a filter "needs" focusing is determined by whether the timestamp
        is within dt of obs_timestamp. obs_timestamp is included as an argument
        so that it can be easily handled in simulation (eg sunsim) mode.
        
        """
        
        if obs_timestamp == 'now':
            utc = datetime.utcnow()
            obs_timestamp = utc.timestamp()
            #utc_datetime_str = datetime.strftime(utc, '%Y-%m-%d %H:%M:%S.%f')
        
    def updateFilterFocus(self, filterID, focus_pos, timestamp):
        """
        update the filter focus log with new results (eg after running a focus loop)
        need to include the filterID, the focus position in microns, and the timestamp (UTC)
        of the observation
        """
        # if the filterID is in active filters, then grab the info from there
        if filterID in self.active_filters:
            name = self.active_filters[filterID].get('name', None)
            cam = self.active_filters[filterID].get('cam', None)
            nominal_focus = self.active_filters[filterID].get('nominal_focus', None)
        else:
            filter_entry = dict()
            # if the filterID is not in active filters, then we have to go rooting through config for it's properties
            for cam in self.config['filters']:
                if filterID in self.config['filters'][cam]:
                    # we ffound the filter! overwrite empty filter_entry
                    filter_entry = self.config['filters'][cam][filterID]
            
            name = filter_entry.get('name', None)
            cam = filter_entry.get('cam', None)
            nominal_focus = filter_entry.get('nominal_focus', None)
        
        # try to update the actual time from the timestamp
        try:
            utc = datetime.fromtimestamp(timestamp, tz = pytz.utc)
            utc_datetime_str = datetime.strftime(utc, '%Y-%m-%d %H:%M:%S.%f')
        except Exception as e:
            tb = traceback.format_exc()
            self.log(f'could not update the string formatted timestamp, something is bad with timestamp: {e.__class__.__name__}, {e}, traceback = {tb}')
            utc_datetime_str = None
        
        # now update the filter entry in the focus_log
        self.focus_log.update({filterID: {  'name' :                name,
                                            'cam' :                 cam,
                                            'nominal_focus' :       nominal_focus,
                                            'last_focus' :          focus_pos,
                                            'last_focus_timestamp': timestamp,
                                            'last_focus_time':      utc_datetime_str
                                            }})
        
       
        # now update the focus log file
        self.updateFocusLogFile()
       
    def printFocusLog(self):
        print('Focus Log: ', json.dumps(focusTracker.focus_log, indent = 2))
        
    def printActiveFilters(self):
        print('Active filters', json.dumps(focusTracker.active_filters, indent = 2))
    
    
    
    
    
if __name__ == '__main__':

    config = yaml.load(open(wsp_path + '/config/config.yaml'), Loader = yaml.FullLoader)
    
    
    focusTracker = FocusTracker(config)
    
    print('setting up focus log')
    focusTracker.setupFocusLog()
    
    print()
    print('initial focus log')
    focusTracker.printFocusLog()
    
    print()
    filterID = 'r'
    focus_pos = random.randint(9000, 11000)
    timestamp = datetime.now(tz = pytz.UTC).timestamp()
    
    print(f'updating the focus position of filter {filterID} to {focus_pos}, timestamp = {timestamp}')

    focusTracker.updateFilterFocus(filterID, focus_pos, timestamp)    
    
    print()
    focusTracker.printFocusLog()
    
    print()
    print(f'updating a random filter name')
    
    filterID = f'filter{random.randint(0,50)}'
    focusTracker.updateFilterFocus(filterID, focus_pos, timestamp)    
    
    print()
    focusTracker.printFocusLog()
    
    
    
    
    