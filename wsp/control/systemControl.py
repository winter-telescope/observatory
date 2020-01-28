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
from telescope import telescope
from telescope import initialize



# Create the control class  
class control(object):
    
    ## Initialize Class ##
    def __init__(self,mode,config_file,base_directory):
        self.config_file = config_file
        self.base_directory = base_directory
        
        if mode not in [0,1,2]:
            raise IOError("'" + str(mode) + "' is note a valid operation mode")
    
        initialize.telescope_initialize()    
        
        # SET UP POWER SYSTEMS #
        pdu1 = power.PDU('pdu1.ini',base_directory)
        
#pdu1 = power.PDU('pdu1.ini',wsp_path)        


