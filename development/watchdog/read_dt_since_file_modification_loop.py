#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May  4 09:13:52 2021

@author: nlourie
"""

import os
import time
from datetime import datetime
import numpy as np
import subprocess

filePath = os.getenv("HOME") + '/data/dm.lnk'
#filePath = os.getenv("HOME") + '/data/dm.lnk/count'
#filePath = 'test.txt'

# launch write loop
#program_to_monitor = 'write_to_file_loop.py'
program_to_monitor = '/Volumes/NateDrive/MIT/WINTER/code/wsp/wsp.py'

args = ["python", program_to_monitor,'-m']
#write_process = subprocess.Popen(args, shell = False, start_new_session = True)


print('starting watchdog loop')
while True:
    
    try:
        #lastmod_timestamp = os.path.getmtime(filePath)
        lastmod_timestamp = os.path.getatime(filePath)

        # DO ALL THE CALCULATIONS LOCALLY OTHERWISE THEY WILL BE WRONG! DON'T USE UTC
        now_timestamp = datetime.now().timestamp()
        #print(f'last update timestamp = {lastmod_timestamp}')
        # get dt in seconds
        dt = now_timestamp - lastmod_timestamp
        
        print(f'dt = {dt}')
        """if dt >= 5.0:
            print(f'dt = {dt:0.2f}, RELAUNCHING WRITER')
            write_process = subprocess.Popen(args, shell = False, start_new_session = True)
            time.sleep(60)"""
        
        # sleep before running loop again
        time.sleep(0.5)

    except KeyboardInterrupt:
        print('exiting watchdog loop.')
        break
    
print('done.')
    





