#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  3 17:30:03 2021

local object for test daemon

@author: nlourie
"""


import os
#import numpy as np
import sys
import Pyro5.core
import Pyro5.server
import logging
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(1, wsp_path)

from utils import logging_setup
from utils import utils


class local_counter(object):
    
    def __init__(self, base_directory, logger = None):
        self.base_directory = base_directory
        
        
        self.logger = logger
        self.msg = 'local initial value'
        self.count = None
        self.state = dict()
        
        self.init_remote_object()
        self.update_state()
        
    def log(self, msg, level = logging.INFO):
        
        msg = f'counter: {msg}'
        
        if self.logger is None:
                print(msg)
        else:
            self.logger.log(level = level, msg = msg)
    
    def run_timer(self):
        self.remote_object.run_timer()
        
    def init_remote_object(self):
        # init the remote object
        try:
            self.remote_object = Pyro5.client.Proxy("PYRONAME:counter")
        
        except Exception as e:
            self.log('connection with remote object failed', exc_info = True)
    
    def update_state(self):
        try:
            self.msg = self.remote_object.getMsg()
            self.count = self.remote_object.getCount()
            self.state.update({'count' : self.count})
            #print(f'state = {self.state}')

        except Exception as e:
            #self.log(f'Could not update remote status: {e}')
            pass

        
    def print_state(self):
        self.update_state()
        #print(f'Local Object: {self.msg}')
        print(f'state = {self.state}')
        
# Try it out
if __name__ == '__main__':
    # load the config
    base_directory = wsp_path
    config_file = base_directory + '/config/config.yaml'
    config = utils.loadconfig(config_file)
    logger = logging_setup.setup_logger(wsp_path, config)
    counter = local_counter(wsp_path, logger = logger)
    """while True:
        try:
            counter = local_counter(wsp_path)
            #counter.get_remote_status()
            #counter.print_status()
            print(f'count = {counter.state["count"]}')
            time.sleep(.5)
        except KeyboardInterrupt:
            break"""
