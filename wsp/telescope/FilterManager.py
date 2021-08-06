#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  5 21:30:08 2021

@author: nlourie
"""

"""
The filter config should look like this:
    
filters:
  r:
    camera: summer
    last_focus: 10500
    position: 3
  u:
    camera: summer
    last_focus: 88
    position: 1
"""

import yaml
import pathlib
import json
import os
import numpy as np
import sys

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'FilterManager: wsp_path = {wsp_path}')

class FilterManager(object):
    def __init__(self, filterConfig_filepath, logger = None):
        self.filterConfig_filepath = filterConfig_filepath
        self.filterConfig = dict()
        self.logger = logger
        
        # load the config
        self.loadConfig()
        
    def log(self, msg):
        msg = 'FilterManager: ' + msg
        if self.logger is None:
            print(msg)
        else:
            self.logger.info(msg)
            
    def loadFocusRecord(self):
        # if the file exists...
        if pathlib.Path(self.filterConfig_filepath).is_file():
            try:
                # load the config
                self.filterConfig = yaml.load(open(self.filterConfig_filepath), Loader = yaml.FullLoader)
            except Exception as e:
                msg = f'could not load filter config: {e}'
                self.log(msg)
                return False
        else:
            msg = f'filter config does not exist! can not load.'
            self.log(msg)
            return False
    
    def updateFocusPosition(self, filterName, position, resaveConfig = True, resaveFilepath = ''):
        # update the focus position if the given filter
        try:
            self.filterConfig['filters'][filterName]['last_focus'] = position
            
            if resaveConfig:
                self.saveFocusConfig(resaveFilepath)
                
        except Exception as e:
            msg = f'could not update filter position: {e}'
            self.log(msg)
            
    def saveFocusConfig(self, filepath = ''):
        # save the new config. by default saves over the old file
        
        if filepath == '':
            filepath = self.filterConfig_filepath
        with open(filepath, 'w') as outfile:
            yaml.dump(self.filterConfig, outfile, default_flow_style=False)
        
        
if __name__ == '__main__':
    
    
    
    
    filepath = 'LastFocus.yaml'
    
    filters = FilterManager(filepath)
    
    print(f'Config File: \n{json.dumps(yaml.load(open(filepath), Loader = yaml.FullLoader), indent = 3)}')
    print()
    
    randomFilterPosition = int(np.random.uniform(low = 10000, high = 10500, size = None))
    
    print(f'Updating u-band filter to: {randomFilterPosition}')
    print()
    
    filters.updateFocusPosition('u', randomFilterPosition)
    
    print(f'Config File: \n{json.dumps(yaml.load(open(filepath), Loader = yaml.FullLoader), indent = 3)}')

        
        