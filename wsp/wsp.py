#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wsp: the WINTER Supervisor Program

This file is part of wsp

# PURPOSE #
This program is the top-level control loop which runs operations for the
WINTER instrument. 



"""
import time
import matplotlib.pyplot as plt
import numpy as np
from telescope import telescope

# Now try to connect to the telescope using the module

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
        
        
    
    


 


