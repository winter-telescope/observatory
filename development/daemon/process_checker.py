#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 17 17:05:34 2021

@author: nlourie
"""
"""


Test Daemon Running in PID 8476

daemon_launcher: launching Pyro5 name server daemon
Pyro5 Name Server Running in PID 8477

daemon_launcher: launching weather daemon
Weather Daemon Running in PID 8484
daemon_launcher: initializing local wea

"""

import psutil, os

main_program_name = 'daemon_launcher'

py_processes = []
main_process = None
child_processes = []
bad = True
for p in psutil.process_iter(['pid', 'name','cmdline']):
    #p = psutil.Process(pid)
    if 'python' in p.name():
        py_processes.append(p)
        

#%%
main_program_name = 'daemon_launcher'
for p in py_processes:
    if main_program_name in p.cmdline()[1]:
        main_process = p
if main_process is None:
    print(f'No {main_program_name} process running.')

else:
    for p in py_processes:
        if p.parent().pid == main_process.pid:
            child_processes.append(p)
    print()
    print(f'Main Process:')      
    for p in [main_process]:
        print(f'\t pid     = \t {p.pid}')
        print(f'\t name    = \t {p.name()}')
        print(f'\t program = \t {p.cmdline()[1].split("/")[-1]}')
        print()
    print(f'Child Processes:')
    for p in child_processes:
    
        print(f'\t pid     = \t {p.pid}')
        print(f'\t name    = \t {p.name()}')
        print(f'\t program = \t {p.cmdline()[1].split("/")[-1]}')
        print(f'\t parent  = \t {p.parent().cmdline()[1].split("/")[-1]}')
        print()
        
