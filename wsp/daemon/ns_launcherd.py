#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 11 13:02:49 2023

ns_launcherd.py

Pyro5 nameserver launcher 

@author: winter
"""

import sys
import getopt
import Pyro5.nameserver
import time
import subprocess

def check_if_ns_running(ns_host):
    try:
        Pyro5.core.locate_ns(host = ns_host)
        return True
    except:
        # the nameserver is not running
        print('control: nameserver not already running. starting from wsp')
        return False
    
if __name__ == '__main__':
    
    # Set the defaults
    ns_host = '192.168.1.10'
    # Get the command line args
    
    args = sys.argv[1:]
    print(f'args = {args}')
    
    options = "n:"
    long_options = ["ns_host:"]
    arguments, values = getopt.getopt(args, options, long_options)
    # checking each argument
    print()
    print(f'It is me! The nameserver launcher! Woo!')
    print(f'arguments = {arguments}')
    for currentArgument, currentValue in arguments:
        if currentArgument in ("-n", "--ns_host"):
            ns_host = currentValue
    
    # Check if the nameserver is running and kill if not    
    ns_conn = check_if_ns_running(ns_host)
    if ns_conn:
        print(f'nameserver is running at host {ns_host}')
        pass
    else:
        print('nameserver at ns_host: {ns_host} not connected. starting now...')
        # launch the nameserver daemon
        #Pyro5.nameserver.start_ns_loop(host = ns_host)
        pythonpath = '/home/winter/anaconda3/envs/wspV0/bin/python'
        programpath ='/home/winter/anaconda3/envs/wspV0/bin/pyro5-ns'
        subprocess.Popen([pythonpath, programpath, '-n', ns_host])#, close_fds = True)
        
        
        time.sleep(1)
        ns_conn = check_if_ns_running(ns_host)
        if ns_conn is False:
            print(f'attempt to restart nameserver failed :(')
        else:
            print(f'successfully restarted nameserver!')
    
    
    print('nameserver launcher is finished?')