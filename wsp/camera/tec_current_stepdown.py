#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 22 16:17:22 2024

@author: winter
"""

import os
#import numpy as np
import sys
import Pyro5.core
import Pyro5.server
import Pyro5.errors
#import traceback as tb
from datetime import datetime, timedelta
from PyQt5 import QtCore
import logging
import numpy as np
import time
import astropy.io.fits as fits
import json
# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f'camera: wsp_path = {wsp_path}')
from utils import utils
from utils import logging_setup
#from housekeeping import data_handler
try:
    import fitsheader
except:
    from camera import fitsheader

from camera import local_camera



config = utils.loadconfig(wsp_path + '/config/config.yaml')
    
logger = logging_setup.setup_logger(wsp_path, config)        

logger = None
verbose = True


cam = local_camera(wsp_path, config, camname = 'winter',
                   daemon_pyro_name = 'WINTERcamera',
                   ns_host = '192.168.1.10', logger = logger, verbose = verbose)

cam.print_state()


#%% Do a stepdown to characterize TEC
time_between_steps_min = 15
dt_sec = time_between_steps_min*60.0

timefmt = '%I:%M:%S'

dv = 0.5
voltages = np.arange(0., 8.5, dv)

nsteps = len(voltages)
runtime_hours = (time_between_steps_min*nsteps)/60.0

starttime = datetime.now()
endtime_est = starttime + timedelta(seconds = runtime_hours*3600.)

print(f'going to step down voltage from {voltages[0]} to {voltages[-1]} in {dv} steps')
print()
print(f'waiting {time_between_steps_min} min between steps')
print(f'estimated total time: {runtime_hours:.1f} h')
print(f'start time: {starttime.strftime(timefmt)}')
print(f'end time  : {endtime_est.strftime(timefmt)}')
print()
try:
    for voltage in voltages:
        now = datetime.now()
        timestr = now.strftime(timefmt)
        print(f'Setting Voltage {voltage}')
        cam.tecSetVolt(voltage)
        
        time.sleep(dt_sec)
except KeyboardInterrupt:
    print(f'keyboard interrupt, exiting routine')
    


