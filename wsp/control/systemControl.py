#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 16:13:17 2020

systemControl.py

This file is part of wsp

# PURPOSE #
This module is the interface for all observing modes to command the various
parts of the instrument including
    - telescope
    - power systems
    - stepper motors
    

@author: nlourie
"""
# system packages
import sys
import os
import numpy as np
import time

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.getcwd())
sys.path.insert(1, wsp_path)

# winter modules
from power import power
from telescope import pwi4
from telescope import telescope
from command import commandServer_multiClient



# Create the control class  
class control(object):
    
    ## Initialize Class ##
    def __init__(self,mode,config_file,base_directory):
        self.config_file = config_file
        self.base_directory = base_directory
        
        
        if mode not in [0,1,2]:
            raise IOError("'" + str(mode) + "' is note a valid operation mode")
    
        if mode == 2:
            #Start up the command server
            #commandServer_multiClient.start_commandServer(addr = '192.168.1.11',port = 7075)
            pass
        if mode in [0,1,2]:
            self.telescope_mount = pwi4.PWI4(host = "thor", port = 8220)
            
        if mode in [0,1]:
            self.telescope_connect()
              
        
        
            # SET UP POWER SYSTEMS #
            pdu1 = power.PDU('pdu1.ini',base_directory)
            pdu1.getStatus()

    # commands that are useful
    def telescope_initialize(self):
        telescope.telescope_initialize(self.telescope_mount)
    def telescope_home(self):
        telescope.home(self.telescope_mount)
    def telescope_axes_enable(self):
        telescope.axes_enable(self.telescope_mount)
    def telescope_connect(self):
        telescope.connect(self.telescope_mount)
    def telescope_disconnect(self):
        telescope.disconnect(self.telescope_mount)
    def telescope_axes_disable(self):
        telescope.axes_disable(self.telescope_mount)
        
if __name__ == '__main__':
    opt = 1
    base_directory = wsp_path
    config_file = ''
    
    winter = control(mode = int(opt), config_file = '',base_directory = wsp_path)
     
    


