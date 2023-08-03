#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 21 12:41:14 2023

This is a daemon script to check if the pyro5 nameserver is running on 
name server host = 192.168.1.10

@author: winter
"""

import Pyro5.core
import Pyro5.nameserver
import time

def check_if_ns_running(ns_host):
    try:
        nameserverd = Pyro5.core.locate_ns(host = ns_host)
        return True
    except:
        # the nameserver is not running
        print('control: nameserver not already running. starting from wsp')
        return False

if __name__ == '__main__':
    ns_host = '192.168.1.10'
    
    ns_conn = check_if_ns_running(ns_host)
    if ns_conn:
        print(f'nameserver is running at host {ns_host}')
        pass
    else:
        print('nameserver at ns_host: {ns_host} not connected. starting now...')
        # launch the nameserver daemon
        Pyro5.nameserver.start_ns_loop(host = ns_host)
        
        time.sleep(1)
        ns_conn = check_if_ns_running(ns_host)
        if ns_conn is False:
            print(f'attempt to restart nameserver failed :(')
        else:
            print(f'successfully restarted nameserver!')
        
