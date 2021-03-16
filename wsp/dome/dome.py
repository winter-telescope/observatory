#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  8 14:34:39 2021

dome.py

This is part of wsp

# Purpose #

This program contains the software interface for the WINTER telescope dome,
including a dome class that contains the necessary commands to communicate
with the telescope dome


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





class local_dome(object):
    
    def __init__(self, base_directory):
        self.base_directory = base_directory
        
        
        
        self.status = dict()
        
        self.init_remote_object()
        self.GetStatus()
        
        
    def init_remote_object(self):
        # init the remote object
        try:
            self.remote_object = Pyro5.client.Proxy("PYRONAME:dome")
        
        except Exception:
            self.logger.error('connection with remote object failed', exc_info = True)
    
    def GetStatus(self, verbose = False):
        try:
            self.status = self.remote_object.GetStatus()
        except Exception as e:
            #print(f'Could not update remote status: {e}')
            pass
        
        if verbose == True:
            self.print_status()
    
    def Home(self):
        try:
            self.remote_object.Home()
        
        except:
            pass
        
    def print_status(self):
        print(f'Local Object Status: {self.status}')
# Try it out
if __name__ == '__main__':


    while True:
        try:
            dome = local_dome(wsp_path)
            dome.GetStatus(verbose = True)
            time.sleep(.5)
            dome.Home()
            time.sleep(0.5)
        except KeyboardInterrupt:
            break
