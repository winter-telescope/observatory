#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 21 14:06:59 2023

freya_watchdog.py

This is part of wsp

# Purpose #

This is a watchdog daemon which makes sure all the necessary daemons are
running on Freya (WINTER camera computer):
    - winterCamerad.py: winter camera daemon
    - winter_image_daemon.py: winter image handler/focusing daemon


# Needs these methods:
    - relaunchCameraDaemon
    - 

@author: nlourie
"""


import time
import datetime
import os

def main():
    while True:
        print(f'env = {os.environ["CONDA_DEFAULT_ENV"]}, time = {datetime.datetime.now()}')
        time.sleep(1)

if __name__ == '__main__':
    main()

