#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 15 16:45:13 2023

just a test script to debug the winter image daemon functionality

@author: nlourie
"""
import Pyro5.core
import Pyro5.client
import os
import winter_utils.utils

try:
    ns = Pyro5.core.locate_ns(host = '192.168.1.10')
    uri = ns.lookup('WINTERimage')
    image_daemon = Pyro5.client.Proxy(uri)
    image_daemon_connected = True
except Exception as e:
    image_daemon_connected = False
    print(f'could not connect to WINTER image daemon', exc_info = True)


#%% Test the bias validation
#tonight_local_str = winter_utils.utils.tonight_local()
image_output_dir = os.path.join(os.getenv("HOME"), 'data', 'images', 'bias')
bias_dir = os.path.join(os.getenv("HOME"), 'data', '')