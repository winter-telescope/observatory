#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  9 10:58:35 2021

daemon_launcher.py

This is part of WSP

### PURPOSE ###
This is a script to launch the various daemons that WSP requires
The idea is that this will launch all the various daemons in other processes 
using the subprocess module. Then when the parent script (ie WSP) dies or is killed,
it will kill all the subprocesses without having to track them down individuallly.


# Notes
Originally did this using an approach from here: 
    1. https://stackoverflow.com/questions/23434842/python-how-to-kill-child-processes-when-parent-dies/23587108
    2. https://stackoverflow.com/questions/19447603/how-to-kill-a-python-child-process-created-with-subprocess-check-output-when-t/19448096#19448096
    
    
    
    libc = ctypes.cdll.LoadLibrary("libc.{}".format("so.6" if platform.uname()[0] != "Darwin" else "dylib"))


    def set_pdeathsig(sig = signal.SIGKILL):
        def callable():
            return libc.prctl(1, sig)
        return callable
    
    #args = ["python","-m","Pyro5.nsc"]
    args = ["pyro5-ns"]
    
    #p = subprocess.Popen(args, preexec_fn = set_pdeathsig(signal.SIGKILL),shell = True)
    
BUT the libc.prctl(1,sig) Stuff didn't work out, would throw an AttributeError,
at the moment this is working properly with just subprocess.Popen and no other args.


@author: winter
"""

import os
import sys
import subprocess

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#wsp_path = os.path.dirname(__file__)
print(f'__file__: {__file__}')
print(f'os.path.abspath(__file__): {os.path.abspath(__file__)}')
print(f'wsp path: {wsp_path}')
sys.path.insert(1, wsp_path)

# import wsp packages
from housekeeping import local_weather
from utils import utils

if __name__ == '__main__':

    # Start the Pyro5 Name Server
    args = ["pyro5-ns"]
    print(f'daemon_launcher: launching Pyro5 name server daemon')
    p_nameserver = subprocess.Popen(args,shell = True)
    
    # Start the weather daemon
    print(f'daemon_launcher: launching weather daemon')
    args = ["python",f"{wsp_path}/housekeeping/weatherd.py"]
    p_weatherd = subprocess.Popen(args,shell = True)
    
    # Initialize a local weather object
    print(f'daemon_launcher: initializing local weather object')
    config = utils.loadconfig(wsp_path + '/config/config.yaml')
    night = utils.night()
    logger = utils.setup_logger(wsp_path, night, logger_name = 'logtest')

    weather = local_weather.Weather(os.path.dirname(os.getcwd()),config = config, logger = logger)
    args = []
    
    while True:
        pass
