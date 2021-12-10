#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May  6 18:35:27 2021

watchdog_start

This is part of wsp

This will start a simple watchdog loop that just checks to make sure
that wsp.py is still writing housekeeping data to its dirfile database




@author: winter
"""
import os
import sys


# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, wsp_path)

# import the alert handler
from watchdog import watchdog

if __name__ == '__main__':
    watchdog.shutdown_watchdog()
    

