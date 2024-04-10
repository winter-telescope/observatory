#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar 14 13:18:05 2024

@author: nlourie
"""


import os
import sys
import psutil
import os
import signal

# add the wsp directory to the PATH
#wsp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'wsp')


#sys.path.insert(1, wsp_path)

#from daemon import daemon_utils

def getPIDS(progname):
    """
    get any pids of programs that are running with the specified program name
    """
    pidlist = list()
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if progname in p.cmdline():
                pidlist.append(p.pid)
        except:
            pass
    return pidlist

def killPIDS(pidlist, logger = None):
    
    if type(pidlist) is int:
        pidlist = [pidlist]
    
    
    for pid in pidlist:
        try:
            msg = f'>> killing process with PID {pid}'
            os.kill(pid, signal.SIGTERM)
        except:
            msg = f'could not kill process with PID {pid}'
        
        if logger is None:
            print(msg)
        else:
            logger.info(msg)


progname = 'slow_counter.py'
print(f'looking for any running processes associated with progname {progname}')


pids = getPIDS(progname)


print(f'pids = {pids}')

print(f'killing the associated PIDs!!!')
killPIDS(pids)



#%%
# pidlist = list()
# for p in psutil.process_iter(['pid', 'name', 'cmdline']):
#     try:
#         if 'python' in p.name():
#             pid = p.pid
#             name = p.name()
#             cmdline = p.cmdline()
#             print(f'{pid}, {name}, {cmdline}')
#             if progname in p.cmdline():
#                 print('FOUND THE PROGRAM')
#             #pidlist.append(p.pid)
#             print()
#     except:
#         pass