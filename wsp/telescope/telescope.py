#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 17:48:35 2020

telescope_initialize.py

This file is part of wsp

# PURPOSE #

This file has an initialization script which gets the telescope ready for 
observing.

@author: nlourie
"""
import time
import numpy as np
from telescope import telescope

def telescope_initialize():
    print("Initializing Telescope...")
    # Now try to connect to the telescope using the module
    try:
        
        pwi4 = telescope.PWI4(host = "thor", port = 8220)
    
        while True:
            s = pwi4.status()
            time.sleep(2)
            if s.mount.is_connected:
                print("Mount is connected")
                break
            else:
                print("Mount is not connected")
                print("Connecting to Mount...")
                s = pwi4.mount_connect()
                time.sleep(2)
     
    except:
        print("The telescope is not online")    
        #TODO add a message to the log
    
    