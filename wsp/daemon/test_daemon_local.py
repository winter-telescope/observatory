#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  3 17:30:03 2021

local object for test daemon

@author: nlourie
"""


import os
import numpy as np
import sys
import Pyro5.core
import Pyro5.server
import time
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(1, wsp_path)





class local_counter(object):
    
    def __init__(self, base_directory):
        self.base_directory = base_directory
        
        
        
        self.msg = 'local initial value'
        self.count = None
        
        self.init_remote_object()
        self.get_remote_status()
        
        
    def init_remote_object(self):
        # init the remote object
        try:
            self.remote_object = Pyro5.client.Proxy("PYRONAME:counter")
        
        except Exception as e:
            self.logger.error('connection with remote object failed', exc_info = True)
    
    def get_remote_status(self, verbose = False):
        try:
            self.msg = self.remote_object.getMsg()
            self.count = self.remote_object.getCount()
        except Exception as e:
            print(f'Could not update remote status: {e}')
        
        if verbose == True:
            self.print_status()
        
    def print_status(self):
        print(f'Local Object: {self.msg}')
# Try it out
if __name__ == '__main__':


    while True:
        try:
            counter = local_counter(os.path.dirname(os.getcwd()))
            counter.get_remote_status(verbose = True)
            time.sleep(.5)
        except KeyboardInterrupt:
            break
